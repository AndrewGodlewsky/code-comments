# CSV export for the reports page: plan

## Summary

A **Download CSV** button on `/reports/{report_id}`. A report with 10,000 rows or fewer returns its CSV in the response to the click. A larger report queues a background job that writes the CSV to the `exports` bucket in parts and emails the user a 24-hour download link. The page shows the state of that export.

## Terms used below

- **Read replica:** a copy of the database that serves reads. Report rows are read only from it.
- **Keyset paging:** fetch the next batch with `row_id > last_row_id ORDER BY row_id LIMIT n`. Each batch costs the same no matter how far along the report is, unlike OFFSET.
- **Multipart upload:** object storage receives a file as numbered parts (each at least 5 MB except the last). Nothing is visible at the key until the upload is completed, so a half-written file cannot be downloaded.
- **Export record:** a new row in the primary database that holds one export's state. It is not report data, so the primary may hold it.
- **Attempt:** one run of the job handler. The queue allows 3 attempts, waits 60 s and then 300 s between them, and each attempt starts from the beginning.

## Steps

### 1. Share the view rules

- **Starts:** a code change, before any export code is written.
- **Data moves:** none at run time.
- **State kept:** none.
- **Work:** move the parsing of `filters` and `cols`, and the keyset row query, out of the rows endpoint into one module. The page API, the small-export response and the job all call that module. Column ids are checked against a whitelist. Because all three use the same code, they cannot disagree about which rows or columns a view means.
- **If it fails:** a mistake here breaks the page. Existing page tests must pass before export code is added.

### 2. Add the export record table

- **Starts:** a migration applied on the primary database.
- **Data moves:** none at run time.
- **State kept:** a table `report_exports` with columns `id`, `user_id`, `report_id`, `workspace_id`, `filters`, `cols`, `status` (`queued`, `running`, `done` or `failed`), `attempt`, `job_id`, `upload_id`, `object_key`, `error` (short text), `created_at`, `started_at`, `finished_at` and `notified_at`. A partial unique index on `(user_id, report_id)` where `status` is `queued` or `running` enforces one active export per user and report.
- **If it fails:** the migration rolls back. Nothing else is deployed.

### 3. Export request endpoint

- **Starts:** the user clicks Download CSV. The page calls `POST /api/reports/{report_id}/exports` with the current `filters` and `cols` from the page URL.
- **Data moves:** the endpoint reads the permission record, then `reports.row_count` from the replica. `row_count` is metadata, not row data, and it is rewritten nightly.
- **Work, in order:**
  1. Check `report.view` on the report's workspace. Return 403 if the check fails.
  2. Validate `cols` and `filters` with the step 1 module. Return 400 for an unknown column or a malformed filter.
  3. If `row_count` is 10,000 or fewer, go to step 4. Otherwise go to step 5.
- **If it fails:** a 403 or 400 is returned and nothing is stored. If the replica is unreachable, return 503 and the page shows a retry message.

### 4. Small export: the response is the CSV

- **Starts:** step 3 with `row_count` at or below 10,000.
- **Data moves:** rows are read from the replica through the step 1 module in keyset pages of 500, and written to the HTTP response with a header row first. The response has `Content-Type: text/csv` and `Content-Disposition: attachment` with a filename built from the report name.
- **State kept:** none. No row is written and no object is stored.
- **Work:** read the first page before sending any headers, so an early database failure becomes a clean error response. Stop after 10,000 rows. See open question 2 for the guard against a stale `row_count`.
- **If it fails:** before headers are sent, return 503. After headers have started, abort the connection instead of ending it normally, so the browser reports an error and does not save a truncated file.

### 5. Large export: start or reuse

- **Starts:** step 3 with `row_count` above 10,000.
- **Data moves:** one row is inserted into `report_exports` with status `queued`, the filters and the cols. The job payload is only `{export_id}`, far below the 64 KB limit.
- **Work, in order:**
  1. In one transaction, first mark any stale queued row for this user and report as `failed` (see the rule below). Then look for this user's `queued` or `running` export for this report. If one exists, return it with HTTP 200 and do not enqueue anything.
  2. Otherwise insert the new row with status `queued` and commit.
  3. After the commit, call `enqueue("report_export", {export_id})` and store the returned `job_id` on the row. Enqueueing after the commit means the job never starts before its row is visible.
  4. Return HTTP 202 with `export_id` and status.
- **Concurrent clicks:** if two clicks arrive together, the unique index rejects the second insert. Catch that error, reread the row and return the winner.
- **Stale queued rows:** a crash between the insert and storing `job_id` leaves a queued row with no `job_id`. A queued row with no `job_id` and an age over 5 minutes is stale. Queued rows that have a `job_id` are never treated as stale.
- **If it fails:**
  - If `enqueue` raises, mark the row `failed` with the error "could not queue" and return 503.
  - If the process dies between the insert and storing `job_id`, the stale rule in step 5.1 clears the row on the next click. If that job still runs later, step 6.1 sees status `failed` and exits.

### 6. Job attempt: begin

- **Starts:** the queue runs the `report_export` handler for attempt 1, 2 or 3.
- **Data moves:** the handler reads the export record on the primary by `export_id`. This is not report data.
- **Work, in order:**
  1. If status is `done`, skip to step 9. If status is `failed`, exit without doing anything. The status field acts as the lock, so a job for a row that was already cleared as stale does nothing.
  2. Check that the user still holds `report.view` on the workspace. If not, mark the row `failed` with "access removed" and exit.
  3. Run a conditional update that sets status `running`, `attempt` to the current attempt number and `started_at` to now, but only where status is `queued` or `running`. If no row changed, exit.
  4. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore a "not found" reply.
  5. Set `object_key` to `exports/{workspace_id}/{report_id}/{export_id}.csv`. The key includes the export id, so one export can never overwrite another export's file. Call `start_multipart`, then store the returned `upload_id`.
- **If it fails:** any error here counts as a failed attempt, and the queue retries from step 6.

### 7. Job attempt: stream rows into parts

- **Starts:** step 6 has finished.
- **Data moves:** rows are read from the replica in keyset batches of 5,000. The job is not bound by the API's batch limit of 500. Each batch is converted to CSV bytes by the step 1 module and appended to one in-memory buffer. When the buffer reaches 16 MB, it is sent with `upload_part(upload_id, part_number, bytes)` and its etag is kept. Every part is 16 MB except the last. The last batch is followed by a final part containing whatever is left in the buffer. The header row is included in the first part.
- **Memory:** the job holds one 16 MB buffer, one batch of rows and a list of etags. For a 900 MB file that is about 60 etags. It never holds the whole report. The peak must stay well under the 512 MB limit; step 12 measures it.
- **Time budget:** each attempt has a 1,800-second limit. Two million rows in 1,800 seconds needs about 1,100 rows per second, or about 0.5 MB per second sustained for a 900 MB file. The queue keeps no progress, so a job that is too slow fails on every attempt, not just one. Step 12 must measure this before release.
- **State kept:** only the in-memory buffer and etags. Nothing is written to the row during this step.
- **If it fails:** an exception, a timeout or a worker crash ends the attempt, and the queue retries from step 6. The incomplete upload is harmless because nothing is visible at the key. The next attempt aborts it in step 6.4. Any left over is discarded by the bucket's 24-hour rule for incomplete uploads.

### 8. Job attempt: publish the file

- **Starts:** every batch has been read and the last part has been uploaded.
- **Data moves:** `complete_multipart(upload_id, etags)` makes the object visible at `object_key`. Then a conditional update sets status to `done` and `finished_at` to now, but only where status is `running`.
- **State kept:** the export row. The object exists once the complete call succeeds, and the row becomes `done` straight after.
- **If it fails:**
  - If `complete_multipart` fails, the attempt fails and the queue retries from step 6. Nobody has a link yet.
  - If the process dies after the complete call but before the row is marked `done`, the next attempt sees status `running` and repeats the upload to the same key. That replaces the object with equivalent content before any link is issued.

### 9. Email the download link

- **Starts:** the row is `done` and `notified_at` is empty. This is reached right after step 8, or on a retry that found the row already done.
- **Data moves:** `send_email(user_id, "report_export_ready", {export_id, report_name, download_url, expires_at})`. `expires_at` is `finished_at` plus 24 hours. `download_url` is `signed_url("exports", object_key, ttl)`, where `ttl` is the remaining time to `expires_at`, capped at 86,400 seconds. Using the remaining time keeps the 24-hour window correct even when a retry sends the email late.
- **State kept:** `notified_at` is set after `send_email` returns.
- **If it fails:** the attempt raises and the queue retries. The next attempt sees `done` with `notified_at` empty and goes straight to this step. If the final attempt's email still fails, the row stays `done`, so the page still offers the download (step 11). Log the error. A duplicate email is possible only if the send succeeds and the `notified_at` write fails. This is accepted.

### 10. Final failure

- **Starts:** the queue calls `on_final_failure` once, after attempt 3 has failed.
- **Work, in order:**
  1. If status is `done`, change nothing and log. The only work left is the email in step 9.
  2. Otherwise run a conditional update that sets status `failed`, `finished_at` to now and `error` to a short reason (exception type and message, cut to 500 characters). It applies only where status is not `done`.
  3. Call `abort_multipart` on `upload_id` on a best-effort basis. Ignore errors.
  4. Call `send_email(user_id, "report_export_failed", {export_id, report_name})`, then set `notified_at`.
- **If it fails:** if the status write itself fails, the row stays `running`. A `running` row whose `started_at` is more than 2 hours old cannot have a live attempt, because three attempts at 30 minutes each plus the waits total about 96 minutes. Step 5.1 treats such a row as `failed`. If only the email fails, the page still shows `failed`.

### 11. Page status and download

- **Starts:** the page loads, a Download CSV click returns from step 5, or the page polls.
- **Data moves:** `GET /api/reports/{report_id}/exports/latest` reads the user's most recent export for this report from the primary. It checks `report.view` first. The response holds `status`, `attempt`, `filters`, `finished_at` and, when the export is `done` and within 24 hours, a fresh `download_url` signed for the remaining time.
- **Display:**
  - `queued`: "Queued".
  - `running`: "Running, attempt n of 3".
  - `done` within 24 hours: "Ready" with a download link and its expiry time.
  - `done` after 24 hours: "Link expired. Start a new export."
  - `failed`: "Export failed" with a button that starts a new export through step 5.
- **Polling:** every 5 seconds while the status is `queued` or `running`. Polling pauses while the tab is hidden and stops at `done` or `failed`. On a later visit, the page loads the latest row and shows its state.
- **State kept:** the server row is the record. The browser keeps nothing extra. The URL still carries only `filters` and `cols`.
- **If it fails:** a failed status request shows "Status unavailable, retrying" and keeps polling with growing delays. The download link is unaffected because it is a direct link.

### 12. Verify before release

- **Unit tests:** CSV quoting, header order, column whitelist, and keyset paging across batch boundaries with no missing or duplicate rows.
- **Concurrency test:** two simultaneous clicks produce one export row and one job.
- **Fault injection:** stop the worker at the start of an attempt, mid-upload, before `complete_multipart`, and after `complete_multipart` but before `done`. Also make the email fail. In each case, no partial file must be downloadable, the final state must be correct and each export must send at most one email.
- **Performance test:** run the job alone on the largest report, about 2 million rows. It must finish within the 1,800-second limit with a clear margin. Measure peak memory against the 512 MB limit.
- **Routing test:** no report row query reaches the primary.
- **Stale count test:** with a deliberately stale `row_count`, confirm the guard in open question 2.

### 13. Release and watch

- Count exports by status and time to finish. Alert on the failure rate.
- Build no cleanup job. The bucket's 7-day lifecycle rule removes old files.

## Open questions for the owner

1. **One export per report, not per filter.** The brief says a second click returns the existing export. If the user changed the filters, they get the old export back. This plan keeps the brief's rule and makes the response state its filters, so the page can say so. The alternative is to include the filters in the uniqueness key.
2. **`row_count` is nightly.** If it is stale, a report of 50,000 rows may look small and step 4 would stream past 10,000. This plan adds a bounded count on the replica (`LIMIT 10001`) before streaming. If the count is above 10,000, the request goes to the large path. Confirm this guard, since it goes beyond the brief.
3. **Nightly rebuild during a job.** If the rebuild changes `row_id` values, a keyset read that spans it can miss or repeat rows. Confirm the rebuild window, or block exports while it runs.
4. **Throughput.** The queue keeps no progress, so if 2 million rows cannot finish in 30 minutes, no retry will help. If step 12 measures too slow, the fix is resumable jobs, which the brief excludes. Decide the fallback before building.
5. **Email templates.** `report_export_ready` and `report_export_failed` are assumed names. Confirm them or create them.
6. **Header labels and CSV injection.** The plan assumes the header row uses the page's column labels. Decide whether cells starting with `=`, `+`, `-` or `@` should be neutralised for spreadsheet safety.
7. **Permission re-check and bearer links.** Step 6.2 re-checks `report.view` when the job starts, which goes beyond the brief. A 24-hour signed link works for anyone who holds it. Confirm both choices.