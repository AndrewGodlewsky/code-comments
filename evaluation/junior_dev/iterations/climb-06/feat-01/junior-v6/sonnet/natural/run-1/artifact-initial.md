# Plan: CSV export for the reports page

## Background

- The page is `/reports/{report_id}`. It loads rows from `GET /api/reports/{report_id}/rows`. That call checks `report.view` and returns 403 if the caller lacks it.
- Rows come from the read replica, 500 at a time, by keyset (`row_id > after ORDER BY row_id`). Report data is never read from the primary.
- Filters and column order exist only in the page URL. The server stores nothing about them, so the click must send them.
- API requests are killed after 60 seconds.
- Jobs run on the `worker` pool: 512 MB per worker, 3 attempts, and an attempt is killed after 1800 s. The backoffs are 60 s and 300 s.
- The queue keeps no progress between attempts, and every attempt restarts from the beginning. Delivery is at least once, so a handler can run again after it has succeeded.
- The `exports` bucket deletes objects after 7 days and discards incomplete multipart uploads after 24 hours.
- Nothing is visible at an object's key until `complete_multipart` succeeds. A completed multipart upload replaces any object already at that key.

## Decisions that apply to every step

- **Shared row reader.** Pull the current rows endpoint's filter parsing, column validation and keyset query into one function, `iter_report_rows(report_id, filters, cols, page_size)`. It reads from the replica only and yields rows in `row_id` order. The rows API, the small-export path and the job all call it. Export therefore cannot drift from what the page shows.
- **Export state lives in a new `report_exports` table on the primary database.** This is not report data, so the primary is allowed. It must be the primary because the "one at a time" guarantee needs a unique index, and a lagging replica would show stale status.

  | Column | Meaning |
  |---|---|
  | `export_id` | Primary key. |
  | `report_id`, `user_id` | Whose export it is. |
  | `filters`, `cols` | Snapshot of the view at click time. |
  | `status` | `queued`, `running`, `done` or `failed`. |
  | `job_id` | Queue job id, nullable. |
  | `object_key` | Always `exports/{export_id}.csv`. |
  | `row_total` | Rows written, nullable. |
  | `error` | Failure reason, nullable. |
  | `notified_at` | When the success email was sent, nullable. |
  | `created_at`, `updated_at` | Timestamps. |

  A **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')` enforces one active export per user per report.
- **Filters are not part of the uniqueness key.** The rule is one active large export per user per report, so a second click with different filters returns the first export. The UI should say this (see open questions).
- **Size rule.** Use `reports.row_count` at click time. At 10,000 or fewer rows the export is synchronous. Above that it is a job. `row_count` is the unfiltered total, so a heavily filtered export of a big report still takes the job path. That is intended and simple.

## Steps

### 1. User clicks Download CSV: the request

- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/export` with the current filters and `cols` copied from the page URL.
- **Data moves:** browser to API: `report_id`, `filters`, `cols`.
- **State kept:** none yet.
- **If it fails:**
  - No `report.view` on the report's workspace: return 403 and do nothing else.
  - Invalid filter or column: return 400. The same validation as the rows API runs here, so a bad request never becomes a job.
  - API or network error: the browser shows an error. Nothing was created, so the user can click again.

### 2. API picks a path

- **Starts it:** step 1 passing its checks.
- **Data moves:** read `reports.row_count`. This is metadata, not report rows. Read it from wherever the page reads it today.
- **State kept:** none.
- **If it fails:** a failed read of `row_count` returns 503 with nothing created.
- **Rule:** 10,000 rows or fewer goes to step 3. More than 10,000 goes to step 4.

### 3. Small export: stream the CSV in the response (no job, nothing stored)

- **Starts it:** step 2 chose the small path.
- **Data moves:**
  - The API replies 200 with `Content-Type: text/csv` and `Content-Disposition: attachment; filename=report-{report_id}.csv`.
  - It writes the header row from the requested `cols`, then loops over `iter_report_rows` (500 rows per page, replica only). It formats each page with a real CSV writer (correct quoting of commas, quotes and newlines; UTF-8) and writes it to the response as it goes.
  - Memory use is one page.
  - 10,000 rows is about 20 pages, which fits well inside the 60 s request limit.
- **State kept:** none. Nothing is written to the database or the bucket.
- **If it fails:**
  - Once streaming has started, the HTTP status is already sent. A replica error or the 60 s kill therefore cuts the connection mid-body. Do not send `Content-Length`. Use chunked transfer, so the browser treats a cut connection as a failed download rather than a complete file.
  - Log the error.
  - The user can click again. There is no retry and no partial state.

### 4. Large export: claim the slot, or return the existing export

- **Starts it:** step 2 chose the large path.
- **Data moves:** in one transaction on the primary, `INSERT INTO report_exports` a row with `status='queued'`, a new `export_id`, `object_key`, and the `filters` and `cols` snapshot.
  - If the partial unique index rejects the insert, an export is already active. Select that row and return it. No second row is created and no second job is queued (**one at a time**).
- **State kept:** the `report_exports` row.
- **If it fails:**
  - A database error returns 503 and nothing was created.
  - If the insert wins but the process dies before step 5, a `queued` row exists with no `job_id`. It would block the user. The recovery is in step 5, not a cleanup job.

### 5. Enqueue the job and answer immediately

- **Starts it:** step 4 created a new row.
- **Data moves:**
  - `enqueue("export_report_csv", {"export_id": ...})`. The payload is the id only (well under 64 KB). The job reads everything else from the row.
  - Store the returned `job_id` on the row.
  - Respond 202 with `{export_id, status:"queued"}`. This returns straight away.
- **State kept:** `job_id` on the row.
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` (error "could not queue"), return 503, and the user can click again.
  - If the process dies between the insert and the enqueue, the row is `queued` with a null `job_id`. When the user clicks again, step 4 finds that row. If it is `queued`, has no `job_id` and is older than 2 minutes, enqueue it now and store the id. Running the handler twice is safe (step 7), so a wrong guess is harmless.
  - Clicking an export that already has a `job_id` just returns it.

### 6. Page shows the export's state

- **Starts it:** the 202 response, or the user opening `/reports/{report_id}` later.
- **Data moves:**
  - `GET /api/reports/{report_id}/export` checks `report.view`, then returns the current user's most recent export for that report: `{export_id, status, created_at}`, or 204 if there is none. Read it from the primary.
  - The page shows queued, running, done or failed. While the status is `queued` or `running`, it polls every 5 seconds. It stops on `done` or `failed`.
  - The Download CSV button is disabled while an export is active.
- **State kept:** reads only. The status is whatever the job wrote in steps 7 to 11.
- **If it fails:** a failed poll keeps the last known status and retries on the next tick. The user can reload at any time and gets the stored state.

### 7. Worker starts an attempt

- **Starts it:** the queue calls `export_report_csv(ctx, payload)`, on attempt 1 and again on each retry. It may also run a second time after a success, since delivery is at least once.
- **Data moves:** load the row by `export_id`.
  - If `status='done'` and `notified_at` is set, return (duplicate delivery).
  - If `status='done'` and `notified_at` is null, jump to step 10. The file is complete, so only the email is missing.
  - If `status='failed'`, return.
  - Otherwise `UPDATE ... SET status='running'`.
- **State kept:** `status='running'`, `updated_at`.
- **If it fails:** raising fails the attempt, and the queue retries after 60 s, then 300 s. A missing row is a bug: raise and let the queue retry, and the final-failure hook (step 11) handles it.

### 8. Stream rows into the bucket (the bounded-memory loop)

- **Starts it:** step 7 decided there is work to do.
- **Data moves:**
  - `start_multipart("exports", object_key)` returns an `upload_id`. Keep it only in a local variable.
  - Write the header row into an in-memory buffer.
  - Loop over `iter_report_rows` (replica only) with a larger page than the UI uses, for example 2,000 rows. Append each formatted page to the buffer.
  - When the buffer reaches **8 MB** (above `MIN_PART_BYTES`), call `upload_part(upload_id, n, buffer)`, keep the returned etag, and clear the buffer. Send whatever remains as the last part, which may be under 5 MB.
  - **Memory:** at any moment the worker holds about one 8 MB buffer, one page of rows, and a list of etags (about 113 for the 900 MB report). That is far below 512 MB and never grows with the report.
  - **Part limit:** 900 MB is about 113 parts, well under `MAX_PARTS` (10,000). At 8 MB parts the limit is not reached until about 80 GB.
  - **Time:** 2 million rows in 1800 s needs about 1,100 rows/s sustained. That is about 2 s per 2,000-row page including the upload. See open questions about measuring this.
- **State kept:** the multipart upload and the etag list live only in this attempt. The object key is deterministic, so a retry needs nothing from the failed attempt.
- **If it fails:**
  - On any exception, call `abort_multipart(upload_id)` (best effort, ignore errors from the abort itself), then re-raise. The attempt fails and the queue retries from the start with a fresh upload.
  - A worker crash or timeout skips the abort. The orphaned parts are discarded by the bucket's 24-hour rule, so no cleanup job is needed.
  - **A half-written file can never be downloaded**, because nothing is visible at the key until step 9.

### 9. Complete the upload, then mark the export done

- **Starts it:** the loop in step 8 finished with no rows left.
- **Data moves:**
  - `complete_multipart(upload_id, etags)` makes the whole object visible at once. If an earlier attempt had already completed it, this simply replaces it with an identical file.
  - Then `UPDATE report_exports SET status='done', row_total=... WHERE export_id=... AND status='running'`.
- **State kept:** the finished object in the `exports` bucket (deleted by the 7-day rule). The row now says `done`.
- **If it fails:**
  - If `complete_multipart` raises, run step 8's failure handling and retry.
  - If the process dies after completing but before the status update, the retry rebuilds and replaces the same object. Wasteful but correct.
  - The status moves to `done` only after the object is whole.

### 10. Email the download link

- **Starts it:** step 9 finished (or step 7 found `done` with `notified_at` null).
- **Data moves:**
  - `url = signed_url("exports", object_key, 86_400)` is created now, so the 24 hours start when the email is sent.
  - `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`.
  - Then set `notified_at = now()`.
- **State kept:** `notified_at`. The signed URL itself is not stored.
- **If it fails:**
  - If `send_email` raises, the attempt fails. The retry goes through step 7, sees `done` with `notified_at` null, and runs only this step. It does not rebuild the file.
  - A crash after sending but before `notified_at` is written can produce a duplicate email. This is accepted, because a duplicate is better than a missing link.
  - The page already shows `done`, because step 9 committed first.

### 11. Final failure

- **Starts it:** the queue calls the `on_final_failure(ctx, payload, error)` hook once, after attempt 3 fails. It is registered as `@job("export_report_csv", on_final_failure=...)`.
- **Data moves:**
  - `UPDATE report_exports SET status='failed', error=<short message> WHERE export_id=... AND status != 'done'`.
  - If that updated a row, send `send_email(user_id, "report_export_failed", {report name})`.
  - Optionally call `abort_multipart` if an upload is known (normally nothing to do).
- **State kept:** `status='failed'` and `error`. Failed is not an active state, so the user can start a new export.
- **If it fails:**
  - If the export is already `done` (only the email kept failing), the hook leaves it as `done` and sends no failure email, because the file exists. Raise an alert for the failed email instead.
  - If the failure email itself fails, log it. The page still shows `failed`.

## Tests to write

- Exactly 10,000 versus 10,001 `row_count` pick different paths.
- The small path sends no `Content-Length`, creates no row, and makes no storage calls.
- Two concurrent large clicks give one row and one job (unique index).
- A killed attempt followed by a retry gives one complete object and one email.
- `status='done'` is never visible before the object exists.
- Duplicate delivery after success sends no second email and does not rebuild the file.
- A 2-million-row run stays under 512 MB peak memory.
- The final-failure path sets `failed` and sends the failure email.

## Open questions for the requester

1. **Throughput.** Does the replica sustain about 1,100 rows/s on the largest report? Run the job once against it before release. If it does not, the queue cannot resume across attempts, so the fix has to be a faster query or a larger page. Slower than the limit means all three attempts time out.
2. **Revoked access.** Permission is checked at click time only. Should the job re-check `report.view` before emailing the link?
3. **Different filters on a second click.** The user gets the already-active export, which may have different filters. Is a short message on the page enough?
4. **Link after 24 hours.** The email link expires after 24 hours but the file lives 7 days. The page does not offer a download link. Should it generate a fresh signed URL on demand? This is not in the brief, so it is not planned.
5. **Spreadsheet formulas.** Should cells beginning with `=`, `+`, `-` or `@` be escaped to prevent formula injection when the CSV is opened in a spreadsheet?
