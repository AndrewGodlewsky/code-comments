# CSV export for the reports page: implementation plan

## Summary

One endpoint decides the path by `reports.row_count`. At 10,000 rows or fewer, the click response is the CSV itself. Above 10,000, the endpoint records a row in a new `report_exports` table, enqueues a background job, and returns at once. The job writes the CSV in 16 MB parts to a multipart upload in the `exports` bucket, makes the file visible only when the upload is completed, and emails a 24-hour download link. The page polls the export's state until it is done or failed.

## Terms used

- **Read replica**: a copy of the primary database. Report rows are read only from it.
- **Keyset paging**: fetching the next page with `row_id > last_seen ORDER BY row_id LIMIT n`. It does not use OFFSET.
- **Multipart upload**: an object is uploaded in numbered parts. Nothing is visible at the object key until `complete_multipart` succeeds.
- **Attempt token (fence)**: a random ID created at the start of each job attempt and stored on the export row. Every later write to that row is applied only if the stored token still matches. This stops an old attempt from overwriting a newer one.
- **Heartbeat**: refreshing the row's `updated_at` as the job makes progress, so a stalled export can be detected.
- **Active export**: an export in state `queued` or `running`.

## Step 1: Measure before building

- **Starts**: a benchmark in a non-production environment, before any code is merged.
- **Data moves**: a test report of about 2 million rows is read with the same keyset query from a replica, written as CSV in 16 MB parts to a scratch key.
- **State**: none. Delete the scratch object afterwards.
- **Goal**: one full attempt finishes in under 20 minutes, which leaves a margin under the 1,800-second attempt timeout. Peak memory stays well under 512 MB. Also time a selective filter. If the filter columns are not indexed, each keyset page may scan far more rows than it returns.
- **On failure**: if the benchmark is over 20 minutes, stop. All three attempts would hit the same timeout, so the approach must change first. See Open Question 1.

## Step 2: Add the state table on the primary database

- **Starts**: the migration, run on deploy.
- **Table `report_exports`**:
  - `id` (UUID, also the export ID)
  - `user_id`, `report_id`
  - `filters`, `cols` (copied from the page URL after validation)
  - `state` (`queued`, `running`, `done` or `failed`)
  - `job_id`, `attempt`, `attempt_token`, `upload_id`, `object_key`
  - `error_message` (short and generic, with no internal detail)
  - `created_at`, `updated_at` (heartbeat), `completed_at`, `email_sent_at`
- **Constraint**: a partial unique index on `(user_id, report_id)` where `state` is `queued` or `running`. This enforces one active export per user per report, even when the button is double-clicked.
- **Why the primary**: this is our state, not report data. The replica rule covers report rows only.
- **On failure**: a failed migration is rolled back. Nothing depends on the table until Step 5.

## Step 3: The click endpoint and the path decision

- **Route**: `POST /api/reports/{report_id}/exports`. The body carries `filters` and `cols` copied from the page URL.
- **Starts**: the user clicks **Download CSV**.
- **Checks, in order**:
  1. The caller has `report.view` on the report's workspace. Otherwise return 403. This is the same check the page uses.
  2. Validate `filters` and `cols` against the report's columns. An unknown column returns 400. Reject a body over 8 KB.
  3. Read `reports.row_count` from the read replica.
  4. If `row_count` is 10,000 or less, go to Step 4. Otherwise go to Step 5.
- **Data moves**: only the request body and one count.
- **State**: none written by these checks.
- **On failure**: 403 or 400 leaves no state. If the count read fails, return 503. Nothing has started, so the user can retry.

## Step 4: Small export (10,000 rows or fewer)

- **Starts**: Step 3 chose the small path.
- **Data moves**: report rows are read from the replica in keyset pages of 500, the same size the page uses, in `row_id` order with the URL's filters. The header row lists the `cols` in URL order. Each row is written as an RFC 4180 CSV line: fields with commas, quotes or newlines are quoted, and quotes are doubled.
- **Buffering**: build the complete CSV in memory, then send it with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`. Do not stream it. A stream that fails midway looks like a complete file to the user but is truncated. A buffered response returns an error instead. At 10,000 rows the buffer is small. Confirm this with the widest realistic row in the Step 1 benchmark.
- **State**: none. No row, no job, nothing stored.
- **On failure**: if the read runs past the API's 60-second kill limit, or fails, the request returns an error. The user retries. No file is produced and nothing is left behind.

## Step 5: Large export: create or return the active one

- **Starts**: Step 3 chose the large path, meaning `row_count` is above 10,000.
- **Procedure**:
  1. Look for an active export for this user and report. If one exists and is not stale (Step 11), return it with `already_running: true`, together with its filters and columns. Stop here.
  2. Insert a row with `state = queued` and `job_id` empty. If the insert hits the unique index because a concurrent click won, read the winning row and return it.
  3. Call `enqueue("report_export", {"export_id": <id>})`. The payload is only the ID, far under the 64 KB limit. The job reads filters and columns from the row.
  4. Store the returned `job_id` on the row. Return 202 with the export ID and state `queued`.
- **Data moves**: one row written to the primary.
- **On failure**:
  - If `enqueue` raises, mark the row `failed` with "could not start" and return 503. The user can click again.
  - If the process dies after the insert and before the enqueue, the row stays `queued` with no `job_id`. Step 11 recovers it.
  - Concurrent clicks cannot create two active rows, because of the index in Step 2.

## Step 6: Job attempt start

- **Starts**: the queue runs `report_export(ctx, payload)` with `ctx.attempt` set to 1, 2 or 3.
- **Procedure**:
  1. Load the row by `payload.export_id`. If the row is missing, or its state is `done` or `failed`, return without doing anything. `done` is the at-least-once case. `failed` means Step 11 or the final failure has already ended this export.
  2. Create a new `attempt_token`. Set `attempt = ctx.attempt`, `state = running` and `updated_at = now`. The update applies only if the state is still `queued` or `running`.
  3. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it. This is best effort: log any error and continue. Clear `upload_id`.
  4. Start a multipart upload to the key `report-exports/{report_id}/{export_id}/{attempt_token}.csv` in the `exports` bucket. Save the returned `upload_id` on the row. The token in the key means no attempt can overwrite another attempt's file.
- **Data moves**: a few small writes to the row.
- **State**: the row holds `attempt`, `attempt_token` and `upload_id`.
- **On failure**: if the state update or the upload start fails, the attempt raises and the queue retries it. A failed abort is ignored, because the bucket's lifecycle rule discards unfinished uploads after 24 hours anyway.

## Step 7: Stream rows into the upload

- **Starts**: Step 6 succeeded.
- **Data moves**:
  - Read report rows from the replica in pages of 5,000, using `row_id > last ORDER BY row_id LIMIT 5000` with the row's filters.
  - Convert each row to a CSV line with the same quoting rules as Step 4. The header row goes first.
  - Append the lines to one in-memory part buffer. When it reaches 16 MB, call `upload_part(upload_id, part_number, bytes)` and keep the returned etag in a list. The final part may be smaller, which the storage rules allow.
- **Memory**: one 16 MB buffer, one 5,000-row page and a list of etags, which is about 57 short strings for 900 MB. This stays far under 512 MB. The whole report is never held in memory. The 2-million-row report is about 900 MB and needs about 57 parts, well under the 10,000-part limit.
- **Heartbeat**: after each part, set `updated_at = now`, but only while the token still matches.
- **Snapshot check**: read `reports.row_count` at the start and at the end of the attempt. If it changed, the nightly rebuild ran during the export and pages may mix two snapshots. Raise an error so the queue retries. This is a proposal, because no version column exists today. See Open Question 2.
- **State**: no progress is saved. A retry starts again from row zero.
- **On failure**:
  - A replica query error or timeout, or an `upload_part` error, makes the attempt raise. The queue waits 60 seconds before attempt 2, or 300 seconds before attempt 3, then runs the handler again from the start.
  - An attempt killed at the 1,800-second limit is handled the same way.
  - A worker crash is handled the same way.
  - In every case the object key stays empty, so no partial file can be downloaded. The next attempt's Step 6 aborts the abandoned upload.

## Step 8: Finish the file and tell the user

- **Starts**: every row has been uploaded as a part.
- **Procedure**:
  1. Call `complete_multipart(upload_id, etags)`. This is the only moment the file appears at its key.
  2. Run a fenced update: `state = done`, `object_key`, `completed_at = now`, `upload_id` cleared. It applies only if the token still matches and the state is `running`. If no row changes, this attempt was superseded. Stop here and send no email.
  3. Call `send_email(user_id, "report_export_ready", {report_id, download_url, expires_at})`, where `download_url = signed_url("exports", object_key, 86400)`. On success, set `email_sent_at`.
- **Order**: the row is marked `done` before the email is sent, so the page shows the export as done even if the email fails.
- **On failure**:
  - If `complete_multipart` fails, the attempt raises and retries. Nothing became visible.
  - If the fenced update changes no rows, stop without sending email.
  - If the email fails after the row is `done`, the attempt raises and the queue retries. The handler then sees `done` with `email_sent_at` empty, and only resends the email. It does not export again. A duplicate email is possible if the send succeeds but writing `email_sent_at` fails. That is acceptable.
  - If the email still fails on the last attempt, `on_final_failure` runs. It must not mark the export failed (Step 9).

## Step 9: Failure on each attempt, and final failure

- **Each failed attempt**: the handler wraps its body in a try block. On an exception, it writes a short `error_message` to the row, conditional on the token, and then re-raises. The row stays `running` with its attempt number and `updated_at`. The page shows "running, attempt N of 3".
- **`on_final_failure(ctx, payload, error)`**, called once after the third attempt fails:
  1. Run a conditional update to `state = failed` with a generic `error_message` such as "The export could not be built. Try again." The update applies only if the state is `queued` or `running`. A `done` export is never marked failed.
  2. Abort the row's `upload_id`, if one exists. This is best effort.
  3. Call `send_email(user_id, "report_export_failed", {report_id})`. Catch and log any error, so the row stays `failed` even if the email does not send.
- **If `on_final_failure` itself fails**: the row stays `running`. Step 11 marks it failed later.

## Step 10: Status endpoint and the page

- **Endpoint**: `GET /api/reports/{report_id}/exports/latest`.
  - Checks `report.view`.
  - Returns the newest row for this user and report. The response has `state`, `attempt`, the filters and columns it was started with, and the generic `error_message`.
  - If the state is `done` and `completed_at` is within 7 days, it also returns a fresh signed URL valid for 24 hours. The URL is generated on each request and is not stored.
  - Reads the primary, because this is our state, not report data.
- **Page behaviour**:
  - On load, fetch the latest export.
  - `queued` or `running`: show the state and attempt number. Poll every 5 seconds, then every 30 seconds after the first 2 minutes. Stop polling on `done` or `failed`.
  - `done`: show a Download button that fetches a fresh link.
  - `failed`: show the message and a Try again button, which calls Step 3.
  - If the latest export's filters differ from the current URL, say so on the page.
  - After 7 days the object is removed by the lifecycle rule. Show "expired, export again".
- **On failure**: if the status request fails, the page shows "status unavailable" and keeps the last known state. It never starts an export.

## Step 11: Stale exports

- **Starts**: any Step 5 click, and any Step 10 status request.
- **Rule**: an active row is stale when either of these holds:
  - `state = running` and `updated_at` is more than 45 minutes old. The 45 minutes is the 30-minute attempt timeout, plus the longest backoff of 5 minutes, plus a margin.
  - `state = queued`, `job_id` is empty, and `updated_at` is more than 5 minutes old. This happens when the process died between the insert and the enqueue.
- **Action**: a conditional update sets the row to `failed` with "The export stopped unexpectedly. Try again." If the queue still holds a scheduled retry for that export, it exits at Step 6 because the state is `failed`.
- **On failure**: if the update fails, the click returns the existing row. It does not start a second export.

## Step 12: Tests and rollout

Automated tests:

- Without `report.view`, `POST` and `GET latest` return 403 and create no row.
- A `row_count` of 10,000 takes the small path. A `row_count` of 10,001 takes the large path.
- The small-path response matches the CSV from the same query. The header order follows `cols`. Commas, quotes and newlines are quoted correctly.
- The large-path output for the same query matches the small-path output for a fixture of about 25,000 rows. Use a small part size in the test so several parts are exercised.
- Two concurrent clicks create one row, and both receive the same export.
- Running the job again after success creates no second row and sends no second email.
- Killing attempt 1 during upload leads to attempt 2 succeeding. No object is visible before completion, and attempt 1's upload is aborted.
- Failing all three attempts runs `on_final_failure`, which marks the row `failed` and sends the failure email.
- An email failure after `done` makes the retry resend the email without exporting again.
- Stale rows are recovered by Step 11.
- A change in `row_count` mid-run causes a retry.
- A test asserts that no query for report rows reaches the primary.
- The page has no horizontal scroll at 375 px width, and the button and status fit.

Rollout:

- Put the feature behind a flag that turns off both paths.
- Enable it for one internal workspace first. Watch attempt durations, failure rates and the time between attempt 1 and completion.
- To roll back, turn the flag off. Existing `done` rows and files need no action, because the lifecycle rule removes them.

## Open questions

1. **Timing.** If the Step 1 benchmark is over 20 minutes, choose one of two options. (a) Upload parts in parallel with a fixed number of threads. Memory grows by one 16 MB buffer per thread. (b) Resume from a checkpoint. Save `upload_id`, the completed part etags and the last `row_id` at each part boundary in the row, and continue from there on retry. Option (b) relaxes "the queue keeps no progress" only for our own state. Owner decision needed.
2. **Nightly rebuild.** No version or snapshot column exists, so a rebuild during an export could mix two snapshots. The Step 7 row-count check is only a partial guard. A real data version on the report would be better.
3. **Bearer link in the email.** The emailed link works for 24 hours for anyone holding it, even if the user later loses `report.view`. Decide whether to accept this, or to check permission on a download endpoint instead.
4. **Permission during the job.** Should each attempt recheck `report.view`? This plan does not, because the click-time check matches the brief. Confirm.
5. **One slot for all filters.** The brief allows one active export per user per report, whatever its filters. A second click with different filters therefore returns the first export. Confirm that this UX is acceptable.
6. **Where `row_count` lives.** This plan reads `reports.row_count` from the replica, which may lag by the replication delay. If the table is only on the primary, the replica-only rule needs a decision.
7. **Formula injection.** Cells that start with `=`, `+`, `-` or `@` can run as formulas in spreadsheet programs. Decide whether to prefix such cells with an apostrophe.
8. **Link lifetime after 24 hours.** The page can issue a fresh link for 7 days, which is the lifecycle window. The brief only states 24 hours for the email. Confirm that the page behaviour is intended.
9. **Email templates.** `report_export_ready` and `report_export_failed` must be created, and their parameters confirmed.
10. **Final-failure guarantee.** Confirm that the queue calls `on_final_failure` even when the last attempt's worker dies. If not, Step 11 handles the case, but only after 45 minutes.
11. **Sub-threshold exports.** A report of 10,001 rows with a filter that matches 3 rows still goes by email, because the rule uses the unfiltered count. This follows the brief. Confirm it is accepted.