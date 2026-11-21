# CSV export for the reports page

Today the reports page loads one report 500 rows at a time from the read replica, and the server keeps no state about what a user is viewing. This plan adds a **Download CSV** button that exports what the user sees: the filters and column order in the page URL, plus a header row. A report of 10,000 rows or fewer is sent back as the CSV in the response. A larger report gets a quick reply, and a background job builds the CSV in object storage and emails the user a link that works for 24 hours. The page shows the export's status. There are two paths because the API stops any request that runs longer than 60 seconds, and a large report could take longer.

## Terms

- **API**: the web servers that answer `/api/...` requests. They stop any request that runs longer than 60 seconds.
- **report.view**: the permission to view a report in its workspace. The page and the export both need it. Without it, the API returns 403 (forbidden).
- **Read replica**: a copy of the database that serves reads. Report rows are read only from it, never from the primary database.
- **row_id**: a number that is unique and increases within one report.
- **Keyset paging**: reading the next page as rows whose `row_id` is greater than the last one seen, in `row_id` order. It never uses OFFSET, so every page is equally fast.
- **reports.row_count**: the total number of rows in a report, before filters. It is rewritten each night, so it can be a day old.
- **Job queue**: the existing background system. Jobs run on workers. Each worker has 512 MB of memory and runs one attempt at a time.
- **Job payload**: the small JSON value passed to a job. It must be under 64 KB.
- **Attempt**: one run of a job. A job gets at most 3 attempts in total. The queue keeps no progress between attempts.
- **At-least-once**: the queue may run a job again after it already succeeded. Job code must be safe to rerun.
- **202 (accepted)**: the API accepted the request, and the work continues in the background.
- **Multipart upload**: writing one large file in parts. Each part except the last must be at least 5 MB, and an upload can have at most 10,000 parts. Nothing is visible at the file's key until the upload is completed in one step. Aborting it discards the parts.
- **exports bucket**: the existing object storage bucket for export files.
- **Lifecycle rule**: the bucket's automatic cleanup. It deletes each file 7 days after it was created, and it discards any multipart upload not completed within 24 hours.
- **Signed link**: a download URL that works for a set time. The longest allowed is 24 hours. Anyone who holds the link can download the file without logging in.
- **send_email(user_id, template, params)**: the existing helper that emails a user with a named template.
- **Partial unique index**: a database rule that rejects a new row if another row matches a condition. Here the condition is status queued or running, so one user can have only one such export per report.
- **report_exports table**: the one new table, with one row per export. Columns: `id`, `report_id`, `user_id`, `status` (queued, running, done or failed), `query` (the filters and column order from the URL), `job_id`, `object_key` (where the file sits in the bucket), `created_at` and `finished_at`.

## How it runs

1. **Click starts the export: `POST /api/reports/{report_id}/exports`.** The user clicks Download CSV. The request carries the filters and column order from the page URL. The API checks `report.view` on the report's workspace and returns 403 without it. It then reads `reports.row_count`. Filters do not change this choice. If the count is 10,000 or fewer, go to step 2. If it is more, go to step 3.

2. **Small path: the response is the CSV.** The API reads the replica in pages of 500 rows, by `row_id`, and streams the rows back as CSV. The first line is a header row. Columns follow the order in the URL. Nothing is stored and no job runs. The stream must finish within the API's 60-second limit. If it breaks, the user gets a partial file and clicks again.

3. **Large path: queue the export.** The API inserts a `report_exports` row with status queued and the query from the URL. The query is saved on the row, not in the job payload, because the job reads it from the row.
   - If the partial unique index rejects the insert, the user already has a queued or running export of this report. The API returns that row with 202 and starts no job. The index also stops two simultaneous clicks from both inserting.
   - Otherwise the API enqueues a `report_export` job whose payload is only the export id. It saves the job id on the row and returns 202 with the export id and status.
   - If enqueueing fails, the row is marked failed, the API returns an error, and the user can click again.
   - A click after an earlier export is done or failed is not a duplicate. The index covers only queued and running rows, so a new row is inserted with its own id and file key. The old file is not overwritten.
   - If the API dies after the insert and before the enqueue, the row stays queued with no job id. See open questions.

4. **Job attempt: build the file.** The queue runs this step for each attempt, using the export id from the payload.
   - Load the row and its query. If the row is already done or failed, stop and do nothing. This covers a finished job that is delivered again, so the file is not rebuilt and no second email goes out.
   - Otherwise, run these parts from the start on every attempt, because the queue keeps no progress:
     - a. Set the row to running.
     - b. Start a multipart upload to `exports/{report_id}/{export_id}.csv`. Nothing is visible at that key yet.
     - c. Read the replica in pages of 500 rows by `row_id`, starting from the first row.
     - d. Write CSV text, with the same header row and column order as the small path, into one buffer of about 8 MB. When the buffer is full, upload it as one part. Only one buffer is in memory at a time, so the report is never held whole. Uploaded parts stay in the unfinished upload until step e.
     - e. Complete the upload. The file appears at its key and replaces any file already there, so a rerun is safe. This is the only moment the file becomes downloadable.
     - f. Set the row to done, with `object_key` and `finished_at`. Then call `send_email` with the success template and a signed link that works for 24 hours.
   - The row holds the status. Report rows stay in the replica.
   - If any of parts b to e raises an error, the job aborts the upload and raises the error, so the queue retries.

5. **Retries and final failure.** An attempt fails when it raises an error, runs past the 30-minute attempt timeout, or its worker dies. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. The row stays running during these waits.
   - After an error, the job has already aborted its upload.
   - After a timeout or worker death, nothing cleans up. The unfinished upload stays until the bucket discards it after 24 hours.
   - Earlier failures send no email.
   - After the third failure, the queue calls `on_final_failure` once. It sets the row to failed and sends the failure email.

6. **Page status: `GET /api/reports/{report_id}/exports/latest`.** The page calls this on load, so a user who comes back later sees the export's state. The API checks `report.view` as step 1 does and returns 403 without it. It returns the user's most recent export of that report, ordered by `created_at`, with its id and status. The page shows queued, running, done or failed. While the status is queued or running, the page asks again every 5 seconds. The 5-second interval is a choice; the brief names none. Polling stops when the status is done or failed. When the status is done, the response includes a new signed link that works for 24 hours, so the user can still download the file later. A new click starts a new export (step 3), and that row becomes the latest.

## Rules for every step

- Report rows are read only from the read replica.
- The server stores only `report_exports` rows. The page stores nothing. Its filters and column order live only in the URL.
- A file is downloadable only after its upload completes (step 4e). A half-written file is never downloadable.
- No job holds a whole report in memory. The largest report has about 2 million rows, about 900 MB as CSV, and a worker has 512 MB.
- Each job must finish within the 30-minute attempt timeout.
- Job code must tolerate reruns, because delivery is at least once.
- One user can have only one queued or running export of a given report. The partial unique index enforces this.
- No code deletes export files. The lifecycle rule deletes each file 7 days after creation. Do not build a cleanup job.

## What happens when things fail

| Where | What the user sees |
| --- | --- |
| Permission check (steps 1 and 6) | 403 error; nothing starts |
| Small path stream breaks (step 2) | Partial download; user clicks again |
| Second click while queued or running (step 3) | Current export's status; no new job |
| Enqueue fails (step 3) | Error; row marked failed; user can click again |
| API dies after insert, before enqueue (step 3) | Stuck as queued with no job; blocks new clicks for this report (see open questions) |
| Attempt raises an error (step 4) | Still running; upload aborted; retry after 60 s or 300 s |
| Attempt times out or worker dies (step 4) | Still running; bucket discards the partial upload after 24 h; retry |
| Job delivered again after done or failed (step 4) | Nothing happens; no rebuild, no email |
| Third attempt fails (step 5) | Failed on the page and by email |

## Build notes

These notes are for building the feature, not for how it runs.

- One migration adds the `report_exports` table. The `report_rows` table and the page's table do not change.
- Create the success and failure email templates. Their names are not defined yet.
- Register the `report_export` job with `on_final_failure`, so the queue calls the failure step after the last attempt.
- Out of scope: scheduled exports, formats other than CSV, and changes to the page's table.

## Open questions

- Nobody has measured whether 2 million rows can be read and uploaded within the 30-minute attempt timeout. If not, every attempt fails.
- Anyone holding a signed link can download the file for 24 hours without logging in. The brief sets no other check.
- A second click with different filters returns the running export, so the page shows the old filters. The duplicate check ignores filters.
- The file is deleted 7 days after creation, but the link stops working after 24 hours. The page may still show done with a dead link after the file is gone. A rule is needed.
- If `send_email` fails after the file is complete (step 4f), the attempt fails. After 3 attempts the export ends as failed, although the file exists.
- If the worker dies after the row is set to done and before the email is sent, the rerun stops at the done check, so no email is sent.
- It is unknown whether the 60-second request limit also covers a streamed response.
- If the API dies after inserting a queued row and before enqueueing, the row stays queued with no job id. The unique index then blocks every new click for that report. The brief gives no rule to clear such a row.
- If `on_final_failure` raises an error, or the worker dies before it runs, the row stays running and no failure email is sent. The queue's code does not say whether the hook is retried. The unique index then blocks new clicks for that report.