# Plan: Download CSV on the reports page

## 0. Background and decisions

**Terms**
- **Row API**: `GET /api/reports/{id}/rows`. It checks `report.view`, reads `report_rows` from the **read replica**, and pages by keyset (`row_id > after ORDER BY row_id`). Requests are killed after 60 s.
- **Job queue** (`jobs.py`): `@job(name, on_final_failure)` handlers and `enqueue(name, payload)`.
  - Delivery is at least once.
  - An attempt is killed after 1800 s, and a worker has 512 MB of memory.
  - There are at most 3 attempts, with waits of 60 s and then 300 s.
  - The queue keeps no progress between attempts.
- **Storage** (`storage.py`): multipart upload to the `exports` bucket.
  - Nothing is visible until `complete_multipart`.
  - Parts must be at least 5 MB, except the last.
  - Objects are deleted after 7 days, and unfinished uploads are discarded after 24 h. Both are existing rules, and we add no cleanup job.

**Decisions**
- **Export record.** Export state lives in a new table, `report_exports`, in the **primary** database. This is export metadata, not report data, so the replica-only rule is not broken. Report rows are still read only from the replica.
- **One active export per user and report.** The active-export rule is enforced by a database unique index, not by application code.
- **Deterministic file name.** The object key is `exports/{report_id}/{export_id}.csv`. A retry or a duplicate delivery overwrites the same key through `complete_multipart`, so it is safe.
- **No in-memory report.** Large exports stream: page from the replica, buffer about 8 MB, upload a part, repeat.

**New table `report_exports`**

| Column | Purpose |
|---|---|
| `export_id` (pk) | Identifies the export |
| `report_id`, `user_id` | Whose export of which report |
| `query_string` | Raw `filters` and `cols` from the page URL, so the job reproduces the view exactly |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | Queue job id, null until enqueued |
| `object_key` | Where the file is stored |
| `attempt` | Current attempt number |
| `row_count_written` | Rows written so far, for debugging |
| `error` | Short failure reason |
| `notified_at` | When the success email was sent |
| `created_at`, `updated_at`, `finished_at` | Timestamps. `updated_at` doubles as a heartbeat. |

Unique partial index: `UNIQUE (user_id, report_id) WHERE status IN ('queued','running')`.

**State machine:**
- `queued → running → done`
- `running → queued` (failed attempt, waiting to retry)
- `running → failed` (last attempt failed)

---

## 1. User clicks "Download CSV"

- **Starts it:** the button sends `POST /api/reports/{report_id}/export?<the page's current query string>`. The query string carries the filters and `cols`.
- **Data moves:** the browser sends the query string. The server returns either a CSV or a small JSON status.
- **Checks, in order:**
  1. Verify the caller has `report.view` on the report's workspace. If not, return 403, the same as the Row API.
  2. Validate `cols` and `filters` with the **same parser the Row API uses**. If invalid, return 400.
  3. Read `reports.row_count` from the replica. This is the unfiltered total and decides the path.
- **State kept:** none yet.
- **Failure:** 403 and 400 show an inline error on the page. If the replica is unavailable, return 503 and show "try again". Never fall back to the primary.

Row count 10,000 or fewer goes to step 2. Above 10,000 goes to step 3. Because `row_count` ignores filters, a heavily filtered view of a big report still takes the large path. That follows from the rule as written.

---

## 2. Small path (10,000 rows or fewer): the response is the CSV

- **Starts it:** step 1 chose this path.
- **Data moves:**
  1. Write the header row, using the requested column order.
  2. Page the replica by keyset with `limit=500` and the request's filters, from the start of the report until a page comes back short.
  3. Append each row as CSV, with correct quoting and escaping of commas, quotes and newlines, in UTF-8.
- **Why buffer:** the whole file is held in memory because it is small. At roughly 450 bytes per row, 10,000 rows is about 5 MB.
- **Response:** `200`, `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="report-{id}.csv"`, with `Content-Length` set. The browser's normal download handles it.
- **State kept:** none. No job, no table row, nothing in storage.
- **Failure:**
  - The whole file is built before any byte is sent, so a failure never produces a truncated file that looks complete. Any query error returns 503 with no file.
  - Use a 45 s deadline inside the 60 s API limit. If it is hit, return 503.
  - If the row count exceeds 10,000 while reading (a stale count), stop and return 503 with "try again" rather than send a partial file.

---

## 3. Large path (above 10,000 rows): create or find the export

- **Starts it:** step 1 chose this path.
- **Data moves:** insert a row into `report_exports`:
  - `status=queued`
  - `query_string` as received
  - `object_key=exports/{report_id}/{export_id}.csv`
  - `ON CONFLICT DO NOTHING`, using the unique partial index.
- **State kept:** the `report_exports` row in the primary database.
- **If the insert hit the conflict** (the user already has an active export of this report):
  - Select that active row and return it. Respond `200 {export_id, status, already_running: true}` and do not enqueue anything.
  - The returned export may have been started with different filters. The response includes its filters, and the page shows them, so the user knows which view is being exported.
  - **Stale rows.** If the active row's `updated_at` is older than 3 hours, treat it as dead. The longest legitimate life is 3 × 1800 s + 360 s of backoff, about 1.6 h. Mark it `failed` (no email) and carry on to create a new one. This is the only recovery path for a lost job.
  - **Lost enqueue.** If the active row has `job_id` null and is older than 2 minutes, re-enqueue it (step 3a) instead of creating a new row.
- **Failure:** if the database write fails, return 503 and nothing exists.

### 3a. Enqueue

- Call `enqueue("report_export", {"export_id": ...})`. The payload holds only the id, because filters could exceed the 64 KB limit. The job reads the filters from the table.
- Store the returned `job_id` on the row.
- Respond `202 {export_id, status: "queued"}`.
- **Failure:** if `enqueue` raises, delete the row so the user is not blocked, and return 503. If the process dies between the insert and the enqueue, the row is repaired by the "lost enqueue" rule above.

---

## 4. Page shows the export status

- **Starts it:**
  - The page loads.
  - A click returns a status (steps 1 and 3).
  - A poll fires every 5 s, only while the shown status is `queued` or `running`.
- **Data moves:** `GET /api/reports/{report_id}/export` returns the caller's **most recent** export for this report as `{export_id, status, created_at, finished_at, query_string}`, or 404 if none. It checks `report.view` first, and only ever shows the caller's own exports.
- **State kept:** none on the client. The server row is the source of truth, so a user returning later sees the same state.
- **Display:** queued, running, done, or failed. A done export reads "Check your email for the download link."
- **Failure:** if a poll fails, keep the last state and retry on the next tick. Polling stops at `done` or `failed`. The existing table is not changed.

---

## 5. Worker runs the job (each attempt starts here)

- **Starts it:** the queue calls `handler(ctx, {"export_id"})`. Each attempt starts from scratch, because the queue keeps no progress.
- **Data moves:** load the `report_exports` row from the primary database.
- **Steps:**
  1. **Already finished?** If the row is `failed`, return, since the failure handler already acted. If it is `done` and `notified_at` is set, return (a duplicate delivery). If it is `done` and `notified_at` is null, skip to step 7 and only send the email.
  2. **Permission re-check.** Confirm the user still has `report.view`. If not, raise an error. All 3 attempts fail the same way, and the final-failure handler then runs.
  3. **Mark running.** Set `status=running`, `attempt=ctx.attempt`, `updated_at=now`.
- **State kept:** the table row.
- **Failure:** any exception here is a failed attempt, and the queue retries it (step 8).

---

## 6. Build the file as a stream, never holding the report

- **Starts it:** step 5 completed.
- **Data moves:**
  1. `upload_id = start_multipart("exports", object_key)`. This is a new upload for every attempt. Nothing is visible at the key yet.
  2. Start with the header row, using the column order from `query_string`.
  3. Loop. Read **5,000 rows** from the replica with the same filters, `row_id > after ORDER BY row_id`. Keyset paging keeps every page equally fast, and OFFSET is never used. Encode the rows as CSV into a buffer. Set `after` to the last `row_id`.
  4. Whenever the buffer reaches **8 MB**, call `upload_part(upload_id, n, buffer)`, store the etag, and empty the buffer. Update `updated_at` and `row_count_written` as a heartbeat.
  5. When the page comes back empty, upload the remaining buffer as the last part (it may be under 5 MB, which is allowed for the last part).
  6. `complete_multipart(upload_id, etags)`. Only now does the file appear at its key.
- **Memory:** peak is about one 8 MB buffer plus one 5,000-row page, roughly 20 to 30 MB. That is far under 512 MB. The largest report (about 900 MB) is about 113 parts, well under the 10,000-part limit.
- **Time:** 2 million rows is about 400 queries. The 1800 s timeout allows about 0.5 MB/s, which is very slow, so this should finish with margin. Before shipping, run it against the 2-million-row report and record the time. The target is under 10 minutes.
- **State kept:** the `upload_id` and etags live in the worker's memory only. A half-uploaded file is invisible in storage.
- **Failure:**
  - **Caught exception.** Call `abort_multipart(upload_id)` in a `finally`/`except` block (best effort), set the row back to `queued` with the error text, and re-raise so the queue retries after 60 s, then 300 s.
  - **Timeout kill or worker death.** Nothing can run, so the row stays `running` during the backoff, which still counts as active. The orphaned upload is discarded by the bucket's 24-hour rule. We do not clean it up ourselves.
  - **Replica error mid-stream.** This is a failed attempt. Never fall back to the primary.
  - **Half-written file.** A half-written file can never be downloaded, because no object exists until `complete_multipart` succeeds. A retry overwrites the same key atomically.

---

## 7. Finish: mark done and email the link

- **Starts it:** `complete_multipart` succeeded in step 6, or this is a retry that found `done` with no `notified_at` (step 5).
- **Order matters.**
  1. Set `status=done`, `finished_at=now`. The page now shows done.
  2. `url = signed_url("exports", object_key, 86_400)`. This is the 24-hour maximum.
  3. `send_email(user_id, "report_export_ready", {report_name, url, expires_in: "24 hours"})`.
  4. Set `notified_at=now`.
- **State kept:** `status`, `finished_at` and `notified_at` on the row.
- **Failure:**
  - If the email raises, the attempt fails and is retried. The retry sees `done` with no `notified_at`, so it only re-sends the email and does not rebuild the file. A fresh signed URL is made each time.
  - If the process dies between sending and setting `notified_at`, the user may get a duplicate email. This is acceptable, since delivery is at least once.
  - After 24 hours the link expires. The file itself is deleted after 7 days by the existing rule.
  - If the database update to `done` fails after the file was completed, the retry rebuilds and overwrites the same key. This is wasted work, but it is correct.

---

## 8. Last attempt fails: `on_final_failure`

- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.
- **Data moves:**
  1. Load the row.
  2. If it is already `done` (only the email failed), do **not** mark it failed. The file is good. Log the problem for follow-up and stop.
  3. Otherwise set `status=failed`, `error` (short, no internals shown to the user), `finished_at=now`. This also frees the unique index, so the user may start a new export.
  4. `send_email(user_id, "report_export_failed", {report_name})`. It has no download link.
- **State kept:** the `failed` row. The page shows failed on the next poll or visit.
- **Failure:** the handler must be idempotent, so a repeat is harmless. If it dies before updating the row, the row is cleared later by the 3-hour stale-row rule in step 3. If the failure email fails, the page still shows failed, and the failure is logged.

---

## 9. Tests and checks before release

- **Boundary.** A report with exactly 10,000 rows takes the small path, and one with 10,001 takes the large path.
- **Permissions.** A user without `report.view` gets 403 on the export, the status endpoint, and the job re-check.
- **Replica only.** An assertion or test that no export path reads `report_rows` from the primary.
- **Double click.** Two simultaneous clicks produce one row and one job. The second returns the first.
- **Retry cases.**
  - Kill an attempt mid-stream, and confirm the key is not visible and the next attempt succeeds.
  - Fail all 3 attempts, and confirm the failed state and the failure email.
  - Fail only the email, and confirm no rebuild and no failed state.
- **Memory.** Run the 2-million-row report under a 512 MB limit, and record the peak and the duration.
- **Escaping.** Commas, quotes, newlines and non-ASCII characters in cell values round-trip correctly.

## 10. Open questions for the product owner

1. The page shows state only, and the download link comes only by email. Should the done state also offer a button that mints a fresh link?
2. An export started with different filters than the user's current view is returned as "already running" (step 3). Is that acceptable, or should it warn first?
