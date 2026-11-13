# CSV export for the reports page: implementation plan

## Overview

The Download CSV button writes the report's current view (URL filters, URL column order, and a header row) to a file. Small reports (`reports.row_count` of 10,000 or fewer) are answered inline in the response. Larger reports are built by a background job that streams rows into object storage and then emails a 24-hour download link. The page shows the state of the latest export at all times.

Terms used below:

- **Read replica**: a read-only copy of the database. Report rows are read only from it. The export state table lives on the primary database because it holds export state, not report data.
- **Keyset paging**: fetching rows with `row_id > last_seen ORDER BY row_id LIMIT n`. OFFSET is never used.
- **Multipart upload**: object storage receives a file as numbered parts. Nothing is visible at the key until the upload is completed. Aborting discards the parts.
- **Compare-and-set (CAS)**: an update that applies only if the row is still in an expected state, for example `UPDATE report_exports SET state = 'done' WHERE export_id = ? AND state = 'running'`. It reports whether it applied. CAS makes retries and duplicate deliveries safe.
- **Attempt**: one run of the job handler. The queue allows 3 attempts and each starts from zero.

## Step 0. Gate: measure replica throughput before building

- **Starts**: a developer, before the job is built.
- **Work**: time keyset reads of 5,000 rows at a time from the replica for the largest report (about 2 million rows), writing them to CSV in bounded chunks. Run from the same network position as a worker.
- **Requirement**: 2 million rows must finish well inside the 1,800-second attempt timeout. That needs at least about 1,100 rows per second. Target at least 2,200 rows per second so one slow stretch does not fail the export.
- **Data and state**: read-only queries; no state. Record the result in the ticket.
- **If it fails**: do not build the job as written. Options are a query or index change on `report_rows` (needs its own review), or splitting the export into several jobs. Splitting is not a small add-on: the storage helpers cannot join objects, and every part except the last must be at least 5 MB, so independent range writers need a second design pass.

## Step 1. Receive the click and check access

- **Starts**: the user clicks Download CSV. The browser sends `POST /api/reports/{report_id}/exports` with the filters and cols strings taken from the page URL.
- **Work**:
  1. Check the `report.view` permission on the report's workspace. Return 403 if it is missing.
  2. Parse filters and cols with the same parser the rows API uses. Reject any column name that is not a column of the report (400). Cap the total input length (for example 4 KB).
  3. Read `reports.row_count` from the read replica.
- **Data moves**: the request in, one integer read.
- **State**: none yet.
- **Failure**: 403 for no access, 400 for bad input, 503 if the replica is unreachable. Nothing has started, so the user can click again.

## Step 2. Choose the path by size

- **Rule**: `row_count` of 10,000 or fewer takes the inline path (step 4). Anything larger takes the large path (steps 5 to 11).
- **Consequence**: the rule uses the unfiltered total, as the brief fixes. A filtered view that returns 40 rows from a 2-million-row report still takes the large path. The page copy should say so.
- **State and failure**: none beyond step 1.

## Step 3. Shared row reader and CSV writer

This is a building block, not something a user triggers. Both paths call it, so their output is identical.

- **Reader**: keyset pages from the read replica, with the same filter logic and column selection as the rows API. Page size is a parameter (500 for the page API, 5,000 for the job).
- **Writer**: the first line is the header row of the chosen columns in the chosen order. Fields are encoded with standard CSV rules: quote any field containing a comma, quote, or line break, double the inner quotes, use UTF-8 and `\r\n` line endings. Output is a byte stream to a sink. The writer never holds more than the current page.
- **Failure**: an exception propagates to the caller. The inline path returns an error. The job attempt fails (step 9).
- **Decision needed**: whether to neutralise cells that start with `=`, `+`, `-` or `@` to block spreadsheet formula injection. Decide before the build.

## Step 4. Inline path (10,000 rows or fewer)

- **Starts**: step 2 chose inline.
- **Work**: the response body is the CSV. Headers: `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename=...`. The step 3 writer streams into the response. Nothing is written to storage or to the database.
- **Time limit**: API servers kill any request that runs past 60 seconds. Ten thousand rows is about 20 page reads. Measure this path in step 0 terms. If the p95 approaches 60 seconds, lower the threshold.
- **Truncation risk**: a kill mid-stream leaves a partial body. The client must fetch the response as a blob and save it only when the fetch completes without a network error. A plain link would save the partial file.
- **Failure**: an error before the first byte returns an error response. An error mid-stream produces no saved file, as above. Nothing needs cleanup.

## Step 5. Large path: record the export and allow one at a time

- **Starts**: step 2 chose large.
- **Data**: one new row in a table `report_exports` on the primary database. Columns: `export_id` (random UUID), `user_id`, `report_id`, `filters`, `cols`, `state`, `attempt`, `job_id`, `upload_id`, `object_key`, `rows_written`, `error_summary`, `created_at`, `attempt_started_at`, `completed_at`, `email_sent_at`.
- **Rule**: a partial unique index on `(user_id, report_id)` where `state` is `queued` or `running`. Insert the row with `state = queued`.
  - If the insert succeeds, go to step 6.
  - If the unique index rejects the insert, read the active row and return it (HTTP 200, step 7) rather than starting another. The page shows that export's filters so the user can see they differ from the click. This follows the brief literally; see open question 1.
- **Failure**: a database error returns 503. No job starts.

## Step 6. Enqueue the job

- **Starts**: step 5 inserted the row.
- **Work**: call `enqueue('report_export', {'export_id': ...})`. The payload holds only the id, far below the 64 KB limit. The row stays the single source for the filters. Save the returned `job_id` on the row.
- **Failure**:
  - If `enqueue` raises, CAS the row from `queued` to `failed` with `error_summary = could not start`, and return 503. The user can click again.
  - If the process dies after the insert and before the enqueue, the row stays `queued` with no `job_id`. Step 15 clears it.

## Step 7. Respond and let the page track it

- **Response**: 202 with JSON `{export_id, state, filters, cols, created_at}`. Or 200 with the existing active export when step 5 found one.
- **Next**: the page starts polling (step 12). Nothing is stored in the browser.

## Step 8. Attempt starts: claim the export and clean up the last attempt

- **Starts**: the queue runs handler `report_export` with `ctx.job_id`, `ctx.attempt` (1, 2 or 3) and the payload `export_id`.
- **Work**:
  1. Load the row. If it does not exist, return.
  2. If `state` is `done` or `failed`, return. Delivery is at least once, so a re-run after success must do nothing.
  3. Claim with CAS: set `state = running`, `attempt = ctx.attempt`, `attempt_started_at = now`, from `queued` or `running`. If the CAS does not apply, return.
  4. If `upload_id` is set from an earlier attempt, call `abort_multipart` on it and clear the field. Ignore "already gone" errors.
  5. Re-check `report.view` for the owner. If access is gone, CAS to `failed` with `error_summary = access removed`, send the failure email (step 14), and return normally. Returning normally stops retries, which would not help.
  6. Call `start_multipart` on bucket `exports` with key `report-exports/{report_id}/{export_id}.csv`. Save the returned `upload_id` on the row before reading any rows. A later attempt can then always find and abort this upload.
- **Failure**: an error in steps 1 to 3 fails the attempt, and the queue retries after 60 seconds, then 300 seconds. If the process dies between steps 6a and 6b, an upload is left open. The bucket rule discards it after 24 hours, which is accepted.

## Step 9. Stream rows into the upload

- **Starts**: step 8, part 6.
- **Work**:
  - Read with the step 3 reader, page size 5,000, keyset on `row_id`, from the replica.
  - The writer buffers bytes. When the buffer reaches 16 MB, send it with `upload_part` (part numbers start at 1) and keep the returned etag. Then clear the buffer.
  - The final buffer can be under 5 MB. It is allowed because it is the last part.
  - Memory: one 16 MB buffer plus one page of rows. A 2-million-row report is about 900 MB of CSV, so about 60 parts. That is far below the 10,000-part limit and well inside the 512 MB worker memory. The job never writes a local file.
  - Retry each `upload_part` up to 3 times inside the attempt before the attempt fails.
  - Every 10 parts, update `rows_written` on the row. The page can show progress, and an operator can see how far a timed-out attempt got.
- **Data moves**: rows from the replica into worker memory, then into object storage.
- **State**: `upload_id` and `rows_written` on the row. The list of etags is held in memory only.
- **Failure**: any unrecovered error fails the attempt. The queue retries from step 8, and the new attempt aborts this upload first. If an attempt reaches the 1,800-second timeout, the worker is stopped and the attempt counts as failed. The next attempt starts again from the first row. If all 3 attempts time out, the export fails (step 14). The step 0 gate exists to prevent this.

## Step 10. Publish the file

- **Starts**: step 9 has written every row.
- **Work**:
  1. Call `complete_multipart(upload_id, etags)`. This makes the object visible at its key in one step, replacing any object already there from an earlier run.
  2. Only after step 1 succeeds, CAS `state` from `running` to `done`, and set `completed_at`, `object_key` and `rows_written`.
- **Why this order**: the page shows `done` only once the complete file exists. If the process dies between steps 1 and 2, the next attempt rebuilds the file and replaces it. The result is correct, just repeated work.
- **Failure**: if `complete_multipart` fails, the attempt fails and the upload stays open for the retry. If the CAS does not apply because the state is already `done`, an earlier attempt finished. Do nothing more and do not email again.

## Step 11. Email the download link

- **Starts**: the step 10 CAS applied in this attempt. Only the attempt that made the transition sends the email.
- **Work**: `url = signed_url('exports', key, 86400)`. Call `send_email(user_id, 'report_export_ready', {report_name, download_url, expires_at})`. On success, set `email_sent_at`.
- **Failure**: if `send_email` raises, log it and leave the state `done`. The page still shows the download. Nothing re-sends automatically (open question 5). Do not re-run the export to fix an email.
- **Caveat**: the emailed link is a bearer link. It keeps working for 24 hours after it is sent, even if the user loses report access in the meantime.
- **Dependency**: the template `report_export_ready` must exist in the email system.

## Step 12. Page shows the export state

- **Starts**: page load, then polling while the export is `queued` or `running`.
- **Work**:
  - The page calls `GET /api/reports/{report_id}/exports/latest`. The server checks `report.view` and returns the most recent export by this user for this report: state, attempt, rows_written, filters, completed_at, error_summary. It returns none if there is none.
  - Banner states:
    - `queued`: waiting to start.
    - `running`: attempt N of 3, with rows written so far against about `row_count`.
    - `done`: a Download button (step 13).
    - `failed`: the error summary and a Start again button that repeats step 1.
    - `expired`: derived when `done` and `completed_at` is more than 7 days ago. The bucket rule has deleted the file. No cleanup job is needed.
  - Poll every 5 seconds while `queued` or `running`, and stop at a terminal state. Re-fetch when the tab regains focus.
  - Returning later shows the latest export in whatever state it is. A new click replaces the displayed export.
- **Data moves**: small JSON responses.
- **State**: none in the browser that must survive reloads. The server holds everything.
- **Failure**: if the status fetch fails, show "status unavailable, retrying" and keep the last state on screen. The export keeps running on the server regardless.

## Step 13. Download a finished export

- **Starts**: the user clicks Download on a `done` export.
- **Work**: `GET /api/exports/{export_id}/download`. The server checks that the caller is the owner, still has `report.view`, and that the state is `done`. It then returns a 302 to a fresh `signed_url` with `ttl = 900` seconds, since the click is immediate.
- **Failure**: 403 for a non-owner or no access, 409 if not `done`, 410 if the object is gone (the page shows `expired`).

## Step 14. Final failure handler

- **Starts**: the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.
- **Work**:
  1. Load the row. If `state` is `done`, do nothing.
  2. CAS `state` from `queued` or `running` to `failed`. Set `error_summary` to a short phrase such as `timed out on attempt 3` or the error class. Do not store stack traces or SQL.
  3. If `upload_id` is set, call `abort_multipart`. Ignore failures here, since the bucket rule covers leftovers.
  4. Call `send_email(user_id, 'report_export_failed', {report_name, page_url, error_summary})`.
- **Failure**: if this handler itself errors, the state stays `running`. Step 15 turns it into `failed` later. In that case the user gets no email (open question 5).

## Step 15. Stale-state rule (read time, not a cleanup job)

- **Starts**: any click (step 1, or the conflict path in step 5) and any status read (step 12).
- **Rule**: a `queued` or `running` row older than 2 hours is treated as `failed`, with `error_summary = stalled`. The queue can use at most 3 × 1,800 s plus 60 s and 300 s of backoff, which is 5,760 s (96 minutes). Two hours therefore cannot cut off a live export.
- **Work**: CAS to `failed`. No email is sent by this rule. The page shows the failure.
- **Purpose**: stops an export that never started, or whose final-failure handler died, from blocking new exports for that report forever. Nothing is deleted.

## Step 16. Verification before release

- **Unit tests**: CSV escaping, column order, and rejection of unknown columns.
- **Equivalence test**: for a fixture report, the inline output and the job output are byte-identical for the same filters and cols.
- **Failure injection**: kill the worker during step 9 and during step 10. Confirm no object appears at the key before `complete_multipart`, and that the next attempt aborts the old upload.
- **Duplicate delivery**: run the handler twice after `done`. Confirm one file and one email.
- **Concurrency**: two simultaneous clicks produce one row (partial unique index).
- **Memory**: peak worker memory during the 2-million-row run stays well below 512 MB.
- **Permission**: remove `report.view` mid-export. Confirm the job fails without retries and the owner gets the failure email.
- **Throughput**: repeat step 0 on a real worker against the full 2-million-row report.

## Open questions for the owner

1. **Same report, different filters.** The plan returns the running export, as the brief says. The alternative is to refuse the click with a message. Recommendation: keep the brief's behaviour and show the running export's filters on the page. Needs a decision.
2. **Throughput gate (step 0).** If the gate fails, the fix needs a second design pass before any build.
3. **Nightly rebuild during an export.** Rows can change between pages, so the file may mix two report versions or miss rows. Check whether the rebuild is atomic and whether the replica can give a stable snapshot. One option: record a rebuild marker at claim time and fail the attempt if it changes.
4. **Threshold on unfiltered count.** Small filtered views go through the job. Accept this, or add a filtered count.
5. **Email delivery.** A failed send is not retried, and an export that fails without its final-failure handler sends no email. Accept, or add a retry for emails only.
6. **Formula injection.** Decide on neutralising cells that start with `=`, `+`, `-` or `@` (step 3).
7. **Email templates.** `report_export_ready` and `report_export_failed` must exist. Confirm who owns the template system.
8. **Inline timing.** Confirm the inline path stays well under the 60-second API limit at 10,000 rows (step 4).
9. **Bucket access.** Confirm the `exports` bucket is private, so signed URLs are the only access path.