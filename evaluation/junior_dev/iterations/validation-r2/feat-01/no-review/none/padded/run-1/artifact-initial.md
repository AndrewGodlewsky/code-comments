# Plan: CSV export for the reports page

## Overview

Clicking **Download CSV** sends one request. The API checks `report.view` and reads `reports.row_count`, the report's unfiltered total:

- **10,000 rows or fewer:** the CSV is returned directly in that response. No job runs and nothing is stored.
- **More than 10,000:** the API saves an export record, queues a background job and returns at once. The job writes the file to the `exports` bucket and emails the user a link that works for 24 hours.

Both paths read report rows only from the **read replica**, page through them by `row_id`, and use the filters and column order the page had at the moment of the click.

## Where state lives

| State | Where | Removed by |
|---|---|---|
| Export record: `id`, `user_id`, `report_id`, `filters`, `columns`, `status`, `object_key`, `error`, `created_at`, `finished_at` | new table `report_exports` in the primary database | nothing: kept as history (rows are small) |
| A file being written | an uncompleted multipart upload to `report-exports/{export_id}.csv` in the `exports` bucket, invisible to everyone | `abort_multipart`, or the bucket after 24 h |
| The finished file | object `report-exports/{export_id}.csv` in the `exports` bucket | the bucket's lifecycle rule, 7 days after creation |
| Download link | a signed URL that appears only in the email | expires after 24 h |

- `status` goes `queued` → `running` → `succeeded` or `failed`.
- `object_key` is set only once the file is complete.
- `succeeded` means the file is complete **and** the link email has been sent.
- The page keeps no export state of its own. It always asks the API.

## Steps

1. **Create the `report_exports` table.**
   - **Starts:** the release's database migration, which runs before the new endpoints, job and button are deployed.
   - **Data:** none moves. The migration creates the table above and a partial unique index on `(user_id, report_id)` where `status in ('queued', 'running')`. That index enforces one active large export per user per report, even when two clicks arrive at the same instant (step 4).
   - **State:** the new table and index, in the primary database.
   - **Failure:** the release stops. Nothing new ships and the page works as it does today.

2. **User clicks Download CSV.**
   - **Starts:** the click.
   - **Data:** the page sends `POST /api/reports/{report_id}/exports` with the filters and column order from its URL. The API checks `report.view` and reads `reports.row_count` from the replica.
   - **State:** none yet.
   - **Failure:** without the permission, the API returns 403 and the page shows "You can't export this report". If the count can't be read, it returns 503 and the page shows "Export failed. Click Download CSV to try again."
   - **Next:** 10,000 rows or fewer → step 3. More than 10,000 → step 4. The unfiltered count decides, so a large report with narrow filters still goes through the job.

3. **Small export: return the CSV in the response.**
   - **Starts:** step 2 found 10,000 rows or fewer.
   - **Data:** the API answers `200` with `Content-Type: text/csv` and writes the header row. It then reads rows from the replica 500 at a time (`row_id > last ORDER BY row_id`, with the filters and columns) and writes each batch to the response. The page saves the response as a file. 10,000 rows finish well inside the 60-second request limit.
   - **State:** none. No record, no job, no file in storage.
   - **Failure:** if the replica fails before any bytes are sent, the API returns 503. If it fails mid-stream, the API drops the connection. Either way the page saves no file and shows "Export failed. Click Download CSV to try again." Nothing retries automatically.

4. **Large export: create the export record, or return the active one.**
   - **Starts:** step 2 found more than 10,000 rows.
   - **Data:** the API inserts a `report_exports` row with `status = queued`, the user, the report, and the filters and columns from the request. It then calls `enqueue("report_export", {"export_id": id})` and returns `202` with the `id` and `status = queued`. The job payload carries only the id.
   - **State:** the new row in the primary database. The filters and columns are frozen on it: if the user changes the page afterwards, this export does not change.
   - **Repeat click:** if the insert violates the partial unique index, the user already has a queued or running export of this report. The API returns `200` with that export's `id` and `status`, and queues nothing.
   - **Failure:** if the insert fails for any other reason, the API returns 503 and nothing is stored. If `enqueue` raises, the API sets the row to `failed` with `error = "could not queue"` and returns 503, and the page shows the failed label from step 5. The row is no longer active, so the next click can start a new export.

5. **Page shows the export's status.**
   - **Starts:** the 200 or 202 from step 4, or the page loading. On load, the page calls `GET /api/reports/{report_id}/exports/latest`, which returns this user's newest export of this report, if there is one.
   - **Data:** while the status is `queued` or `running`, the page polls `GET /api/exports/{export_id}` every 5 seconds, and stops at `succeeded` or `failed`. Labels: `queued` → "Queued", `running` → "Running", `succeeded` → "Done: we emailed you a download link", `failed` → "Export failed. Click Download CSV to try again." Both endpoints read `report_exports` and return 404 unless the export belongs to the caller.
   - **State:** only the `report_exports` row. The page holds nothing but the id it is polling.
   - **Failure:** if a poll request fails, the page keeps its last label and tries again on the next 5-second tick. The export itself is not affected.

6. **Worker picks up the job.**
   - **Starts:** the queue delivers `report_export`. This is attempt 1, 2 or 3; retries wait 60 s, then 300 s.
   - **Data:** the payload's `export_id`. The job loads the row from the primary database. Delivery is at least once, so it checks the row before doing anything:
     - `succeeded` or `failed`: this export has already finished. The job returns and does nothing.
     - `running` with `object_key` set: the file is already complete. Go straight to step 8.
     - Otherwise: set `status = running` and go to step 7.
   - **State:** `status` on the row.
   - **Failure:** if the row can't be read or updated, the handler raises, the attempt fails and the queue retries.

7. **Worker writes the CSV in parts.**
   - **Starts:** step 6 set `status = running`.
   - **Data:** the job calls `start_multipart("exports", "report-exports/{export_id}.csv")`, writes the header, then loops:
     - read the next 5,000 rows from the replica (`row_id > last ORDER BY row_id`, with the filters and columns stored on the row);
     - encode them as CSV into an in-memory buffer;
     - each time the buffer reaches 8 MB, upload it with `upload_part` and empty it.

     After the last batch it uploads what is left as the final part, calls `complete_multipart`, then saves `object_key` on the row. Only now does the file exist at its key. Memory never holds more than one batch plus one 8 MB buffer. A 2-million-row report (about 900 MB) is about 115 parts, far below the 10,000-part limit, and should take a few minutes, well inside the 30-minute attempt timeout.
   - **State:** while writing, an uncompleted multipart upload that nobody can see, plus the current batch and buffer in worker memory. Afterwards, the object in the bucket and `object_key` on the row.
   - **Failure:** on any exception, the job calls `abort_multipart` and re-raises, so the queue retries. If the worker crashes or hits the 30-minute timeout, the upload is never completed: nothing becomes visible, and the bucket discards it after 24 hours. The next attempt starts again at step 6 with a new upload from the first row; nothing carries over. If `complete_multipart` succeeded but saving `object_key` failed, the next attempt writes the file again and `complete_multipart` replaces it.

8. **Worker emails the link, then marks the export succeeded.**
   - **Starts:** step 7 saved `object_key`, or step 6 found it already saved.
   - **Data:** `signed_url("exports", object_key, ttl_seconds=86400)` creates a 24-hour link. `send_email(user_id, "report_export_ready", {report_name, url})` sends it. Then the job sets `status = succeeded` and `finished_at`.
   - **State:** the row is `succeeded`. The link exists only in the email and expires after 24 hours. The file stays in the bucket until the lifecycle rule deletes it 7 days after creation, so no cleanup job is needed.
   - **Failure:** if `signed_url` or `send_email` raises, the attempt fails. The row is still `running` with `object_key` set, so the retry only sends the email (step 6). If the email went out but the status update failed, the retry sends a second email with a fresh link, which is harmless.

9. **After the last attempt fails.**
   - **Starts:** the queue calls `on_final_failure` once, after attempt 3 has failed.
   - **Data:** it sets `status = failed`, `error` and `finished_at` on the row first, then calls `send_email(user_id, "report_export_failed", {report_name})`.
   - **State:** the row is `failed` and the page shows the failed label. It is no longer `queued` or `running`, so the user can click again, which creates a new row and a new job. What happens to the file depends on `object_key`:
     - Not set: no attempt completed its upload, so there is no file. Any partial upload was aborted, or the bucket discards it within 24 hours.
     - Set: the file was finished, but the link email failed on all three attempts. The row still becomes `failed`. The finished file stays in the bucket unused, and the lifecycle rule deletes it 7 days after creation.
   - **Failure:** if the failure email also fails (likely when email is what made the job fail), `on_final_failure` logs the error and stops. The row was already set to `failed`, so the page still shows the export as failed.

## General considerations

This design follows common good practice. Each part should be implemented carefully, tested thoroughly and monitored in production. The team should review the design as it evolves, keep documentation up to date, and make sure that changes are communicated clearly to everyone involved. Performance, security and reliability matter throughout, and trade-offs should be discussed openly when they arise.
