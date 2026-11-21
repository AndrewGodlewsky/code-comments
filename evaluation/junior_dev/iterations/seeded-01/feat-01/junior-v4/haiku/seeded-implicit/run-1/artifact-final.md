# CSV export plan

## What this is

Today the reports page loads rows through `GET /api/reports/{id}/rows`. The API checks `report.view`, reads rows from the read replica, and keeps no view state. Filters and column order live only in the page URL.

This plan adds a **Download CSV** button. A report of 10,000 rows or fewer returns its CSV in the click's response. A larger report is built by a background job. The job writes the CSV to the `exports` bucket and emails the user a link that works for 24 hours.

## Terms

- **Export:** one CSV request. A large export has one row in `report_exports`.
- **Job:** work the job queue runs outside the request.
- **Attempt:** one run of a job. A job gets at most 3 attempts. Each attempt has 512 MB of memory and 30 minutes to finish.
- **Owner:** the job id that claimed an export. Every attempt of one job has the same job id.
- **Replica:** a read-only copy of the database. Report rows are read only from it.
- **Multipart upload:** a file sent in parts. Nothing is visible at its key until the upload is completed.
- **Signed link:** a download URL that stops working after a set time.

## Steps

1. **Choose the path.**
   - Starts: the user clicks Download CSV.
   - Does: the page sends `POST /api/reports/{id}/exports` with the filters and columns from the URL. The API checks `report.view`, then reads `reports.row_count` from the replica. At 10,000 or fewer, go to step 2. Above 10,000, go to step 3.
   - Keeps: nothing.
   - If it fails: no `report.view` gives 403. Nothing is stored, so the user can click again.

2. **Small report: return the CSV.**
   - Starts: step 1 chose the small path.
   - Does: the API writes the header row, then reads rows from the replica in batches of 500, in `row_id` order. The response body is the CSV, with status 200. The page saves it as a file.
   - Keeps: nothing.
   - If it fails: the download is incomplete. Nothing is stored, so the user clicks again.

3. **Large report: create the export and queue the job.**
   - Starts: step 1 chose the large path.
   - Does: inserts a `report_exports` row on the primary database with status `queued`, the user, the report, the filters and the columns. Then enqueues `report_export` with payload `{export_id}` only. Returns 202 with the export id and status.
   - Keeps: the row, on the primary database.
   - One at a time: a partial unique index on (user, report) for statuses `queued` or `running` blocks a second insert. If the insert hits that index, the API returns the existing export.
   - Crash repair: if the returned export is still `queued`, the API enqueues `report_export` for it again. This covers a crash between the insert and the first enqueue. The extra job may also run, and step 4 makes sure only one job does the work.
   - If it fails: if the enqueue call fails, the row is set to `failed` with the error, and the API returns an error.

4. **Job starts (each attempt).**
   - Starts: the queue runs `report_export` with the export id.
   - Does, in order:
     1. Load the row. If the status is `done` or `failed`, stop.
     2. Check `report.view` for the row's user again. Permission may have changed while the job waited.
     3. Claim the export with one conditional update. Set status `running` and owner to this job's id, only if the owner is empty or already this job's id, and the status is `queued` or `running`. If no row changed, another job owns the export, so stop.
   - Keeps: the status and owner on the row.
   - If it fails: a failed check raises an error, which fails the attempt. The queue retries it (step 7). A user who lost access gets all 3 attempts, about 6 minutes, and then the failure email.

5. **Job writes the file.**
   - Starts: step 4 claimed the export.
   - Does: starts a multipart upload to `exports/{export_id}/attempt-{n}.csv`, where `n` is this attempt's number, so each attempt writes its own file. Writes the header. Reads rows from the replica in batches of 500, by `row_id`, never with OFFSET. Sends a part each time the buffer reaches 5 MB. The largest report needs about 180 parts.
   - Keeps: one batch and one part in memory. The file is invisible until step 6.
   - If it fails: an error aborts the upload. A timeout or a dead worker cannot run the abort. The stray upload stays invisible, and the bucket's lifecycle rule discards it after 24 hours.

6. **Job finishes.**
   - Starts: the last batch is written.
   - Does, in this order:
     1. Completes the upload. The file becomes visible at its key.
     2. Creates a signed link valid for 86,400 seconds.
     3. Calls `send_email(user_id, template, {link})`.
     4. Sets status `done`, and records `object_key` and `finished_at`.
   - Keeps: the file in the `exports` bucket. The status, key and time on the row.
   - If it fails: any failure before step 4 ends the attempt, and step 7 retries the whole export. This assumes `send_email` raises on failure. A retry after a lost write can send the email twice. A retry never replaces an earlier file, because each attempt writes its own file.

7. **Retries and final failure.**
   - Starts: an attempt fails by error, timeout or dead worker.
   - Does: the queue waits 60 seconds, then 300 seconds, and runs step 4 again from the start with the same export id. That is 3 attempts in total. The status stays `running` between attempts. After the third failure, the queue calls the failure handler once. The handler sets status `failed` with the error text and emails the user that the export failed.
   - Keeps: no progress between attempts. Each attempt makes its own upload and file.
   - If it fails: until the queue notices a dead worker, the export stays `running`. If the failure handler's email fails, see open questions.

8. **Page shows status.**
   - Starts: the user opens the report page, or starts a large export.
   - Does: on load, the page calls `GET /api/reports/{id}/exports/latest` for the user's latest export of this report. While the status is `queued` or `running`, it polls `GET /api/reports/{id}/exports/{export_id}` until the status is `done` or `failed`. Both calls check `report.view` and that the export belongs to the user. The status is read from the primary, so it is current.
   - Shows:
     - `queued`: "Queued." Download CSV is disabled.
     - `running`: "Building the file." Download CSV is disabled.
     - `done`: "Done. The link was emailed to you." Download CSV starts a new export.
     - `failed`: "Failed: " and the error text. Download CSV starts a new export.
   - Keeps: nothing in the browser.
   - If it fails: a failed poll keeps the last state shown, and the next poll tries again.

Cleanup is not a job. The bucket deletes each file 7 days after it was created. Each link stops working 24 hours after it was sent.

## Open questions

- The threshold uses the unfiltered row count. A filter that leaves 50 rows of a 2-million-row report still takes the job path. A second export with other filters returns the running one. Confirm this is wanted.
- The done state has no download link. If the email is lost or the link has expired, the user can only click Download CSV again to make a new file.
- Speed is not measured. Two million rows in 1,800 seconds needs about 1,100 rows per second. It is also not known whether 10,000 rows finish within the API's 60-second limit.
- A nightly rebuild could change rows during a long export. It is not known whether the rebuild can run then.
- How far the replica can lag is not known.
- How the queue notices a dead worker, how long that takes, and where the queue keeps its jobs are not stated.
- Whether `send_email` returns before the email is sent, and whether it raises on failure, is not stated.
- Whether the queue retries the failure handler if the handler's own email fails is not known.
- The email template name and content are not chosen.