# Plan: "Download CSV" on the reports page

## Summary

Today the reports page loads rows from an API that reads the read replica, checks `report.view`, and pages by `row_id`. The server does not store the user's filters; they live only in the page URL.

This plan adds one endpoint for the click. It picks a path by `reports.row_count`:

- **10,000 rows or fewer:** the response is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the endpoint records an export row, queues a background job and returns at once. The job streams the file into the `exports` bucket and emails a 24-hour link. The page shows the export's state.

## Terms

- **Small path / large path:** the two ways to export, chosen by size.
- **Export row:** one row in the new table `report_exports` (primary database). It holds metadata only. Report rows are always read from the read replica.
- **Multipart upload:** a storage upload made of parts. Nothing is visible at the file's key until `complete_multipart` succeeds, so a half-written file can never be downloaded.
- **Attempt:** one run of the job handler. The queue makes at most 3 (waits 60 s, then 300 s; kills an attempt after 1800 s). It keeps no progress between attempts and may run a handler twice for the same job.

### The `report_exports` table

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
| `created_at`, `finished_at` | timestamps |

A partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')` allows only one large export at a time per user and report. The database enforces it, so two simultaneous clicks cannot both win.

## How the system runs

### 1. User clicks "Download CSV" (browser)

- **Starts when:** the user clicks the button on `/reports/{report_id}`.
- **Does:** sends `POST /api/reports/{report_id}/export` with the page URL's query string (filters, `cols`). The button is disabled while the request is in flight.
- **Keeps data in:** nothing.
- **When it goes wrong:** a network error shows "Export failed to start, try again". If an export row was already created, the next click returns it.

### 2. Endpoint checks the request (API server)

- **Starts when:** the request arrives.
- **Does:** runs the same `report.view` check as the rows API. Parses `filters` and `cols` with the rows API's parser and rejects columns not in the report. Reads `reports.row_count` from the replica.
- **Keeps data in:** nothing.
- **When it goes wrong:** no permission returns 403. Bad filters or columns return 400. A replica error returns 503 and the user can click again.

### 3. Choose the path (API server)

- **Starts when:** step 2 passes.
- **Does:** `row_count <= 10,000` goes to 4a. Anything larger, or a null `row_count`, goes to 4b. `row_count` is the unfiltered total, so a filtered export of a large report still takes the large path. That is accepted: it errs toward the safe path.
- **Keeps data in:** nothing.
- **When it goes wrong:** nothing can fail here.

### 4a. Small path: build the CSV and reply (API server)

- **Starts when:** step 3 chose the small path.
- **Does:**
  1. Write the header row (requested columns, requested order) into an in-memory buffer.
  2. Read replica pages of 500 rows (`row_id > after ORDER BY row_id`, filters applied) and append CSV lines, until a page is empty. 10,000 rows is about 4.5 MB, which is safe to buffer.
  3. Reply `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`. The browser saves it and shows no export status.
  4. Stale `row_count` guard: if the loop reads more than 10,000 rows, discard the buffer and go to 4b. Nothing has been sent yet, so this is safe.
- **Keeps data in:** nothing is stored and no job runs.
- **When it goes wrong:** a replica error returns 503 with a JSON error and the user clicks again. Nothing was sent before the buffer was full, so the error status is clean.

### 4b. Large path: register the export (API server, primary database)

- **Starts when:** step 3 chose the large path.
- **Does:** inserts an export row (`status='queued'`, `query_string`, `user_id`, `report_id`) with `ON CONFLICT DO NOTHING` against the partial unique index.
  - If a row was created, go to step 5.
  - If it conflicted, return the user's active export of this report as `200 {export_id, status, query_string}` and start nothing. This applies even if the new click had different filters; the response carries the active export's own filters so the page can show what is running.
- **Keeps data in:** `report_exports`.
- **When it goes wrong:** if the database is unreachable, return 503. Nothing exists.

### 5. Enqueue the job (API server)

- **Starts when:** step 4b created a row.
- **Does:** calls `enqueue("report_export", {"export_id": ...})`, saves the returned `job_id` on the row, and replies `202 {export_id, status:'queued'}`. Filters are read from the row, so the payload is tiny.
- **Keeps data in:** `job_id` on the export row.
- **When it goes wrong:**
  - If `enqueue` raises, set the row to `failed` (error "could not queue"). That frees the unique slot. Return 503.
  - If the server dies between insert and enqueue, the row is `queued` with a null `job_id`. When a later click conflicts with such a row older than 2 minutes, step 4b enqueues for it instead of only returning it. Step 7 tolerates duplicate enqueues.

### 6. The page shows the export's state (browser and API)

- **Starts when:** the page loads, or the click returns a 200 or 202 JSON response.
- **Does:** calls `GET /api/reports/{report_id}/exports/latest`. The server runs `report.view` and returns the user's most recent export of this report (`status`, `attempt`, `created_at`, `finished_at`, `error`). While the status is `queued` or `running`, the page polls every 5 seconds and stops on `done` or `failed`. It shows:
  - `queued`: "Export queued".
  - `running`: "Export running", plus "attempt 2 of 3" when `attempt` is above 1.
  - `done`: "Export ready, the link was emailed to you". The link expires 24 hours after the email.
  - `failed`: "Export failed" and a "Try again" button.
- **Keeps data in:** nothing new. The page only reads `report_exports`, so a reload recovers the state.
- **When it goes wrong:** a failed poll keeps the last state and retries on the next tick. A user without `report.view` gets 403.

### 7. Worker starts the job (worker pool)

- **Starts when:** the queue calls `handler(ctx, {"export_id"})`, on the first attempt and on each retry.
- **Does:**
  1. Load the row. If `status='failed'`, return.
  2. If `status='done'` and `notified_at` is set, return. This is a duplicate delivery; send nothing.
  3. If `status='done'` and `notified_at` is null, skip to step 10.
  4. Re-check `report.view` for `user_id`. If now denied, set `status='failed'`, `error='access removed'` and return. No retry, no email.
  5. Set `status='running'`, `attempt=ctx.attempt`, `job_id=ctx.job_id`.
- **Keeps data in:** the status and attempt fields on the export row.
- **When it goes wrong:** an error here raises, so the queue retries. The row stays `queued` or `running`.

### 8. Stream rows into storage (worker, replica to bucket)

- **Starts when:** step 7 passed.
- **Does:**
  1. `upload_id = start_multipart("exports", file_key)` with `file_key = "export-{export_id}.csv"`. The key is the same on every attempt.
  2. Put the header row in a bytes buffer.
  3. Loop: read 5,000 rows from the replica (`row_id > after ORDER BY row_id LIMIT 5000`, same filters, columns and query builder as the rows API). Append CSV lines to the buffer.
  4. Whenever the buffer reaches 8 MB, call `upload_part`, keep the etag and empty the buffer.
  5. At the end, upload the remainder as the last part (it may be under 5 MB). An empty result still gives a header-only file.
  6. Deadline guard: after each page, if 1,700 s have passed, raise so the upload is aborted before the queue kills the worker.
- **Keeps data in:** the open multipart upload, which is invisible. Its `upload_id` is not saved, because each attempt starts over.
- **Limits:** the worker holds one 8 MB buffer, one page of about 2.3 MB, and about 113 etags for the largest report (900 MB). That is far below 512 MB and does not grow with report size. 113 parts is far below the 10,000-part maximum. Time is not measured yet: about 400 page queries plus 900 MB of upload, target under 10 minutes. Measure it in staging on the largest report.
- **When it goes wrong:** on any exception, call `abort_multipart(upload_id)` as best effort and re-raise so the queue retries (step 11). If the worker dies, no abort runs; the bucket discards unfinished uploads after 24 hours, so no cleanup job is needed. A partial file is never visible.

### 9. Make the file visible and mark it done (worker)

- **Starts when:** step 8 uploaded the last part.
- **Does:** calls `complete_multipart(upload_id, etags)`, the only moment the file appears at `file_key`. Then sets the row to `status='done'`, `file_key`, `finished_at=now`.
- **Keeps data in:** the object in the `exports` bucket and the `done` row. The bucket deletes the object after 7 days.
- **When it goes wrong:** if `complete_multipart` raises, nothing is visible; abort and retry as in step 8. If the worker dies after completing but before the row update, the retry rebuilds the same key, and `complete_multipart` replaces the object, so the file is never half-written.

### 10. Email the download link (worker)

- **Starts when:** step 9 finished, or step 7 found `done` with no `notified_at`.
- **Does:** creates `signed_url("exports", file_key, 86400)` at send time, so the 24 hours start when the user is told. Calls `send_email(user_id, "report_export_ready", {report_name, url, expires_in_hours: 24})`. Then sets `notified_at=now`.
- **Keeps data in:** `notified_at`.
- **When it goes wrong:**
  - If `send_email` raises, the handler raises and the queue retries. The retry only resends the email (step 7.3).
  - If the email was sent but the `notified_at` write failed, the user may get a second email. Accepted.
  - If all 3 attempts fail here, the file exists and the row stays `done`, but the user never got the link. Log it for operators. See the open questions.

### 11. Retries and final failure (queue and handler)

- **Starts when:** an attempt raises, times out or loses its worker.
- **Does:** the queue retries from step 7 and rebuilds the file from the start. The row stays `running` and `attempt` shows the count. After the last attempt fails, the queue calls `on_final_failure(ctx, payload, error)`, which must be safe to call twice:
  1. Update the row to `status='failed'`, short `error`, `finished_at=now`, only `WHERE status != 'done'`. This frees the unique slot, so the user can click again.
  2. Call `send_email(user_id, "report_export_failed", {report_name})` inside try/except so a mail failure cannot undo step 1.
- **Keeps data in:** `status='failed'` and `error` on the row.
- **When it goes wrong:** if the email fails, the page still shows `failed` when the user returns.

### 12. Old files (no work)

The bucket deletes each object 7 days after creation. The email link stops working after 24 hours. Nothing to build.

## What happens when things fail

Each step above lists its own failures. In short:

| Where | Failure | Result |
|---|---|---|
| Steps 2, 4a, 4b, 5 | permission, input, replica or database error, enqueue error | error status returned, the user can click again; no half-created export is left active |
| Step 5 | server dies before enqueue | a later click re-enqueues after 2 minutes |
| Steps 7 to 9 | any error, timeout or dead worker | abort the upload, the queue retries from scratch; the file is invisible until complete |
| Step 10 | email fails | retry resends the email only |
| Step 11 | last attempt fails | row `failed`, failure email, new export allowed |

## Tests to write

- Exactly 10,000 rows goes to the small path (no job, no stored file). 10,001 goes to the large path.
- A stale `row_count` (says 9,000, actually 12,000) falls through from 4a to 4b without sending a partial response.
- Two simultaneous clicks produce one row and one job, and both get the same `export_id`.
- A user without `report.view` gets 403 on the click and on the status endpoint.
- A job on 2 million generated rows keeps worker memory flat (well under 512 MB) and finishes inside the attempt timeout.
- Kill the worker mid-upload: no object appears at `file_key`, and the retry produces a complete file.
- The handler running twice for a finished job sends one success email.
- Three failing attempts leave the row `failed`, send one failure email, and allow a new export.

## Open questions

1. **Nightly rebuild during a long export.** The job reads the replica for several minutes. If the nightly rebuild rewrites rows in that window, the file could mix old and new data. Do we need a rebuild marker, or is it acceptable?
2. **After the 24-hour link expires.** The file lives 7 days but the page offers no new link. Should the page get a "get a new link" button (a small extra endpoint)? It would also cover the step 10 gap.
3. **CSV formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in spreadsheets. Should the export prefix them with `'`? This changes cell values.
4. **`send_email` semantics.** We assume it raises on failure and may deliver twice on retry. Please confirm.
