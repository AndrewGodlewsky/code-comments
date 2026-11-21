# CSV export for the reports page: implementation plan

## What this is

Today the reports page at `/reports/{report_id}` shows one report as a table with infinite scroll. It loads rows from `GET /api/reports/{id}/rows`, which reads them from the read replica. Filters and column order live only in the page URL. The server stores nothing about the view.

This plan adds a **Download CSV** button that exports what the user sees. A report of 10,000 rows or fewer downloads at once, straight from the click. A larger report is built by a background job. The job writes the file to the `exports` bucket and emails the user a link that works for 24 hours. The page shows the export's state while it runs and afterwards.

Out of scope: scheduled exports, formats other than CSV, and changes to the table on the page.

## Terms

- **Read replica:** a read-only copy of the database. Report rows are read only from it, never from the primary.
- **Primary:** the writable database. Export state lives here, so a user sees a new state at once.
- **row_id:** a number that is unique and increasing within a report. Reads page by it: "rows after the last one seen, in order" (keyset paging). Offsets are never used.
- **reports.row_count:** the total number of unfiltered rows. It is rewritten each night, so it can be stale.
- **report_exports:** a new table on the primary. It holds one row per large export.
- **Job queue:** runs a job on a worker with 512 MB of memory. An attempt fails if the job raises, runs past 30 minutes, or its worker dies. A job gets up to 3 attempts, waiting 60 s before attempt 2 and 300 s before attempt 3. The queue keeps no progress between attempts, so each attempt starts from the beginning. `on_final_failure` runs once, after the third failure. A job may run again after it has already succeeded.
- **Multipart upload:** storage builds one file from numbered parts. The file is not visible at its key until the upload completes. Every part except the last must be at least 5 MB. There can be at most 10,000 parts. `abort_multipart` discards the parts.
- **Signed URL:** a download link that expires. Here it lasts at most 24 hours.
- **Lifecycle rule:** the `exports` bucket deletes each object 7 days after creation. It also discards multipart uploads not completed within 24 hours. This plan builds no cleanup job.
- **Export status:** `queued` (job queued, no attempt started), `running` (an attempt is in progress or waiting to retry), `done`, or `failed`. The page also shows `expired` for a `done` export more than 7 days old. That is a display state only and is not stored.

## How the system runs

### 1. Click

- **Starts:** the user clicks Download CSV. The page sends `POST /api/reports/{id}/exports` with `filters` and `cols` from the page URL.
- **Does, in order:**
  1. Check `report.view` on the report's workspace. Return 403 if it is missing.
  2. Validate `filters` and `cols`. Return 400 for an unknown column or a malformed filter.
  3. Look for this user's active export of this report, meaning status `queued` or `running`. If one exists, run the stale checks below, then return it with 202 and the status panel. This runs before the size check, so one-at-a-time applies to every click.
  4. Read `reports.row_count` from the replica. At 10,000 or fewer, go to step 2. Above 10,000, go to step 3.
- **Keeps data:** nothing is stored in this step.
- **If it fails:** if the replica cannot be reached, return 503 and store nothing. A repeated click is always safe.
- **Stale checks** (run whenever step 3 finds an active row):
  - A `queued` row with no `job_id`, and `updated_at` more than 10 minutes old, means the process died between insert and enqueue. Enqueue it again and store the `job_id`.
  - A `running` row with `updated_at` more than 2 hours old means its final-failure handler never finished. Mark it `failed` and let the new click go ahead. Two hours covers the whole retry window: three 30-minute attempts plus 6 minutes of waits, about 96 minutes.

### 2. Sync CSV (10,000 rows or fewer)

- **Starts:** step 1 routes here.
- **Does:** read keyset pages of 500 rows from the replica. Write the header row first, then each row, with columns in `cols` order. Keep the whole CSV in memory. Send nothing until the scan finishes. The reply is `200` with `Content-Type: text/csv`, `Content-Disposition: attachment`, and a name such as `{report}-{date}.csv`.
- **Keeps data:** nothing. No job and no `report_exports` row.
- **Overflow:** if the scan reaches row 10,001, the stored count was stale. Discard the buffer, which was never sent, and go to step 3. The reply is then `202`.
- **If it fails:** a replica error during the scan returns 503 with no body. The browser never saves a truncated file, and the user clicks again. Holding the full CSV until the end is what makes this safe.

### 3. Large export: create the row and queue the job (more than 10,000 rows)

- **Starts:** step 1, or the overflow from step 2.
- **Does:**
  1. Insert a `report_exports` row with status `queued`, the user, the report, `filters` and `cols`.
  2. Call `enqueue('build_report_csv', {export_id})`. The payload is only the id, far below the 64 KB limit.
  3. Store the returned `job_id` on the row.
  4. Return `202` with the export id and status.
- **Keeps data:** the row on the primary. A unique partial index allows only one `queued` or `running` row per user and report. If two clicks race, the second insert fails. That request reads and returns the row the first request created, and no second job is queued.
- **If it fails:** if `enqueue` throws, mark the row `failed` with the reason "could not queue" and return 503. If the process dies after the insert, the stale check in step 1 enqueues it later.

### 4. Build the file (one job attempt)

- **Starts:** the queue runs attempt 1 at once. Attempts 2 and 3 run after the 60 s and 300 s waits.
- **Does, in order:**
  1. Load the row from the primary. If it is `done` and the email was not sent, skip to the success email (last item). If it is `done` with the email sent, or it is `failed`, stop. This covers duplicate delivery. Otherwise set status `running`, `attempt` to this attempt, and `updated_at` to now.
  2. Check `report.view` for the row's user. If it is denied, raise, so the attempt fails.
  3. Start a multipart upload to `exports/{export_id}.csv`. Store its `upload_id` on the row.
  4. Write the header row. Then loop: read 5,000 rows from the replica after the last `row_id`, using a short query that releases its connection. Format the rows as CSV and append them to an in-memory buffer. When the buffer reaches 8 MB, upload it as the next part, keep its etag, and clear the buffer. The job reads through the shared query code from the refactor, not through the HTTP API.
  5. Upload the last buffer. It may be under 5 MB because it is the last part. A 900 MB file needs about 115 parts, well under 10,000.
  6. Complete the upload with all the etags. The file becomes visible at its key only now.
  7. Set status `done`, `object_key`, `completed_at`, and `upload_id` to null.
  8. Send the success email (step 6) and set `email_sent_at`.
- **Keeps data:** the row on the primary. The buffer and etags live only in worker memory. Uploaded parts stay in the bucket until the upload completes or is aborted. Peak memory is one 8 MB buffer plus one page of rows, far below 512 MB. The whole report is never held in memory.
- **If it fails:**
  - An exception after the upload starts calls `abort_multipart` and re-raises, so the queue retries. The row stays `running`.
  - A timeout at 30 minutes, or a dead worker, runs no code. The lifecycle rule discards the incomplete upload after 24 hours. The next attempt starts a new upload and overwrites `upload_id`.
  - If the success email fails after the row is `done`, the attempt raises. The retry skips straight to sending the email.
  - Nothing is visible at the key before step 6, so a half-written file can never be downloaded.

### 5. Final failure

- **Starts:** the queue calls `on_final_failure` once, after the third failed attempt. This includes timeouts and dead workers.
- **Does:** if `upload_id` is set, abort the upload. Set status `failed`, a short `error` reason, and `updated_at`. Then send the failure email (step 6).
- **Keeps data:** the row is `failed`. Any partial upload is aborted, or left for the lifecycle rule.
- **If it fails:** the row stays `running`. The stale check in step 1 marks it `failed` after 2 hours, so the user is not blocked for long. If the failure email cannot be sent, log the error, record it, and leave the row `failed`.

### 6. Emails

- **Starts:** the success item in step 4, or the final failure in step 5.
- **Does:**
  - Success: `send_email(user_id, 'export_ready', {report_name, download_url, expires_at})`. `download_url` is `signed_url(exports, object_key, 86400)`, created when the email is sent, so it works for 24 hours.
  - Failure: `send_email(user_id, 'export_failed', {report_name, export_id})`.
  - Two new email templates are needed.
- **Keeps data:** `email_sent_at` on the row prevents a second success email.
- **If it fails:** on success, the attempt raises and the retry sends only the email. Never log the download URL.

### 7. Status and download endpoints

- **Starts:** the page's load, its polling, and its Download button.
- **Does:**
  - `GET /api/reports/{id}/exports/latest` returns the caller's most recent export for this report, read from the primary. It includes `status`, `attempt` and timestamps. It includes a download link only when `done`. It sets `expired: true` when `done` and `completed_at` is more than 7 days ago. It checks `report.view`.
  - `GET /api/reports/{id}/exports/{export_id}/download` checks that the caller owns the export and still has `report.view`. It then issues a fresh signed URL valid for 24 hours and redirects to it. A new link is issued on every click, so the page link still works after the emailed link expires. It returns 410 when the object is past 7 days.
- **Keeps data:** nothing beyond the row. No CSV passes through the API.
- **If it fails:** an export that belongs to another user returns 404, so existence is not revealed.

### 8. Page

- **Starts:** page load, the Download click, and polling.
- **Does:**
  - On load, call `latest`. If the status is `queued` or `running`, show a status panel (for example "attempt 2 of 3") and poll every 5 s until `done` or `failed`. Stop polling when the page is hidden or left.
  - `done` shows a Download button. `failed` shows the reason and a button that starts a new export. `expired` shows "expired, export again".
  - The Download CSV click sends the POST from step 1. If the reply is `text/csv`, save the blob. If it is `202`, show the status panel.
  - The table itself is unchanged. Filters stay only in the URL.
- **Keeps data:** nothing in the browser beyond what is shown.
- **If it fails:** a failed poll keeps the last state shown, displays "Could not check status", and retries the poll.

## Build and rollout

1. **Move the query code first.** Move the parsing and SQL out of the page's API handler into one module. The page, the sync path and the job all call it. `filters` and `cols` become a validated query spec. Column names are checked against the report's allowed columns, and raw text never goes into SQL. The keyset query is `row_id > :after ORDER BY row_id LIMIT :n` on the replica. If the existing page tests fail, revert this change before anything else starts.
2. **Create the `report_exports` table on the primary.** Columns: `id`, `user_id`, `report_id`, `workspace_id`, `filters` and `cols` (normalised from the URL), `status`, `job_id` (nullable), `attempt` (last attempt started), `upload_id` (nullable), `object_key` (`exports/{id}.csv`), `error` (short, nullable), `email_sent_at` (nullable), `created_at`, `updated_at`, `completed_at`. Add a unique partial index on `(user_id, report_id) WHERE status IN ('queued','running')`. The migration runs before any code that uses the table. If it fails, nothing changes. The table can be dropped and the migration re-run.
3. **Measure before enabling the large path.** Run the job against the 2-million-row report with the widest column set. Use a worker with the real 512 MB limit and the real replica. Record the wall-clock time and peak memory in the team's notes. Pass: the full run, including upload, takes under 900 s (half the 1,800 s attempt limit), and peak memory is under 256 MB. If time fails, first tune the query page size and the part size. If it still fails, add checkpoints. After each successful part, store the last `row_id`, the `upload_id` and the etags on the row. A retry then resumes from there and completes the upload with all the etags. Build checkpoints only if this gate fails.
4. **Release in two stages.** Release the sync path first. Enable the large path behind a flag only after the gate passes.

### Tests

- Boundaries: 10,000 rows goes to the sync path, 10,001 goes to the large path, and a stale count that overflows goes to the large path.
- The sync CSV and the large-path CSV are byte-identical for the same filters on a fixture report.
- Two concurrent clicks create one row and one job.
- Permission is denied both at the click and at the start of the job.
- A failure injected at part 3 leaves no object at the key, and `abort_multipart` is called.
- A duplicate delivery of a finished job completes once and sends one email.
- The job's queries use the replica connection. The primary is never queried for report rows.
- Memory stays bounded on a large synthetic report.
- The stale checks fire at their thresholds: 10 minutes for `queued`, 2 hours for `running`.

## Open questions for the product owner

1. **Filters on an in-flight export.** A click returns the running export even when its filters differ. Should the page show that export's filters, or block the click with a message?
2. **Nightly rebuild during an export.** The file can mix two data versions. Either fail the attempt when the report's data version changes (this needs a version field), or do not start large exports during the rebuild window.
3. **Bearer links.** Anyone with the emailed link can download the file for 24 hours. Is that acceptable?
4. **Revoked permission.** Permission is checked only at the start of each attempt. Is that enough?
5. **CSV formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in spreadsheet programs. Values are left unchanged unless the team decides to prefix them.
6. **Retention.** `report_exports` rows are kept indefinitely, since no cleanup job is planned. Is that acceptable?
7. **Concurrency.** Many large exports at once would load the replica and occupy workers. Should there be a cap?