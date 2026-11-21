# CSV export plan

Adds a **Download CSV** button to the reports page. Today the page loads rows 500 at a time from `GET /api/reports/{report_id}/rows`, and the server stores nothing about what the user is viewing. Small reports are sent straight back as the CSV. Large reports are built by a background job, put in object storage and emailed as a link, because a request is killed after 60 seconds and a worker has only 512 MB of memory. Export state is kept in a new table so the page can show it.

Out of scope: scheduled exports, formats other than CSV, changes to the table on the page.

## Terms

- **Read replica**: the copy of the database that report rows must be read from. Report data is never read from the primary database.
- **Keyset paging**: read rows with `row_id > after ORDER BY row_id LIMIT n`. `row_id` is unique and increasing within a report. Never use OFFSET.
- **`reports.row_count`**: the total, unfiltered row count of a report. It is rewritten each night. It decides which path an export takes, even when the user has filtered the view.
- **Job queue** (`jobs.py`): runs a handler on a worker (512 MB memory, one attempt at a time). A job is tried at most 3 times, waiting 60 s and then 300 s between attempts. An attempt is killed after 1800 s. Each retry starts the handler again from the beginning with the same payload (under 64 KB). Delivery is at least once, so a handler can run again after it has succeeded.
- **Multipart upload** (`storage.py`): a large object is uploaded in parts of at least 5 MB (except the last), at most 10,000 parts. Nothing is visible at the key until `complete_multipart` succeeds.
- **`exports` bucket**: already exists. Its lifecycle rules delete every object after 7 days and discard a multipart upload not completed within 24 hours.
- **Signed URL**: a download link from `signed_url(bucket, key, ttl_seconds)`. The maximum is 86,400 s (24 hours).
- **Export record**: a row in the new `report_exports` table. It holds the export id, report id, user id, filters, column order, status (`queued`, `running`, `done` or `failed`), job id, object key and created time. It lives in the primary database, which is fine because it is not report data.

## Steps

1. **Create the table.** Add `report_exports` with a unique partial index on `(user_id, report_id)` for rows whose status is `queued` or `running`. The index is what enforces "one large export at a time".

2. **The user clicks Download CSV.** The page sends `POST /api/reports/{report_id}/exports` with the filters and column order taken from the page URL. The server checks the `report.view` permission on the report's workspace and returns 403 if it is missing. It then reads `reports.row_count` and picks a path.

3. **Small path (10,000 rows or fewer).** The response is the CSV. The server writes the header row, then pages through the replica by keyset in batches of 500 and writes each batch to the response as it goes. No job runs, nothing is stored and there is no export record. If it fails midway, the download fails and the user clicks again.

4. **Large path (more than 10,000 rows).** The server inserts an export record with status `queued`, enqueues a `report_export` job with the export id, and returns the record straight away.
   - If the insert breaks the unique index, the user already has an export of this report queued or running. The server returns that existing record and enqueues nothing.
   - If the enqueue call fails, the server sets the record to `failed` so it does not block the next click, and returns an error.

5. **The job runs.** At the start of each attempt, the handler loads the record. If it is already `done`, it stops (this covers repeated delivery). Otherwise it sets `running`, then:
   - starts a multipart upload for the key `exports/{export_id}.csv`;
   - writes the header row, then pages through the replica by keyset in batches of 5,000 rows, appending CSV text to one in-memory buffer;
   - when the buffer reaches about 8 MB, uploads it as a part and empties it. Memory use is therefore one buffer plus one batch, never the whole report. The largest report (about 900 MB) needs roughly 115 parts, far below the limit;
   - after the last batch, uploads the remainder as the final part and calls `complete_multipart`. The file becomes visible only now, so a half-written file is never downloadable;
   - builds a signed URL with a 24-hour lifetime, calls `send_email(user_id, template, params)` with it, and sets the record to `done` with the object key.

6. **The page shows status.** When the report page loads, it asks for the user's most recent export of this report (`GET /api/reports/{report_id}/exports/latest`) and shows its status. While the status is `queued` or `running` it polls the same endpoint every few seconds. This also covers a user who leaves and comes back. A `done` export tells the user to check their email.

7. **Old files** are removed by the bucket's lifecycle rule. Do not build a cleanup job.

## What happens when things fail

| Failure | What happens |
|---|---|
| User lacks `report.view` | 403, no record, no job. |
| Small export fails midway | The download breaks; the user clicks again. |
| Second click during a large export | Returns the existing export; no new job. |
| Handler raises (replica error, upload error, email error) | The handler aborts its multipart upload and re-raises. The queue retries from the start with a fresh upload, up to 3 attempts in total. The record stays `running` between attempts. |
| Attempt times out or the worker dies | The abort does not run. The leftover upload is never completed, so nothing is downloadable, and the bucket discards it after 24 hours. The queue retries as above. |
| Job runs again after succeeding | The handler sees `done` and stops. |
| Last attempt fails | `on_final_failure` sets the record to `failed` and emails the user that the export failed. The page shows `failed`, and the user may start a new export. |

The email templates for success and failure are new; their names are to be chosen when building.

## Building it

Build in this order: table and index, the job, the endpoint (both paths), then the page status. The job can be tried against a large test report before the button is shown.

## Open questions

- Whether a 2-million-row export finishes within the 1,800 s attempt timeout is unmeasured. Measure it on the largest report before launch. If it is too slow, raise the batch size.
- The poll interval and the email template names are not decided.
- Permission is checked only at click time, not again when the job runs.