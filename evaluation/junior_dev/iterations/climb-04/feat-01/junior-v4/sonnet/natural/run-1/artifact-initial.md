# Plan: Download CSV on the reports page

## Summary

The Download CSV button calls one endpoint, which uses `reports.row_count` to pick a path.

- **10,000 rows or fewer:** the response is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the endpoint records an export row, queues one background job and returns straight away. The job streams the report from the read replica into the `exports` bucket as a multipart upload. It makes the file visible only when every part is uploaded, then emails a 24-hour link.

State for large exports lives in one new table, `report_exports`. The page polls it to show queued, running, done or failed.

## Vocabulary

- **view:** the filters and column order from the page URL. The server stores nothing about it today, so the click must send it.
- **rows API:** the existing `GET /api/reports/{id}/rows`. It checks `report.view`, reads `report_rows` from the read replica and pages by `row_id` (keyset).
- **queue:** `jobs.py`. `enqueue(name, payload)` has at-least-once delivery. A job gets at most 3 attempts, with waits of 60 s and 300 s between them. An attempt is killed after 1800 s, and the queue keeps no progress between attempts. Workers have 512 MB.
- **export row:** one row in the new `report_exports` table (step 0).

## Step 0. Prerequisites (built before anything else)

**New table `report_exports`.** It holds export metadata only, not report data, so it lives on the primary database. The rule against reading report data from the primary does not apply to it.

| Column | Meaning |
|---|---|
| `export_id` | Primary key. |
| `report_id`, `user_id` | Who asked, for which report. |
| `filters`, `cols` | The validated view, stored as text. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id` | Nullable. Set after enqueue. |
| `attempt` | Last attempt number that started. |
| `upload_id` | Nullable. Current multipart upload. |
| `object_key` | `report-exports/{export_id}.csv`. Fixed per export, not per attempt. |
| `row_count_written` | Rows written by the last completed upload. |
| `expires_at` | Nullable. When the emailed link stops working. |
| `notified_at` | Nullable. When the success or failure email was sent. |
| `error` | Short, user-safe reason. |
| `created_at`, `updated_at` | Timestamps. |

**Unique partial index** on `(user_id, report_id)` where `status IN ('queued','running')`. The database enforces "one active large export per user per report", so two simultaneous clicks cannot both win.

**Two email templates**, `export_ready` and `export_failed`, for the existing `send_email(user_id, template, params)`.

**Failure:** none at runtime. The migration is additive and safe to deploy first.

## Step 1. The user clicks Download CSV

**Starts it:** a click. The page sends `POST /api/reports/{report_id}/export` with the current `filters` and `cols` copied from the page URL.

**Data moves:** the request carries filters and column order. The endpoint does the following, in order:

1. Check `report.view` on the report's workspace. Return 403 otherwise, using the same check as the rows API.
2. Validate `filters` and `cols` with the rows API's own parser, so the export accepts exactly what the page accepts. Return 400 for anything invalid.
3. Read `reports.row_count`. Read it from the replica, the same as other report data. The value changes only at the nightly rebuild, so replica lag does not matter.
4. If `row_count <= 10,000`, go to step 2. Otherwise go to step 3.

**State:** none written yet.

**Failure:** 403 or 400 as above. If the replica is unreachable, return 503 and write nothing. The button shows an error and the user can click again.

## Step 2. Small path (10,000 rows or fewer)

**Starts it:** step 1 chose the small path.

**Data moves:**

1. Page through `report_rows` on the read replica by keyset (`row_id > after ORDER BY row_id`), 500 rows per query, using the view's filters. Never use OFFSET.
2. Keep only the selected columns, in the URL's order.
3. Build the whole CSV in memory, header row first. At most about 5 MB fits easily in memory, and about 20 queries fit well inside the API's 60 s limit.
4. Reply `200` with `Content-Type: text/csv` and `Content-Disposition: attachment`. The page saves the response as a file.

**State:** none. No export row, no job, no stored object.

**Failure:**

- **Any error before the last row is read:** return 500 with no file. The CSV is fully built before sending, so a truncated file can never look complete. The user can click again.
- **`row_count` is stale and more than 20,000 rows come back:** discard the buffer and continue at step 3. This is a safeguard I added. The count is rewritten nightly, so it should be rare.

## Step 3. Large path: record the export (or return the existing one)

**Starts it:** step 1 chose the large path (or the stale-count fallback in step 2).

**Data moves:** one insert into `report_exports`, in a single statement:

- `status='queued'`, `job_id=NULL`, the validated view, a new `export_id`, and `object_key` derived from it.
- Use `INSERT ... ON CONFLICT DO NOTHING RETURNING *` against the partial unique index.
- If the insert returns no row, the user already has an active export of this report. Select it and return it with `existing: true`. No second job starts.

Reply `202` with `{export_id, status, filters, cols, existing}`. The page shows the status (step 5). If `existing` is true, the page also says that an earlier export (with its own filters) is still in progress.

The one-at-a-time rule is per user and report, not per view. A second click with different filters therefore returns the first export rather than starting another.

**State:** the new row in `report_exports`.

**Failure:** if the insert fails, return 500. Nothing is queued and the user can retry.

## Step 4. Queue the job

**Starts it:** step 3 created a new row. It does not run for an `existing` result.

**Data moves:** `enqueue("report_csv_export", {"export_id": ...})`. The payload holds only the id, well under 64 KB, because the full view is in the row. The returned `job_id` is saved on the row.

**State:** `report_exports.job_id`.

**Failure:**

- **Enqueue raises:** mark the row `failed` with a short error (the user sees a failed export and can click again) and return 500. Do not email.
- **The API process dies between the insert and the enqueue:** the row stays `queued` with `job_id NULL` and would block the user. To recover, step 3 checks the existing row first. If it is `queued`, has no `job_id` and is older than 2 minutes, it runs step 4 again for that same `export_id`. The job is idempotent (step 8), so a double enqueue is harmless.

## Step 5. The page shows the export's state

**Starts it:** the report page loads, and the user comes back later. It also starts after step 3 returns.

**Data moves:** the page calls `GET /api/reports/{report_id}/exports/latest`. That call checks `report.view`, then returns the current user's newest export row for this report: `status`, `filters`, `cols`, `created_at`, `error`, and `expires_at` when done. While the state is `queued` or `running`, the page polls every 5 seconds and stops on `done` or `failed`.

How each state shows:

- **queued, running:** show it. (Between retries the row goes back to `queued`, so the page keeps showing progress.)
- **done:** show it. While `expires_at` is in the future, offer a download. The endpoint checks permission again and returns `signed_url(..., ttl_seconds=remaining time)`. After `expires_at`, show "link expired, export again". The file itself is deleted by the bucket after 7 days.
- **failed:** show it with the short `error`.

**State:** read only.

**Failure:** if a poll fails, the page keeps the last known state and retries on the next tick. The export is unaffected.

## Step 6. A job attempt starts

**Starts it:** the queue calls the handler `handler(ctx, {"export_id"})`, for attempt 1, 2 or 3.

**Data moves:**

1. Load the row.
2. If `status` is `done` or `failed`, handle the duplicate delivery as described in step 8 and return.
3. Re-check that the user still has `report.view` on the workspace. If not, fail the export with "access removed" (step 10).
4. If the row has an `upload_id` from an earlier attempt, call `abort_multipart(upload_id)`. Ignore errors, because the 24-hour lifecycle rule discards stragglers anyway.
5. Set `status='running'`, `attempt=ctx.attempt`, `upload_id=NULL`.
6. Call `start_multipart("exports", object_key)` and save the returned `upload_id` on the row.

**State:** `status`, `attempt`, `upload_id`.

**Failure:** any exception here is an ordinary attempt failure (step 9).

## Step 7. Stream the report into the bucket

**Starts it:** step 6 finished.

**Data moves:**

1. Read `report_rows` from the **read replica** only. Use keyset pages of 5,000 rows (the job reads the database directly, so the API's 500-row limit does not apply). Use the same filters and the same column selection as the page, in the same order.
2. Write the CSV header first, then each row. Use standard CSV quoting and UTF-8.
3. Append encoded rows to one in-memory buffer. When it reaches 8 MB, call `upload_part(upload_id, n, buffer)`, keep the returned etag in a list, and empty the buffer. The last part may be smaller.
4. After the last page, upload the final part, then call `complete_multipart(upload_id, etags)`.

**Memory:** at most one 8 MB buffer, one 5,000-row page and a list of etags. A 900 MB report makes about 113 parts, far below `MAX_PARTS` (10,000), and every part but the last meets the 5 MB minimum.

**Time:** about 400 pages of 5,000 rows for 2 million rows. This must finish inside the 1,800 s attempt timeout. Measure it on the largest report before launch. The handler also checks the clock and, past 1,700 s, aborts the upload and raises, so cleanup happens before the queue kills it. If measurement shows the job cannot finish in time, the fallback is to save `last_row_id`, the etags and the part number on the row and resume from there on a retry. I left that out because it adds a lot of state. Because the queue timeout kills the process, no cleanup code is guaranteed to run. That is why step 6 aborts the previous upload.

**State:** only the in-memory buffer and etag list. The object is **invisible** until `complete_multipart` succeeds. A half-written file therefore never exists as a downloadable object.

**Failure:** see step 9.

## Step 8. Mark done and email the link

**Starts it:** `complete_multipart` returned.

**Data moves:**

1. `UPDATE report_exports SET status='done', upload_id=NULL, row_count_written=... WHERE export_id=? AND status='running'`.
2. If `notified_at` is null, call `signed_url("exports", object_key, 86400)`. Send `send_email(user_id, "export_ready", {report name, url, expires_at})`. Then set `expires_at = now + 24h` and `notified_at = now`.

Because the key is fixed per export and `complete_multipart` replaces what is there, a repeated delivery of a succeeded job rewrites identical content. It does not create a second object.

**Duplicate delivery:** if the handler runs again and finds `status='done'` with `notified_at` set, it returns immediately. No second email goes out. If it finds `done` with `notified_at` null (a crash before the email), it only does the email step.

**State:** `status`, `notified_at`, `expires_at`.

**Failure:**

- **The email call raises:** the attempt fails and is retried. The retry finds `done` with `notified_at` null and goes straight to the email, without rebuilding the file.
- **Crash after the email but before `notified_at` is written:** the user gets a second email with a fresh link. I accept this, because a duplicate is better than none.
- **All attempts fail on the email step:** the final-failure handler (step 10) sees `done`, leaves it as `done` and logs the error. The file is fine and the page still offers the download.

## Step 9. An attempt fails

**Starts it:** the handler raises, the 1,800 s timeout kills it, or the worker dies.

**Data moves (when the handler can still run):** catch the exception and call `abort_multipart(upload_id)`. Then set `status='queued'` with the last error recorded, and re-raise so the queue schedules a retry. The page keeps showing a pending state.

**Retry timing:** the queue waits 60 s before attempt 2 and 300 s before attempt 3. In the worst case the three attempts can take about 96 minutes (3 x 30 min of attempts plus 6 min of waits). Each retry starts from the beginning (step 6). Parts from the failed attempt are aborted or discarded, and the new attempt gets a fresh `upload_id`.

**State:** `status`, `error`, `upload_id` (cleared).

**Failure:** if the abort itself fails, ignore it. The bucket discards incomplete uploads after 24 hours.

## Step 10. The last attempt fails

**Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.

**Data moves:**

1. `UPDATE report_exports SET status='failed', error=<short reason>, upload_id=NULL WHERE export_id=? AND status IN ('queued','running')`. If the row is already `done`, change nothing (see step 8).
2. Abort any open upload.
3. If `notified_at` is null, call `send_email(user_id, "export_failed", {report name})` and set `notified_at`.

Do these in that order, so the page shows failed even if the email fails. The user can then start a new export, because `failed` is no longer active in the unique index.

**State:** `status='failed'`, `error`, `notified_at`.

**Failure:** if the email fails, log it. The page still shows `failed`, which is the user's reliable signal. I could not tell from `jobs.py` whether the queue retries `on_final_failure`, so this step must not depend on it.

## Step 11. Download link expiry and cleanup

**Starts it:** time passing.

**What happens:**

- At `expires_at` (24 hours after the email), the signed link stops working. No code runs. The page switches to "link expired".
- Seven days after creation, the bucket's existing lifecycle rule deletes the object. There is no cleanup job.
- Rows in `report_exports` stay as a history. They are small, and the page reads only the latest one per user and report.

**Failure:** none to handle.

## Tests to write

- **Size boundary:** 10,000 rows takes the small path, 10,001 takes the large path, and the stale-count fallback switches paths.
- **Permissions:** 403 without `report.view` on the click, the status endpoint and the download endpoint.
- **One at a time:** two simultaneous clicks produce one row and one job. The second click returns the first export.
- **Orphaned `queued` row:** one with no `job_id` gets re-enqueued, and a double enqueue sends only one email.
- **Memory and parts:** a 2-million-row run stays under 512 MB, and every part except the last is at least 5 MB.
- **No half-written file:** kill a worker mid-upload and confirm nothing is downloadable at the key.
- **Retries:** fail attempt 1 and confirm attempt 2 succeeds with one email. Fail all three and confirm one failure email and a `failed` page.
- **Duplicate delivery:** run the same job twice after success. Confirm the second run does nothing and sends no email.

## Risks and open questions

- **Throughput is unmeasured.** The 1,800 s limit is the main risk for the 2-million-row report. Measure it, then decide whether resumable progress is needed.
- **Data changing during a long export.** The nightly rebuild could run while a long export is reading, so the file may mix old and new rows. Say so in the release notes, or schedule around the rebuild.
- **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas when the CSV is opened in a spreadsheet. I suggest prefixing such cells with a single quote, but that changes the data, so it needs your decision.
- **Email templates.** `export_ready` and `export_failed` need copy and registration with `send_email`.
