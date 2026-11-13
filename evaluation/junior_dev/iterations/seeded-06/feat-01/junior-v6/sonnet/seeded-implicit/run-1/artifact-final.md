# CSV export plan

Today the reports page (`/reports/{report_id}`) loads rows 500 at a time from `GET /api/reports/{report_id}/rows`. It reads only from the read replica and checks the `report.view` permission. This plan adds a **Download CSV** button. The CSV holds what the user is looking at when they click: the filters and column order from the page URL, plus a header row. A small report is returned directly as the response to the click. A large report is built by a background job, stored in object storage, and its download link is emailed to the user. The page shows the export's state. The split exists because API requests are killed after 60 seconds and workers have only 512 MB of memory. The largest report is about 2 million rows (about 900 MB as CSV).

## Terms

- **Read replica**: the secondary database. Report data must only be read from it, never from the primary.
- **`row_id`**: an increasing id on every row, unique within its report. We page with `row_id > after ORDER BY row_id` (keyset), never OFFSET, so every page is equally fast.
- **`reports.row_count`**: the total, unfiltered row count of a report, rewritten each night. It is the only stored size, so it decides small versus large.
- **View state**: the filters and column order. They live only in the page URL. The server stores nothing about what a user is looking at, so the click must send them.
- **Job queue** (`jobs.py`): runs `@job` handlers on workers. Each worker has 512 MB of memory and runs one attempt at a time. A job is tried 3 times in total, with waits of 60 s then 300 s between attempts. An attempt still running after 30 minutes is killed. The queue keeps no progress between attempts: each attempt starts the handler again from the beginning with the same payload. Delivery is at least once, so a handler may run again after it has succeeded. The payload must be JSON and under 64 KB. `on_final_failure` is called once, after the last attempt fails.
- **`exports` bucket** (`storage.py`): object storage. Objects are deleted 7 days after creation. A multipart upload not completed within 24 hours is discarded.
- **Multipart upload**: a file uploaded in parts. Each part except the last must be at least 5 MB, and there are at most 10,000 parts. Nothing is visible at the key until `complete_multipart` succeeds, and `abort_multipart` discards the parts. Completing replaces any object already at the key.
- **Signed URL**: a download link from `signed_url(bucket, key, ttl_seconds)`. Anyone holding the link can download until it expires. The maximum lifetime is 86,400 s (24 hours).
- **`send_email(user_id, template, params)`**: the existing function that emails a user.
- **`report_exports`**: the new table that keeps the state of each large export.

## Rules

- Export uses the same `report.view` permission check as the page (403 otherwise).
- Rows are read only from the replica, in keyset batches.
- A user can have only one large export of a given report queued or running.
- The job must never hold a whole report in memory and must finish within the 30-minute attempt timeout.
- A half-written file must never be downloadable.
- Old files are deleted by the bucket's existing lifecycle rule. We build no cleanup job.
- Out of scope: scheduled exports, formats other than CSV, changes to the table on the page.

## How it runs

1. **Table.** `report_exports` has columns `id`, `report_id`, `user_id`, `query` (the filters and `cols` copied from the URL), `status` (queued / running / done / failed), `job_id`, `object_key`, `error`, `created_at`, `finished_at`. A unique index on (`user_id`, `report_id`) where status is queued or running enforces one active export per user and report. Only the API (creates it as queued) and the job (running, done, failed) change status.
2. **Click.** The page calls `POST /api/reports/{report_id}/exports` with the current filters and columns. The API checks `report.view` (403 on failure), then reads `reports.row_count` and compares it with 10,000, a constant in the API. The count is unfiltered, so a heavily filtered large report still takes the job path.
3. **Small report (10,000 rows or fewer).** The response is the CSV: header row, then rows read from the replica in batches and streamed out. No record is created, no job runs, nothing is stored. If it fails, the request errors and the user clicks again.
4. **Large report (above 10,000 rows).** The API inserts a `report_exports` row (status queued, with the query) and enqueues a `report_export` job whose payload is only the `export_id`. It returns `202` with `{export_id, status}`. If the insert hits the unique index, an export is already active: the API returns that export with `200` and starts nothing. If enqueue fails, the API marks the row failed and returns 500.
5. **Job, each attempt.** If the export is already done, stop (this covers duplicate delivery). Otherwise set status running and start a multipart upload to the fixed key `{export_id}.csv`. Loop: read a batch from the replica after the last `row_id`, append CSV text to a buffer of about 8 MB, upload each full buffer as a part, then free it. At most one buffer and one batch are in memory. 900 MB is about 110 parts, far below the 10,000-part limit. At the end call `complete_multipart`, set status done and store the key, then email the user with `send_email(user_id, "report_export_ready", {link})`, where link is `signed_url("exports", key, 86400)`. The link is valid for 24 hours from the email. The file lives 7 days until the bucket rule deletes it.
6. **Page status.** On load, and after a click, the page asks `GET /api/reports/{report_id}/exports/latest` for the current user's newest export of this report (same permission check, own exports only). This is how the page learns the `export_id` after a reload. While it is queued or running the page polls every 5 seconds. It shows queued, running, done or failed.
7. **Duplicates.** "Duplicate" means the same user and the same report, whatever the filters. A second click while one is queued or running returns that export (step 4). A new export is allowed once the earlier one is done or failed.

## When things fail

| Where | What happens |
|---|---|
| Small path | Request errors; no state to clean up. |
| Enqueue fails (step 4) | The API marks the row failed and returns 500. |
| Job attempt fails (exception, timeout, dead worker) | The queue retries after 60 s, then 300 s. Each retry restarts from the first row, reuses the same export record and key, and starts a new upload. Status stays running during retries. The failing attempt aborts its upload; if the worker died, the bucket discards the stale upload after 24 hours. |
| Half-written file | Never downloadable, because nothing is visible at the key until `complete_multipart`. |
| Last attempt fails | The queue calls `on_final_failure` once. It sets status failed, stores the error, and emails the user that the export failed. The page then shows failed. |
| Job runs again after success | Step 5 sees done and stops, so no second file or email. |
| Email fails after done | The attempt raises and is retried, but the retry stops at done, so no email is sent. The page still shows done. |

## Rollout

Ship the table and API first, then the job, then the button.

## Open questions

- Can 2 million rows be built within the 30-minute attempt timeout? It needs measuring on the largest report; the batch size may need tuning.
- Anyone who gets the emailed link can download the file for 24 hours. Is that acceptable?
- After the email, the page shows done but has no way to get a fresh link. Should it?
