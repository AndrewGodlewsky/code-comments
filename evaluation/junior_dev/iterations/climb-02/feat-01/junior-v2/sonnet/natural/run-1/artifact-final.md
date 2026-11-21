# Plan: CSV export for the reports page

## Read this first

**Terms**
- **Small export**: `reports.row_count` is 10,000 or less. The click response is the CSV.
- **Large export**: `row_count` is above 10,000. A background job builds the file.
- **Replica**: the read replica. Report rows (`report_rows`) are read only from there, never from the primary database.
- **Export row**: a record in a new `report_exports` table on the primary database. It holds export state, not report data, so the primary is fine. Reads of it also go to the primary, so replica lag never shows a stale state or allows a duplicate.

**Facts about the existing system that drive the design**
- Rows are paged by keyset: `row_id > after ORDER BY row_id`. Never use OFFSET.
- API requests are killed after 60 seconds.
- Workers have 512 MB. The queue gives each job 3 attempts, with waits of 60 s and 300 s before attempts 2 and 3. Each attempt is killed after 30 min and restarts from scratch with the same payload. Delivery is at least once, so a handler can run again after it has succeeded.
- A multipart upload is invisible until `complete_multipart`. The bucket deletes objects after 7 days and discards unfinished uploads after 24 hours. We build no cleanup job.
- `row_count` is the unfiltered total. A filtered view of a big report can be small but still takes the large path. This is by design.

## Step 1. Create the `report_exports` table (one-off migration)

- **Starts when:** deployed with the feature.
- **Data:**
  - `export_id` (UUID, primary key), `user_id`, `report_id`
  - `filters` (JSON) and `cols` (ordered list), copied from the click
  - `status` (`queued`, `running`, `done` or `failed`)
  - `attempt`, `job_id`, `object_key`, `rows_written`, `error_text` (for engineers only, never shown on the page)
  - `created_at`, `updated_at`, `completed_at`, `email_sent_at`
- **State kept:** in this table. A **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')` enforces "one at a time". The database enforces it, so two simultaneous clicks cannot both win.
- **Object key:** `reports/{report_id}/{export_id}.csv`. It is fixed per export, so a repeated run overwrites the same object.
- **If it fails:** the migration fails and the feature is not released.

## Step 2. The user clicks Download CSV

- **Starts when:** the page calls `POST /api/reports/{report_id}/exports` with the current `filters` and `cols` from the page URL, in the same form as the rows API.
- **Checks, in order:**
  1. The caller has `report.view` on the report's workspace (the same check the page and rows API use). Otherwise 403.
  2. `filters` and `cols` are valid for this report (same parser as the rows API). Otherwise 400.
  3. Read `reports.row_count`. At most 10,000 uses the small path (Step 3). Above 10,000 uses the large path (Step 4).
- **State kept:** none yet.
- **If it fails:** an unexpected error returns 500 and the user can click again. Nothing was created.

## Step 3. Small path: the response is the CSV

- **Starts when:** Step 2 chose the small path.
- **What happens:**
  1. Read the rows from the replica with the page's keyset paging, 500 rows per page, with the filters applied.
  2. Build the whole CSV **in memory**, then send it. At about 450 bytes per row (900 MB over 2 M rows), 10,000 rows is about 5 MB. Filters only remove rows, so the result never exceeds `row_count`, and the 10,000 limit is checked against `row_count` only.
  3. Respond `200` with `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment`. The page's JavaScript saves the response as a file.
- **CSV format:** a header row with column labels in the order of `cols`, then one row per record, escaped per RFC 4180. Use the same serializer as the job (Step 7), so the two paths cannot drift apart.
- **State kept:** none. No job, no export row, nothing stored.
- **If it fails:** a replica error or timeout (about 20 queries, well under 60 s) returns 500 and the user clicks again. The file is fully built before sending, so a failure never produces a truncated download.

## Step 4. Large path: create the export, or return the existing one

- **Starts when:** Step 2 chose the large path.
- **What happens, in one primary-database transaction:**
  1. **Stale check.** Find this user's `queued` or `running` export for this report. Mark it `failed` if either rule matches, which releases the unique slot:
     - It is older than 2 hours. A job lives at most about 96 min (3 x 30 min plus 6 min of waits), so this one is dead.
     - It has no `job_id` and is older than 1 minute. The request that created it crashed before Step 5.
  2. **Insert** an export row with status `queued`.
  3. If the insert hits the unique index, an export is already active. Read it and **return it** (HTTP 200, `{export_id, status, filters, cols, already_active: true}`) without starting another. A click with *different* filters also returns the active one. The page shows its filters, so the user can see which export it is.
- **State kept:** the export row.
- **If it fails:** the transaction rolls back, nothing is created and the API returns 500.

## Step 5. Enqueue the job and answer the click

- **Starts when:** Step 4 inserted a new row.
- **What happens:**
  1. Call `enqueue("report_export", {"export_id": ...})`. The job loads filters and columns from the export row.
  2. Save the returned `job_id` on the row.
  3. Respond `202 {export_id, status: "queued"}`. The page then shows the state (Step 12).
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` and return 503. The user can click again.
  - If the process dies before the `job_id` is saved, the row stays `queued` with no `job_id`. The stale check in Step 4 clears it on the next click.

## Step 6. A worker starts an attempt

- **Starts when:** the queue calls `handler(ctx, payload)`. This happens up to 3 times, and possibly again after a success.
- **What happens:**
  1. Load the export row.
  2. If the row is `failed`, **return normally** and do nothing else. The slot was released and a new export may be active, so this handler must not revive the row.
  3. If the row is `done`, go straight to Step 9 to finish any unsent email, then stop. This makes duplicate delivery harmless.
  4. Re-check `report.view` for the row's user. If access was lost, set `failed`, send no email and **return normally**, so the queue does not retry.
  5. Otherwise (`queued`, or `running` because of a retry or duplicate delivery) set `status = running` and `attempt = ctx.attempt`, then continue to Step 7. If two attempts run at once, both write the same content to the same key, so the result is still correct.
- **State kept:** the export row.
- **If it fails:** an exception ends the attempt, and Step 10 handles it.

## Step 7. Stream the rows into storage

- **Starts when:** Step 6 passed.
- **What happens:**
  1. `upload_id = start_multipart("exports", object_key)`. Nothing is visible yet.
  2. Write the header row into an in-memory buffer.
  3. Loop: read **5,000 rows** from the replica with `row_id > last_row_id ORDER BY row_id`, using the stored filters. Append their CSV text to the buffer, free the page, and remember the last `row_id`.
  4. When the buffer reaches **8 MiB** (above the 5 MB minimum part size), call `upload_part` with the next part number, keep the etag, and empty the buffer.
  5. Stop when a page comes back empty. Upload whatever remains in the buffer as the last part (any size; a report with zero matching rows still uploads its header).
- **Memory:** about 8 MiB buffer, plus one page, plus the etag list: a few tens of MB, far below 512 MB. The 900 MB report becomes about 115 parts, far below the 10,000-part limit.
- **Time:** about 400 page reads plus about 115 part uploads. Before release, run the largest report (2 M rows) in staging and record the time. Target 15 minutes or less, half the 30-minute timeout. If slower, enlarge the pages and upload parts concurrently. The timeout cannot be reasoned away, so measure it.
- **State kept:** upload ID, etags and last `row_id` live only in the attempt's memory. A retry starts again from the beginning.
- **If it fails:** if replica reads or uploads raise, call `abort_multipart(upload_id)` as best effort, then re-raise (Step 10). If the worker is killed or times out, no abort runs. This is safe, because the half-written upload is invisible and the bucket discards it within 24 hours.

## Step 8. Publish the file

- **Starts when:** the last part is uploaded.
- **What happens:**
  1. `complete_multipart(upload_id, etags)`. This is the **only** moment the object appears at its key, and it appears complete.
  2. Update the row: `status = done`, `completed_at = now`, `rows_written`.
  3. Continue straight to Step 9.
- **Why a half-written file is never downloadable:** nothing exists at the key until step 1 completes, nothing else writes to that key, and the row says `done` only after the object exists.
- **If it fails:**
  - If `complete_multipart` raises, go to Step 10.
  - If the worker dies after the object appeared but before the row is marked `done`, the retry rebuilds and overwrites the same key with the same content. This is safe.

## Step 9. Email the download link

- **Starts when:** straight after Step 8, or from Step 6 when a rerun finds the row `done`. It runs only if `email_sent_at` is empty.
- **What happens:**
  1. `url = signed_url("exports", object_key, 86_400)`, the maximum, giving 24 hours from the moment of the email.
  2. `send_email(user_id, "report_export_ready", {report name, url, row count})`. This template must be added; I have no sign it exists.
  3. Set `email_sent_at`.
- **Data moves:** a signed link goes to the user's email. Anyone holding it can download until it expires.
- **If it fails:** the email error raises, and the retry in Step 6 sees `done` with no `email_sent_at` and only resends the email. The file is not rebuilt. A duplicate email is possible only if the worker dies between sending and saving `email_sent_at`, and we accept that.

## Step 10. An attempt fails and the queue retries

- **Starts when:** the handler raises, times out or its worker dies, and attempts remain.
- **What happens:** if the handler raised, it first sets the row back to `queued` as best effort. After a timeout or a dead worker the row keeps reading `running` during the 60 s or 300 s wait. Either way the export is still in progress, so the page need not tell them apart. The queue then calls the handler again from the start (Step 6).
- **State kept:** the row stays `queued` or `running`. Both count as active, so the user cannot start a second export during retries.
- **If it fails:** nothing here matters. If the status update is lost, the row still reads `running` or `queued`, which is still true.

## Step 11. The last attempt fails

- **Starts when:** the queue calls `on_final_failure(ctx, payload, error)`, once, after attempt 3 has failed.
- **What happens, in order:**
  1. If the row is already `done`, do **not** mark it failed. The file exists and only the email failed. The page keeps showing `done` with its download button (Step 13), and an error is logged.
  2. Otherwise set `status = failed` and store the error text in `error_text`. This releases the unique slot, so the user can start a new export.
  3. Call `send_email(user_id, "report_export_failed", {report name})`. This second template must also be added. Wrap the call in try/except so an email error cannot undo step 2.
- **If it fails:** if the `failed` update cannot be saved, the row stays active. The stale rule in Step 4 clears it 2 hours after creation, and the status endpoint (Step 12) already reports it as failed.

## Step 12. The page shows the export's state

- **Starts when:** the page loads, and then every 5 seconds while the state is `queued` or `running`. This also covers the user returning later, because state comes from the database, never from the browser.
- **Data:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export of this report as `{export_id, status, filters, created_at, completed_at, download_available}`. It does the same `report.view` check (403 otherwise) and reads from the primary. `download_available` is true only when `status` is `done` and `completed_at` is less than 24 hours ago.
- **Display:** one of queued, running, done, failed. A `queued` or `running` row past the stale rule in Step 4 is reported as `failed`. For `done`, show the Download button if `download_available` is true, otherwise "Link expired, export again" (Step 13). When `failed`, the Download CSV button works again, since no export is active.
- **State kept:** only the `report_exports` row. Nothing is added to the page's table.
- **If it fails:** a failed poll keeps the last known state on screen and retries on the next tick.

## Step 13. Download from the page when the state is `done`

- **Starts when:** the user clicks Download on a `done` export.
- **What happens:** `GET /api/reports/{report_id}/exports/{export_id}/download` checks `report.view`, checks the export belongs to the caller, and checks it is `done` and under 24 hours old. It then redirects to `signed_url("exports", object_key, 300)`, a short link minted each time.
- **After 24 hours:** the page keeps the `done` label but shows "Link expired, export again". A new click starts a new export, because only `queued` or `running` exports block one (decision 2 below).
- **If it fails:** a 403 or 404 shows a message. If the file is gone (the bucket deletes it after 7 days), the user starts a new export.

## Step 14. Tests before release

- **Small path:** exactly 10,000 rows returns CSV; 10,001 starts a job. Check quoting of commas, quotes and newlines, and column order.
- **Permissions:** 403 on both paths, on status and on download. Report rows come only from the replica (check the connection used).
- **Duplicate click:** two simultaneous clicks produce one export row and the same `export_id` returned to both.
- **Failure paths:**
  - Force an error mid-upload: no object appears at the key, and the retry succeeds.
  - Force `on_final_failure`: the row is `failed`, the failure email is sent and a new click works.
  - Rerun a succeeded job: no second file, and no second email unless the first send was never saved.
  - Run the handler on a `failed` row: it does nothing.
- **Largest report:** run the 2 M-row report in staging. Record peak worker memory (well below 512 MB) and total time (target under 15 minutes).

## Decisions I made that you may want to change

1. **One active export per user and report, whatever the filters.** A click with other filters returns the running one. The alternative, one per user, report and filter set, departs from the brief's wording.
2. **A link only lasts 24 hours.** The file survives 7 days because of the bucket's rule. After 24 hours the page still shows `done` but offers no download. Letting the page mint links for the full 7 days would be a small change.
3. **Nightly rebuild.** If the rebuild rewrites `report_rows` while an export runs, the file may mix old and new rows. I added no snapshot, because exports rarely overlap the rebuild and avoiding it would need an extra column or a rebuild lock.
4. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in a spreadsheet. I have not altered the data. Ask security whether to prefix such cells with `'`.
5. **Two new email templates** (`report_export_ready`, `report_export_failed`) must be written, since I only know the `send_email` signature.

## Open questions

- The exact name of the shared `report.view` check function is not known to me. Step 2 only says to reuse the one the rows API uses.
