# CSV export for the reports page: implementation plan

## Terms used in this plan

- **Read replica**: a copy of the database that serves reads. Report rows are read only from it.
- **Keyset pagination**: each page asks for rows with `row_id > last_seen` in order, so every page costs the same. Offsets are never used.
- **Multipart upload**: object storage receives a file as numbered parts. Nothing is visible at the file's key until the parts are joined in a final `complete` call.
- **Signed URL**: a download link that works for a set time.
- **Attempt**: one run of a background job. The queue retries a failed job up to 3 times in total, waiting 60 s before attempt 2 and 300 s before attempt 3. An attempt is killed after 1,800 s. Each attempt starts from the beginning, because the queue keeps no progress.
- **Export record**: a new row in the primary database that tracks one large export. It holds state, not report rows, so the primary may hold it.

Names marked as proposed (table, endpoints, job name, email templates) are new and can change.

## Step 1: Add the export record and the one-at-a-time rule

- **Starts**: a schema migration deploy.
- **Data moved**: none. Creates table `report_exports` on the primary with these columns: `export_id`, `user_id`, `report_id`, `filters`, `cols`, `state` (`queued`, `running`, `done`, `failed`), `job_id`, `attempt`, `upload_id`, `file_key`, `rows_written`, `error`, `created_at`, `started_at`, `updated_at`, `completed_at`, `email_sent_at`.
- **Rule**: a partial unique index on `(user_id, report_id)` where `state` is `queued` or `running`. The database itself then refuses a second active export of the same report for the same user.
- **State kept**: the table only.
- **On failure**: if the migration fails, nothing is deployed. Nothing else in the plan runs until it succeeds.

## Step 2: Move the row query into one shared function

- **Starts**: a code change in the existing rows API.
- **Data moved**: report rows, read from the read replica. The existing keyset query moves into `read_report_rows(report_id, filters, cols, after_row_id, limit)`, which returns rows with columns in the requested order.
- **Used by**: the page API (Step 3 small path), the job (Step 6), and so the filters and column order match exactly across the page and the export.
- **Validation**: `filters` and `cols` are parsed and checked against the report's allowed fields. Unknown fields return 400. The job reads the filters and columns from the export record. They were validated when the export was requested.
- **On failure**: a failed replica query raises an error to the caller. The page already handles this. Replica lag means rows may be a few seconds old, the same as the page today.

## Step 3: The export endpoint decides the path

- **Starts**: the user clicks Download CSV. The page sends `POST /api/reports/{id}/exports` (proposed) with the filters and `cols` from the page URL.
- **Checks, in order**: the report exists (404 otherwise), and the caller has `report.view` on its workspace (403 otherwise). This is the same check as the page.
- **Data moved**: reads `reports.row_count` from the read replica. This is report data, so it does not come from the primary.
- **Decision**: `row_count` of 10,000 or fewer goes to Step 4. More than 10,000 goes to Step 5. The decision uses the unfiltered count, as the brief fixes.
- **State kept**: none on this step.
- **On failure**: a permission or lookup error returns 500 or 403. No state changes.

## Step 4: Small report: build the CSV in the response

- **Starts**: Step 3 chose the small path.
- **Data moved**: calls `read_report_rows` in pages of 1,000, starting from `after_row_id = 0`, until a page comes back empty. Writes the header row from `cols`, then the rows, using RFC 4180 quoting and UTF-8.
- **Memory**: the whole CSV is held in memory before the response starts. At 10,000 rows and roughly 450 bytes per row (estimated from 900 MB for 2 million rows), that is about 5 MB. Buffering means a read error becomes a clean 5xx, not a truncated file.
- **Response**: `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{id}.csv"`.
- **Stores nothing**: no export record, no job, no email, no file.
- **Guard**: if more than 10,000 rows come back, the report grew after `row_count` was read. Stop and return `409` with a message to click again. The next click takes the large path.
- **Time**: 10 queries at most. Well inside the 60 s API limit.
- **On failure**: a replica read error returns `503`. Nothing is stored, so the user simply retries.

## Step 5: Large report: start the export or return the active one

- **Starts**: Step 3 chose the large path, `row_count` above 10,000.
- **Procedure**:
  1. In one primary transaction, mark this user's stale rows for this report as `failed`. A row is stale if it is `queued` with `job_id` null and older than 5 minutes, or if it is `queued` or `running` and older than 2 hours. Two hours is longer than the worst case of 3 attempts (3 × 1,800 s + 60 s + 300 s, about 96 minutes). Then insert a new row with state `queued`, the filters, and the columns.
  2. If the insert hits the unique index, another click won the race. Read the active row and return it. No second export starts.
  3. Call `enqueue('report_csv_export', {export_id})`. The payload is only the id, far under 64 KB.
  4. Save the returned `job_id` on the row.
  5. Return `202` with `export_id`, `state`, `filters` and `cols`. The `filters` are returned so the page can show what the active export really contains (see Open question 1).
- **Data moved**: one small row written on the primary. The payload carries no report data.
- **On failure**:
  - A crash between steps 1 and 4 leaves a `queued` row with no `job_id`. The 5-minute rule in step 1 clears it on the next click, so the user is blocked for at most 5 minutes.
  - If `enqueue` raises, mark the row `failed` with the error and return `503`. Nothing was queued, so no email is sent.
  - If saving `job_id` fails after `enqueue` succeeded, the job still runs. Its start check (Step 6) finds the row taken over or missing and exits.

## Step 6: Job attempt: build the file in parts

- **Starts**: the queue runs `report_csv_export` with `{export_id}`. Every attempt calls the handler from the beginning.
- **Start check**: load the row.
  - If `state` is `done`, go to Step 7's email-only path (see Step 7) and stop. Delivery is at least once, so duplicates happen.
  - If `state` is `failed`, or `job_id` is set and does not match this job, stop.
  - Otherwise continue.
- **Permission check**: `report.view` for `user_id` on the report's workspace. If it is denied, set the row to `failed` with the error `permission denied`, send the failure email (Step 8), and return normally. Retrying cannot help, so do not raise.
- **Mark running**: set `state = running`, `job_id`, `attempt = ctx.attempt`, `started_at`, and `rows_written = 0`. Make this conditional on the row still being `queued` or `running`.
- **Clear the last attempt's upload**: if `upload_id` is set from an earlier attempt, call `abort_multipart` on it and ignore "not found" errors. Then clear `upload_id`.
- **Choose the key**: `exports/{report_id}/{export_id}.csv`. The key is unique to this export, so no other export can overwrite it.
- **Start the upload**: `upload_id = start_multipart('exports', key)`. Save `upload_id` on the row so a later attempt or the final failure can abort it.
- **Loop**:
  1. Call `read_report_rows(report_id, filters, cols, after_row_id=last_id, limit=5000)` against the replica.
  2. Encode the rows as CSV bytes and append them to an in-memory buffer. The header row goes first.
  3. When the buffer reaches 16 MB, call `upload_part(upload_id, part_number, buffer)`. Keep the returned etag in memory and clear the buffer.
  4. After each part, update `rows_written` and `updated_at` so the page can show progress.
  5. Stop when a read returns no rows.
- **Final part**: flush the remaining buffer as the last part. It may be under 5 MB, because the last part is allowed to be small. A report with no rows still produces one part, the header.
- **Complete**: `complete_multipart(upload_id, etags)`. Only now does the file appear at its key.
- **Memory**: at most one 16 MB buffer plus one page of about 2 MB. The full file is never assembled. Peak use stays far below the 512 MB limit.
- **Time budget**: 2 million rows must finish inside 1,800 s. That needs at least about 1,100 rows per second, or about 0.5 MB per second. The target is 15 minutes, which means about 2,200 rows per second. Step 11 measures this.
- **Parts limit**: at 16 MB per part, 10,000 parts covers about 160 GB, far beyond the 900 MB largest report.
- **On failure**: an exception, timeout, or worker death ends the attempt. The queue retries after 60 s or 300 s. The incomplete upload is invisible, so no partial file is downloadable. The next attempt aborts the saved `upload_id` (see above). If the worker died before `upload_id` was saved, the bucket's 24-hour rule discards the incomplete upload. Retries restart from row 0 because parts and etags are not saved between attempts.

## Step 7: Finish: mark done and email the link

- **Starts**: `complete_multipart` succeeded in Step 6.
- **State change**: set `state = done`, `file_key`, `completed_at`, and final `rows_written`. Make this conditional on `state = running` and `attempt = ctx.attempt`. If it matches no row, another attempt has taken over, so stop.
- **Link**: `signed_url('exports', file_key, 86400)`, a link valid for 24 hours.
- **Email**: `send_email(user_id, 'report_export_ready', {report_id, export_id, download_url, expires_at})` (template name proposed). After it succeeds, set `email_sent_at`.
- **Email-only path**: if the start check (Step 6) finds `state = done` and `email_sent_at` is null, it sends the email and sets `email_sent_at`. It does not rebuild the file. This covers a failed email after the state was saved.
- **On failure**:
  - If the state update fails after `complete_multipart`, the attempt is retried and rebuilds to the same key with equivalent content. The old object is replaced, so this is harmless.
  - If the email fails, the attempt is retried. The start check then takes the email-only path, so the file is not rebuilt.

## Step 8: Final failure

- **Starts**: the queue calls `on_final_failure(ctx, payload, error)` after the third attempt fails. A timeout or worker death counts as a failure.
- **State change**: set `state = failed`, `error` (the last error, shortened), and `completed_at`. Make this conditional on the row not already being `done` or `failed` for this export. If no row matches, stop.
- **Cleanup**: if `upload_id` is set, call `abort_multipart` (best effort). No file is visible at the key, so nothing else needs deleting.
- **Email**: `send_email(user_id, 'report_export_failed', {report_id, export_id})` (template name proposed).
- **On failure**: the state is saved before the email, so the page shows `failed` even if the email fails. The queue calls `on_final_failure` only once, so a failed email is not retried automatically. Log it for follow-up (Open question 8).
- **Page effect**: the page shows `failed` and offers Start again, which runs Step 5 again.

## Step 9: Show the export status on the page

- **Starts**: page load, and polling while an export is active.
- **Endpoint**: `GET /api/reports/{id}/exports/latest` (proposed). It requires `report.view` and returns the caller's most recent export for this report by `created_at`. The response holds `state`, `rows_written`, `filters`, `error`, and whether a download is available. It reads the export table on the primary. That is allowed, because it is export state and not report rows.
- **Page behaviour**:
  - On load, call the endpoint.
  - If the state is `queued` or `running`, poll every 5 seconds until it is `done` or `failed`. Show `rows_written` as progress.
  - If `done`, show a Download button (Step 10).
  - If `failed`, show the error and a Start again button.
  - If no export exists, show Download CSV.
- **On failure**: if the status call fails, keep the last known state, show a retry message, and keep polling. Browsing the table does not depend on export state.

## Step 10: Download the finished file

- **Endpoint**: `GET /api/reports/{id}/exports/{export_id}/download` (proposed).
- **Checks**: `report.view`, and the export belongs to the caller. Otherwise 403 or 404.
- **State rules**:
  - If `state` is not `done`, return `409`.
  - If `completed_at` is more than 7 days ago, the bucket has deleted the file. Return `410 Gone`, and the page says the export has expired and offers a new one.
- **Response**: `302` to `signed_url('exports', file_key, 86400)`. A fresh 24-hour link is made on every click.
- **Data moved**: none. The file is served by the bucket.
- **On failure**: if signing fails, return `500`. A retry works because nothing was changed.
- **Note**: anyone who holds a signed link can download the file for 24 hours. The emailed link has the same property, which the brief accepts.

## Step 11: Prove the limits before release

- **Speed**: run the job against the 2-million-row report on the read replica. Record rows per second and total time. Target 15 minutes, with a hard limit of 30 minutes. If it is slower, the options are a larger page size, reading row ranges in parallel, or raising `ATTEMPT_TIMEOUT_SECONDS`. The last one changes the shared queue config and needs its owner's approval.
- **Memory**: run a worker with its 512 MB limit and record peak memory with the 16 MB part buffer.
- **Failures**: kill a worker mid-run, make `upload_part` raise, and exceed the timeout in a test. Confirm that the retry restarts, that no partial file can be downloaded, and that after the third failure the state is `failed` and one failure email is sent.
- **Duplicates**: run the handler twice for one `done` export. Confirm no second file is built and no duplicate email is sent.
- **Concurrency**: send two simultaneous clicks for one report. Confirm one export row exists and both responses point to it.
- **Small path**: a 10,000-row report streams back within 60 seconds, and its bytes match a reference CSV.
- **CSV**: quoting of commas, quotes, and newlines matches RFC 4180.

## Open questions and decisions for the owner

1. **Same report, different filters**: per the brief, a second click returns the active export even if its filters differ. Confirm this is intended. The page must show the active export's filters, as Step 5 returns them.
2. **Expired exports**: the brief lists four states. After 7 days a `done` export is gone. This plan treats `expired` as a display rule (Step 10), not a fifth state. Confirm.
3. **Snapshot consistency**: the nightly rebuild could change `row_id` values during a 15-minute export. Keyset paging could then skip or repeat rows. Decide whether rebuilds wait for running exports, or whether each export records a snapshot id.
4. **Permission removed after queueing**: Step 6 re-checks at job start and fails without retry. Confirm.
5. **Stale `row_count`**: the threshold uses a nightly value. Step 4's guard covers the small path. Confirm the 409 retry message is acceptable.
6. **Spreadsheet formula injection**: cells starting with `=`, `+`, `-` or `@` can run formulas when opened in a spreadsheet. Decide whether to prefix such cells.
7. **Export record retention**: the table keeps one row per large export. The brief sets no cleanup job for files. Decide how long to keep rows; they are small.
8. **Email failures**: no automatic retry exists for the failure email (Step 8) or the ready email beyond the email-only path in Step 7. Decide whether this is acceptable or needs its own retry.