# CSV export plan

Users want a **Download CSV** button on the reports page. The button saves the rows the user is looking at: the same filters and column order from the page URL, plus a header row (the first line of the file, holding the column names). Small reports download straight away, as the response to the click. Large reports are built in the background by a worker process, and the user then gets an email with a download link.

## How the pieces fit

- **The reports page** shows one report as a table. As the user scrolls, it asks our API for the next 500 rows.
- **The button** asks the API to start an export. A small export returns the CSV in that same response. A large export creates a record in the database and queues a job.
- **The job** is code that runs later on a worker, separate from the web server. It writes the CSV to object storage (cloud file storage), then emails the user a link.
- **The `report_exports` table** holds one record per large export. That record is the only place its status is kept. The page reads it to show progress.

## Words used in this plan

- **Primary and replica.** The primary is the main database, the one that accepts writes. The replica is a read-only copy of it. Report rows are read only from the replica, never from the primary.
- **Endpoint.** A URL on our API that the page calls, such as `POST /api/reports/{report_id}/exports`.
- **Row ID.** A number that identifies a row inside one report. It only goes up, so rows can be put in order.
- **Keyset paging.** Reading a table in pages by remembering the last row ID you saw and asking for the rows after it (`row_id > last ORDER BY row_id`). Unlike OFFSET, which must skip over every earlier row, each page costs the same no matter how far into the report you are.
- **Job and queue.** A job is a piece of background work. The queue holds jobs and hands each one to a worker. Each worker has 512 MB of memory and runs one attempt at a time. An **attempt** is one run of a job. A job gets at most 3 attempts. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. An attempt still running after 30 minutes is killed and counts as failed. The queue keeps no progress between attempts, so each attempt starts the job from the beginning with the same payload.
- **At least once.** The queue may run a job again even after it already succeeded. So every step must be safe to repeat.
- **Payload.** The small piece of data sent with a job when it is queued. Ours is JSON, under 64 KB.
- **Export record.** A row in the new `report_exports` table. It tracks one large export from start to finish.
- **Unique index.** A database rule that refuses two rows with the same values in the chosen columns. Here it means the database refuses a second active export for the same user and report, even when two clicks arrive at the same moment.
- **Object storage and the exports bucket.** Object storage keeps files under a key (a name). A **bucket** is a storage area. The `exports` bucket holds export files. Each file is deleted 7 days after it was created.
- **Multipart upload.** A way to write one large file as numbered **parts**, then join them. Every part except the last must be at least 5 MB. Nothing appears at the file's key until the upload is completed. The bucket discards any upload not completed within 24 hours.
- **ETag.** The identifier storage returns for each uploaded part. The join step needs all of them, in order.
- **Signed link.** A download URL that works without logging in, for a set time. Anyone who has the link can download the file until it expires.
- **Template.** Pre-written email text with blanks, such as the link, filled in from `params`.
- **Filters and columns.** The `filters` and `cols` values in the page URL, for example `?status=open&region=EU&cols=date,customer,amount`.

## Steps

### 1. Add the `report_exports` table

- **Starts when:** the database migration that creates the table is deployed. A migration is a script that changes the database structure.
- **Columns:** `id`, `report_id`, `user_id`, `status` (one of `queued`, `running`, `done`, `failed`), `filters` and `cols` (copied from the URL when the user clicks), `upload_id`, `object_key`, `row_count`, `error` (a short message), `email_sent_at`, `created_at` and `updated_at`.
- **Where state lives:** this table is the only record of an export's state.
- **One active export:** a unique index on (`user_id`, `report_id`), applied only to rows whose status is `queued` or `running`. The database then refuses a second active export for the same user and report.
- **If it fails:** the migration is rolled back. Nothing else has changed.

### 2. Handle the click: `POST /api/reports/{report_id}/exports`

- **Starts when:** the user clicks Download CSV. The page sends the filters and columns from its URL, because the server stores no view state.
- **Checks, in order:**
  1. The caller must have the `report.view` permission on the report's workspace. If not, return HTTP 403 (forbidden) and stop. No data is read.
  2. Read `reports.row_count` from the replica. This is the total number of rows in the report with no filters applied.
  3. If the count is 10,000 or fewer, take the small path (step 3).
  4. If the count is more than 10,000, take the large path (step 4).
- **If it fails:** a database error returns an error response. No export starts and no record is written.

### 3. Small report: send the CSV in the response

- **Starts when:** step 2 found 10,000 rows or fewer.
- **Data moves:** the server reads rows from the replica 500 at a time, using the same keyset query and filters as the page. It writes a header row, then one CSV line per row, with columns in the order given by `cols`. Quotes, commas and line breaks inside values are escaped as the CSV format requires. The response has `Content-Type: text/csv` and `Content-Disposition: attachment`, so the browser saves it as a file. Bytes are sent as they are produced, not held until the end.
- **Where state lives:** nothing. No export record and no file are created.
- **Time limit:** API servers stop any request that runs longer than 60 seconds. The whole stream must finish within that time.
- **If it fails:** an error before the first byte returns a normal error response. If the database fails, or the 60 seconds run out part-way through, the response simply stops. The browser then saves a partial file, and the user is not told. See open question 2.

### 4. Large report: create the record and queue the job

- **Starts when:** step 2 found more than 10,000 rows.
- **Steps:**
  1. Look for an active export (status `queued` or `running`) for this user and this report. If one exists, return it with HTTP 200 and stop. The response should say which filters that export uses.
  2. Insert a row with status `queued`, along with the filters and columns from the URL.
  3. Queue the `report_export` job with the payload `{"export_id": ...}`. The payload holds only the ID, far under the 64 KB limit. The job reads everything else from the row, because the page URL is not available when the job runs.
  4. Return HTTP 202 (accepted) with the export ID and status `queued`.
- **If it fails:**
  - If the insert breaks the unique index, another click won the race. Return that active export.
  - If queueing fails, set the row to `failed` in the same request and return an error. This stops the row from blocking the user.
  - If the process dies between steps 2 and 3, the row stays `queued` and blocks new exports. See open question 4.

### 5. The `report_export` job: build the file

- **Starts when:** a worker picks up the job. Each attempt starts from the beginning, because the queue keeps no progress between attempts.
- **Steps:**
  1. Load the row by `export_id`.
     - If it is `done` and `email_sent_at` is set, stop. This is a repeat run and the work is finished.
     - If it is `done` but `email_sent_at` is empty, the file is ready but the email was never sent. Skip to step 7.
  2. Set the status to `running`.
  3. If the row already holds an `upload_id` from an earlier attempt, abort that upload. This discards any parts it left behind.
  4. Start a multipart upload to the key `{report_id}/{export_id}.csv` in the exports bucket. Save the returned `upload_id` on the row.
  5. Write the header row into a buffer (a small in-memory holding area). Then repeat until no rows are left:
     - read the next 5,000 rows from the replica (keyset, with the same filters and columns);
     - encode them as CSV and add them to the buffer;
     - when the buffer reaches 5 MB, upload it as the next part and keep that part's ETag.

     When a read returns no rows, upload whatever is left in the buffer as the final part. The final part may be smaller than 5 MB; that is allowed.
  6. Complete the upload, passing the ETags in part order. The file now appears at its key, replacing any older file there. Save `object_key` and `row_count` on the row, and set the status to `done`.
  7. Create a signed link with `signed_url(bucket, key, 86400)`, which works for 24 hours. Send it to the user with `send_email(user_id, <download-ready template>, params)`. Then set `email_sent_at` on the row.
- **Memory:** at most one batch of rows and one 5 MB buffer are held at once, so about 10 MB at most, whatever the report size. The largest report (about 900 MB as CSV) needs about 180 parts, well under the limit of 10,000.
- **Where state lives:** the row (status, `upload_id`, `object_key`, `email_sent_at`) and the parts already uploaded to storage. Nothing is kept on the worker's disk.
- **If it fails** (an exception, the 30-minute timeout, or the worker dying): the queue waits 60 seconds and retries. The page keeps showing `running`. If the worker died, the upload may be left open. The next attempt aborts it in step 3, and the bucket discards it after 24 hours at the latest. Nothing half-written is visible, because the file appears only in step 6.
- **Time risk:** if one full run takes longer than 30 minutes, every attempt will be killed at the same point, and the export can never finish. Measure a run on the largest report before release. See open question 1.

### 6. Final failure: after the third attempt

- **Starts when:** the third attempt fails. The queue then calls the job's failure handler once.
- **Steps, in this order:**
  1. Abort the open upload, if there is one. Ignore any error here.
  2. Set the status to `failed` and save a short error message. This comes before the email, so an email failure cannot leave the row stuck at `running`.
  3. Send the failure email with `send_email` and the failure template.
- **If it fails:** if step 1 fails, the upload stays open, and the bucket discards it within 24 hours. If step 3 fails, the page still shows `failed`, because step 2 already saved that.

### 7. Show the status on the report page

- **Starts when:** the page loads, or the user clicks Download CSV.
- **Data:** `GET /api/reports/{report_id}/exports/latest` returns the user's most recent export for this report, with its status, error text and times. The endpoint checks `report.view`.
- **While queued or running:** the page asks again every 5 seconds and stops when the status is `done` or `failed`. Each request reads one row.
- **Coming back later:** the same request shows the latest state, so a user who closed the tab still sees `done` or `failed`.
- **When `done`:** the Download button calls `GET /api/exports/{export_id}/download`. This checks permission again and returns a new signed link valid for 24 hours. The emailed link expires after 24 hours, but the file itself lasts 7 days, so the page needs its own way to get a fresh link.
- **When `failed`:** show the error. The user clicks Download CSV again to start a new export.
- **If the status request fails:** the page retries on the next poll. The server state is unchanged.

### 8. Expiry and cleanup

- The bucket deletes each file 7 days after it was created, and discards open uploads after 24 hours. No cleanup job is built.
- After 7 days the row still says `done`, but the file is gone. The download endpoint must detect this and return a clear message such as "This export has expired. Please export again." The storage helpers have no existence check, so either one must be added, or the missing-file error must be caught and turned into that message.

## Open questions for review

1. **Job time.** Nobody has measured whether a 900 MB export finishes within 30 minutes. If it does not, the job cannot succeed as designed. Measure it on the largest report and plan a fix if needed.
2. **Partial small files.** A failed small export can save a partial file with no error message. Either build the whole small CSV in memory before sending it (this only bounds memory if row width is known), or accept the risk.
3. **Rebuild during a run.** The nightly rebuild can rewrite `report_rows` while a job is reading them, so the file could mix two versions of the data. Options: take a snapshot, or skip exports during the rebuild window.
4. **Rows stuck in `queued`.** If the process dies between steps 2 and 3 of step 4, the row blocks new exports. Options: a sweep that marks old `queued` rows as `failed`, or a timeout.
5. **Bearer links.** Anyone holding a 24-hour signed link can download the file without logging in. The permission check happens only when the link is made.
6. **Changed filters.** A click while an export is active returns the existing export, even if the URL filters have changed. The page should show which filters that export uses.
7. **Filtered small views.** `row_count` is the unfiltered total, so a filtered view of 50 rows from a 2-million-row report still takes the background path. This follows the brief, but it costs a job for a small download.