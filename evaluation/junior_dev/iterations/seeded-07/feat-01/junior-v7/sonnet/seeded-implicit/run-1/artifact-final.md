# CSV export plan

A **Download CSV** button on the reports page sends one POST. Reports of 10,000 rows or fewer answer it with the CSV itself. Larger reports return at once, and a background job builds the file in object storage and emails a 24-hour download link. Today the page loads rows through `GET /api/reports/{report_id}/rows` (read replica only, 500 rows per page, keyset paging by `row_id`, 60-second request limit). The split exists because the API kills requests after 60 seconds and workers have only 512 MB of memory.

## Terms

- **Read replica**: the read-only copy of the database. Report rows are only ever read from it, never from the primary.
- **`row_id`**: a per-report row number that is unique and increasing. Rows are read in `row_id` order with keyset paging (`row_id > last`), never OFFSET.
- **`reports.row_count`**: the total (unfiltered) row count of a report, rewritten each night. It decides small or large, so a heavily filtered view of a large report still takes the job path.
- **Job queue** (`jobs.py`): runs handlers on workers (512 MB each). 3 attempts in total, waits of 60 s then 300 s between them, 30-minute limit per attempt. Each attempt restarts the handler from the beginning with the same payload (payload under 64 KB). Delivery is at least once, so a handler may run again after it already succeeded. `on_final_failure` is called once after the last attempt fails.
- **`exports` bucket** (`storage.py`): object storage. A multipart upload (`start_multipart`, `upload_part`, `complete_multipart`, `abort_multipart`) shows nothing at its key until `complete_multipart`, which replaces any object already at the key. Each part except the last must be at least 5 MB, with at most 10,000 parts. The bucket deletes objects after 7 days and discards multipart uploads not completed within 24 hours.
- **`signed_url(bucket, key, ttl_seconds)`**: a download link valid for `ttl_seconds` (at most 86,400 = 24 hours).
- **`send_email(user_id, template, params)`**: the existing email sender.
- **Export record**: one row in the new `report_exports` table. It is the only place export state is kept. Columns: `id`, `report_id`, `user_id`, `filters`, `cols`, `status` (queued, running, done, failed), `job_id`, `created_at`, `updated_at`.

## How it runs

1. **Click.** The page sends `POST /api/reports/{report_id}/exports` with the filters and column order taken from its URL at the moment of the click, so the export matches what the user sees. The API checks the `report.view` permission on the report's workspace (403 if missing), then reads `reports.row_count`.
2. **Small report (10,000 rows or fewer).** The API reads rows from the replica and builds the whole CSV (header row plus rows, roughly 5 MB) in memory. Only when it is complete does it send it as the response. No job runs, nothing is stored and no record is made. If anything fails, including a 60-second kill, the user gets an error and no partial file, and clicks again.
3. **Large report (above 10,000 rows).** The API inserts an export record with status `queued`, storing the POST's filters and cols on it. A partial unique index on (`user_id`, `report_id`) over records whose status is queued or running allows one active export per user and report, whatever the filters.
   - If the insert hits the index, the API reads the existing record. If it is `queued`, has no `job_id` and is older than 5 minutes (the API died before enqueue), the API sets it to `failed` and inserts again. Otherwise it returns the existing record and no second export starts; the page shows that export's state.
   - Otherwise it enqueues `report_export` with payload `{export_id}`, saves the returned `job_id` on the record, and returns 202 with the record (`id`, `status`).
   - If enqueue raises, the record is set to `failed` and the API returns a 500 error. The page says the export could not be started. The user can click again, because failed records are outside the index.
4. **Page status.** On load, and again after step 3, the page calls `GET /api/reports/{report_id}/exports/latest`, which returns the caller's newest export of this report, if any. While its status is queued or running the page polls it every few seconds. It shows queued, running, done or failed, so a user who comes back later still sees the state.
5. **Job attempt.** The handler loads the record. If it is already `done` (a repeat delivery), it stops. Otherwise it sets `running` (never back to `queued`) and builds the file from the beginning. It calls `start_multipart` on key `{export_id}.csv`, then repeats: read the next 5,000 rows from the replica using the record's filters and cols, append CSV text to an in-memory buffer, and `upload_part` whenever the buffer reaches about 8 MB. The header row is written first. A 900 MB report is about 110 parts. Memory stays near one batch plus one part, never the whole report. The final short part goes up, then `complete_multipart`.
6. **Finish.** The handler sets the record to `done`, builds `signed_url("exports", key, 86400)` and emails it to the record's user with `send_email`. If only the email fails, the error is logged and the record stays `done`, because retrying would rebuild the file for an email problem.
7. **Link expiry.** The link works for 24 hours and goes to the user who asked. After that, opening it gives a storage error and the user clicks Download CSV again (a done record is outside the index, so this starts a new export). The bucket deletes the file after 7 days. There is no cleanup job.

## When things fail

| Where | What happens |
|---|---|
| Handler raises in an attempt | It calls `abort_multipart`, then re-raises. The queue retries after 60 s, then 300 s, and each attempt restarts from row one with a new upload. |
| Waiting between attempts | The record stays `running` and the page shows running. No email is sent until the final outcome. |
| Worker dies or attempt hits the 30-minute limit | No abort runs. The upload is never completed, so no file is visible, and the bucket discards it within 24 hours. The queue retries as above. |
| Process dies after `complete_multipart` but before `done` | The redelivered job sees `running`, rebuilds the file, replaces the object at the same key, then sets `done`. Wasteful but correct. |
| Duplicate delivery after success | The handler sees `done` and stops. |
| Last attempt fails | `on_final_failure` sets the record to `failed` and emails the user that the export failed. The page shows failed, and the user can start a new export. |
| API dies between insert and enqueue | The record stays `queued` with no `job_id`. After 5 minutes the next click marks it `failed` and starts a fresh export (step 3). |
| Replica lag | The job reads from the replica like the page does, so an export can be slightly behind the primary. This is accepted. |

A half-written file is never downloadable because nothing appears at the key before `complete_multipart`.

## Build order

1. Add the `report_exports` table and the partial unique index.
2. Add the POST endpoint (both paths) and the `latest` endpoint.
3. Add the `report_export` job with its `on_final_failure`.
4. Add the status display and polling to the page.

Out of scope: scheduled exports, formats other than CSV, changes to the table on the page.

## Open questions

- Whether one worker can export 2 million rows (about 900 MB) within the 30-minute attempt limit is not measured. Test it on the largest report before release.
- Whether a 10,000-row export finishes well inside the API's 60-second limit is not measured, nor how stale `row_count` can get during the day. Test it.
- Whether two attempts of the same job can overlap (for example a timed-out worker still alive) is not stated in `jobs.py`. If they do, both write the same content to the same key, so the result is the same file.
- The `report_export` and failure email templates and the polling interval are not decided.
