# CSV export for the reports page: implementation plan

## Terms used in this plan

- **Keyset paging**: fetch the next page with `WHERE row_id > last_row_id ORDER BY row_id LIMIT n`. Never OFFSET. The first page has no `row_id` condition.
- **Read replica**: a read-only copy of the database. Report rows are read only from it.
- **Export row**: one record in the primary database per large export. It holds the export's state and never holds report rows.
- **Multipart upload**: object storage accepts a file as numbered parts. Nothing is visible at the final key until `complete_multipart` succeeds. `abort_multipart` discards the parts. Each part except the last must be at least 5 MB. There are at most 10,000 parts.
- **Queue context (`ctx`)**: the queue gives each job handler a `ctx` with `job_id` and `attempt` (1, 2 or 3). The queue sets these; this plan does not.
- **Attempt**: one run of a job handler. The queue allows 3 attempts, waits 60 s before attempt 2 and 300 s before attempt 3, and kills any attempt still running after 1,800 s. A worker that dies also counts as a failed attempt, and the queue schedules the next one. Each attempt starts from the beginning.
- **Dead attempt**: an attempt that was killed, or whose worker died. No code runs after that, so the export row keeps the state the attempt last wrote.
- **Delivery at least once**: a handler can run again for a job that already succeeded. Every step tolerates this.
- **Heartbeat**: none. Every write to the export row sets `updated_at`. The longest gap between writes in a healthy export is about 35 minutes, under the 2-hour stale rule in step 4.

## Overview

1. The user clicks **Download CSV** once. The page calls the sync endpoint (step 3). If that answers 409 (too large), the page calls the large-export endpoint (step 4) in the same click. The user sees 'Preparing export' and never has to click again. If the sync call answers any other error (400, 403, 404 or 500), the page shows that error's message, and no export is started.
2. At 10,000 rows or fewer, the CSV comes back in the step 3 response. Nothing is stored.
3. Above 10,000 rows, step 4 creates an export row, queues a job and returns at once. The job (steps 5 to 7) streams the rows into a multipart upload in the `exports` bucket, marks the row done and emails a 24-hour link (step 8). The page polls the row and shows its state (step 10).

If step 4 answers with an error (for example 503, when the job could not be queued), the page shows 'Could not start the export' with a **Try again** button. The page does not retry by itself. Try again repeats the click from step 3.

## Steps

### Step 1. Add the export state table

- **Starts**: a database migration, run during deploy.
- **Data**: no report rows. Table `report_exports` in the primary database, with columns `export_id` (UUID, primary key), `user_id`, `report_id`, `filters` (text, max 4 KB), `cols`, `status` (`queued`, `running`, `done` or `failed`), `attempt` (0 until the first claim), `job_id`, `upload_id`, `object_key`, `row_count`, `created_at`, `started_at`, `completed_at`, `expires_at`, `email_sent_at`, `error_summary` (short text, never row content) and `updated_at`.
- **State**: the table. A partial unique index on `(user_id, report_id)` where `status IN ('queued', 'running')` enforces one active export per user per report.
- **Fails**: a failed migration stops the deploy with nothing changed. To roll back, drop the table. Nothing uses it before step 4 ships.

### Step 2. Shared row reader

- **Starts**: called by step 3 with the `filters` and `cols` from the page URL, and by step 6 with the `filters` and `cols` stored on the export row.
- **Data out**: CSV lines as a stream, header row first. The header lists the `cols` names in URL order.
- **Validation**: check every column name and filter field against the allowlist the page already uses. Reject anything else with 400. Never put raw URL text into SQL.
- **Query**: against the replica, in pages of 5,000 rows: `SELECT ... FROM report_rows WHERE report_id = ? AND <filters> AND row_id > ? ORDER BY row_id LIMIT 5000`. The first page has no `row_id` condition. Write CSV with the standard `csv` module, encoded as UTF-8.
- **Stop**: when a page comes back empty. A database error raises and is never read as the end of the data, because a silently truncated file is worse than a failed one.
- **State**: none. One page is in memory at a time.
- **Fails**: the reader raises and does not catch. The caller decides what happens next.

### Step 3. Synchronous path (10,000 rows or fewer)

- **Starts**: `GET /api/reports/{id}/export.csv?filters=...&cols=...`, sent by the click.
- **Checks, in order**:
  1. The caller has `report.view` on the report's workspace. Otherwise 403.
  2. Read `reports.row_count` from the replica. If it is above 10,000, return 409 with a body that says to use the large path.
- **Data**: the step 2 reader writes the CSV into an in-memory buffer. If it produces more than 10,000 rows (for example, because `row_count` is stale), discard the buffer and return 409. The cap keeps memory to a few megabytes.
- **Response**: 200 with `Content-Type: text/csv`, `Content-Disposition: attachment; filename=...` and `Content-Length`. The body is sent only after it is fully built.
- **State**: none. No row, queue entry or email.
- **Fails**: 400 for bad filters or columns, 403 for no permission, 404 for an unknown report, 409 for the large path, 500 for a database error. Nothing was sent before the body was complete, so no partial file exists and nothing needs cleaning up.

### Step 4. Large path: the click creates an export row (above 10,000 rows)

- **Starts**: `POST /api/reports/{id}/exports` with the same `filters` and `cols`. The page sends it when step 3 returns 409.
- **Checks**: `report.view`, then validation with the step 2 parser. The filters string is at most 4 KB.
- **Clear stale rows first**: set `status = failed` and `error_summary = stale` on this user's active rows for this report that are stale. An active row is stale when `updated_at` is older than 2 hours, or when it is `queued`, has no `job_id` and `created_at` is older than 5 minutes. This update must run before the insert, because the partial unique index would otherwise block the insert on a stale row. The longest healthy export is about 96 minutes, so 2 hours is safe. A job that later runs for a row marked failed exits at step 5.
- **Insert**: a row with `status = queued`, `user_id`, `report_id`, `filters`, `cols` and `created_at`. The filters and columns live on the row, not in the job payload.
- **One at a time**: if the insert conflicts with the index, read the existing active row and return it with 200. No second job starts. This also covers two clicks that arrive together.
- **Enqueue**: `job_id = enqueue('build_report_export', {export_id})`. The payload is only the id. Then save `job_id` on the row. The job can start before this save. That is harmless, because step 5 also writes `job_id`, and both carry the same value.
- **Response**: 202 with `export_id`, `status`, `created_at` and `attempt`. The request does not wait for the file. The page starts polling from this response (step 10).
- **State**: the export row from step 1.
- **Fails**: if `enqueue` raises, set the row to `failed` with `error_summary = could not queue` and return 503. The page then offers Try again (Overview). If the process dies after the insert but before the enqueue, the row has no `job_id`, and the stale rule clears it on a later click after 5 minutes.

### Step 5. The queue starts the job: claim the export

- **Starts**: the queue runs `build_report_export` with `ctx` and payload `{export_id}`.
- **Data**: read the export row by `export_id`.
- **Decision**:
  - No row, `status = failed`, or `status = done` with `email_sent_at` set: exit successfully.
  - `status = done` and `email_sent_at` null: go to step 8 only.
  - `status = running` and `attempt >= ctx.attempt`: another copy of an attempt at least this new is active. Exit. If that copy later dies, the queue counts the death as a failed attempt and schedules the next one, which has a higher number and passes this check. If the dead copy was attempt 3, the queue calls step 9 instead.
  - Otherwise (`status = queued`, or `status = running` with a lower `attempt`): claim it. One conditional update sets `status = running`, `attempt = ctx.attempt`, `started_at = now`, `job_id = ctx.job_id` and `updated_at = now`, where `export_id`, `status` and `attempt` still match what was read. If zero rows change, another copy won the race: exit. Otherwise go to step 6.
- **Why a row can stay `running` between attempts**: a `running` row with a lower `attempt` number is a dead attempt (killed at 1,800 s, or its worker died). It runs no code, so nothing reset its row. An attempt that raises does not leave the row `running`: the failure rule in step 7 sets it to `queued` first.
- **State**: the export row.
- **Fails**: a database error during the read or claim raises, and the queue retries. The page keeps its last state, at most one attempt behind.

### Step 6. Stream rows into a multipart upload (the heavy step)

- **Starts**: a successful claim in step 5.
- **Key**: `reports/{report_id}/exports/{export_id}.csv` in the `exports` bucket. The key is unique per export, so a retry can only replace its own file.
- **Clean up an earlier attempt**: if the row has an `upload_id`, call `abort_multipart(upload_id)` and ignore 'not found' errors. Then call `start_multipart(bucket, key)` and save the new `upload_id` on the row before any part is uploaded. A later attempt can then abort it even if this one dies.
- **Every attempt starts from the first page.** Earlier etags are never read or reused, so an attempt never continues an earlier upload.
- **Row-count check, start**: read `reports.row_count` from the replica as `N0`.
- **Loop**: run the step 2 reader with the `filters` and `cols` from the export row. Append its CSV bytes to a buffer. When the buffer reaches 8 MB, call `upload_part(upload_id, part_number, bytes)`, keep the returned etag with its part number, and clear the buffer. Part numbers start at 1. After the last page, upload any remaining bytes as the final part, which may be smaller than 5 MB.
- **Row-count check, end**: read `reports.row_count` again as `N1`. If `N1 != N0`, the nightly rebuild ran during the export. Raise, so the queue retries.
- **Memory**: one page of 5,000 rows plus one 8 MB buffer. The whole report is never held in memory. A 900 MB CSV needs about 115 parts.
- **Deadline**: 2,000,000 rows in 1,800 s needs at least 1,112 rows per second. Step 11 sets the gate at 2,500 rows per second. If the measured rate is too low, the options are: (a) a faster query or CSV writer; (b) up to 4 parallel part uploads, each with its own 8 MB buffer, still within memory; (c) split the work into jobs by `row_id` range, each uploading parts to the same `upload_id`, plus a completion job. Option (c) needs its own design before it is built.
- **State**: `upload_id` and `updated_at` on the row. The etags exist only in the worker's memory and are lost when the attempt ends.
- **Fails**: the failure rule in step 7 applies to any exception. If the attempt is killed or its worker dies, no code runs and the upload stays open. The next attempt aborts it by the saved `upload_id`, or step 9 does after attempt 3. Nothing is visible at the key until step 7.

### Step 7. Complete the file and mark the export done

- **Starts**: the loop finishes and the `N1` check passes.
- **Action**: call `complete_multipart(upload_id, etags)`. The object appears at the key and replaces any object already there. The only object that can already be there comes from an earlier attempt of this same export.
- **Then**: a conditional update sets `status = done`, `completed_at = now`, `object_key`, `row_count` (rows written), `expires_at = completed_at + 7 days - 1 hour` and `updated_at = now`, where `status = running` and `attempt = ctx.attempt`. The one-hour margin keeps the page from offering a link to a file the lifecycle rule is about to delete. If zero rows change, the export was taken over or marked failed: exit without sending email.
- **State**: the export row.
- **Failure rule for steps 6 and 7**: on any exception:
  1. Call `abort_multipart(upload_id)` on a best-effort basis and ignore its errors.
  2. Run a conditional update that only applies where `status = running` and `attempt = ctx.attempt`. If `ctx.attempt < 3`, it sets `status = queued` and a short `error_summary`, so the page shows 'waiting to retry'. On attempt 3 it leaves the status alone, and step 9 sets it. The condition means an attempt that was taken over cannot change a newer attempt's row.
  3. Re-raise. The queue waits, then starts the next attempt, which runs step 5 again.
- **Two cases the rule leaves behind**:
  - If `complete_multipart` already succeeded, the abort finds nothing. The next attempt rebuilds the whole file from the first page and replaces the object at the key.
  - If the update in step 7 never happened (for example, the database is down), the row stays `running` with this attempt's number and `upload_id`. The next attempt takes it over in step 5. After attempt 3, step 9 marks it failed.

### Step 8. Email the download link

- **Starts**: directly after step 7 marks done, or when step 5 routes a `done` row with no `email_sent_at` here.
- **Action**: `url = signed_url(bucket, object_key, 86400)`. Call `send_email(user_id, report_export_ready, {report_id, export_id, download_url: url, link_expires_at: now + 24h})`. On success, set `email_sent_at = now`.
- **Status**: this step never changes `status`.
- **Independent of the page**: the page's Download button does not wait for this step and does not check `email_sent_at` (step 10). A user who clicks Download before the email is sent gets the file. The email may arrive later, or not at all if it fails.
- **Data**: the link is a bearer URL. Anyone holding it can download the CSV until it expires.
- **State**: `email_sent_at` on the row.
- **Fails**: if `send_email` raises, raise. The queue retries, and step 5 routes the retry back here with a new link and a fresh 24 hours. If every attempt fails, step 9 sees `done` and does not mark the export failed. The failure is logged for operations. If the email is sent but setting `email_sent_at` fails, the retry sends a second email, which is acceptable under at-least-once delivery.

### Step 9. Final failure

- **Starts**: the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 has failed. This includes timeouts and dead workers.
- **Action**:
  1. If the row has an `upload_id` and `status` is not `done`, call `abort_multipart(upload_id)` on a best-effort basis and ignore errors. This discards the open upload that a killed attempt 3 left behind.
  2. Conditional update: `status = failed`, `error_summary` (the error text cut to 500 characters, with no row content) and `updated_at = now`, where `export_id` matches and `status <> done`.
  3. Only if step 2 changed a row, call `send_email(user_id, report_export_failed, {report_id, export_id})`.
- **State**: the export row.
- **Fails**: a failed abort or email is logged and not raised. If the status update fails, raise. The queue's behaviour in that case is an assumption (open question 4). A row left `running` is cleared by the 2-hour rule in step 4.

### Step 10. Status and download on the page

- **Starts**: the page loads, or step 4 returns an export. The page polls `GET /api/reports/{id}/exports/latest` every 5 seconds while the latest export is `queued` or `running`. Polling stops on `done` or `failed`.
- **Finding the export**: `GET /api/reports/{id}/exports/latest` checks `report.view` and returns the caller's most recent export for this report, in any status, as 200 with the export. If the caller has no export for this report, it returns 204 with no body. The 200 response includes `export_id`, `status`, `attempt`, `filters`, `cols`, `created_at`, `completed_at`, `row_count`, `expires_at` and a short `error`. Because the server holds the state, a new tab shows the same export with no id in the URL. It never returns another user's export.
- **No export yet**: on page load, a 204 from `latest` (or a 403 for a user without `report.view`) shows no status line. The page shows only the **Download CSV** button.
- **After a 202 from step 4**: the page shows 'Queued' at once, from the 202 body, and starts polling. The row is saved before the 202 is sent, so the first poll returns that same row. If a poll fails, the page keeps the last state on screen and polls again on the next tick.
- **Which path a click takes**: the page does not choose between steps 3 and 4 by itself. It asks step 3 first, and only a 409 leads to step 4. Any other error from step 3 is shown as the Overview describes, and no export starts. If an export is already active, step 4 returns that row with 200, so the click shows the active export and starts no second job.
- **Display**:
  - `queued` with `attempt = 0`: 'Queued'.
  - `queued` with `attempt > 0`: 'Retrying, attempt N of 3', where N = `attempt + 1`. `attempt` holds the last attempt that ran.
  - `running`: 'Running, attempt N of 3', where N = `attempt`.
  - `done`: 'Ready', with a Download button while `now < expires_at`. Otherwise 'Expired. Export again'.
  - `failed`: 'Failed', with a 'Try again' button that calls step 4.
  - If the export's `filters` or `cols` differ from the page's current URL, say so and show the export's own filters. Step 4 returns the active export whatever the URL says, so this case happens.
- **Download**: `GET /api/reports/{id}/exports/{export_id}/download` checks `report.view`, that the caller owns the export, and `status = done` with `now < expires_at`. It returns a 302 to `signed_url(bucket, object_key, min(86400, expires_at - now))`. Each click gets a fresh link, separate from the emailed one. It does not check `email_sent_at`.
- **State**: none beyond the export row. The browser holds only the polling timer.
- **Fails**: 403 for no permission. 404 for an unknown export or another user's export. 410 when the export has expired.

### Step 11. Verification before rollout

- **Unit tests**: the keyset reader uses `row_id`, never OFFSET; it stops on an empty page; it raises on a database error and yields nothing after the error. The CSV writer keeps column order, quotes commas, quotes and newlines, and rejects unknown columns.
- **State tests**: duplicate delivery of a done export; takeover of a dead `running` attempt; email-only retry; a stale active row is marked failed before the insert; a failure rule that does not overwrite a newer attempt's row; the final failure hook does not overwrite `done` and sends no email when it changes nothing.
- **Failure injection on a staging bucket**: kill the worker mid-upload; make `complete_multipart` fail; make `send_email` fail. Confirm no object exists at the key before completion, and that an aborted upload leaves no object.
- **Boundaries**: 10,000 rows takes the sync path; 10,001 takes the large path; with a stale `row_count` and more than 10,000 rows, the sync path returns 409.
- **Concurrency**: 20 simultaneous POSTs from one user for one report create exactly one row and one job.
- **Permissions**: a user without `report.view` gets 403 from every endpoint, including download with a valid `export_id`.
- **Load gate**: on a 2,000,000-row report against a replica-sized database, end-to-end time is 800 s or less (and under 1,800 s in any case), and peak memory is 256 MB or less (and under 512 MB in any case). The 10,000-row sync path finishes well inside 60 s.
- **Email**: the emailed link downloads the complete file within 24 hours.

### Step 12. Rollout and monitoring

- **Starts**: release behind a feature flag. The flag disables the large path (step 4 and the page's large-path behaviour) and leaves the sync path on.
- **Metrics**: exports started, attempts, failures by error type, duration, rows per second, file size, stale rows cleared, and the rate of 409 responses from step 3.
- **Rollback**: turn the flag off. Existing export rows and files remain until the lifecycle rule removes them. No migration is reversed.

## Open questions and assumptions

1. **Nightly rebuild and `row_id`**: the brief does not say whether the rebuild renumbers rows. If it does, a rebuild during an export could corrupt the file. The `N0`/`N1` check in step 6 catches a change in count, but not a renumbering that keeps the count. Confirm with the owners, and consider a rebuild version id on `reports`. Running large exports outside the rebuild window is the fallback.
2. **Replica reads of `reports.row_count`**: assumed allowed, because it is report metadata.
3. **Email templates**: `report_export_ready` and `report_export_failed` are not in the brief and must be created. Assumed: `send_email` raises on failure.
4. **Final failure hook**: assumed that an error inside `on_final_failure` is logged by the queue and not retried.
5. **Bearer links**: the emailed link and the page links work for anyone who holds them for their lifetime, even if the user later loses `report.view`. The brief does not say whether this is acceptable.
6. **CSV hygiene**: not in the brief. Cells that start with `=`, `+`, `-` or `@` can run as formulas in a spreadsheet. Decide whether to prefix them, and whether to write a UTF-8 byte-order mark so Excel reads the encoding.
7. **Sync decision uses total rows**: as the brief asks, the choice uses the unfiltered `row_count`. A filter that leaves 50 rows on a 2,000,000-row report still takes the large path. The page should say so.
8. **Retention**: the 7-day deletion rule already exists on the `exports` bucket (see `existing/storage.py`). It is not part of this plan, and nothing here sets it up. This plan only uses it to compute `expires_at`. The page offers downloads until `expires_at`. The emailed link is made at completion and lasts 24 hours, so it expires before the file does.