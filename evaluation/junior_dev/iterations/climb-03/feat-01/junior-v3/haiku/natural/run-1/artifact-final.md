# Plan: CSV export for the reports page

The reports page gets a **Download CSV** button. The server checks permission and the report's size. A report of 10,000 rows or fewer comes back as a CSV in the same response. A larger report is built by a background job that writes the file to the `exports` bucket and emails the user a download link that works for 24 hours. The page shows the export's status while it builds.

## Terms

- **Primary database**: the read-write database. Export records are written here.
- **Read replica**: a read-only copy. Report rows are read only from here.
- **Keyset paging**: each page asks for rows with `row_id` greater than the last `row_id` seen, ordered by `row_id`, with a limit. Never OFFSET.
- **Job queue**: runs a handler on a worker. Each attempt has a 30-minute timeout. A failed attempt is retried after 60 s, then after 300 s, up to 3 attempts in total. Each attempt starts from scratch with the same payload. A job can run twice, so handlers must tolerate that. After the third failed attempt, the queue calls the final-failure handler once. No code runs between attempts.
- **Multipart upload**: a file is uploaded in parts. Nothing is visible at its key until the upload is completed. Aborting discards the parts. Every part except the last must be at least 5 MB. At most 10,000 parts are allowed.
- **Export record**: one row per export in the `report_exports` table on the primary database. It holds state, never report rows.
- **Stale row**: a `queued` export with no `job_id` that was created more than 5 minutes ago. The server stopped after inserting it and before saving the job id, so no job is coming for it.

## Steps

1. **Create the table (at deploy).** A migration adds `report_exports` with these columns: `export_id` (primary key), `user_id`, `report_id`, `filters` and `cols` (copied from the page URL), `status` (`queued`, `running`, `done` or `failed`), `job_id`, `attempt`, `upload_id`, `object_key`, `email_sent_at`, `error`, `created_at`, `updated_at` and `completed_at`. It also adds a partial unique index on `(user_id, report_id)` where `status` is `queued` or `running`, so two clicks cannot both create an active export. If the migration fails, the deploy stops.

2. **Shared row reader and CSV writer (code change, before the feature).** One function takes `report_id`, `filters`, `cols` and a starting `row_id`. It yields pages of 500 rows read from the replica by keyset paging, and never builds a list of all rows. A second function turns one row into one CSV line (RFC 4180 quoting, UTF-8). A header line is built from `cols`. The existing rows API uses the same filter and column parsing, and its response does not change. If the replica is unavailable, the request returns 503. Nothing is written.

3. **Click, and choose the path.** The page sends `POST /api/reports/{report_id}/exports` with the current `filters` and `cols`. The server checks `report.view` on the report's workspace and returns 403 if the check fails. It reads `reports.row_count` from the replica. This is the unfiltered total. If the count is 10,000 or fewer, go to step 4. Otherwise go to step 5. If this read fails, return 503 and the page shows a retry message.

4. **Small path: stream the CSV.** Rows are read in pages of 500 through the step 2 reader. Each page is written to the response as CSV lines, so only one page is held at a time. Headers: `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. No job is created and no file is stored. The API kills any request that runs longer than 60 seconds, so the time for 10,000 rows must be measured. The permission check from step 3 applies to this request even if the permission is revoked during the stream.

5. **Large path: record the export and queue the job.**
   - Start a transaction and look for this user's export for this report with status `queued` or `running`.
   - If one exists and is stale, set it to `failed` with `error = "could not queue"`. Only rows still `queued` are changed, so one click wins. Doing this before the insert frees the unique index for the new row. Then continue with the next item.
   - If one exists and is not stale, return it (skip to the last item).
   - Otherwise insert a row with status `queued`. If the insert hits the unique index, another click won the race. Read the winning row and return it. This click enqueues nothing.
   - After the insert commits, call `enqueue("export_report", {"export_id": ...})`.
   - Save the returned `job_id` with an update that writes only that column. The worker never reads or writes `job_id`.
   - Return HTTP 202 with the returned export's `export_id`, `status`, `filters` and `cols`.

   A click while an export is `queued` or `running` gets that export back, even if its filters differ from the page's. A new export starts only after the old one is `done` or `failed`, or is stale and so marked `failed`. If `enqueue` raises, set the row to `failed` with `error = "could not queue"` and return 503. The user can click again. If the server crashes after the insert and before `job_id` is saved, the row is a stale row.

6. **Job attempt: checks, then start.** The queue runs `export_report` with payload `{"export_id": ...}` and a context holding `job_id` and `attempt` (1, 2 or 3). The handler reads the export row from the primary, with its user, report, filters and columns. It then checks, in this order:
   - If the row is `failed`, return. Nothing is left to do.
   - If the row is `done` and `email_sent_at` is set, return. This is a duplicate delivery.
   - If the row is `done` but `email_sent_at` is empty, go to step 9. Do not rebuild the file.
   - Otherwise re-check `report.view` for the user. If the check fails, raise. The queue retries, and the last attempt is handled by step 10.
   - Set `status = running`, `attempt = ctx.attempt` and `updated_at = now`. A `running` status left by an earlier attempt that timed out or died is overwritten here.

   An exception in this step is a normal attempt failure. Between attempts the row keeps the status it already has. The page shows "attempt N of 3", where N is the last attempt that started. The unique index keeps blocking new clicks during retries.

7. **Build the file in parts.**
   - Start a multipart upload to the `exports` bucket at key `reports/{report_id}/exports/{export_id}-attempt{attempt}.csv`. Save the returned `upload_id` on the row before any part is uploaded. A new attempt replaces the saved `upload_id`.
   - Read a page of 500 rows from the replica and write its CSV lines into a 16 MB buffer. Continue from the last `row_id` until all rows are read.
   - When the buffer reaches 16 MB, upload it as the next part. Keep only the returned etag, and clear the buffer.
   - After the last page, upload what remains as the last part.

   Memory use is one page, one 16 MB buffer and a list of etags, well inside 512 MB. About 900 MB of CSV is about 57 parts, far under the limit. The whole build must finish inside one 30-minute attempt.
   If the handler raises, abort the upload as a best effort, then raise. If the worker dies or the attempt times out, no code runs. The parts stay until the bucket's 24-hour rule discards them. The next attempt starts a new upload. Nothing can be downloaded until step 8.

8. **Make the file visible.**
   - Complete the multipart upload with all etags. The object becomes visible at its key.
   - Update the row: `object_key = key`, `status = done`, `completed_at = now`, `upload_id = null`.

   If completing the upload raises, nothing is visible. Abort the upload as a best effort and raise. If the row update raises after the upload was completed, the object is visible but the row is not `done`. Do not abort the completed upload. Raise. The row stays `running` with the completed `upload_id`. The next attempt overwrites `upload_id` before it uploads any part. If this was the last attempt, step 10 tries to abort the completed upload, ignores any error, and marks the export failed. The orphaned object expires after 7 days.

9. **Email the link.**
   - Generate a download URL for `object_key` that lasts 86,400 seconds (24 hours).
   - Call `send_email(user_id, "export_ready", {"download_url": url, "report_id": ..., "export_id": ...})`.
   - On success, set `email_sent_at = now`.

   If `send_email` raises, the attempt raises. The next attempt sees `done` without `email_sent_at` (step 6), sends the email again, and does not rebuild the file. Known gap: if the email is delivered but the process dies before `email_sent_at` is saved, the user gets the link twice. This is accepted, because email delivery cannot be made atomic with the database write.

10. **Final failure.** The queue calls the final-failure handler once, after the third failed attempt. It receives `export_id` and the queue's error for that attempt.
    - Read the export row from the primary. It gives `user_id`, `report_id`, `status` and `upload_id`.
    - If the row is `done`, stop. An earlier attempt finished the file, so it stays `done`. An export that is `done` but whose email failed on every attempt gets no failure email, and the page keeps showing Download.
    - Otherwise run a conditional update, only where `status` is not `done`, that sets `status = failed`, `error` to the queue's error text cut to 500 characters, and `updated_at = now`. Do this first, so the page shows the failure even if the steps after it fail.
    - If `upload_id` is set, abort that upload as a best effort and ignore any error.
    - Call `send_email(user_id, "export_failed", {"report_id": ..., "export_id": ...})`. If this fails, log it. The page still shows the export as failed.

11. **Status on the page.** When the page loads, or the user returns to the report, it calls `GET /api/reports/{report_id}/exports/latest`. The server checks `report.view` and returns the newest export for this user and report, read from the primary. The "requested" time is `created_at`. The page shows:
    - `queued`: "Queued", with the request time.
    - `running`: "Building file, attempt N of 3", using `attempt`.
    - `done`: a **Download** button. Each `latest` call returns a new signed URL that lasts 24 hours. If `completed_at` is more than 7 days ago, the file has been deleted, so the page shows "Expired, export again".
    - `failed`: "Export failed", with a **Try again** button that starts step 5.

    A stale row is shown as `failed`. Loading the page does not change the row. Only **Try again** changes it, because step 5 marks it `failed` before inserting the new export. While the state is `queued` or `running`, the page calls `latest` every 5 seconds and stops at `done` or `failed`. If a call fails, the page keeps the last known state and shows a retry message.

12. **Button front end.** When the user clicks **Download CSV**, the page sends the step 3 request.
    - If the response is `text/csv`, the page reads the whole body and saves it only after the body finishes (step 4). A cut-off body makes `fetch` throw, so nothing is saved and the user can click again.
    - If the response is JSON with status 202, the page shows the export panel (step 11).
    - A network error or a 503 shows a message, and the button can be pressed again.

**Rollout:** ship behind a feature flag. Enable it for internal users first, and watch job duration and failure counts before enabling it for everyone.

**Retention:** the `exports` bucket's rules delete each object 7 days after creation and discard uploads not completed within 24 hours. Export rows are kept, because they are small and the status page needs them. No cleanup job is built.

## Open questions

1. **Threshold uses the unfiltered total.** A filter that leaves 50 rows of a 2-million-row report still takes the large path. Should the server count filtered rows, or accept the cost?
2. **`row_count` can be stale.** It is rebuilt nightly, so a report that grew past 10,000 rows during the day can take the small path and run past 60 seconds. Options: a time check that returns an error before the response starts, or a count query on the replica before streaming.
3. **Time budget for the job.** Every attempt starts from scratch. If the 2-million-row build takes more than 30 minutes, all three attempts fail the same way. Fallbacks if this is too slow: (a) larger pages in the job only; (b) parallel part uploads with at most about 4 parts in memory; (c) saving the upload ID, each part's etag and the last `row_id` on the export row, so a later attempt can resume. Option (c) goes against the queue's design and needs a decision.
4. **Column headers.** Should the CSV header use the column ids from the URL (`customer`) or the labels the page shows (`Customer name`)?
5. **Excel and formulas.** Should the file start with a UTF-8 byte-order mark for Excel? Should cells starting with `=`, `+`, `-` or `@` get an apostrophe prefix, to block formula injection? The plan assumes yes to both. Needs confirmation.
6. **Repeated click with different filters.** The plan returns the active export, which may use other filters. Is that acceptable, or should the server return 409 so the page can say so?
7. **Email templates.** The plan assumes `export_ready` and `export_failed` exist or will be created. Check the names that `send_email` uses.
8. **Link exposure.** The download link is a bearer link. Anyone who gets it can download the file for 24 hours. This matches the brief, but the product owner should be told.
9. **Empty `cols`.** If the URL has no `cols`, does the page show all columns in a default order? The export must use the same default.
10. **Primary or replica for permission checks and the count.** The existing files do not say whether the `report.view` checks (steps 3, 6 and 11) and the `row_count` read use the primary or the replica. The plan follows the page API's path, which is not confirmed.