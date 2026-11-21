# Plan: Download CSV on the reports page

## Summary

Clicking **Download CSV** calls one new endpoint. It checks permission and reads `reports.row_count`.

- **10,000 rows or fewer:** the response is the CSV, built from the read replica. Nothing is stored.
- **More than 10,000 rows:** the endpoint records an export row and enqueues a background job. It returns at once.
- **The job:** it streams rows from the replica, writes them to the `exports` bucket as a multipart upload, then emails a 24-hour link.
- **Status:** the page reads the export row to show queued, running, done or failed.

New pieces:

- A `report_exports` table.
- Three endpoints.
- One job, `export_report_csv`.
- Two email templates, `export_ready` and `export_failed`.
- A small UI change.

Existing pieces we rely on (all described in the three files in `existing/`):

- The reports rows API and its keyset paging.
- `jobs.py`: `job`, `enqueue`, and the 3-attempt retry policy.
- `storage.py`: multipart upload and `signed_url`.
- The bucket's 7-day delete rule.

## Facts from the existing code that shape the design

- Report rows come only from the read replica, paged by `row_id` (`row_id > after ORDER BY row_id`), never by OFFSET.
- API requests die at 60 seconds.
- A job attempt dies at 1800 seconds and has 512 MB of memory. The queue keeps no progress between attempts, and each attempt restarts from the beginning.
- Delivery is at least once, so the handler must tolerate being run again.
- Nothing is visible in the bucket at a key until `complete_multipart` succeeds.
- Every part except the last must be at least 5 MB. A file can have at most 10,000 parts.
- `signed_url` allows at most 86,400 seconds.
- The server stores nothing about what the user is viewing. Filters and columns exist only in the page URL, so the click must send them.

## Steps

### 1. Add the `report_exports` table (one-time migration)

- **Starts it:** deploy.
- **Data moves:** none.
- **State kept:**
  - A new table on the primary database. It holds export bookkeeping, not report data, so the rule against reading report data from the primary does not apply.
  - Columns:
    - `export_id` (uuid, primary key)
    - `user_id`
    - `report_id`
    - `filters` and `cols` (the raw values from the click, stored as text)
    - `status` (`queued`, `running`, `done` or `failed`)
    - `job_id`
    - `attempt`
    - `error` (short text)
    - `file_key`
    - `created_at`, `started_at`, `finished_at`
    - `emailed_at`
  - **Partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')`. This enforces "one large export at a time". Done and failed rows fall out of the index, so they never block a new export.
  - Plain index on `(user_id, report_id, created_at DESC)` for the status lookup.
- **If it fails:** the migration fails and nothing ships. Nothing else depends on it yet.

### 2. Click: `POST /api/reports/{report_id}/exports`

- **Starts it:** the user clicks Download CSV.
- **Data moves:** the browser sends `filters` and `cols` exactly as they appear in the page URL. The page sends them, because the server does not remember what the user is looking at.
- **Checks, in order:**
  1. The caller must have `report.view` on the report's workspace. Use the same check as the rows API, and return 403 otherwise.
  2. Validate `cols` and `filters` with the same parser the rows API uses, so the CSV matches the table. If they are invalid, return 400.
  3. Read `reports.row_count` for this report. Read it from the replica, to stay clear of the primary rule. It is rewritten only nightly, so the value is stable during the day.
  4. If `row_count <= 10000`, go to step 3. Otherwise go to step 4.
- **State kept:** none at this step.
- **If it fails:**
  - Permission: 403.
  - Bad input: 400.
  - Replica or database unreachable: 500, and the user can click again. Nothing has been created yet.
- **Frontend:** call it with `fetch`.
  - If the response is `text/csv`, save it as a file.
  - If it is JSON (`202`), show the export state from step 5.

### 3. Small path (`row_count <= 10,000`): the response is the CSV

- **Starts it:** step 2 chose the small path.
- **Data moves:**
  1. Write the header row first, using the column names in `cols` order.
  2. Read rows from the replica with the existing keyset query: `row_id > after ORDER BY row_id LIMIT 500`.
     - Start with `after` set to zero.
     - Set `after` to the last `row_id` of each page.
     - Stop on a short page.
  3. Encode each page with a real CSV writer (`csv` module) so commas, quotes and newlines in cells are escaped.
  4. Collect everything in memory. At the current average of about 450 bytes per row, 10,000 rows is roughly 4.5 MB. At most 20 queries are needed, far inside the 60-second limit.
  5. Send the complete body as `200 text/csv` with `Content-Disposition: attachment; filename=report-{id}.csv` and a `Content-Length`.
- **State kept:** none. No export row, no job, no stored file.
- **If it fails:**
  - Any error before the body is sent returns 500 with no file.
  - The body is built fully before sending, so a failure can never produce a half-finished CSV download.
  - If the request exceeds the 60-second kill, the user gets an error. They click again.
- **Note:** `row_count` is the unfiltered total. A heavily filtered view of a big report still takes the large path. That follows the rule as specified.

### 4. Large path (`row_count > 10,000`): claim the slot, then enqueue

- **Starts it:** step 2 chose the large path.
- **Data moves and order:**
  1. Generate a new `export_id`.
  2. On the primary, run `INSERT INTO report_exports (...status='queued') ... ON CONFLICT DO NOTHING`. The partial unique index makes this the lock.
  3. **If the insert was skipped,** this user already has a queued or running export of this report. Select that row and return it as `202` with its `export_id`, `status`, `filters` and `cols`. No second export starts. The existing export may have different filters from this click, so the page shows which view it covers. Different filters do not allow a second concurrent export.
  4. **If the insert succeeded,** call `enqueue("export_report_csv", payload)`.
     - The payload contains `export_id`, `user_id`, `report_id`, `filters` and `cols`.
     - It is well under the 64 KB limit.
     - Do not put rows in the payload.
  5. Save the returned `job_id` on the row and return `202` with the export row.
- **State kept:** the `report_exports` row (`queued`, with `job_id`).
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` (error `could not enqueue`) so it doesn't block the user, and return 500. The user can click again.
  - If the API process dies between the insert and the enqueue, the row stays `queued` with `job_id` NULL. The next click finds it through the conflict path in item 3. If `job_id` is NULL and the row is more than 2 minutes old, that click re-enqueues with the same `export_id` and saves the `job_id`. This is safe because the handler tolerates duplicates (step 6).

### 5. Status on the page

- **Starts it:**
  - Page load.
  - A `202` from step 2 or 4.
  - A 5-second poll timer, while the status is `queued` or `running`.
- **Data moves:**
  - `GET /api/reports/{report_id}/exports/latest` returns this user's newest export row for this report: `status`, `created_at`, `finished_at`, and the filters it covers. It returns 404 if there is none.
  - It applies the same `report.view` check, so a user whose access is revoked gets 403.
  - It reads the primary, because the replica could lag right after a click and show nothing. This is bookkeeping data, not report data.
- **State kept:** none new. The row from step 4 is the single source of truth, and it survives navigation and returning later.
- **What the page shows:**
  - `queued` or `running`: the button is disabled and a "queued" or "running" label is shown. Polling continues.
  - `done`: "done, link was emailed to you". The page does not mint new links. If someone wants a re-download button, that needs a decision, because the file is deleted after 7 days.
  - `failed`: "failed", and the button works again.
- **If it fails:** a failed poll leaves the last known state on screen and retries on the next tick. Polling stops when the state is `done` or `failed`.

### 6. Job start: `export_report_csv(ctx, payload)`, registered with `@job("export_report_csv", on_final_failure=...)`

- **Starts it:** the queue calls the handler, for attempt 1, 2 or 3. Duplicate delivery is also possible.
- **Data moves:** load the export row by `export_id`.
- **Guards, to make repeated runs safe:**
  - Status `failed`: return. The final-failure path already handled it.
  - Status `done` and `emailed_at` set: return. This is a duplicate delivery, and the user already has the email.
  - Status `done` and `emailed_at` NULL: the file is already complete. Skip to step 8 (send the email only). Do not rebuild.
  - Otherwise set `status='running'`, `attempt=ctx.attempt`, and `started_at` (first attempt only).
- **State kept:** the row update. The status stays `running` through the backoff gaps between attempts, and the page shows running.
- **If it fails:** an exception here is a normal failed attempt, and the queue retries it per step 9.
- **Key choice:** the object key is deterministic, `exports/{report_id}/{export_id}.csv`. A rerun that gets as far as completing writes to the same key. `complete_multipart` replaces any existing object, so this is harmless.

### 7. Job body: stream rows into a multipart upload (never hold the report)

- **Starts it:** step 6 passed the guards.
- **Data moves, in this loop:**
  1. Call `start_multipart("exports", key)` and keep the `upload_id`.
  2. Start an in-memory byte buffer and write the header row, with columns in the `cols` order from the payload.
  3. Fetch a page from the **read replica**: the same filters as the page, `row_id > after ORDER BY row_id LIMIT 5000`, with `after` starting at 0.
     - Use a plain keyset query per page, each on its own short query. Do not hold a cursor or transaction open for 30 minutes, which the replica may cancel.
     - 5,000 rows is about 2.3 MB. That is far larger than the 500-row page the UI uses, which is fine since there is no 60-second limit here. It cuts the largest report to about 400 queries.
  4. Encode the page with the CSV writer into the buffer.
  5. When the buffer reaches **8 MiB** (above the 5 MB minimum), call `upload_part(upload_id, n, bytes)`, record `(n, etag)`, and **empty the buffer**.
  6. Set `after` to the page's last `row_id`. Stop on a short page.
  7. After the loop, upload whatever remains in the buffer as the last part. The header guarantees there is always at least one part, even for zero rows. The last part may be under 5 MB.
- **Memory:** about 8 MiB buffer plus one page (about 2.3 MB), plus the list of etags. That is roughly 20 MB for the largest report, against a 512 MB limit. The part count for 900 MB is about 113, far under 10,000.
- **Time:**
  - The limit is 1800 seconds. The largest report needs 2,000,000 rows in that time, which is about 1,100 rows per second at minimum.
  - Add a deadline check: before each page, if the elapsed time is over 1,650 seconds, abort and raise a clear error. This avoids being killed mid-upload.
  - Retrying a job that is too slow will not help, because each attempt restarts from zero and will hit the same limit. The measurement in step 11 must show real headroom before launch.
- **State kept:**
  - The in-progress upload exists only in storage, invisible at the key. Nothing is in the database yet.
  - Nothing is saved between attempts, which matches the queue's behaviour.
- **If it fails:**
  - On any exception (replica error, storage error, the deadline), call `abort_multipart(upload_id)` and re-raise. The queue then retries.
  - If the worker dies or is killed, the upload cannot be aborted. The bucket rule discards incomplete uploads after 24 hours. That is accepted, and no cleanup job is written.
  - Because nothing is visible until step 8, a half-written file can never be downloaded.
- **Known tradeoff:** the nightly rebuild rewrites report data. A job running across it could read some old and some new rows, since rows are not locked. This is accepted. It affects only exports started near the rebuild.

### 8. Finish: publish the file, mark done, email the link

- **Starts it:** the loop in step 7 ended without error (or step 6 jumped here).
- **Data moves, in this order:**
  1. `complete_multipart(upload_id, etags)`. Only now does the object become visible at `file_key`.
  2. On the primary, update the row to `status='done'`, `file_key`, `finished_at`.
  3. `signed_url("exports", file_key, 86400)`. Generate it now, at send time, so the 24 hours start when the email is sent.
  4. Look up the user's address through `send_email(user_id, "export_ready", {report_name, download_url, expires_at})`. The `export_ready` template is new, and its text needs to be written and approved.
  5. Set `emailed_at`.
- **State kept:** the `done` row, the finished object in the bucket, and `emailed_at`.
- **If it fails:**
  - `complete_multipart` fails: treat it as an attempt failure (step 7 rules). The upload is aborted and the attempt is retried.
  - Marking done fails: attempt failure. A rerun rebuilds, and `complete_multipart` replaces the object at the same key.
  - Email fails after `done` was saved: the attempt fails, and the retry sees `done` with `emailed_at` NULL and only resends the email (step 6). This avoids a rebuild.
  - A crash between sending the email and writing `emailed_at` could send a second email. This is the accepted cost of at-least-once delivery.
- **File lifetime:** the link works for 24 hours. The bucket's rule deletes the object after 7 days. We do nothing about either.

### 9. Failure: retries and the final failure

- **Starts it:** an attempt raises, times out at 1800 seconds, or its worker dies.
- **Data moves:**
  - The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3, for 3 attempts in total. We add no retry logic of our own.
  - After the third failure the queue calls `on_final_failure(ctx, payload, error)` once:
    1. Update the row to `status='failed'` with a short `error` and `finished_at`. Do this first, so the page is correct even if the email fails.
    2. Call `send_email(user_id, "export_failed", {report_name})`. The `export_failed` template is new. Wrap it in a try/except that logs the failure. Never raise from here.
- **State kept:** the `failed` row. A failed row is terminal and is not counted in the unique index, so the user can start a new export at once.
- **If it fails:** if the failure email can't be sent, the user still sees "failed" on the page. If the final-failure hook itself can't update the row, the row stays `running`, which blocks new exports. Alert on a `running` row older than 6 hours. The worst case is the 3 attempts at 30 minutes plus 6 minutes of backoff, about 5.1 hours.

### 10. Cleanup: nothing to build

- **Starts it:** the bucket's own rules, not our code.
- **Data moves:** the bucket deletes each object 7 days after creation. It discards uploads not completed within 24 hours.
- **State kept:** `report_exports` rows stay as a small history. After 7 days a `done` row has no file behind it.
- **If it fails:** nothing of ours can fail here. We add no cleanup job.

### 11. Verify before shipping

- **Starts it:** feature complete, before enabling it for users.
- **What to check:**
  1. **Timing.**
     - Run the job on the largest report (about 2 million rows) against the production replica.
     - Record total time, peak memory and part count.
     - Pass only if it finishes in about a third of 1800 seconds or less, so slower days still fit.
     - If it doesn't, stop and rework before launch. Options are a larger page size or an index review.
  2. **Memory.** Peak stays well under 512 MB while the file written is about 900 MB.
  3. **Row-count boundary.** Test 10,000 rows (small path) and 10,001 (job).
  4. **Double click.** Two clicks give one export and one job, and the second click gets the first one back. Test two simultaneous requests too.
  5. **Failure injection.**
     - Fail the job mid-stream and confirm no object appears at the key.
     - Fail all three attempts and confirm the page shows failed and the failure email is sent.
     - Re-run a finished job and confirm no second email.
  6. **Permission.** A user without `report.view` gets 403 from all three endpoints.
  7. **Contents.** The CSV filters and column order match the page URL, with escaped commas, quotes and newlines, and a header row.

## Assumptions and open questions

- **Different filters, same report.** One large export per user per report means a second click with different filters returns the first export. That follows the rule as written. Confirm this is what the product wants.
- **Email templates.** `send_email` exists, but the `export_ready` and `export_failed` templates probably don't. Copy needs sign-off.
- **Re-download.** The page shows "done" but not a download link. The only link is the one emailed, valid for 24 hours. A "get a new link" button is out of this plan.
- **Spreadsheet formula cells.** Cells beginning with `=`, `+`, `-` or `@` can run as formulas when opened in Excel. Escaping them changes the data. This plan writes values as they are. Decide whether to escape them.
