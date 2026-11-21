# Plan: CSV export for the reports page

## Summary

Today the reports page loads rows through an existing API, and the server keeps no record of what a user is looking at (filters and column order live only in the page URL). The new **Download CSV** button calls one new endpoint, which reads `reports.row_count` and picks a path. At 10,000 rows or fewer, the response to the click is the CSV and nothing is stored. Above that, the endpoint records an export in a new table, queues a background job and returns at once. The job streams the rows into object storage and emails a 24-hour link, and the page shows the export's state from the table. It is shaped this way so that no worker ever holds a large report in memory and a half-written file is never downloadable.

## Terms

- **Page API:** the existing `GET /api/reports/{report_id}/rows`. It checks `report.view` on the report's workspace (403 otherwise) and reads `report_rows` only from the **read replica**, never the primary. It pages by keyset (`row_id > after ORDER BY row_id`, never OFFSET), 500 rows per page. `row_id` is unique and increasing within a report. API servers kill any request that runs longer than 60 s.
- **Queue:** `jobs.py`, the background job queue. A job is tried at most 3 times, with a wait of 60 s before attempt 2 and 300 s before attempt 3. An attempt still running after 1800 s is killed. Each attempt restarts the handler from the beginning with the same payload (no saved progress). Delivery is at least once, so a handler may run again after success. `on_final_failure(ctx, payload, error)` is called once after the last attempt fails. Each worker has 512 MB of memory. Payloads must be under 64 KB.
- **Storage:** `storage.py`, with the `exports` bucket. A multipart upload sends a file in parts (each at least 5 MB except the last, at most 10,000 parts). Nothing is visible at the object key until `complete_multipart` succeeds. The bucket deletes every object 7 days after creation and discards multipart uploads not completed within 24 hours. `signed_url` makes a download link that lasts at most 86,400 s (24 hours).
- **Shared CSV writer:** one new function that turns rows into CSV text (RFC 4180 quoting, UTF-8). Both paths use it.
- **`reports.row_count`:** the total, unfiltered row count of a report, rewritten in the nightly rebuild. The largest report has about 2 million rows (roughly 900 MB as CSV, about 450 bytes per row).
- **`report_exports` table:** new, in the **primary database**. It holds export bookkeeping, not report data, so the "no report data from the primary" rule does not apply, and the replica is read-only anyway. Columns:

| Column | Meaning |
|---|---|
| `id` | UUID made by the endpoint. Used in the object key and the job payload. |
| `report_id`, `user_id` | Who asked for which report. |
| `filters`, `cols` | Raw strings copied from the page URL at click time. The only record of what the user was looking at. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id`, `attempt` | The queue's job id, and the last attempt number that started (0 until the first). |
| `upload_id` | The current multipart upload id, so a later attempt or the failure handler can discard an orphaned upload. |
| `object_key` | `reports/{report_id}/{id}.csv`, set at creation. |
| `error` | Short failure reason, shown only in logs and the page's failed state. |
| `created_at`, `started_at`, `finished_at`, `emailed_at` | Timestamps. `emailed_at` makes the email step safe to retry alone. |

  Two indexes: a partial **unique** index on `(report_id, user_id) WHERE status IN ('queued','running')`, which makes the database itself enforce one active large export per user per report, even under double-clicks; and `(report_id, user_id, created_at DESC)` for the page's status lookup.

- **Endpoints (both new):**
  - `POST /api/reports/{report_id}/export` with body `{filters, cols}` copied verbatim from the page URL. It answers `200 text/csv` (small path) or `202 {export_id, status}` (large path). The page script checks the response type and either saves the file or shows status.
  - `GET /api/reports/{report_id}/export` returns the caller's most recent export for the report as `{export_id, status, created_at, finished_at}`, or 404 if none. It reads the primary and needs `report.view`.

## How it runs

### 1. Click: validate and choose a path

- **Starts it:** the click; the page sends `filters` and `cols` from its URL.
- **What it does:**
  1. Check `report.view` (same check as the Page API). If it fails, return 403.
  2. Parse `filters` and `cols` with the Page API's parsing and column validation, moved into one shared function so page and CSV cannot disagree. Return 400 for bad input, or for `filters` + `cols` over 8 KB combined.
  3. Read `reports.row_count` from the replica. If it is 10,000 or fewer, take the small path. Otherwise take the large path.
- **State kept:** none.
- **On failure:** 403 or 400 as above. If the replica is unreachable, return 503 asking the user to try again. Never fall back to the primary.

### 2. Small path: return the CSV in the response

- **Starts it:** step 1 chose the small path.
- **What it does:**
  1. Build the header row in the requested column order.
  2. Read rows from the replica by keyset in pages of 500, with the same filters and `row_id > after ORDER BY row_id`.
  3. Encode each page with the shared CSV writer and hold everything in memory (at most 10,000 rows, about 4.5 MB). This is deliberate: a failure then returns a clean error instead of a truncated download.
  4. Return `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{id}-{date}.csv"`.
  5. If the loop reads more than 10,000 rows, `row_count` was stale: switch to the large path.
  6. Stop after 45 s (under the 60 s kill). This should never trigger, since 10,000 rows is about 20 queries.
- **State kept:** none. No job runs and nothing is stored.
- **On failure:** a query error or the 45 s limit returns 503 with a retry message. The page shows the error and the user clicks again. No partial CSV is ever sent.

### 3. Large path: create or return the export record

- **Starts it:** step 1 chose the large path, or step 2 found a stale count.
- **What it does:**
  1. Make an `id` and `INSERT` a `queued` row (with `filters`, `cols`, `object_key`) using `ON CONFLICT DO NOTHING` against the unique index. If a row was inserted, go to step 4.
  2. If nothing was inserted, a queued or running export already exists. `SELECT` it and return `202` with its id and status; no second export starts. Even if its filters differ from this click, the existing one wins, and the UI says "An export of this report is already in progress."
  3. If that `SELECT` finds nothing, the other export finished in between: repeat the insert once.
  4. If the existing row is `queued`, has no `job_id` and is over 2 minutes old, a request crashed between insert and enqueue. Run step 4 again for that row, using its existing id.
- **State kept:** the `report_exports` row, the single source of truth for "one at a time".
- **On failure:** if the database write fails, return 503. Nothing was queued, so a retry is clean.

### 4. Enqueue the job

- **Starts it:** step 3 inserted a row or is repairing a stuck one.
- **What it does:** call `enqueue("report_export", {"export_id": id})`. The payload is only the id; the job reads filters, columns and user from the table. Store the returned `job_id` on the row and return `202 {export_id, status: "queued"}`.
- **State kept:** `job_id` on the row.
- **On failure:**
  - If `enqueue` raises, set the row to `failed` with an error note, which frees the unique slot, and return 503.
  - If the process dies after the insert but before `job_id` is saved, the row sits `queued` with no job; the 2-minute repair rule in step 3 fixes it on the next click.
  - If `enqueue` worked but saving `job_id` failed, repair may queue a second job for the same id. That is safe because the job tolerates duplicates (step 5).

### 5. Page shows the export's state

- **Starts it:** a 202 response, or any later visit to `/reports/{report_id}`.
- **What it does:** on page load, and every 5 s while the state is `queued` or `running`, the page calls `GET /api/reports/{report_id}/export` and shows a status line (queued, running, done or failed). It stops polling at `done` or `failed`. While queued or running, the button is disabled and shows the status. The state survives a closed tab because it lives in the table.
- **State kept:** none new; the page only reads.
- **On failure:** if a poll fails, keep the last known state and retry on the next tick. The job does not depend on the page.

### 6. Worker starts an attempt

- **Starts it:** the queue runs `report_export(ctx, payload)`, on the first attempt and on every retry, always from the beginning.
- **What it does:**
  1. Load the row by `payload.export_id`.
  2. If `status` is `failed`, return. If it is `done`, jump to step 9 (covers duplicate delivery and email-only retries).
  3. If the row has an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore errors (storage discards stragglers after 24 hours anyway).
  4. Set `status='running'`, `attempt=ctx.attempt`, `started_at=now`.
  5. Call `start_multipart("exports", object_key)` and store the new `upload_id`.
- **State kept:** the row (`running`, `attempt`, `upload_id`).
- **On failure:** raise; the queue retries after its backoff. The page keeps showing "running", including during the 60 s and 300 s waits.

### 7. Worker streams rows into the upload

- **Starts it:** step 6 finished.
- **What it does:**
  1. Start an in-memory buffer holding the header row.
  2. Loop: read the replica by keyset in pages of 5,000 rows, using the stored `filters`, `cols` and `row_id > after ORDER BY row_id`. Never fetch the whole result; each query is short, so no long-lived cursor is held on the replica.
  3. Encode each page with the shared CSV writer and append it to the buffer.
  4. When the buffer reaches **16 MB**, call `upload_part(upload_id, n, data)`, keep the etag, clear the buffer and increment `n`. That is above the 5 MB minimum and gives about 57 parts for the 900 MB report, far below 10,000.
  5. After the last page, upload what remains as the final part. The header row guarantees at least one part, even when a filter matches nothing.
  6. After each part, check elapsed time. Past 1700 s, call `abort_multipart` and raise, because a timed-out attempt is killed and cannot clean up.
- **Memory and time:** memory stays at about one 16 MB buffer plus one 5,000-row page, far below 512 MB at any report size. The 2-million-row report is about 400 queries and 57 uploads. Measure it on a production-sized report before release; the aim is well under 15 minutes, leaving more than half of the 1800 s limit spare.
- **State kept:** etags in worker memory only. A retry starts over from row 1.
- **On failure:** on any exception (replica or upload error), try `abort_multipart`, then re-raise so the queue retries. A killed attempt (timeout or dead worker) leaves an orphaned upload, which the next attempt aborts in step 6, or storage discards after 24 hours. Nothing is visible at `object_key` until completion, so a half-written file is never downloadable.

### 8. Worker completes the file

- **Starts it:** step 7 uploaded every part.
- **What it does:**
  1. Call `complete_multipart(upload_id, etags)`; the object appears at `object_key` all at once.
  2. Run `UPDATE report_exports SET status='done', finished_at=now WHERE id=? AND status='running'`.
- **State kept:** `status='done'`.
- **On failure:** if `complete_multipart` fails, raise and let the queue retry. If the worker dies between the two calls, the object exists but the row says `running`; the retry rebuilds the whole file and replaces the object at the same key with the same content. No link exists until step 9, so nobody can fetch the file early.

### 9. Worker emails the download link

- **Starts it:** step 8 marked the export `done`, or step 6 found a `done` row.
- **What it does:**
  1. Skip if `emailed_at` is set.
  2. Call `signed_url("exports", object_key, 86400)`. This is the maximum, and the link works for 24 hours from now.
  3. Call `send_email(user_id, "report_export_ready", {report name, url, expires})`.
  4. Set `emailed_at=now`.
- **State kept:** `emailed_at`. A retry only repeats this step and never rebuilds 900 MB for an email problem.
- **On failure:** raise so the queue retries. A rare duplicate email from at-least-once delivery is accepted.

### 10. Last attempt fails: mark failed and notify

- **Starts it:** the queue calls `on_final_failure` once, after attempt 3 fails.
- **What it does:**
  1. Load the row. If it is already `done`, only the email failed: log it and stop, so the page keeps showing the good file.
  2. Otherwise set `status='failed'`, `error` (short text) and `finished_at=now`. This frees the unique slot so the user can start a new export. Do this **before** the email, so the page is right even if the email fails.
  3. If an `upload_id` is stored, call `abort_multipart`, ignoring errors.
  4. Call `send_email(user_id, "report_export_failed", {report name})`.
- **State kept:** `status='failed'`.
- **On failure:** wrap the abort and the email in try/catch and log them; this handler is not retried. If the database update itself fails, the row stays `running` and blocks new exports: alert on this case and consider a manual reset.

### 11. Cleanup

The bucket's lifecycle rule does it, with no code from us: objects go 7 days after creation and uncompleted uploads after 24 hours. No cleanup job is built. `report_exports` rows stay as history.

## What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Click | no permission, bad input, over 8 KB | 403 or 400 |
| Click, small path | replica down, query error, 45 s limit | 503, nothing sent, user clicks again |
| Large path, insert | database write fails | 503, nothing queued |
| Enqueue | `enqueue` raises | row set `failed`, slot freed, 503 |
| Enqueue | crash before `job_id` saved | next click after 2 minutes repairs it |
| Worker | error or timeout in an attempt | upload aborted or left to expire, queue retries from row 1 |
| Worker | crash between complete and `done` | retry rebuilds, replaces same key |
| Email | send fails | queue retries only the email; if all fail, export stays `done` and the failure is logged |
| All 3 attempts fail | | row `failed`, failure email sent |
| Status poll | request fails | page keeps last state, retries in 5 s |

## Open questions

1. **Email templates.** `report_export_ready` and `report_export_failed` are assumed to be new `send_email` templates. Adjust if names are fixed elsewhere.
2. **`row_count` is unfiltered and nightly.** A filtered export of a big report still takes the large path, by design. A nightly rebuild during a long export could mix old and new rows in one file; nothing guards against it. Decide whether that matters.
3. **Expired files.** The link lasts 24 hours and the object 7 days. After that a `done` export has no file but the page still shows "done" (the four fixed states). Consider an "expired" note on `done` exports older than 7 days. A new click already starts a fresh export, since only `queued` and `running` block.
4. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in a spreadsheet. The brief does not mention it. The shared CSV writer is the one place to add a guard.
5. **Persistent timeouts.** If the 2-million-row report cannot finish within 1800 s, all three attempts time out and the export ends `failed`. The load test is the guard.

## Build and test checklist

- 10,000 rows returns CSV. 10,001 rows queues a job. A stale `row_count` falls through to the large path.
- Two concurrent clicks produce one export row and one job. After `done` or `failed`, a click starts a new export.
- A user without `report.view` gets 403 on both endpoints.
- A worker killed mid-upload and retried leaves no object at the key until completion, and the orphan upload is aborted.
- Failure on all three attempts gives status `failed` and a failure email. Failure only in the email step leaves the status `done`.
- A load test on the 2-million-row report shows peak memory under 512 MB and a runtime well under 1800 s.

Out of scope: scheduled exports, formats other than CSV, and changes to the table on the page.
