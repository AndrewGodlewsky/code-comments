# CSV export plan

## What this is

The reports page gets a **Download CSV** button. It exports the rows the user is looking at: the filters and column order from the page URL, plus a header row. A small report (10,000 rows or fewer) downloads straight away, in the response to the click. A large report is built by a background job. The job writes the CSV to object storage and emails the user a link that works for 24 hours. The page shows the state of a large export.

Today the page loads rows in pages from the read replica through `GET /api/reports/{report_id}/rows`. The server stores no view state, so the export reads rows the same way.

## Terms

- **Report**: one table of rows. Rows are read from the read replica, never from the primary database.
- **View**: the filters and column order in the page URL.
- **Export**: one request for a CSV of one view. Each export is a row in the `report_exports` table, with a status.
- **Status**: one of queued, running, done or failed.
- **Job**: work that the job queue runs in the background on a worker. A worker has 512 MB of memory.
- **Attempt**: one run of a job. A job gets at most 3 attempts. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. Each attempt starts from the beginning. An attempt that runs longer than 30 minutes is stopped.
- **Multipart upload**: a file sent to object storage in parts. Nothing is visible at the file's key until the upload is completed.
- **Signed link**: a download URL that stops working after a set time. Here it lasts 24 hours.

## Main flow

1. **The click starts the export.** The page sends `POST /api/reports/{report_id}/exports` with the filters and columns from the URL.
   - Starts when: the user clicks Download CSV.
   - What it does: checks `report.view` on the report's workspace, then reads `reports.row_count`. If the count is 10,000 or fewer, go to step 2. Otherwise go to step 3.
   - Data kept: nothing yet.
   - When it fails: no permission means a 403, and nothing starts.

2. **A small export streams the CSV.**
   - Starts when: step 1 chose this path.
   - What it does: writes the header row. Then it reads report rows from the replica 500 at a time, in `row_id` order, applying the filters. Each batch goes into the response as soon as it is read.
   - Data kept: nothing. Only one batch is in memory at a time.
   - When it fails: the server stops partway through the response. The browser should not save the file as complete. The user clicks again.

3. **A large export is recorded and queued.**
   - Starts when: step 1 chose this path.
   - What it does: if this user already has a queued or running export of this report, returns that one. Otherwise it inserts a `report_exports` row with status queued, the user, the report, the filters and the columns. Then it queues a `report_export` job whose payload is only the export id. It returns the export id and status to the page.
   - Data kept: the `report_exports` row, in the primary database.
   - One at a time: a unique index allows only one queued or running row per user and report. Two fast clicks cannot both create one. The second request gets the first row back.
   - When it fails: if queuing fails, the row is marked failed and the request returns an error.

4. **The job builds the file.**
   - Starts when: the queue runs an attempt.
   - What it does: loads the export row. If the row is already done, it stops. Otherwise it sets status to running and starts a multipart upload to `exports/{export_id}.csv`. It writes the header row. It reads the replica 500 rows at a time, in `row_id` order, with the stored filters, and collects the CSV text into parts of at least 5 MB. Each part is uploaded as it fills. Then it goes to step 5.
   - Data kept: one batch and one part in memory at a time. Uploaded parts wait in the bucket, invisible. The status is in the row.
   - When it fails: any error ends the attempt, and the attempt tries to abort its upload. The queue then retries after 60 seconds, and after 300 seconds, starting over with a new upload. An attempt that runs past 30 minutes is stopped and counts as failed. If the worker dies, no abort runs. The bucket discards the unfinished upload within 24 hours.

5. **The job publishes the file.**
   - Starts when: step 4 has uploaded every row.
   - What it does: completes the upload, so the file appears at its key. Creates a signed link that lasts 86,400 seconds. Calls `send_email(user_id, template, params)` with the link. Sets status to done.
   - Data kept: the file stays in the `exports` bucket. The bucket's lifecycle rule deletes it 7 days after it was created. No cleanup job is needed. The status is done in the row.
   - When it fails: an error ends the attempt, and the job retries from step 4. If the email is sent but the row is not yet marked done, a retry sends the email again. The queue delivers at least once, so this is accepted.

6. **The job gives up.**
   - Starts when: the third attempt has failed.
   - What it does: `on_final_failure` sets status to failed, then sends the user a failure email.
   - Data kept: status failed. Any unfinished upload is left to the 24-hour rule.
   - Next: the user can start a new export, because none is queued or running.

7. **The page shows the state.**
   - Starts when: the user opens the report page or clicks Download CSV.
   - What it does: calls `GET /api/reports/{report_id}/exports/latest`, which returns this user's latest export of this report after a `report.view` check. The page shows queued, running, done or failed. While the status is queued or running, the page asks again every few seconds.
   - Data kept: nothing new. The page reads the row.
   - When it fails: the page keeps the last state it showed and asks again.

## What happens when things fail

| Situation | What happens | What the user sees |
|---|---|---|
| No `report.view` permission | 403, nothing starts | Error on the page |
| Small export read fails partway | Response is cut off | Incomplete download; user clicks again |
| Queuing fails after the row is inserted | Row marked failed | Error on the page |
| An attempt errors or runs past 30 minutes | Retry after 60 s, then 300 s, from the start | Nothing, until the final failure |
| Worker dies during an attempt | Queue retries; unfinished upload dropped after 24 h | Nothing, until the final failure |
| Third attempt fails | Status failed; failure email sent | Failure email and failed status on the page |
| Crash between sending the email and marking done | Next attempt sends the email again | Duplicate email |

## Open questions

- Can a 2-million-row report finish inside the 30-minute attempt timeout? If not, the job must be split, and this plan does not yet say how.
- Can a 10,000-row small export finish inside the API's 60-second limit?
- `reports.row_count` is the total, unfiltered count. A heavily filtered view of a large report still takes the job path. The brief sets this rule. Confirm that it is intended.
- What does the page show for a done export after its 24-hour link has expired?
- Does `send_email` raise an error when it fails, or return a value? Step 5 assumes it raises.