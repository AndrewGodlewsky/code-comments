# CSV export plan

This plan adds a **Download CSV** button to the reports page. Small reports download directly in the click response. Large reports are built by a background job, and the user is emailed a download link.

## Background: the existing system this plan relies on

- **Reading rows.** Report rows are read only from the read replica, never from the primary database.
  - The API fetches rows in `row_id` order, 500 at a time. Each query asks for `row_id > after`, where `after` is the last `row_id` already seen. This is called keyset paging.
  - API requests are killed after 60 seconds.
- **Row count.** `reports.row_count` is the total, unfiltered number of rows in a report. The largest report has about 2 million rows, roughly 900 MB as CSV.
- **Job queue.** `enqueue(name, payload)` returns a `job_id` and runs a handler on a worker with 512 MB of memory.
  - An attempt fails if the handler raises, runs past the 30-minute timeout, or its worker dies.
  - A job is tried at most 3 times, waiting 60 s before attempt 2 and 300 s before attempt 3.
  - Each attempt restarts the handler from the beginning with the same payload. The queue keeps no progress between attempts.
  - Delivery is at least once, so a handler may run again after it has already succeeded. Handlers must tolerate that.
  - `on_final_failure` runs once, after the last attempt has failed.
- **Object storage.** A multipart upload sends a file in parts.
  - Nothing is visible at the object's key until `complete_multipart` succeeds.
  - Every part except the last must be at least 5 MB. A file may have at most 10,000 parts.
  - The `exports` bucket deletes objects 7 days after creation and discards uploads not completed within 24 hours.
- **Permission.** Both the page and the export use the `report.view` permission on the report's workspace.

## What this plan adds

One new table, `report_exports`, in the primary database. It holds export bookkeeping, not report data, so the rule "never read report data from the primary" does not apply to it. Status reads go to the primary, because replica lag could show a stale status.

## The plan

### 1. Create the `report_exports` table
- **Starts it:** a one-time migration.
- **Columns:**
  - `export_id` (primary key)
  - `report_id`, `user_id`
  - `filters`, `cols`: the view the user was looking at
  - `status`: `queued`, `running`, `done` or `failed`
  - `job_id`, `object_key`, `error`
  - `emailed_at`: set once the success email is sent
  - `created_at`, `updated_at`
- **Duplicate guard:** a partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')`. The database then enforces "one active large export per user per report", even if two clicks arrive together.
- **If it fails:** the migration fails and nothing ships.

### 2. The click: `POST /api/reports/{report_id}/exports`
- **Starts it:** the user clicks **Download CSV**. The page sends the `filters` and `cols` from its current URL in the request body.
- **What happens:**
  1. Check `report.view` on the report's workspace. Return 403 if the user lacks it, as the rows API does.
  2. Read `reports.row_count` from the replica. It is the unfiltered total, so a filtered export can only be smaller. That is fine, because the size threshold is defined on `row_count`.
  3. If it is 10,000 or fewer, go to step 3. Otherwise go to step 4.
- **State:** none yet.
- **If it fails:** return an error, which the page shows. Nothing has been created.

### 3. Small report (10,000 rows or fewer): the response is the CSV
- **Starts it:** step 2.
- **Data moves:**
  1. The API request handler writes the header row, built from `cols`.
  2. It reads rows from the replica 500 at a time with keyset paging, applying `filters`.
  3. It streams each page into the HTTP response as `text/csv` with a download filename.
- **State:** none. No job runs, nothing is stored, and no `report_exports` row is written.
- **If it fails:** 10,000 rows is about 20 queries, well under the 60 s limit. If a query fails or the connection drops mid-stream, the browser gets a broken download and the user can click again. Nothing needs cleanup.

### 4. Large report (over 10,000 rows): create or reuse an export, then queue the job
- **Starts it:** step 2.
- **What happens:**
  1. Insert a `report_exports` row with status `queued`, plus `report_id`, `user_id`, `filters` and `cols`.
  2. If the insert violates the unique index, the user already has an active export of this report. Return that existing export and stop. No second job starts. This applies even if the new request has different filters.
  3. Otherwise call `enqueue("report_export", {"export_id": ...})`. The payload holds only the id, because the filters and columns are in the table. This keeps it far below the 64 KB limit.
  4. Save the returned `job_id` on the row.
  5. Respond immediately with `202`, the `export_id` and the `status`.
- **State:** the `report_exports` row.
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` so the unique index stops blocking the user, and return an error. The user can click again.
  - A crash between the insert and the enqueue leaves a `queued` row with no job, which blocks that user from exporting that report. The plan has no sweeper for this, so it needs an explicit decision (see "Open points").

### 5. The job: `report_export(ctx, payload)`
- **Starts it:** the queue runs it on a worker, once per attempt. Every attempt starts from scratch.
- **Opening checks, in order:**
  1. Load the export row.
  2. If its status is `failed`, return. This is a late duplicate delivery after the final failure.
  3. If its status is `done` and `emailed_at` is set, return. This handles at-least-once delivery.
  4. If its status is `done` but `emailed_at` is empty, an earlier attempt finished the file but failed to send the email. Skip to build step 7.
  5. Otherwise set the status to `running`. It stays `running` across retries.
- **Building the file.** These rules keep memory low and the file safe:
  1. Call `start_multipart("exports", key)`, where `key` is derived from `export_id` (for example `report-exports/{export_id}.csv`). Keep the returned `upload_id`.
  2. Write the header row, then loop over keyset pages from the replica (`row_id > after`, using `filters` and `cols`). Use pages larger than the page's 500, for example 5,000. That is about 400 queries for 2 million rows instead of 4,000.
  3. Append each page's CSV text to an in-memory buffer. When the buffer reaches about 8 MB (above the 5 MB minimum part size), call `upload_part`, keep the returned etag, and empty the buffer.
  4. At any moment memory holds one page, one buffer and a list of etags: a few tens of MB, however large the report is. The largest report (about 900 MB) is roughly 110 parts, far below the 10,000-part limit.
  5. When the rows run out, upload the final buffer as the last part, then call `complete_multipart`. Only now does the file appear at `key`, so a half-written file can never be downloaded.
  6. Set the status to `done` and save `object_key`.
  7. Create a link with `signed_url("exports", key, 86_400)`, valid for 24 hours. Send it with `send_email(user_id, "export_ready", {link, report name})`. Then set `emailed_at`. On a retry that skipped here from opening check 4, the link is created fresh, so it is valid for 24 hours from now.
- **State:** progress exists only in the attempt's memory and in the upload's parts. A retry starts over with a new upload.
- **If it fails:**
  - If the handler raises, call `abort_multipart(upload_id)` and re-raise. The queue then retries after 60 s, and after another 300 s if the second attempt also fails.
  - If an attempt times out or its worker dies, the handler cannot clean up. The unfinished upload is invisible and the bucket discards it after 24 hours. No cleanup job is needed.
  - If the email call fails after the file is complete, the handler raises. The retry sends only the email (opening check 4) and does not rebuild the file.
- **Timeout risk, needs a test.** The 30-minute limit applies to each whole attempt, and retries do not resume. Before launch, export the largest report (about 2 million rows) in a staging environment and record the time. If it takes more than about 15 minutes, change the approach before shipping. Otherwise a slow report would time out on all three attempts in turn.

### 6. Final failure
- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.
- **What happens:**
  1. Load the export row. If its status is already `done` (only the email failed), leave it as `done` and log the error. Do not mark a finished export as failed.
  2. Otherwise set the status to `failed` and store a short `error`. This also frees the unique index, so the user can start a new export.
  3. Send the user a failure email with `send_email(user_id, "export_failed", {report name})`.
- **State:** the `report_exports` row.
- **If it fails:** the status is set before the email is sent. If the email call fails, the page still shows `failed`, which matters most. Log the email error.

### 7. Status on the page
- **Starts it:** two triggers.
  - The user loads `/reports/{report_id}`.
  - The user clicks the button and gets a `202` back.
- **Data moves:**
  - A new endpoint, `GET /api/reports/{report_id}/exports/latest`, applies the same `report.view` check. It returns the current user's most recent export of that report (status, timestamps, error), read from the primary.
  - The page shows the status: `queued`, `running`, `done` or `failed`.
  - While the status is `queued` or `running`, the page polls every few seconds. It stops on `done` or `failed`.
  - The lookup runs on every page load, so a user who returns later sees the current state.
- **State:** the `report_exports` row, which is the single source of truth.
- **If it fails:** a failed poll leaves the last known status on screen and retries on the next tick. It never changes the export.

### 8. Cleanup
- **Starts it:** the bucket's existing lifecycle rule, not this plan.
- **What happens:** objects are deleted 7 days after creation, and unfinished uploads are discarded after 24 hours.
- **What this plan builds:** nothing. There is no cleanup job. Old `report_exports` rows stay as history.

## Open points to confirm
- **Orphaned `queued` rows (step 4).** Decide whether a rare crash between insert and enqueue is acceptable, or whether to add a cheap check, such as treating a `queued` row older than an hour as failed.
- **Expired downloads.** The emailed link lasts 24 hours and the file lasts 7 days. The page shows `done` but offers no download link, and after 7 days no file exists. Decide what the page should show or offer.
- **Nightly rebuild.** If the report data is rebuilt while a large export is running, the export may mix old and new rows. Decide whether that is acceptable.
