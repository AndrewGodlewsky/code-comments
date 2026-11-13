# CSV export plan

## Summary

The reports page shows one report as a table. It loads rows from `GET /api/reports/{report_id}/rows`. That call checks the `report.view` permission, reads rows from the read replica, and pages by `row_id`. The server stores nothing about what the user is viewing. The filters and column order live only in the page URL.

This plan adds a **Download CSV** button. The CSV holds what the user is looking at: the rows that match the URL's filters, in the URL's column order, with a header row first. The report size decides how the export runs. A report of 10,000 rows or fewer is streamed back as the CSV in the response to the click, and nothing is stored. A larger report makes the click return at once with an export record. A background job then builds the CSV in small pieces, uploads it to object storage, emails the user a link that works for 24 hours, and marks the export done. The page shows the export's state until it ends. The click stays fast, no worker holds a whole report in memory, and a half-written file is never downloadable.

## Terms

- **View**: the filters and column order in the page URL, for example `?status=open&region=EU&cols=date,customer,amount`.
- **Report size**: `reports.row_count`, the total number of rows in the report before filters. It is rewritten each night when report data is rebuilt. The largest report today has about 2 million rows, roughly 900 MB as CSV.
- **Read replica**: a read-only copy of the database. Report rows are read only from it, never from the main database. It can lag behind the main database.
- **Main database**: the writable database. It holds the export records.
- **Export**: one row in the `report_exports` table. It tracks one large CSV from queued to done or failed.
- **Job**: work that the background job queue runs on the worker pool. Each worker has 512 MB of memory and runs one job attempt at a time.
- **Attempt**: one run of a job. A job gets at most 3 attempts in total. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. An attempt still running after 30 minutes is killed.
- **Payload**: the data passed to a job. It must be JSON and under 64 KB.
- **Final-failure handler**: a function the queue calls once, after the third attempt has failed.
- **At-least-once delivery**: the queue may run a job again after it has already succeeded, so the job must handle a repeat.
- **Multipart upload**: sending one file to object storage in parts. Each part except the last must be at least 5 MB. A file can have at most 10,000 parts. Nothing is visible at the file's key until the upload is completed. Aborting discards the parts uploaded so far.
- **Exports bucket**: the object storage bucket `exports`, which already exists. Every object is deleted 7 days after it was created. An upload not completed within 24 hours is discarded. Old files are removed by this rule only. No cleanup job is built.
- **Signed link**: a download URL that works for a set time, at most 24 hours.
- **`send_email(user_id, template, params)`**: the existing mail helper. It finds the user's address from `user_id`.

## Steps

1. **The user clicks Download CSV.** The page sends `POST /api/reports/{report_id}/exports` with its current view. The server first checks `report.view` on the report's workspace. Without it, the server returns 403 and stores nothing. With it, the server reads `reports.row_count` and goes to step 2 if the count is 10,000 or fewer, or to step 3 if it is higher. The POST does no export work itself, because API servers kill any request that runs longer than 60 seconds.

2. **Small report: stream the CSV.** The response body is the CSV. It starts with the header row. Then it sends rows read from the read replica in batches of 500, using `row_id` order, in the view's column order, with the view's filters applied. Nothing is stored. If reading fails partway, the response stops, the download fails, and the user clicks again. The whole response must finish within the 60-second API limit.

3. **Large report: queue a job.** This runs when the count is above 10,000.
   a. The server looks for an export of this report by the same user with status `queued` or `running`. This check ignores the view's filters. If one exists, the server returns it and starts nothing.
   b. Otherwise the server inserts a `report_exports` row with status `queued`, the view, and the user and report ids. It then enqueues a `report_export` job whose payload is only the `export_id`. If the enqueue fails, the row is set to `failed` and the POST returns an error.
   c. The server returns `202` with the `export_id` and its status. The click returns at once.
   A database rule allows only one `queued` or `running` export per user and report. So two clicks that arrive together cannot both start one. If the insert is refused by that rule, the server returns the export that won, as in step 3a.

4. **The job builds the file.** The queue starts an attempt, passing the `export_id`. Each attempt does the following.
   a. It loads the export row. If the status is `done`, it stops. The queue may run the job again after success, and this stops a second file from being written.
   b. It sets the status to `running` and `attempt` to this attempt's number. It starts a new multipart upload to `exports/report-{report_id}/{export_id}.csv` and saves the `upload_id`. Each attempt starts its own upload.
   c. It writes the header row. Then it reads rows from the read replica in batches of 500, in `row_id` order, in the view's column order, with the view's filters applied. It holds one batch and one upload part at a time. When a part reaches 5 MB, it uploads that part and keeps its etag. The whole report is never held in memory, so a 2-million-row report fits in a 512 MB worker.
   d. After the last row, it uploads the final part, which may be smaller than 5 MB, and completes the upload. Completing the upload makes the file appear at its key. Only now can the file be downloaded, so a half-written file is never downloadable.
   e. It creates a signed link valid for 24 hours. It calls `send_email` with the user, an export-ready template and the link. Only after the email is sent does it set the status to `done`.
   The whole attempt must finish within the 30-minute attempt limit. If anything fails, step 5 applies.

5. **Failure and retry inside the job.** This runs when an attempt raises an error, runs past 30 minutes, or its worker dies.
   - If the attempt raises an error, the job catches it first. It calls `abort_multipart` on this attempt's `upload_id`, saves the error text on the export row, and re-raises so the queue retries. A timeout or a worker death skips this abort, so the bucket's 24-hour rule discards the unfinished upload.
   - Between attempts the status stays `running`.
   - The next attempt starts again at step 4b with a new upload. Earlier parts are never reused.
   - When the third attempt fails, the queue calls the final-failure handler once. The handler sets the status to `failed`, saves the error, and sends the failure email with `send_email`. Only this handler sends the failure email, so the user is not emailed after each retry.

6. **The page shows the export state.** When the report page opens, it calls `GET /api/reports/{report_id}/exports/current`. This call does the same `report.view` check. It returns the user's most recent export for this report, so a user who comes back later still sees its state. If the user has no export for this report, the page shows only Download CSV.
   - Status `queued` or `running`: the page shows that state and calls this endpoint again every 5 seconds.
   - Status `done`: the page shows a download button. The call returns a fresh signed link valid for 24 hours. If the file is more than 7 days old, the bucket rule has deleted it. The call then returns no link, and the page offers Download CSV again, which starts a new export.
   - Status `failed`: the page says the export failed and offers Download CSV, which starts a new export.
   The page stops polling at `done` or `failed`.

## What happens when things fail

| Where | What goes wrong | Result |
|---|---|---|
| 1. Click | No `report.view` permission | 403; nothing is stored |
| 2. Small stream | Read error, or the response runs past 60 seconds | Download stops; nothing is stored; user clicks again |
| 3b. Enqueue | Enqueue error | Row set to `failed`; POST returns an error |
| 3. Two clicks at once | The one-export rule refuses the second insert | Server returns the existing export; no job starts |
| 4 and 5. Attempt 1 or 2 raises an error | Upload aborted; status stays `running`; next attempt after 60 or 300 seconds |
| 4 and 5. Attempt 1 or 2 times out or its worker dies | No abort runs; status stays `running`; bucket rule discards the unfinished upload after 24 hours; next attempt after 60 or 300 seconds |
| 4 and 5. Attempt 3 fails for any reason | Final-failure handler sets `failed`, saves the error and sends the failure email |
| 4e. Email fails | Counts as an attempt failure; retried like any other failure |
| 4a. Job runs again after success | Status is `done`; the job stops; no second file is written |
| 6. Emailed link | Link is more than 24 hours old; it stops working. The status call returns a fresh link |
| 6. Status call, file more than 7 days old | No link; page offers Download CSV to start a new export |

## Build and rollout

These are the pieces to build. They are not part of how the system runs.

- Create the `report_exports` table in the main database. It holds `export_id`, `report_id`, `user_id`, `view` (the page's query string), `status` (`queued`, `running`, `done` or `failed`), `attempt`, `upload_id`, `file_key`, `error`, and created and updated times. Only the export code writes to it.
- Add the database rule that allows only one `queued` or `running` export per user and report.
- Register the `report_export` job with its final-failure handler.
- Add an export-ready email template and a failure email template for `send_email`.
- Add the Download CSV button and the status display to the reports page. The page's table does not change.
- Out of scope: scheduled exports, formats other than CSV, and changes to the table on the page.

## Open questions

- Should the duplicate check compare filters? As written, a second export of the same report with different filters returns the first export.
- The 10,000-row threshold counts the unfiltered total, so a small filtered view of a large report takes the job path.
- Can a 2-million-row export (about 900 MB) finish within the 30-minute attempt limit? No timing is in the files.
- How far can the replica lag behind the main database? The files do not say.
- Can a 10,000-row stream finish within the 60-second API limit? Not measured.
- Anyone holding a signed link can download the file until it expires. Is that acceptable?
- A retry after the email was sent can send the email a second time. Is that acceptable?