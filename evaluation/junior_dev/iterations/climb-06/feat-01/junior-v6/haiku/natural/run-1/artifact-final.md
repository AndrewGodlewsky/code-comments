# CSV export for the reports page: implementation plan

## What this is and how it works

Today the reports page (`/reports/{report_id}`) shows one report as an infinite-scroll table. It loads rows in pages from `GET /api/reports/{report_id}/rows`. The page's filters and column order live only in the page URL. The server stores nothing about what a user is looking at. Users cannot export anything today.

This plan adds a **Download CSV** button. The file holds exactly what the user sees when they click: the same filters, the same columns in the same order, and a header row. The export takes one of two paths, chosen by the report's size.

- A report with 10,000 rows or fewer is built inside the click's request. The CSV is the response.
- A larger report returns `202` at once. A background job then writes the CSV to object storage in numbered parts. The job saves its progress after each part, and it emails the user a download link that works for 24 hours.

Why it is shaped this way: an API request is killed after 60 seconds, so a large file cannot be built inside one. A job can be killed and retried, so progress is saved after every part, and a retry resumes from the last saved part instead of starting over. A job that has run for 20 minutes hands the rest of its work to a new job. Export state is kept in two small tables on the primary database, so the page can show it.

Scope: CSV only. No scheduled exports, no other formats, and no change to the table on the page. Report data is read only from the read replica, as the page reads it today.

## Terms

- **Report:** one table the page shows. It belongs to a workspace.
- **`report.view`:** the permission to view a report in its workspace. The page and the export both check it.
- **Report rows:** the rows of the `report_rows` table. Each row has a `row_id` that is unique and increases within its report.
- **`reports.row_count`:** the total number of rows in a report before any filter. It is rewritten each night, when the report data is rebuilt.
- **Read replica:** a read-only copy of the database. All report rows and report counts are read from it, never from the primary.
- **Primary database:** the writable database. Export state is stored here.
- **Keyset paging:** each page is fetched with `row_id > last row_id seen`, in `row_id` order. Offsets are never used, so every page is equally fast.
- **Normalised filters and columns:** the `filters` and `cols` strings from the URL, after the same parser the rows API uses.
- **Queue job:** a unit of background work. Its handler is the function that does the work.
- **Attempt:** one run of a job's handler. An attempt fails if the handler raises, runs longer than 1,800 seconds, or its worker dies. A failed attempt is retried after 60 seconds, then after 300 seconds, for 3 attempts in total. The queue keeps no progress between attempts. Each retry runs the handler again from the start, with the same payload.
- **At least once:** the queue may run a handler again even after it has succeeded. Handlers must tolerate this.
- **Payload:** the data passed to a job. It must be JSON-serialisable and under 64 KB.
- **Worker:** a process with 512 MB of memory. It runs one attempt at a time.
- **Multipart upload:** a file sent to object storage as numbered parts. The object becomes visible at its key only when the upload is completed. A multipart upload has at most 10,000 parts. Every part except the last must be at least 5 MB.
- **Part and etag:** a numbered piece of a multipart upload. Storage returns an etag for each part. Completing the upload needs every etag.
- **Committed part:** a part whose row has been saved in the `export_parts` table. Only committed parts count as progress.
- **Checkpoint:** `next_row_id`, the last `row_id` in a committed part. A retry resumes after it.
- **Export row:** the row in `export_jobs` for one export. It holds the export's state. It is not report data, so the replica rule does not apply to it.
- **Partial unique index:** a database rule that allows at most one row with the same key among the rows that match a condition. Here it allows one active export per user and report.
- **Conditional write:** an update that changes a row only if the row still holds the value the run expects. If it changes no rows, another run or a status change got there first.
- **Stale guard:** a rule that treats an active export with no updates for 6 hours as dead.
- **Lifecycle rule:** the bucket's automatic rule. It deletes each object 7 days after it is created. It discards a multipart upload that is not completed within 24 hours.
- **Signed URL:** a download link that stops working after a set time. Anyone who holds it can download the file until it expires.
- **`send_email(user_id, template, params)`:** the existing function that emails a user from a named template.

## Data kept for an export

Table `export_jobs` has one row per export. It lives on the primary database.

| Field | Purpose |
|---|---|
| `export_id` (UUID, primary key) | Names the export and its object key |
| `user_id`, `report_id` | Owner and report |
| `filters`, `cols` | The normalised URL strings |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | The queue job that currently owns the export |
| `attempt` | The attempt number of the last run that started |
| `upload_id`, `upload_started_at` | The open multipart upload |
| `next_row_id` | The checkpoint: the last `row_id` in a committed part |
| `finished` | True once every row is in a committed part |
| `storage_key`, `object_created_at` | Set when the upload completes |
| `email_sent_at` | Set after the ready email is sent |
| `error` | A short message for a failed export |
| `created_at`, `updated_at` | `updated_at` changes on every state change and checkpoint |

Table `export_parts` has one row per committed part: `export_id`, `part_number`, `etag`, `last_row_id`. For the largest report this is about 60 rows.

Two rules on these tables:

- A partial unique index on `(user_id, report_id)`, where `status` is `queued` or `running`, allows only one active export per user and report. It holds even when two clicks race.
- The object key is `reports/{report_id}/exports/{export_id}.csv`. Each export has its own key, so no export overwrites another.

## How the export runs

### Step 1. The click checks the report and the parameters

- **Starts:** the user clicks **Download CSV**. The page calls `GET /api/reports/{report_id}/export?filters=...&cols=...`, with the same values as the page URL.
- **Does, in order:**
  1. Finds the report. An unknown report gives 404. The permission check needs the report's workspace, so the report must be found first.
  2. Checks `report.view` on the report's workspace. Without it the answer is 403, the same answer the page gives.
  3. Checks `filters` and `cols` with the same validator the rows API uses. The parameters are never parsed a second way. Bad values give 400.
- **Data moved:** only the URL parameters.
- **State:** none.

### Step 2. Choose the path by size

- **Starts:** Step 1 passes.
- **Does:** reads `reports.row_count` from the read replica. A count of 10,000 or less goes to Step 3. A count above 10,000 goes to Step 4.
- **Data moved:** one number, from the replica.
- **State:** none.
- **On failure:** if the replica is unreachable, return 503 with a retry message. Never fall back to the primary.
- **Note:** `row_count` counts all rows, before filters. So a small filtered view of a large report takes the large path. That is correct but slower. Whether to count filtered rows instead is an open question at the end.

### Step 3. Small path: build the CSV inside the request

- **Starts:** Step 2 chooses the small path.
- **Does:** reads `report_rows` from the replica in keyset pages of 500 rows, with the URL filters applied. It writes a header row, then one CSV line per row, with the columns in URL order.
- **The cap:** the cap counts the filtered rows actually read, not `row_count`. When the 10,001st matching row appears, reading stops and the buffer is dropped. The request then goes to Step 4, because the replica's count was stale. The user gets the same `202` response as any large click. Step 4 builds that response at that moment, so it reflects an export row created then.
- **Data moved:** report rows, held in API-server memory. At 10,000 rows this is a few megabytes.
- **State:** nothing is stored. The request writes no export row and queues no job.
- **Response:** `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. The body is sent only after it is complete, so the browser never saves a partial file.
- **On failure:** a database error, or the 60-second API limit, before the body is complete returns an error with no body. The user clicks again. Buffering is deliberate. A stream that fails halfway would leave a truncated file that looks complete.

### Step 4. Large path: create the export, or return the active one

- **Starts:** Step 2 chooses the large path, or Step 3 hits its cap.
- **Does:** inserts one `export_jobs` row on the primary, in one statement, with `status = queued` and the normalised `filters` and `cols`. The partial unique index blocks a second active export for the same user and report.
- **If the insert conflicts:** an active export already exists. Return that export instead of starting another. Its `filters` come back in the response, so the page can say which view the export covers. A second click after a filter change therefore gets the older view, and the page says so.
- **Stale guard:** if the conflicting row's `updated_at` is more than 6 hours old, the export is dead. Abort its `upload_id` if it has one, mark it `failed` with the error `stalled`, and insert the new row. If the insert conflicts again, return the active export.
- **Response:** `202 Accepted` with `{export_id, status, filters}`. The page starts polling (Step 11).
- **On failure:**
  - If the insert fails, return 500. There is no row and no job.
  - If the insert works but Step 5 fails, mark the row `failed` with the error `could not queue`, and return 503. The user can click again.

### Step 5. Queue the job

- **Starts:** Step 4 inserted a new row.
- **Does:** calls `enqueue("csv_export", {"export_id": ...})`. The payload is one UUID, far under the 64 KB limit. The job reads the filters and columns from the row, not from the payload, so the two cannot disagree. `enqueue` returns a `job_id`, which is saved on the row.
- **Order:** the job may start before the `job_id` save finishes. That is safe. Step 6 writes the same `job_id`, so either order leaves the same value.
- **State:** `job_id` on the row. Until it is saved, the stale guard is the backstop.
- **On failure:**
  - If `enqueue` raises, nothing runs. Step 4 marks the row `failed`.
  - If `enqueue` works but saving `job_id` fails, Step 4 also marks the row `failed`. The job then reads `failed` in Step 6 and returns.

### Step 6. Each attempt starts: load the row, check it, then resume or start

- **Starts:** the queue calls the handler with `ctx.attempt` (1, 2 or 3) and `{export_id}`.
- **Does:** reads the export row from the primary. Then it runs these checks in order, and stops at the first one that applies:
  1. The row is missing: return.
  2. `status = done` and `email_sent_at` is empty: go to Step 10.
  3. `status = done` and `email_sent_at` is set: return. This is a duplicate delivery.
  4. `status = failed`: return.
  5. The user has lost `report.view`, or the report was deleted. The permission is checked again for `row.user_id`, because the user may lose access while the job waits in the queue. Set `failed` with the error `no access` or `report not found`. Send the failure email (Step 12). Then **return normally**. Returning, not raising, stops the queue from retrying a failure that will not change.
  6. Otherwise set `status = running`, `attempt = ctx.attempt`, `job_id = ctx.job_id` and `updated_at = now`.
  7. If `upload_id` is set and `upload_started_at` is less than 20 hours ago, resume that upload. If `finished` is true, go to Step 9. Otherwise continue from `next_row_id` in Step 7, or from the start if it is null.
  8. Otherwise (there is no upload, or it is too old): abort any old upload. Delete this export's `export_parts` rows, and set `next_row_id` to null and `finished` to false, so no old etag is reused. Call `start_multipart(exports, storage_key)`, save the new `upload_id` and `upload_started_at`, and start from the beginning.
- **Data moved:** the export row, and the permission lookup.
- **State:** the fields named above.
- **On failure:** a database or permission-lookup error raises. The queue retries after 60 seconds, then after 300 seconds. This attempt has uploaded nothing. Parts committed by earlier attempts stay. The retry reads the row again and continues from the checkpoint. If saving the row after `start_multipart` fails, the new upload is orphaned. The bucket discards it after 24 hours.

### Step 7. Stream rows into committed parts

- **Starts:** Step 6 has set up the upload and has a checkpoint.
- **Does, in a loop:**
  1. Reads the next page of 5,000 rows from the replica: `row_id > checkpoint ORDER BY row_id LIMIT 5000`, with the row's filters and columns.
  2. Formats each row as one CSV line and adds it to a byte buffer. The header row is the first line of part 1.
  3. When the buffer reaches 16 MB after a complete row, cuts a part there. Rows after the cut stay in memory for the next part.
  4. Calls `upload_part(upload_id, part_number, data)` and gets an etag. Part numbers start at 1. The part number is 1 plus the number of committed parts for this export, counted from `export_parts`. It is never kept only in memory.
  5. In one primary transaction, inserts the `export_parts` row (`export_id`, `part_number`, `etag`, `last_row_id`). It also sets `next_row_id` to the part's last `row_id`, and `updated_at` to now. The update applies only if `status = running` and `next_row_id` still holds the value this run read. If the transaction changes no rows, or the part number is already taken, another run got there first. Stop and return normally.
  6. Checks the time budget (Step 8), then returns to the loop.
- **Why a retry is safe:** cuts depend only on the checkpoint and the data. A retry from the same checkpoint gives the same rows, the same cuts and the same part numbers. Every part except the last is 16 MB, above the 5 MB minimum.
- **Memory:** at most one page of 5,000 rows and one 16 MB buffer are held at a time, far under the 512 MB limit. The whole report is never in memory, and the file is never written to local disk.
- **Size:** at about 450 bytes per row, the 2-million-row report makes about 57 parts. That is far under the 10,000-part limit.
- **State:** `next_row_id` is the checkpoint. Committed parts are in `export_parts`.
- **On failure:**
  - A crash before `upload_part`: the buffer is lost. The retry starts at `next_row_id` and regenerates those rows.
  - A crash after `upload_part` but before the transaction: an uncommitted part exists. The retry regenerates the same rows and uploads the same `part_number`, which replaces it. Nothing is lost.
  - A replica query error: retry the page query up to 3 times within the attempt, then fail the attempt.
  - A storage error on `upload_part`: the attempt fails. The retry resumes from the checkpoint.

### Step 8. Hand over to a new job when an attempt runs long

- **Starts:** after each committed part in Step 7.
- **Rule:** if this attempt has run for 20 minutes, it starts no new part. The queue kills an attempt at 30 minutes, so this leaves about 10 minutes of margin. The check runs only at part boundaries, so no interim part is ever short. A short interim part would break the 5 MB minimum. A part takes seconds to minutes, so the margin is ample. The 20-minute figure comes from the measurement under Building.
- **Does:** if rows remain, calls `enqueue("csv_export", {"export_id": ...})`, saves the returned `job_id` on the row as in Step 5, and returns normally. The new job starts at attempt 1 and resumes from the checkpoint. This is why a 2-million-row export can finish, even though no single attempt is guaranteed to do all of it.
- **Data moved:** none beyond Step 7.
- **State:** the checkpoint is committed. The row stays `running`. The row's `attempt` shows the last run that started.
- **On failure:**
  - If `enqueue` raises, the attempt fails. The retry resumes from the same checkpoint, so no work is lost.
  - The old handler returns normally after `enqueue`, so the queue does not retry it. Only a worker that dies in the short gap between `enqueue` and the return causes a retry. That retry runs beside the new job. Both runs upload identical parts. The conditional write in Step 7 lets only one advance, and the other stops. The result is wasted work, not a wrong file.

### Step 9. Finish: complete the upload

- **Starts:** the query finds no rows after the checkpoint. Or Step 6 sends the run here because `finished` is true.
- **Does:**
  1. Flushes the last buffer as the final part. This part may be under 5 MB, which the last part is allowed to be. In one transaction, it saves the part's `export_parts` row and sets `finished = true`. The write is conditional, as in Step 7.
  2. Calls `complete_multipart(upload_id, etags)`, with the etags sorted by `part_number` from `export_parts`. The object becomes visible at `storage_key` in one step. Completing replaces any object already at that key. Keys are unique per export, so this does not happen in normal runs.
  3. Conditionally sets `status = done`, `storage_key`, `object_created_at = now` and `updated_at = now`, only if `status = running`. If zero rows change, stop and return normally, as in Step 7.
- **Data moved:** the etags. The file itself is never read back.
- **State:** `done` is written only after the object is complete. A half-written file can never be linked or downloaded.
- **On failure:**
  - If `complete_multipart` raises, the handler tries `abort_multipart` and clears `upload_id`, then the attempt fails. Abort is harmless if the completion actually succeeded. The next attempt finds no upload and restarts from scratch (Step 6, check 8). This costs a full re-export, but such failures are rare. The storage helpers cannot tell 'already completed' from 'upload gone', so restarting is the only safe choice.
  - If the `done` write fails after completion succeeded, the attempt fails. The next attempt calls `complete_multipart` again, which fails, and clears `upload_id`. A later run then restarts from scratch. The export can end `failed` although the object exists. The last open question covers this gap.
  - If the upload is older than 20 hours, Step 6, check 7 treats it as gone and the run restarts.

### Step 10. Email the ready link

- **Starts:** `status = done` and `email_sent_at` is empty. This happens right after Step 9, or on a retry (Step 6, check 2).
- **Does:** calls `signed_url(exports, storage_key, ttl = min(86400, object_created_at + 7 days - now))`. The `ttl` may be at most 86,400 seconds, so the link lasts up to 24 hours and never outlives the object. Then calls `send_email(user_id, "export_ready", {report_id, report_name, download_url, expires_at})`.
- **State:** on success, sets `email_sent_at = now`.
- **On failure:** if `send_email` raises, the attempt fails without redoing the export, because the file is already done. The retry runs Step 6, check 2, and sends the email again. If all 3 attempts fail, the final-failure handler (Step 12) leaves `status` as `done`. The page still offers the download (Step 11), so the file is not lost.

### Step 11. The page shows the state and offers the link

- **Starts:** the report page loads. While an export is `queued` or `running`, the page polls every 5 seconds. It stops when the status is `done` or `failed`.
- **Endpoint:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export for this report. Its fields are `status`, `filters`, `created_at`, `attempt` (while running), `error` (if failed) and, if `done` and not expired, a fresh `download_url`.
- **Permission:** the endpoint checks `report.view` and returns only rows where `user_id` is the caller.
- **Link:** every page load mints a new signed URL with `ttl = min(86400, object_created_at + 7 days - now)`. When that is zero or less, no URL is offered, and the page says 'This export has expired. Export again.'
- **Click while active:** the button calls Step 4, which returns the active export. It does not start another.
- **Data moved:** a read of the export tables on the primary, since this is export state, not report data.
- **On failure:** if the endpoint errors, the page shows 'Export status unavailable' and keeps polling. A failed poll never changes the export.

### Step 12. Failure: retries, then the final failure

- **Ordinary attempt failure** (a raise, a timeout or a worker death): the queue waits 60 seconds, then 300 seconds, and retries. `status` stays `running` while the job waits. The page shows the attempt number. The checkpoint is kept, so finished work is not repeated.
- **Final failure:** after the 3rd attempt fails, the queue calls `on_final_failure(ctx, payload, error)`. The handler:
  1. Reloads the row. If `status = done`, it changes nothing. The file is complete, and only the email failed.
  2. Otherwise sets `status = failed`, sets `error` to a short summary with no stack trace, and sets `updated_at`.
  3. Calls `abort_multipart(upload_id)` if `upload_id` is set, so the parts are dropped now, not after 24 hours.
  4. Calls `send_email(user_id, "export_failed", {report_id, report_name, retry_hint})`. If this send fails, it logs the failure. The page still shows `failed`.
- **The handler itself fails** (for example, the database is down during `on_final_failure`): the row stays `running`. The stale guard in Step 4 clears it after 6 hours with no updates. The user can click again then.
- **Permission lost, or the report is gone:** handled in Step 6, check 5, without retries.

### Step 13. Expiry and cleanup

- **Starts:** time passing.
- **Files:** the bucket's lifecycle rule deletes each object 7 days after `object_created_at`. The page treats the export as expired from then on. Emailed links last 24 hours. Page links are capped at the time left on the object. So no link works after the object is gone.
- **Uploads:** multipart uploads that are never completed are discarded by the bucket after 24 hours. Step 12 aborts them sooner when a failure is final.
- **Rows:** the `export_jobs` and `export_parts` rows stay. No cleanup job is built. Deleting old files is left to the bucket's lifecycle rule. The rows are small: a few hundred bytes per export, plus about 60 part rows for the largest report.

## Building and rolling out

### Before coding: measure (gate)

- **Starts:** a decision before any code is written. The owner is whoever builds the job.
- **Data:** a copy or staging replica of the 2-million-row report. The measurement reads it in keyset pages of 5,000 rows, formats CSV, and uploads 16 MB parts to a test bucket.
- **Record:** rows per second, the time for one part, and the replica query time per page.
- **What the numbers decide:** the time budget per attempt in Step 8. The total run takes about 900 MB divided by the measured bytes per second. If the total exceeds about 4 hours, stop and reconsider the design before building. For example, split the report into row ranges that parallel jobs handle.
- **On failure:** if a worker cannot reach the replica, that is a blocker. Do not build the job against the primary as a workaround.

### Tests

- **Unit:** the keyset page query. Part cuts are deterministic for a fixed checkpoint. The state checks in Step 6. The single-active rule under two simultaneous clicks.
- **Integration, with a fake object store:** resume after a crash at each point in Step 7 (before upload, after upload, after checkpoint) gives a byte-identical file. No interim part is under 5 MB. A timed-out attempt resumes. A final failure aborts the upload and sends one failure email.
- **Scale:** the measured report, run end to end, with peak memory under 512 MB and every attempt under 1,800 seconds.
- **Permission:** a user who loses `report.view` between the click and the run gets a failed export and no file.

### Before shipping

- The email templates `export_ready` and `export_failed` must exist. Their parameters are listed in Steps 10 and 12.

## What happens when things fail

| Where | What goes wrong | What happens |
|---|---|---|
| Step 1 | Unknown report, no `report.view`, bad parameters | 404, 403 or 400. No work is done. |
| Step 2 | Replica unreachable | 503. No fallback to the primary. |
| Step 3 | Database error, or the 60-second limit, before the body is complete | An error with no body. The user clicks again. |
| Step 4 | Insert fails, or queueing fails | 500 with no row. Or the row is marked `failed` and 503 is returned. |
| Step 6 | Database or permission-lookup error | The queue retries after 60 seconds, then 300 seconds. Committed parts are kept. |
| Step 6 | The user lost `report.view`, or the report was deleted | `failed` with `no access` or `report not found`. One failure email. No retry. |
| Step 7 | Replica query error | 3 retries within the attempt, then the attempt fails. |
| Step 7 | `upload_part` error | The attempt fails. The retry resumes from the checkpoint. |
| Step 8 | `enqueue` raises | The attempt fails. The retry resumes from the same checkpoint. |
| Step 9 | `complete_multipart` raises | The upload is cleared. A later run restarts from scratch. |
| Step 10 | `send_email` fails | The retry sends the email only. If all attempts fail, the export stays `done`. |
| Step 12 | Handler fails during final failure | The row stays `running` until the stale guard clears it after 6 hours. |
| Any step | Every attempt fails | `failed`, parts aborted, one failure email. |

## Open questions

1. **Dedupe ignores filters.** The spec allows one active export per user per report. A user who changes a filter and clicks again gets the existing export, with the old filters. Step 4 returns the filters, so the page can say so. Is that acceptable, or should the key include the filters?
2. **Nightly rebuild during a long export.** `reports.row_count` is rewritten when the data is rebuilt each night. A multi-hour export that spans a rebuild could mix two versions of the report. Is there a report generation or rebuild timestamp? If yes, store it on the row when the export starts, and restart from scratch in Step 6 if it changes. If not, consider holding large exports during the rebuild window.
3. **Access after the link is sent.** The emailed link is a bearer link for 24 hours. If `report.view` is revoked after the email, the link still works until it expires. Is that acceptable?
4. **Filtered size.** The path is chosen by the unfiltered `row_count`, so small filtered views of large reports go to the job. Is counting filtered rows, at extra cost, worth it?
5. **CSV details.** The spec does not say whether to write a UTF-8 byte-order mark, which helps Excel show non-ASCII characters. It also does not say how to neutralise cells that begin with `=`, `+`, `-` or `@`, which prevents spreadsheet formula injection. Both need a decision before Step 7 is coded.
6. **Stale threshold.** The 6-hour stale guard in Step 4 assumes that queue delay plus retries stays well under 6 hours. Confirm this against the queue's real backlog.
7. **A completed object cannot be detected.** The storage helpers have no check that an object exists at a key. So a retry cannot tell whether a completed upload already made the object. If the `done` write fails after completion, the export can be marked `failed` while the object exists. Add an existence check to `storage.py`, or store a 'completed' flag, before shipping.