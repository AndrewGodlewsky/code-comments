# CSV export for the reports page

Users want a **Download CSV** button on the reports page. The page loads a report's rows in pages from the read replica, and its filters and column order live only in the page URL. The click builds a CSV of what the user is looking at. Reports of 10,000 rows or fewer return the CSV in the response. Larger reports are built by a background job that saves the file to storage and emails the user a link that works for 24 hours.

## Out of scope

Scheduled exports, formats other than CSV, and changes to the table on the page.

## Terms

- **Report row count**: `reports.row_count`, the total number of rows in a report before filters. It is rebuilt each night, so it can be a day old. The path choice uses this total, not the count after filters.
- **Read replica**: a copy of the database that only serves reads. Report rows are read only from it, never from the main database.
- **Keyset paging**: reading rows after the last `row_id` seen, in `row_id` order, instead of skipping a number of rows. Every page is equally fast.
- **Job queue**: runs a handler function in the background, outside the web request. An attempt fails if the handler raises an error, runs longer than 30 minutes, or its worker dies. A failed job is retried after 60 seconds, then after 300 seconds, up to 3 attempts in total. The queue keeps no progress between attempts, so each attempt starts from the beginning. A job can run again after it has already succeeded.
- **Worker**: a process that runs jobs. Each worker has 512 MB of memory and runs one attempt at a time.
- **Exports bucket**: the existing object storage bucket `exports`. An existing lifecycle rule deletes each file 7 days after it was created. We build no cleanup job.
- **Multipart upload**: writes one large file as numbered parts. Nothing is visible at the file's key until all parts are joined. Every part except the last must be at least 5 MB, and a file can have at most 10,000 parts. The bucket discards an upload that is not completed within 24 hours.
- **Signed link**: a download URL that stops working after a set time. Ours works for 24 hours, the longest allowed.
- **Export record**: one row in a new `report_exports` table for each large export. It holds the user, the report, the filters, the column order, the status, the upload id and the file's key.
- **send_email(user_id, template, params)**: the existing helper that emails a user from a named template.

## Steps

1. **The user clicks Download CSV.** The page sends the current filters and column order from the URL. The server first checks `report.view` on the report's workspace, as the page does, and returns 403 if the user lacks it. Nothing is stored. Then the server reads `reports.row_count`.
   - 10,000 or fewer: go to step 2.
   - More than 10,000: go to step 3. A filtered view with few rows still takes the job path if the whole report is large.

2. **Small report: the response is the CSV.** The server reads the matching rows from the read replica, using keyset paging. It writes a header row, then one line per row, with columns in URL order. It returns the file as the response. Nothing is stored and no job runs. The API kills any request that runs longer than 60 seconds, so this path must finish within that time.
   - Kept in: nothing. The file exists only in the response.
   - If it fails: the download stops and nothing is left behind. The user clicks again. No queue retry applies, because no job exists.

3. **Large report: the click starts a job.** The server checks whether the user already has an export of this report that is queued or running. The database enforces this with a unique index on user and report while the status is queued or running, so two quick clicks cannot both create one.
   - If one exists, the server returns that export instead of starting another.
   - If none exists, the server creates the export record with status `queued`, enqueues a `report_export` job with the export's id as its payload, and returns the export's status straight away.
   - Kept in: the export record in `report_exports`.
   - If enqueueing fails: the record is set to `failed` and the user sees an error.

4. **The job builds the file.** A worker starts this when it picks up the job. Each attempt does all of the following from the beginning.
   1. Load the export record. If it is already `done`, stop. Otherwise set its status to `running`. It stays `running` through any retry wait.
   2. Start a multipart upload to the `exports` bucket, at a key for this export. Save the upload id on the record.
   3. Read rows from the read replica in batches, in `row_id` order, using keyset paging and the filters on the record. Write a header row first, then the rows, with columns in the stored order, as CSV text in a buffer. Each time the buffer reaches 5 MB, upload it as the next part. Only one buffer and one batch of rows are in memory at a time, so the whole report is never held in memory.
   4. Upload the remaining buffer as the last part. It may be smaller than 5 MB. Complete the upload. This makes the file visible at its key and replaces any file already there.
   5. Create a signed link that works for 24 hours. Send it to the user with `send_email`. Then set the record to `done`.
   - Kept in: rows stay in the read replica. Uploaded parts stay in the unfinished upload until it is completed. The status and upload id are in `report_exports`. The finished file is in the `exports` bucket.
   - The whole attempt must finish within 30 minutes.
   - If the attempt fails: the job aborts the upload it started, so no partial file remains. The queue retries the job.
   - If the worker dies: the upload is left unfinished. The queue retries the job. The bucket discards the unfinished upload after 24 hours.

5. **Last attempt fails.** After the third attempt fails, the queue calls the failure handler once. The handler aborts the upload if one is recorded, sets the record to `failed` with the error, and emails the user that the export failed.

6. **The page shows the status.** The page asks the server for the status of the user's latest export of this report, using the same `report.view` check. It shows queued, running, done or failed. The status comes from `report_exports`, so it is still shown when the user returns later. While an export is queued or running, the page polls the server for updates.

## What happens when things fail

| Where | What goes wrong | What happens |
|---|---|---|
| Step 1 | User lacks `report.view` | 403. Nothing is created. |
| Step 2 | Query fails or times out | Download stops. Nothing is stored. The user clicks again. |
| Step 3 | User clicks again while an export is active | The existing export is returned. No new job starts. |
| Step 3 | Enqueueing fails | The record is set to `failed`. The user sees an error. |
| Step 4 | Attempt raises an error or passes 30 minutes | Upload is aborted. The queue retries. |
| Step 4 | Worker dies during an attempt | Upload is left unfinished. The queue retries. The bucket discards the unfinished upload after 24 hours. |
| Step 4 | Job runs again after it succeeded | The record is `done`, so the attempt stops. |
| Step 5 | Third attempt fails | Record is `failed`. Upload is aborted. The user is emailed that the export failed. |

## Build order

1. Create the `report_exports` table, with the unique index for active exports.
2. Add `POST /api/reports/{report_id}/exports` (steps 1 to 3) and the status request (step 6).
3. Add the `report_export` job and its failure handler (steps 4 and 5).
4. Add the status display and polling to the reports page.

## Open questions

- Which `send_email` template names are used for the download link and for the failure notice? Not decided.
- Can a report of about 2 million rows (about 900 MB as CSV) finish within the 30-minute attempt timeout? Not known. The plan has no measurement.
- Should the page also show the download link when an export is done, or only send it by email? The brief asks only for the status.