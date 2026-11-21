# Plan: Download CSV on the reports page

## What this is

Today the reports page loads rows through `GET /api/reports/{id}/rows`, 500 at a time, from the read replica. The server stores nothing about the user's current view.

The new **Download CSV** button calls one endpoint. That endpoint reads `reports.row_count` and picks a path.

- **10,000 rows or fewer:** the response is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the endpoint saves an export record, queues one background job and returns at once. The job streams the report into the `exports` bucket as a multipart upload. The file becomes visible only when every part is uploaded. Then the job emails a 24-hour link.

The page polls the export record to show queued, running, done or failed.

## Terms

- **view:** the filters and column order in the page URL. The click must send them, because the server does not keep them.
- **rows API:** the existing `GET /api/reports/{id}/rows`. It checks `report.view`, parses filters and columns, reads `report_rows` from the read replica and pages by `row_id` (keyset, never OFFSET).
- **`reports.row_count`:** the unfiltered total rows in a report. It changes only at the nightly rebuild. A filtered view has at most this many rows.
- **queue (`jobs.py`):** `enqueue(name, payload)` returns a `job_id`. Delivery is at least once. A job gets 3 attempts, with waits of 60 s then 300 s. An attempt is killed after 1,800 s. The queue keeps no progress between attempts. Workers have 512 MB.
- **`ctx`:** the `JobContext` the queue passes to the handler. It holds `job_id` and `attempt` (1 to 3).
- **`on_final_failure(ctx, payload, error)`:** a function we register with the job. The queue calls it once, after the last attempt fails.
- **storage helpers (`storage.py`):** `start_multipart(bucket, key)` returns an `upload_id`. `upload_part(upload_id, n, data)` returns an etag. `complete_multipart(upload_id, etags)` makes the object visible at its key. `abort_multipart(upload_id)` discards the parts. `signed_url(bucket, key, ttl_seconds)` returns a link (ttl at most 86,400). Their errors are not documented, so any exception from them counts as a failure of the step that called them.
- **`send_email(user_id, template, params)`:** the existing email function. Any exception counts as a failed send.
- **export record:** one row in the new `report_exports` table (see "Build and rollout").
- **`fail_export(export_id, reason)`:** our helper, defined in step 9. It marks an export failed and emails the user.

## How it runs

### Step 1. The user clicks Download CSV

- **Starts it:** a click. The page sends `POST /api/reports/{report_id}/export` with `filters` and `cols` copied from the URL.
- **What it does:**
  1. Check `report.view` on the report's workspace, as the rows API does. Return 403 if missing.
  2. Validate `filters` and `cols` with the rows API's own parser. Return 400 if invalid.
  3. Read `reports.row_count` from the replica. If it is 10,000 or fewer, go to step 2. Otherwise go to step 3. A heavily filtered view of a large report still takes the large path. That is slower than needed but correct.
- **What the page gets:** `200` with `text/csv` (small path, the page saves the body as a file) or `202` with JSON (large path, the page starts showing status).
- **State kept:** none.
- **If it fails:** 403 or 400 as above. If the replica is down, return 503 and write nothing. The user can click again.

### Step 2. Small path

- **Starts it:** step 1 chose the small path.
- **What it does:** page through `report_rows` on the replica by keyset, 500 rows per query, with the view's filters. Keep the selected columns in URL order. Build the whole CSV in memory with a header row first. Reply `200` with `Content-Type: text/csv` and `Content-Disposition: attachment`. Under 10,000 rows is a few MB and about 20 queries, well inside the API's 60 s limit.
- **State kept:** none. No record, no job, no object.
- **If it fails:**
  - Any error before the last row: return 500 with no file. The file is sent only when complete, so a cut-off file never looks whole. The user can click again.
  - More than 10,000 rows arrive (the count was stale): stop, drop the buffer and continue at step 3 in the same request.

### Step 3. Large path: record the export and queue the job

- **Starts it:** step 1 chose the large path, or step 2 hit a stale count.
- **What it does**, on the primary database:
  1. Look for the user's active (`queued` or `running`) export of this report. If one exists and is not an orphan, reply `202` with it and `existing: true`. Do not start a second job. This holds during a retry wait too.
  2. Otherwise insert a record: `status='queued'`, `job_id` empty, the validated view, a new `export_id`, and `object_key = report-exports/{export_id}.csv`. Use `INSERT ... ON CONFLICT DO NOTHING RETURNING *` against the unique index. If it returns no row, another click won a race. Select the active export and reply `202` with `existing: true`.
  3. For a new record (or an orphan), call `enqueue("report_csv_export", {"export_id": ...})`. The payload is only the id. Save the returned `job_id` on the record, then reply `202` with `{export_id, status, filters, cols, existing}`.
- **Orphan:** a `queued` record with no `job_id` that is older than 2 minutes. Its request died before the enqueue was saved. The next click re-runs sub-step 3 for it. A record that has a `job_id` is never an orphan. If the first job did start, a second job is harmless because the job is safe to run twice (steps 5 and 7).
- **One at a time:** the rule is per user and report, not per view. A click with different filters returns the earlier export, and the page says an earlier export is still running.
- **State kept:** the record in `report_exports`.
- **If it fails:**
  - Select or insert fails: return 500. Nothing is queued.
  - Enqueue raises: mark the record `failed` with a short error, return 500, send no email. `failed` is not active, so the user can click again.
  - Saving `job_id` fails after a good enqueue: return 500 and leave the record. The job will set `job_id` itself in step 5.

### Step 4. The page shows the export's state

- **Starts it:** the report page loads (including when the user returns later), and after a `202` reply.
- **What it does:** call `GET /api/reports/{report_id}/exports/latest`. It checks `report.view`, then returns the user's newest export for this report: `export_id`, `status`, `filters`, `cols`, `created_at`, `error`, and `expires_at` when done. While the status is `queued` or `running`, poll every 5 seconds. Stop on `done` or `failed`.
  - **queued, running:** show progress. This includes retry waits.
  - **done:** while `expires_at` is in the future, show a Download button. It calls `GET /api/reports/{report_id}/exports/{export_id}/download`. That endpoint checks `report.view`, checks the export belongs to the user and is `done`, and returns `{url}` from `signed_url("exports", object_key, remaining time until expires_at)`. After `expires_at`, show "link expired, export again".
  - **failed:** show the short `error`.
- **State kept:** none (read only).
- **If it fails:** if a poll fails, keep the last state and try again on the next tick. If the download call fails, show an error. The export is not affected.

### Step 5. A job attempt starts

- **Starts it:** the queue calls `handler(ctx, {"export_id"})`, for attempt 1, 2 or 3.
- **What it does:**
  1. Load the record and check `status`.
     - `failed`: return without raising. Nothing more happens.
     - `done`: go straight to step 7 item 2 (the email, only if `notified_at` is empty), then return. This covers duplicate delivery and a retry after a failed email.
     - `queued` or `running`: carry on.
  2. Re-check that the user still has `report.view`. If not, call `fail_export(export_id, "access removed")` and return without raising. Retrying cannot help, so this skips the retries.
  3. If the record holds an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore errors.
  4. Set `status='running'`, `attempt=ctx.attempt`, `job_id=ctx.job_id`, `upload_id` empty.
  5. Call `start_multipart("exports", object_key)` and save the new `upload_id`.
- **State kept:** `status`, `attempt`, `job_id`, `upload_id` on the record.
- **If it fails:** any exception is an ordinary attempt failure (step 8).

### Step 6. Stream the report into the bucket

- **Starts it:** step 5 finished.
- **What it does:**
  1. Read `report_rows` from the **read replica only**, in keyset pages of 5,000 rows, with the same filters and columns as the page. Count the rows.
  2. Write the header, then each row, as UTF-8 CSV with standard quoting.
  3. Add rows to one in-memory buffer. At 8 MB, call `upload_part(upload_id, n, buffer)`, keep the etag and empty the buffer. The last part may be smaller.
  4. After the last page, upload the final part and call `complete_multipart(upload_id, etags)`.
- **Memory:** one 8 MB buffer, one page and the etag list. A 900 MB report makes about 113 parts. That is far below the 10,000 part limit, and every part except the last is over the 5 MB minimum.
- **Time:** 2 million rows is about 400 pages, and the attempt must finish inside 1,800 s. Measure this on the largest report before launch.
- **State kept:** the buffer, etags and row count live in memory only. The object is invisible until `complete_multipart` succeeds, so a half-written file is never downloadable.
- **If it fails:** any exception, such as a replica error, is an ordinary attempt failure (step 8). The next attempt starts from the first row.

### Step 7. Mark done and email the link

- **Starts it:** `complete_multipart` returned, or step 5 found the record `done`.
- **What it does:**
  1. `UPDATE report_exports SET status='done', upload_id=NULL, row_count_written=<count>, expires_at=COALESCE(expires_at, now + 24h) WHERE export_id=? AND status='running'`. If no row matches, another delivery already finished it. Reload the record and go on only if it is `done`.
  2. If `notified_at` is empty, call `signed_url("exports", object_key, time left until expires_at)`, then `send_email(user_id, "export_ready", {report name, url, expires_at})`, then set `notified_at`. The emailed link and the page's link both end at `expires_at`.
- **State kept:** `status`, `row_count_written`, `expires_at`, `notified_at`.
- **If it fails:**
  - Email raises: the record stays `done`. Re-raise. The retry sees `done` with `notified_at` empty and only sends the email. The file is not rebuilt.
  - Crash after the email but before `notified_at` is saved: the user gets a second email with the same expiry. This is accepted.
  - A duplicate delivery that finds `done` with `notified_at` set returns at once and sends nothing.
  - Every attempt fails on the email: step 9 leaves the record `done` and logs the error. The page still offers the download.

### Step 8. An attempt fails

- **Starts it:** the handler raises, the 1,800 s timeout kills it, or the worker dies.
- **What it does:**
  - If the handler can still run: abort the upload (ignore errors), run `UPDATE ... SET status='queued', error=<last error> WHERE export_id=? AND status='running'`, and re-raise so the queue retries. The `WHERE` leaves a `done` or `failed` record alone.
  - If the process is killed: no code runs. The record stays `running` with its old `upload_id`. The next attempt (step 5) aborts that upload. The bucket also discards uploads left over after 24 hours.
- **Timing:** each retry starts from the beginning. In the worst case three attempts and two waits take about 96 minutes.
- **State kept:** `status`, `error`, `upload_id`.
- **If it fails:** if the abort fails, ignore it.

### Step 9. Failing an export

- **Starts it:** the queue calls `on_final_failure` after attempt 3 fails, or step 5 calls it for removed access. Both call `fail_export(export_id, reason)`.
- **What it does**, in this order:
  1. Load the record and note its `upload_id` and `notified_at`. If it is `done`, stop and change nothing.
  2. `UPDATE report_exports SET status='failed', error=<short reason>, upload_id=NULL WHERE export_id=? AND status IN ('queued','running')`.
  3. If there was an `upload_id`, call `abort_multipart` and ignore errors.
  4. If `notified_at` is empty, call `send_email(user_id, "export_failed", {report name})` and set `notified_at`.
- **State kept:** `status='failed'`, `error`, `notified_at`. The user can now start a new export.
- **If it fails:** if the email fails, log it. The page still shows `failed`, which is the reliable signal. The queue may not retry `on_final_failure`, so this step does not rely on it.

### After the export

Once `expires_at` passes, the link stops working and the page shows "link expired". The bucket deletes the object 7 days after creation. There is no cleanup job. Records stay as history, and the page reads only the newest per user and report.

## Build and rollout

### Build first

- **Table `report_exports`**, on the primary database. It holds export metadata only, so the rule against reading report data from the primary does not apply.

  | Column | Meaning |
  |---|---|
  | `export_id` | Primary key. |
  | `report_id`, `user_id` | Who asked, and for which report. |
  | `filters`, `cols` | The validated view, as text. |
  | `status` | `queued`, `running`, `done` or `failed`. |
  | `job_id` | Empty until enqueue is saved. The job also sets it. |
  | `attempt` | Last attempt that started. |
  | `upload_id` | Current multipart upload, or empty. |
  | `object_key` | `report-exports/{export_id}.csv`. Fixed per export. |
  | `row_count_written` | Rows in the finished file. |
  | `expires_at` | When the download link stops working. |
  | `notified_at` | When the success or failure email was sent. |
  | `error` | Short, user-safe reason. |
  | `created_at`, `updated_at` | Timestamps. |

- **Unique partial index** on `(user_id, report_id)` where `status IN ('queued','running')`. The database enforces one active large export per user and report.
- **Two email templates**, `export_ready` and `export_failed`.
- The migration only adds things, so it is safe to deploy first.

### Tests

- **Size boundary:** 10,000 rows takes the small path, 10,001 takes the large path, and a stale count falls back to the large path.
- **Permissions:** 403 without `report.view` on the click, the status call and the download call. Access removed mid-job fails the export once, with one email and no retries.
- **One at a time:** two simultaneous clicks make one record and one job. The second click returns the first export, including during a retry wait.
- **Orphan:** a `queued` record with no `job_id` older than 2 minutes is re-queued on the next click, and a double enqueue sends one email.
- **Memory and parts:** a 2-million-row run stays under 512 MB, and every part except the last is at least 5 MB.
- **No half-written file:** kill a worker mid-upload and confirm nothing is downloadable at the key.
- **Retries:** fail attempt 1 and confirm attempt 2 succeeds with one email. Fail all three and confirm one failure email and a `failed` page.
- **Email failure:** make the success email raise once. Confirm the record stays `done`, the retry only sends the email, and the page never shows `queued` after `done`.
- **Duplicate delivery:** run the same job twice after success. The second run does nothing and sends no email.

## Open questions

- **Throughput is unmeasured.** The 1,800 s limit is the main risk for the 2-million-row report. Measure it. If it is too slow, save `last_row_id`, etags and the part number on the record and resume on retry. That adds a lot of state, so it is left out for now.
- **Data may change during a long export.** Pages are separate queries, so the nightly rebuild could mix old and new rows in one file. Mention it in the release notes or schedule around the rebuild.
- **Concurrent attempts.** It is not known whether the queue can run two attempts of one job at once. This plan assumes it cannot. If it does, both write identical content to the same key, and the worst case is a wasted retry.
- **Helper errors.** `storage.py` and `send_email` do not document what they raise. Any exception is treated as failure.
- **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in a spreadsheet. Prefixing them with a single quote would fix it but changes the data. This needs a decision.
- **Email copy.** `export_ready` and `export_failed` need wording and registration with `send_email`.
