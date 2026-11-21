# Plan: Download CSV on the reports page

## Summary

Today the reports page (`/reports/{report_id}`) shows one report as a table. It loads rows 500 at a time from `GET /api/reports/{report_id}/rows`, which first checks the `report.view` permission and then reads from the read replica. The page URL holds the filters and column order, and the server stores nothing about the view.

This plan adds a **Download CSV** button that calls one new endpoint. The endpoint reads the report's total row count and picks a path:

- **Small report (10,000 rows or fewer).** The response to the click is the CSV, streamed back. No job runs and nothing is stored.
- **Large report (more than 10,000 rows).** The endpoint saves an export record and queues a background job. The click returns at once. The job writes the CSV to object storage, then emails the user a download link that works for 24 hours. The page shows the export's state by reading the record.

The split exists because a web request is killed after 60 seconds, and the largest report (about 2 million rows, about 900 MB of CSV) cannot be built inside one request or held in a 512 MB worker.

## Terms

- **Read replica.** A copy of the database used for reading report data. Report data must never be read from the primary database.
- **`report.view`.** The permission to see a report. Export uses the same check as the page.
- **`row_count`.** The report's total, unfiltered row count, stored in `reports.row_count` and rewritten nightly. It picks the path, even when the user has filtered the view.
- **Keyset paging.** Read rows with `row_id > after ORDER BY row_id LIMIT n`. `row_id` is unique and increasing within a report. The next page starts from the last `row_id` seen. Never use OFFSET.
- **Shared row query.** The existing function that turns `filters` and `cols` into a replica query. The rows API, the small path and the job all call it, so the CSV matches the table. If it is currently inline in the rows handler, extract it first.
- **Job queue.** `enqueue(name, payload)` runs `handler(ctx, payload)` on a worker. A job gets 3 attempts in total, waiting 60 s then 300 s between them. An attempt is killed after 1,800 s. The queue keeps no progress between attempts, so each attempt starts from the top. Delivery is at least once, so a finished job may occasionally run again. `on_final_failure(ctx, payload, error)` is called once after the last attempt fails.
- **Multipart upload.** Storage accepts a big file as numbered parts. Each part except the last must be at least 5 MB. Nothing is visible at the key until `complete_multipart` succeeds, so a half-written file can never be downloaded. `abort_multipart` discards the parts.
- **`exports` bucket.** Existing storage bucket. It deletes every object after 7 days and discards multipart uploads not completed within 24 hours.
- **`signed_url(bucket, key, ttl)`.** Returns a download link valid for `ttl` seconds, at most 86,400 (24 hours).
- **`send_email(user_id, template, params)`.** Existing email sender. This plan adds two templates: `report_export_ready` and `report_export_failed`.
- **`report_exports` table.** New table on the primary database. One row per large export. It is the only record of an export's state. The "never read from the primary" rule covers report data, not this bookkeeping.

### The `report_exports` table

| column | meaning |
|---|---|
| `export_id` | UUID made by the endpoint |
| `user_id`, `report_id` | who asked, and for which report |
| `filters`, `cols` | the view, copied from the URL at click time |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | queue job id, null until enqueued |
| `upload_id` | the current multipart upload, so a retry can abort it |
| `file_key` | set once the file is published |
| `error` | short failure reason |
| `created_at`, `updated_at` | timestamps |

- A **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')` allows only one active export per user and report. The database enforces it, so two simultaneous clicks cannot both succeed.
- An index on `(user_id, report_id, created_at DESC)` serves the status read.
- Rows are never deleted. They are tiny, and a cleanup job is out of scope.
- The file key is `exports/{report_id}/{export_id}.csv`. A retry writes to the same key, so orphans cannot pile up.

## How it runs

### 1. The user clicks Download CSV
- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/export?filters=...&cols=...`, copying both values from the page URL (the server does not know the view otherwise).
- **State:** none.
- **If it fails:** the button shows an error and the user clicks again. Nothing was created.

### 2. The server checks permission and picks a path
- **Starts it:** step 1.
- **What it does:** checks `report.view` (403 if missing, before anything else), reads `reports.row_count`, then goes to step 3 if it is 10,000 or fewer, or step 4 if it is more.
- **State:** read only.
- **If it fails:** a missing report returns 404. A database error returns 500 and creates nothing.
- A filtered view of a big report still takes the large path, because the rule is by `row_count`. That is intended.

### 3. Small path: stream the CSV in the response
- **Starts it:** step 2, with 10,000 rows or fewer.
- **What it does:** sends headers `Content-Type: text/csv` and `Content-Disposition: attachment; filename=report-{id}.csv`. Writes the header row in the URL's column order. Then loops over the shared row query with keyset paging, 500 rows per page, writing each page to the response and starting the next from the last `row_id`. A real CSV writer escapes commas, quotes and newlines. Reads come from the read replica only. Memory holds one page.
- **State:** none. No record, no job, no stored file.
- **If it fails:** if a query fails mid-stream, abort the connection instead of ending the response normally, so the browser reports a failed download rather than saving a truncated file. The user clicks again. If a stale `row_count` hides a much larger report, the 60-second request limit kills it and the download fails the same way.

### 4. Large path: create the export, or return the existing one
- **Starts it:** step 2, with more than 10,000 rows.
- **What it does:** makes an `export_id` and inserts a `report_exports` row with status `queued`, the user, the report, `filters` and `cols`. If the insert hits the unique index, an export is already queued or running for this user and report. Do not start another. Return that row with HTTP 200, including its `filters` and `cols` so the page can show which view it is for. This covers double-clicks and second tabs.
  - Recovery for a lost enqueue (see step 5): if the existing row is `queued`, has no `job_id` and is older than 2 minutes, enqueue it again and save the new `job_id`. This is safe because the job tolerates repeats.
- **State:** the new row on the primary database.
- **If it fails:** any other insert error returns 500. No row exists, so nothing is stuck.

### 5. Enqueue the job and answer
- **Starts it:** step 4 created a new row.
- **What it does:** calls `enqueue("build_report_export", {"export_id": ...})`. The payload is only the id, because the job reads the view from the row. Saves the returned `job_id` on the row and returns HTTP 202 with `{export_id, status: "queued"}`. The page then shows "Queued" and starts polling (step 11).
- **State:** `job_id` on the row.
- **If it fails:** if `enqueue` raises, set the row to `failed` (error "could not queue") and return 500. `failed` does not hold the unique slot, so the user can click again. If the process dies between the insert and the enqueue, the row stays `queued` with no `job_id`, and the next click repairs it as described in step 4.

### 6. The job starts an attempt
- **Starts it:** the queue calls `build_report_export(ctx, payload)` for attempt 1, 2 or 3.
- **What it does, in order:**
  1. Load the row by `export_id`.
  2. If `status` is `done` or `failed`, return. This makes duplicate delivery harmless.
  3. Re-check `report.view` for the row's user. If it is gone, run the failure routine (step 10) with reason "permission removed" and return normally so the queue does not retry.
  4. Set `status = 'running'`.
  5. If `file_key` is already set, an earlier attempt built the file and only the email failed. Skip to step 9.
  6. If `upload_id` is set, an earlier attempt left an unfinished upload. Call `abort_multipart(upload_id)`, ignoring errors.
- **State:** `status = running`.
- **If it fails:** an exception, timeout or worker death counts as a failed attempt. The queue retries after 60 s, then 300 s, up to 3 attempts.

### 7. The job builds the file and streams it to storage
- **Starts it:** step 6, when `file_key` is not set.
- **What it does:**
  1. Call `start_multipart("exports", key)` and save the `upload_id` on the row at once.
  2. Start a byte buffer holding the CSV header row, in the saved `cols` order.
  3. Loop over the shared row query with the saved `filters` and `cols`, keyset paging from `after = 0`, 5,000 rows per page. Encode each page with the CSV writer and append it to the buffer. Read from the replica only.
  4. Whenever the buffer reaches 8 MB, call `upload_part(upload_id, n, bytes)` (parts count from 1), keep the etag and empty the buffer.
  5. When rows run out, upload what remains as the last part. It may be under 5 MB. An empty result still uploads the header row.
- **Why it is safe:** memory is one 8 MB buffer plus one page, far under 512 MB. 900 MB at 8 MB per part is about 113 parts, well under the 10,000 limit. About 400 page queries and 113 uploads should fit well inside the 1,800 s timeout (measure it in step 12). Nothing is visible at the key during the build.
- **State:** `upload_id` on the row. Part numbers, etags and the last `row_id` live only in the job's memory.
- **If it fails:** let the exception propagate so the queue retries. The next attempt aborts the old upload (step 6) and restarts from row 1. Restarting is acceptable at this size and avoids storing a resume cursor. If every attempt dies, the bucket discards the unfinished upload after 24 hours.

### 8. The job publishes the file
- **Starts it:** the last part is uploaded.
- **What it does:** calls `complete_multipart(upload_id, etags)`, which makes the object visible at the key, then saves `file_key` on the row.
- **State:** `file_key`.
- **If it fails:** if `complete_multipart` raises, nothing is visible, and the retry rebuilds. If the process dies after completing but before saving `file_key`, the retry rebuilds and overwrites the same key with identical content. The file is always whole.

### 9. The job emails the link and marks the export done
- **Starts it:** step 8, or step 6 finding `file_key` set.
- **What it does:** calls `signed_url("exports", file_key, 86_400)` just before sending, so the 24 hours start at send time. Calls `send_email(user_id, "report_export_ready", {report name, url})`. Then sets `status = 'done'`. Setting `done` last means the page never says "done" for a user with no link.
- **State:** `status = 'done'`.
- **If it fails:** if the email raises, the attempt fails and the retry redoes only this step with a fresh link, without rebuilding. If the process dies after sending but before `done`, the retry sends a second email. That is the one duplicate we accept.

### 10. The last attempt fails
- **Starts it:** the queue calls `on_final_failure` after attempt 3 fails. The "permission removed" case in step 6 calls the same routine.
- **What it does:**
  1. Load the row. If it is `done`, stop.
  2. Set `status = 'failed'` with a short `error`. Do this first, so the row is never left `running`.
  3. Best effort: `abort_multipart(upload_id)` if set.
  4. Send `report_export_failed` (no report data in it). Log and swallow any email error.
- **State:** `status = 'failed'`. This frees the unique slot, so the user can click again for a fresh export.
- **If it fails:** if the routine dies after step 2, the page still shows "failed". Only the email is lost, which we accept.

### 11. The page shows the export's state
- **Starts it:** the page loads, a click returns 200 or 202, or a poll timer fires (every 5 seconds while the state is `queued` or `running`).
- **What it does:** calls `GET /api/reports/{report_id}/export`, which checks `report.view` (403 otherwise) and returns the caller's latest row for this report as `{export_id, status, created_at, filters, cols}`, or `null`. The page shows queued, running, done or failed, and stops polling on `done` or `failed`. On `failed` the button is enabled again. On `done` it shows "Link sent by email". It does not link to the file, because the link lasts 24 hours and the file 7 days.
- **State:** read only. The browser keeps only the poll timer. Because state is in the table, it survives reloads and shows when the user returns later.
- **If it fails:** a failed poll is ignored and retried on the next tick.

## What happens when things fail

| Where | What happens |
|---|---|
| Click request fails (1) | Error shown, click again. Nothing created. |
| No permission / no report (2) | 403 / 404. |
| Stream breaks, small path (3) | Connection aborted, browser shows a failed download. |
| Insert fails, other than conflict (4) | 500, no row. |
| Enqueue fails (5) | Row set to `failed`, 500. Click again. |
| Process dies before enqueue (5) | Row stays `queued` with no `job_id`. Next click after 2 minutes re-enqueues it. |
| Query or upload fails (7) | Attempt fails, queue retries, old upload aborted, rebuild from row 1. |
| Worker dies mid-build (7) | Same retry. Without one, the bucket discards the upload after 24 hours. |
| Publish fails or dies (8) | Retry rebuilds and overwrites the same key. |
| Email fails (9) | Retry skips the build, sends a fresh link. |
| Dies after email, before `done` (9) | Retry sends a second email. |
| All 3 attempts fail (10) | Row `failed`, failure email, upload aborted. |
| Duplicate delivery after `done` (6) | Job returns and does nothing. |

## How to build and verify it

Before building, confirm these assumptions, which the three existing files do not state:

- `report_exports` may live on the primary database. If `reports.row_count` must come from the replica, read it there. It changes only nightly.
- `on_final_failure` is called whenever the last attempt fails, whether by exception, timeout or worker death (as the `jobs.py` docstring says).
- The shared row query exists or can be extracted.

Checks before release:

- **Both paths.** 10,000 rows streams. 10,001 rows takes the job.
- **Size and format.** A 2-million-row run stays under 512 MB. The output equals the table for the same filters and column order, with a header row.
- **One at a time.** Two simultaneous clicks make one row and one job.
- **Failure injection.** Fail `upload_part` on attempt 1 only: the old upload is aborted and the file is complete. Fail every attempt: the page shows "failed", the failure email arrives and no object is downloadable. Fail `send_email` once: the file is not rebuilt.
- **Duplicate delivery.** Rerun a `done` job: it does nothing.
- **Timing.** Measure the largest report's build time. If it exceeds about half of 1,800 s, raise the page or part size, or reconsider resumable uploads.
- **Permission.** A user without `report.view` gets 403 from both endpoints.

Out of scope: scheduled exports, formats other than CSV, changes to the page's table, and any cleanup job.

## Open questions for the owner

- A second click with different filters returns the running export for the first view. This follows "one at a time per report" literally. Confirm that is wanted, or limit by view instead.
- Should the page offer a fresh download link on `done`, after the emailed one expires? That needs one more endpoint and a permission check each time.
