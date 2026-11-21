# CSV export for the reports page: implementation plan

## Summary

One endpoint decides the path by `reports.row_count`. At 10,000 rows or fewer, the click response is the CSV itself. Above 10,000, the endpoint records a row in a new `report_exports` table, enqueues a background job, and returns at once. The job writes the CSV in 16 MB parts to a multipart upload in the `exports` bucket, makes the file visible only when the upload is completed, and emails a 24-hour download link. The page polls the export's state until it is done or failed.

Where this plan cannot give an answer, the step says so and points to an Open Question. Nothing in this plan is confirmed beyond what the three existing files state.

## Fixed requirements

These are the requirements the plan must meet. The steps below show how.

- **Contents**: the CSV holds the rows the user sees: the filters and column order from the page URL, plus a header row.
- **Access**: the export uses the same `report.view` permission check as the page. Report rows are read only from the read replica.
- **Size paths**: `reports.row_count` decides. At 10,000 or fewer, the click response is the CSV and nothing is stored. Above 10,000, a background job builds the file.
- **Large exports**: the file goes to the `exports` bucket. The user gets an email with a download link that works for 24 hours, sent with the existing `send_email(user_id, template, params)`. The bucket's lifecycle rule deletes old files. No cleanup job is built.
- **Status on the page**: while a large export is queued or running, and when the user returns later, the page shows its state: queued, running, done or failed.
- **One at a time**: a user can have only one large export of a given report queued or running. Clicking again returns that export.
- **Limits**: a worker has 512 MB of memory. The largest report has about 2 million rows. The job never holds a whole report in memory and must finish within the queue's 1,800-second attempt timeout.
- **Failure**: the queue's normal retries apply. A half-written file is never downloadable. After the last failed attempt, the user gets a failure email and the page shows failed.
- **Out of scope**: scheduled exports, formats other than CSV, and changes to the table on the page.

These requirements come from the request that asked for this plan. The page does not enforce them; the steps below do.

## Terms used

- **Read replica**: a copy of the primary database. Report rows are read only from it. Which database holds the `reports` table is not stated (Open Question 6).
- **Primary**: the main database that accepts writes. Export state is kept here.
- **Keyset paging**: fetching the next page with `row_id > last_seen ORDER BY row_id LIMIT n`. It does not use OFFSET.
- **Job queue**: the existing in-house background job queue, defined in `existing/jobs.py`. A handler is registered with `@job(name, on_final_failure=...)` and a job is queued with `enqueue(name, payload)`. Jobs run on the `worker` pool. Its settings are constants in that file: 3 attempts in total (`MAX_ATTEMPTS`), waits of 60 s before attempt 2 and 300 s before attempt 3 (`BACKOFF_SECONDS`), and a 1,800 s limit per attempt (`ATTEMPT_TIMEOUT_SECONDS`). An attempt that runs past the limit is killed by the queue and counts as failed. The file does not say how the kill is done (Open Question 15).
- **Attempt**: one run of the job handler. `ctx.attempt` gives its number, 1, 2 or 3.
- **Snapshot**: the report rows as they stood after one nightly rebuild.
- **Multipart upload**: an object is uploaded in numbered parts. Nothing is visible at the object key until `complete_multipart` succeeds.
- **Attempt token (fence)**: a random ID created at the start of each job attempt and stored on the export row. A write to that row is applied only if the stored token still matches and the state is the expected one. This stops an old attempt from overwriting a newer one.
- **Heartbeat**: refreshing the row's `updated_at` as the job makes progress, so a stalled export can be detected.
- **Active export**: an export in state `queued` or `running`.
- **Conditional update**: one SQL `UPDATE` whose `WHERE` clause holds the checks (for example, the token and the state). The database reports how many rows matched. Zero matched rows means the write was not applied. Every conditional update in this plan is one such statement.
- **Report access check**: the `report.view` check the page already uses. This plan calls the same check. How it resolves the report's workspace is not described (Open Question 16).

## Step 1: Measure before building

- **Starts**: a benchmark in a non-production environment, before any code is merged.
- **Data moves**: a test report of about 2 million rows is read with the same keyset query from a replica, and written as CSV in 16 MB parts to a scratch key.
- **State**: none. Delete the scratch object afterwards.
- **Goal**: one full attempt finishes in under 20 minutes, which leaves a margin under the 1,800-second attempt timeout. Peak memory stays well under 512 MB.
- **Also measure**:
  - A selective filter. If the filter columns are not indexed, each keyset page may scan far more rows than it returns.
  - The small path at 10,000 rows, using the widest realistic row. API requests are killed after 60 seconds (Step 4), so this must finish well under that. If it does not, lower the 10,000 threshold.
- **On failure**: if the large-export benchmark is over 20 minutes, stop. All three attempts would hit the same timeout, so the approach must change first. Which change to make is an owner decision (Open Question 1).

## Step 2: Add the state table on the primary database

- **Starts**: the migration, run on deploy.
- **Table `report_exports`**:
  - `id` (UUID, also the export ID)
  - `user_id`, `report_id`
  - `filters`, `cols` (copied from the page URL after validation)
  - `state` (`queued`, `running`, `done` or `failed`)
  - `job_id`, `attempt`, `attempt_token`, `upload_id`, `object_key`
  - `links_until` (empty until the export is done; see Step 8). No download link is issued after this time.
  - `error_message` (short and generic, with no internal detail)
  - `created_at`, `updated_at` (heartbeat), `completed_at`, `email_sent_at`
- **Constraint**: a partial unique index on `(user_id, report_id)` where `state` is `queued` or `running`. This enforces one active export per user per report, even when the button is double-clicked.
- **Why the primary**: this is our state, not report data. The replica rule covers report rows only.
- **On failure**: a failed migration is rolled back. Nothing depends on the table until Step 5.

## Step 3: The click endpoint and the path decision

- **Route**: `POST /api/reports/{report_id}/exports`. The body carries `filters` and `cols` copied from the page URL.
- **Starts**: the user clicks **Download CSV**.
- **Checks, in order**:
  1. The caller has `report.view` on the report's workspace, using the report access check. Otherwise return 403. This is the same check the page uses.
  2. Validate `filters` and `cols` against the report's columns. An unknown column returns 400. Reject a body over 8 KB.
  3. Read `reports.row_count` from the read replica. This is the total number of rows in the report with no filter. The nightly rebuild writes it. How and when the rebuild writes it, relative to the rows, is not known (Open Questions 2 and 6).
  4. If `row_count` is 10,000 or less, go to Step 4. Otherwise go to Step 5.
- **Data moves**: only the request body and one count.
- **State**: none written by these checks.
- **On failure**: 403 or 400 leaves no state. If the count read fails, return 503. Nothing has started, so the user can retry.

## Step 4: Small export (10,000 rows or fewer)

- **Starts**: Step 3 chose the small path.
- **Data moves**: report rows are read from the replica in keyset pages of 500, the same size the page uses, in `row_id` order. Only rows that match the URL's filters are read, exactly as on the page. The threshold uses the unfiltered `row_count`, but the file may hold fewer rows than that. The header row lists the `cols` in URL order. Each row is written as an RFC 4180 CSV line: fields with commas, quotes or newlines are quoted, and quotes are doubled. The loop stops at the first page with fewer than 500 rows.
- **Row cap**: if more than 10,000 rows have been read, stop and return 503 ("the report changed, try again"). This protects the buffer when `row_count` is stale. A normal run reads at most 20 pages.
- **Time limit**: API servers kill any request that runs longer than 60 seconds. This applies to the page and to this path. The small path reads up to 20 pages in one request, so Step 1 times it.
- **Buffering**: build the complete CSV in memory, then send it with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`. Do not stream it. A stream that fails midway looks like a complete file to the user but is truncated. A buffered response returns an error instead. At 10,000 rows the buffer is small. Confirm this with the widest realistic row in the Step 1 benchmark.
- **State**: none. No row, no job, nothing stored.
- **On failure**: if the read runs past the 60-second limit, fails, or hits the row cap, the request returns an error. The user retries. No file is produced and nothing is left behind.

## Step 5: Large export: create or return the active one

- **Starts**: Step 3 chose the large path, meaning `row_count` is above 10,000.
- **Procedure**:
  1. Look for an active export for this user and report.
     - If one exists and is not stale (Step 11 rule), return it with `already_running: true`, together with its filters and columns. Stop here.
     - If one exists and is stale, run the Step 11 update on it. If that update changes one row, the stale export is now `failed`, so the slot is free. Continue to substep 2 in the same request. If it changes no row, another request already handled it: look up the active export again and return it with `already_running: true`. If the Step 11 update itself fails, return the existing row with `already_running: true` and start nothing.
     - If none exists, go to substep 2.
  2. Insert a row with `state = queued` and `job_id` empty. If the insert hits the unique index because a concurrent click won, read the winning row and return it with `already_running: true`.
  3. Call `enqueue("report_export", {"export_id": <id>})`. The payload is only the ID, far under the 64 KB limit. The job reads filters and columns from the row. What `enqueue` returns and how it fails beyond raising is not described (Open Question 17).
  4. Store the returned `job_id` on the row. Return 202 with the export ID and state `queued`.
- **Response after a stale recovery**: if the Step 11 update in substep 1 changed one row and the insert in substep 2 then succeeds, the response is the same 202 with the new export ID and state `queued`, as for any new click. The previous stale export is already `failed` and is not returned.
- **Data moves**: one row written to the primary. This step reads no report rows, so the 60-second limit is not a risk here.
- **On failure**:
  - If `enqueue` raises, mark the row `failed` with "could not start" and return 503. The user can click again. The plan treats every raise the same way, because the failure modes are not described.
  - If the process dies after the insert and before the enqueue, the row stays `queued` with no `job_id`. Step 11 recovers it.
  - If the process dies after the enqueue and before the `job_id` is stored, the row stays `queued` with no `job_id`. The job still runs and Step 6 handles it. Step 11 may mark the row failed first; the job then exits at Step 6.
  - Concurrent clicks cannot create two active rows, because of the index in Step 2.

## Step 6: Job attempt start

- **Starts**: the job queue runs `report_export(ctx, payload)` with `ctx.attempt` set to 1, 2 or 3. The handler is registered under the name `report_export`, with an `on_final_failure` function (Step 9). The queue's settings are in the Terms section. Each attempt runs the handler again from the start with the same payload. Delivery is at least once, so the handler may run again for an export that already succeeded.
- **Procedure**:
  1. Load the row by `payload.export_id`. Then take the first case that applies:
     - The row is missing, or its state is `failed`: return without doing anything. `failed` means Step 11 or the final failure has already ended this export.
     - The state is `done` and `email_sent_at` is set: return without doing anything. The export and its email are complete.
     - The state is `done` and `email_sent_at` is empty: the export is finished but its email was not confirmed. Do not export again. Go to Step 8, substep 4, using the stored `object_key`, then return. If that email fails, raise so the queue retries. On the last attempt, `on_final_failure` runs, and it leaves a `done` row unchanged (Step 9).
     - The state is `queued` or `running`: continue with substep 2.
  2. Read the row's current `upload_id` into memory, and create a new `attempt_token`. Run this conditional update: `UPDATE report_exports SET attempt = ctx.attempt, attempt_token = <new>, state = 'running', upload_id = NULL, updated_at = now() WHERE id = <export_id> AND state IN ('queued', 'running')`. If zero rows match, return without doing anything.
  3. If the read in substep 2 found an old `upload_id`, call `abort_multipart` on it. This is best effort: log any error and continue.
  4. Start a multipart upload to the key `report-exports/{report_id}/{export_id}/{attempt_token}.csv` in the `exports` bucket. Save the returned `upload_id` with a fenced update: `UPDATE report_exports SET upload_id = <id>, updated_at = now() WHERE id = <export_id> AND attempt_token = <token> AND state = 'running'`. If zero rows match, this attempt was superseded: call `abort_multipart` on the new upload and return without error.
- **Data moves**: a few small writes to the row.
- **State**: the row holds `attempt`, `attempt_token` and `upload_id`.
- **Crash between writes**: the four substeps are separate writes, so a crash can leave these states:
  - After substep 2 and before substep 3: the old upload is not aborted, but the row no longer points to it. The bucket's 24-hour rule discards it.
  - After substep 4 starts the upload and before the save: the new upload is not recorded. The 24-hour rule discards it. The next attempt does not abort it, which is accepted.
- **On failure**: if the state update or the upload start fails, the attempt raises and the queue retries it. A failed abort is ignored, because the bucket's lifecycle rule discards unfinished uploads after 24 hours anyway.

## Step 7: Stream rows into the upload

- **Starts**: Step 6 succeeded.
- **Data moves**:
  - Read report rows from the replica in pages of 5,000, using `row_id > last ORDER BY row_id LIMIT 5000` with the row's filters.
  - Convert each row to a CSV line with the same quoting rules as Step 4. The header row goes first.
  - Append the lines to one in-memory part buffer. When it reaches 16 MB, call `upload_part(upload_id, part_number, bytes)` and keep the returned etag in a list. The final part may be smaller, which the storage rules allow.
- **Memory**: one 16 MB buffer, one 5,000-row page and a list of etags, which is about 57 short strings for 900 MB. This stays far under 512 MB. The whole report is never held in memory. The 2-million-row report is about 900 MB and needs about 57 parts, well under the 10,000-part limit.
- **Heartbeat and fence**: after each part, run this conditional update: `UPDATE report_exports SET updated_at = now() WHERE id = <export_id> AND attempt_token = <token> AND state = 'running'`.
  - If one row matches, continue.
  - If zero rows match, this attempt has been stopped or superseded (for example, by Step 11). Call `abort_multipart` on its own `upload_id`, log the stop, and return without error. Returning without error means the queue does not retry it, and no failure email is sent.
- **Snapshot check**: read `reports.row_count` at the start and at the end of the attempt. If it changed, the nightly rebuild ran during the export and pages may mix two snapshots. Raise an error so the queue retries.
  - This is a partial guard only. No version column exists today, and how the nightly rebuild writes rows and `row_count` is not known (Open Question 2). A rebuild that changes the rows but leaves `row_count` the same is not detected. The attempt then completes with pages from two snapshots and no error, and the user gets that file. This gap is accepted only until Open Question 2 is resolved.
- **State**: no progress is saved. A retry starts again from row zero.
- **On failure**:
  - A replica query error or timeout, or an `upload_part` error, makes the attempt raise. The queue waits 60 seconds before attempt 2, or 300 seconds before attempt 3, then runs the handler again from the start.
  - An attempt killed at the 1,800-second limit is handled the same way. The plan assumes the queue counts a kill as a failed attempt, as `existing/jobs.py` says. How the kill is done is not known (Open Question 15).
  - A worker crash is handled the same way.
  - In every case the object key stays empty, so no partial file can be downloaded. The next attempt's Step 6 aborts the abandoned upload.

## Step 8: Finish the file and tell the user

- **Starts**: every row has been uploaded as a part.
- **Procedure**:
  1. Run the fence check from Step 7 again (token matches and state is `running`). If it does not match, call `abort_multipart` on this attempt's `upload_id`, and return without error.
  2. Record `t0`, the current time. Call `complete_multipart(upload_id, etags)`. This is the only moment the file appears at its key.
  3. Run a fenced update: `UPDATE report_exports SET state = 'done', object_key = <key>, completed_at = now(), links_until = t0 + 7 days, upload_id = NULL WHERE id = <export_id> AND attempt_token = <token> AND state = 'running'`. `t0` is taken before the object exists, so `links_until` is never later than the object's deletion time under the 7-day lifecycle rule. The 7-day rule is stated in the storage helper's comments; how the storage service enforces it is not known (Open Question 13). If no row changes, this attempt was superseded. Stop here and send no email.
  4. Send the email. Set `download_url = signed_url("exports", object_key, 86400)` and `expires_at = now + 24 hours`, then call `send_email(user_id, "report_export_ready", {report_id, download_url, expires_at})`. The template does not exist yet and its parameters are not confirmed (Open Question 9). Whether `send_email` is idempotent is not known (Open Question 15). On success, run `UPDATE report_exports SET email_sent_at = now() WHERE id = <export_id> AND state = 'done' AND email_sent_at IS NULL`.
- **Order**: the row is marked `done` before the email is sent, so the page shows the export as done even if the email fails.
- **Leftover file**: if the state changes between step 1 and step 2, the file can become visible at a key that no row refers to. No download link is issued for it, and the lifecycle rule deletes it after 7 days.
- **On failure**:
  - If `complete_multipart` fails, the attempt raises and retries. Nothing became visible.
  - If the fenced update changes no rows, stop without sending email.
  - If the email fails after the row is `done`, the attempt raises and the queue retries. The retry follows Step 6, case 3: it sees `done` with `email_sent_at` empty, and only resends the email. It does not export again. A duplicate email is possible if the send succeeds but writing `email_sent_at` fails. That is acceptable.
  - If the email still fails on the last attempt, `on_final_failure` runs. It leaves the `done` row unchanged and sends no failure email (Step 9). The user can still download the file from the page (Step 10). Whether the user is told some other way is undecided (Open Question 14).

## Step 9: Failure on each attempt, and final failure

- **Each failed attempt**: the handler wraps its body in a try block. On an exception, it writes a short `error_message` to the row, conditional on the token, and then re-raises. The row stays `running` with its attempt number and `updated_at`. The page shows "running, attempt N of 3". An attempt killed by the timeout cannot write this message, so the row keeps its last heartbeat instead.
- **`on_final_failure(ctx, payload, error)`**, called once after the third attempt fails. It receives the same `payload` as the handler, which holds only `export_id`, so it first loads the row by `payload.export_id` to get `user_id`, `report_id` and `upload_id`. Whether it runs when the worker dies on the last attempt is not confirmed (Open Question 10).
  1. If the row is missing, log and return.
  2. If the row is `done`, log and return. Nothing else is changed: the file is complete and the page offers the download. The email may be unsent (Step 8).
  3. Otherwise run a conditional update to `state = failed` with a generic `error_message` such as "The export could not be built. Try again." The update applies only if the state is `queued` or `running`.
  4. Abort the row's `upload_id`, if one exists. This is best effort.
  5. Call `send_email(user_id, "report_export_failed", {report_id})`. The template does not exist yet (Open Question 9). Catch and log any error, so the row stays `failed` even if the email does not send.
- **If `on_final_failure` itself fails**: the row stays `running`. Step 11 marks it failed later.

## Step 10: Status endpoint and the page

- **Endpoint**: `GET /api/reports/{report_id}/exports/latest`.
  - Checks `report.view` using the report access check from Step 3.
  - Reads the primary, because this is our state, not report data.
  - Returns the newest row for this user and report: `state`, `attempt`, `completed_at`, the filters and columns it was started with, and the generic `error_message`.
  - **Stale rows**: if the row is active and stale under the Step 11 rule, this request runs the Step 11 update first. If that update changes the row, the response shows `state: failed` with the generic message. If the update changes nothing, the response shows the row as read. If the update fails, the response shows the row as read and the page keeps its last known state.
  - If the state is `done` and the current time is before `links_until`, it also returns a fresh signed URL: `download_url = signed_url("exports", object_key, ttl)`, where `ttl = min(86400, links_until - now)` seconds. The URL is generated on each request and is not stored. The link therefore works for at most 24 hours and never after the object could have been deleted. Whether this 24-hour page link is intended is unconfirmed (Open Question 8).
  - If the state is `done` and `links_until` has passed, it returns `expired: true` and no URL. This does not depend on the lifecycle rule having run. A leftover object is simply never linked. Nothing deletes it early.
- **Page behaviour**:
  - On load, fetch the latest export.
  - `queued` or `running`: show the state and attempt number. Poll every 5 seconds, then every 30 seconds after the first 2 minutes. Stop polling on `done` or `failed`.
  - `done` with a `download_url`: show a **Download** button. Clicking it calls this same endpoint again and opens the fresh `download_url` from the response. If the response says `expired: true` instead, show the expired state.
  - `done` and the page is still open after `links_until`: the next poll or click receives `expired: true`, and the page switches to the expired state.
  - `expired: true`: show "expired, export again" and a button that calls Step 3.
  - `failed`: show the message and a Try again button, which calls Step 3.
  - If the latest export's filters differ from the current URL, say so on the page.
  - The frontend stack and the detailed rendering are not described in this plan. Only the behaviour above is specified.
- **On failure**: if the status request fails, the page shows "status unavailable" and keeps the last known state. It never starts an export.

## Step 11: Stale exports

- **Starts**: any Step 5 click, and any `GET latest` request (Step 10).
- **Rule**: an active row is stale when either of these holds:
  - `state = running` and `updated_at` is more than 45 minutes old. The 45 minutes is the 30-minute attempt timeout, plus the longest backoff of 5 minutes, plus a margin.
  - `state = queued`, `job_id` is empty, and `updated_at` is more than 5 minutes old. This happens when the process died between the insert and the enqueue or before the `job_id` was stored.
- **Action**:
  1. Read the row's `upload_id`.
  2. Run one conditional update: set `state = 'failed'` and `error_message = "The export stopped unexpectedly. Try again."`, with the stale rule repeated in the `WHERE` clause. A row that was refreshed in the meantime is not changed. Report whether one row changed.
  3. If step 2 changed a row, abort the `upload_id` read in step 1, best effort.
- **Effect on a running attempt**: the attempt's heartbeat and Step 8 fence both require `state = 'running'`. Its next check (at the next part boundary, or before completing the upload) fails, so it aborts its own upload and returns without writing anything more. The most it can do after Step 11 is upload one more part, which it then aborts. The lifecycle rule removes any leftover upload after 24 hours.
- **If the queue still holds a scheduled retry for that export**: it exits at Step 6 because the state is `failed`.
- **Not covered**: a job that waits in the queue for a long time with `job_id` set is not checked by this rule. How the queue handles such a wait is unknown (Open Question 10).
- **On failure**: if the update fails, the request returns the existing row. It does not start a second export.

## Step 12: Tests and rollout

Automated tests:

- Without `report.view`, `POST` and `GET latest` return 403 and create no row.
- A `row_count` of 10,000 takes the small path. A `row_count` of 10,001 takes the large path.
- The small-path response matches the CSV from the same query. The header order follows `cols`. Commas, quotes and newlines are quoted correctly. A filter that matches few rows returns only those rows.
- The small path returns 503 when more than 10,000 rows are read.
- The large-path output for the same query matches the small-path output for a fixture of about 25,000 rows. Use a small part size in the test so several parts are exercised.
- Two concurrent clicks create one row, and both receive the same export.
- Running the job again after success creates no second row and sends no second email.
- Running the job again after `done` with `email_sent_at` empty resends the email and does not upload anything.
- Killing attempt 1 during upload leads to attempt 2 succeeding. No object is visible before completion, and attempt 1's upload is aborted.
- Failing all three attempts runs `on_final_failure`, which loads the row by `export_id`, marks it `failed` and sends the failure email.
- A final failure on a `done` row leaves the row unchanged and sends no failure email.
- An email failure after `done` makes the retry resend the email without exporting again.
- Stale rows are recovered by Step 11. When two clicks find the same stale row, one marks it failed and inserts the new row. The other re-reads and returns that row.
- `GET latest` on a stale running row returns `failed` and applies the Step 11 update.
- An attempt whose row was marked `failed` by Step 11 stops at its next fence check, aborts its upload, and writes nothing more.
- A change in `row_count` mid-run causes a retry.
- The status endpoint, after `links_until`, returns `expired: true` and no `download_url`. Before it, the returned link's lifetime does not exceed `links_until`.
- A test asserts that no query for report rows reaches the primary.
- The page has no horizontal scroll at 375 px width, and the button and status fit.

Rollout:

- Put the feature behind a flag that turns off both paths.
- Enable it for one internal workspace first. Watch attempt durations, failure rates and the time between attempt 1 and completion.
- To roll back, turn the flag off. Existing `done` rows and files need no action, because the lifecycle rule removes them.
- Who runs the worker processes, how many there are, and how they are deployed is not known (Open Question 12). The rollout assumes the team can change worker settings if needed.

## Open questions

1. **Timing.** If the Step 1 benchmark is over 20 minutes, choose one of two options. (a) Upload parts in parallel with a fixed number of threads. Memory grows by one 16 MB buffer per thread. (b) Resume from a checkpoint. Save `upload_id`, the completed part etags and the last `row_id` at each part boundary in the row, and continue from there on retry. Option (b) relaxes "the queue keeps no progress" only for our own state. Owner decision needed.
2. **Nightly rebuild.** The page's report size is set by `reports.row_count`, which the nightly rebuild rewrites. It is not known whether the rebuild replaces the report rows all at once or updates them in place, or whether it writes `row_count` before, during or after the rows change. No version or snapshot column exists, so a rebuild during an export could mix two snapshots. The Step 7 row-count check is only a partial guard. A real data version on the report would be better.
3. **Bearer link in the email.** The emailed link works for 24 hours for anyone holding it, even if the user later loses `report.view`. Decide whether to accept this, or to check permission on a download endpoint instead.
4. **Permission during the job.** Should each attempt recheck `report.view`? This plan does not, because the click-time check matches the fixed requirements. Confirm.
5. **One slot for all filters.** The fixed requirements allow one active export per user per report, whatever its filters. A second click with different filters therefore returns the first export. Confirm that this UX is acceptable.
6. **Where `row_count` lives.** This plan reads `reports.row_count` from the replica, which may lag by the replication delay. It is also not stated which database holds the `reports` table. If the table is only on the primary, the replica-only rule needs a decision.
7. **Formula injection.** Cells that start with `=`, `+`, `-` or `@` can run as formulas in spreadsheet programs. Decide whether to prefix such cells with an apostrophe.
8. **Link lifetime.** The emailed link lasts 24 hours from sending. The page link lasts `min(24 hours, links_until - now)` and is issued again on each request until `links_until`. Confirm that this is intended, since the fixed requirements state 24 hours only for the email.
9. **Email templates.** `report_export_ready` and `report_export_failed` must be created, and their parameters confirmed.
10. **Final-failure guarantee and queue wait.** `existing/jobs.py` says a worker death counts as a failed attempt, and that `on_final_failure` runs after the last failed attempt. It is not confirmed that this still holds when the worker dies on the last attempt. If not, Step 11 handles the case, but only after 45 minutes. Also not confirmed: how a job that waits in the queue for a long time, with no attempt yet started, is handled. Step 11 does not check that case when `job_id` is set.
11. **Sub-threshold exports.** A report of 10,001 rows with a filter that matches 3 rows still goes by email, because the rule uses the unfiltered count. This follows the fixed requirements. Confirm it is accepted.
12. **Worker operations.** The queue's settings (3 attempts, 60 s and 300 s backoff, 1,800 s timeout, 512 MB per worker, one attempt at a time) are known from `existing/jobs.py`. It is not known who runs the worker processes, how many there are, or how they are deployed.
13. **Storage provider.** The `exports` bucket and `signed_url` are used as described in the existing storage helpers. Which storage service backs them, how the link signature is checked, and therefore the exact lifecycle and link behaviour, is not stated.
14. **Missed email after done.** If the email for a `done` export still fails on the last attempt, the user is not told by email. The page still offers the download, but a user who does not open the page will not know the file exists. Decide whether to add a fallback notice.
15. **Queue kill and send_email internals.** How the queue kills an attempt that passes 1,800 s is not described. Also not described: what `send_email` does internally and whether it is idempotent, and what `signed_url` does internally.
16. **Report access check.** How the `report.view` check resolves the report's workspace, and how the check is implemented, is not described in the existing files. This plan reuses the page's check as it is.
17. **enqueue contract.** What `enqueue` returns beyond `job_id`, and which failures it can raise, is only partly described in `existing/jobs.py`. Step 5 treats every raise the same way.