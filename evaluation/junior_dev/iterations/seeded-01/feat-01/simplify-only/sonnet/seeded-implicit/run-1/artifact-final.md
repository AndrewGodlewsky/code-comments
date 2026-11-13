# CSV export plan

A **Download CSV** button on the reports page. Small reports come back as the response to the click, with nothing stored. Large reports are built by a background job, saved in object storage, and linked by email. The page shows the state of a large export.

Today, the page at `/reports/{report_id}` loads rows from `GET /api/reports/{report_id}/rows` in pages of 500. The API checks the `report.view` permission and reads from the read replica. It pages by `row_id` (`row_id > after ORDER BY row_id`), never by OFFSET. Filters and column order live only in the page URL, and the server stores nothing about them.

## Terms

- **Read replica**: the database copy that all report rows must be read from. Never read report rows from the primary.
- **Large report**: one where `reports.row_count` is above 10,000. That count is the unfiltered total and is rebuilt each night. A filtered export of a large report still takes the large path.
- **Export record**: a row in a new `report_exports` table. It holds the export id, user, report, the filters and columns from the page URL, a state (`queued`, `running`, `done` or `failed`), and its creation time. This table is not report data, so it lives in the primary database.
- **Job**: a background task on the existing queue. It gets a payload, which here is only the export id. It is tried at most 3 times, an attempt is killed after 30 minutes, and each retry starts from the beginning. A job may occasionally run again after it has succeeded.
- **Multipart upload**: how a big file is written to the `exports` bucket in parts of at least 5 MB. Nothing is visible at the file's name until the upload is completed. An aborted upload leaves nothing behind.

## How it runs

### 1. The user clicks Download CSV
- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/exports` with the current URL's filters and column order.
- **What it does:** checks `report.view` on the report's workspace and returns 403 if the user lacks it. Then reads `reports.row_count` and picks a path.
- **Data kept in:** nothing yet.
- **If it fails:** a normal error response. The user can click again.

### 2a. Small report (10,000 rows or fewer)
- **Starts it:** step 1.
- **What it does:** writes a header row, then streams rows from the read replica 500 at a time using the `row_id` paging above, using the requested filters and columns. The response is the CSV, sent as a file download.
- **Data kept in:** nothing. No record, no job, no stored file.
- **If it fails:** the response breaks off and the browser shows a failed download. The user can click again. This takes well under the API's 60-second request limit.

### 2b. Large report (above 10,000 rows)
- **Starts it:** step 1.
- **What it does:**
  1. Tries to insert an export record in state `queued`. A unique rule allows only one record per user and report in state `queued` or `running`. If one already exists, the API returns that record and stops, so a second click never starts a second export.
  2. Enqueues a `report_export` job with the export id as the payload.
  3. Returns the record straight away.
- **Data kept in:** the export record, in the primary database.
- **If it fails:** if the insert fails, the user gets an error and no job exists. If enqueueing fails, the API marks the record `failed` so it does not block later clicks, and returns an error.

### 3. The job builds the file
- **Starts it:** the queue, for each attempt.
- **What it does:**
  1. Loads the export record. If it is already `done`, the job stops, because this is a repeat delivery.
  2. Sets the state to `running`.
  3. Starts a multipart upload to the `exports` bucket. The file name is fixed from the export id, so a retry writes to the same name.
  4. Reads rows from the read replica in `row_id` order, a few thousand per query, and writes the header and rows as CSV. It keeps one part (about 8 MB) in memory at a time and uploads it when full. It never holds more, so a 2-million-row report (about 900 MB) fits in the worker's 512 MB.
  5. Completes the upload, which makes the whole file visible at once.
- **Data kept in:** the upload parts in the bucket, until completed. The state in the export record.
- **If it fails:** the job aborts the upload and raises, and the queue retries after 60 seconds, then after 300 seconds. The state stays `running` between attempts. A half-written file is never visible, because nothing appears until the upload completes.

### 4. The user is told
- **Starts it:** the job after step 3 succeeds.
- **What it does:** creates a download link that works for 24 hours (the storage maximum), sends it with `send_email(user_id, "report_export_ready", params)`, then sets the state to `done`.
- **Data kept in:** the file in the bucket, deleted by the bucket's existing 7-day rule. There is no cleanup job. The export record stays.
- **If it fails:** if the email call raises, the attempt fails and the whole job retries. A retry rebuilds the file and replaces the old one. A rare repeat email is accepted.

### 5. The page shows the state
- **Starts it:** the page loading, or a poll every 5 seconds while the state is `queued` or `running`.
- **What it does:** calls `GET /api/reports/{report_id}/exports/latest`, which checks `report.view` and returns the signed-in user's newest export of this report. The page shows its state: queued, running, done or failed. This is how the user sees the state when they come back later. The page shows no download link, because the link is in the email.
- **Data kept in:** the export record.
- **If it fails:** the page keeps the last state it showed and tries again on the next poll.

### 6. The last attempt fails
- **Starts it:** the queue calls the job's final-failure handler once, after attempt 3 fails.
- **What it does:** sets the state to `failed`, which also lets the user start a new export. Then sends `send_email(user_id, "report_export_failed", params)`.
- **Data kept in:** the export record.
- **If it fails:** the failure is logged and the user may not be emailed. The page still shows `failed` once the state is set.

## What happens when other things fail

| Case | Result |
|---|---|
| Worker dies or the 30-minute timeout kills an attempt | Counts as a failed attempt and is retried. The open upload cannot be aborted, so the bucket discards it after 24 hours. |
| Job delivered twice | The second run sees `done` and stops. If the first run has not finished yet, both write the same file name and the last completed upload wins. |
| User clicks again during a large export | Gets the existing export back (step 2b). |
| Export finished earlier | State is `done`, so the next click starts a fresh export. |

## How to build it

1. Add the `report_exports` table with the unique rule on user and report for states `queued` and `running`.
2. Add the POST endpoint with the permission check and the small path.
3. Add the large path, the job and its final-failure handler, and the two email templates.
4. Add the GET endpoint and the page status display.
5. Test with the 2-million-row report. Check the worker's peak memory and that an attempt finishes within 30 minutes.

## Open questions

- Can the job read 2 million rows and upload 900 MB inside 30 minutes? This is unmeasured; step 5 of the build checks it. The batch size may need tuning.
- Do the `report_export_ready` and `report_export_failed` email templates exist? If not, they need writing.
- Should the job re-check `report.view` when it runs? The plan checks it only at the click.
- The export is a snapshot of whatever the replica holds as it reads. If the nightly rebuild runs during a long export, the file could mix old and new rows. This is not handled.
- If the final-failure handler itself crashes, the record may stay `running` and block new exports.