# Plan: CSV export for the reports page

## Overview

The reports page gets a **Download CSV** button. The click either returns the CSV directly (10,000 rows or fewer) or starts a background job that writes the file to the `exports` bucket and emails a 24-hour download link (more than 10,000 rows). A small table records each large export so the page can show its status, enforce one active export per user and report, and make failed exports visible.

Terms used below:
- **Read replica**: a read-only copy of the database. Report rows are read only from here.
- **Keyset paging**: each page asks for rows with `row_id > last_seen ORDER BY row_id LIMIT n`. It never uses OFFSET.
- **Multipart upload**: object storage receives a file as numbered parts. The file stays invisible at its key until the parts are joined in one "complete" call. Parts are at least 5 MB each, except the last.
- **Attempt**: one run of a job handler. A job gets up to 3 attempts, with waits of 60 s and then 300 s between them. Each attempt starts from the beginning. An attempt is killed after 1,800 s.

---

## Step 1. Share the row-reading code between the page and the export

- **Starts when:** this is built before any new endpoint, so the export cannot drift from the page.
- **Data moves:** none at runtime. The page API's current filter parsing, column validation and keyset query move into one shared module. The page keeps calling it, and the export calls it too.
- **State:** none.
- **If it fails:** the page's existing tests fail, and the change is not deployed. The page's behaviour must not change.

The shared module does three things: it parses `filters` and `cols` from the URL, it rejects unknown columns or filters with a 400, and it builds the keyset query against the replica. Using one module means the export always returns the same rows, in the same column order, that the page shows.

## Step 2. Add the export state table

- **Starts when:** a database migration is deployed.
- **Data moves:** none yet.
- **State:** a new table on the primary database, named `report_exports` to avoid confusion with the `exports` bucket. Columns:
  - `export_id` (UUID, primary key)
  - `user_id`, `report_id`, `workspace_id`
  - `filters` and `cols` (the raw validated query strings from the URL)
  - `state`: one of `queued`, `running`, `done`, `failed`
  - `job_id` (from the queue, set after enqueue)
  - `attempt` (the number of the latest attempt)
  - `upload_id` (the open multipart upload, if any)
  - `object_key` (set when the file is complete)
  - `error` (a short reason, with no row data)
  - `email_sent_at`
  - `created_at`, `updated_at`, `finished_at`

  A **partial unique index** on `(user_id, report_id)` where `state` is `queued` or `running` enforces one active export per user and report, even if two clicks arrive at the same moment.
- **If it fails:** the migration stops the deploy. Nothing else has changed yet.

This table holds only export metadata, so it is allowed to live on the primary. Report rows never go there.

## Step 3. Handle the click: `POST /api/reports/{report_id}/exports`

- **Starts when:** the user clicks Download CSV. The page sends the same `filters` and `cols` it is showing, as query parameters.
- **Data moves:**
  1. The API checks that the caller has `report.view` on the report's workspace. Otherwise it returns 403.
  2. It validates `filters` and `cols` with the shared module. Otherwise it returns 400.
  3. It reads `reports.row_count` from the **replica**. The brief says report data is never read from the primary, and this is report metadata, so reading it from the replica keeps the rule simple.
  4. If `row_count` is 10,000 or less, it goes to Step 4. Otherwise it goes to Step 5.
- **State:** none for this step.
- **If it fails:** a 403 or 400 is returned as-is. If the replica cannot be reached, the API returns 503 and the page shows a retry message.

## Step 4. Small export: stream the CSV in the response

- **Starts when:** Step 3 finds 10,000 rows or fewer.
- **Data moves:** the API sends a header row built from `cols`. It then reads report rows from the replica with keyset pages of 500 rows, filtered by `filters` and ordered by `row_id`. Each page is encoded as CSV and written to the response as it arrives. The response has `Content-Type: text/csv` and `Content-Disposition: attachment`. Memory use is one page at a time.
- **State:** nothing is stored. No job runs and no file is written. This follows the brief.
- **If it fails:**
  - If the replica fails before the first byte is sent, the API returns 503 and the user can click again.
  - If it fails mid-stream, the connection drops. The page must download with `fetch` and not with a plain link, so that a dropped stream shows an error instead of a silently truncated file.
  - The API kills any request after 60 s. Step 12 measures whether 10,000 rows finish well within that limit. If they do not, the threshold has to change, and that decision goes back to the owner.

Escaping rules apply to every CSV in this plan (Steps 4 and 7). Quote any field that contains a comma, quote or line break. Prefix any field that starts with `=`, `+`, `-` or `@` with a single quote, so that spreadsheet programs do not run it as a formula.

## Step 5. Large export: record it and enqueue a job

- **Starts when:** Step 3 finds more than 10,000 rows. The API returns quickly and never waits for the file.
- **Data moves:** nothing big moves. Only a row in `report_exports` is written, and then a job is queued.
- **State:** the `report_exports` table, and the queue's job record.

Sequence:
1. Look for an active row (`state` is `queued` or `running`) for this user and report.
   - If one exists and it is stale, mark it `failed` with reason "stalled". A row is stale in two cases:
     - It is `queued` with no `job_id` and `created_at` is more than 5 minutes ago. The API crashed between the insert and the enqueue.
     - It is `running` and `updated_at` is more than 2 hours ago. Every attempt updates `updated_at`, and the worst case for three attempts is about 1.7 hours.

     This marks one row. It deletes no files. It is not a cleanup job.
   - If an active row still exists, return it now (see the response below).
2. Otherwise, insert a new row with `state = queued`, `filters` and `cols` set from the request, and a new `export_id`.
   - If the insert hits the unique index, another click got there first. Read the row that won and return it.
3. Enqueue job `export_report` with payload `{"export_id": ...}`. The payload holds only the ID, because the queue limits payloads to 64 KB and the URL parameters could be long.
4. Save the returned `job_id` on the row.
5. Return `202` with JSON `{export_id, state, filters, cols}`.

The response for an already-active export has the same shape. The page then shows that export's status.

- **If it fails:**
  - If the enqueue raises an error, mark the row `failed` with reason "could not queue", and return 503.
  - If the API crashes after the insert and before the enqueue, the row is left `queued` with no `job_id`. The stale rule in step 1 of this step clears it on the next click, and the user is not blocked.
  - The queue may run the job after the row was marked failed as stalled. The handler in Step 6 checks the state first and exits if the row is `failed`.

## Step 6. Job attempt: start the upload

- **Starts when:** the queue runs `export_report` (for the first attempt or a retry).
- **Data moves:** the handler reads its row from `report_exports` by `export_id`. It re-checks `report.view` for `user_id`.
- **State:** the row is updated on each attempt.

Sequence:
1. Load the row.
   - If `state` is `done`, skip to Step 9 to resend the email if it has not been sent yet (`email_sent_at` is empty). Then stop.
   - If `state` is `failed`, stop.
2. Re-check `report.view`. If the user has lost access, mark the row `failed` with reason "access removed", send the failure email, and stop without raising an error. The queue then treats the job as done, and it does not retry.
3. Set `state = running`, `attempt = ctx.attempt`, `updated_at = now`.
4. If `upload_id` is already set from an earlier attempt, call `abort_multipart(upload_id)`. Ignore any error, because the upload may already be gone.
5. Call `start_multipart("exports", "reports/{report_id}/{export_id}.csv")`. Store the returned `upload_id` on the row.

The key contains `export_id`, so each export has a stable key. A rerun with the same content replaces the object at that key, which is safe.

- **If it fails:** an exception ends the attempt. The queue retries after 60 s, and then after 300 s. If the row cannot be read at all, the exception ends the attempt and the same retry rules apply.

## Step 7. Job attempt: stream rows into parts

- **Starts when:** Step 6 succeeds.
- **Data moves:**
  1. Write the header row.
  2. Read report rows from the **replica** in keyset pages of 5,000 rows (`row_id > last ORDER BY row_id LIMIT 5000`), with the same `filters` and `cols`, using the shared module.
  3. Encode each row as CSV and append it to an in-memory buffer.
  4. When the buffer reaches 16 MB, call `upload_part(upload_id, part_number, data)`. Keep the returned etag and the part number in a small list, and clear the buffer. Part numbers count from 1.
  5. When the last page is read, upload the remaining buffer as the final part. The last part may be smaller than 5 MB.
- **State:** the open `upload_id` is stored on the row. The list of etags lives in memory for this attempt only. The queue keeps no progress between attempts, so a retry starts again from Step 6.
- **Memory:** at most one 5,000-row page and one 16 MB buffer are held at a time. This keeps a worker far under 512 MB, even for the 2-million-row report (about 900 MB of CSV). The file needs about 57 parts, well under the limit of 10,000.
- **Time:** the 2-million-row export must finish within the 1,800 s attempt timeout. That needs a sustained rate of about 0.5 MB/s, including replica reads and uploads. Step 12 measures this.
- **If it fails:**
  - An exception, a worker crash, or the 1,800 s timeout ends the attempt. The multipart upload stays open and invisible. The next attempt aborts it in Step 6, and the bucket discards it after 24 hours in any case.
  - Nothing is visible at the final key, so a half-written file cannot be downloaded.
  - The queue retries after 60 s, then after 300 s, from Step 6.
- **Open risk:** if a 2-million-row export takes close to 30 minutes, every retry will time out in the same way. Step 12 decides this. The fallback is to save the `upload_id` and the last `row_id` after each part, so that a retry can resume. That fallback is not part of this plan.

## Step 8. Job attempt: make the file visible

- **Starts when:** Step 7 has read every page and uploaded the last part.
- **Data moves:** `complete_multipart(upload_id, etags)` joins the parts and makes the object visible at its key. This is the only step that makes the file downloadable.
- **State:** the row is then set to `state = done`, with `object_key`, `finished_at` and `upload_id` cleared.
- **If it fails:**
  - If `complete_multipart` fails, the object is not visible. The attempt ends and the queue retries from Step 6.
  - If the object is complete but the database update fails, the attempt also ends. The row still says `running`, and the next attempt redoes the export and replaces the same key with identical content. This is safe, because the job may run more than once.

## Step 9. Email the download link

- **Starts when:** Step 8 has set the row to `done`, or Step 6 finds a `done` row with `email_sent_at` empty.
- **Data moves:** `signed_url("exports", object_key, 86400)` creates a link that works for 24 hours. The link is generated at send time, so it is valid for a full 24 hours from the email. Then `send_email(user_id, "export_ready", {export_id, report_id, download_url, expires_at})` is called.
- **State:** after the send succeeds, `email_sent_at` is set on the row.
- **If it fails:** the send raises an exception and the attempt ends. The file is already `done`, so the next attempt skips the export (Step 6) and only resends the email. The user does not get a second copy of the file, and a second email is sent only if `email_sent_at` is still empty.

The templates `export_ready` and `export_failed` must be created. This plan assumes they do not exist yet.

## Step 10. Final failure: after the third attempt

- **Starts when:** the queue has used all 3 attempts and each one failed. The queue then calls `on_final_failure(ctx, payload, error)` once.
- **Data moves:** the handler loads the row and then:
  - If the row is `done` (the file is complete but the email failed on every attempt), it does not mark the row failed. It tries `send_email` for `export_ready` once more. The file is still usable and the page shows it as done.
  - Otherwise it aborts `upload_id` (ignoring errors), sets `state = failed` with a short `error` (no row data and no stack trace), and sends `export_failed` with `{export_id, report_id}`.
- **State:** the row is set to `failed` or stays `done`. The page reads this row, so the page is correct even if the email fails.
- **If it fails:** if the failure email also fails, the error is logged. The page still shows the state. Nothing else retries, so this is the accepted limit.

## Step 11. Page status and download

- **Starts when:** the reports page loads, and while an export is `queued` or `running`.
- **Data moves:**
  1. On load, the page calls `GET /api/reports/{report_id}/exports/latest`. This returns the user's active export for that report if one exists, otherwise the most recent one. The check is `report.view`, and only the user's own rows are returned.
  2. While the state is `queued` or `running`, the page polls the same endpoint every 5 seconds. It shows the state, and when the export started.
  3. When the state is `done`, the page shows a **Download** button. That button calls `GET /api/exports/{export_id}/download`. The API checks that the export belongs to the user and that the user still has `report.view`, then returns a fresh `signed_url` with a 24-hour life. A fresh link is needed because the email link expires after 24 hours, while the file stays for 7 days.
  4. When the state is `failed`, the page shows a message and a **Start again** button, which sends the same POST as Step 3.
  5. When `finished_at` is more than 7 days ago, the file has been deleted by the bucket's lifecycle rule. The page shows "expired" and offers **Start again**.
- **State:** nothing new. The page keeps no state beyond what the API returns.
- **If it fails:** if the status request fails, the page shows "status unavailable" and retries. If the download request fails, the user sees an error and can try again. Neither failure changes any data.
- **Concurrent clicks:** Step 5 returns the active export instead of starting a new one, so the page shows that export's filters.

## Step 12. Test before release

- **Starts when:** the code is complete and before the feature is enabled.
- **Tests:**
  1. **Boundary:** a report with exactly 10,000 rows goes the small path, and one with 10,001 rows goes the large path.
  2. **Replica only:** check that report rows are never read through the primary's connection in the export code.
  3. **Concurrency:** two simultaneous clicks produce one row, and both responses carry the same `export_id`.
  4. **Retries:** make an attempt fail at part 30. Check that the attempt is retried, that no object is visible at the key until the final complete, and that the final file has every row.
  5. **Timeout:** make an attempt run past 1,800 s, and check that the retry starts from the beginning.
  6. **Final failure:** make all three attempts fail. Check that the row is `failed`, that the `export_failed` email is sent, and that the page shows the failure.
  7. **Email failure:** make `send_email` fail once. Check that the next attempt only resends the email.
  8. **Stale rows:** create a `queued` row with no `job_id` that is older than 5 minutes. Check that the next click clears it and starts a new export.
  9. **Sync timing:** stream 10,000 rows and measure the time. It must finish well inside 60 s with margin.
  10. **Largest report:** run the 2-million-row report in a staging worker with a 512 MB memory limit. Measure peak memory, and total time against the 1,800 s attempt timeout.
  11. **Lifecycle:** confirm that the 7-day rule and the 24-hour multipart rule exist on the `exports` bucket. Do not add a cleanup job.

Measured results from Step 12 are needed before release, because the plan's time and memory assumptions are estimates until then.

---

## Decisions to confirm with the owner

1. **Sync time limit.** If 10,000 rows cannot stream comfortably within 60 s on the replica, the threshold must come down. This conflicts with the fixed 10,000 figure, so it needs an explicit decision.
2. **Active export with different filters.** Step 5 returns an active export even when its filters differ from what the user is now viewing. The page must show which filters that export used. The alternative is to reject the click with 409.
3. **Permission re-check in the job.** This plan re-checks `report.view` at the start of each attempt. If access is removed, the job ends without a retry.
4. **Retry from the start.** If the largest export takes close to 30 minutes, retries from the start will fail the same way. The resume fallback in Step 7 would then be needed.
5. **Stale `running` threshold.** The 2-hour threshold in Step 5 is a judgement. It must stay longer than the worst-case retry window.
6. **Expiry window.** Files are removed after 7 days by the bucket rule, so the page shows "expired" after that. The 7 days is measured from `finished_at`.
7. **Email templates.** `export_ready` and `export_failed` are new. Their content and wording need to be decided.
8. **CSV format details.** The plan uses UTF-8, with escaping for formula-like fields. Whether to add a byte-order mark (for Excel) is not decided.
9. **Row count staleness.** `reports.row_count` is rewritten each night, so the 10,000 decision can be out of date for a report rebuilt that day. The brief accepts this, and the plan keeps it.