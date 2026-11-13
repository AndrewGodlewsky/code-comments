# Plan: Download CSV on the reports page

## Summary

Today the reports page (`/reports/{id}`) loads rows 500 at a time from a read-only copy of the database. This plan adds a **Download CSV** button. For reports of 10,000 rows or fewer, the click response is the CSV itself. For bigger reports, the click creates an export record and queues a background job. The job streams the file into object storage in pieces, then emails the user a 24-hour link. The page shows the export's state from the record. Streaming keeps the worker's memory small. The record and a unique index keep each user to one active export per report.

## Terms

- **Row API**: `GET /api/reports/{id}/rows`. It checks `report.view`, reads `report_rows` from the **read replica**, and pages by keyset (`row_id > after ORDER BY row_id`, never OFFSET). Requests are killed after 60 s.
- **Read replica**: the read-only database copy. Report rows are read only from it, never from the primary.
- **Primary**: the main database. The new `report_exports` table lives here. It holds export metadata, not report data, so the replica-only rule is not broken.
- **Job queue** (`jobs.py`): `@job(name, on_final_failure)` registers a handler and `enqueue(name, payload)` queues it (payload under 64 KB).
  - Delivery is at least once, so a job may run again after it succeeded.
  - There are at most 3 attempts, with waits of 60 s and then 300 s.
  - An attempt is killed after 1800 s. A worker has 512 MB of memory.
  - The queue keeps no progress between attempts.
  - A dead worker or timeout counts as a failed attempt.
  - `on_final_failure` runs once after the last failed attempt.
- **Multipart upload** (`storage.py`, `exports` bucket): upload a file in parts, and it becomes visible only at `complete_multipart`.
  - Each part except the last must be at least 5 MB. There are at most 10,000 parts.
  - Existing bucket rules delete objects after 7 days and discard unfinished uploads after 24 h. We build no cleanup job.
- **Signed URL**: a download link that expires. `signed_url(bucket, key, ttl_seconds)` allows at most 86,400 s (24 h).
- **Active export**: a `report_exports` row with status `queued` or `running`.

## Rules that apply throughout

- Export uses the same `report.view` check and the same filter and `cols` parser as the Row API.
- Never fall back to the primary for report rows. A replica error is a failure.
- Out of scope: scheduled exports, formats other than CSV, changes to the table on the page.

## Data: `report_exports` (primary database)

| Column | Purpose |
|---|---|
| `export_id` (pk) | Identifies the export |
| `report_id`, `user_id` | Whose export of which report |
| `query_string` | Raw `filters` and `cols` from the page URL, so the job reproduces the view exactly |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | Queue job id, null until enqueued |
| `object_key` | `exports/{report_id}/{export_id}.csv`. The same key on every attempt, so a retry or duplicate overwrites safely |
| `attempt` | Current attempt number |
| `row_count_written` | Rows written so far, for debugging |
| `error` | Short failure reason |
| `notified_at` | When the success email was sent |
| `created_at`, `updated_at`, `finished_at` | Timestamps. Every write to the row (mark running, heartbeat, back to queued, done, failed) sets `updated_at`, so it doubles as a heartbeat. |

Unique partial index: `UNIQUE (user_id, report_id) WHERE status IN ('queued','running')`. The database enforces one active export per user and report, not application code.

States: `queued → running → done`; `running → queued` (failed attempt, waiting to retry); `running → failed` (last attempt failed).

## How it runs

### 1. User clicks Download CSV

- **Starts it:** the button sends `POST /api/reports/{report_id}/export?<the page's current query string>`. The query string carries the filters and `cols`.
- **Does:** in order, (1) check `report.view`, else 403; (2) validate `cols` and `filters`, else 400; (3) read `reports.row_count` from the replica. This is the unfiltered total and picks the path: 10,000 or fewer goes to step 2, above 10,000 goes to step 3. So a heavily filtered view of a big report still takes the large path. That follows from the rule as written.
- **State kept:** none.
- **Fails:** 403 and 400 show an inline error. A replica outage returns 503 and the page shows "try again".

### 2. Small path: the response is the CSV

- **Does:** write the header row in the requested column order. Page the replica by keyset with `limit=500` and the request's filters until a page comes back short. Append each row as UTF-8 CSV, quoting commas, quotes and newlines. The whole file is held in memory because it is small (about 450 bytes per row, so about 5 MB at 10,000 rows).
- **Response:** `200`, `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="report-{id}.csv"`, `Content-Length` set.
- **State kept:** none. No job, no table row, nothing in storage.
- **Fails:** no byte is sent until the file is complete, so a failure never gives a truncated file. Any query error returns 503. A 45 s deadline (inside the 60 s API limit) returns 503. If more than 10,000 rows turn up (a stale count), stop and return 503 "try again".

### 3. Large path: create or find the export

- **Does:** insert a `report_exports` row with `status=queued`, `query_string` as received, and the `object_key`, using `ON CONFLICT DO NOTHING` on the unique index. Then go to 3a.
- **State kept:** that row, in the primary database.
- **If the insert conflicts** (an active export exists, including one waiting between retry attempts): return that row as `200 {export_id, status, already_running: true, query_string}` and enqueue nothing. It may have different filters from the current view, so the page shows its filters.
  - **Stale row.** If the active row's `updated_at` is older than 3 hours, treat it as dead (the longest legitimate life is 3 × 1800 s + 360 s of backoff, about 1.6 h). This is the only recovery path for a lost job. In the same request: run one conditional update, set `failed` (no email) `WHERE export_id=? AND status IN ('queued','running') AND updated_at < now() - 3 hours`, so only one request wins. Then repeat the insert. If it conflicts again, another request got there first, so return that row.
  - **Lost enqueue.** If the active row has `job_id` null and is older than 2 minutes, re-enqueue it (3a) instead of creating a new row.
- **Fails:** if the database write fails, return 503 and nothing exists.

### 3a. Enqueue

- Call `enqueue("report_export", {"export_id": ...})`. The payload holds only the id, because filters could exceed the 64 KB limit. Store the returned `job_id` on the row. Respond `202 {export_id, status: "queued"}`.
- **Fails:** if `enqueue` raises, delete the row so the user is not blocked, and return 503. If the process dies between insert and enqueue, the lost-enqueue rule repairs it.

### 4. Page shows the export status

- **Starts it:** page load; a click that returns a status; a poll every 5 s while the shown status is `queued` or `running`.
- **Does:** `GET /api/reports/{report_id}/export` checks `report.view`, then returns the caller's own **most recent** export as `{export_id, status, created_at, finished_at, query_string}`, or 404 if none. After a click, the newest is the one just returned. If a stale row was failed and replaced, the new one is shown.
- **Display:** queued, running, done or failed. Done reads "Check your email for the download link."
- **State kept:** none on the client. The server row is the truth, so a returning user sees the same state.
- **Fails:** if a poll fails, keep the last state and retry next tick. Polling stops at `done` or `failed`.

### 5. Worker starts an attempt

- **Starts it:** the queue calls `handler(ctx, {"export_id"})`. Every attempt starts from scratch.
- **Does:** load the row (it holds user, report and `query_string`).
  1. If `failed`, return (the failure handler already acted). If `done` with `notified_at` set, return (duplicate delivery). If `done` with `notified_at` null, skip to step 7 and only send the email.
  2. Re-check that the user still has `report.view`. If not, raise. All 3 attempts fail the same way and the final-failure handler runs.
  3. Set `status=running`, `attempt=ctx.attempt`, `updated_at=now`.
- **Fails:** any exception is a failed attempt and the queue retries it.

### 6. Build the file as a stream

- **Does:**
  1. `upload_id = start_multipart("exports", object_key)`. A new upload every attempt.
  2. Parse `query_string` with the Row API parser (it was validated at click time). Write the header row in its column order. A parse error is a failed attempt.
  3. Loop: read **5,000 rows** from the replica with the same filters (`row_id > after ORDER BY row_id`), encode as CSV into a buffer, set `after` to the last `row_id`.
  4. When the buffer reaches **8 MB**, `upload_part(upload_id, n, buffer)`, keep the etag, empty the buffer, and update `updated_at` and `row_count_written`.
  5. When a page comes back empty, upload the rest as the last part (it may be under 5 MB).
  6. `complete_multipart(upload_id, etags)`. Only now does the file appear at its key.
- **Size check:** peak memory is one 8 MB buffer plus one page, about 20 to 30 MB, far under 512 MB. The largest report (about 900 MB, 2 million rows) is about 113 parts and about 400 queries. The 1800 s timeout needs only about 0.5 MB/s, so there is large margin. Target under 10 minutes, measured before release.
- **State kept:** `upload_id` and etags live in worker memory only. A half-uploaded file is invisible in storage.
- **Fails:**
  - *Caught exception or replica error:* best-effort `abort_multipart(upload_id)`, set the row back to `queued` with the error text, and re-raise so the queue retries after 60 s, then 300 s.
  - *Timeout kill or worker death:* nothing can run, so the row stays `running` during the backoff, still active. The orphaned upload is discarded by the 24 h bucket rule. If it is the last attempt, `on_final_failure` still runs (step 8).
  - *Half-written file:* never downloadable, because no object exists until `complete_multipart`. A retry overwrites the same key atomically.
  - *Concurrent duplicate delivery:* two workers may run the same export. We add no lock. Each has its own `upload_id` and builds the same file, and the last `complete_multipart` wins. Work is wasted but the result is correct.

### 7. Finish: mark done and email the link

- **Starts it:** `complete_multipart` succeeded, or step 5 found `done` with no `notified_at`.
- **Does, in this order:** (1) set `status=done`, `finished_at=now`; (2) `url = signed_url("exports", object_key, 86_400)`; (3) `send_email(user_id, "report_export_ready", {report_name, url, expires_in: "24 hours"})`; (4) set `notified_at=now`.
- **State kept:** `status`, `finished_at`, `notified_at` on the row.
- **Fails:**
  - If the email raises, the attempt fails and retries. The retry sees `done` without `notified_at`, sends only the email with a fresh URL, and does not rebuild.
  - If the email fails on every attempt, the row stays `done`, the page says "Check your email", and the user has no link (see open questions).
  - If the process dies between sending and setting `notified_at`, a duplicate email is possible. This is acceptable with at-least-once delivery.
  - If the update to `done` fails after the file was completed, the retry rebuilds and overwrites the same key. This wastes work but is correct.
  - The link expires after 24 h. The file is deleted after 7 days by the existing rule.

### 8. Last attempt fails: `on_final_failure`

- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails for any reason (error, timeout, dead worker).
- **Does:** load the row.
  - If already `done` (only the email failed), do not mark it failed. The file is good. Log it for follow-up and stop.
  - Otherwise set `status=failed`, a short `error` (no internals shown to the user), `finished_at=now`. This frees the unique index so the user can start a new export. Then `send_email(user_id, "report_export_failed", {report_name})`, with no link.
- **State kept:** the `failed` row. The page shows it on the next poll or visit.
- **Fails:** the handler is idempotent, so a repeat is harmless. If it dies before updating the row, the 3-hour stale rule in step 3 clears it. If the email fails, the page still shows failed and the failure is logged.

## Tests and checks before release

- **Boundary:** exactly 10,000 rows takes the small path, 10,001 the large path.
- **Permissions:** a user without `report.view` gets 403 on export, on the status endpoint, and at the job re-check.
- **Replica only:** a test or assertion that no export path reads `report_rows` from the primary.
- **Double click:** two simultaneous clicks make one row and one job, and the second returns the first.
- **Retries:** kill an attempt mid-stream (key not visible, next attempt succeeds); fail all 3 attempts (failed state and failure email); fail only the email (no rebuild, not failed).
- **Memory and time:** run the 2-million-row report under a 512 MB limit and record peak memory and duration.
- **Escaping:** commas, quotes, newlines and non-ASCII characters round-trip.

## Open questions for the product owner

1. The page shows state only, and the link comes only by email. Should the done state also offer a button that mints a fresh link?
2. An export started with different filters than the user's current view is returned as "already running" (step 3). Is that acceptable, or should it warn first?
3. If the success email fails on all 3 attempts, the export stays `done` but the user never gets a link. Is logging enough, or should the page offer a way to get one (see question 1)?
