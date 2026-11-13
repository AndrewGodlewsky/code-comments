# CSV export for the reports page: implementation plan

## Overview

The reports page (`/reports/{report_id}`) shows one report as an infinite-scrolling table. This plan adds a **Download CSV** button. The button exports exactly what the user is looking at: the filters and column order in the page URL, plus a header row.

The export takes one of two paths, chosen by `reports.row_count`:

- **Small (10,000 rows or fewer):** the click response is the CSV. No job runs and nothing is stored.
- **Large (more than 10,000 rows):** the click returns at once with an export record. A background job writes the CSV to the `exports` bucket in parts, then emails the user a 24-hour download link. The page shows the export's state until it finishes.

### Terms used below

- **Read replica:** a read-only copy of the primary database. Report rows (`report_rows`) may only be read from it, never from the primary.
- **Keyset paging:** reading rows in order with `WHERE row_id > :last ORDER BY row_id LIMIT n`. It is used instead of OFFSET so every page is equally fast.
- **Job queue:** the existing background queue. A job handler is a function `handler(ctx, payload)`. An attempt fails if the handler raises, exceeds the 1800-second attempt timeout, or its worker dies. Failed attempts are retried after 60 s and then 300 s, for 3 attempts in total. The queue keeps no progress between attempts: each attempt starts the handler again with the same payload. `on_final_failure(ctx, payload, error)` runs once after the last failed attempt. Delivery is at least once, so a handler may run again after it has succeeded.
- **Worker:** a process with 512 MB of memory that runs one attempt at a time.
- **Multipart upload:** object storage builds an object from numbered parts (part 1, 2, ...). Each part except the last must be at least 5 MB, and there can be at most 10,000 parts. Nothing is visible at the key until `complete_multipart` succeeds, and that step is atomic. `abort_multipart` discards the parts. Incomplete uploads are discarded automatically after 24 hours.
- **Export record:** a new row in the primary database table `report_exports`. It holds an export's state and is not report data. Its columns are `id`, `user_id`, `report_id`, `filters`, `cols`, `status` (`queued`, `running`, `done` or `failed`), `job_id`, `attempt`, `upload_id`, `object_key`, `parts` (a list of `{part_number, etag}`), `last_row_id`, `rows_written`, `error`, `email_sent_at`, `created_at`, `updated_at` and `completed_at`.
- **`exports` bucket lifecycle:** every object is deleted 7 days after creation. This plan adds no cleanup job.

---

## Steps

### 1. The user clicks Download CSV

- **Starts when:** the user clicks the button on the reports page.
- **Data moves:** the browser reads `filters` and `cols` from the current page URL and sends them to `POST /api/reports/{report_id}/exports`. The body is JSON with those two fields. Nothing else is sent.
- **State kept:** none in the browser.
- **On failure:** a network error or a 5xx response shows an inline error with a Retry button. The browser downloads the file only after the whole response has arrived (fetch to blob), so a connection cut midway raises an error instead of saving a truncated file.

### 2. The API checks the request and picks a path

- **Starts when:** step 1's request reaches the API.
- **Data moves:**
  1. Check that the caller has `report.view` on the report's workspace. If not, return 403. This is the same check the page uses.
  2. Validate `filters` and `cols` with the same parser the page API uses. Every name in `cols` must be a known column. Unknown names or malformed filters return 400.
  3. Read `reports.row_count`. This is the unfiltered total. Metadata is not report rows, so either the primary or the replica may serve it.
  4. If `row_count` is 10,000 or fewer, go to step 3. Otherwise, or if `row_count` is missing, go to step 4. A missing count takes the large path so that an unknown-size report is never built in the request.
- **State kept:** none.
- **On failure:** 403 if the permission check fails. 400 if validation fails. 404 if the report does not exist. A database error returns 500, and nothing has been started.

### 3. Small path: the response is the CSV

- **Starts when:** `row_count` is 10,000 or fewer.
- **Data moves:** the API reads the report's rows from the **read replica** with the same keyset query and filters the page uses, 500 rows per query. It writes a header row, then one CSV line per row in the `cols` order. Fields containing commas, quotes or newlines are quoted per RFC 4180. The response is `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. Nothing is stored.
- **State kept:** none. The request holds the data only while it streams.
- **On failure:** if the replica or the request fails partway, the API ends the response with an error status. Because the browser downloads only after the body is complete (step 1), the user sees an error, not a partial file. The request has a 60-second limit. At 10,000 rows, a 20-query stream is well within that. If the limit is ever exceeded, the same error path applies.

### 4. Large path: record the export

- **Starts when:** `row_count` is above 10,000, or is missing.
- **Data moves:** the API inserts one row into `report_exports` in the primary database with `status = queued`, `user_id`, `report_id`, the canonical `filters` and `cols`, and `created_at`. Before inserting, it checks for an active export of this report by this user. The rule is: at most one export per user and report may be `queued` or `running`. The database enforces this with a unique partial index on `(user_id, report_id)` where `status` is `queued` or `running`. If an active export exists, return it with `200` and do nothing else. This is how a second click returns the existing export.
- **Stale active rows:** a `queued` row with no `job_id` after 5 minutes, or a `queued` or `running` row not updated for 2 hours, is treated as dead. The click marks it `failed` with the reason `stale` and then inserts a new row. This guard stops a crash between steps 4 and 5, or a failed `on_final_failure` call, from blocking the user forever. It is not a cleanup job.
- **State kept:** the export row, in the primary database.
- **On failure:** a database error returns 500 and nothing is queued. A unique-index conflict is not a failure. It is handled as the "return the existing export" case above.

### 5. Enqueue the export job

- **Starts when:** step 4 inserted a new row.
- **Data moves:** the API calls `enqueue("build_csv_export", {"export_id": id})`. The payload holds only the ID, far under the 64 KB limit. The job reads everything else from the export row. The API then saves the returned `job_id` on the row and returns `202` with the export record.
- **State kept:** the row (`status = queued`, `job_id` set) and the queue's own record of the job.
- **On failure:**
  - If `enqueue` raises, the API sets the row to `failed` with `error = "could not start"` and returns `503`. The user can click again.
  - If the process dies between the insert and the `enqueue` call, the row stays `queued` with no `job_id`. The stale guard in step 4 clears it on the next click.

### 6. Job attempt starts: claim the export

- **Starts when:** the queue starts an attempt of `build_csv_export`. The attempt number is 1, 2 or 3.
- **Data moves:**
  1. Load the export row by `export_id`.
  2. If the status is `done` or `failed`, end the attempt. A redelivered job must do nothing once the export has finished.
  3. Recheck `report.view` for the user. Access may have been removed since the click. If it was, mark the export `failed` with `error = "access removed"`, do not send a link, and end the attempt.
  4. Claim the row with a conditional update that only succeeds if `status` is `queued` or `running`. Set `status = running`, `attempt` to the current attempt number, and `updated_at`. Every later checkpoint is fenced on `attempt`, so a stale attempt that is still running cannot overwrite a newer one's progress.
- **State kept:** the row (`status = running`, `attempt`).
- **On failure:** a database error raises, and the queue retries the attempt.

### 7. Start or resume the multipart upload

- **Starts when:** step 6 claims the export.
- **Data moves:**
  - **Fresh export** (`upload_id` is empty): call `start_multipart("exports", key)` with `key = "report-exports/{export_id}.csv"`. Save the returned `upload_id` on the row. Use a key that is unique per export, so a completed file never overwrites another export's file. Nothing is visible at the key yet.
  - **Resumed export** (`upload_id` is set): keep the existing `upload_id`. Read `parts` and `last_row_id` from the row. Continue from step 8 at `last_row_id`. Do not call `abort_multipart`. The parts already uploaded are reused.
- **State kept:** `upload_id`, `object_key`, `parts` and `last_row_id` on the row.
- **On failure:**
  - If `start_multipart` raises, the attempt fails and the queue retries.
  - If a resumed upload is gone (for example, it passed the 24-hour lifecycle or was aborted), the next `upload_part` or `complete` call fails with an unknown-upload error. The job then clears `upload_id`, `parts` and `last_row_id`, starts a fresh upload, and rewrites from the beginning. It treats the attempt as failed, so the queue retries it.

### 8. Stream rows from the replica into parts

- **Starts when:** step 7 has an upload ready.
- **Data moves:**
  1. Read `report_rows` from the **read replica** in keyset batches of 10,000 rows: `WHERE report_id = :report AND <filters> AND row_id > :last ORDER BY row_id LIMIT 10000`. Use the same query builder as the page API, so the CSV matches the page. Use the batch size from the page's `limit=500` only as a reference, because larger batches fit the time budget.
  2. Format each batch to CSV in the `cols` order. Write the header row first, into part 1.
  3. Append the formatted text to an in-memory buffer. When the buffer reaches 8 MB, upload it with `upload_part(upload_id, part_number, data)`. Part numbers count from 1.
  4. After each successful `upload_part`, save a checkpoint with one conditional update, fenced on `attempt`: append `{part_number, etag}` to `parts` and set `last_row_id` to the last `row_id` in that part. Only the part and checkpoint writes change state, so the saved `last_row_id` always matches the saved parts.
- **Memory:** one 10,000-row batch and one 8 MB buffer, about 30 MB in total. The job never holds the whole report, which stays well inside the 512 MB worker limit.
- **Size:** the largest report is about 2 million rows and 900 MB of CSV. At 8 MB per part, that is about 115 parts, far under the 10,000-part limit.
- **Time:** the attempt timeout is 1800 seconds. The plan depends on finishing one large export within that time, so measure before release. Measure the replica read time per batch and the upload time per part against the largest report in staging. Keep a margin of at least 20 percent. If the work does not fit, the checkpoints let later attempts continue, but the queue allows only 3 attempts, so a job that times out three times fails.
- **State kept:** the parts already uploaded (in the bucket, incomplete and invisible), and the checkpoints (`parts`, `last_row_id`) in the row.
- **On failure:**
  - Replica query error: the attempt fails. The next attempt resumes from `last_row_id`.
  - `upload_part` error: the attempt fails. The buffer is lost, but the rows after the last checkpoint are read again, so no data is missing.
  - Attempt timeout or worker death: the same as above. Resume from the last checkpoint.
  - A checkpoint write that fences out (`attempt` no longer matches): the attempt stops without writing anything.
  - A part uploaded but not checkpointed is uploaded again with the same part number on resume, which replaces it.
- **Open risk:** the nightly rebuild may change `report_rows` while a multi-attempt export is resuming. Rows from before and after the change could then be mixed. See Open question 3.

### 9. Finish the upload and make the file visible

- **Starts when:** step 8 has read the last batch.
- **Data moves:** upload any remaining buffered rows as the final part. The last part may be smaller than 5 MB. Then call `complete_multipart(upload_id, etags)`, where `etags` is the full ordered list from `parts`. Completion is atomic: the object appears at its key only when this call succeeds, so a half-written file is never downloadable.
- **State kept:** after completion the file is in the `exports` bucket at its key. Save `rows_written`, and set `status = done` and `completed_at` with a conditional update fenced on `attempt`.
- **On failure:**
  - If `complete_multipart` fails, the attempt fails. The parts are still stored (within 24 hours), so the next attempt calls `complete_multipart` again with the saved etags.
  - If `complete_multipart` succeeds but the database update fails, the next attempt finds no upload, because it has completed. The job must check whether the object exists before starting over. `storage.py` has no existence check today, so one must be added. See Open question 4. If the object exists, the job marks the export `done` and continues to step 10.

### 10. Send the download link

- **Starts when:** the export is `done` and `email_sent_at` is empty.
- **Data moves:** call `signed_url("exports", object_key, 86400)` to get a URL that works for 24 hours. Then call `send_email(user_id, "export_ready", {report_id, export_id, url, expires_at})`. After the email succeeds, set `email_sent_at`.
- **State kept:** `email_sent_at` on the row, so a redelivered or retried attempt does not send the email twice. Delivery is at least once, so a crash between the send and the flag write can still produce one duplicate. The email service has no idempotency key in the existing helper.
- **On failure:** if `send_email` raises, the attempt fails and is retried. The retry sees `status = done` with an empty `email_sent_at`, so it sends the email again. If all 3 attempts fail, step 12 runs, but it must leave a `done` export as `done` (see step 12).

### 11. The page shows the export's state

- **Starts when:** the reports page loads, the user clicks Download CSV, or the user returns to the report later.
- **Data moves:**
  - The page calls `GET /api/reports/{report_id}/exports/latest`. The API checks `report.view` and returns the user's most recent export of this report: `status`, `created_at`, `completed_at`, `error`, and for `done` exports a fresh signed URL valid for 24 hours. The URL is generated on each request. The API returns `expired` instead of a link when `created_at` is more than 7 days ago, or the object is gone.
  - While the status is `queued` or `running`, the page polls every 3–5 seconds. It stops when the status is `done` or `failed`.
  - The page shows the `filters` and `cols` of the returned export. A second click may return an earlier export with different filters (see Open question 1).
- **State kept:** the export row only. The page keeps no state of its own, so state survives a reload.
- **On failure:** if the status request fails, the page shows the last known state and retries on the next poll. A `failed` status shows the stored `error` text (a short message, never a stack trace) and a **Try again** button. That button starts a new export, because `failed` is not an active state.

### 12. Final failure

- **Starts when:** the third attempt fails, or the queue calls `on_final_failure(ctx, payload, error)`.
- **Data moves:**
  1. If the export is already `done` (only the email failed), do not mark it failed. Log the error. The user still sees the download link on the page. Leave `email_sent_at` empty so an operator can resend.
  2. Otherwise, call `abort_multipart(upload_id)` to discard the parts. If that call fails, ignore the error, because the lifecycle rule removes the parts within 24 hours.
  3. Set `status = failed`, `error` to a short message such as "export failed after 3 attempts", and `completed_at`.
  4. Send `send_email(user_id, "export_failed", {report_id, export_id})`.
- **State kept:** the row (`status = failed`, `error`).
- **On failure:** if `on_final_failure` itself raises, the row stays `running`. The stale guard in step 4 clears it on the user's next click. Nothing else is needed.

---

## Summary of state

| Where | What | Who writes it |
|---|---|---|
| `report_rows` on the read replica | Report data | Nightly rebuild only. The export reads it and never writes it. |
| `report_exports` on the primary | Export state, parts, checkpoints, email flag | Click (step 4), job (steps 6, 7, 8, 9, 10, 12) |
| `exports` bucket, `report-exports/{export_id}.csv` | The finished CSV, visible only after completion | Job (step 9). Lifecycle deletes it 7 days after creation. |
| Incomplete multipart uploads | Parts of unfinished exports | Job. Aborted on final failure, or removed by the lifecycle after 24 hours. |
| Queue | Job and its attempts | The queue |

## Open questions and decisions for the owner

1. **Dedupe ignores filters.** The brief says a second click returns the existing export of the report. If the user changed the filters, they get the earlier export with the old filters. Decide whether the dedupe key should include `filters` and `cols`. If it does, two exports of different views can run at once, which the brief forbids. The page must at least show the filters of the returned export.
2. **The threshold uses the unfiltered count.** A filtered view of 50 rows from a 2-million-row report takes the large path, so the user waits for an email. The brief fixes the rule on `row_count`. Counting filtered rows would be more accurate but is an extra query per click and is not in the brief.
3. **Nightly rebuild during an export.** If `report_rows` is rebuilt while a multi-attempt export resumes, keyset resumption can mix old and new rows. Decide how to detect this. Options are a data-generation or version number on `reports`, or a check of `row_count` at each checkpoint. If it changes, the job must abort the upload and start again. A version number is the reliable option, and the rebuild must write it.
4. **Storage helper for an existence check.** `storage.py` has `start_multipart`, `upload_part`, `complete_multipart`, `abort_multipart` and `signed_url`, but no way to check whether an object exists. Step 9 needs one. Add a small helper, such as `object_exists(bucket, key)`. This is not a cleanup job.
5. **Email link is a bearer link.** A link works for 24 hours for anyone who holds it, even if the user later loses `report.view`. This follows from the brief. The page's link is checked against permission on each request, but the emailed link is not.
6. **Replica index.** Keyset paging by `row_id` within `report_id` needs an index on `report_rows (report_id, row_id)` on the replica. Confirm that it exists before the timing test in step 8.
7. **Retention of export rows.** The lifecycle removes files after 7 days, but `report_exports` rows are kept indefinitely. The brief rules out a cleanup job for files. Decide whether row retention needs a rule.
8. **Timing evidence.** The 1800-second attempt limit is the main risk. Do not release until a timed run of the 2-million-row report has passed inside one attempt with a 20 percent margin, or the checkpoint resumption has been tested across a forced timeout.