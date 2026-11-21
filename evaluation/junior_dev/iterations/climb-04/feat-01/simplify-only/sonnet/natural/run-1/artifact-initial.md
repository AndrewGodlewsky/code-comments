# Plan: "Download CSV" on the reports page

## Overview

One endpoint handles the click. It decides by `reports.row_count`:

- **10,000 rows or fewer:** the response is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the endpoint records an export, queues a background job and returns at once. The job streams the file into the `exports` bucket and emails a 24-hour link. The page shows the export's state.

New state lives in one new table, `report_exports`, on the primary database. It holds export metadata only. Report rows are always read from the read replica.

### Existing facts this plan relies on

- The rows API checks the `report.view` permission on the report's workspace and returns 403 if it is missing. Export reuses that check.
- Filters and column order exist only in the page URL. The server stores nothing about what the user is looking at, so the click must send them.
- Rows are paged by keyset (`row_id > after ORDER BY row_id`) and never by OFFSET.
- API requests are killed after 60 seconds.
- Workers have 512 MB of memory.
- The queue makes at most 3 attempts, waits 60 s then 300 s between them, and kills an attempt after 1800 s. It keeps no progress between attempts and may run a handler twice for the same job.
- Storage multipart uploads are invisible until `complete_multipart`. Each part except the last must be at least 5 MB. `signed_url` allows at most 86,400 s. The bucket deletes objects after 7 days and discards unfinished multipart uploads after 24 hours.

### New state: table `report_exports` (primary database)

| Column | Meaning |
|---|---|
| `export_id` | primary key |
| `user_id`, `report_id` | who asked, and for which report |
| `query_string` | the filters and `cols` copied from the page URL |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | the queue's id, null until enqueued |
| `attempt` | the attempt number currently or last running |
| `file_key` | null until the file is complete, then `export-{export_id}.csv` |
| `notified_at` | set once the success email has been sent |
| `error` | short reason, set on failure |
| `created_at`, `updated_at`, `finished_at` | timestamps |

A **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')` enforces "one large export at a time". The database enforces it, so two simultaneous clicks cannot both win.

---

## Steps

### 1. User clicks "Download CSV" (browser)

- **Starts when:** the user clicks the button on `/reports/{report_id}`.
- **Data moves:** the page sends `POST /api/reports/{report_id}/export` with the current URL's query string (filters, `cols`). The server keeps no view state, so the page must send it.
- **State:** none. The button is disabled while the request is in flight.
- **If it fails:** a network error shows "Export failed to start, try again". Nothing was created that could be left behind. If step 4b already created a row, the next click returns that row.

### 2. Endpoint authorises and validates (API server)

- **Starts when:** the request arrives.
- **Data moves:** the endpoint runs the `report.view` check on the report's workspace, the same code as the rows API.
  - It parses `filters` and `cols` with the same parser the rows API uses.
  - It rejects any column not belonging to the report.
  - It reads `reports.row_count`. This is not report row data, but read it from the replica too so no extra primary load is added.
- **State:** none.
- **If it fails:**
  - Missing permission returns 403.
  - Bad filters or columns return 400.
  - A replica error returns 503 and the user can click again.

### 3. Choose the path (API server)

- **Starts when:** step 2 passes.
- **Data moves:** `row_count <= 10,000` goes to step 4a. Anything larger goes to step 4b. A null `row_count` goes to 4b, the safe path.
- **Note:** `row_count` is the unfiltered total. A filtered export of a large report therefore still takes the job path even if few rows match. That is accepted, because it errs toward the safe path.
- **State:** none.
- **If it fails:** there is no separate failure here.

### 4a. Small path: build the CSV and respond (API server)

- **Starts when:** step 3 chose the small path.
- **Data moves:**
  1. Write the header row (the requested columns, in the requested order).
  2. Loop over replica pages of 500 rows (`row_id > after ORDER BY row_id`, with the filters applied) and append CSV lines to an in-memory buffer.
  3. Stop at the first empty page.
  4. Reply `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{id}.csv"`.
  - Size: 10,000 rows is about 4.5 MB at roughly 450 bytes per row (900 MB / 2M rows). That is safe to buffer. Buffering also means an error can still return a clean error status, because no headers have been sent yet.
  - The browser code sees the `text/csv` content type, saves the body as a file and shows no export status.
  - **Guard against a stale `row_count`:** if the loop reads more than 10,000 rows, discard the buffer and go to step 4b. Nothing has been sent yet, so this is safe.
- **State:** none. Nothing is stored and no job runs.
- **If it fails:** a replica error or timeout returns 500/503 with a JSON error, and the user clicks again. The 60-second API limit is far above what 20 page queries need.

### 4b. Large path: register the export (API server, primary database)

- **Starts when:** step 3 chose the large path.
- **Data moves:**
  - Insert a `report_exports` row: `status='queued'`, `query_string`, `user_id`, `report_id`, with `ON CONFLICT DO NOTHING` against the partial unique index.
  - If the insert created a row, continue to step 5.
  - If it conflicted, select the user's active export of this report and return it as `200 {export_id, status, ...}` without starting anything. This is the "click again returns the existing export" rule. It applies even if the new click has different filters, and the response includes the active export's own filters so the page can show what is running.
- **State:** the new row in `report_exports`.
- **If it fails:** if the database is unreachable, return 503 and nothing exists.

### 5. Enqueue the job (API server)

- **Starts when:** step 4b inserted a new row.
- **Data moves:** call `enqueue("report_export", {"export_id": ...})`. The payload holds only the id, which is far under the 64 KB limit. Filters are read from the row. Save the returned `job_id` on the row, then respond `202 {export_id, status:'queued'}`.
- **State:** `job_id` on the row.
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` (error "could not queue"), which frees the unique slot, and return 503.
  - If the server dies between the insert and the enqueue, the row is `queued` with a null `job_id`. This is the one gap in the flow. Repair it without a cleanup job: when a later click conflicts with a row that is `queued`, has a null `job_id` and is older than 2 minutes, step 4b enqueues for that row instead of just returning it. Step 7 tolerates duplicate enqueues.

### 6. The page shows the export's state (browser plus API)

- **Starts when:** the page loads, or a 202/200 JSON response arrives from the click.
- **Data moves:**
  - On page load the page calls `GET /api/reports/{report_id}/exports/latest`. The server runs `report.view` and returns the user's most recent export of this report (`status`, `attempt`, `created_at`, `finished_at`, `error`) from the primary table. This is what makes the state show up when the user comes back later.
  - While the status is `queued` or `running`, the page polls the same endpoint every 5 seconds. It stops on `done` or `failed`.
  - Display text:
    - `queued`: "Export queued".
    - `running`: "Export running" (with "attempt 2 of 3" if `attempt` > 1).
    - `done`: "Export ready, the link was emailed to you at {time}". The email link expires 24 hours after it was sent, which the page can state from `finished_at`.
    - `failed`: "Export failed" plus a "Try again" button.
- **State:** none new. The page only reads `report_exports`.
- **If it fails:** a failed poll keeps the last shown state and retries on the next tick. The state is in the database, so a reload recovers it.

### 7. Worker starts the job (worker pool)

- **Starts when:** the queue calls `handler(ctx, {"export_id"})`. This happens on the first attempt and on each retry.
- **Data moves:**
  1. Load the row. If `status='failed'`, return.
  2. If `status='done'` and `notified_at` is set, return. This is a duplicate delivery, so send nothing.
  3. If `status='done'` and `notified_at` is null, skip straight to step 10.
  4. Otherwise re-check `report.view` for `user_id`, in case access was removed since the click. If it is now denied, set `status='failed'` with `error='access removed'` and return. Do not retry and do not email.
  5. Set `status='running'`, `attempt=ctx.attempt`, `job_id=ctx.job_id`.
- **State:** the status and attempt fields on the row.
- **If it fails:** an error here raises, so the queue retries. The row stays `queued` or `running`.

### 8. Stream the rows into storage (worker, replica to bucket)

- **Starts when:** step 7 passed.
- **Data moves:**
  1. `upload_id = start_multipart("exports", file_key)`, with `file_key = "export-{export_id}.csv"`. The key is the same on every attempt.
  2. Write the header row into a bytes buffer.
  3. Loop: read a page of 5,000 rows from the **replica** (`row_id > after ORDER BY row_id LIMIT 5000`, same filters and columns, same query builder as the rows API). Append CSV lines to the buffer and remember the last `row_id`.
  4. Whenever the buffer reaches 8 MB, call `upload_part(upload_id, n, buffer)`, keep the returned etag, and **empty the buffer**.
  5. At the end of the data, upload the remainder as the final part (it may be under 5 MB, which storage allows for the last part). An empty result still produces a header-only file.
  - **Memory:** at any moment the worker holds one buffer (about 8 MB), one page (about 2.3 MB), and the list of etags (about 113 entries for 900 MB). That is a small fraction of 512 MB, and independent of report size.
  - **Parts limit:** 900 MB at 8 MB per part is about 113 parts, far below the 10,000-part maximum.
  - **Time:** 2 million rows is about 400 page queries plus about 900 MB of upload. I have not measured this, so measure it in staging against the largest report. The target is at most 10 minutes, well under the 1,800 s attempt timeout.
  - **Deadline guard:** check the elapsed time after each page. At 1,700 s, raise an error. That lets step 11 abort the upload cleanly instead of the queue killing the worker.
- **State:** the open multipart upload, which is invisible. Its `upload_id` is not saved, because the queue keeps no progress and every attempt starts from the beginning.
- **If it fails:** on any exception, call `abort_multipart(upload_id)` best-effort, then re-raise so the queue retries (step 11). If the worker is killed or dies, no abort runs. The bucket's rule discards unfinished uploads after 24 hours, so this needs no cleanup job. Because nothing is visible until step 9, a partial file can never be downloaded.

### 9. Make the file visible and mark it done (worker)

- **Starts when:** step 8 has uploaded the last part.
- **Data moves:** call `complete_multipart(upload_id, etags)`. This is the only moment the file appears at `file_key`. Then update the row: `status='done'`, `file_key`, `finished_at=now`.
- **State:** the object in the `exports` bucket and the `done` row. The bucket deletes the object after 7 days. We build no cleanup.
- **If it fails:**
  - If `complete_multipart` raises, nothing is visible. Abort and retry as in step 8.
  - If the worker dies after the complete but before the row update, the retry rebuilds the same key. `complete_multipart` replaces the object atomically, so the file is never half-written.

### 10. Email the download link (worker)

- **Starts when:** step 9 finished, or step 7 found `done` with no `notified_at`.
- **Data moves:**
  - `url = signed_url("exports", file_key, 86400)`. This is the maximum the helper allows and equals the required 24 hours. Generate it now, at send time, so the 24 hours start when the user is told.
  - Call `send_email(user_id, "report_export_ready", {report_name, url, expires_in_hours: 24})`.
  - Then set `notified_at=now`.
- **State:** `notified_at`.
- **If it fails:**
  - If `send_email` raises, the handler raises and the queue retries. The retry sees `done` without `notified_at` and only resends the email, without rebuilding the file (step 7.3).
  - If the email was sent but the `notified_at` write failed, the user may get a second email. That is rare and harmless, so accept it.
  - **Known gap:** if all 3 attempts fail at this step, the file exists and the row stays `done`, but the user never got the link. The final-failure handler (step 11) does not mark it `failed`, because a file does exist. Log it for operators. Decide if a page-side "get link" button is wanted (see open questions).

### 11. Retries and final failure (queue plus handler)

- **Starts when:** an attempt raises, times out or loses its worker.
- **Data moves:**
  - The queue retries after 60 s, then 300 s, up to 3 attempts in total. The row stays `running`, with `attempt` showing the retry count.
  - Each retry starts from step 7 and rebuilds the file from the beginning.
  - After the last attempt fails, the queue calls `on_final_failure(ctx, payload, error)`, registered on the job. It must be safe to call twice and:
    1. Updates the row: `status='failed'`, `error` = short reason, `finished_at=now`, but only `WHERE status != 'done'`.
    2. Calls `send_email(user_id, "report_export_failed", {report_name})`. Wrap this in try/except so a mail failure cannot undo step 1.
  - Setting `failed` frees the unique-index slot, so the user can click again.
- **State:** `failed`, plus `error` on the row.
- **If it fails:** if the email fails, the page still shows `failed` (step 6), so the user can see the failure when they return.

### 12. Old files (no work)

Nothing to build. The bucket's lifecycle rule deletes each object 7 days after creation. The email link stops working after 24 hours.

---

## Tests to write

- Exactly 10,000 rows goes to the small path (no job, no stored file). 10,001 goes to the job path.
- A stale `row_count` (says 9,000, actually 12,000) falls through from 4a to 4b without sending a partial response.
- Two simultaneous clicks produce one row and one job, and both get the same `export_id`.
- A user without `report.view` gets 403 on the click and on the status endpoint.
- A job on 2 million generated rows keeps worker memory flat (well under 512 MB) and finishes inside the attempt timeout.
- Kill the worker mid-upload: no object appears at `file_key`, and the retry produces a complete file.
- The handler running twice for a finished job sends one success email.
- Three failing attempts leave the row `failed`, send one failure email, and allow a new export.

## Open questions

1. **Nightly rebuild during a long export.** The job reads from the replica for several minutes. If the nightly rebuild rewrites rows in that window, the file could mix old and new data. Do we need a rebuild marker to detect this, or is it acceptable?
2. **After the 24-hour email link expires.** The file lives 7 days but the page offers no new link. Should the page show a "get a new link" button, which would be a small extra endpoint? That would also cover the step 10 known gap.
3. **CSV formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in spreadsheets. Should the export prefix them with `'`? This changes the cell values.
4. **Exact semantics of `send_email`.** We assume it raises on failure and may deliver twice on retry. Please confirm.
