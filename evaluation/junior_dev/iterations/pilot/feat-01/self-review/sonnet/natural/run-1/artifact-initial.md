# Plan: CSV export for the reports page

## How it works

A **Download CSV** button on `/reports/{report_id}` sends the current page view (filters and column order from the URL) to one new endpoint. The server picks a path from `reports.row_count`.

- **10,000 rows or fewer:** the response is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the response is immediate and a background job builds the file. The job streams the rows into the `exports` bucket as a multipart upload. When the upload completes, it emails a 24-hour link. If the last attempt fails, it emails a failure notice instead.

Both paths use the same CSV-writing code. That code reads from the read replica in pages of `row_id`.

### Terms used below

- **Replica:** the read replica. All report rows come from here and never from the primary.
- **Primary:** the primary database. It holds only the new export-tracking table, which is not report data.
- **View:** the normalised pair `{filters, cols}` taken from the page URL.

### Names I am proposing

These do not exist yet:

- Table `report_exports`.
- Endpoints `POST /api/reports/{id}/exports`, `GET /api/reports/{id}/exports/latest` and `GET /api/reports/{id}/exports/{export_id}/download`.
- Job `report_export`.
- Email templates `report_export_ready` and `report_export_failed`.
- Object key `reports/{report_id}/{export_id}.csv`.

### New state: the `report_exports` table (primary)

| Column | Purpose |
|---|---|
| `id` | Export id. It is also the job payload and part of the object key. |
| `report_id`, `user_id` | Who asked for what. |
| `filters`, `cols` | The normalised view, saved so the job and the page agree on what was exported. |
| `state` | `queued`, `running`, `done` or `failed`. |
| `attempt` | The current attempt number, from `ctx.attempt`. |
| `job_id` | The id returned by `enqueue`. |
| `upload_id` | The current multipart upload, so a later attempt can abort a dead one. |
| `object_key`, `finished_at` | Set when the file is published. |
| `ready_email_sent_at` | Makes the success email safe to repeat. |
| `error` | A short failure reason. |
| `created_at`, `updated_at` | Timestamps. |

**Unique partial index** on `(user_id, report_id) WHERE state IN ('queued','running')`. This enforces "one large export at a time" in the database, so two simultaneous clicks cannot both win.

---

## Steps

### 1. User clicks Download CSV
- **Starts it:** the user clicks the button.
- **Data moves:** the page sends `POST /api/reports/{report_id}/exports` with the `filters` and `cols` from the current URL. It sends the same values the rows API uses.
- **State:** none. The server stores nothing about what the user is looking at, and the view travels only in this request.
- **If it fails:** the page shows an inline "Export failed to start, try again" message. A network error leaves nothing behind, so a retry is safe.

### 2. Server authorises and validates
- **Starts it:** the request from step 1.
- **Data moves:**
  - Run the same `report.view` check on the report's workspace that the rows API runs.
  - Parse `filters` and `cols` with the rows API's own parsing code, so the export means exactly what the table shows.
  - Reject unknown columns.
- **State:** none.
- **If it fails:** return 403 without `report.view`, or 400 for a bad filter or column. Nothing is created.

### 3. Server picks the path
- **Starts it:** step 2 succeeded.
- **Data moves:** read `reports.row_count`.
  - 10,000 or fewer goes to step 4.
  - More than 10,000 goes to step 5.
  - `row_count` is the unfiltered total, so a filtered export is never larger than it. The threshold can therefore only send a small filtered view down the job path, never the reverse.
- **State:** none. `row_count` is rewritten nightly, so it can be stale until then. That is acceptable for choosing a path.
- **If it fails:** a failed read returns 500. Nothing is created.

### 4. Small path: the response is the CSV
- **Starts it:** step 3 chose "small".
- **Data moves:**
  - Respond 200 with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
  - Write the header row (column names in `cols` order).
  - Then stream the rows from the replica with keyset paging (`row_id > after ORDER BY row_id LIMIT 500`), one page at a time, never `OFFSET`.
  - That is at most 20 queries, well inside the API's 60-second request kill.
  - The page receives the response and saves it as a file.
- **State:** none. No job, no table row, no stored file.
- **If it fails:**
  - If the replica errors mid-stream, abort the connection so the browser sees a failed download. Do not end the stream cleanly, because a clean end would make a truncated file look complete.
  - There is no retry. The user clicks again.
  - A 60-second kill hits the same abort.

### 5. Large path: create the export record and enqueue
- **Starts it:** step 3 chose "large".
- **Data moves:**
  1. On the primary, insert a `report_exports` row: `state=queued`, with the user, report, view and a new `id`.
  2. If the unique index rejects the insert, a queued or running export already exists for this user and report. Return that one and enqueue nothing. This may have been started with different filters, and the page shows which.
  3. Otherwise call `enqueue("report_export", {"export_id": id})`. The payload is tiny, far under 64 KB, because the view lives in the table.
  4. Save the returned `job_id` on the row.
  5. Respond 202 with the export record.
- **State:** the `report_exports` row is the single source of truth.
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` (`error="could not queue"`) right away and return 500. The user is not blocked.
  - If the server dies between insert and enqueue, the row stays `queued` with no job. To stop that blocking the user forever, treat any `queued` or `running` row whose `updated_at` is older than 2 hours as orphaned.
    - The longest legitimate life of a job is 3 x 1,800 s plus 360 s of backoff, about 96 minutes.
    - Step 7 updates `updated_at` on every attempt.
    - When step 5 meets such a row, mark it `failed` and carry on with a fresh insert.

### 6. Page shows export status
- **Starts it:** the page loads, or the user has just started an export.
- **Data moves:**
  - The page calls `GET /api/reports/{id}/exports/latest`. It runs the `report.view` check and returns the caller's most recent export for this report: `state`, `attempt`, the view it was built with, and `finished_at`.
  - While the state is `queued` or `running`, poll every 5 seconds. Stop on `done` or `failed`.
  - A user who comes back later calls the same endpoint on page load and sees the current state.
  - For `done`, show a Download button (see step 10).
  - For `failed`, show the reason and let the user start a new export.
  - If the file is more than 7 days old (see step 10), show it as expired rather than offering a dead link.
- **State:** read from the **primary**. This table is not report data, and the replica's lag could hide a row created a moment ago.
- **If it fails:** a failed poll keeps the last known state on screen and tries again on the next tick. It never changes the export.

### 7. Worker starts an attempt
- **Starts it:** the queue runs the `report_export` handler `handler(ctx, {"export_id": ...})`. This happens at first delivery and again at each retry. Delivery is at least once, so the handler may also run again after a success.
- **Data moves:**
  1. Load the row.
  2. **If `state=done`:** do not rebuild the file. Go straight to the email part of step 9 only if `ready_email_sent_at` is empty. Otherwise return.
  3. Check that the user still has `report.view`. If not, set `failed` with `error="permission revoked"` and return normally. Returning means no retry and no email.
  4. If the row has an `upload_id` from an earlier attempt, call `abort_multipart(upload_id)` and ignore errors.
  5. Set `state=running`, `attempt=ctx.attempt`, `upload_id=NULL` and bump `updated_at`.
- **State:** the table row.
- **If it fails:** if the handler raises, the queue retries after 60 s, then 300 s. Each attempt starts from the beginning, because the queue keeps no progress.

### 8. Worker builds the file in a stream
- **Starts it:** step 7 finished.
- **Data moves:**
  1. Call `start_multipart("exports", key)` with `key = reports/{report_id}/{export_id}.csv`. Save the returned `upload_id` on the row.
  2. Run the shared CSV writer. It writes the header row, then pages the **replica** by `row_id` with `LIMIT 5000`, using the saved filters and column order.
  3. Append each page's CSV text to a buffer.
  4. When the buffer reaches 8 MB (above the 5 MB minimum part size), call `upload_part(upload_id, n, bytes)`, keep the etag, and empty the buffer.
  5. At the end, upload whatever remains as the last part. It may be under 5 MB, and a header-only file is one small part.
  - **Memory:** only one page (about 2 MB at the current row size) and one buffer (8 MB) exist at a time, so about 10 to 30 MB against the 512 MB limit. The whole report is never held. A 900 MB file is about 113 parts, far below the 10,000-part limit.
  - **Time:** the 2-million-row report is about 400 replica queries and 113 uploads. Before launch, measure this on the largest report in staging. It should finish in well under 10 minutes. The attempt timeout is 1,800 s, and a timeout means a full restart, so a slow export cannot recover through retries.
- **State:** the parts sit invisibly in the bucket. Nothing is readable at `key` yet. The row holds `upload_id`.
- **If it fails:**
  - On any exception (replica error, upload error), call `abort_multipart(upload_id)` and re-raise so the queue retries. Retries use a new multipart upload.
  - If the worker is killed or times out, it cannot abort. The next attempt aborts the saved `upload_id` in step 7. Anything still left is discarded by the bucket's 24-hour rule for incomplete uploads.
  - A half-written file is never visible, because no object exists until step 9.

### 9. Worker publishes the file and emails the user
- **Starts it:** step 8 uploaded the last part.
- **Data moves, in this order:**
  1. `complete_multipart(upload_id, etags)` makes the object visible at `key`.
  2. Update the row: `state=done`, `object_key`, `finished_at`, `upload_id=NULL`.
  3. `signed_url("exports", key, 86400)` creates a link valid for 24 hours.
  4. `send_email(user_id, "report_export_ready", {report name, url, expires_at})`.
  5. Set `ready_email_sent_at`.
- **State:** the row is `done`, with the object in the bucket. The bucket's existing 7-day lifecycle rule deletes the file later. No cleanup job is built.
- **If it fails:**
  - Failure before step 2: the attempt raises and is retried. The key is deterministic, so a repeated `complete_multipart` replaces the same object. That is harmless.
  - Failure after step 2, for example the email call raising: the attempt raises and is retried. Step 7 then sees `done` with no `ready_email_sent_at`, and only re-sends the email. It never rebuilds the file.
  - A crash between sending the email and setting `ready_email_sent_at` can send the email twice. I accept that to avoid losing the email.

### 10. User downloads later from the page (my addition)
- **Starts it:** the user clicks Download on a `done` export.
- **Data moves:**
  - `GET /api/reports/{id}/exports/{export_id}/download` checks that the caller owns the export and still has `report.view`.
  - It returns a redirect to a fresh `signed_url` with a short TTL, for example 5 minutes.
  - This lets someone who missed the 24-hour email link still get the file for the 7 days it exists.
  - If you would rather keep the email link as the only route, drop this step. The page would then show only the state.
- **State:** none new.
- **If it fails:** the endpoint returns 403 if permission is lost. It returns 410 "expired" once the file is older than 7 days, and the page then shows it as expired.

### 11. Final failure
- **Starts it:** the third attempt fails (raise, timeout or worker death). The queue calls `on_final_failure(ctx, payload, error)` once. It is registered as `@job("report_export", on_final_failure=...)`.
- **Data moves:**
  1. Load the row. If `state=done`, do nothing. This guards a late duplicate delivery of an export that already succeeded.
  2. Otherwise abort the saved `upload_id` and ignore errors.
  3. Set `state=failed` with a short `error`.
  4. `send_email(user_id, "report_export_failed", {report name, link to the report page})`.
- **State:** the row is `failed`. That also frees the partial unique index, so the user can start a new export. The page shows "failed" via step 6.
- **If it fails:** the hook runs only once. If the email fails, log it. The state is already `failed`, so the page still tells the user. Any leftover parts are discarded after 24 hours.

---

## Why the requirements hold

| Requirement | Where it is met |
|---|---|
| Same contents as the page | Step 2 reuses the rows API's parser, and the CSV writer is shared (steps 4 and 8). |
| `report.view` check | Steps 2, 6, 7 and 10. |
| Replica only | Steps 4 and 8. The primary holds only `report_exports`. |
| Small exports store nothing | Step 4. |
| One large export at a time | The partial unique index (step 5). |
| 512 MB memory | Step 8 never holds more than a page plus an 8 MB buffer. |
| Attempt timeout | Measured in staging before launch (step 8). |
| No half-written download | Multipart upload is invisible until `complete_multipart`, and the link is emailed only after `done` (step 9). |
| Retries and failure email | Steps 7 and 11. |

## Open questions

1. **Nightly rebuild.** If the rebuild rewrites `report_rows` while a long export is paging, the file could mix old and new data. I don't know how the rebuild works (swap or in place). Please confirm before relying on exports that run near the rebuild time.
2. **Different filters while one is running.** The second click returns the first export, even if the filters changed. The page must show which filters that export used, so the user does not assume it matches the screen.
3. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas when the file is opened in a spreadsheet. Decide whether to prefix them with `'` in the CSV writer. This changes the data, so I have left it as a decision.
4. **Row history.** `report_exports` rows are kept forever. This is small, but you said not to build cleanup, so I left it.
5. **Replica limits.** Check whether the replica has a statement timeout or query-cost cap that would affect 5,000-row pages under heavy filters.
