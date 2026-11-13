# CSV export for the reports page: implementation plan

## What this is

The reports page shows one report as a table, 500 rows at a time. Its filters and column order live only in the page address, so the server keeps no record of what a user is viewing.

This plan adds a **Download CSV** button. The file holds the rows the user sees, in the column order they see, with a header row. The export takes one of two paths, chosen by the report's total row count:

- **10,000 rows or fewer:** the server builds the CSV and returns it in the response to the click. Nothing is stored.
- **More than 10,000 rows:** the click records an export and returns at once. A background job writes the CSV to object storage in parts. When the file is complete, the job emails the user a download link that works for 24 hours. The page shows the export's progress until it ends.

The split exists because a small file fits in one web response within the server's 60-second limit, and a large one does not.

Out of scope: scheduled exports, formats other than CSV, changes to the table on the page, and any cleanup job for old files.

## Terms

- **Page view:** the filters and column order in the page address, for example `?status=open&region=EU&cols=date,customer,amount`. The export uses these same strings.
- **report.view:** the permission to see a report in its workspace. The server checks it on every request.
- **row_id:** a number on each report row. It is unique and increases within its report.
- **row_count:** the stored total number of rows in a report, before any filter. It is rebuilt each night.
- **Read replica:** a read-only copy of the database. Report rows are read only from it, never from the primary database.
- **Primary database:** the main database. Export records are kept here.
- **Keyset paging:** reading rows in `row_id` order and asking for the rows after the last one seen. The plan never uses OFFSET, so every page is equally fast.
- **Reader:** returns report rows in pages from the replica. It applies the export's filters and columns with the same logic as the rows API. The job reads 5,000 rows per page.
- **Writer:** turns rows into CSV bytes. It writes a header row, then one line per row, in the chosen columns and order. A field with a comma, a quote or a line break is wrapped in quotes, and quotes inside it are doubled. Output is UTF-8 with `\r\n` line endings. It passes bytes on as it goes, so it holds at most one page of rows.
- **Job queue:** the existing background system. `enqueue(name, payload)` adds a job and returns a `job_id`. A worker process runs the job's handler. Each worker has 512 MB of memory and runs one attempt at a time.
- **Attempt:** one run of a job handler. The queue numbers attempts 1, 2 and 3 (`ctx.attempt`). It retries a failed attempt by itself, waiting 60 seconds before attempt 2 and 300 seconds before attempt 3. Each attempt starts from the beginning. An attempt still running after 30 minutes is killed and counts as failed.
- **Final-failure handler:** a function the queue calls once, after the third attempt has failed.
- **At-least-once delivery:** the queue can run a handler again even after it has succeeded. Handlers must tolerate a repeat.
- **Multipart upload:** object storage receives one file as numbered parts. Nothing is visible at the file's key until the upload is completed. Aborting the upload discards the parts.
- **exports bucket:** the private object-storage bucket for export files. Its rule deletes each file 7 days after it was written. It also discards multipart uploads not completed within 24 hours.
- **Signed URL:** a download link that works for a set time.
- **Export record:** one row in the `report_exports` table on the primary database. It holds the export's state. Its columns are `export_id` (random UUID), `user_id`, `report_id`, `filters`, `cols`, `state` (queued, running, done or failed), `attempt`, `attempt_started_at`, `job_id`, `upload_id`, `object_key`, `rows_written`, `error_summary`, `created_at`, `completed_at` and `email_sent_at`.
- **Compare-and-set (CAS):** an update that changes the row only if the row still holds the values we expect. It reports whether it applied. Every state change in this plan is a CAS, so two writers cannot both win.
- **Stale export:** an export whose state has not moved for too long. It is marked failed on read, not by a cleanup job. See the stale check below.

## How it runs

### Part A: the click

1. **Receive the click and check access.** The user clicks Download CSV. The browser sends `POST /api/reports/{report_id}/exports` with the page view's filters and cols.
   - The server checks report.view on the report's workspace. Without it, the server returns 403.
   - It parses filters and cols with the rows API's parser. A column name that is not a column of the report returns 400. Input is capped at 4 KB.
   - It reads row_count from the replica.
   - It stores nothing. If the replica is unreachable, it returns 503. Nothing has started, so the user can click again.

2. **Choose the path by size.** If row_count is 10,000 or fewer, go to step 3. Otherwise go to step 4.
   - The count is unfiltered. A filtered view of 40 rows from a 2-million-row report still takes the large path. The page says so beside the button.

3. **Inline path.** The response body is the CSV from the Writer. The headers are `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename=...`.
   - Rows come from the replica and stream to the browser. Nothing is stored.
   - The request must finish within 60 seconds. Ten thousand rows is about 20 page reads. The throughput gate checks this.
   - If the connection drops partway, the browser must not save the partial file. So the button fetches the response as a blob and saves it only when the fetch finishes without a network error. A plain download link would save a partial file.

4. **Large path: record the export.**
   - First, run the stale check on this user's export for this report, if there is one. A stalled export is marked failed here, so it cannot block the new click.
   - Insert one export record with state `queued`. A partial unique index on (user_id, report_id), covering only rows in state `queued` or `running`, allows one active export per user and report.
   - If the insert succeeds, go to step 5.
   - If the index rejects the insert, read the active export. If it is stale, mark it failed and try the insert once more. If it is not stale, return it with HTTP 200. The page then shows the notice in Part C, and the new click starts nothing.
   - If the database fails, return 503. No job starts.

### Part B: the background job

5. **Enqueue the job.** This starts when step 4 inserts the row.
   - It calls `enqueue('report_export', {'export_id': ...})`. The payload holds only the ID. The job reads the filters and columns from the export record.
   - It saves the returned `job_id` on the row.
   - It returns 202 with `export_id`, `state`, `filters`, `cols` and `created_at`. On the conflict path it returns 200 with the active export.
   - If `enqueue` raises, it sets the row to `failed` with `error_summary` "could not start" and returns 503. The user can click again.
   - If the process dies after the insert and before `enqueue`, the row stays `queued` with no `job_id`. The stale check clears it after 2 hours.

6. **Claim the export.** The queue runs an attempt of the `report_export` handler. The handler gets the job ID, the attempt number and the `export_id`. Each attempt claims the row before doing any work, so a repeat cannot run the export twice at once.
   - Load the row. If it does not exist, return.
   - If `state` is `done` or `failed`, return. A repeat after success does nothing.
   - Claim with CAS: set `state` to `running`, `attempt` to this attempt's number and `attempt_started_at` to now. The CAS applies only if `state` is `queued`, or if `state` is `running` and the stored `attempt` is lower than this attempt's number. A duplicate of the same attempt, or an older one, matches nothing, so the handler returns.
   - If `upload_id` is set from an earlier attempt, abort that upload and clear the field. Ignore "already gone" errors.
   - Check report.view for the owner again. If access is gone, set the row to `failed` with `error_summary` "access removed", send the failure email (step 13), and return normally. Returning normally stops the retries, because a retry cannot restore access.
   - Start a multipart upload on the exports bucket with key `report-exports/{report_id}/{export_id}-attempt{N}.csv`, where N is this attempt's number. Each attempt writes its own key, so two attempts never write the same object. Save the `upload_id` on the row before reading any rows.
   - An error before the upload starts fails the attempt, and the queue retries.
   - One window cannot be closed. If the process dies between starting the upload and saving its ID, no later attempt can find the upload to abort it. The bucket rule discards it after 24 hours. This is accepted.

7. **Write the rows.** This starts after step 6 saves the `upload_id`.
   - The Reader reads 5,000 rows per page from the replica. It uses the filters and columns on the export record, not the page.
   - The Writer buffers bytes. When the buffer reaches 16 MB, the job sends it with `upload_part` as one part. Part numbers start at 1. It keeps the returned etag, then clears the buffer. The last part may be under 5 MB, which is allowed.
   - Every 10 parts, it saves `rows_written` on the row. It does this only if the row's `attempt` still equals this attempt, so an old attempt cannot overwrite a newer one's progress.
   - Memory use is one 16 MB buffer plus one page of rows. The largest report is about 900 MB of CSV, so about 60 parts. The limit is 10,000 parts. The job never writes a local file. The etags stay in memory.
   - A failed part upload is retried up to 3 times within the same attempt. If it still fails, the attempt fails.
   - An attempt still running at 1,800 seconds is killed and counts as failed.
   - If the replica fails during a read, the read errors and the attempt fails. The next attempt starts again from the first row, after aborting the old upload (step 6).

8. **Publish the file.** This starts when every row has been written.
   - Call `complete_multipart` with the `upload_id` and the etags. This makes the object visible at this attempt's own key. No export record points to it yet.
   - Only after that call succeeds, CAS the row from `running` to `done`. The CAS applies only if `attempt` still equals this attempt. Set `completed_at`, `object_key` (this attempt's key) and `rows_written`.
   - If the CAS applies, this attempt sends the email (step 9). If it does not, this attempt stops and sends nothing.
   - Why this order: the page shows `done` only when the file exists, and a key is served only when a `done` row names it.
   - If `complete_multipart` fails, the attempt fails. The upload stays open for the retry.
   - If the process dies after `complete_multipart` but before the CAS, the row still says `running`. The queue retries after 60 seconds, and the retry writes the whole file again under its own key. The finished object from the dead attempt is never linked, so it is never served. The retry's abort of the old upload ID gets "already gone", which is ignored.
   - Objects from attempts that were never linked stay in the bucket until the 7-day rule deletes them. No job deletes them.

9. **Email the download link.** This starts when the CAS in step 8 applies. Only that attempt sends the email.
   - It builds a signed URL for the row's `object_key`, valid for 86,400 seconds. It calls `send_email(user_id, 'report_export_ready', {report_name, download_url, expires_at})`. On success it saves `email_sent_at`.
   - If the send raises, it logs the error and leaves the state `done`. The page still offers the download. Nothing re-sends the email, and the export is not rerun to fix an email.
   - The link is a bearer link. Anyone who holds it can download the file for 24 hours after it is sent, even if the user has lost access in that time.
   - The template `report_export_ready` must already exist in the email system.

### Part C: the page and the download

10. **Show the export state.** This starts on page load and repeats while the export is `queued` or `running`.
    - The page calls `GET /api/reports/{report_id}/exports/latest`. The server checks report.view, runs the stale check, and returns the user's most recent export for this report: state, attempt, rows_written, filters, completed_at and error_summary. It returns nothing if there is none.
    - The banner depends on the state:
      - `queued`: "Waiting to start."
      - `running`: "Running, attempt N of 3. R rows written so far." The page shows no total or percentage, because row_count is unfiltered and would not match a filtered export. Between attempts the row stays `running` with the last attempt that started, so the banner shows that attempt's number.
      - `done`: a Download button (step 11).
      - `failed`: the `error_summary` and a Start again button, which repeats the click (step 1).
      - `expired`: the state is `done` and `completed_at` is more than 7 days ago. The bucket rule has deleted the file.
    - It polls every 5 seconds while the export is `queued` or `running`, and stops at a final state. It also fetches again when the tab regains focus.
    - A later visit shows the latest export in whatever state it is in. A new click replaces it on screen.
    - The browser keeps nothing that a reload needs. The server holds all state.
    - If the status request fails, the page shows "Status unavailable, retrying" and keeps the last state on screen. The export keeps running on the server.

11. **Download a finished export.** This starts when the user clicks Download on a `done` export.
    - The browser calls `GET /api/exports/{export_id}/download`. The server checks that the caller is the owner, still has report.view, and that the state is `done`. It returns a 302 to a new signed URL that lasts 900 seconds, because the click is immediate.
    - It returns 403 for a non-owner or a caller without access, and 409 if the export is not `done`. It returns 410 if the file is gone, and the page then shows `expired`.

12. **Explain an ignored click.** This starts when a click gets the 200 from step 4 and the active export's filters differ from the page's current filters.
    - The page shows: "An export of this report is already running with filters X. Your new filters were not used. You can start a new export when it finishes."
    - There is no cancel. The user waits for the running export to end, then clicks again. The notice exists so that the user does not take the running file for the one they clicked for.

### Part D: failures and stale exports

13. **Final failure.** The queue calls the final-failure handler once, after attempt 3 fails. That includes an attempt killed by the 30-minute timeout and an attempt whose worker died.
    - Load the row. If `state` is `done`, do nothing.
    - CAS `state` from `queued` or `running` to `failed`. Set `error_summary` to a short phrase: `timed out on attempt 3`, or `failed on attempt 3` when the form of the error is not known. Do not store stack traces or SQL.
    - If `upload_id` is set, abort the upload and ignore failures. The bucket rule covers leftovers.
    - Call `send_email(user_id, 'report_export_failed', {report_name, page_url, error_summary})`.
    - If this handler itself fails, the state stays `running`. The stale check marks it `failed` later, and no email is sent in that case.

14. **Stale check.** This is a check on read, not a cleanup job. It runs on every click, before the insert in step 4, and on every status read in step 10.
    - A `running` export is stale when `attempt_started_at` is more than 2 hours ago. A `queued` export is stale when `created_at` is more than 2 hours ago.
    - A stale export is marked `failed` with `error_summary` "stalled". Nothing is deleted.
    - Why 2 hours is safe: one attempt lasts at most 1,800 seconds. The whole retry chain lasts at most 3 × 1,800 + 60 + 300 = 5,760 seconds, which is 96 minutes. So a live attempt is never cut off.
    - If a stale export's worker is still alive, the user sees "failed: stalled". The worker's later CAS fails, so it writes no `done` and no link is issued. A finished file may sit under its own key with nothing naming it. No email is sent.

## What happens when things fail

| Step | What goes wrong | What happens | What the user sees |
|---|---|---|---|
| 1 | No access, bad input, or replica down | Nothing starts. 403, 400 or 503 | An error; can click again |
| 3 | Connection drops during the inline download | Browser discards the partial file | An error; no partial file saved |
| 4 | Database error on insert | 503. No job starts | An error; can click again |
| 4 | An active export blocks the click | Returned with 200 | The notice in Part C |
| 5 | `enqueue` raises | Row set to `failed`, "could not start" | An error; can click again |
| 5 | Process dies before `enqueue` | Row stays `queued` with no job | Waiting, then `failed: stalled` after 2 hours |
| 6 | Error during claim or setup | Attempt fails; retry after 60 s, then 300 s | Queued or running |
| 6 | Process dies between starting the upload and saving its ID | Upload never recorded; bucket discards it in 24 h | Running; retry proceeds |
| 6 | Owner has lost report.view | `failed: access removed`; no retry; failure email | Failed |
| 7 | A part upload fails | Retried 3 times, then the attempt fails | Running; retry |
| 7 | Attempt reaches 1,800 s | Killed; attempt fails; next attempt starts from row 1 | Running; retry |
| 7 | Replica fails during a read | Attempt fails; next attempt starts from row 1 | Running; retry |
| 8 | `complete_multipart` fails | Attempt fails; upload kept for the retry | Running; retry |
| 8 | Process dies after `complete_multipart`, before the CAS | Retry writes under its own key; old object never linked | Running, then done |
| 9 | Email send fails | Logged; state stays `done` | Download works; no email |
| 10 | Status request fails | Server work continues | "Status unavailable, retrying" |
| 11 | Download of an old file | Object gone under the 7-day rule | Expired |
| 13 | The final-failure handler itself fails | State stays `running` until the stale check | `failed: stalled` after 2 hours; no email |

## Open questions

- How does the queue start a waiting job, and how long can a job wait? `jobs.py` does not say. If the queue backs up beyond 2 hours, the stale check marks a waiting export as stalled.
- Does the queue confirm that a killed attempt has stopped before its retry starts? The file contents do not depend on this, because each attempt writes its own key. The progress and completion writes do depend on the attempt-number check.
- Rows can change between pages during the nightly rebuild. The file may then mix two report versions or miss rows. Is the rebuild atomic, and does the replica give a stable snapshot? One option is to record a rebuild marker at claim time and fail the attempt if the marker changes.
- The brief says a second click returns the running export. The notice in Part C is our addition. Is that the wanted behaviour?
- The unfiltered threshold sends small filtered views through the job. Accept that, or add a filtered count?
- Failed emails are not retried. Accept that, or add retries for emails only?
- `jobs.py` does not say what form the error takes when the final-failure handler runs. Until it is known, `error_summary` uses the fixed phrases in step 13.
- Should cells that start with `=`, `+`, `-` or `@` be neutralised to block spreadsheet formula injection? This must be decided before building.
- Who owns the email templates `report_export_ready` and `report_export_failed`?
- Is the `exports` bucket private, so that signed URLs are the only access path?

## How to build and roll out

These steps are for the people building the feature. They are not part of how the feature runs.

- **Throughput gate, before building.** Time keyset reads of 5,000 rows at a time from the replica for the largest report (about 2 million rows). Write CSV in chunks. Run from the same network position as a worker. The job needs at least 1,100 rows per second to finish within 1,800 seconds. Target 2,200 rows per second for margin. Record the result in the ticket.
  - If the gate fails, do not build the job as written. The options are a query or index change on `report_rows`, which needs its own review, or splitting the export into several jobs. Splitting is a second design. The storage helpers cannot join objects, and every part except the last must be at least 5 MB.
  - Does the gate pass? That is unknown until it is run. The inline path's 60-second limit at 10,000 rows is checked by the same measurement.
- **Verification before release:**
  - Unit tests for CSV escaping, column order and rejection of unknown columns.
  - Equivalence: for a fixture report, inline and job output are byte-identical for the same filters and cols.
  - Failure injection: kill the worker during the row write, and again during publish. Confirm that no object is linked before `complete_multipart`, and that the next attempt aborts the old upload.
  - Duplicate delivery: run the handler twice after `done`. Confirm one file and one email.
  - Concurrency: two simultaneous clicks produce one export record.
  - Memory: peak worker memory during the 2-million-row run stays well below 512 MB.
  - Permission: remove report.view mid-export. Confirm the job fails without retries and the owner gets the failure email.
  - Throughput: repeat the gate on a real worker against the full report.