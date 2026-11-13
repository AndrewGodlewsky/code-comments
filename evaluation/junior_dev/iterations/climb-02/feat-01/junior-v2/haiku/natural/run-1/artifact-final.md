# CSV export for the reports page: plan

## Summary

A **Download CSV** button on `/reports/{report_id}`. A view of 10,000 rows or fewer returns its CSV in the response to the click. A larger view queues a background job that writes the CSV to the `exports` bucket in parts and emails the user a 24-hour download link. The page shows the state of that export.

## Terms

- **Primary and read replica:** the primary is the main database. The replica is a read-only copy. Report rows are read only from the replica. Export records live on the primary, because they are not report data.
- **Queue:** the existing background job queue (`existing/jobs.py`). `enqueue(name, payload)` returns a `job_id`. An attempt running longer than 1,800 s is killed and counts as failed. A job gets 3 attempts, waiting 60 s and then 300 s between them. Each attempt starts again from the beginning with the same payload and no saved progress. Delivery is at least once, so a job can run again after it has succeeded.
- **Keyset paging:** the next batch is `row_id > last_row_id ORDER BY row_id LIMIT n`. Each batch costs the same however far along the report it is, unlike OFFSET.
- **Multipart upload:** the object store takes a file as numbered parts (each at least 5 MB except the last). Nothing is visible at the key until the upload completes, so a half-written file cannot be downloaded.
- **Export record:** one row in `report_exports` on the primary, holding one export's state.

## Steps

### 1. Share the view rules

- **Starts:** a code change, before any export code is written.
- **Data moves:** none at run time. **State kept:** none.
- **Work:** move the parsing of `filters` and `cols`, and the keyset row query, out of the rows endpoint into one module. The page API, step 4 and the job all call it. Column ids are checked against a whitelist. One code path means the three cannot disagree about which rows or columns a view means.
- **If it fails:** a mistake breaks the page. Existing page tests must pass before step 2.

### 2. Add the export record table

- **Starts:** a migration on the primary.
- **State kept:** table `report_exports` with columns `id`, `user_id`, `report_id`, `workspace_id`, `filters`, `cols`, `status` (`queued`, `running`, `done`, `failed`), `attempt`, `job_id`, `upload_id`, `object_key`, `error` (short text), `created_at`, `started_at`, `finished_at`, `notified_at`. A partial unique index on `(user_id, report_id)` where status is `queued` or `running` allows at most one active export per user and report.
- **If it fails:** the migration rolls back. Nothing else is deployed.

### 3. Export request endpoint

- **Starts:** the click. The page calls `POST /api/reports/{report_id}/exports` with `filters` and `cols` from the URL.
- **Data moves:** reads the `report.view` permission record. Reads `reports.row_count` from the replica (nightly metadata).
- **Work, in order:**
  1. Check `report.view` on the report's workspace with the same check the page API uses. Return 403 if it fails.
  2. Validate `cols` and `filters` with the step 1 module. Return 400 for an unknown column or a malformed filter.
  3. If `row_count` is above 10,000, go to step 5.
  4. Otherwise count the matching rows on the replica, stopping at 10,001 (`SELECT count(*) FROM (... LIMIT 10001)`). If the count is above 10,000, the stored `row_count` is stale: go to step 5. Otherwise go to step 4.
- **Why the count:** it runs before any response header is sent, so it is the last check before streaming. See open question 2.
- **If it fails:** 400 or 403 is returned and nothing is stored. If the replica is unreachable, return 503 and the page shows a retry message.

### 4. Small export: the response is the CSV

- **Starts:** step 3 found 10,000 or fewer matching rows.
- **Data moves:** rows are read from the replica through the step 1 module in keyset pages of 500 and written to the HTTP response, header row first. The response has `Content-Type: text/csv` and `Content-Disposition: attachment`, with a filename built from the report name.
- **State kept:** none. No row is written and no object is stored.
- **Work:** read the first page before sending headers. Stop at 10,000 rows as a backstop.
- **If it fails:** before headers are sent, return 503. After they have started, abort the connection instead of ending it normally, so the browser reports an error rather than saving a truncated file.

### 5. Large export: start or reuse

- **Starts:** step 3 sends the request here.
- **Data moves:** one row is inserted into `report_exports` with status `queued`, `filters` and `cols`. The job payload is only `{export_id}`.
- **Work, in order:**
  1. In one transaction, mark this user's stale rows for this report as `failed` with error "stale". A row is stale when either:
     - it is `queued`, has no `job_id`, and `created_at` is more than 5 minutes old (the process died before `job_id` was stored); or
     - it is `running` and `started_at` is more than 2 hours old. No live attempt lasts that long: an attempt is killed at 30 minutes, and 3 attempts plus the waits total about 96 minutes.

     Queued rows that have a `job_id` are never stale.
  2. If this user has a `queued` or `running` export for this report, return it with HTTP 200 and enqueue nothing.
  3. Otherwise insert a new `queued` row and commit.
  4. After the commit, call `enqueue("report_export", {export_id})` and store the returned `job_id` on the row. Enqueueing after the commit means the job never starts before its row is visible.
  5. Return HTTP 202 with `export_id` and status.
- **Concurrent clicks:** the unique index rejects the second insert. Catch that error, reread the row and return the winner.
- **If it fails:**
  - If `enqueue` raises, mark the row `failed` with error "could not queue" and return 503.
  - If the process dies before `job_id` is stored, the next click's step 5.1 marks the row `failed`. If its job still runs, step 6.1 sees `failed` and exits.

### 6. Job attempt: begin

- **Starts:** the queue runs the `report_export` handler for attempt 1, 2 or 3. The payload gives `export_id`.
- **Data moves:** the handler reads the export record from the primary by `export_id`. It holds the `filters` and `cols` saved in step 5, which every later step uses. This is not report data.
- **Work, in order:**
  1. If status is `done`, go to step 9. If `failed`, exit. If `queued` or `running`, continue.
  2. Check that the user still holds `report.view` on the workspace. If not, mark the row `failed` with error "access removed" and exit.
  3. Run a conditional update that sets status `running`, `attempt` to the current attempt number and `started_at` to now, where status is `queued` or `running`. If no row changed, exit. A retry after a crash finds the row `running` and passes this step.
  4. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore a "not found" reply.
  5. Set `object_key` to `exports/{workspace_id}/{report_id}/{export_id}.csv`. The key includes the export id, so one export never overwrites another's file. Call `start_multipart` and store the returned `upload_id`.
- **If it fails:** any error here counts as a failed attempt, and the queue retries from step 6.

### 7. Job attempt: stream rows into parts

- **Starts:** step 6 has finished.
- **Data moves:** rows are read from the replica in keyset batches of 5,000, filtered and ordered by the saved `filters` and `cols` through the step 1 module. Each batch is converted to CSV bytes and appended to one in-memory buffer. When the buffer reaches 16 MB, it is sent with `upload_part(upload_id, part_number, bytes)` and its etag is kept. The header row goes first in part 1. After the last batch, the rest of the buffer is sent as a final part, which may be under 16 MB.
- **State kept:** only the buffer and the etags. The export row is not written during this step.
- **Memory:** one 16 MB buffer, one batch and a list of etags (about 60 for a 900 MB file). The whole report is never held. Step 12 measures the peak.
- **Time:** 2 million rows in 1,800 s needs about 1,100 rows per second, or about 0.5 MB per second. The queue keeps no progress, so a job that is too slow fails on every attempt. Step 12 measures this before release.
- **If it fails:** an exception, a timeout or a worker crash ends the attempt, and the queue retries from step 6. The incomplete upload is invisible, step 6.4 aborts it, and the bucket's 24-hour rule removes anything left over.

### 8. Job attempt: publish the file

- **Starts:** every batch has been read and the last part uploaded.
- **Data moves:** `complete_multipart(upload_id, etags)` makes the object visible at `object_key`. Then a conditional update sets status `done` and `finished_at` to now, where status is `running`.
- **State kept:** the export row.
- **If it fails:**
  - If `complete_multipart` fails, the attempt fails and the queue retries from step 6. No link has been issued.
  - If the process dies after the complete call but before the row is `done`, the next attempt finds the row `running` and repeats steps 6 to 8 with the same key. That replaces the object with equivalent content before any link is issued.

### 9. Email the download link

- **Starts:** the row is `done` and `notified_at` is empty. This follows step 8, or a retry that finds the row already `done`.
- **Data moves:** `send_email(user_id, "report_export_ready", {export_id, report_name, download_url, expires_at})`. `expires_at` is `finished_at` plus 24 hours. `download_url` is `signed_url("exports", object_key, ttl)`, where `ttl` is the seconds left until `expires_at`, so a late retry gets a shorter link that ends at the same time. Object storage serves the URL, so the browser downloads from the bucket directly.
- **State kept:** `notified_at` is set after `send_email` returns.
- **If it fails:** the attempt raises and the queue retries. The next attempt finds the row `done` with `notified_at` empty and comes straight to this step. If the final attempt's email fails, the row stays `done`, so the page still offers the download (step 11). Log the error. A duplicate email is possible only if the send succeeds and the `notified_at` write fails. This is accepted.

### 10. Final failure

- **Starts:** the queue calls `on_final_failure` once, after attempt 3 has failed.
- **Work, in order:**
  1. If status is `done`, change nothing and log. Step 9 is the only work left.
  2. Otherwise run a conditional update that sets status `failed`, `finished_at` to now and `error` to the exception type and message, cut to 500 characters, where status is not `done`.
  3. Call `abort_multipart` on `upload_id`, best effort, ignoring errors.
  4. Call `send_email(user_id, "report_export_failed", {export_id, report_name})`, then set `notified_at`.
- **If it fails:** if the step 2 write fails, the row stays `running`. Its `started_at` ages past 2 hours, and step 5.1 marks it `failed` without sending an email. If only the email fails, the page still shows `failed`.

### 11. Page status and download

- **Starts:** page load, a Download CSV click that returns from step 5, or polling.
- **Data moves:** `GET /api/reports/{report_id}/exports/latest` checks `report.view` and reads the user's newest export for this report (by `created_at`) from the primary. The response holds `status`, `attempt`, `filters`, `finished_at` and, when the export is `done` and less than 24 hours old, a fresh `download_url` signed for the time left. Because `filters` is returned, the page can say which filters the export used.
- **Display:**
  - `queued`: "Queued".
  - `running`: "Running, attempt n of 3".
  - `done` within 24 hours: "Ready", with a download link and its expiry time.
  - `done` after 24 hours: "Link expired. Start a new export."
  - `failed`: "Export failed", with a button that starts a new export through step 5.
- **After a failure:** step 5 inserts a new row. The failed row is not active, so it does not block the new one. Old rows stay as history.
- **Polling:** every 5 seconds while the status is `queued` or `running`. Polling pauses while the tab is hidden and stops at `done` or `failed`. A later visit loads the newest row.
- **State kept:** the server row. The browser keeps nothing extra. The URL still carries only `filters` and `cols`.
- **If it fails:** a failed status request shows "Status unavailable, retrying" and keeps polling with growing delays. Download links are served by the bucket and are not affected.

### 12. Verify before release

- **Unit tests:** CSV quoting, header order, column whitelist, and keyset paging across batch boundaries with no missing or duplicate rows.
- **Concurrency test:** two simultaneous clicks produce one export row and one job.
- **Fault injection:** stop the worker at the start of an attempt, mid-upload, before `complete_multipart`, and after `complete_multipart` but before `done`. Also make the email fail. In every case no partial file may be downloadable, the final state must be correct, and each export sends at most one email.
- **Performance test:** run the job alone on the largest report (about 2 million rows). It must finish within 1,800 s with a clear margin. Measure peak memory against the 512 MB limit.
- **Routing test:** no report row query reaches the primary.
- **Stale count test:** with a deliberately stale `row_count`, confirm the guard in step 3.4.

### 13. Release and watch

- Count exports by status and by time to finish. Alert on the failure rate.
- Build no cleanup job. The bucket's 7-day lifecycle rule removes old files.

## Open questions

1. **One export per report, not per filter.** A second click while an export is active returns that export, even if the filters differ. The response states its filters so the page can say so. The alternative is to put the filters in the uniqueness key.
2. **`row_count` is nightly.** Step 3.4 adds a bounded count on the replica before streaming. This goes beyond the brief. Confirm it.
3. **Nightly rebuild during a job.** If the rebuild changes `row_id` values, a keyset read that spans it can miss or repeat rows. Confirm the rebuild window, or block exports while it runs.
4. **Throughput.** The queue keeps no progress, so if 2 million rows cannot finish in 1,800 s, no retry will help. If step 12 measures too slow, the fix is resumable jobs, which the brief excludes. Decide the fallback before building.
5. **Email templates.** `report_export_ready` and `report_export_failed` are assumed names. Confirm them or create them.
6. **Header labels and CSV injection.** The header uses the page's column labels. Decide whether cells starting with `=`, `+`, `-` or `@` are neutralised.
7. **Permission re-check and bearer links.** Step 6.2 re-checks `report.view` when the job starts, which goes beyond the brief. Anyone holding a 24-hour link can download the file. Confirm both choices.
8. **Overlapping deliveries.** Delivery is at least once, so two attempts of one job could run at the same time. Step 6.4 could then abort the other attempt's upload. Not decided.
9. **Where the permission record lives.** The brief's files do not say which database the `report.view` check reads. Not known. Step 3 uses the same check as the page API.