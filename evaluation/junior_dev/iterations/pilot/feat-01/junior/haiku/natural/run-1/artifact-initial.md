# CSV export for the reports page: implementation plan

## Terms used in this plan

- **Read replica**: a read-only copy of the database. Report rows are read only from it. Writes go to the **primary** database.
- **Keyset paging**: fetching the next page with `WHERE row_id > :last ORDER BY row_id LIMIT n`. Offset paging is never used.
- **Job queue**: `enqueue(name, payload)` runs `handler(ctx, payload)` on the worker pool. Each **attempt** runs the handler from the start. The queue keeps no progress between attempts. A job gets at most 3 attempts, with waits of 60 s and then 300 s before attempts 2 and 3. An attempt is killed after 1,800 s. Delivery is at least once, so a handler can run again for a job that already succeeded. `on_final_failure(ctx, payload, error)` runs once, after the third failed attempt.
- **Multipart upload**: object storage assembles an object from numbered parts. Nothing is visible at the object's key until `complete_multipart` succeeds. `complete_multipart` replaces any existing object at that key in one step. `abort_multipart` discards the parts.
- **Export record**: a row in a new `report_exports` table in the primary database. It holds export state (status, file location, timestamps). It is not view state. Filters and column order still live only in the page URL.

## Decisions this plan makes where the brief is silent

1. The path threshold uses `reports.row_count` (the unfiltered total), as the brief says. A filter that matches 3 rows on a 2-million-row report still takes the job path.
2. "One large export of a given report at a time" is scoped to **user and report**. A second click with different filters returns the export already running, and the page shows that export's own filters so the user is not misled.
3. Each attempt writes its file to a key that includes the job's `job_id`, so two runs never overwrite each other's file while someone is downloading it.
4. The download link in the email is a bearer link. Anyone who holds it can download for 24 hours. This is listed under Open questions.

## Plan

### Step 1. The page sends the export request

- **Starts:** the user clicks **Download CSV** on `/reports/{report_id}`.
- **Data:** the page reads the current URL's query string (for example `?status=open&region=EU&cols=date,customer,amount`) and sends `filters` and `cols` unchanged in a request to `POST /api/reports/{report_id}/exports` with a JSON body `{"filters": "...", "cols": "..."}`. The server uses the same parsing rules as the rows API.
- **State:** none.
- **On failure:** a network error or a 5xx response makes the page show "Export could not start. Try again." No record is created.

### Step 2. The API checks permission and validates the input

- **Starts:** the request from Step 1 arrives.
- **Checks, in order:**
  1. The caller must have `report.view` on the report's workspace. Otherwise return **403**.
  2. `filters` and `cols` are parsed by the rows API's parser. An unknown column or a malformed filter returns **400**.
  3. If the combined `filters` and `cols` text is longer than 8 KB, return **400**. The export record and job payload must stay small.
- **Data moved:** none.
- **State:** none.
- **On failure:** 403 or 400 is returned at once. Nothing is stored.

### Step 3. Choose the path by row count

- **Starts:** a validated request.
- **Data:** one read of `reports.row_count` for the report, from the **read replica**. `row_count` is report metadata, not report rows, but the plan reads it from the replica too, so no report data comes from the primary.
- **Rule:**
  - `row_count` is 10,000 or less: go to Step 5 (sync path).
  - `row_count` is more than 10,000: go to Step 6 (large path).
- **State:** none.
- **On failure:** report not found returns **404**. Replica unreachable returns **503**. Do **not** fall back to the primary.

### Step 4. One CSV writer, shared by both paths

- **Starts:** called by Step 5 for each page, and by Step 10 for each page in the job. Using one writer means both paths produce identical files.
- **Input:** the column list in `cols` order, and a stream of rows (strings).
- **Output:** CSV bytes.
  - The first line is a header row with the column labels in `cols` order.
  - Lines end with CRLF.
  - A cell is wrapped in double quotes if it contains a comma, a double quote, CR or LF. Double quotes inside a cell are doubled, as RFC 4180 requires.
  - Text is UTF-8.
  - A cell that starts with `=`, `+`, `-` or `@` gets a leading apostrophe (formula-injection guard; see Open questions).
- **Data:** rows go in, bytes come out. The writer holds no rows between calls.
- **State:** none.
- **On failure:** an encoding error raises. The caller treats it as a failed request (sync path) or a failed attempt (job).

### Step 5. Sync path (row_count of 10,000 or less)

- **Starts:** Step 3 chose the sync path.
- **Data:** keyset pages of 500 rows from the replica:
  `SELECT row_id, <cols> FROM report_rows WHERE report_id = :id AND <filters> AND row_id > :after ORDER BY row_id LIMIT 500`
  Each page goes through the Step 4 writer. The bytes are streamed to the browser as the response, with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}-{YYYY-MM-DD}.csv"`.
- **Memory:** one page at a time. The file is streamed, never built whole.
- **State:** nothing is stored. There is no export record and no file.
- **Time limit:** API servers kill any request after 60 s. At 500 rows a page, 10,000 rows is about 20 queries, which should finish well inside the limit. Step 18 checks this.
- **Hard cap:** if more than 10,000 rows come back (possible when `row_count` is stale), stop writing and close the connection without the final chunk. The browser then reports a failed download rather than saving a silently short file. Log the event.
- **Page handling:** the page saves a `text/csv` response as a file. If the response is JSON, the page treats it as a large export and shows the status panel (Step 8).
- **On failure:** a database error, timeout or cap hit ends the stream early, and the browser shows a failed download. Nothing was stored, so the user simply clicks again.

### Step 6. Create the export record (large path)

- **Starts:** Step 3 chose the large path.
- **Stale check first:** if the user already has an active export of this report whose `updated_at` is older than the stale limit (Step 16), set that row to `failed` with `error_code = 'stale'`.
- **Data:** insert one row into `report_exports` in the **primary** database:
  `id` (new UUID), `user_id`, `workspace_id`, `report_id`, `filters`, `cols`, `status = 'queued'`, `attempt = 0`, `created_at`, `updated_at`.
- **Duplicate guard:** a partial unique index on `(user_id, report_id) WHERE status IN ('queued', 'running')` makes the insert "insert or do nothing". If nothing was inserted, read the existing active row and return it. The response is **202** with that row's state, and the page shows that export's filters.
- **State:** the primary database row holds export state only.
- **On failure:** a database write error returns **500**. Nothing is queued, so the user can click again.

### Step 7. Queue the job

- **Starts:** Step 6 inserted the row.
- **Data:** `enqueue("report_csv_export", {"export_id": "<uuid>"})`. The payload is only the ID, far under the 64 KB limit. The job reads `filters` and `cols` from the row. The returned `job_id` is saved on the row.
- **State:** the queue holds the job. The row holds `job_id`.
- **Response:** **202** with `{"export_id", "status": "queued", "filters", "cols"}`.
- **On failure:** if `enqueue` raises or times out, update the row in the same request to `status = 'failed'`, `error_code = 'enqueue_failed'`, and return **503** with a message. Without this, a row that no worker will ever run would block the user's next click.

### Step 8. The page shows the export's state

- **Starts:** page load (this covers a user who comes back later), and the response to Step 7 or Step 6.
- **Data:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export for that report: `id`, `status`, `attempt`, `rows_written`, `filters`, `cols`, `created_at`, `completed_at`, and `download_available`. It returns only rows owned by the caller.
- **Behaviour:** while the status is `queued` or `running`, the page polls every 5 s. It stops polling at `done` or `failed`. The status panel shows "Queued", "Running (attempt N of 3)", "Ready to download", or "Failed, start again".
- **State:** the page holds only what it displays.
- **On failure:** a failed poll keeps the last state shown and retries after 15 s. Nothing is cancelled.

### Step 9. Each attempt starts: claim the export

- **Starts:** the queue runs the handler for attempt 1, 2 or 3. `ctx.attempt` says which.
- **Load:** read the row for `payload.export_id` from the primary.
  - Row missing: log and return. There is nothing to do.
  - `status = 'done'` and `email_sent_at` is empty: go to Step 13 only. The file already exists, so the export is not rebuilt.
  - `status = 'done'` and `email_sent_at` is set: return.
  - `status = 'failed'`: return. The stale guard already closed it.
- **Permission:** check that `user_id` still has `report.view` on the workspace. If not, raise. The attempt counts as failed.
- **Claim:** `UPDATE report_exports SET status = 'running', attempt = :ctx.attempt, updated_at = now() WHERE id = :id AND status IN ('queued', 'running')`.
- **Clean up an earlier attempt:** if `upload_id` is set on the row, call `abort_multipart(upload_id)` and clear the field. Ignore errors from this call, because a completed upload cannot be aborted.
- **State:** the primary row.
- **On failure:** a database error or a permission failure raises. The queue then retries, and after the third failure Step 15 applies.

### Step 10. Stream rows from the replica into the writer

- **Starts:** Step 9 succeeded.
- **Data:** keyset pages of **5,000** rows from the replica (larger than the API's 500, to cut round trips; Step 18 confirms the size):
  `SELECT row_id, <cols> FROM report_rows WHERE report_id = :id AND <filters> AND row_id > :after ORDER BY row_id LIMIT 5000`
  Each page goes through the Step 4 writer, and the bytes are appended to a part buffer.
- **Replica only:** the job's database role has no grant on the primary's `report_rows`. An accidental primary read fails instead of succeeding.
- **Memory:** one page (about 2 to 3 MB) plus one part buffer (16 MB). The whole report is never held. The peak is well under the 512 MB worker limit.
- **Scale:** 2 million rows at 5,000 a page is about 400 queries.
- **State:** nothing is stored in this step beyond the heartbeat in Step 11.
- **On failure:** a replica error or timeout raises. The queue retries from row 0, because it keeps no progress. The previous upload is aborted in Step 9.

### Step 11. Upload the file in parts

- **Starts:** the part buffer reaches 16 MB, or the last page has been written.
- **Setup (first buffer in an attempt):** the key is `exports/{export_id}/{job_id}.csv`. Call `start_multipart(exports, key)` to get an `upload_id`. Save `upload_id` on the row right away, so a later attempt or the final failure can abort it.
- **Each full buffer:** call `upload_part(upload_id, part_number, bytes)`, with part numbers counting from 1. Keep the returned etags in memory. For the largest report that is about 60 entries. After each part, update `rows_written` and `updated_at` on the row. This is the heartbeat that Step 16 relies on.
- **Limits:** 16 MB parts satisfy the 5 MB minimum. The last part may be smaller. The 10,000-part maximum is far above the roughly 60 parts needed for a 900 MB file.
- **Visibility:** nothing is visible at the key yet.
- **State:** `upload_id` and `rows_written` on the row. The parts sit in storage, invisible.
- **On failure:** an `upload_part` error raises, and the queue retries. The next attempt aborts the stored `upload_id` (Step 9). If the worker dies, the parts stay invisible, and the bucket's 24-hour rule discards an upload that is never completed.

### Step 12. Complete the file and mark it done

- **Starts:** the last part is uploaded.
- **Data:** call `complete_multipart(upload_id, etags)`. The object becomes visible at its key. The key replaces any object already there, in one step, so a reader sees either the old file or the new one, never a partial file.
- **Then:** `UPDATE report_exports SET status = 'done', file_key = :key, rows_written = :n, upload_id = NULL, completed_at = now(), updated_at = now() WHERE id = :id AND status = 'running'`.
- **State:** the row.
- **On failure:**
  - If `complete_multipart` fails, nothing is visible. Raise, and the retry rebuilds the file.
  - If the complete call succeeds but the row update fails, raise. The retry rebuilds the file and completes it to the same key. This costs time but is safe.

### Step 13. Email the download link

- **Starts:** the row is `done` and `email_sent_at` is empty.
- **Data:** `url = signed_url(exports, file_key, 86400)`. Then `send_email(user_id, "report_export_ready", {report_id, download_url: url, expires_at})`. The link works for 24 hours from the moment it is signed here.
- **After a successful send:** `UPDATE report_exports SET email_sent_at = now() WHERE id = :id`.
- **State:** the row (`email_sent_at`). The email provider holds the message.
- **On failure:** if `send_email` raises, the attempt raises and the queue retries. The next attempt takes the "done, email not sent" branch in Step 9 and sends again without rebuilding the file. If every attempt fails here, Step 15 does not change a `done` export to `failed`. The page then shows "Ready to download", but the user gets no email.

### Step 14. Download from the page

- **Starts:** the user clicks **Download** on a `done` export.
- **Data:** `GET /api/exports/{export_id}/download` checks that the caller owns the row (`user_id`) and still has `report.view`. It checks that `status = 'done'`. It then returns a **302** redirect to a fresh `signed_url(exports, file_key, 86400)`. The URL is generated on each click and is never stored.
- **Expiry:** the bucket deletes each object 7 days after it was written. The page shows "Available until {completed_at + 7 days}" and hides the button after that.
- **State:** none written.
- **On failure:** not the owner, or permission lost: **403** or **404**. Object already deleted: **410**, and the page shows "This export has expired. Start a new one."

### Step 15. Final failure

- **Starts:** the third attempt has failed by exception, by the 1,800-second timeout, or because its worker died. The queue calls `on_final_failure(ctx, payload, error)` once.
- **Logic:**
  1. Load the row.
  2. If `status = 'done'`, do not change it. The file is fine and only the email failed. Log the error.
  3. Otherwise `UPDATE` the row to `status = 'failed'`, with `error_code` (`timeout`, `exception`, or `attempts_exhausted` for worker death), `completed_at` and `updated_at`.
  4. If `upload_id` is set, call `abort_multipart(upload_id)` and ignore any error.
  5. Call `send_email(user_id, "report_export_failed", {report_id})`. Log any error from the send and do not raise it.
- **Effect:** the export no longer counts as active, so the user can start a new one. The page shows "Failed" with a **Try again** action, which sends a new Step 1 request.
- **On failure of this handler itself** (for example, the database is down): log it. The row stays `queued` or `running` until the stale guard in Step 16 recovers it.

### Step 16. Stale-row guard

- **Starts:** a user clicks again (Step 6) while their one active row is old.
- **Rule:** an active row is treated as stale, and set to `failed` with `error_code = 'stale'`, when:
  - it is `queued` and has not been updated for more than 2 hours, or
  - it is `running` and has not been updated for more than 45 minutes.
- **Why these numbers:** a running attempt updates its row after every part. The longest silence is the backoff between attempts, at most 5 minutes. The longest full run of three attempts is about 96 minutes (3 × 30 min, plus 60 s and 300 s). A queued job can wait longer if the worker pool is saturated. If a stale row's job runs later, Step 9 sees `failed` and returns. Both thresholds are assumptions for the owner to confirm.
- **State:** the row.

### Step 17. Concurrency and duplicate delivery

- **Two clicks at once:** the partial unique index lets one insert win. The other request reads the winning row (Step 6).
- **Duplicate delivery:** two runs of one job both pass the conditional claim in Step 9. Each writes its own file, because each key includes `job_id`, so neither overwrites a file being downloaded. The last completion sets `file_key`. The email is sent once in practice, because `email_sent_at` is checked. A rare race can send it twice, which is acceptable.
- **Two different jobs for one export:** only one row is kept active, so the second job finds a finished or failed row and returns, or both files are written and only one is recorded. Any unrecorded file is removed by the 7-day lifecycle rule.

### Step 18. Checks before release

Each check has a pass condition.

1. **Time:** on a 2-million-row report with the replica and 5,000-row pages, the job finishes in under 900 s (half the 1,800-second limit). If it cannot, the design must change, for example to smaller chunked jobs. Raising the page size alone will not fix a job that is too slow.
2. **Memory:** on a 512 MB worker, peak memory stays well below the limit.
3. **Kill test:** kill the worker during an upload. The retry produces a complete file. Before completion, no object exists at the key.
4. **Forced failure:** make the replica fail at about 50%. All three attempts run. `on_final_failure` sends the failure email, sets `failed`, and aborts the upload. The page shows "Failed", and a new click starts a fresh export.
5. **Permission:** remove `report.view` between the click and the job's run. The job fails. The download endpoint refuses.
6. **Threshold:** 10,000 rows takes the sync path. 10,001 takes the large path. A stale `row_count` produces the hard-cap behaviour in Step 5.
7. **Concurrency:** five simultaneous clicks create one row and one job.
8. **Replica only:** a test confirms the job's database role cannot read the primary's `report_rows`.
9. **CSV round trip:** values with commas, quotes, line breaks, non-ASCII text and formula-like text all read back correctly.

### Step 19. Maintenance after release

- No cleanup job is built. The bucket's rules delete objects after 7 days and discard unfinished multipart uploads after 24 hours.
- `report_exports` rows are kept until a retention rule is chosen (Open questions).
- Watch counts of failed exports, timeouts, attempts-to-success, and job durations, so the Step 18 time margin is confirmed in production.

## Open questions for the owner

1. **Scope of the one-at-a-time rule.** This plan scopes it to user and report, so a second click with different filters returns the running export. Confirm, or change the key to include filters and columns.
2. **Stale `row_count`.** `row_count` is rewritten only by the nightly rebuild, so a report that grows during the day can cross 10,000 unnoticed. Step 5 handles this by cutting the stream, but a user gets a failed download in that case. Is a failed download acceptable, or should the sync path check the live count first?
3. **Nightly rebuild during a long export.** The rebuild may rewrite `report_rows` while a job pages through it, which could mix two versions of the data or change `row_id` values. Options: (a) record a build version when the job starts and fail the attempt if it changes; (b) read the whole export in one snapshot on the replica, which holds a long transaction for the full run. Does the rebuild keep `row_id` values stable?
4. **Bearer link in the email.** Anyone holding the link can download the file for 24 hours, without signing in. Accept this, or send only a link to the page's download endpoint (Step 14), which checks permission?
5. **CSV details.** Add a UTF-8 byte-order mark so Excel reads non-ASCII text correctly? Use the formula-injection guard in Step 4, which alters cells that start with `=`, `+`, `-` or `@`? Use the page's column labels for the header row?
6. **Retention of `report_exports` rows.** How long are they kept?
7. **Stale thresholds.** Confirm the 2-hour and 45-minute values in Step 16.