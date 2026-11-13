# CSV export for the reports page: implementation plan

## Terms

- **Row and row_id.** A report's data is in the `report_rows` table. Each row has a `row_id` that increases within its report.
- **Read replica.** A read-only copy of the database. Report rows are read only from it. The primary is the writable database.
- **Export state.** Our own bookkeeping about exports. It is not report data, so it lives on the primary. A user who clicks must see the state at once, and replica lag would delay that.
- **Job queue (`jobs.py`).** Runs a handler on a worker with 512 MB of memory. An attempt fails if the handler raises, if it passes 30 minutes, or if its worker dies. A job gets up to 3 attempts, with waits of 60 s and 300 s before attempts 2 and 3. `on_final_failure` runs once, after the third failure. The queue keeps no progress between attempts.
- **Multipart upload.** Object storage builds one file from numbered parts. Nothing is visible at the key until `complete_multipart` succeeds. `abort_multipart` discards the parts. Every part except the last must be at least 5 MB, and there can be at most 10,000 parts.
- **Signed URL.** A download link that expires. Here it may last at most 24 hours.
- **Lifecycle rule.** The `exports` bucket deletes each object 7 days after creation. It discards incomplete multipart uploads after 24 hours.

## Decisions this plan makes

- A new table, `report_exports`, on the primary holds the state of each export (schema below).
- The job reads its inputs from that row. Its queue payload is only `{export_id}`, far below the 64 KB limit.
- The job reads the replica directly through the shared query code from Step 1. It does not call the HTTP API, which returns at most 500 rows per page and is killed after 60 s.
- Status values are `queued` (enqueued, no attempt started yet), `running` (an attempt is in progress, including a wait before a retry, and the page shows "attempt 2 of 3"), `done`, and `failed`. The page also shows `expired` for a `done` export older than 7 days. That is a display state only.

`report_exports` columns: `id` (export id), `user_id`, `report_id`, `workspace_id`, `filters` and `cols` (normalised values from the URL), `status`, `job_id` (nullable, set after enqueue), `attempt` (last attempt started), `upload_id` (nullable, current multipart upload), `object_key` (`exports/{id}.csv`), `error` (short reason, nullable), `email_sent_at` (nullable), and `created_at`, `updated_at`, `completed_at`.

A unique partial index on `(user_id, report_id) WHERE status IN ('queued','running')` (or the database's equivalent) allows at most one active large export per user and report.

## Steps

### 1. Share the view-state query code

- **Starts:** This is the first code change, before any export code. It moves the parsing and SQL out of the page's API handler into a module the page, the sync path and the job all call.
- **Data:** The URL values `filters` and `cols` become a validated query spec. The keyset query is `row_id > :after ORDER BY row_id LIMIT :n` against the replica. Column names are checked against the report's allowed columns. Raw text is never placed into SQL.
- **State:** None new.
- **Failure:** An unknown column or a malformed filter returns 400 from the page API and from the export endpoint. If the refactor breaks the page, the existing page tests catch it and the change is reverted before anything else starts.

### 2. Create the `report_exports` table

- **Starts:** The migration runs on the primary before the code that uses it is deployed.
- **Data:** None moved.
- **State:** The table and the partial unique index above.
- **Failure:** If the migration fails, nothing changes. The table can be dropped and the migration re-run.

### 3. Handle the Download CSV click

- **Starts:** The user clicks. The page sends `POST /api/reports/{id}/exports`, with `filters` and `cols` from the page URL.
- **Data and checks, in order:**
  1. Check `report.view` on the report's workspace. Return 403 if it is missing.
  2. Validate the parameters with Step 1. Return 400 on failure.
  3. Look for this user's active large export of this report (`queued`, or `running` with no stale guard firing, see Step 5). If one exists, return it with 202 and the status panel. This runs before the size check, so one-at-a-time applies to every click.
  4. Read `reports.row_count` from the replica. It is the unfiltered total and is rewritten nightly. If it is 10,000 or fewer, go to Step 4. Otherwise go to Step 5.
- **State:** Nothing stored in this step.
- **Failure:** If the replica is unreachable, return 503 and store nothing. A repeated click is always safe.

### 4. Sync path (10,000 rows or fewer)

- **Starts:** Step 3 routes here.
- **Data:** Read keyset pages of 500 rows from the replica. Write the header row first, then each row, with columns in the order of `cols`. Hold the whole CSV in memory, capped at 10,000 rows (a few MB), and send nothing until the scan is complete. The response is `200` with `Content-Type: text/csv` and `Content-Disposition: attachment` and a name such as `{report}-{date}.csv`.
- **State:** Nothing is stored. There is no job and no `report_exports` row.
- **Overflow:** If the scan reaches row 10,001, the stored count was stale. Discard the buffer, which has not been sent, and go to Step 5. The response is then `202`.
- **Failure:** A replica error during the scan returns 503 with no body, so the browser never saves a truncated file. The user clicks again. Holding the full CSV until the end is what makes this safe.

### 5. Large path: create the export and enqueue the job

- **Starts:** Step 3 routes here, either from the size check or from Step 4's overflow.
- **Data:**
  1. In one step, insert a `report_exports` row with status `queued` and the user, report, `filters` and `cols`.
  2. Call `enqueue('build_report_csv', {export_id})`.
  3. Store the returned `job_id` on the row.
  4. Return `202` with the export id and status.
- **State:** The row lives on the primary. Concurrent clicks are safe. The second insert fails the unique index, and that request reads and returns the row the first request created. It does not enqueue a second job.
- **Stale guard (runs on every click that finds an active row):** If the row is `queued` with `job_id` empty and `updated_at` more than 10 minutes old, the earlier process died between insert and enqueue. Enqueue it again and store the `job_id`. If the row is `running` and `updated_at` is more than 2 hours old, its final-failure handler never completed. Mark it `failed` and let the new click proceed. Two hours covers the whole retry window: three 30-minute attempts plus 6 minutes of waits, about 96 minutes.
- **Failure:** If `enqueue` throws, mark the row `failed` with the reason "could not queue" and return 503.

### 6. Job attempt: `build_report_csv(ctx, payload)`

- **Starts:** The queue runs attempt 1 at once. Attempts 2 and 3 run after the 60 s and 300 s waits.
- **Data, in order:**
  - **a.** Load the row from the primary. If it is `done` and `email_sent_at` is empty, go to step h only. If it is `done` and the email was sent, or it is `failed`, return. This covers duplicate delivery. Otherwise set `status = running`, `attempt = ctx.attempt`, and `updated_at = now`.
  - **b.** Re-check `report.view` for the row's user. If it is denied, raise, so the attempt fails.
  - **c.** Call `start_multipart(exports, exports/{export_id}.csv)` and store the `upload_id` on the row.
  - **d.** Write the header row. Then loop: read 5,000 rows from the replica with keyset (`row_id > last`), each read a short query whose connection is released afterwards. Format them as CSV and append to an in-memory buffer. When the buffer reaches 8 MB, call `upload_part(n)` and keep the returned etag. Then clear the buffer. Peak memory is one 8 MB buffer plus one page, far below 512 MB. Holding the full report is never needed.
  - **e.** Upload the last buffer. It may be under 5 MB because it is the last part. A 900 MB file needs about 115 parts, well under 10,000.
  - **f.** Call `complete_multipart(upload_id, etags)`. The object becomes visible at its key only now.
  - **g.** Set `status = done`, `object_key`, `completed_at`, and `upload_id = null`.
  - **h.** Send the `export_ready` email (Step 8) and set `email_sent_at`.
- **State:** The row is on the primary. The buffer and etags live only in worker memory. Uploaded parts sit in the bucket until the upload completes or is aborted.
- **Failure:**
  - An exception in steps c to f calls `abort_multipart(upload_id)` and re-raises, so the queue retries. The row stays `running`.
  - A timeout at 30 minutes or a dead worker runs no code. The incomplete upload is discarded by the 24-hour lifecycle rule. The next attempt starts a new upload and overwrites `upload_id` on the row.
  - Nothing is visible at the key until step f, so a half-written file can never be downloaded.
  - If the email in step h fails after `done`, the attempt raises and the retry takes the step a path to send only the email.

### 7. Measure before release (gate)

- **Starts:** Before the large path is enabled for users.
- **Data:** Run the job against the 2-million-row report with the widest column set. Use a worker with the real 512 MB limit and the real replica. Record the wall-clock time and peak memory.
- **Pass:** The full run, including upload, takes under 900 s, which is half the 1,800 s attempt limit. Peak memory is under 256 MB.
- **Fail:** First tune the query page size and part size. If it still fails the time limit, add checkpoints. After each successful part, store the last `row_id`, the `upload_id`, and the etags on the row. A retry then resumes from there and completes the upload with all etags. Open uploads last 24 hours, so this fits the 60 s and 300 s retry waits. Checkpoints are not built unless this gate fails.
- **State:** The benchmark results are recorded in the team's notes.

### 8. Emails on success and failure

- **Starts:** Step 6h on success. Step 9 on final failure.
- **Data:**
  - Success: `send_email(user_id, 'export_ready', {report_name, download_url, expires_at})`. The `download_url` is `signed_url(exports, object_key, 86400)`, generated when the email is sent, so it works for 24 hours.
  - Failure: `send_email(user_id, 'export_failed', {report_name, export_id})`.
  - Two new email templates are needed.
- **State:** `email_sent_at` on the row prevents a duplicate success email.
- **Failure:** On the success path, a send error fails the attempt, and the retry sends only the email (Step 6a). On the failure path, log the error and record it. The page still shows `failed`. Never log the download URL.

### 9. Final failure

- **Starts:** The queue calls `on_final_failure(ctx, payload, error)` after the third attempt fails. This includes timeouts and dead workers.
- **Data:** If `upload_id` is set, call `abort_multipart`. Set `status = failed`, `error` to a short reason, and `updated_at`. Then send the failure email (Step 8).
- **State:** The row is `failed`. Any partial upload was aborted, or is left for the lifecycle rule.
- **Failure:** If this handler itself fails, the row stays `running`. The stale guard in Step 5 marks it `failed` after 2 hours, so the user is never blocked for long.

### 10. Status and download endpoints

- **Starts:** The page's load, its polling, and its Download button.
- **Data:**
  - `GET /api/reports/{id}/exports/latest` returns the caller's most recent export for this report from the primary. It includes `status`, `attempt`, and timestamps. A download link is included only when `done`. It returns `expired: true` when `done` and `completed_at` is more than 7 days ago. It checks `report.view`.
  - `GET /api/reports/{id}/exports/{export_id}/download` checks that the caller owns the export and still has `report.view`. It then issues a fresh `signed_url(..., 86400)` and redirects to it. It returns 410 when the object is past 7 days. A new link is issued on every click, so the page link works even after the email link has expired.
- **State:** None beyond the row. No CSV passes through the API.
- **Failure:** An export that belongs to another user returns 404, so existence is not revealed.

### 11. Page changes

- **Starts:** Page load, the Download click, and polling.
- **Data:**
  - On load, call `latest`. If the status is `queued` or `running`, show a status panel and poll every 5 s until `done` or `failed`. Stop polling when the page is hidden or left.
  - `done` shows a Download button that calls Step 10. `failed` shows the reason and a button that starts a new export. `expired` shows "expired, export again".
  - The Download CSV click sends Step 3's `POST`. If the response is `text/csv`, save the blob. If it is `202`, show the status panel.
  - The table itself is unchanged.
- **State:** Nothing in the browser beyond what is shown. Filters stay only in the URL.
- **Failure:** If a poll fails, keep the last state shown and show "Could not check status", then retry the poll.

### 12. Tests

- Boundaries: 10,000 rows goes to the sync path, 10,001 goes to the large path, and a stale `row_count` that overflows routes to the large path.
- The sync CSV and the large-path CSV are byte-identical for the same filters on a fixture report.
- Two concurrent clicks create one row and one job.
- Permission is denied both at the click and at the start of the job.
- A failure injected at part 3 leaves no object at the key, and `abort_multipart` is called.
- A duplicate delivery of a finished job completes once and sends one email.
- The job's queries go to the replica connection, and the primary is never queried for report rows.
- Memory stays bounded on a large synthetic report.
- The stale guards in Steps 5 and 9 fire at their thresholds.

### 13. Rollout

- Release the sync path first. Enable the large path behind a flag only after the Step 7 gate passes.

## Open questions for the product owner

1. **Different filters on an in-flight export.** Under the brief, a click returns the running export even when its filters differ. Should the page show that export's filters, or should it block the click with a message?
2. **Nightly rebuild during an export.** If the rebuild runs during a large export, the file can mix two data versions. Options: fail the attempt when the report's data version changes (this needs a version field), or do not start large exports during the rebuild window.
3. **Bearer links.** Anyone with the emailed link can download the file for 24 hours. Is that acceptable?
4. **Revoked permission.** The plan re-checks permission only at the start of each attempt. Is that enough?
5. **CSV formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas in spreadsheet programs. The plan leaves values unchanged unless the team decides to prefix them.
6. **Retention of rows.** `report_exports` rows are kept indefinitely, because the brief rules out a cleanup job. Confirm that this is acceptable.
7. **Concurrency.** Many large exports at once would load the replica and occupy workers. Should there be a cap?