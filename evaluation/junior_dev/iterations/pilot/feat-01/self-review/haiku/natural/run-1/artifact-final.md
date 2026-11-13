# Plan: CSV export for the reports page

## Overview

The reports page gets a **Download CSV** button. What happens after the click depends on the number of rows in the report:

- **10,000 rows or fewer:** the server builds the CSV and sends it in the same HTTP response. Nothing is stored.
- **More than 10,000 rows:** the server records the export in a small database table and replies immediately. A background job then builds the CSV as a file in the `exports` storage bucket. When the file is ready, the user gets an email with a download link that works for 24 hours. The page shows the export's progress.

A new table, `report_exports`, records each large export. It shows status on the page, allows only one active export per user and report, and makes failures visible.

## Key terms

- **Report rows:** the rows of one report, stored in the `report_rows` table. Each row has a `row_id` that is unique and increases within its report.
- **Primary database:** the main database. It accepts writes.
- **Read replica:** a read-only copy of the primary database. Report rows are read only from the replica, never from the primary.
- **Keyset paging:** to fetch the next page, ask for rows whose `row_id` is greater than the last `row_id` already seen, sorted by `row_id`, with a limit. The database can use its index directly, so every page takes about the same time. This plan never uses OFFSET.
- **Job queue:** the existing background job system. A job is a named handler function plus a small JSON payload. Jobs run on worker processes, each with 512 MB of memory.
- **Attempt:** one run of a job's handler. A job gets at most 3 attempts. After a failed attempt the queue waits 60 s before attempt 2 and 300 s before attempt 3. Each attempt starts from the beginning and keeps no progress from earlier attempts. An attempt still running after 1,800 s is killed.
- **At-least-once delivery:** the queue may run a job again even after it succeeded. Every step must therefore be safe to repeat.
- **Multipart upload:** object storage receives a file as numbered parts. The file is invisible at its final key until one "complete" call joins the parts. Every part except the last must be at least 5 MB. An upload that is never completed or aborted is discarded by the bucket after 24 hours.
- **Signed URL:** a download link that stops working after a set time.
- **Lifecycle rule:** a bucket setting. The `exports` bucket deletes each object 7 days after it was created.
- **Partial unique index:** a database index that enforces uniqueness only for rows matching a condition. Here it allows at most one row per user and report whose `state` is `queued` or `running`.
- **`send_email(user_id, template, params)`:** the existing email helper.
- **`report.view`:** the existing permission a user needs on a report's workspace to see its data.

---

## Step 1. Share the row-reading code between the page and the export

- **What starts it:** this step is built before any new endpoint, so the export cannot drift away from the page.
- **Data moved at runtime:** none. The page API's existing code for parsing filters, checking columns, and building the keyset query moves into one shared module. The page keeps calling it, and the export calls it too.
- **State:** none.
- **If it fails:** the page's existing tests fail and the change is not deployed. The page's behaviour must not change.

The shared module does three things:
1. It parses `filters` and `cols` from the URL.
2. It rejects unknown columns or filters with a 400 error.
3. It builds the keyset query against the replica.

Because the page and the export use the same module, the export returns the same rows, in the same column order, that the page shows.

## Step 2. Add the export state table

- **What starts it:** a database migration is deployed.
- **Data moved:** none yet.
- **State:** a new table named `report_exports` on the primary database. The name avoids confusion with the `exports` bucket. Columns:
  - `export_id` (UUID, primary key)
  - `user_id`, `report_id`, `workspace_id`
  - `filters` and `cols`: the raw, validated query strings from the URL
  - `state`: one of `queued`, `running`, `done`, `failed`
  - `job_id`: the queue's ID for the job, set after the job is queued
  - `attempt`: the number of the latest attempt
  - `upload_id`: the open multipart upload, if there is one
  - `object_key`: the file's key in the bucket, set when the file is complete
  - `error`: a short reason, with no row data
  - `email_sent_at`
  - `created_at`, `updated_at`, `finished_at`

  A **partial unique index** on `(user_id, report_id)`, applied only to rows whose `state` is `queued` or `running`, allows only one active export per user and report. The database enforces this even when two clicks arrive at the same moment.
- **If it fails:** the migration stops the deploy. Nothing else has changed yet.

This table holds only export metadata, so it may live on the primary. Report rows never go there.

## Step 3. Handle the click: `POST /api/reports/{report_id}/exports`

- **What starts it:** the user clicks Download CSV. The page sends the same `filters` and `cols` it is showing, as query parameters.
- **Data moved:**
  1. The API checks that the caller has `report.view` on the report's workspace. If not, it returns 403.
  2. It validates `filters` and `cols` with the shared module. If they are invalid, it returns 400.
  3. It reads `reports.row_count` from the **replica**. Report rows are never read from the primary. This value is report metadata rather than rows, but reading it from the replica keeps one rule for all report reads.
  4. If `row_count` is 10,000 or less, go to Step 4. Otherwise go to Step 5.
- **State:** none.
- **If it fails:** a 403 or 400 is returned as is. If the replica cannot be reached, the API returns 503 and the page shows a retry message.

## Step 4. Small export: stream the CSV in the response

- **What starts it:** Step 3 finds 10,000 rows or fewer.
- **Data moved:**
  1. The API writes a header row, built from `cols`.
  2. It reads report rows from the replica in keyset pages of 500 rows, using the same `filters`, sorted by `row_id`.
  3. Each page is encoded as CSV and written to the response as soon as it is ready.

  The response has `Content-Type: text/csv` and `Content-Disposition: attachment`. Only one page is held in memory at a time.
- **State:** nothing is stored. No job runs and no file is written. This follows the brief.
- **If it fails:**
  - If the replica fails before the first byte is sent, the API returns 503. The user can click again.
  - If it fails partway through the stream, the connection drops. The page must download with `fetch`, not with a plain link. A plain link would save a silently truncated file without any warning. With `fetch`, a dropped stream produces an error that the page can show.
  - The API kills any request that runs longer than 60 s. Step 12 measures whether 10,000 rows finish well inside that limit. If they do not, the 10,000-row threshold must change, and that decision goes back to the owner (Decision 1).

**CSV escaping (applies to Steps 4 and 7):** use UTF-8. Wrap any field that contains a comma, a double quote, or a line break in double quotes, and double any quote characters inside it. Prefix any field that starts with `=`, `+`, `-` or `@` with a single quote, so that spreadsheet programs do not run it as a formula. This also affects negative numbers, which will appear as text such as `'-5`.

## Step 5. Large export: record it and queue a job

- **What starts it:** Step 3 finds more than 10,000 rows. The API returns quickly and never waits for the file.
- **Data moved:** no file data moves. The API writes one row to `report_exports` and queues one job.
- **State:** the `report_exports` table, and the queue's own job record.

Sequence:

1. **Look for an active row** (`state` is `queued` or `running`) for this user and report.
   - **If one exists and is stale,** mark it `failed` with the reason "stalled", then continue to item 2. A row is stale in one of two cases:
     - It is `queued` with no `job_id`, and `created_at` is more than 5 minutes ago. The API probably crashed between inserting the row and queuing the job.
     - It is `running`, and `updated_at` is more than 2 hours ago. `updated_at` is set when an attempt starts (Step 6). An attempt is killed after 1,800 s, so after 2 hours no attempt can still be running. The longest possible run of all three attempts, including the waits, is 5,760 s (about 1.6 hours).

     Marking a row stalled changes only that row. It deletes no files. It is not a cleanup job.
   - **If an active row exists that is not stale,** return it now (see the response below).
2. **Otherwise, insert a new row** with `state = queued`, the `filters` and `cols` from the request, and a new `export_id`.
   - If the insert breaks the partial unique index, another click won the race. Read the winning row and return it.
3. **Queue the job `export_report`** with the payload `{"export_id": ...}`. The payload holds only the ID, because the queue limits payloads to 64 KB and URL parameters could be longer.
4. **Save the returned `job_id`** on the row.
5. **Return `202`** with JSON `{export_id, state, filters, cols}`.

When an active export is returned instead of a new one, the response has the same JSON shape. Its `filters` and `cols` are those of the active export, which may differ from what the user is viewing. Decision 2 covers this.

A click after an export is `done` or `failed` is not blocked. It starts a new export, because no active row exists.

- **If it fails:**
  - If queuing the job raises an error, mark the row `failed` with the reason "could not queue", and return 503.
  - If the API crashes after the insert and before the job is queued, the row stays `queued` with no `job_id`. The stale rule in item 1 clears it on a later click, so the user is not blocked for long.
  - The queue may run the job after the row was already marked `failed` as stalled. The handler in Step 6 checks the state first and exits if the row is `failed`.
  - If the queue loses a job that already has a `job_id`, the row stays `queued` and no stale rule applies. See Decision 10.

## Step 6. Job attempt: set up the upload

- **What starts it:** the queue runs `export_report`, for the first attempt or for a retry.
- **Data moved:** the handler reads its row from `report_exports` by `export_id`, then checks `report.view` for the row's `user_id`.
- **State:** the row is updated at the start of each attempt.

Sequence:

1. **Load the row.**
   - If `state` is `done`, skip to Step 9 to resend the email if `email_sent_at` is still empty. Then stop.
   - If `state` is `failed`, stop.
   - If `state` is `queued` or `running`, continue.
2. **Re-check `report.view`.** If the user has lost access, mark the row `failed` with the reason "access removed", send the failure email (Step 10), and stop without raising an error. The queue then treats the job as succeeded, so it does not retry.
3. **Set** `state = running`, `attempt = ctx.attempt`, and `updated_at = now`.
4. **If `upload_id` is already set** from an earlier attempt, call `abort_multipart(upload_id)`. Ignore any error, because the upload may already be gone.
5. **Call** `start_multipart("exports", "reports/{report_id}/{export_id}.csv")`. Store the returned `upload_id` on the row.

The key contains `export_id`, so each export always uses the same key. A rerun with the same content replaces the object at that key, which is safe.

- **If it fails:** an exception ends the attempt, and the queue retries after 60 s, then after 300 s. If the row cannot be read at all, the exception ends the attempt and the same retry rules apply.

## Step 7. Job attempt: stream rows into parts

- **What starts it:** Step 6 succeeds.
- **Data moved:**
  1. Write the header row.
  2. Read report rows from the **replica** in keyset pages of 5,000 rows (`row_id > last ORDER BY row_id LIMIT 5000`), using the same `filters` and `cols` through the shared module from Step 1.
  3. Encode each row as CSV and append it to an in-memory buffer.
  4. When the buffer reaches 16 MB, call `upload_part(upload_id, part_number, data)`. Keep the returned etag and part number in a small in-memory list, then clear the buffer. Part numbers count from 1.
  5. When the last page has been read, upload the remaining buffer as the final part. The final part may be smaller than 5 MB.
- **State:** the open `upload_id` is stored on the row. The list of etags exists only in memory, for this attempt. The queue keeps no progress between attempts, so a retry starts again at Step 6.
- **Memory:** at most one 5,000-row page and one 16 MB buffer are held at a time. This should keep a worker far under 512 MB, even for the largest report (about 2 million rows, roughly 900 MB of CSV). That file needs about 57 parts, well under the limit of 10,000. These are estimates until Step 12 measures them.
- **Time:** the largest export must finish within the 1,800 s attempt timeout. Roughly 900 MB must move in 1,800 s, so the sustained rate must be about 0.5 MB/s, including replica reads and uploads. This is an estimate. Step 12 measures it.
- **If it fails:**
  - An exception, a worker crash, or the 1,800 s timeout ends the attempt. The multipart upload stays open and invisible. The next attempt aborts it in Step 6. The bucket discards it after 24 hours in any case.
  - Nothing is visible at the final key, so a half-written file cannot be downloaded.
  - The queue retries after 60 s, then after 300 s, starting again at Step 6.
- **Open risk:** if the largest export takes close to 30 minutes, every attempt will time out in the same way. Step 12 decides this. The fallback would be to save the `upload_id` and the last `row_id` after each part, so a retry could resume. That fallback is not part of this plan (see Decision 4).

## Step 8. Job attempt: make the file visible

- **What starts it:** Step 7 has read every page and uploaded the last part.
- **Data moved:** `complete_multipart(upload_id, etags)` joins the parts and makes the object visible at its key. This is the only step that makes the file downloadable.
- **State:** the row is then set to `state = done`, with `object_key` and `finished_at` set and `upload_id` cleared.
- **If it fails:**
  - If `complete_multipart` fails, the object is not visible. The attempt ends, and the queue retries from Step 6.
  - If the object is complete but the database update fails, the attempt also ends. The row still says `running`. The next attempt redoes the export and replaces the same key with identical content. The abort in Step 6 is ignored, because that upload has already completed. This is safe, because jobs may run more than once.

## Step 9. Email the download link

- **What starts it:** Step 8 has set the row to `done`, or Step 6 finds a `done` row whose `email_sent_at` is empty.
- **Data moved:** `signed_url("exports", object_key, 86400)` creates a link that works for 24 hours. The link is created at send time, so it is valid for a full 24 hours from the email. Then `send_email(user_id, "export_ready", {export_id, report_id, download_url, expires_at})` is called.
- **State:** after the send succeeds, `email_sent_at` is set on the row.
- **If it fails:** the send raises an exception and the attempt ends. The file is already `done`, so the next attempt skips the export (Step 6) and only resends the email. The user does not get a second copy of the file. A second email is sent only if `email_sent_at` is still empty.

The templates `export_ready` and `export_failed` must be created. This plan assumes they do not exist yet.

## Step 10. Final failure: after the third attempt

- **What starts it:** all 3 attempts have failed. The queue then calls `on_final_failure(ctx, payload, error)` once.
- **Data moved:** the handler loads the row first.
  - If the row cannot be loaded, log the error and stop. There is no row to update.
  - If the row is `done` and `email_sent_at` is set, do nothing.
  - If the row is `done` and `email_sent_at` is empty (the file is complete, but the email failed on every attempt), try `send_email` for `export_ready` once more. The file is still usable, and the page shows it as done.
  - Otherwise, abort `upload_id` if one is set (ignoring errors), set `state = failed` with a short `error` (no row data and no stack trace), and send `export_failed` with `{export_id, report_id}`.
- **State:** the row is set to `failed`, or it stays `done`. The page reads this row, so the page is correct even if the email fails.
- **If it fails:** if the failure email also fails, the error is logged. The page still shows the correct state. Nothing else retries. This is the accepted limit.

## Step 11. Page status and download

- **What starts it:** the reports page loads, and then again while an export is `queued` or `running`.
- **Data moved:**
  1. On load, the page calls `GET /api/reports/{report_id}/exports/latest`. This returns the user's active export for that report if one exists. Otherwise it returns the most recent one. The endpoint checks `report.view` and returns only the user's own rows.
  2. While the state is `queued` or `running`, the page polls the same endpoint every 5 seconds. It shows the state and when the export started.
  3. When the state is `done`, the page shows a **Download** button. The button calls `GET /api/exports/{export_id}/download`. The API checks that the export belongs to the user and that the user still has `report.view`. It then returns a fresh signed URL valid for 24 hours. A fresh link is needed because the email link expires after 24 hours, while the file itself stays for 7 days.
  4. When the state is `failed`, the page shows a message and a **Start again** button. The button sends the same POST as Step 3.
  5. When `finished_at` is more than 7 days ago, the bucket's lifecycle rule has deleted the file. The page shows "expired" and offers **Start again**. The file's age is counted from when it was completed, which is almost the same time as `finished_at` (Decision 6).
- **State:** nothing new. The page keeps nothing beyond what the API returns.
- **If it fails:** if the status request fails, the page shows "status unavailable" and retries. If the download request fails, the user sees an error and can try again. Neither failure changes any data.
- **Concurrent clicks:** Step 5 returns the active export instead of starting a new one. The page then shows that export's filters.

## Step 12. Test before release

- **What starts it:** the code is complete, before the feature is enabled.
- **Tests:**
  1. **Boundary:** a report with exactly 10,000 rows takes the small path. A report with 10,001 rows takes the large path.
  2. **Replica only:** check that report rows are never read through the primary's connection in the export code.
  3. **Concurrency:** two simultaneous clicks produce one row, and both responses carry the same `export_id`.
  4. **Retries:** make an attempt fail at part 30. Check that the attempt is retried, that no object is visible at the key until the final complete, and that the final file contains every row.
  5. **Timeout:** make an attempt run past 1,800 s. Check that the retry starts from the beginning.
  6. **Final failure:** make all three attempts fail. Check that the row is `failed`, that the `export_failed` email is sent, and that the page shows the failure.
  7. **Email failure:** make `send_email` fail once. Check that the next attempt only resends the email.
  8. **Stale rows:** create a `queued` row with no `job_id` that is older than 5 minutes. Check that the next click clears it and starts a new export.
  9. **Synchronous timing:** stream 10,000 rows and measure the time. It must finish well inside 60 s, with margin.
  10. **Largest report:** run the 2-million-row report in a staging worker with a 512 MB memory limit. Measure peak memory and total time against the 1,800 s attempt timeout.
  11. **Lifecycle:** confirm that the 7-day rule and the 24-hour multipart rule exist on the `exports` bucket. Do not add a cleanup job.

The measured results from Step 12 are needed before release. Until then, the time and memory figures in this plan are estimates.

---

## Decisions to confirm with the owner

1. **Sync time limit.** If 10,000 rows cannot stream comfortably within 60 s on the replica, the threshold must come down. This conflicts with the fixed 10,000 figure, so it needs an explicit decision.
2. **Active export with different filters.** Step 5 returns an active export even when its filters differ from what the user is now viewing. The page must then show which filters that export used. The alternative is to reject the click with 409.
3. **Permission re-check in the job.** This plan re-checks `report.view` at the start of each attempt. If access has been removed, the job ends without a retry.
4. **Retry from the start.** If the largest export takes close to 30 minutes, retries from the start will time out the same way. The resume fallback described in Step 7 would then be needed.
5. **Stale `running` threshold.** The 2-hour threshold in Step 5 is a judgement call. It must stay longer than the longest possible run of the job (5,760 s), plus the time between attempts.
6. **Expiry window.** The bucket deletes files 7 days after creation, so the page shows "expired" after that. The 7 days are counted from `finished_at`, which is effectively the file's creation time.
7. **Email templates.** `export_ready` and `export_failed` are new. Their content and wording need to be decided.
8. **CSV format details.** The plan uses UTF-8 with escaping for formula-like fields. Whether to add a byte-order mark (which helps Excel open UTF-8 files) is not decided.
9. **Row count staleness.** `reports.row_count` is rewritten each night, so the 10,000-row decision can be out of date on a day when the report is rebuilt. The brief accepts this, and the plan keeps it.
10. **Queued job that never runs.** The stale rule covers a `queued` row with no `job_id`, and a `running` row. It does not cover a row that has a `job_id` but whose job never starts, for example if the queue loses it. Such a row would stay `queued` and block new exports for that user and report. Proposed fix: treat a `queued` row as stale when `created_at` is older than a threshold the owner sets. This is not yet decided.