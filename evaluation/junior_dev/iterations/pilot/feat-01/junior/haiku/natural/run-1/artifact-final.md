# CSV export for the reports page: implementation plan

## Terms used in this plan

- **Read replica**: a read-only copy of the database. Report rows are read only from it. Writes go to the **primary** database.
- **Keyset paging**: fetching the next page with `WHERE row_id > :after ORDER BY row_id LIMIT n`, where `:after` is the last `row_id` of the previous page. Offset paging is never used.
- **`filters` and `cols` text**: the `filters` and `cols` parts of the page URL's query string, kept as text. Example: `filters` = `status=open&region=EU`, `cols` = `date,customer,amount`. The existing rows API parser turns them into a list of column conditions and a list of column names. The grammar of `filters` belongs to that parser, which is not in this plan's files. This plan relies on only three guarantees from it: it rejects malformed input, it names only columns it can check, and its values can be bound as parameters (Open question 9).
- **Job queue**: `enqueue(name, payload)` runs `handler(ctx, payload)` on the worker pool. Each **attempt** runs the handler from the start, and the queue keeps no progress between attempts. A job gets at most 3 attempts. Attempt 2 starts 60 s after attempt 1 fails. Attempt 3 starts 300 s after attempt 2 fails. The queue retries only after a failed attempt. An attempt is killed after 1,800 s, and a worker death counts as a failed attempt. Delivery is at least once, so a handler can run again for a job that already succeeded. `on_final_failure(ctx, payload, error)` runs once, after the third failed attempt.
- **Handler and `ctx`**: the **handler** is the function the queue calls for each attempt. This plan's handler is `report_csv_export`, registered in the export module as `@job("report_csv_export", on_final_failure=...)`. Its `ctx` has two fields only: `job_id` and `attempt`. The handler reads the attempt number `n` from `ctx.attempt` and the export id from `payload.export_id`.
- **Bucket**: a named container in object storage. `exports` is the existing bucket for export files. A **key** is the path of an object inside a bucket.
- **Signed URL**: a download link that works without signing in, until its expiry time. `signed_url` makes one. Anyone who holds it can download the object until it expires.
- **Multipart upload**: object storage assembles an object from numbered parts. Nothing is visible at the object's key until `complete_multipart` succeeds. `complete_multipart` replaces any existing object at that key in one step. `abort_multipart` discards the parts.
- **Export record**: a row in a new `report_exports` table in the primary database. It holds export state (status, attempt number, file location, timestamps). It is not view state. Filters and column order still live only in the page URL.
- **Active export**: an export record whose status is `queued` or `running`.

## Who runs each step

- **API servers** (the web application that serves `/api/...`): Steps 1 to 8 and Step 14. They check permission, choose the path, stream the sync CSV, create and queue the export record, and answer the status and download requests.
- **Job workers** (the processes that run `report_csv_export`): Steps 9 to 13 and Step 15. They claim the row, read the replica, write the file, send the email and handle final failure.
- **Helpers used by both**: the CSV writer (Step 4), and the existing storage helpers from `storage.py` (`signed_url`, the multipart calls) and the existing `send_email`. This plan treats any exception from these helpers as a failure. Their error types and timeouts are not documented in the files (Open question 11).

## Decisions this plan makes where the brief is silent

1. The path threshold uses `reports.row_count` (the unfiltered total), as the brief says. A filter that matches 3 rows on a 2-million-row report still takes the job path.
2. "One large export at a time" is scoped to **user and report**. A second click with different filters returns the active export, and the page shows that export's own filters so the user is not misled.
3. Each attempt writes its file to `exports/{export_id}/attempt-{n}.csv`, where `n` is the attempt number. Only one run can hold a given attempt number (Step 9), so no two runs share a key, and a file being downloaded is never overwritten.
4. The download link in the email is a bearer link. Anyone who holds it can download for 24 hours. This is listed under Open questions.
5. The queue does not document what its `error` argument contains, so the plan does not try to tell timeout, exception and worker death apart. Every final failure gets `error_code = 'attempts_exhausted'`, and the text of `error` is stored for diagnosis, if it has any.
6. `job_id` (the value returned by `enqueue`) is stored on the export row only for support lookups. Nothing in this plan reads it.

## Plan

### Step 1. The page sends the export request

- **Starts:** the user clicks **Download CSV** on `/reports/{report_id}`.
- **Data:** the page takes the query string of the current URL and sends its `filters` and `cols` values unchanged, as text, in a request to `POST /api/reports/{report_id}/exports` with JSON body `{"filters": "...", "cols": "..."}`. No report rows are sent.
- **The response decides the path.** The server chooses the path in Step 3, and the same endpoint returns one of these. The page branches on the HTTP status and the `Content-Type`:
  - **200 with `Content-Type: text/csv`**: the sync path (Step 5). The page reads the body as a file and saves it in the browser, using the filename from `Content-Disposition`.
  - **202 with `Content-Type: application/json`**: the large path (Steps 6 and 7). The body is the export state described in Step 8. The page shows the status panel.
  - **400, 403, 404, 500 or 503 with a JSON error body**: the page shows the message in the body.
- **State:** none in this step.
- **On failure:**
  - A network error or a 5xx response from the sync path, or from Step 3 or Step 6, shows "Export could not start. Try again." No record is created.
  - The one exception is the 503 from a Step 7 enqueue failure. That request has already created a row, which is marked `failed` with `error_code = 'enqueue_failed'`. The page shows the same message, and the user can try again.
  - If the sync stream breaks part way (Step 5), the page's read of the body fails and the page shows "Download failed. Try again."
- **Try again:** the **Try again** action on a failed export sends the same request as Download CSV, built from the current page URL. It is not a different request.

### Step 2. The API checks permission and validates the input

- **Starts:** the request from Step 1 arrives. The caller is the signed-in user of the existing web application. This plan uses that application's existing session check and does not change it.
- **Checks, in order:**
  1. The caller must have `report.view` on the report's workspace. This is the same check the rows API makes for the page (`existing/reports_page.md`). Otherwise return **403**.
  2. `filters` is parsed into conditions and `cols` into a list of column names, using the rows API's parser. Every column named in either must exist on the report. A malformed filter or an unknown column returns **400**. Values are never pasted into SQL text: each value is passed as a bound parameter. Each column name in the SQL is taken from the report's column list, matched to the parser's output, so no column name comes from the request text directly.
  3. If the combined `filters` and `cols` text is longer than 8 KB, return **400**. The size is the UTF-8 byte length of the two text values together. The export record and job payload must stay small.
- **Error bodies:** 400, 403, 404, 500 and 503 responses are JSON objects with a `message` field, which the page displays. This plan defines no other fields.
- **Data moved:** none.
- **State:** none.
- **On failure:** 403 or 400 is returned at once. Nothing is stored.

### Step 3. Choose the path by row count

- **Starts:** a validated request.
- **Data:** one read of `reports.row_count` for the report, from the **read replica**. `reports.row_count` is a column of the `reports` table. The nightly rebuild rewrites it. `row_count` is report metadata, not report rows, but the plan reads it from the replica too, so no report data comes from the primary. Replica lag can make the value older than the primary's (Open question 2).
- **Rule:**
  - `row_count` is 10,000 or less: go to Step 5 (sync path).
  - `row_count` is more than 10,000: go to Step 6 (large path).
- **State:** none.
- **On failure:** report not found returns **404**. Replica unreachable returns **503**. Do **not** fall back to the primary.

### Step 4. One CSV writer, shared by both paths

- **Starts:** called by Step 5 for each page, and by Step 10 for each page in the job. One writer means both paths produce identical files.
- **Input:** the column names from `cols`, in `cols` order, and a stream of rows (strings).
- **Output:** CSV bytes.
  - The first line is a header row. Its labels are the column names exactly as they appear in `cols` (for example `date,customer,amount`). The page's display labels are not used.
  - Lines end with CRLF.
  - A cell is wrapped in double quotes if it contains a comma, a double quote, CR or LF. Double quotes inside a cell are doubled, as RFC 4180 requires.
  - Text is UTF-8.
  - A cell that starts with `=`, `+`, `-` or `@` gets a leading apostrophe (formula-injection guard; see Open questions). This also affects negative numbers.
- **Data:** rows go in, bytes come out. The writer holds no rows between calls.
- **State:** none.
- **On failure:** an encoding error raises. The caller treats it as a failed request (sync path) or a failed attempt (job).

### Step 5. Sync path (row_count of 10,000 or less)

- **Starts:** Step 3 chose the sync path.
- **Data:** keyset pages of 500 rows from the replica:
  `SELECT row_id, <cols> FROM report_rows WHERE report_id = :id AND <filters> AND row_id > :after ORDER BY row_id LIMIT 500`
  Here `<cols>` and `<filters>` stand for the column names and conditions from Step 2, built as described there. Each page goes through the Step 4 writer. The bytes are streamed as the response, with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}-{YYYY-MM-DD}.csv"`. The date is the server's UTC date on the day the request starts.
- **Memory:** one page at a time. The file is streamed, never built whole.
- **State:** nothing is stored. There is no export record and no file.
- **Time limit:** API servers kill any request after 60 s. At 500 rows a page, 10,000 rows is about 20 queries, which should finish well inside the limit. Step 18 checks this.
- **Hard cap:** if more than 10,000 rows come back (possible when `row_count` is stale), stop writing and close the connection without the final chunk. The page's read then fails, and the user sees a failed download rather than a silently short file. Log the event.
- **On failure:** a database error, timeout or cap hit ends the stream early. Nothing was stored, so the user simply clicks again.

### Step 6. Create the export record (large path)

- **Starts:** Step 3 chose the large path.
- **Order of operations:** the stale check runs first, then the insert. A concurrent request is decided by the unique index and the conditional updates, not by timing.
- **Stale check first:** if the user already has an active export of this report whose `updated_at` is older than the stale limit (Step 16), set that row to `failed` with `error_code = 'stale'`. The update's condition repeats the staleness test, so a row that has just been updated is not closed. If that row has `upload_id` set, call `abort_multipart(upload_id)`, ignore its errors, and clear `upload_id` in the same step. A run still writing to that upload fails at its next `upload_part` or heartbeat and stops (Step 11).
- **Data:** insert one row into `report_exports` in the **primary** database: `id` (new UUID), `user_id`, `workspace_id`, `report_id`, `filters`, `cols`, `status = 'queued'`, `attempt = 0`, `created_at`, `updated_at`.
- **Duplicate guard:** a partial unique index on `(user_id, report_id) WHERE status IN ('queued', 'running')` makes the insert "insert or do nothing". If nothing was inserted, read the existing active row and return it. The response is **202** with that row's state, in the same fields as the Step 7 and Step 8 responses. `attempt` is the row's current value (0 if still queued, the running attempt number otherwise), so the page shows that export's filters.
- **State:** the primary database row holds export state only.
- **On failure:** a database write error returns **500**. Nothing is queued, so the user can click again.

### Step 7. Queue the job

- **Starts:** Step 6 inserted the row.
- **Data:** `enqueue("report_csv_export", {"export_id": "<uuid>"})`. The payload is only the ID, far under the 64 KB limit. The job reads `filters` and `cols` from the row. The plan calls `enqueue` once per request; there is no enqueue retry.
- **State:** the queue holds the job. The row holds `job_id`, the value returned by `enqueue`, which is used only for support lookups.
- **Response:** **202** with the same fields as the Step 8 response for the new row: `export_id`, `status` (`"queued"`), `attempt` (0), `filters`, `cols`, and the other Step 8 fields.
- **On failure:**
  - If `enqueue` raises or times out, update the row in the same request to `status = 'failed'`, `error_code = 'enqueue_failed'`, and return **503** with a message. Without this, a row that no worker will run would block the user's next click. The job may in fact have been queued. If it runs, Step 9 sees `failed` and returns at once.
  - If saving `job_id` on the row fails after a successful enqueue, log the error and still return the 202. The job runs from the row alone (Step 9). The missing `job_id` affects only support lookups.
  - If the process crashes after the insert but before the enqueue, the row stays `queued` with no job. The stale guard in Step 6 and Step 16 recovers it after 2 hours, when the user next clicks.

### Step 8. The page shows the export's state

- **Starts:** page load (this covers a user who comes back later), and the 202 response from Step 6 or Step 7.
- **Data:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export for that report, by `created_at`, whatever its status: `id`, `status`, `attempt`, `rows_written`, `filters`, `cols`, `created_at`, `completed_at`, and `download_available`. It returns only rows owned by the caller. `error_code` and `error_message` are stored for support only and are not returned by this endpoint or by the download endpoint.
  - A new export is created only when no active one exists. So the most recent export is the active one whenever one exists, and otherwise the last finished one. A stale row closed by Step 6 or Step 16 is the most recent export and is therefore shown with status `failed`.
  - If the caller has never exported this report, the endpoint returns HTTP 200 with `{"export": null}`.
  - `download_available` is true only when `status = 'done'` and the current time is before `completed_at + 7 days`. Step 12 records `completed_at` before the file is completed, so this expiry is never later than the bucket's deletion time.
- **Behaviour:** while the status is `queued` or `running`, the page polls every 5 s. It stops polling at `done` or `failed`. The status panel shows "Queued", "Running (attempt N of 3)", "Ready to download", or "Failed, start again". The panel shows the `filters` and `cols` of the export it displays. When the response is `{"export": null}`, the page shows only the Download CSV button and no status panel. The "Available until" date is `completed_at + 7 days`, shown in the user's local time zone.
- **State:** the page holds only what it displays.
- **On failure:** a failed poll keeps the last state shown and retries after 15 s. Nothing is cancelled.

### Step 9. Each attempt starts: load and claim the export

- **Starts:** the queue runs the handler `report_csv_export` for attempt `n`. `ctx.attempt` gives `n` (1, 2 or 3). The export id comes from `payload.export_id`. The handler is registered in the export module with `@job("report_csv_export", on_final_failure=...)` and run by the existing worker pool. Steps 9 to 13 all run inside this one handler call, so a failure in any of them, including the email in Step 13, counts as a failed attempt, and the 1,800-second timeout covers all of them.
- **Load:** read the row for `payload.export_id` from the primary.
  - Row missing: log and return. There is nothing to do.
  - `status = 'done'` and `email_sent_at` is empty: go to Step 13 only. The file already exists, so the export is not rebuilt. This branch does not run the permission check or the claim below, so the email can be sent even if the user has since lost `report.view` (Open question 13).
  - `status = 'done'` and `email_sent_at` is set: return.
  - `status = 'failed'`: return. The stale guard or the final failure already closed it.
  - `status = 'running'` and `attempt >= n`: another run of this attempt is live or has already run. Log and return.
  - Otherwise (`status = 'queued'`, or `status = 'running'` with `attempt < n`): continue to the permission check and claim.
- **Permission:** check that `user_id` still has `report.view` on the workspace, using the same check as Step 2. If not, raise. The attempt counts as failed.
- **Claim:** `UPDATE report_exports SET status = 'running', attempt = :n, updated_at = now() WHERE id = :id AND (status = 'queued' OR (status = 'running' AND attempt < :n))`.
  - **Check the number of rows updated.** If it is 0, the row is no longer queued or running, or another run has already claimed this attempt number. Log and return **without doing any work**. This is not an error.
- **Why a lower `attempt` is safe to take over:** the queue retries only after a failed attempt, so a `running` row with a lower attempt number belongs to an attempt that has ended.
- **Clean up an earlier attempt:** if `upload_id` is set on the row, call `abort_multipart(upload_id)` and clear the field. Ignore errors from this call, because a completed upload cannot be aborted.
- **State:** the primary row.
- **On failure:** a database error or a permission failure raises. The queue then retries, and after the third failure Step 15 applies.
- **Memory limit:** the 512 MB limit belongs to the existing worker pool (`jobs.py`). This plan does not set or enforce it. Step 10 keeps this job's memory use well below it.

### Step 10. Stream rows from the replica into the writer

- **Starts:** Step 9 claimed the row.
- **Parse again:** before the first query, the job runs `filters` and `cols` from the row through the same rows API parser and the same column check as Step 2, using the report's current column list. No parsed form is saved; the stored text is the only copy. If parsing or the column check fails, the attempt raises, the queue retries, and Step 15 applies after the third failure. In practice the same text was accepted in Step 2, so this fails only if the report's columns or the parser changed in between.
- **Paging state:** `after` is a variable held in memory for this attempt. The first query has no lower bound on `row_id`. After each page, `after` becomes the last `row_id` of that page. It is not saved anywhere, so a retry starts again from the first row.
- **Data:** keyset pages of **5,000** rows from the replica (larger than the API's 500, to cut round trips; Step 18 confirms the size):
  `SELECT row_id, <cols> FROM report_rows WHERE report_id = :id AND <filters> AND row_id > :after ORDER BY row_id LIMIT 5000`
  Each page goes through the Step 4 writer, and the bytes are appended to a part buffer.
- **Nightly rebuild during the read:** if the nightly rebuild rewrites `report_rows` while this read runs, the result is not settled by this plan. See Open question 3.
- **End of data:** stop when a page returns fewer than 5,000 rows, including zero rows. Then flush the last part buffer (Step 11) and go to Step 12.
- **Replica only:** the job's database role has no grant on the primary's `report_rows`. An accidental primary read fails instead of succeeding.
- **Memory:** one page (about 2 to 3 MB) plus one part buffer (16 MB). The whole report is never held. The peak is well under the 512 MB worker limit.
- **Scale:** 2 million rows at 5,000 a page is about 400 queries.
- **On failure:** a replica error or timeout raises. The queue retries from the first row, because it keeps no progress. The previous upload is aborted in Step 9.

### Step 11. Upload the file in parts

- **Starts:** the part buffer reaches 16 MB, or the last page has been written.
- **Key:** `exports/{export_id}/attempt-{n}.csv`.
- **Setup (first buffer in an attempt):** call `start_multipart(exports, key)` to get an `upload_id`. Save `upload_id` on the row right away, so a later attempt or the final failure can abort it. Update only `WHERE id = :id AND attempt = :n AND status = 'running'`.
  - **If that update matches 0 rows,** the row has moved on: the stale guard or the final failure closed it, or the claim was lost. Call `abort_multipart(upload_id)`, ignore its errors, and return without writing more. The row may not hold this `upload_id`, so this is the only place this upload is aborted.
- **Each full buffer:** call `upload_part(upload_id, part_number, bytes)`, with part numbers counting from 1. Keep the returned etags in memory. For the largest report that is about 60 entries. After each part, update `rows_written` and `updated_at` on the row with the same condition. This is the heartbeat that Step 16 relies on.
  - If that update matches 0 rows, the row has moved on (the stale guard or the final failure closed it). Abort this upload with `abort_multipart`, and return without writing more.
- **Limits:** 16 MB parts satisfy the 5 MB minimum. The last part may be smaller. The 10,000-part maximum is far above the roughly 60 parts needed for a 900 MB file.
- **Visibility:** nothing is visible at the key yet.
- **State:** `upload_id` and `rows_written` on the row. The parts sit in storage, invisible.
- **On failure:** an `upload_part` error raises, and the queue retries. The next attempt aborts the stored `upload_id` (Step 9). If the worker dies, the parts stay invisible, and the bucket's 24-hour rule discards an upload that is never completed.

### Step 12. Complete the file and mark it done

- **Starts:** the last part is uploaded.
- **Data:** take `t0 = now()` immediately before calling `complete_multipart(upload_id, etags)`. The object becomes visible at its key. Because the key is unique to this attempt, no other object is replaced.
- **Then:** `UPDATE report_exports SET status = 'done', file_key = :key, rows_written = :n, upload_id = NULL, completed_at = :t0, updated_at = now() WHERE id = :id AND attempt = :n AND status = 'running'`.
  - `completed_at` is `t0`, which is never later than the object's creation, so the expiry shown on the page (Step 8) is never later than the bucket's deletion.
  - **Check the number of rows updated.** If it is 0, the row moved on (the stale guard closed it). Log and return. The file at the key is unreferenced and the 7-day rule removes it.
- **State:** the row.
- **On failure:**
  - If `complete_multipart` fails, nothing is visible. Raise. The retry builds a new file under its own attempt key.
  - If the complete call succeeds but the row update fails, raise. The row still says `running` with `upload_id` set. The next attempt, or the final failure in Step 15, calls `abort_multipart(upload_id)`; that call fails, because the upload is already complete, and its error is ignored. The completed file from the failed attempt stays in the bucket, unreferenced, until the 7-day rule removes it. No other cleanup is done.

### Step 13. Email the download link

- **Starts:** the row is `done` and `email_sent_at` is empty. This happens after Step 12, or in Step 9's `done` branch on a later attempt.
- **Data:**
  - `expires_at` is the expiry of the signed link: signing time plus 86,400 seconds (24 hours). It is not the 7-day file expiry. It is sent as an ISO 8601 UTC timestamp.
  - `url = signed_url(exports, file_key, 86400)`.
  - `send_email(user_id, "report_export_ready", {report_id, download_url: url, expires_at})`.
  - The email template tells the user that the link works for 24 hours, and that after it expires they should open the report and press **Download**. That button works until the date shown on the page (7 days after the file was built). The template's full text is owned outside this plan; it must meet these requirements.
- **After a successful send:** `UPDATE report_exports SET email_sent_at = now() WHERE id = :id`.
- **State:** the row (`email_sent_at`). The email provider holds the message.
- **On failure:** if `send_email` raises, the attempt raises and the queue retries. The next attempt takes the "done, email not sent" branch in Step 9 and sends again without rebuilding the file. If every attempt fails here, Step 15 does not change a `done` export to `failed`. The page then shows "Ready to download", but the user gets no email.
- **Known duplicate:** if the email is sent but recording `email_sent_at` fails, the next attempt sends it again. This is accepted.

### Step 14. Download from the page

- **Starts:** the user clicks **Download** on a `done` export. The button uses the `id` from the latest export (Step 8). That is the export on the screen, with its filters.
- **Data:** the button navigates to `GET /api/exports/{export_id}/download`, which checks, in this order:
  1. The caller owns the row (`user_id`) and still has `report.view`. Otherwise **403** or **404**.
  2. `status = 'done'`. Otherwise **404**.
  3. The date on the row: if now is at or after `completed_at + 7 days`, return **410** without calling object storage.
  4. Otherwise return a **302** redirect to `signed_url(exports, file_key, ttl)`, where `ttl` is the smaller of 86,400 seconds and the time left until `completed_at + 7 days`. The browser follows the redirect and downloads the file. The URL is generated on each click and is never stored. Because `completed_at` is never later than the object's creation (Step 12), the link expires before the object is deleted.
- **Expiry:** the bucket deletes each object 7 days after it was created. The page shows "Available until {completed_at + 7 days}" and hides the button after that (see Step 8).
- **State:** none written.
- **On failure:** not the owner, or permission lost: **403** or **404**. Date passed: **410**, and the page shows "This export has expired. Start a new one." The plan decides 410 from the row date only. It does not ask object storage whether the object exists, so an object removed early (for example by hand) is not detected. What storage returns for an expired signed link is not specified (Open question 10), and this plan does not depend on it.

### Step 15. Final failure

- **Starts:** the third attempt has failed. This may be an exception, the 1,800-second timeout, or a worker death. The queue calls `on_final_failure(ctx, payload, error)` once.
- **Logic:**
  1. Load the row. If it is missing, log and return.
  2. If `status = 'done'`, do not change it. The file is fine and only the email failed. Log the error.
  3. Otherwise update the row to `status = 'failed'`, `error_code = 'attempts_exhausted'`, `error_message` = the text of `error`, cut to 500 characters, `completed_at = now()` (the moment the row is marked failed), and `updated_at = now()`. Use the condition `status IN ('queued', 'running')`. The text of `error` may be empty or unhelpful; no logic in this plan depends on it.
  4. If `upload_id` is set, call `abort_multipart(upload_id)`, ignore any error, and clear `upload_id`. If the upload was already completed (Step 12), this call fails and its error is ignored. A completed file from a failed attempt is then left unreferenced, and the 7-day bucket rule removes it.
  5. Call `send_email(user_id, "report_export_failed", {report_id})`. The failure email's text is owned outside this plan. Log any error from the send and do not raise it.
- **Effect:** the export no longer counts as active, so the user can start a new one. The page shows "Failed" with a **Try again** action, which sends a new Step 1 request.
- **On failure of this handler itself** (for example, the database is down): log it. The row stays `queued` or `running` until the stale guard in Step 16 recovers it.

### Step 16. Stale-row guard

- **Starts:** a user clicks again (Step 6) while their one active row is old. The guard runs only at that click. Nothing else polls for stale rows.
- **Rule:** an active row is treated as stale, and set to `failed` with `error_code = 'stale'` (and its upload aborted, as Step 6 describes), when:
  - it is `queued` and has not been updated for more than 2 hours, or
  - it is `running` and has not been updated for more than 45 minutes.
- **Why these numbers:** a running attempt is killed 30 minutes after it starts, and its row is updated when it starts and after every part. The queue then waits at most 5 minutes before the next attempt. So a live run goes at most about 35 minutes without an update. The 45-minute limit gives a 10-minute margin beyond that. A queued job can wait longer if the worker pool is saturated, so queued rows get 2 hours. If a stale row's job runs later, Step 9 sees `failed` and returns. Both thresholds are assumptions for the owner to confirm.
- **State:** the row.

### Step 17. Concurrency and duplicate delivery

- **Two clicks at once:** the partial unique index lets one insert win. The other request reads the winning row (Step 6).
- **Duplicate delivery of one job:** the queue's at-least-once delivery (see `jobs.py`) can run the same job more than once. Two runs of the same attempt number cannot both write. The claim in Step 9 accepts a `running` row only for a lower attempt number, and the database serializes the updates. The second run sees the same attempt number and returns.
- **A duplicate after the export is done:** it takes Step 9's `done` branch. If the email has not been recorded, it may send the email a second time. This is accepted.
- **Two jobs for one export row:** the plan enqueues once per request (Step 7) and has no enqueue retry, so a row gets one enqueue call. Any second job for the row can come only from queue redelivery, which is the case above. Both pass through Step 9, and only the run that claims an attempt number writes. The other returns.
- **A failed enqueue that still queued a job:** the row is marked `failed` (Step 7), so the job returns at once in Step 9.
- **A run after the stale guard:** the guard may mark the row `failed` while a run is still going. The run notices at its next heartbeat (Step 11) or at its Step 12 update, and stops. Its file, if any, is never referenced.

### Step 18. Checks before release

Each check has a pass condition. None of these checks has been run yet, so no result exists for any of them.

1. **Time:** on a 2-million-row report with the replica and 5,000-row pages, the job finishes in under 900 s (half the 1,800-second limit). If it cannot, the design must change, for example to smaller chunked jobs. Raising the page size alone will not fix a job that is too slow. Status: not yet measured.
2. **Memory:** on a 512 MB worker, peak memory stays well below the limit.
3. **Kill test:** kill the worker during an upload. The retry produces a complete file. Before completion, no object exists at the key.
4. **Forced failure:** make the replica fail at about 50%. All three attempts run. `on_final_failure` sends the failure email, sets `failed`, and aborts the upload. The page shows "Failed", and a new click starts a fresh export.
5. **Permission:** remove `report.view` between the click and the job's run. The job fails. The download endpoint refuses.
6. **Threshold:** 10,000 rows takes the sync path. 10,001 takes the large path. A stale `row_count` produces the hard-cap behaviour in Step 5.
7. **Concurrency:** five simultaneous clicks create one row and one job.
8. **Claim:** deliver the same job twice while the first run is in progress. Only one run writes. The second returns without writing.
9. **Replica only:** a test confirms the job's database role cannot read the primary's `report_rows`.
10. **CSV round trip:** values with commas, quotes, line breaks, non-ASCII text, negative numbers and formula-like text all read back correctly.
11. **Parse again:** a job whose stored `filters` or `cols` no longer parses or names a removed column fails cleanly and reaches Step 15.
12. **Download expiry:** a download after 7 days from `completed_at` returns 410 and makes no storage call. A download just before that time returns a 302 whose link expires no later than the 7-day date.

### Step 19. Maintenance after release

- No cleanup job is built. The bucket's rules delete objects after 7 days and discard unfinished multipart uploads after 24 hours. Both rules are set up outside this plan, as `storage.py` describes.
- `report_exports` rows are kept until a retention rule is chosen (Open questions).
- Watch counts of failed exports, timeouts, attempts-to-success, and job durations, so the Step 18 time margin is confirmed in production.

## Open questions for the owner

1. **Scope of the one-at-a-time rule.** This plan scopes it to user and report, so a second click with different filters returns the running export. Confirm, or change the key to include filters and columns.
2. **Stale `row_count`.** `row_count` is rewritten only by the nightly rebuild, so a report that grows during the day can cross 10,000 unnoticed. Replica lag can also make the replica's value older than the primary's. Step 5 handles this by cutting the stream, but a user gets a failed download in that case. Is a failed download acceptable, or should the sync path check the live count first?
3. **Nightly rebuild during a long export.** The rebuild may rewrite `report_rows` while a job pages through it, which could mix two versions of the data or change `row_id` values. Options: (a) record a build version when the job starts and fail the attempt if it changes; (b) read the whole export in one snapshot on the replica, which holds a long transaction for the full run. Does the rebuild keep `row_id` values stable? Until this is answered, the plan does not guarantee a correct file when the rebuild runs during an export.
4. **Bearer link in the email.** Anyone holding the link can download the file for 24 hours, without signing in. Accept this, or send only a link to the page's download endpoint (Step 14), which checks permission?
5. **CSV details.** Add a UTF-8 byte-order mark so Excel reads non-ASCII text correctly? Use the formula-injection guard in Step 4, which alters cells that start with `=`, `+`, `-` or `@` (including negative numbers)? Should the header use the page's display labels instead of the column names from `cols`?
6. **Retention of `report_exports` rows.** How long are they kept?
7. **Stale thresholds.** Confirm the 2-hour and 45-minute values in Step 16.
8. **Queue error types.** Does the queue pass the cause (timeout, exception or worker death) in the `error` argument of `on_final_failure`? If it does, the cause can be stored in `error_code` in Step 15 instead of the single `attempts_exhausted` code.
9. **Rows API parser.** The grammar of `filters` and the parser's behaviour are not in the planning files. Steps 2 and 10 rely on that parser to name only known columns, to reject malformed input, and to bind values as parameters.
10. **Storage behaviour for signed links.** `storage.py` does not say which component checks a signed URL's signature, or what storage returns for an expired link. The plan's Step 13 email relies on the user being able to reopen the page after an expiry, but the exact view a user sees for an expired link is unknown. Also, an object deleted early (for example by hand) is not detected by Step 14, which decides 410 from the row date only. Confirm the storage behaviour, and decide whether to add an existence check.
11. **Helper error types and timeouts.** The error types and timeouts of the storage helpers and `send_email` are not documented in the planning files. Step 15 and the retry rules treat any exception as a failure. Confirm whether any of these errors should be handled differently.
12. **Email and failure texts.** The `report_export_ready` and `report_export_failed` templates are owned outside this plan. Confirm who writes them and that they state the 24-hour link and the 7-day Download behaviour.
13. **Email after permission loss.** The Step 9 `done`-without-email branch skips the permission check, so the bearer link in Step 13 can be emailed to a user who no longer has `report.view`. Should that branch re-check permission and skip the email if it fails, or is sending the email acceptable?