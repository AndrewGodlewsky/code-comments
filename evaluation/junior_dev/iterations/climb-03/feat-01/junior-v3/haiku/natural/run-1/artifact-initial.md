# Plan: CSV export for the reports page

## Terms used in this plan

- **Primary database**: the main read-write database. Export state is written here.
- **Read replica**: a read-only copy of the primary. Report rows are read only from here.
- **Keyset paging**: each page asks for rows with `row_id > last_seen_row_id`, ordered by `row_id`, with a limit. Pages stay fast no matter how deep they go.
- **Job queue** (`jobs.py`): runs a registered handler on a worker. Each attempt has a 30-minute timeout. A failed attempt is retried after 60 s, then 300 s, for 3 attempts in total. Each attempt starts from scratch, and the queue stores no progress. Delivery is at least once.
- **Multipart upload** (`storage.py`): an object is uploaded in parts. Nothing is visible at the key until `complete_multipart` runs. `abort_multipart` discards the parts. Parts other than the last must be at least 5 MB.
- **Export record**: a new row in the primary database, one per export. It holds the state of the export. It never holds report rows.

## Overview

The button sends one request. The server checks permission and the size of the report, then does one of two things:

- **Small (row_count of 10,000 or fewer):** the response body is the CSV. Nothing is stored.
- **Large (row_count above 10,000):** the server records an export, queues a job, and returns at once. The job builds the file in the `exports` bucket and emails a 24-hour download link. The page shows the export's state.

Both paths read rows through one shared function, so the filters, column order and row order match what the page shows.

---

## Step 1. Add the export record table (primary database)

- **Starts:** a schema migration, run at deploy time.
- **Data moved:** none at runtime.
- **State:** a new table `report_exports`, with these columns:
  - `export_id` (primary key)
  - `user_id`, `report_id`
  - `filters` and `cols`, copied from the URL as sent
  - `status`: one of `queued`, `running`, `done`, `failed`
  - `job_id`
  - `attempt` (the number of the attempt currently running)
  - `upload_id` (the multipart upload of the current attempt)
  - `object_key`, set when the file is complete
  - `email_sent_at`
  - `error` (a short text, shown only on failure)
  - `created_at`, `updated_at`, `completed_at`
- Add a **partial unique index** on `(user_id, report_id)` where `status` is `queued` or `running`. This enforces "one active export per user and report" in the database itself, so two simultaneous clicks cannot both succeed.
- **On failure:** if the migration fails, the deploy stops. Nothing else has changed.

## Step 2. Share the row reader and the CSV writer

- **Starts:** a code change, before any feature work.
- **Data moved:** report rows, read from the replica in keyset pages of 500 rows (the same page size as the page API).
- **What to build:**
  - One function that takes `report_id`, `filters`, `cols` and a starting `row_id`. It yields pages of rows from `report_rows` on the replica, using `row_id > after ORDER BY row_id`.
  - One function that turns a row into one CSV line, using RFC 4180 quoting, UTF-8 encoding, and a header line built from `cols`.
  - The existing rows API is changed to use the same filter and column parsing. Its response must stay the same.
- **State:** none.
- **On failure:** if the replica is unavailable, the calling request fails with 503. Because the API has no write, nothing is left behind.

## Step 3. Accept the click and decide the path

- **Starts:** the user presses **Download CSV**. The page sends `POST /api/reports/{report_id}/exports` with the current `filters` and `cols` from the URL.
- **Data moved:**
  - The server checks `report.view` on the report's workspace. If the check fails, it returns 403, as the page does.
  - The server reads `reports.row_count`. This is the unfiltered total, as the spec requires.
- **Decision:**
  - If `row_count` is 10,000 or fewer, go to Step 4.
  - If `row_count` is above 10,000, go to Step 5.
- **State:** none in this step.
- **On failure:** if the `reports` read fails, return 503. The client shows a retry message.

## Step 4. Small path: stream the CSV in the response

- **Starts:** Step 3 chose the small path.
- **Data moved:** rows are read from the replica in pages of 500 through the shared reader (Step 2). Each page is written to the response body as CSV lines. The response has `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`.
- **State:** none. No job is created and no file is stored.
- **Memory:** only one page is held at a time.
- **Time limit:** the API kills any request that runs longer than 60 seconds. 10,000 rows should fit comfortably, but this must be measured (see the testing list).
- **On failure:**
  - If the request is cut off partway, the response is truncated. The client must not save a partial file. The client reads the whole body with `fetch`, and only saves it when the body finishes. A cut-off response makes `fetch` throw, so no file is saved. The user sees an error and can click again.
  - If permission is revoked during the stream, the check in Step 3 has already passed. This is accepted for this request.

## Step 5. Large path: record the export and queue the job

- **Starts:** Step 3 chose the large path.
- **Data moved:** one row is inserted into `report_exports`, and one job payload is queued. The payload is only `{"export_id": "..."}`, which is far below the 64 KB limit. The filters and columns are read from the export row by the job.
- **Order of work:**
  1. In a database transaction, look for an existing export for this user and report with status `queued` or `running`. If one exists, return it (see the rule below).
  2. If none exists, insert a row with status `queued`.
  3. If the insert hits the unique index, another request won the race. Read the row that won and return it.
  4. After the insert commits, call `enqueue("export_report", {"export_id": ...})`. Store the returned `job_id` on the row.
  5. Return HTTP 202 with the export's JSON (`export_id`, `status`, `filters`, `cols`).
- **Rule for a repeated click:** a click while an export is `queued` or `running` gets that export back with 202. The response says which filters the existing export uses. If the user changed the filters, the page shows that the existing export has different filters. A new export starts only after the old one is `done` or `failed`.
- **State:** `report_exports` holds the row. The job queue holds the job.
- **On failure:**
  - If `enqueue` raises an error, update the row to `failed` with `error = "could not queue"`, then return 503. The user can click again.
  - If the server crashes between step 2 and step 4, the row stays `queued` with no `job_id`. The status read (Step 11) treats a `queued` row with no `job_id` older than 5 minutes as `failed`. This check runs when someone reads the status, so no background job is needed.

## Step 6. Job attempt: start and guards

- **Starts:** the job queue runs the `export_report` handler with `payload = {"export_id": ...}` and a `JobContext` holding `job_id` and `attempt` (1, 2 or 3).
- **Data moved:** the handler reads the export row from the primary database, along with the user, the report, the filters and the columns.
- **Guards, in order:**
  1. If the row is `done` and `email_sent_at` is set, the work is already finished. Return without doing anything. This covers duplicate job delivery.
  2. If the row is `done` but `email_sent_at` is empty, the file exists but the email did not go out. Skip to Step 9.
  3. Otherwise, re-check `report.view` for the user. If the check fails, raise an error. The queue will retry, and after the last attempt Step 10 marks the export as failed.
  4. Set `status = running`, `attempt = ctx.attempt`, and `updated_at = now`. The page can now show "running".
- **If the row is already `failed`:** return without doing anything.
- **State:** the row moves `queued` to `running`.
- **On failure:** an exception here is handled by the queue like any other attempt failure.

## Step 7. Job attempt: build the file in parts

- **Starts:** Step 6 passed.
- **Data moved:**
  - Rows are read from the **replica** through the shared reader (Step 2), in pages of 500 rows.
  - CSV bytes are collected in a buffer of 16 MB. When the buffer is full, it is uploaded as one part. The buffer is then cleared. The last part may be smaller.
  - About 900 MB of CSV, for the largest report, becomes about 57 parts. This is well under the 10,000-part limit.
- **Steps:**
  1. Call `start_multipart("exports", key)`, where `key = "reports/{report_id}/exports/{export_id}-attempt{attempt}.csv"`. Store the returned `upload_id` on the row before uploading any part, so a later attempt or the failure handler can find and abort it.
  2. Read a page, write its CSV lines into the buffer, and move to the next page using the last `row_id`.
  3. When the buffer reaches 16 MB, call `upload_part(upload_id, part_number, bytes)` and keep the returned etag in a list. The list holds only etags, not data.
  4. When the last page is read, upload the remaining bytes as the last part.
- **Why a per-attempt key:** if an older attempt is still running when a new one starts, the two never overwrite each other's object. The row records which object is the final one (Step 8).
- **Memory bound:** at any time the process holds one 500-row page, one 16 MB buffer, and a list of etags. This stays well inside the 512 MB limit. The row reader must not collect rows into a list.
- **Time bound:** the attempt has 30 minutes. Each attempt starts from scratch, so the whole file must be built within one attempt. This must be measured against the 2-million-row report (see the testing list).
- **State:** the row holds `upload_id` and `attempt`. The uploaded parts are held by the storage service and are invisible until Step 8.
- **On failure:**
  - If the handler raises, call `abort_multipart(upload_id)` as a best effort, then raise the error. The queue retries.
  - If the worker dies or the attempt times out, no code runs. The uploaded parts stay until the bucket's lifecycle rule discards incomplete uploads after 24 hours. The next attempt starts its own upload and records the new `upload_id`.
  - A half-written file is never downloadable, because nothing is visible at the key until Step 8.

## Step 8. Job attempt: make the file visible

- **Starts:** every row has been read and every part has been uploaded.
- **Data moved:** none. The storage service joins the parts.
- **Steps:**
  1. Call `complete_multipart(upload_id, etags)`. This makes the object visible at its key.
  2. Update the row: `object_key = key`, `status = done`, `completed_at = now`, `upload_id = null`.
- **State:** the row now holds the final object's key.
- **On failure:**
  - If `complete_multipart` raises, nothing is visible. Abort the upload as a best effort and raise. The queue retries.
  - If the step 2 update fails after the object was completed, the attempt raises. The next attempt rebuilds the file under a new key and completes it. The first object is harmless and expires with the 7-day lifecycle rule.

## Step 9. Job attempt: email the download link

- **Starts:** the row is `done` (Step 8, or Step 6 guard 2).
- **Data moved:**
  - Generate `url = signed_url("exports", object_key, 86400)`. The link works for 24 hours, as the spec requires.
  - Call `send_email(user_id, "export_ready", {"download_url": url, "report_id": ..., "export_id": ...})`.
- **State:** on success, set `email_sent_at = now`.
- **On failure:** if `send_email` raises, the attempt raises. The next attempt sees `done` without `email_sent_at` and sends the email again (Step 6, guard 2). It does not rebuild the file.
- **Known gap:** if the email is delivered but the process dies before `email_sent_at` is saved, the user gets the link twice. This is accepted, because email delivery cannot be made atomic with the database write.

## Step 10. Final failure

- **Starts:** the queue calls `on_final_failure(ctx, payload, error)` once, after the third attempt fails.
- **Data moved:** the failure handler reads `upload_id` from the row, so it can abort any upload that was left open.
- **Steps, in this order:**
  1. Set the row to `status = failed`, `error = <error text, cut to 500 characters>`, `updated_at = now`. Do this first, so the page shows failed even if the next step fails.
  2. If `upload_id` is set, call `abort_multipart(upload_id)` as a best effort.
  3. Call `send_email(user_id, "export_failed", {"report_id": ..., "export_id": ...})`.
- **Do not** set `failed` on a row that is already `done`. A `done` export can only be overwritten by a later attempt that succeeds. If the final attempt fails after an earlier one completed the file, the export stays `done`. (This is a conditional update: `WHERE status <> 'done'`.)
- **State:** the row is `failed` (or left `done`).
- **On failure:** if the email call fails, log it. The page still shows the export as failed, so the user can see the failure there.

## Step 11. Status on the page

- **Starts:** the page loads, or the user comes back to the report later.
- **Data moved:** the page calls `GET /api/reports/{report_id}/exports/latest`. The server checks `report.view`, then returns the newest export for this user and report, from the primary database.
- **What the page shows, by state:**
  - `queued`: "Queued", with the time it was requested.
  - `running`: "Building file, attempt N of 3".
  - `done`: a **Download** button. The server returns a fresh signed URL with a 24-hour lifetime while the object still exists. Objects are deleted 7 days after creation, so after that the page shows "Expired, export again".
  - `failed`: "Export failed", with a **Try again** button that starts Step 5.
- **Polling:** while the state is `queued` or `running`, the page checks the status every 5 seconds. It stops when the state is `done` or `failed`.
- **Stale check:** a `queued` row with no `job_id` older than 5 minutes is shown as `failed` (see Step 5).
- **State:** none written by this step, except the stale check, which is shown only and not saved.
- **On failure:** if the status request fails, the page shows the last known state and a retry message.

## Step 12. Front end for the button

- **Starts:** the user presses **Download CSV**.
- **Steps:**
  1. Send `POST /api/reports/{report_id}/exports` with the current filters and columns.
  2. If the response is `text/csv`, read the whole body and save it as a file. Save only after the body has finished. This is the small path (Step 4).
  3. If the response is JSON with status 202, show the export panel (Step 11).
- **On failure:** a network error or a 503 shows a message, and the button can be pressed again.

## Step 13. Retention and cleanup

- Files are removed by the existing lifecycle rule on the `exports` bucket, 7 days after creation. No cleanup job is built, as the spec requires.
- Export rows are kept. They are small, and the status page needs the history.
- Abandoned multipart uploads are removed by the bucket's 24-hour rule.

## Step 14. Testing and rollout

Test these cases before release:

1. **Boundary:** a report with 10,000 rows takes the small path, and one with 10,001 rows takes the large path.
2. **Timing of the small path:** a 10,000-row export finishes within the 60-second API limit, measured on the replica.
3. **Timing of the large path:** a 2-million-row export finishes within the 30-minute attempt timeout, measured on the replica. **If it does not, see the open questions.**
4. **Memory:** a 2-million-row job stays well inside 512 MB, measured with a memory profiler.
5. **Double click:** two clicks at once produce one export. The second request gets the first export back.
6. **Click during a run:** a click while the export is `running` returns the running export.
7. **Duplicate delivery:** running the handler again on a `done` export sends no second email and rebuilds nothing.
8. **Crash mid-upload:** a worker killed during upload leaves no visible file. The retry completes and the download works.
9. **Crash before enqueue:** a `queued` row with no `job_id` shows as `failed` after 5 minutes, and the user can try again.
10. **Final failure:** after three failed attempts, the row shows `failed`, the upload is aborted, and the failure email is sent.
11. **Email failure:** if the link email fails once, the next attempt sends it without rebuilding the file.
12. **Permission revoked:** a user who lost `report.view` cannot start an export, and the job fails at its re-check.
13. **Truncated small download:** a cut-off small download is not saved by the browser.

**Rollout:** ship behind a feature flag, and enable it first for internal users. Watch the job's duration and failure counts before turning it on for everyone.

---

## Open questions

These points are not settled by the brief. Each needs an answer before or during build.

1. **Threshold uses the unfiltered total.** A filter that leaves 50 rows of a 2-million-row report still takes the large path, so the user waits for an email for a tiny file. The brief asks for `row_count`. Should the server count the filtered rows as well, or accept the cost?
2. **`row_count` is stale.** It is rebuilt nightly. A report that grew past 10,000 rows during the day may take the small path and run past the 60-second limit. Options: a time check in the small path that stops and returns an error before the response starts, or a count query on the replica before streaming.
3. **Attempt time budget.** The queue starts every attempt from scratch. If the 2-million-row build takes more than 30 minutes, all three attempts fail the same way. If Step 14 test 3 fails, the fallbacks are: (a) read larger pages in the job only, (b) upload parts in parallel, with at most about 4 parts in memory at once, or (c) save the upload ID and each part's etag and last `row_id` on the export row, so a later attempt resumes where the last one stopped. Option (c) goes against the queue's design, so it needs a decision.
4. **Column headers.** Should the CSV header use the column ids from the URL (`customer`) or the labels the page shows (`Customer name`)? The brief does not say.
5. **Excel and formulas.** Should the file start with a UTF-8 byte-order mark, so Excel reads accents correctly? Should cells that start with `=`, `+`, `-` or `@` be prefixed with an apostrophe, to block spreadsheet formula injection? This plan assumes yes to both, and needs confirmation.
6. **Repeated click with different filters.** The plan returns the active export, which may have other filters. Is that acceptable, or should the server return 409 so the page can say "an export is already running with other filters"?
7. **Email templates.** The plan assumes templates named `export_ready` and `export_failed` exist or will be created. Check the names used by `send_email`.
8. **Link exposure.** The download link is a bearer link. Anyone who gets it can download the file for 24 hours. This matches the brief, but it should be stated to the product owner.
9. **Empty `cols`.** If the URL has no `cols`, does the page show all columns in a default order? The export must use the same default.