# CSV export for the reports page: implementation plan

## Summary

A **Download CSV** button on `/reports/{report_id}` exports the rows the user is looking at: the filters and column order from the page URL, plus a header row. The click takes one of two paths, chosen by `reports.row_count`:

- **Small (10,000 rows or fewer):** the API builds the CSV and returns it in the same response. No job runs and nothing is stored.
- **Large (over 10,000 rows):** the API records an export, queues a background job, and returns at once. The job writes the CSV to the `exports` bucket in parts, marks the export `done`, and emails the user a link that works for 24 hours. The page shows the export's state until it is done or has failed.

The only new server state is one `report_exports` table that tracks large exports. The view itself (filters and columns) stays in the URL.

## Terms used in this plan

- **Read replica:** a copy of the primary database that serves reads. Report rows must come from it, never from the primary.
- **Keyset paging:** fetching the next page as `WHERE row_id > last_row_id ORDER BY row_id LIMIT n`. It stays fast on large reports, unlike OFFSET.
- **Multipart upload:** object storage accepts one file as numbered parts. Nothing is visible at the final key until the parts are joined. Every part except the last must be at least 5 MB.
- **Attempt:** one run of a job handler. The queue runs a job at most 3 times, waiting 60 s and then 300 s between attempts. Each attempt starts from the beginning and keeps no progress.
- **Attempt timeout:** 30 minutes. An attempt still running at that point is killed.

## Plan

### 1. Add the export table

- **Starts:** the deploy that includes the migration. It runs before any other step ships.
- **Data:** creates table `report_exports` with `id`, `user_id`, `report_id`, `filters` (query string), `cols`, `status` (`queued`, `running`, `done`, `failed`), `attempt`, `job_id`, `upload_id`, `file_key`, `error_summary`, `created_at`, `started_at`, `completed_at`, `email_sent_at`.
- **State:** the primary database. This is job state, not report data, so writing it to the primary is allowed.
- **Index:** a partial unique index on `(user_id, report_id)` where `status` is `queued` or `running`. It enforces one active large export per user and report, even when two clicks arrive at the same moment. This assumes a database with partial indexes (PostgreSQL has them). Otherwise use a lock row.
- **On failure:** the migration fails and the deploy stops. Nothing else has started.

### 2. Add the button and status panel to the page

- **Starts:** the user clicks **Download CSV**.
- **Data:** the button reads `filters` and `cols` from the page URL and sends `POST /api/reports/{report_id}/exports` with that same query string. No row data is sent.
- **Response handling:**
  - `200` with `Content-Type: text/csv`: the browser saves the body as a file.
  - `202` with JSON `{export_id, status}`: the page shows the export panel (step 10) and starts polling.
  - `400`, `403`, `404`, `503`: show a message and re-enable the button. Retrying is safe, because step 5 returns the existing export instead of creating a duplicate.
- **State:** nothing stored in the browser beyond what is on screen.
- **Table on the page:** unchanged.

### 3. Check permission, validate, and choose the path (API)

- **Starts:** `POST /api/reports/{report_id}/exports`.
- **Steps, in order:**
  1. Check `report.view` on the report's workspace. Return 403 otherwise. This is the same check the page uses.
  2. Parse `filters` and `cols` with the same parser the page uses. Reject unknown column names and over-long values with 400. Validating column names here keeps them out of SQL.
  3. Read `reports.row_count` from the read replica. Return 404 if the report does not exist.
  4. If `row_count` is 10,000 or less, go to step 4. Otherwise go to step 5.
- **Data moved:** the query string and one number.
- **State:** nothing written.
- **On failure:** 400, 403 or 404 goes back to the browser. Nothing is stored.
- **Note:** `row_count` counts unfiltered rows, as the brief specifies. A filter that leaves 3 rows still takes the large path if the report has more than 10,000 rows (see open decision 6).

### 4. Small path: build the CSV in the response

- **Starts:** step 3 chose the small path.
- **Data:** keyset pages from `report_rows` on the read replica, 500 rows per query, with the filters applied and rows in `row_id` order. The header row uses the `cols` names in the order given. Each row is written with Python's `csv` module, which handles quoting and escaping.
- **Buffering:** build the whole CSV in memory first. 10,000 rows is about 4.5 MB. Then send it with a `Content-Length` header and `Content-Disposition: attachment` with a filename built from the report name and date. Do not stream it. A stream cut off partway would save a truncated file that looks complete. Buffering turns any failure into an error response.
- **State:** none.
- **On failure:** a replica error, or a request killed at the 60-second API limit, returns an error. The user sees a message and can click again. Step 13 measures the 10,000-row case against the limit.

### 5. Large path: record the export and queue the job

- **Starts:** step 3 chose the large path.
- **Steps:**
  1. Look for an active export for `(user_id, report_id)`, meaning status `queued` or `running`. If one exists, return it with `202` and start nothing new. If the active export is `queued` with no `job_id` and was created more than 5 minutes ago, it is stranded (the process died between the insert and the enqueue). Re-run substep 3 for it, then return it. This recovers without a cleanup job.
  2. Otherwise insert a row with status `queued`, `filters` and `cols`. If the insert hits the unique index because another click won the race, read the winning row and return it with `202`.
  3. Enqueue job `csv_export` with payload `{"export_id": ...}` only. The filters are read from the row, which keeps the payload far below the 64 KB limit. Save the returned `job_id` on the row.
  4. Return `202` with `{export_id, status: "queued"}`.
- **Data moved:** one row written to `report_exports`.
- **On failure:** if the enqueue call raises, set the row to `failed` with `error_summary` "could not start", return `503`, and send no email. The user is watching the request. The next click creates a new export.

### 6. Start of each job attempt

- **Starts:** the queue runs the handler `csv_export(ctx, payload)` on a worker. `ctx.attempt` is 1, 2 or 3.
- **Steps:**
  1. Load the row by `export_id`. If it is missing, log it and return normally.
  2. If the status is `failed`, return normally. This is a duplicate delivery.
  3. If the status is `done`, skip to step 9 (email only).
  4. Otherwise run a conditional update: set status `running`, `attempt = ctx.attempt`, `started_at = now`, only where status is `queued` or `running`.
  5. Re-check `report.view` for the user. If access is gone, set status `failed` with "no access to this report", send the failure email (step 11), and return normally. Do not retry, because the condition will not change.
  6. Go to step 7.
- **Data:** the export row only.
- **State:** `status`, `attempt`, `started_at`.
- **On failure:** a database error in this step raises, and the queue retries the attempt.
- **Note:** the queue has no hook between attempts, so during the 60 s and 300 s waits the status still reads `running`. The page shows the attempt number, such as "attempt 2 of 3", to keep this accurate.

### 7. Write the file in parts

- **Starts:** step 6 passed.
- **Steps:**
  1. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it. Ignore errors, which mean the upload is already gone or complete.
  2. Call `start_multipart(bucket="exports", key="report-{report_id}/export-{export_id}.csv")`. The key contains the export ID, not the attempt number, so every attempt writes to the same key. Save `upload_id` on the row before uploading any part.
  3. Put the header row into an in-memory buffer.
  4. Loop: read the next 5,000 rows from the replica by keyset (`row_id > last`, with filters). Format them as CSV lines and append them to the buffer. When the buffer reaches 16 MB, call `upload_part(upload_id, part_number, buffer)`, keep the returned etag with its part number, and clear the buffer. Stop when a page returns fewer than 5,000 rows.
  5. Upload what remains in the buffer as the final part. It may be under 5 MB, because only non-final parts must be that large.
- **Data moved:** replica rows, then CSV text in worker memory, then bucket parts. No local disk is used.
- **Memory:** one 16 MB part buffer plus one page of about 2 MB. The worker has 512 MB, so the design target is under 200 MB. Two million rows make about 60 parts, far under the 10,000-part limit.
- **Replica use:** each page is a separate short query. No transaction is held open on the replica for the whole run.
- **Timing:** the attempt limit is 1,800 seconds. Two million rows at about 450 bytes each is about 900 MB, so the job must average at least 1,111 rows per second just to fit. Target 15 minutes, about 2,200 rows per second. Retries start from zero, so a job that is too slow fails all three attempts. Benchmark this before the job is accepted (step 13).
- **State:** `upload_id` on the row. The parts sit in the bucket until the upload is completed or aborted.
- **On failure:**
  - Exception (database or upload error): make a best-effort `abort_multipart` call in an exception handler, then raise. The queue retries from step 6.
  - Timeout or worker death: no handler code runs. The unfinished upload stays until substep 1 of the next attempt aborts it, or until the bucket rule discards it after 24 hours.
  - Throughout, nothing is visible at the final key, so a half-written file cannot be downloaded.

### 8. Finish the file

- **Starts:** the last part is uploaded.
- **Steps:**
  1. Confirm the report data was not rebuilt during the run (open decision 2). If it was, raise, so the retry reads the new data.
  2. Call `complete_multipart(upload_id, etags)`. This joins the parts and makes the object visible at its key.
  3. Set status `done`, `file_key`, `completed_at = now`, and clear `upload_id`.
- **State:** the object in the bucket, and the row set to `done`.
- **On failure:**
  - Completion fails: the object is not visible. The attempt raises. The retry aborts the upload (step 7, substep 1) and starts over.
  - Completion succeeds but the row update fails: the object is visible, but the row still says `running`. The attempt raises. The retry rebuilds the file and completes it to the same key, which replaces the object with the same content, then marks the row `done`. Each export writes only its own key.

### 9. Email the download link

- **Starts:** the row is `done`. This happens at the end of step 8, or on a retry that finds `done` in step 6.
- **Steps:**
  1. If `email_sent_at` is set, stop.
  2. Create the link: `signed_url(bucket="exports", key=file_key, ttl_seconds=86400)`.
  3. Call `send_email(user_id, "csv_export_ready", {report_id, export_id, download_url, expires_at})`. The template does not exist yet (open decision 9).
  4. Set `email_sent_at = now`.
- **Data:** the signed URL goes into the email only. It is not stored, because the page generates a fresh link (step 10).
- **On failure:** `send_email` raises, so the attempt fails. The retry does not rebuild the file. It reaches step 6, sees `done`, and sends the email again. If every attempt fails to send, the final-failure hook (step 11) leaves the status as `done` (open decision 3).

### 10. Show the export state on the page

- **Starts:** the page loads. Then it polls every 5 seconds while the latest export is `queued` or `running`.
- **Endpoint:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export for this report: `status`, `attempt`, `created_at`, `completed_at` and `expires_at`. It checks `report.view`. When the export is `done` and not expired, it includes a download URL: `/api/reports/{report_id}/exports/{export_id}/download`.
- **Displayed states:**
  - `queued`: "Waiting to start."
  - `running`: "Building your CSV (attempt N of 3)."
  - `done`: "Download CSV," with "Available until {expires_at}."
  - `done` and expired: "This file has expired. Start a new export."
  - `failed`: "The export failed," with a button to start a new export.
- **Expiry:** the bucket deletes each object 7 days after creation. The page computes `expires_at` as `completed_at + 7 days` instead of waiting for a 404.
- **Download endpoint:** `GET /api/reports/{report_id}/exports/{export_id}/download` checks `report.view`, checks that the status is `done` and the file is not expired, and redirects to `signed_url(..., ttl_seconds = min(86400, seconds until expiry))`.
- **State:** none new. Everything comes from the row.
- **On failure:** a failed poll keeps the last state on screen and tries again later. Polling stops at `done` or `failed`. If the object has been deleted, the redirect fails and the page shows the expired message.

### 11. Final failure

- **Starts:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.
- **Steps:**
  1. Load the row. If it is `done`, log the error and stop. The file exists, so the page still offers it (open decision 3).
  2. If it is `failed`, stop. This is a duplicate call.
  3. Otherwise set status `failed`, `completed_at = now`, and `error_summary` to short, user-safe text such as "The export could not be built after 3 attempts." Put the raw error in logs, not in the row.
  4. If `upload_id` is set, abort that upload. Ignore errors.
  5. Call `send_email(user_id, "csv_export_failed", {report_id, export_id})`.
- **State:** status `failed`. The unique index covers only `queued` and `running`, so the user can start a new export at once.
- **Timing:** the worst case is three 30-minute attempts plus the 60 s and 300 s waits, about 96 minutes, before this hook runs and the failure email goes out.
- **On failure:** if the email send fails, log it. The page still shows `failed`.

### 12. Lifecycle, retention and cleanup

- **Starts:** nothing. This step confirms existing rules.
- **Steps:** no new job is built. The bucket's 7-day rule deletes finished files. Unfinished uploads are discarded after 24 hours. A failed attempt leaves at most one unfinished upload, which step 7 (substep 1) or the 24-hour rule removes.
- **Table rows:** `report_exports` rows are not deleted in this plan. One row per large click is small, but the table grows without limit (open decision 8).

### 13. Tests and rollout

- **Tests (all must pass before rollout):**
  - CSV: header order follows `cols`. Commas, quotes and newlines in values are escaped. Zero matching rows still produce a header.
  - Path choice: `row_count` of 10,000 takes the small path. 10,001 takes the large path.
  - Concurrency: two simultaneous large clicks create one row.
  - Stranded row: a `queued` row with no `job_id` is re-enqueued on the next click.
  - Storage: before `complete_multipart`, the key does not exist. After an injected failure in a part upload, no object exists at the key.
  - Retries: kill an attempt partway. The next attempt aborts the old upload and completes.
  - Duplicate delivery: run the handler twice on a `done` export. Only one email is sent.
  - Email failure after `done`: the retry sends only the email, and the status stays `done`.
  - Access revoked: the job marks the export `failed` and does not retry.
  - Benchmark: 2,000,000 rows on a production-sized dataset. The job finishes in under 15 minutes with peak memory under 200 MB.
  - Small-path benchmark: 10,000 rows return well inside the 60-second API limit.
- **Rollout order:** (1) migration; (2) workers with the `csv_export` handler, because the API enqueues to it; (3) API endpoints; (4) button and panel. The button ships last, so no user sees it before the back end works.
- **Feature flag:** optional. If used, it gates the button.

## Open decisions

1. **The one-active-export rule ignores filters.** The brief limits exports per user and report. A second click with different filters returns the first export, which has the first export's filters. Either show the export's filters in the panel, or add filters to the rule, which then allows several exports per report.
2. **A nightly rebuild during a run.** The job pages by `row_id` over a run that may last 30 minutes. If the rebuild rewrites rows, the file could skip or duplicate rows. Confirm whether `row_id` stays stable across rebuilds. If it does not, add a report data version (for example, a `rebuilt_at` value), read it at the start, and compare it before completion (step 8, substep 1). Alternatively, avoid running large exports during the rebuild window.
3. **Email failure after the file is built.** Proposed: keep the status `done` so the page still offers the file, and alert the operations team. Alternative: a fallback email through another channel.
4. **If the benchmark misses the 15-minute target.** Options: (a) upload parts in parallel; (b) read several `row_id` ranges in parallel; (c) save progress on the row (last `row_id`, `upload_id`, and the list of parts with etags) so a retry resumes instead of starting over. Options (a) and (b) make each attempt faster. Option (c) is the only one that makes a retry cheaper, and it needs the 24-hour window for unfinished uploads to be longer than the retry gap.
5. **Status during retry waits.** The queue has no hook between attempts, so the status reads `running` during the waits. Add a retry hook to the queue if the page should show `queued` during waits.
6. **The threshold counts unfiltered rows.** This follows the brief. Consider counting filtered rows if users dislike waiting for a job when their filtered result is small.
7. **CSV formula injection and encoding.** Cells that start with `=`, `+`, `-` or `@` run as formulas in spreadsheet apps. Decide whether to prefix such cells with an apostrophe. Also decide whether to write a UTF-8 byte-order mark so Excel reads non-ASCII text correctly.
8. **Row retention.** Decide whether `report_exports` rows are kept forever, or whether they are removed after some period.
9. **Email templates.** `csv_export_ready` and `csv_export_failed` must be created. The parameters in steps 9 and 11 are proposals.