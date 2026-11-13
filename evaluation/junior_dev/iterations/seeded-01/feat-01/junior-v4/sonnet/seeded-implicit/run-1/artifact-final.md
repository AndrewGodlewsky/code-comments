# CSV export plan

A **Download CSV** button on the reports page. A small report comes back as the click's response. A large report is built by a background job, saved to object storage, and emailed to the user as a link. The page shows the state of large exports.

How the page works today: `/reports/{report_id}` calls `GET /api/reports/{report_id}/rows?filters=...&cols=...&after={row_id}&limit=500`. The API checks the `report.view` permission and reads the `report_rows` table on the read replica only, never the primary. It pages by `row_id` (keyset, never OFFSET). Filters and column order live only in the page URL. API requests are killed after 60 seconds.

## Terms

- **Read replica**: a copy of the database used for report reads. It can lag slightly behind the primary.
- **Job queue** (`jobs.py`): runs a handler on a worker with 512 MB of memory. It tries a job at most 3 times, waits 60 s then 300 s between attempts, and kills an attempt after 30 minutes. Each attempt restarts the handler from the beginning with the same payload. Delivery is at least once, so a handler can occasionally run again after it succeeded. After the last attempt fails, the queue calls the job's `on_final_failure(ctx, payload, error)` once.
- **Multipart upload** (`storage.py`): a file is uploaded in parts of at least 5 MB (up to 10,000 parts). Nothing is visible at the key until `complete_multipart` is called. The bucket discards an upload not completed within 24 hours, and deletes every object 7 days after creation.
- **Export record**: one row in `report_exports`. It is the only source of truth for an export's status.
- **Large report**: `reports.row_count` is above 10,000. This is the unfiltered total and is the only test, so a filtered export of a large report still uses the job.

The `report_exports` table has these columns: `id`, `report_id`, `user_id`, `filters`, `cols` (copied from the page URL at click time), `status` (`queued`, `running`, `done`, `failed`), `object_key`, `created_at`, `finished_at`. A unique index on (`user_id`, `report_id`) where `status` is `queued` or `running` allows only one active export per user per report. Records are never deleted.

## How it runs

1. **Click.** The page calls `POST /api/reports/{report_id}/exports` with the current filters and columns. The API returns 403 without `report.view`, then reads `reports.row_count` and picks a path. The small path returns `200` with `Content-Type: text/csv` and a download header. The large path returns `202` with a JSON export record. The page branches on the status code.
   - Failure: a bad request or 403 is shown by the page. Nothing is stored.

2. **Small path (10,000 rows or fewer).** The response is the CSV: a header row, then rows read from the replica 500 at a time by `row_id`, streamed out. No record, no job, nothing stored.
   - Failure: if the stream breaks, the download is broken and the user clicks again.

3. **Large path: create the record.** The API inserts a `queued` record. If the unique index rejects the insert, the user already has an active export of this report, so the API returns that existing record. Otherwise it enqueues a `report_export` job whose payload is only the `export_id`, and returns the new record straight away.
   - Failure: if enqueue fails, mark the record `failed` and return an error, so it does not block later clicks.

4. **Page shows status.** When the page loads, and every 5 seconds while the status is `queued` or `running`, it calls `GET /api/reports/{report_id}/exports/latest`. This returns the caller's newest export of that report (same permission check). The record exists before the POST returns, and an active export is always the newest, so after a click the first poll shows the new export. The page shows queued, running, done or failed; a retry also shows `running`. When `done`, the page says the download link was emailed. It has no download button. Coming back later works the same way, because the record is in the database.
   - Failure: a failed poll is ignored and retried on the next tick.

5. **Job attempt starts.** The job loads the record by `export_id`. If it is missing, or its status is not `queued` or `running` (for example `done` from a repeated delivery, or `failed`), the job stops. Otherwise it sets `running` and starts a multipart upload to the `exports` bucket at `exports/{export_id}.csv`.
   - Failure: any error here fails the attempt (see step 8).

6. **Job builds the file.** It reads rows from the replica by `row_id`, 5,000 at a time, using the stored filters and columns, and writes the header first. It holds one buffer of about 8 MB and uploads it as a part whenever it fills, so memory stays small however large the report is. The largest report (about 900 MB) needs about 110 parts. The read is a keyset scan, not a snapshot, like the page.
   - Failure: any error fails the attempt (see step 8).

7. **Job finishes.** It calls `complete_multipart`, which is the first moment the file is visible. It then builds `signed_url(exports, key, 86400)`, a link that anyone holding it can use for 24 hours, and calls `send_email(user_id, "report_export_ready", {link})`. It then sets the record to `done` and stores `object_key`. The email comes before `done` on purpose: the user may get the email a moment before the page says `done`, and if the last write fails, the retry may send a second email and replace the file. That is better than a user who never gets a link. Both links point to the same key. The link stops working after 24 hours and the file is deleted after 7 days by the bucket's lifecycle rule, so no cleanup job is built.
   - Failure: if the email or the final write fails, the attempt fails and the whole export is retried.

8. **Failure and retry.** If an attempt raises, times out or loses its worker, the queue retries it after the backoff, starting again at step 5 with a new upload. When the handler raises, it aborts its multipart upload first. If the worker dies or times out, nothing aborts, but the unfinished upload is never visible and the bucket discards it. While waiting to retry, the record stays `running`, so a new click returns the same export. After the last attempt fails (at worst about 1.5 hours after the click), the queue calls `on_final_failure`. It sets the record to `failed` and calls `send_email(user_id, "report_export_failed", {})`. No email is sent for attempts that will be retried. A `failed` export no longer blocks a new click.

## Open questions

- Whether 30 minutes (one attempt) is enough to export 2 million rows at 5,000 rows per query. Measure it before relying on it.
- The nightly rebuild could change rows while an export is reading them. We do not guard against this.
- After 24 hours the emailed link is dead and after 7 days the file is gone, but the page still shows `done`. Decide whether the page should say the file has expired, or offer a fresh link.
- If the API dies between inserting the record and enqueuing the job, the record stays `queued` and blocks that user's clicks on that report. No reaper is planned.
