# Plan: CSV export for the reports page

## How the pieces fit

A click on **Download CSV** sends the page's current URL state to a new endpoint. The endpoint picks one of two paths by `reports.row_count`.

- **Small report (10,000 rows or fewer):** the response is the CSV, streamed from the read replica. Nothing is stored.
- **Large report (more than 10,000 rows):** a row in a new `report_exports` table records the request and a background job is queued. The job streams rows from the replica into a multipart upload in the `exports` bucket. When it finishes, it emails a 24-hour signed link. The page shows the export's state by reading `report_exports`.

Existing facts this plan relies on (from the three files):

- Rows are read with keyset paging (`row_id > after ORDER BY row_id`) from the read replica only.
- API requests are killed after 60 seconds.
- Jobs run in 512 MB workers, with at most 3 attempts. Backoff is 60 s then 300 s, and each attempt is killed after 1800 s. The queue keeps no progress between attempts.
- Delivery is at least once.
- Nothing is visible in object storage until `complete_multipart` succeeds.
- The `exports` bucket deletes objects after 7 days and discards unfinished multipart uploads after 24 hours.

## Step 0. Prerequisites (build once)

**Starts:** before any endpoint work.

**Data and state:**

1. **A new table `report_exports` on the primary database.** This is application state, not report data, so the primary is allowed. Columns:
   - `export_id` (uuid, primary key)
   - `user_id`
   - `report_id`
   - `filters` and `cols` (the raw values from the click)
   - `state` (`queued`, `running`, `done` or `failed`)
   - `job_id`
   - `object_key`
   - `error_message`
   - `emailed_at`
   - `created_at` and `updated_at`
2. **A partial unique index** on `(user_id, report_id) WHERE state IN ('queued','running')`. This is what enforces "one at a time". The database enforces it, so two simultaneous clicks cannot both win.
3. **A shared generator `iter_report_rows(report_id, filters, cols)`.**
   - It yields CSV-ready rows in the requested column order.
   - It pages by `row_id` from the read replica, with page size about 2,000.
   - It uses the same filter parsing and column validation as `GET /api/reports/{id}/rows`.
   - Both the small path and the job use it, so the two paths cannot disagree about contents.
4. **A shared CSV writer.** It writes a header row, quotes fields correctly, and neutralises cells that start with `=`, `+`, `-` or `@` so spreadsheets do not run them as formulas. Use one writer everywhere.
5. **Two email templates for `send_email`:** `export_ready` (params: report name, link, expiry) and `export_failed` (params: report name). Check whether these exist; this plan assumes they do not.

**Failure:** none at runtime. These are build-time items.

## Step 1. The click: `POST /api/reports/{report_id}/export`

**Starts:** the user clicks Download CSV. The page sends its current URL query (`filters`, `cols`) with the request. The server holds no view state, so the page must send it.

**Data:** report id, filters and cols from the page, plus the caller's identity.

**Actions, in order:**

1. Check `report.view` on the report's workspace, as the rows API does. Return 403 if the caller lacks it.
2. Validate filters and cols with the same parser as the rows API. Return 400 if they are invalid. This keeps a bad request from becoming a job that fails three times.
3. Read `reports.row_count`.
   - 10,000 or fewer: go to Step 2.
   - More than 10,000: go to Step 3.

**State kept:** none yet.

**Failure:** 403 or 400 as above. A database error returns 500 and the user can click again.

**Notes:**

- `row_count` is the unfiltered total and is refreshed nightly. A filtered view of a big report therefore still takes the large path, and a report that grew after the rebuild can be slightly over 10,000 rows on the small path. Both are acceptable, and the 60-second limit has plenty of margin at about 10,000 rows. This follows the brief's rule.
- I assume `reports.row_count` is not report data, so reading it from the primary is allowed. If your rule says the replica only, read it from the replica; the nightly refresh makes staleness irrelevant.

## Step 2. Small path: stream the CSV in the response

**Starts:** Step 1, with `row_count <= 10,000`.

**Data moves:** replica rows to the CSV writer to the HTTP response, a page at a time.

**Actions:**

1. Respond 200 with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
2. Write the header row, then each row from `iter_report_rows`.
3. Nothing is stored and no job is queued.

**State kept:** none.

**Failure:**

- If the replica errors before the first byte is sent, return 500.
- If it errors mid-stream, abort the connection so the browser shows a failed download. Never end the response normally with partial data. The user clicks again.
- The 60-second kill applies. About 10,000 rows is a few seconds, so it is not a concern.

## Step 3. Large path: create or return the export

**Starts:** Step 1, with `row_count > 10,000`.

**Data moves:** one new row in `report_exports`, then a job payload of `{"export_id": ...}`. The payload is tiny and well under 64 KB. Filters and cols live in the table row, not the payload.

**Actions:**

1. Try to insert a `report_exports` row with `state='queued'`, `user_id`, `report_id`, `filters`, `cols` and a generated `object_key`.
   - Use `exports/{report_id}/{export_id}.csv` for the key. The key is unique per export and fixed across retries.
2. If the unique index rejects the insert, an export for this user and report is already queued or running. Select that row and return it with 200. No second job is started.
3. Otherwise call `enqueue("report_export", {"export_id": ...})`, then save the returned `job_id` on the row.
4. Return 202 with the export's id and state (`queued`). The response is immediate.

**State kept:** the `report_exports` row on the primary. This row is the single source of truth for the page.

**Failure:**

- **`enqueue` raises.** Mark the row `failed` with a message and return 503, so the user is not locked out. The user can click again.
- **The API process dies between the insert and the enqueue.** The row would stay `queued` with no job and block the user. To handle this, in the "already active" branch of step 2, if the row has no `job_id` and is more than 2 minutes old, mark it `failed` and repeat the insert once.

**Notes:**

- If the user clicks again with different filters while an export of the same report is active, they get the existing export, with its original filters. The brief says one per user per report, so this is by design. The page should show the filters of the running export so this is not confusing.

## Step 4. The job: `report_export` (runs on a worker)

**Starts:** the queue calls `handler(ctx, {"export_id"})`, once per attempt. Attempt 1 runs at once, and attempts 2 and 3 run after 60 s and 300 s. The handler is registered with `@job("report_export", on_final_failure=...)`, which is Step 6.

**Data moves:** replica to a bounded in-memory buffer to object-storage parts. At most one buffer of about 8 MB plus one page of rows is in memory at a time. Never collect a whole report in a list.

**Actions:**

1. **Load the row** by `export_id`.
   - If `state='done'`, skip to the email step (Step 5, part b). This handles at-least-once delivery and a retry after a failure that came after the file was complete.
   - If the row is `failed`, return without doing anything.
2. **Re-check `report.view`** for `user_id`. If access was removed, raise an error. This is rare and costs only a quick failure.
3. **Mark the row `running`** and set `updated_at`.
4. **Start the upload:** `upload_id = start_multipart("exports", object_key)`. Keep `upload_id` only in the handler's local variables. Each attempt starts a fresh one.
5. **Stream the file:**
   - Start the buffer with the header row.
   - Pull rows from `iter_report_rows`, which pages by `row_id` from the replica.
   - Append each row to the buffer.
   - Whenever the buffer reaches 8 MB, call `upload_part(upload_id, n, bytes)`, keep the returned etag, increment `n`, and empty the buffer.
   - At the end, upload the remainder as the last part. The last part may be under 5 MB.
   - The largest report is about 900 MB, so that is about 113 parts, well under the 10,000-part limit. Each part must be at least 5 MB (`MIN_PART_BYTES`), so the 8 MB threshold is safe.
6. **Check a soft deadline** between pages. If 25 minutes have passed, call `abort_multipart` and raise an error. This stops the attempt cleanly before the queue's 30-minute kill.
7. **Finish:** `complete_multipart(upload_id, etags)`. Only now does the object appear at `object_key`.

**State kept:**

- The row's state moves to `running`.
- The multipart parts live in storage and are invisible until completion.
- The `upload_id` and etags are in memory only.

**Failure:**

- **Any exception** (replica error, storage error, soft deadline): call `abort_multipart(upload_id)` if one was started, then re-raise.
  - If `ctx.attempt < 3`, first set the row back to `queued` so the page shows that a retry is waiting.
  - The queue retries after the backoff and starts again from the beginning, as the queue guarantees nothing else.
- **Worker killed or attempt timed out:** the handler cannot clean up, so the multipart upload is orphaned. The bucket discards it after 24 hours. The next attempt uses a new `upload_id`, so there is no conflict. The row stays `running`, which still counts as active.
- **A half-written file is never downloadable.** The key holds nothing until `complete_multipart`, and that call is the last step of building the file.
- **Duplicate run of a finished job:** the check in step 1 returns early. If two attempts overlap, both write the same key and the last `complete_multipart` wins. Both produce a complete file, never a partial one.
- **Timeout risk:** 2 million rows is about 1,000 page queries plus about 113 part uploads, run one after another. Before release, measure a 2-million-row export in staging. If it takes more than about 15 minutes, change the design before shipping. Retries cannot fix a job that is too slow, because every attempt does the same work.

**Note:** the scan is not a snapshot. If the nightly rebuild rewrites rows while a job runs, the file can mix old and new data. This risk is accepted, as the rebuild runs overnight and exports are mostly daytime.

## Step 5. Finish: mark done, then email

**Starts:** `complete_multipart` returned in Step 4. This step also runs at the start of a retry when the row is already `done` (see Step 4, part 1).

**Data moves:** the state change in the database, then the link in an email.

**Actions:**

a. Update the row with `UPDATE ... SET state='done' WHERE export_id=? AND state<>'failed'`.

b. If `emailed_at` is empty:

   - `url = signed_url("exports", object_key, 86400)`. 86,400 s is the 24-hour maximum.
   - `send_email(user_id, "export_ready", {report name, url, expiry})`.
   - Set `emailed_at`.
   - The link is generated at send time and never stored. It is valid for 24 hours from the email.

**State kept:** `state='done'` and `emailed_at` on the row. The file stays in the bucket for 7 days and the lifecycle rule deletes it. No cleanup job is built.

**Failure:**

- **`send_email` raises:** the attempt fails and is retried. The retry sees `done` with no `emailed_at` and only resends the email. It does not rebuild the file.
- **Crash after sending but before `emailed_at` is set:** the user may get a second email. That is acceptable under at-least-once delivery.
- **If all three attempts fail at the email step,** the file exists but the user has no link. Step 6 handles this case.

## Step 6. Final failure: `on_final_failure(ctx, payload, error)`

**Starts:** the queue calls it once, after attempt 3 has failed.

**Data moves:** the error text goes to the row and the failure email.

**Actions:**

1. Load the row. If `state='done'`, the file was built but the email kept failing.
   - Leave the state as `done`.
   - Log the error for engineers.
   - Do not send a failure email, as the export itself succeeded.
2. Otherwise run `UPDATE ... SET state='failed', error_message=? WHERE state IN ('queued','running')`.
3. If that update changed a row, call `send_email(user_id, "export_failed", {report name})`.

**State kept:** `state='failed'` with the error message. A failed row leaves the partial unique index, so the user can start a new export.

**Failure:** if the failure email also fails, the row is still `failed`, so the page is correct, and the error is logged. There is no further retry here.

## Step 7. Status on the page

**Starts:** the report page loads, and then repeatedly while an export is active.

**Data moves:** `GET /api/reports/{report_id}/export` returns the caller's most recent export for that report: `export_id`, `state`, `created_at`, the filters it was started with, and `error_message` if failed.

**Actions:**

1. On page load, call the endpoint. This also covers a user coming back to the report later. If an export exists, show `queued`, `running`, `done` or `failed` next to the button.
2. While the state is `queued` or `running`, poll every 5 seconds, and stop when it reaches `done` or `failed`. Also stop when the user leaves the page.
3. While an export is active, the button reuses the existing export (Step 3) instead of starting another.
4. Apply the `report.view` check to this endpoint too, and return only the caller's own exports.

**State kept:** none on the client. The `report_exports` row is the truth.

**Failure:** if a poll fails, keep the last known state and retry on the next tick.

**Notes:**

- The row shows `done` even after the 24-hour link expires or the file is deleted after 7 days. The brief asks for a state only, not a download button. If users need to re-download from the page, add an endpoint that checks `report.view` and returns a fresh `signed_url` while the object still exists. This is out of scope here.
- Only the latest export per user and report is shown.

## Step 8. Checks before release

1. **Contents match:** for the same view, the small-path CSV equals the large-path CSV. Cover column order, filters, the header row, and values containing commas, quotes and newlines.
2. **Dedupe:** two simultaneous clicks produce one row and one job.
3. **Retries:** force a failure on attempt 1 and confirm that:
   - the multipart upload is aborted;
   - the row goes back to `queued`;
   - attempt 2 succeeds;
   - one email is sent.
4. **Final failure:** force all three attempts to fail and confirm the page shows `failed`, the user gets one failure email, and no object exists at the key.
5. **Duplicate delivery:** run the handler twice for the same export and confirm there is one valid file. The second run sends no email, because `emailed_at` is already set.
6. **Memory:** run a 2-million-row export on a 512 MB worker and watch peak memory.
7. **Duration:** the same run must finish well inside the 1800 s limit. Aim for under 15 minutes (see the timeout note in Step 4).
8. **Replica only:** confirm no report row query reaches the primary.

## Open questions for the reviewer

- Are the `export_ready` and `export_failed` email templates available, or do they need to be created?
- Is a stale `row_count` (refreshed nightly) acceptable for choosing the path?
- Does the page need a download button for a finished export, given the link only lives 24 hours?
