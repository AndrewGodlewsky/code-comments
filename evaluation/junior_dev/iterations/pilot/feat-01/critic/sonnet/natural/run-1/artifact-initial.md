# Plan: CSV export for the reports page

## Overview

The Download CSV button calls one new endpoint. The server picks one of two paths by `reports.row_count`:

- **Small report (10,000 rows or fewer).** The response to the click is the CSV. No job runs and nothing is stored.
- **Large report (more than 10,000 rows).** The server records an export, queues a background job and returns at once. The job streams the rows into the `exports` bucket and emails a 24-hour link. The page shows the export's state.

The page URL is the only place the current view lives. The server stores nothing about it, so the click must send the page's filters and column order, and the server must copy them into the export record.

### Terms used below

- **Replica**: the read replica. All `report_rows` reads go here and never to the primary.
- **App DB**: the primary application database. It holds the new `report_exports` table, because state must not be read from a replica that may lag.
- **Active export**: an export whose status is `queued` or `running`.

### New state: table `report_exports` (App DB)

| Column | Meaning |
|---|---|
| `id` | UUID, also used in the object key |
| `user_id`, `report_id` | Who asked and for which report |
| `filters`, `cols` | Validated copy of the view at click time |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | Returned by `enqueue`. It is null until the job is queued. |
| `object_key` | `{report_id}/{id}.csv` in the `exports` bucket |
| `rows_written`, `error` | Filled in at the end |
| `notified_at` | Set once the success email has been sent |
| `created_at`, `updated_at`, `finished_at` | Timestamps |

**Unique partial index** on `(user_id, report_id) WHERE status IN ('queued','running')`. The database enforces "one at a time" with it. Application code alone cannot do that safely, because two clicks can race.

## Steps

### 1. The user clicks Download CSV
- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/export` with the current URL's `filters` and `cols`.
- **Data moves:** the browser sends the filters and column order. The page does not send a row count or any decision about which path to take.
- **State:** none yet.
- **If it fails:** the button shows an error and can be clicked again. Nothing has been created yet.

### 2. The server checks permission and validates the view
- **Starts it:** step 1 arriving at the API.
- **Data moves:** the server checks `report.view` on the report's workspace, using the same check as the rows API. It returns 403 if the caller lacks it. It then validates `filters` and `cols` with the same parser the rows API uses, so the export and the page cannot disagree. Unknown columns or bad filters return 400. It reads `reports.row_count`.
- **State:** none written.
- **If it fails:** 403 or 400 and nothing else happens. See open question 1 about where `row_count` is read from.

### 3. The server picks a path
- **Starts it:** step 2 passing.
- **Rule:** `row_count <= 10,000` goes to step 4. `row_count > 10,000` goes to step 5.
- **Note:** `row_count` is the unfiltered total. A heavily filtered view of a big report still takes the large path. That is what was specified and it is correct, only slower than needed.

### 4. Small path: the response is the CSV
- **Starts it:** step 3.
- **Data moves:**
  1. Read rows from the **replica** with the rows API's keyset query (`row_id > after ORDER BY row_id`, never OFFSET) in pages of 500.
  2. Write the header row (columns in URL order), then each row, with the shared CSV writer from step 7.
  3. Keep the result in memory. At 10,000 rows it is about 5 MB (roughly 450 bytes a row). Send it only when it is complete, with `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
- **State:** none. Nothing is stored and no job runs.
- **If it fails:**
  - A replica error returns a 500. The user never receives a partial file, because nothing is sent until the CSV is complete. The user can click again.
  - The work is about 20 queries, well under the 60-second request limit.
  - `row_count` can be stale between nightly rebuilds. If the read passes 10,000 rows, stop, discard the buffer and go to step 5. That protects the API server's memory and the 60-second limit.

### 5. Large path: record the export, or return the existing one
- **Starts it:** step 3.
- **Data moves:**
  1. `INSERT` a `report_exports` row with status `queued`, the validated `filters` and `cols`, and a new `id`.
  2. If the unique index rejects the insert, an export is already active for this user and report. Load that row and return it (step 6) without starting anything. This also covers a double-click or two racing requests.
  3. Call `enqueue("report_export", {"export_id": id})`. The payload is deliberately tiny, far under the 64 KB limit. The filters and columns stay in the row, which is the single source of truth.
  4. Save the returned `job_id` on the row.
- **State:** the App DB row, `queued`.
- **If it fails:**
  - If `enqueue` raises, mark the row `failed` immediately so the slot is freed, and return a 500.
  - If the server dies between the insert and the enqueue, the row stays `queued` with no `job_id`. When a click finds an active row with a null `job_id` older than 2 minutes, it enqueues the job for that row itself.
  - **Dead-slot guard.** The longest legitimate life of a job is 3 attempts x 30 min + 6 min of backoff, about 96 minutes. A click that finds an active row older than 2 hours marks it `failed` and starts a fresh export. This stops a lost job from blocking the user forever.
  - If the existing active export has different filters from this click, the user still gets the existing one. The rule is one per user per report. The page should make that visible.

### 6. The click returns straight away
- **Starts it:** step 5.
- **Data moves:** HTTP 202 with `{export_id, status, created_at}`. For a duplicate click, the existing export is returned with the same shape.
- **State:** none new.
- **If it fails:** the client retries the click. Step 5 is idempotent in effect, because the second request returns the first one's export.

### 7. The worker runs the job (`report_export`, attempts 1 to 3)
- **Starts it:** the queue. If an attempt fails, the queue retries after 60 s and then 300 s. The queue keeps no progress, so every attempt starts from the beginning with the same payload.
- **Data moves, in order:**
  1. **Load and guard.** Read the export row.
     - If it is `done`, skip to step 8c. Delivery is at least once, so duplicate runs happen.
     - If it is `failed`, return.
     - If it is not found, return.
  2. **Mark running.** Set `status='running'`. A retry keeps it `running` through the backoff gap, which is still an active state.
  3. **Recheck permission.** Check that the user still has `report.view`. If not, mark the export `failed` and return, because retrying cannot help. Send no data.
  4. **Start the upload.** Call `start_multipart("exports", object_key)`. Nothing is visible at the key until `complete_multipart`.
  5. **Stream rows.**
     - Read the replica with keyset pagination in pages of about 5,000 rows. This is the job's own query, not the 500-row API cap. It cuts about 4,000 round trips for the largest report to about 400, and the view's filters are applied.
     - Encode each row with the CSV writer and append it to a byte buffer. Row 1 of the first part is the header.
     - When the buffer reaches **8 MB** (above the 5 MB minimum), call `upload_part(upload_id, n, data)`, keep the etag and clear the buffer.
     - Upload the remainder as the last part. The header guarantees at least one part, even for a report with no matching rows.
     - Memory stays at about one buffer plus one page, roughly 15 MB against 512 MB. The 900 MB file is about 113 parts, well under the 10,000-part limit.
  6. **Publish.** Call `complete_multipart(upload_id, etags)`. This is the only moment the file becomes downloadable, so a half-written file cannot be fetched. It replaces any object at the key, so a duplicate run is harmless.
- **CSV writer (shared with step 4).** It uses UTF-8 and RFC 4180 quoting. Any cell starting with `=`, `+`, `-` or `@` gets a leading `'`, to block spreadsheet formula injection.
- **State:** the row is `running`. The upload exists only inside the bucket until step 6 completes it.
- **If it fails:**
  - On any exception, call `abort_multipart(upload_id)` (best effort) and re-raise so the queue retries.
  - If the worker is killed or times out, nothing can clean up. The bucket discards an unfinished multipart upload after 24 hours, so no cleanup job is needed.
  - Each retry starts a new upload for the same key. Unfinished uploads never become visible, so retries cannot leave a bad file.
  - **Time budget.** One attempt must finish within the **1,800 s** timeout, which means at least about 1,100 rows/s for 2 million rows. The attempt has no progress to resume from, so a timeout wastes the whole 30 minutes. See open question 2 for the benchmark that gates shipping.

### 8. Mark the export done and email the link
- **Starts it:** step 7.6 succeeding.
- **Data moves:**
  - **a.** `UPDATE report_exports SET status='done', rows_written=..., finished_at=now() WHERE id=... AND status='running'`. This frees the user's slot.
  - **b.** Build the link with `signed_url("exports", object_key, 86400)`. 86,400 s (24 hours) is the maximum the helper allows and exactly the requirement. Call `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`. Then set `notified_at`.
  - **c.** On a duplicate or retried run where the row is already `done` but `notified_at` is null, do only the email and the `notified_at` update. Nothing is rebuilt.
- **State:** the row moves to `done`, then `notified_at` is set.
- **If it fails:**
  - If `send_email` raises, the attempt fails and the queue retries. The retry hits the guard in step 7.1 and resends only the email.
  - If the last attempt fails at the email step, step 9 must not overwrite a `done` export.
  - If the job crashes between sending and recording `notified_at`, the user may get one duplicate email. That is acceptable.
  - The 24-hour link is valid for 24 hours from the moment the email is built. The file stays in the bucket for 7 days under the existing lifecycle rule, and nothing deletes it sooner.

### 9. Final failure handler (`on_final_failure`)
- **Starts it:** the queue, once, after attempt 3 fails.
- **Data moves:**
  1. Reload the row. If it is `done`, leave it alone. This happens when only the email failed. Log the email error and stop.
  2. Otherwise set `status='failed'`, save a short `error`, and set `finished_at`. This frees the slot, so the user may start a new export.
  3. Call `send_email(user_id, "report_export_failed", {report name})`.
- **State:** the row moves to `failed`.
- **If it fails:**
  - Do the status update first, so the page is correct even if the email fails.
  - Catch and log email errors rather than raising, because the queue calls this handler only once.
  - No bad file can exist, because the object is only created by `complete_multipart`.

### 10. The page shows the export state
- **Starts it:** two triggers. One is the page load for `/reports/{id}`. The other is a 202 response from step 6.
- **Data moves:**
  1. The page calls `GET /api/reports/{report_id}/exports/current`. The server checks `report.view`, then reads the user's most recent export for this report from the **App DB** (never the replica, which may lag).
  2. The response is `{id, status, created_at, finished_at}`. The server leaves out rows older than 7 days, because the bucket has deleted their files.
  3. The page shows a status chip: queued, running, done or failed. While the status is queued or running, it polls every 5 seconds. It stops polling on done or failed. Polling also stops when the tab is hidden.
  4. For `done`, the page offers a Download link. Clicking it calls `GET /api/reports/{report_id}/exports/{id}/download`. The server re-checks `report.view` and returns a redirect to `signed_url(..., 300)`, a short-lived link for use while the file exists (under 7 days). This is a small extension beyond the emailed link. Drop it if you want the email to be the only way to download.
- **State:** none new. The page only reads.
- **If it fails:**
  - If a poll fails, the page keeps its last known state and tries again at the next interval.
  - The user who comes back later sees the same state, because it lives in the App DB and not in the browser.

### 11. Tests and rollout
- **Starts it:** development.
- **Tests:**
  - **Both paths.** Check both sides of the 10,000-row boundary. Check that the small path's header and column order match the URL and that CSV escaping is right.
  - **Parity with the page.** Assert that the export's rows equal the rows API's rows for the same filters.
  - **Replica only.** Assert that no query on the export path touches the primary for report rows.
  - **Concurrency.** Fire two clicks at once and assert one export row and one job.
  - **Failure injection.** Fail the job on attempts 1, 2 and 3, and kill the worker mid-upload. Assert that no object exists at the key before `complete_multipart`, that retries recover, and that attempt 3 failing marks `failed`, sends the failure email and frees the slot.
  - **Duplicate delivery.** Run the handler twice for the same export and assert one email.
  - **Memory.** Run the largest report (about 2 million rows) with the worker memory capped at 512 MB. Peak memory should stay near 15 MB.
- **Rollout:** ship behind a flag, enable it for one workspace, then widen.
- **If it fails:** the flag turns the button off without a redeploy.

## Out of scope
Scheduled exports, formats other than CSV, changes to the table on the page, and any cleanup job for old files.

## Open questions and risks
1. **Where is `reports.row_count` read from?** The brief says report rows must come only from the replica but does not say where the `reports` metadata comes from. Use the same source the page uses. Confirm that this is allowed.
2. **Will the largest report fit in 30 minutes?** No test has run this. Before shipping, run step 7 against the 2-million-row report on the replica and record the time. If it needs more than about 15 minutes (half the limit), tune the page size or the encoding before launch. A timeout wastes the whole 30 minutes, and three timeouts mean a failed export.
3. **Nightly rebuild.** A rebuild during a large export could give a mix of old and new rows. The plan does not prevent this. It is rare, but decide whether to accept it or to ask the owners of the rebuild job.
4. **Emailed link vs permission.** The emailed link works for 24 hours even if the user loses `report.view` in that time. This follows the brief. Decide whether it is acceptable.
5. **One export per report regardless of filters.** A second click with different filters returns the first export. The page should say so, so the user is not surprised.
