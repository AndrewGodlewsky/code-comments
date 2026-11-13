# CSV export for the reports page: implementation plan

## Terms used in this plan

- **Keyset paging**: fetch the next page with `WHERE row_id > last_row_id ORDER BY row_id LIMIT n`. Never OFFSET.
- **Read replica**: a read-only copy of the database. Report rows are read only from it.
- **Export row**: one new record in the primary database for each large export. It holds the export's state. It never holds report rows.
- **Multipart upload**: object storage accepts a file as numbered parts. Nothing is visible at the final key until `complete_multipart` succeeds. `abort_multipart` discards the parts. Every part except the last must be at least 5 MB. There is a limit of 10,000 parts.
- **Attempt**: one run of a job handler. The queue allows 3 attempts in total. It waits 60 s before attempt 2 and 300 s before attempt 3. It kills any attempt still running after 1,800 s. Between attempts it keeps no progress, so each attempt starts from the beginning.
- **Delivery at least once**: a handler can run again for a job that already succeeded. Every step below is written to tolerate that.

## Overview

1. The user clicks **Download CSV**.
2. If the report has 10,000 rows or fewer, the server builds the CSV in memory and returns it in the same response. Nothing is stored.
3. If the report has more than 10,000 rows, the server creates an export row, queues a job, and returns at once. The job streams the rows into a multipart upload in the `exports` bucket. When the upload completes, the job marks the row done and emails a 24-hour link. The page polls the row's state and shows it.

## Steps

### Step 1. Add the export state table

- **Starts**: a database migration, run during deploy.
- **Data**: no report rows. Table `report_exports` in the primary database, with these columns: `export_id` (UUID, primary key), `user_id`, `report_id`, `filters` (text, capped at 4 KB), `cols` (text), `status` (`queued`, `running`, `done` or `failed`), `attempt` (integer, 0 until the first claim), `job_id`, `upload_id`, `object_key`, `row_count`, `created_at`, `started_at`, `completed_at`, `expires_at`, `email_sent_at`, `error_summary` (short text, never row content), `updated_at`.
- **State**: the table itself. Add a partial unique index on `(user_id, report_id)` where `status IN ('queued', 'running')`. The database then enforces "one active export per user per report".
- **Fails**: if the migration fails, the deploy stops and nothing has changed. To roll back, drop the table. Nothing depends on it until step 4 ships.

### Step 2. Build one shared row reader

- **Starts**: called by the synchronous path (step 3) and by the job (step 6).
- **Data in**: `report_id`, the `filters` and `cols` from the page URL.
- **Data out**: a stream of CSV lines, with the header row first. The header lists the `cols` names in the order given in the URL.
- **Validation**: check every column name and filter field against the allowlist the page already uses. Reject anything else with 400. Never put raw URL text into SQL.
- **Query**: run this against the replica, with a page size of 5,000 rows: `SELECT ... FROM report_rows WHERE report_id = ? AND <filters> AND row_id > ? ORDER BY row_id LIMIT 5000`. Write CSV with the standard `csv` module, encoded as UTF-8.
- **Stop condition**: stop when a page comes back empty. A database error must raise. It must never be read as the end of the data, because a silently truncated file is worse than a failed one.
- **State**: none. Only one page is held in memory at a time.
- **Fails**: the reader raises and does not catch. The caller decides what happens next.

### Step 3. Synchronous path (10,000 rows or fewer)

- **Starts**: `GET /api/reports/{id}/export.csv?filters=...&cols=...`, sent by the click.
- **Checks, in order**:
  1. The caller has `report.view` on the report's workspace. Otherwise return 403.
  2. Read `reports.row_count` from the replica. If it is above 10,000, return 409 with a body that says to use the large path. The page then calls step 4.
- **Data**: the reader from step 2 writes the whole CSV into an in-memory buffer. The buffer is capped at 10,000 rows, which is a few megabytes. If the reader produces more than 10,000 rows (for example, because `row_count` is stale), stop, discard the buffer, and return 409 so the page takes the large path. This cap keeps memory bounded.
- **Response**: 200 with `Content-Type: text/csv`, `Content-Disposition: attachment; filename=...`, and `Content-Length`. The body is sent only after it is fully built.
- **State**: none. No row, queue entry, or email.
- **Fails**: 400 for bad filters or columns, 403 for no permission, 404 for an unknown report, 409 for the large path, 500 for a database error. A 500 sends no partial file, because nothing was sent before the body was complete. Nothing needs cleaning up.

### Step 4. Large path: the click creates an export row (above 10,000 rows)

- **Starts**: `POST /api/reports/{id}/exports` with the same `filters` and `cols`. The page sends it after step 3 returns 409.
- **Checks**: `report.view`, then validation with the step 2 parser. The filters string must be at most 4 KB.
- **Data**: insert a row with `status = queued`, `user_id`, `report_id`, `filters`, `cols` and `created_at`. The filters and columns are stored on the row, not in the job payload.
- **One at a time**: the insert runs against the partial unique index from step 1. If the insert conflicts, read the existing active row and return it with 200. No second job is started. This also handles two clicks that arrive together.
- **Stale rows**: an active row is treated as active only if `updated_at` is within the last 2 hours. The longest a healthy export can run is about 96 minutes (3 × 1,800 s plus the 60 s and 300 s waits). An older active row is treated as failed by this endpoint, so a lost failure hook cannot block the user forever. Also, a `queued` row with no `job_id` older than 5 minutes is treated as dead in the same way.
- **Enqueue**: call `enqueue("build_report_export", {"export_id": ...})`. The payload is only the id, far under 64 KB. Save the returned `job_id` on the row.
- **Response**: 202 with `export_id`, `status`, `created_at` and `attempt`. The request does not wait for the file.
- **State**: the row from step 1.
- **Fails**: if `enqueue` raises, set the row to `failed` with `error_summary = "could not queue"` and return 503. If the process dies between the insert and the enqueue, the row has no `job_id`. The stale-row rule above clears it on the next click, so no cleanup job is needed.

### Step 5. The queue starts the job: claim the export

- **Starts**: the queue runs `build_report_export`, attempt 1, 2 or 3, with payload `{export_id}`.
- **Data**: read the export row by `export_id`.
- **Decision**:
  - No row: exit successfully.
  - `status = done` and `email_sent_at` is null: go to step 8 only.
  - `status = done` and `email_sent_at` is set, or `status = failed`: exit.
  - `status = running` and `attempt >= ctx.attempt`: another copy of this attempt is active. Exit.
  - Otherwise (`queued`, or `running` with a lower attempt number from a dead attempt): claim it with one conditional update. Set `status = running`, `attempt = ctx.attempt`, `started_at = now`, and `job_id`, where `export_id` matches and the status and attempt still match what was read. If zero rows change, another copy won the race. Exit.
- **State**: the export row.
- **Fails**: a database error during the read or claim raises, and the queue retries. The page keeps showing the last state it had, which is at most one attempt behind.

### Step 6. Stream rows into a multipart upload (the heavy step)

- **Starts**: a successful claim in step 5.
- **Key**: `reports/{report_id}/exports/{export_id}.csv` in the `exports` bucket. The key is unique per export, so a retry can only replace its own file.
- **Clean up an earlier attempt**: if the row already has an `upload_id`, call `abort_multipart(upload_id)` and ignore "not found" errors. Then call `start_multipart(bucket, key)`. Save the new `upload_id` on the row before any part is uploaded. A later attempt can then abort it even if this one dies.
- **Stability check, start**: read `reports.row_count` from the replica as `N0`.
- **Loop**: read pages through the step 2 reader and append the CSV bytes to a buffer. When the buffer reaches 8 MB, call `upload_part(upload_id, part_number, bytes)`. Keep the returned etag with its part number, then clear the buffer. Part numbers start at 1. After the last page, upload any remaining bytes as the final part. That part may be smaller than 5 MB.
- **Stability check, end**: read `reports.row_count` again as `N1`. If `N1 != N0`, the nightly rebuild ran during the export. Raise, so the queue retries. This guards against row ids changing partway through a read.
- **Memory**: at most one page of 5,000 rows plus one 8 MB buffer. The whole report is never held in memory. A 900 MB CSV needs about 115 parts, far below the 10,000 limit.
- **Deadline**: 2,000,000 rows in 1,800 s needs at least 1,112 rows per second. Step 11 sets the gate at 2,500 rows per second end to end, which is about 13 minutes. If the measured rate is too low, the options are: (a) use a faster query or CSV writer; (b) upload parts in parallel, with up to 4 workers and one 8 MB buffer each, which fits in memory; (c) split the work into jobs by `row_id` range, each uploading parts to the same `upload_id`, plus a final completion job. Option (c) needs its own design before it is built.
- **State**: `upload_id` on the row, and the etags held in the worker's memory only.
- **Fails**:
  - An exception in the loop (database error, upload error, or row count changed): call `abort_multipart(upload_id)` on a best-effort basis, then raise. The queue schedules the next attempt.
  - The worker dies, or the attempt hits the 1,800 s limit: no code runs, so the upload stays open. The next attempt aborts it using the saved `upload_id`. If there is no next attempt, the bucket's lifecycle rule discards it within 24 hours.
  - At no point is a partial file visible at the key, because nothing is visible until step 7. A half-written file cannot be downloaded.

### Step 7. Complete the file and mark the export done

- **Starts**: the loop finishes and the stability check passes.
- **Action**: call `complete_multipart(upload_id, etags)`. The object appears at the key. It replaces an object already there, which can only come from an earlier attempt of this same export.
- **Then**: a conditional update sets `status = done`, `completed_at = now`, `object_key`, `row_count` (rows written) and `expires_at = completed_at + 7 days - 1 hour`, where `status = running` and `attempt = ctx.attempt`. The one-hour margin keeps the page from offering a link to a file the lifecycle rule is about to delete.
- **Data**: the file moves into storage. Only metadata is written to the database.
- **State**: the export row.
- **Fails**:
  - `complete_multipart` raises: the object is not created. Raise. The next attempt aborts the saved `upload_id` and starts over.
  - `complete_multipart` succeeds but the database update fails: the file exists but the row still says `running`. Raise. The retry rebuilds the file and replaces it at the same key. This costs time but not correctness.
  - Any other exception before this step: if `ctx.attempt < 3`, set `status = queued` and a short `error_summary` before re-raising, so the page shows that the export is waiting to retry. On attempt 3, leave the status alone and let the final failure hook (step 9) set it.

### Step 8. Email the download link

- **Starts**: directly after step 7, or on a retry that step 5 routes here (`done` with no `email_sent_at`).
- **Action**: generate `url = signed_url(bucket, object_key, 86400)`. Call `send_email(user_id, "report_export_ready", {report_id, export_id, download_url: url, link_expires_at: now + 24h})`. After it succeeds, set `email_sent_at = now` on the row.
- **Data**: the link is a bearer URL. Anyone holding it can download the CSV until it expires.
- **State**: `email_sent_at` on the row.
- **Fails**: if `send_email` raises, raise. The queue retries, and step 5 routes the retry here again. The retry makes a new link with a fresh 24-hour lifetime. If all attempts fail at this step, the final failure hook (step 9) sees `status = done` and does not mark the export failed. The user can still download from the page, but they do not get the email. Log it for operations.

### Step 9. Final failure

- **Starts**: the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 has failed. Per the queue's contract, this includes timeouts and dead workers.
- **Action**: conditional update: `status = failed`, `error_summary` (the error text cut to 500 characters, with no row content), `updated_at = now`, where `export_id` matches and `status <> 'done'`. Then call `send_email(user_id, "report_export_failed", {report_id, export_id})`.
- **State**: the export row.
- **Fails**: if the email fails, log it and do not raise. The page still shows the export as failed. If the status update fails, raise. The queue's behaviour in that case is an assumption (see the open questions). A row stuck in `running` is cleared by the 2-hour rule in step 4.

### Step 10. Status and download on the page

- **Starts**: the page loads, and then polls every 5 seconds while the latest export is `queued` or `running`. Polling stops on `done` or `failed`.
- **Status**: `GET /api/reports/{id}/exports/latest` checks `report.view`, then returns the caller's most recent export for this report, in any status. The response includes `export_id`, `status`, `attempt`, `filters`, `cols`, `created_at`, `completed_at`, `row_count`, `expires_at` and a short `error`. It never returns another user's export.
- **Display**:
  - `queued`: "Queued". If `attempt > 0`, show "Retrying, attempt N of 3".
  - `running`: "Running, attempt N of 3".
  - `done`: "Ready" with a Download button while `now < expires_at`. Otherwise "Expired. Export again".
  - `failed`: "Failed" with a "Try again" button that calls step 4.
  - If the export's `filters` or `cols` differ from the page's current URL, say so and show the export's own filter text. Step 4 returns the running export, so this case happens.
- **Download**: `GET /api/reports/{id}/exports/{export_id}/download` checks `report.view`, the caller's ownership, and `status = done` with `now < expires_at`. It returns a 302 to `signed_url(bucket, object_key, min(86400, expires_at - now))`. Each click gets a fresh link, separate from the emailed one.
- **State**: none beyond the export row. The browser holds only the polling timer.
- **Fails**: 403 for no permission, 404 for an unknown export or one belonging to someone else, 410 when the export has expired.

### Step 11. Verification before rollout

- **Unit tests**: the keyset reader uses `row_id`, never OFFSET; it stops on an empty page; it raises on a database error and yields nothing after the error. The CSV writer follows column order, quotes commas, quotes and newlines, and rejects unknown columns.
- **State tests**: duplicate delivery of a done export; takeover of a dead running attempt; email-only retry; the final failure hook does not overwrite `done`.
- **Failure injection on a staging bucket**: kill the worker mid-upload; make `complete_multipart` fail; make `send_email` fail. Confirm no object exists at the key before completion, and that an aborted upload leaves no object.
- **Boundaries**: 10,000 rows takes the sync path; 10,001 takes the large path; with a stale `row_count` and more than 10,000 rows, the sync path returns 409.
- **Concurrency**: 20 simultaneous POSTs from one user for one report create exactly one row and one job.
- **Permissions**: a user without `report.view` gets 403 from every endpoint, including download with a valid `export_id`.
- **Load gate**: on a 2,000,000-row report against a replica-sized database, measure end-to-end time (target 800 s or less, and under 1,800 s in any case) and peak memory (target 256 MB or less, and under 512 MB in any case). Also check the sync path for 10,000 rows finishes well inside 60 s.
- **Email**: confirm the emailed link downloads the complete file within 24 hours.

### Step 12. Rollout and monitoring

- **Starts**: release behind a feature flag. The flag disables the large path (step 4 and the page's large-path button) and leaves the sync path on.
- **Metrics**: exports started, attempts, failures by error type, duration, rows per second, file size, stale rows cleared, and the rate of 409 responses from step 3.
- **Rollback**: turn the flag off. Existing export rows and files remain until the lifecycle rule removes them. No migration is reversed.

## Open questions and assumptions

1. **Nightly rebuild and `row_id`**: the brief does not say whether the rebuild renumbers rows. If it does, a rebuild during an export could corrupt the file. The `row_count` check in step 6 catches a rebuild that changes the count, but not one that keeps it the same. Confirm with the owners, and consider a rebuild version id on `reports`. Running large exports outside the rebuild window is a fallback.
2. **Replica reads of `reports.row_count`**: assumed to be allowed from the replica, because it is report metadata.
3. **Email templates**: `report_export_ready` and `report_export_failed` are named here but are not mentioned in the brief. They must be created. Also assumed: `send_email` raises on failure.
4. **Final failure hook**: assumed that an error inside `on_final_failure` is logged by the queue and not retried.
5. **Bearer links**: the emailed link and the page link work for anyone who holds them for their lifetime, even if the user later loses `report.view`. The decision on whether this is acceptable is not in the brief.
6. **CSV hygiene**: not in the brief. Cells that start with `=`, `+`, `-` or `@` can run as formulas when opened in a spreadsheet. Decide whether to prefix them. Decide also whether to add a UTF-8 byte-order mark so Excel reads the encoding correctly.
7. **Sync decision uses total rows**: as the brief asks, the choice uses the unfiltered `row_count`. So a filter that leaves 50 rows on a 2,000,000-row report still takes the large path. The page should explain this.
8. **Retention**: the file is kept 7 days by the lifecycle rule. The page offers downloads until `expires_at`, which is 7 days minus 1 hour after completion. The emailed link lasts 24 hours.