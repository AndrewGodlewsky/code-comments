# CSV export for the reports page: implementation plan

## Summary

The reports page (`/reports/{report_id}`) shows one report as an infinite-scrolling table. Today it loads rows in pages from the read replica, and the server stores nothing about what the user is viewing. This plan adds a **Download CSV** button that exports what the user sees (the filters and column order in the page URL, plus a header row): reports of 10,000 rows or fewer return the CSV in the click's own response, and larger reports return at once while a background job writes the file in parts and emails a link that works for 24 hours. The two paths exist because a large report cannot be built safely inside one 60-second API request, and the job writes in parts so that no worker ever holds a whole report in memory.

**Out of scope:** scheduled exports, formats other than CSV, and changes to the table on the page.

## Terms

- **Read replica:** a read-only copy of the primary database. Report rows (`report_rows`) are read only from it, never from the primary.
- **Keyset paging:** reading rows in `row_id` order, asking for the rows after the last one seen (`row_id > :last`). It is used instead of OFFSET so every page is equally fast.
- **Job queue:** the existing background queue. A job handler is a function `handler(ctx, payload)`.
- **Attempt:** one run of a job handler. `ctx.attempt` is its number: 1, 2 or 3. An attempt fails if the handler raises, runs longer than 1,800 seconds, or its worker dies.
- **Retry and final failure:** a job gets at most 3 attempts. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. Each attempt starts the handler from the beginning with the same payload, and the queue keeps no progress between attempts. After the third failed attempt, the queue calls `on_final_failure(ctx, payload, error)` once.
- **At least once:** a handler may run again after it already succeeded, so a rerun must be harmless.
- **Worker:** a process with 512 MB of memory that runs one attempt at a time.
- **Multipart upload:** object storage builds one object from numbered parts (1, 2, ...). Each part except the last must be at least 5 MB, and there can be at most 10,000 parts. Nothing is visible at the object's key until `complete_multipart` succeeds, and that call is atomic. `abort_multipart` discards the parts. Incomplete uploads are discarded automatically after 24 hours.
- **Export record:** a row in the primary-database table `report_exports`. It holds one export's state, not report data. Its columns are listed under Build and rollout.
- **Status:** the export record's state: `queued`, `running`, `done` or `failed`.
- **Active export:** an export whose status is `queued` or `running`.
- **Checkpoint:** the progress saved on the export record after each uploaded part (`parts`, `last_row_id`, `rows_written`).
- **Fenced update:** a database update that succeeds only if the record's `attempt` still equals the attempt making it. A stale attempt therefore cannot overwrite a newer attempt's progress.
- **Bearer link:** a download link that works for anyone who holds it, with no login.
- **Lifecycle rule:** the `exports` bucket deletes every object 7 days after it was created. This plan adds no cleanup job.

## How the export runs

### 1. The user clicks Download CSV

- **Starts when:** the user clicks the button on the reports page.
- **What it does:** the browser reads `filters` and `cols` from the current page URL and sends them as JSON to `POST /api/reports/{report_id}/exports`. Nothing else is sent. The export always starts from the first matching row, never from the scroll position.
- **Response:** on the small path, the response is the CSV (step 3). On the large path, it is the export record, which the page shows (step 11).
- **What it keeps:** nothing in the browser.
- **On failure:** a network error or a 5xx response shows an inline error with a Retry button. For a CSV, the browser saves the file only after the whole response has arrived (fetch to blob), so a connection cut midway shows an error instead of a truncated file.

### 2. The API checks the request and picks a path

- **Starts when:** the request from step 1 reaches the API.
- **What it does:**
  1. Check that the caller has `report.view` on the report's workspace. This is the same check the page uses.
  2. Validate `filters` and `cols` with the page API's parser. Every name in `cols` must be a known column.
  3. Read `reports.row_count`, the unfiltered total. It is metadata, not report rows, so the primary or the replica may serve it.
  4. If `row_count` is 10,000 or fewer, go to step 3. Otherwise, or if the count is missing, go to step 4. A missing count takes the large path, so a report of unknown size is never built inside a request.
- **What it keeps:** nothing.
- **On failure:** 403 if the permission check fails. 400 if validation fails (unknown column names or malformed filters). 404 if the report does not exist. 500 on a database error. Nothing has started in any of these cases.

### 3. Small path: the response is the CSV

- **Starts when:** `row_count` is 10,000 or fewer.
- **What it does:** reads all matching rows from the read replica with the page's keyset query, 500 rows per query, in `row_id` order from the first row. It builds the whole CSV in memory: a header row, then one line per row in `cols` order. Fields containing commas, quotes or newlines are quoted per RFC 4180, the standard CSV quoting rules. Only after the whole CSV is built does it send `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. Building first matters: once a 200 status is sent, a later failure cannot change it.
- **What it keeps:** nothing stored. The CSV exists only in the request's memory. Its size at 10,000 rows is not yet measured (see Open questions).
- **Time:** the API kills any request that runs longer than 60 seconds. Twenty queries of 500 rows fit well within that. If the limit is hit, the same error path applies.
- **On failure:** a replica error or a timeout returns an error status. The browser shows an error with a Retry button. The user never gets a partial file.

### 4. Large path: record the export

- **Starts when:** `row_count` is above 10,000, or is missing.
- **What it does,** in one primary-database transaction:
  1. Mark this user's stale exports of this report as `failed` with `error = "stale"`. An export is stale if it is `queued`, has no `job_id`, and was created more than 5 minutes ago. An export is also stale if it is `queued` or `running` and was last updated more than 2 hours ago. This stops a crash between steps 4 and 5 from blocking the user forever. It is not a cleanup job.
  2. Insert a new export record with `status = queued`, `user_id`, `report_id`, `created_at`, and `filters` and `cols` in the normalised form from step 2.
  3. Commit, then go to step 5.
- **One active export:** a unique partial index on `(user_id, report_id)` where `status` is `queued` or `running` allows at most one active export per user and report.
- **Second click:** if the insert hits that index, the API rolls back, reads the user's active export for this report, and returns it with `200`. Nothing new starts. Two clicks at the same moment work the same way: the second insert waits for the first commit, fails on the index, and returns the first export.
- **What it keeps:** the export record, in the primary database.
- **On failure:** a database error returns `500`, and nothing is queued. An index conflict is not a failure. It is the second-click case above.

### 5. Enqueue the export job

- **Starts when:** step 4 committed a new record.
- **What it does:** calls `enqueue("build_csv_export", {"export_id": id})`. The payload holds only the ID, far under the 64 KB limit. The job reads everything else from the export record. The API then saves the returned `job_id` on the record and returns `202` with the record.
- **The job may start before `job_id` is saved.** That is harmless. The job never reads `job_id`; it finds its record by `export_id`. `job_id` is kept for support lookups. If saving it fails after a successful enqueue, the API logs the error and still returns `202`. One rare case remains: if the job waits more than 5 minutes in the queue with no `job_id` saved, the stale rule in step 4 fails the record, and the job then ends at step 6 because the record is no longer `queued`.
- **What it keeps:** the record (`status = queued`, and `job_id` once saved), and the queue's own record of the job.
- **On failure:**
  - If `enqueue` raises, the API sets the record to `failed` with `error = "could not start"` and returns `503`. The user can click again.
  - If the process dies after the insert and before `enqueue`, the record stays `queued` with no `job_id`. Clicks in the next 5 minutes get that record back. After that, the stale rule in step 4 clears it.

### 6. The job attempt claims the export

- **Starts when:** the queue starts an attempt of `build_csv_export`. The handler reads the attempt number from `ctx.attempt`, never from the payload.
- **What it does:**
  1. Load the export record by `export_id`.
  2. If `status` is `failed`, or `done` with `email_sent_at` set, end the attempt. A redelivered job does nothing once the export has finished and been emailed.
  3. Recheck `report.view` for the user. If it is gone, send no link. If the export is `queued` or `running`, mark it `failed` with `error = "access removed"`. In every case, end the attempt.
  4. If `status` is `done`, go to step 10. This covers a finished export whose email has not been sent yet.
  5. Claim the record with one conditional update that succeeds only if `status` is `queued` or `running`. It sets `status = running`, `attempt = ctx.attempt` and `updated_at`. If no row matches, the export was marked failed meanwhile, so end the attempt.
- **Fencing:** every later write in this attempt is a fenced update. A stale attempt that wakes after a newer one has claimed the export matches no rows, so it stops without writing. This relies on the queue killing an attempt that times out before it starts the next attempt.
- **What it keeps:** the record (`status = running`, `attempt`).
- **On failure:** a database error fails the attempt, and the queue retries it.

### 7. Start or resume the multipart upload

- **Starts when:** step 6 claimed the export.
- **What it does:**
  - **Fresh export** (`upload_id` is empty): call `start_multipart("exports", key)` with `key = "report-exports/{export_id}.csv"`. The key is unique per export, so one export never overwrites another's file. Save `upload_id` and `object_key` in one fenced update. Nothing is visible at the key yet.
  - **Resumed export** (`upload_id` is set): keep the existing upload and do not abort it, because its parts are reused. Read `parts` and `last_row_id` from the record, and continue at step 8 from `last_row_id`. The in-memory buffer starts empty.
  - **Part numbers:** the next part number is `len(parts) + 1`. Checkpoints are saved in order, so numbers stay in sequence. The header row goes into part 1, so it is written whenever the next part number is 1.
- **What it keeps:** `upload_id`, `object_key`, `parts` and `last_row_id` on the record.
- **On failure:**
  - If `start_multipart` raises, the attempt fails and the queue retries. If the upload started but the fenced save failed, the upload stays invisible, and the lifecycle discards it after 24 hours.
  - If a resumed upload is gone (it passed 24 hours, or was aborted), the next `upload_part` or `complete_multipart` call fails with an unknown-upload error. The attempt then clears `upload_id`, `object_key`, `parts` and `last_row_id` in one fenced update, and ends as failed. The next attempt starts fresh from the first row. This uses one of the 3 attempts.

### 8. Stream rows from the replica into parts

- **Starts when:** step 7 has an upload ready.
- **What it does,** in a loop:
  1. Read the next batch of up to 10,000 rows from the read replica: `WHERE report_id = :report AND <filters> AND row_id > :last ORDER BY row_id LIMIT 10000`. `:last` starts at `last_row_id`, or is empty on a fresh start. It uses the page API's query builder, so the CSV matches the page. The page reads 500 rows per request; the export reads 10,000 because larger batches fit the time budget.
  2. Format each row as one CSV line in `cols` order, quoted as in step 3.
  3. Append whole lines to a buffer. When the buffer reaches 8 MB, upload it as one part with `upload_part(upload_id, part_number, data)`.
  4. After each successful `upload_part`, save a checkpoint. This is one fenced update that appends `{part_number, etag}` to `parts`, sets `last_row_id` to the `row_id` of the last row in that part, and sets `rows_written` to the total number of rows in all parts.
- **Batches and parts need not line up.** The buffer holds only whole lines, so each part ends at the end of a row, possibly partway through a batch. The checkpoint records the last row inside the uploaded part. Rows after it, including the rest of the batch, are read again on resume. Nothing after the checkpoint was uploaded, so the final file has no missing or repeated rows.
- **Memory:** one 10,000-row batch and one 8 MB buffer, about 30 MB in total. The job never holds the whole report, which stays far inside the 512 MB worker limit.
- **Size:** the largest report is about 2 million rows and 900 MB of CSV. At 8 MB per part, that is about 115 parts, far under the 10,000-part limit.
- **Time:** each attempt has 1,800 seconds. One large export must finish within that, so it is measured before release (see Build and rollout). If an attempt runs out of time, the next attempt resumes from the checkpoint. There are only 3 attempts in total.
- **What it keeps:** the parts already uploaded (in the bucket, incomplete and invisible), and the checkpoint on the record.
- **On failure:**
  - Replica query error: the attempt fails. The next attempt resumes from `last_row_id`.
  - `upload_part` error: the attempt fails. The buffer is lost, and rows after the checkpoint are read again.
  - Attempt timeout or worker death: the same as above. The next attempt resumes from the checkpoint.
  - A checkpoint whose fence fails (`attempt` no longer matches): the attempt stops and writes nothing more.
  - A part uploaded but not checkpointed: the next attempt uploads a part with the same number, which replaces it.
  - A nightly rebuild during a resume can mix rows from before and after the rebuild. See the last open question.

### 9. Finish the upload and make the file visible

- **Starts when:** the last batch has been read. A resume that is already at the last row also starts here.
- **What it does:** uploads any remaining buffered lines as the final part. The last part may be smaller than 5 MB. Checkpoint it as in step 8. If the buffer is empty, skip the upload. Then call `complete_multipart(upload_id, etags)`, where `etags` is the full ordered list from `parts`. Completion is atomic: the object appears at its key only if this call succeeds, so a half-written file is never downloadable. After completion, one fenced update sets `status = done` and `completed_at`.
- **What it keeps:** the finished object at its key in the `exports` bucket, and the record.
- **On failure:**
  - If `complete_multipart` raises for any reason other than an unknown upload, the attempt fails. The parts stay for 24 hours. The next attempt resumes at the saved `last_row_id`, reads nothing, and calls `complete_multipart` again with the saved etags.
  - If `complete_multipart` reports an unknown upload, the upload may already have completed. Check first whether an object exists at `object_key` (this needs the `object_exists` helper in Build and rollout). If it does, set `status = done` and `completed_at`, and go to step 10. If it does not, clear the upload fields as in step 7 and end as failed.
  - If the object is complete but the `done` update fails, the upload no longer exists, so the next attempt takes the unknown-upload path above.

### 10. Send the download link

- **Starts when:** the export is `done` and `email_sent_at` is empty. This happens right after step 9 in the same attempt, or in a later attempt that step 6 sends here.
- **What it does:** calls `signed_url("exports", object_key, 86400)` for a URL valid for 24 hours. Then calls `send_email(user_id, "export_ready", {report_id, export_id, url, expires_at})`. After it succeeds, sets `email_sent_at` in a fenced update.
- **What it keeps:** `email_sent_at`, so a finished export is not emailed twice. Delivery is at least once. A crash between the send and the flag write can still cause one duplicate, because the email helper has no idempotency key (a value that lets the receiver ignore a repeat).
- **On failure:** if `send_email` raises, the attempt fails. The record stays `done` with `email_sent_at` empty, so the next attempt goes from step 6 to this step and sends the email again. If all 3 attempts fail, step 12 runs and leaves the export `done`.

### 11. The page shows the export's state

- **Starts when:** the page loads, the user clicks Download CSV, or the user returns to the report later.
- **What it does:** the page calls `GET /api/reports/{report_id}/exports/latest`. The API checks `report.view` and returns the user's most recent export of this report: `status`, `filters`, `cols`, `created_at`, `completed_at` and `error`. For a `done` export, it adds a signed URL valid for 24 hours, generated fresh on each request.
- **Expiry:** the API returns `expired` instead of a link when `completed_at` is more than 7 days ago, or when the object is gone. The 7 days run from when the object was created, which is at completion, so a link made close to that limit may stop working before 24 hours.
- **Polling:** while the status is `queued` or `running`, the page polls every 3 to 5 seconds. It stops when the status is `done` or `failed`.
- **Filters:** the page shows the `filters` and `cols` of the returned export, so the user can see which view it is. A click can return an earlier export with other filters (see Open questions).
- **What it keeps:** the export record only. The page keeps no state of its own, so the state survives a reload.
- **On failure:** if the status request fails, the page keeps its last known state and retries on the next poll. A `failed` export shows its stored `error`, a short message and never a stack trace, with a **Try again** button, which starts a new export. An `expired` export says the link has expired and offers Download CSV again. Neither `failed` nor `expired` is an active state, so step 4 creates a new record.

### 12. Final failure

- **Starts when:** the third attempt fails, or the queue calls `on_final_failure(ctx, payload, error)`.
- **What it does:**
  1. Load the record. If `status` is `done`, only the email failed. Do not change the status. Log the error. The user still sees the link on the page. Leave `email_sent_at` empty so an operator can resend.
  2. Otherwise, if there is an `upload_id`, call `abort_multipart(upload_id)`. If that fails, ignore the error, because the lifecycle removes the parts within 24 hours.
  3. Set `status = failed`, `error = "export failed after 3 attempts"` and `completed_at`.
  4. Call `send_email(user_id, "export_failed", {report_id, export_id})`. If it fails, log the error. The record is already `failed`, and the page shows that.
- **What it keeps:** the record (`status = failed`, `error`).
- **On failure:** if this handler itself raises, the record stays `queued` or `running`. The stale rule in step 4 clears it only after 2 hours without an update, so the user cannot start a new export for up to 2 hours.

## What happens when things fail

| Where it fails | What the user sees | What is left behind |
|---|---|---|
| Permission check at click | 403 | Nothing |
| Bad `filters` or `cols` | 400 | Nothing |
| Report does not exist | 404 | Nothing |
| Database error at click | 500 | Nothing queued |
| Small path: replica error or 60-second timeout | Error with Retry, no file | Nothing stored |
| `enqueue` raises | 503, and the user can click again | Record `failed`, "could not start" |
| Process dies after insert, before `enqueue` | The queued export comes back on clicks for 5 minutes, then clears | Record `queued`, no `job_id` |
| Access removed before the job runs | Export shows `failed`, "access removed" | Record `failed`, no link sent |
| Resumed upload is gone | Export continues after the next attempt starts | Upload fields cleared; the next attempt starts fresh |
| Replica error, `upload_part` error, attempt timeout or worker death | Export keeps running on the next attempt | Checkpointed parts, resumed from `last_row_id` |
| Checkpoint fence fails | The stale attempt stops | Nothing more written by that attempt |
| `complete_multipart` fails | Export keeps running on the next attempt | Parts kept for 24 hours |
| Email fails after `done` | Link still shown on the page | Record `done`, `email_sent_at` empty for an operator to resend |
| Third attempt fails | Page shows `failed` with Try again, and an email is sent | Record `failed`; parts aborted |
| Final-failure handler raises | Export looks active until the stale rule clears it | Record `queued` or `running` for up to 2 hours |

## Where state lives

| Where | What | Who writes it |
|---|---|---|
| `report_rows` on the read replica | Report data | The nightly rebuild only. The export reads it and never writes it. |
| `report_exports` on the primary | Export state, parts, checkpoints, email flag | Click (step 4), job (steps 6, 7, 8, 9, 10, 12) |
| `exports` bucket, `report-exports/{export_id}.csv` | The finished CSV, visible only after completion | Job (step 9). Lifecycle deletes it 7 days after creation. |
| Incomplete multipart uploads | Parts of unfinished exports | Job. Aborted on final failure, or removed by the lifecycle after 24 hours. |
| Queue | Jobs and their attempts | The queue |

## Build and rollout

These are needed to build and release the feature. They are not part of how the export runs.

- **Storage helper:** add `object_exists(bucket, key)` to `storage.py`. Step 9 needs it. It is not a cleanup job.
- **Table:** create `report_exports` with these columns: `id`, `user_id`, `report_id`, `filters`, `cols`, `status`, `job_id`, `attempt`, `upload_id`, `object_key`, `parts` (a list of `{part_number, etag}`), `last_row_id`, `rows_written`, `error`, `email_sent_at`, `created_at`, `updated_at` and `completed_at`. Add the unique partial index from step 4.
- **Replica index:** confirm that the read replica has an index on `report_rows (report_id, row_id)`. Keyset paging depends on it. Confirm this before the timing test.
- **Timing test:** on the largest report in staging, measure the replica read time per batch and the upload time per part. Keep a margin of at least 20 percent inside the 1,800-second attempt limit. Do not release until a timed run of the 2-million-row report has passed inside one attempt with that margin, or until checkpoint resumption has been tested across a forced timeout.
- **If a run does not fit:** the checkpoints let later attempts continue, but the job has only 3 attempts. A run that times out three times fails.

## Open questions

1. **Dedupe ignores filters.** A second click returns the existing export of that report. If the user changed the filters, they get the earlier export with the old filters. Adding `filters` and `cols` to the key would let two exports of different views run at once, which the brief forbids. The owner must decide. The page at least shows the filters of the returned export.
2. **The threshold uses the unfiltered count.** A filtered view of 50 rows from a 2-million-row report takes the large path, so the user waits for an email. Counting filtered rows would be more accurate, but it costs an extra query per click and is not in the brief.
3. **Nightly rebuild during an export.** If `report_rows` is rebuilt while a multi-attempt export resumes, rows from before and after the rebuild can mix. Options are a data-generation number on `reports` that the rebuild writes, or a check of `row_count` at each checkpoint. A number is the reliable option. If it changes, the job must abort the upload and start again.
4. **The emailed link is a bearer link.** Anyone who holds it can download for 24 hours, even after the user loses `report.view`. The page's link is checked on each request, but the emailed link is not. This follows from the brief.
5. **Export record retention.** Files are deleted after 7 days, but `report_exports` rows are kept indefinitely. The brief rules out a cleanup job for files. The owner must decide whether the rows need a retention rule.
6. **Memory for the small path.** The size of a 10,000-row CSV held in the request is not measured. Measure it during the timing test.