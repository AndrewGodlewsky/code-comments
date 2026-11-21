# Plan: CSV export for the reports page

## Summary

Today the page `/reports/{report_id}` shows one report as a table with infinite scroll. It loads rows from `GET /api/reports/{report_id}/rows`, 500 at a time, from the read replica. Filters and column order live only in the page URL. The server stores nothing about them.

We add a **Download CSV** button. The click sends the current filters and columns to a new API. The API reads `reports.row_count`. At 10,000 rows or fewer, the response to the click is the CSV, streamed. No job runs and nothing is stored. Above 10,000, the API records an export in a new database table, queues a background job and answers at once. The job streams the rows into a multipart upload in the `exports` bucket, so memory stays small. It then emails the user a download link that works for 24 hours. The page shows the export's state: queued, running, done or failed. The two paths exist because a large report cannot be built inside the 60-second request limit or held in a worker's 512 MB.

Out of scope: scheduled exports, formats other than CSV, and changes to the table on the page.

## Terms

- **Report page / rows API:** the page `/reports/{report_id}` and `GET /api/reports/{report_id}/rows`. The API returns 403 if the signed-in user lacks `report.view` on the **workspace** that owns the report.
- **Read replica:** a read-only copy of the database. Report data must only be read from it, never from the primary database.
- **Keyset paging:** reading rows with `row_id > after ORDER BY row_id`. `row_id` is unique and increasing within a report. This is never done with OFFSET.
- **`reports.row_count`:** the unfiltered total number of rows in a report. Only the nightly rebuild of the report data rewrites it. The largest report has about 2 million rows, about 900 MB as CSV.
- **Request limit:** API servers kill any request that runs longer than 60 seconds.
- **Queue and worker pool:** the job queue (`jobs.py`) runs jobs on separate worker processes. Each has 512 MB of memory and runs one job attempt at a time. A job waiting for a free worker stays queued.
- **Attempt:** one run of a job handler. A job gets at most 3 attempts. Waits before attempts 2 and 3 are 60 s and 300 s. An attempt is killed after 1800 s. An attempt fails if the handler raises, times out or its worker dies. The queue keeps no progress between attempts: each one restarts from the beginning with the same payload.
- **At-least-once delivery:** a handler may run again for a job that already succeeded, so handlers must tolerate that.
- **`@job(name, on_final_failure=...)`, `enqueue(name, payload)`:** the queue's decorator and enqueue call. The payload must be JSON and under 64 KB. `on_final_failure(ctx, payload, error)` is called once, after the last attempt fails.
- **`exports` bucket:** object storage. It deletes every object 7 days after creation and discards a multipart upload not completed within 24 hours.
- **Multipart upload:** `start_multipart(bucket, key)` returns an `upload_id`. `upload_part(upload_id, n, data)` returns an etag. Every part except the last must be at least 5 MB (`MIN_PART_BYTES`), and there can be at most 10,000 parts (`MAX_PARTS`). Nothing is visible at the key until `complete_multipart(upload_id, etags)` succeeds, which then replaces any object already at that key. `abort_multipart(upload_id)` discards the parts.
- **`signed_url(bucket, key, ttl_seconds)`:** returns a download link valid for `ttl_seconds`, at most 86,400 (24 hours).
- **`send_email(user_id, template, params)`:** the existing email sender. It looks up the user's address itself. Two new templates are needed: `report_export_ready` and `report_export_failed`.
- **Export row:** one row in the new `report_exports` table, which records one large export.
- **Active export:** an export row whose status is `queued` or `running`.

## Rules that apply to every step

- **Contents.** The CSV holds what the user sees at click time: the filters and column order from the page URL, plus a header row. Export uses the same `report.view` check as the page and reads report rows only from the read replica.
- **Shared row reader.** Move the rows endpoint's filter parsing, column validation and keyset query into one function, `iter_report_rows(report_id, filters, cols, page_size)`. It reads from the replica only and yields rows in `row_id` order. The rows API, the small export and the job all call it, so export cannot drift from what the page shows.
- **Export state lives in a new `report_exports` table on the primary database.** It is not report data, so the primary is allowed. It must be the primary because the one-at-a-time rule needs a unique index and a lagging replica would show stale status.

  | Column | Meaning |
  |---|---|
  | `export_id` | Primary key. |
  | `report_id`, `user_id` | Whose export it is. |
  | `filters`, `cols` | Snapshot of the view at click time. |
  | `status` | `queued`, `running`, `done` or `failed`. |
  | `job_id` | Queue job id, nullable. |
  | `object_key` | Always `exports/{export_id}.csv`. |
  | `row_total` | Rows written, nullable. |
  | `error` | Failure reason, nullable. |
  | `notified_at` | When the success email was sent, nullable. |
  | `created_at`, `updated_at` | Timestamps. |

- **One at a time.** A partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')` allows one active large export per user per report. Filters are not part of the key, so a second click with different filters gets the first export back (see open questions). Rows are never deleted. Finished and failed rows stay as history, and the bucket's 7-day rule removes their files.
- **Size rule.** Use `reports.row_count` at click time, even though it is the unfiltered total. At 10,000 or fewer the export is synchronous. Above that it is a job. A heavily filtered export of a big report still takes the job path. That is intended and simple.
- **How the user gets a large file.** Only through the emailed link. The page shows the state but offers no download.
- **No cleanup job.** The bucket's lifecycle rules remove old files and abandoned uploads.

## How it runs

### 1. User clicks Download CSV: the request

- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/export` with the filters and `cols` copied from the page URL.
- **Data moves:** browser to API: `report_id`, `filters`, `cols`. The API takes `user_id` from the signed-in session, as the rows API does. The browser never sends it.
- **State kept:** none yet.
- **If it fails:**
  - No `report.view` on the report's workspace: return 403 and do nothing else.
  - Invalid filter or column: return 400. The same validation as the rows API runs here, so a bad request never becomes a job.
  - API or network error: the browser shows an error. Nothing was created, so the user can click again.

### 2. API picks a path

- **Starts it:** step 1 passing its checks.
- **Data moves:** read `reports.row_count` (metadata, not report rows) from wherever the page reads it today. 10,000 rows or fewer goes to step 3. More goes to step 4.
- **State kept:** none.
- **If it fails:** a failed read of `row_count` returns 503 and nothing is created.
- **Stale count:** `row_count` changes only in the nightly rebuild, so it can be wrong only while a rebuild runs. We accept that. See step 3.

### 3. Small export: stream the CSV in the response (no job, nothing stored)

- **Starts it:** step 2 chose the small path.
- **Data moves:**
  - The API replies 200 with `Content-Type: text/csv` and `Content-Disposition: attachment; filename=report-{report_id}.csv`.
  - It writes the header row from the requested `cols`, then loops over `iter_report_rows` (500 rows per page, replica only). A real CSV writer formats each page (correct quoting of commas, quotes and newlines; UTF-8). Each page goes to the response as it is formatted.
  - Memory use is one page. 10,000 rows is about 20 pages, well inside the 60 s limit.
- **State kept:** none. Nothing is written to the database or the bucket.
- **If it fails:**
  - Once streaming starts, the HTTP status is already sent. A replica error or the 60 s kill therefore cuts the connection mid-body. Send no `Content-Length` and use chunked transfer, so the browser treats a cut connection as a failed download, not a complete file.
  - If a stale `row_count` hides a much bigger report, the 60 s kill cuts the download the same way. The user can click again after the nightly rebuild finishes. The stream cannot switch to the job path once it has started.
  - Log the error. There is no retry and no partial state. The user can click again.

### 4. Large export: claim the slot, or return the existing export

- **Starts it:** step 2 chose the large path.
- **Data moves:** in one transaction on the primary, insert a `report_exports` row with `status='queued'`, a new `export_id`, `object_key`, and the `filters` and `cols` snapshot. The transaction holds only this insert and commits before step 5. The enqueue is not inside it, because a job could otherwise start before its row is visible.
  - If the insert succeeds, go to step 5 with the new row.
  - If the unique index rejects it, an export is already active. Select that row. No second row is created.
    - If the row is `queued`, has no `job_id` and is older than 2 minutes, the click that created it died before queueing. Go to step 5 with this row so the job is queued now.
    - Otherwise return it as it is: 202 with `{export_id, status}` and no new job.
- **State kept:** the `report_exports` row.
- **If it fails:** a database error returns 503 and nothing is created.

### 5. Enqueue the job and answer immediately

- **Starts it:** step 4 passed a row that has no job yet: a new row, or the stale `queued` row found by a repeat click.
- **Data moves:**
  - `enqueue("export_report_csv", {"export_id": ...})`. The payload is the id only. The job reads everything else from the row.
  - Store the returned `job_id` on the row. This update touches only `job_id`, never `status`, so it cannot overwrite a `running` or `done` written by a fast worker. The worker finds its row by `export_id` and never needs `job_id`, so it does not matter if the worker starts first.
  - Respond 202 with `{export_id, status:"queued"}` straight away. This is also the answer to a repeat click that repaired a stale row.
- **State kept:** `job_id` on the row.
- **If it fails:**
  - `enqueue` raises on a new row: set the row to `failed` (error "could not queue"), return 503. The user can click again.
  - The process dies between the insert and the enqueue: the row stays `queued` with no `job_id` and blocks the user until they click again. Step 4 then finds it and sends it here. Two clicks racing on the same stale row may queue two jobs. That is safe, because running the handler twice is safe (step 7).

### 6. Page shows the export's state

- **Starts it:** the 202 response, or the user opening `/reports/{report_id}` later.
- **Data moves:**
  - `GET /api/reports/{report_id}/export` checks `report.view`, then reads from the primary the current user's most recent export for that report (highest `created_at`, any status). It returns `{export_id, status, created_at}`, or 204 if there is none. Older rows and their files stay (files until the 7-day rule), but only the newest is shown, so a new click replaces what the page shows.
  - The page shows queued, running, done or failed. While the status is `queued` or `running` it polls every 5 seconds. It stops on `done` or `failed`.
  - On `done` the page says the download link was sent by email. It offers no download button.
  - The Download CSV button is disabled while a large export is active. Small exports create no row, so the page cannot see them. For a small export the browser just saves the file, the button is disabled only while that request is in flight, and the status area does not change.
- **State kept:** reads only. The status is whatever the job wrote in steps 7 to 11.
- **If it fails:** a failed poll keeps the last known status and retries on the next tick. A reload always gets the stored state.

### 7. Worker starts an attempt

- **Starts it:** the queue calls `export_report_csv(ctx, payload)` on attempt 1 and on each retry. It may also run again after a success (at-least-once delivery).
- **Data moves:** load the row by `export_id`.
  - `done` with `notified_at` set: return (duplicate delivery).
  - `done` with `notified_at` null: jump to step 10. The file is complete, so only the email is missing.
  - `failed`: return.
  - Otherwise `UPDATE ... SET status='running'`.
- **State kept:** `status='running'`, `updated_at`.
- **If it fails:**
  - Raising fails the attempt, and the queue retries after 60 s, then 300 s. A missing row is a bug: raise and let the queue retry. The final-failure hook (step 11) handles the end.
  - A killed or crashed attempt leaves the row `running`. During the wait the page keeps showing `running` and the slot stays held, so no second export can start. The retry sets `running` again, which changes nothing. Only `done` or `failed` frees the slot.

### 8. Stream rows into the bucket (the bounded-memory loop)

- **Starts it:** step 7 found work to do.
- **Data moves:**
  - `start_multipart("exports", object_key)` returns an `upload_id`. Keep it in a local variable.
  - Write the header row into an in-memory buffer.
  - Loop over `iter_report_rows` (replica only) with a bigger page than the UI, for example 2,000 rows. Append each formatted page to the buffer.
  - When the buffer reaches **8 MB** (above `MIN_PART_BYTES`), call `upload_part(upload_id, n, buffer)`, keep the etag and clear the buffer. Send what remains as the last part, which may be under 5 MB.
  - **Memory:** the worker holds about one 8 MB buffer, one page of rows and a list of etags (about 113 for the 900 MB report). That is far below 512 MB and does not grow with the report. The job never holds a whole report.
  - **Part limit:** 900 MB is about 113 parts, well under 10,000. With 8 MB parts the limit is not reached until about 80 GB.
  - **Time:** 2 million rows in 1800 s needs about 1,100 rows/s sustained, about 2 s per 2,000-row page including the upload. See open questions.
  - **Consistency:** each page is a separate keyset query, so the file is not one snapshot. Data changes only in the nightly rebuild, so a job overlapping a rebuild could miss or repeat rows. See open questions.
- **State kept:** the multipart upload and etag list live only in this attempt. The object key is fixed, so a retry needs nothing from the failed attempt.
- **If it fails:**
  - On any exception, call `abort_multipart(upload_id)` (best effort, ignore its own errors), then re-raise. The attempt fails and the retry starts fresh.
  - A worker crash or timeout skips the abort. The bucket's 24-hour rule discards the orphaned parts.
  - **A half-written file can never be downloaded**, because nothing is visible at the key until step 9.

### 9. Complete the upload, then mark the export done

- **Starts it:** the loop in step 8 has no rows left.
- **Data moves:**
  - `complete_multipart(upload_id, etags)` makes the whole object visible at once. If an earlier attempt had already completed it, this replaces it with an identical file.
  - Then `UPDATE report_exports SET status='done', row_total=... WHERE export_id=... AND status='running'`.
  - If that changes zero rows, the row was no longer `running`. Reload it. `done` with `notified_at` null: go to step 10. `done` and notified: stop. `failed`: stop and send no email. The email must match what the page shows.
- **State kept:** the finished object in the `exports` bucket. The row now says `done`.
- **If it fails:**
  - `complete_multipart` raises: handle as in step 8 and retry.
  - The process dies after completing but before the status update: the retry rebuilds and replaces the same object. Wasteful but correct.
  - Status becomes `done` only after the object is whole.

### 10. Email the download link

- **Starts it:** step 9 finished, or step 7 found `done` with `notified_at` null.
- **Data moves:**
  - The report name comes from the `reports` row for the export's `report_id`. `send_email` takes `user_id` from the export row and finds the address itself.
  - `url = signed_url("exports", object_key, 86_400)` is made now, so the 24 hours start when the email is sent.
  - `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`, then set `notified_at = now()`.
  - The job never re-checks `report.view` (see open questions). It uses `filters` and `cols` only in step 8.
- **State kept:** `notified_at`. The signed URL is not stored.
- **If it fails:**
  - `send_email` raises: the attempt fails. The retry goes through step 7, sees `done` with `notified_at` null and runs only this step, without rebuilding the file.
  - A crash after sending but before `notified_at` is written can cause a duplicate email. We accept that, because a duplicate is better than a missing link.
  - The page already shows `done`, because step 9 committed first.

### 11. Final failure

- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once after attempt 3 fails, including a third 1800 s timeout. It is registered as `@job("export_report_csv", on_final_failure=...)`.
- **Data moves:**
  - `UPDATE report_exports SET status='failed', error=<short message> WHERE export_id=... AND status != 'done'`.
  - If a row was updated, `send_email(user_id, "report_export_failed", {report name})`.
  - Optionally call `abort_multipart` if an upload is known (normally nothing to do).
- **State kept:** `status='failed'` and `error`. Failed is not active, so the user can start a new export.
- **If it fails:**
  - The export is already `done` (only the email kept failing): leave it `done`, send no failure email because the file exists, and raise an alert about the failed email.
  - The failure email itself fails: log it. The page still shows `failed`.
  - The hook never runs or dies before the update: the row stays `running` and holds the slot. See open questions.

## Building and testing

Tests to write:

- Exactly 10,000 versus 10,001 `row_count` pick different paths.
- The small path sends no `Content-Length`, creates no row and makes no storage calls.
- Two concurrent large clicks give one row and one job (unique index).
- A repeat click on a stale `queued` row with no `job_id` queues it and returns 202.
- A worker that starts before `job_id` is stored still runs, and storing `job_id` does not change `status`.
- A new click after a `done` export creates a new row, and the page shows the new one.
- A killed attempt followed by a retry gives one complete object and one email.
- `status='done'` is never visible before the object exists.
- Duplicate delivery after success sends no second email and does not rebuild the file.
- A 2-million-row run stays under 512 MB peak memory.
- The final-failure path sets `failed` and sends the failure email.

Also needed: add the `report_export_ready` and `report_export_failed` email templates, and extract `iter_report_rows` from the rows endpoint.

## Open questions for the requester

1. **Throughput.** Does the replica sustain about 1,100 rows/s on the largest report? Run the job once against it before release. The queue cannot resume across attempts, so if it is too slow the fix is a faster query or a larger page. Otherwise all three attempts time out.
2. **Revoked access.** Permission is checked at click time only. Should the job re-check `report.view` before emailing the link?
3. **Different filters on a second click.** The user gets the already-active export, which may have different filters. Is a short message on the page enough?
4. **Link after 24 hours.** The link expires after 24 hours but the file lives 7 days, and the page offers no download. Should it make a fresh signed URL on demand? The brief does not ask for it, so it is not planned.
5. **Spreadsheet formulas.** Should cells starting with `=`, `+`, `-` or `@` be escaped against formula injection?
6. **Queue wait.** The queue's behaviour when all workers are busy (order, and whether the 1800 s timeout counts waiting) is not documented. The plan assumes the timeout counts only running time.
7. **Rebuild overlap.** It is not documented how the nightly rebuild changes `report_rows` (in place or by replacement) or what the replica shows mid-rebuild. Until known, an export overlapping a rebuild may be inconsistent. Could exports simply be avoided during the rebuild window?
8. **Where the final-failure hook runs.** `jobs.py` does not say which process runs the hook or what happens if it dies. If it can die, a row could stay `running` forever. Does the queue guarantee the hook, or do we need a sweep?
9. **Unseen code.** The code behind `send_email`, the permission check, sessions and the source of `row_count` and report names was not available. The plan assumes they work as described above.
