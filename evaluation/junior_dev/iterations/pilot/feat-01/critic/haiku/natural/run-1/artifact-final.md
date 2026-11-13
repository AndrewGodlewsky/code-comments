# CSV export for the reports page: implementation plan

## Summary

A **Download CSV** button on `/reports/{report_id}` exports the rows the user is looking at: the filters and column order from the page URL, plus a header row. The click takes one of two paths, chosen by `reports.row_count`:

- **Small (`row_count` of 10,000 or fewer):** the API builds the CSV and returns it in the same response. Nothing is stored.
- **Large (`row_count` over 10,000, up to `MAX_EXPORT_ROWS`):** the API records an export in a new `report_exports` table, queues a background job, and returns at once. The job writes the CSV to the `exports` bucket in parts, marks the export `done`, and emails the user a download link. The page shows the export's state until it is done, expired, or failed.

Recovery uses one shared function, `reconcile` (step H3), called from three places: the click, the page's poll, and a new 5-minute sweep. The sweep is the only background work added beyond the export job itself. It fails stuck exports, re-queues exports whose job was never enqueued, and retries unsent emails. It deletes no files.

The only new server state is the `report_exports` table. The view (filters and columns) stays in the URL.

## Fixed requirements

These come from the feature request. This plan does not change them.

1. **Contents:** the filters and column order from the page URL, plus a header row. The export uses the same `report.view` check as the page. Report rows are read only from the read replica.
2. **Two paths by size:** decided by `reports.row_count`. At 10,000 rows or fewer, the response is the CSV. Above 10,000, the click returns at once and a background job builds the file.
3. **Large exports:** the job writes the file to the `exports` bucket and emails a download link that works for 24 hours, using the existing `send_email(user_id, template, params)`. Deleting old files is left to the bucket's lifecycle rule. No file-cleanup job is built.
4. **Status on the page:** queued, running, done or failed, including when the user returns later.
5. **One at a time:** a user may have only one large export of a given report queued or running. A click while one is active returns that export.
6. **Limits:** a worker has 512 MB of memory and the largest report has about 2 million rows. The job never holds a whole report in memory and finishes within the queue's attempt timeout.
7. **Failure:** use the queue's normal retries. A half-written file is never downloadable. When the last attempt fails, email the user and show the export as failed.

**Out of scope:** scheduled exports, formats other than CSV, and changes to the table on the page.

## Terms

- **Read replica:** a copy of the primary database that serves reads. Report rows are read only from it. Job state is written only to the primary.
- **Queue:** the background job system. Each run of a job's handler is an **attempt**. The queue makes at most 3 attempts, waits 60 s before attempt 2 and 300 s before attempt 3, and ends any attempt that runs longer than 30 minutes. The queue calls the final-failure hook once, after attempt 3 fails.
- **Keyset paging:** fetching the next page as `WHERE row_id > last ORDER BY row_id LIMIT n`. It avoids OFFSET, so late pages are as fast as early ones.
- **Multipart upload:** the bucket receives one file as numbered parts. Nothing is visible at the final key until the parts are joined. Every part except the last must be at least 5 MB.
- **Run token:** a random ID written when an attempt claims the export. Every write by an attempt is conditional on the run token still being its own. A newer claim therefore fences off an older attempt.
- **Heartbeat:** a conditional write of `updated_at` that shows the current run is alive.
- **Stale:** a queued or running export whose `updated_at` is older than `STALE_AFTER`.
- **Active:** status is queued or running.
- **object_exists(bucket, key):** a new storage helper that returns true when a visible object is at the key. It checks metadata and does not download the object.

## Decisions

| Question | Decision |
|---|---|
| One active export, and filters | One active large export per user and report. A click while one is active returns that export. The page compares its filters with the current URL. If they differ, the panel says "An export with different filters is running" and offers Cancel. The page never starts an export by itself. The alternative, rejecting the click with 409, was rejected because the user would then have no way to reach the running export from the page. |
| Changes to filters or columns during a run | The export keeps the filters and columns it was created with. The page shows those, not the current URL, and the filter-mismatch panel covers the difference. |
| Small path while a large export is active | The small path ignores active exports. The one-at-a-time rule covers large exports only. |
| Threshold uses unfiltered rows | Kept, as required. A selective filter on a large report still runs in the background. The panel says before the click that large reports are built in the background and emailed. Revisit if users report it often. |
| Rebuild during a run | Each run reads `reports.rebuilt_at` when it claims the export and stores it as `data_version`. It is checked before each part and before completion. A change makes the attempt raise, and the retry starts with the new value. The small path checks it at the start and end of its read. |
| Replica lag | The rebuild writes rows and `rebuilt_at` in one transaction (A3), and the replica applies each transaction atomically (A5). So any rows read after a `rebuilt_at` change are from the new data, and the final check catches any change that happened during the run. A stale `row_count` can only change the path. |
| CSV formula injection | Any cell whose first character is `=`, `+`, `-`, `@`, tab or carriage return gets a leading apostrophe. Applied on both paths. Negative numbers also get the apostrophe. This is an accepted cost for safety in Excel. |
| Encoding | UTF-8 with a byte-order mark, so Excel reads non-ASCII text correctly. |
| Row retention | `report_exports` rows are kept. Each large export adds one row. Revisit at 1 million rows. An owner must be named (see Open items). |
| Benchmark misses the 15-minute target | No resume in v1. The first fallback is parallel part upload with at most 4 parts in flight, which adds 64 MB of buffers. Resuming from saved progress is rejected for v1, because it would depend on `row_id` staying stable across rebuilds. |
| Status during retry waits | The row stays `running`. The page shows the last attempt that started, for example "attempt 1 of 3" during the wait before attempt 2. The queue has no retry hook, and adding one is out of scope. |
| Email fails after `done` | The status stays `done`, so the page still offers the file. The attempt raises and the queue retries it. The sweep retries unsent emails. After 24 hours without a sent email, the sweep alerts operations. |
| Email templates | `csv_export_ready` with `{report_id, export_id, download_url, link_expires_at, file_expires_at}`. `csv_export_failed` with `{report_id, export_id, error_summary}`. |
| Download window | The emailed link lasts 24 hours from the moment it is created. The page's Download button also works for 24 hours from `completed_at`, the same window the brief sets for the email. After that the download endpoint returns 410 and the page offers a new export. This is a product decision to confirm (see Open items). |
| Maximum size | 2,000,000 rows (provisional, equal to the largest report today). POST returns 413 above it. A larger report needs a new decision. |
| Cancel | The only way to abandon a running export. Nothing is replaced automatically. |
| Feature flag off | Every export endpoint returns 404, as required. Exports already running finish on the workers or go stale under step H3. Emailed links keep working until they expire, because they do not pass through the endpoint. The sweep keeps running when the flag is off, because it is a worker job, not an export endpoint. |
| Revoked access | An emailed link is a bearer URL and still works until it expires, at most 24 hours after it was sent. Page downloads check permission on every request. This is accepted. |

## Constants

- `SMALL_MAX_ROWS` = 10,000
- `SMALL_MAX_BYTES` = 16 MB, the largest CSV the small path builds in memory (proposed)
- `SMALL_MAX_CONCURRENT` = 4 small builds per API process (proposed). Extra requests get 503 with "try again shortly".
- `MAX_EXPORT_ROWS` = 2,000,000 (provisional)
- `MAX_COLUMNS` = 30 and `MAX_VALUE_CHARS` = 200 for filter values and column names (proposed, to be confirmed before step 1)
- `MAX_QUERY_BYTES` = 2 KB
- Replica page size: 500 rows (small path), 1,000 rows (job). The job page is smaller than before because row size is not capped by this plan (see step 7).
- Replica query timeout: 30 s per page. Part upload timeout: 120 s per call.
- Part buffer: 16 MB
- `MAX_ATTEMPTS` = 3. Attempt timeout: 30 min. Retry waits: 60 s, then 300 s.
- `ENQUEUE_GRACE` = 2 min
- `SWEEP_INTERVAL` = 5 min
- `STALE_AFTER` = 120 min (derived in step H3)
- Poll interval: 5 s
- Link TTL: `min(24 h, file_expires_at - now)` for email; `min(24 h, completed_at + 24 h - now)` for page downloads.
- File expiry: 7 days (bucket rule). Stored as `file_expires_at`.

## Assumptions to verify before building

- **A1 (attempt timeout).** The queue ends any attempt no later than 30 minutes after it starts. It starts no retry until the ended attempt is gone. The stale bound (step H3) and the timing of the final hook depend on this. Verify with the queue's owner before step 2. If it does not hold, the final hook must wait for the worker to confirm it has stopped, and `STALE_AFTER` must grow.
- **A2 (pickup delay).** The time from a job becoming due (enqueue, or the end of a retry wait) to a worker starting it is at most 50 minutes (P_max). Verify from queue metrics. If it does not hold, `STALE_AFTER` must be at least 30 + 5 + P_max, plus a 35-minute margin.
- **A3 (rebuild).** The nightly rebuild writes the report rows and `reports.rebuilt_at` in one transaction. If `rebuilt_at` does not exist, step 1 adds it and changes the rebuild.
- **A4 (database).** The primary database is PostgreSQL, which supports partial unique indexes. If not, stop and redesign around a lock row before step 1.
- **A5 (replica).** The replica applies each primary transaction atomically and in order, with bounded lag. Verify with replica monitoring before step 2.
- **A6 (row size).** The average selected row is under 1 KB. This is unverified. The benchmark (step 13) records the largest row on production data. If the largest row times the job page size exceeds 50 MB, the page size drops until it does not.
- **A7 (scheduler).** The platform can run a job every `SWEEP_INTERVAL`. If not, a scheduler is added in step 1. Without it, stuck exports are recovered only on click or poll.

## State rules

Every change to `status` is a conditional update. A handler whose update matches zero rows changes nothing more and returns normally.

| From | To | Caused by | Condition |
|---|---|---|---|
| (none) | queued | Insert, step 5.2 | The partial unique index rejects a second active row. |
| queued (no job_id) | queued (job_id set) | Enqueue saved, step 5.3, or re-enqueue by H3 | `job_id` is null. Does not change `status` or `updated_at`. |
| queued, running | running | Claim, step 6.6 | `status` in (queued, running). Sets `attempt`, `run_token`, `data_version`. |
| running | running | Heartbeat, steps 6.6, 7.4, 8.2 | `status` = running AND `run_token` = the attempt's own token. Only `updated_at` (and, in step 7.2 and 8.3, `file_key` or `file_expires_at`) changes. |
| queued, running | done | Finish, H1 | `status` in (queued, running). Clears `upload_id`. |
| done | done (email) | Email sent, H2 | `email_sent_at` is null. Changes only `email_sent_at`. This is not a status transition. |
| queued, running | failed | Enqueue failure (5.3), no access (6.5), cancel (10), stale (H3), final failure (11.5) | `status` in (queued, running). |
| done, failed | (none) | Terminal | `done` never becomes `failed`. `failed` never changes. |

Only queued and running rows block a new export.

## Shared helpers

These are used by several steps. Each is defined once here.

**H1 `finish_if_uploaded(row)`.** Used by steps 6.4, 8.4 and 11.4.
1. If `file_key` is not set, or `object_exists(exports, file_key)` is false, return "not finished".
2. Conditional update: status in (queued, running) to done, `completed_at` = now, `upload_id` cleared. If zero rows match, return "not finished".
3. Call H2. Return "done".

**H2 `send_email_once(row)`.** Used by steps 8.5, 6.3 and the sweep.
1. If `email_sent_at` is set, stop.
2. Create the link: `signed_url(exports, file_key, min(86400, file_expires_at - now))`.
3. Call `send_email(user_id, csv_export_ready, {...})`.
4. Set `email_sent_at` = now. Changes only that field.
- If the send raises, the caller raises. The retry sends again.
- The signed URL goes only into the email. It is not stored.

**H3 `reconcile(row)`.** Used by step 5.1 (click), step 10 (poll) and the sweep. Each call is idempotent.
1. If the row is not active, stop.
2. If the row is queued, `job_id` is null, and `created_at` is older than `ENQUEUE_GRACE`, the enqueue never completed. Enqueue `csv_export` with `{export_id}`. Conditional update: set `job_id` where `job_id` is null. The handler tolerates a duplicate job (step 6).
3. If `updated_at` is older than `STALE_AFTER`, call H4 with summary "The export stopped responding." and notify = true.

**H4 `fail_export(row, summary, notify)`.** Used by steps 5.3, 6.5, 10 (cancel, notify = false), H3 and 11.5.
1. Conditional update: status in (queued, running) to failed, `completed_at` = now, `error_summary` = summary. If zero rows match, stop without sending email.
2. If `upload_id` is set, call `abort_multipart`. Ignore errors.
3. If notify, send `csv_export_failed` with `{report_id, export_id, error_summary}`. Only the caller that set the row to failed sends this, so there is one failure email.

## Plan

### 1. Migration and prerequisites

- **Starts:** the first deploy. Nothing else ships before it.
- **Checks first:** A3, A4, A5, A7 hold. The `report_rows` table has an index on `(report_id, row_id)`, which the page already uses. Add the `object_exists` helper to `storage.py`. Confirm `MAX_COLUMNS`, `MAX_VALUE_CHARS` and `SMALL_MAX_BYTES` with the product owner.
- **Data:** create `report_exports` with `id`, `user_id`, `report_id`, `filters` (normalised query string), `cols`, `status` (queued, running, done, failed), `attempt`, `run_token`, `job_id`, `upload_id`, `file_key`, `data_version`, `error_summary`, `created_at`, `started_at`, `updated_at`, `completed_at`, `file_expires_at`, `email_sent_at`. If `reports.rebuilt_at` does not exist, add it, and change the nightly rebuild to set it in the same transaction as the rows.
- **Indexes:** a partial unique index on `(user_id, report_id)` WHERE `status` IN (queued, running). A second index on `(user_id, report_id, created_at)` for the latest-export lookup.
- **Scheduler:** register the sweep (H3 over all active rows, and H2 for done rows with unsent email) to run every `SWEEP_INTERVAL`. The sweep deletes no files.
- **State:** the primary database. This is job state, not report data.
- **On failure:** the migration fails and the deploy stops. Nothing uses the table yet.

### 2. Shared CSV format

- **Starts:** called by step 4 (small path) and step 7 (job).
- **Rules:**
  - The header row lists the `cols` names in the order given.
  - Each value is written by Python's `csv` module with default quoting. It handles commas, quotes and newlines inside fields.
  - A value whose first character is `=`, `+`, `-`, `@`, tab or carriage return gets a leading apostrophe.
  - The output begins with a UTF-8 byte-order mark.
  - Lone surrogates in values are replaced with U+FFFD, so encoding cannot fail.
  - A query that matches no rows still produces the header row.
- **Data:** row values in, bytes out. No state.
- **On failure:** no expected failures. Any other exception propagates to the caller, which fails its own path.

### 3. POST `/api/reports/{report_id}/exports`: validate and choose the path

- **Starts:** the user clicks **Download CSV**. The request carries only the page's query string. No row data is sent.
- **Steps, in order:**
  1. If the feature flag is off, return 404.
  2. Load the report. If it does not exist, return 404.
  3. Check `report.view` on the report's workspace. Without it, return 403. This is the same check the page uses.
  4. Parse `filters` and `cols` with the page's parser. Return 400 for an unknown column name, more than `MAX_COLUMNS` columns, a filter value or column name longer than `MAX_VALUE_CHARS`, or a query string over `MAX_QUERY_BYTES`. Column names are checked against the report's columns, so they never reach SQL unchecked.
  5. Read `reports.row_count` from the read replica. If it is above `MAX_EXPORT_ROWS`, return 413 with the message that the report is too large to export.
  6. If `row_count` is `SMALL_MAX_ROWS` or less, go to step 4. Otherwise go to step 5.
- **Data moved:** the query string and one number.
- **State:** nothing is written.
- **On failure:** 400, 403, 404 and 413 return to the browser. Nothing is stored.

### 4. Small path: build the CSV in the response

- **Starts:** step 3.6 chose the small path.
- **Steps:**
  1. If `SMALL_MAX_CONCURRENT` builds are already running in this API process, return 503 "try again shortly".
  2. Read `reports.rebuilt_at` from the replica. Call it `v0`.
  3. Read keyset pages of 500 rows from `report_rows` on the read replica, with the filters applied and ordered by `row_id`: `WHERE row_id > last ORDER BY row_id LIMIT 500`.
  4. Format each page with step 2 into an in-memory buffer.
  5. If the buffer grows past `SMALL_MAX_BYTES`, stop and return 413 with the message that the export is too large to download directly and that fewer columns may help.
  6. If more than `SMALL_MAX_ROWS` rows are read, stop and return 409 with the message that the report changed while the export was being built, so the user should click again. This can only happen if `row_count` was stale.
  7. Stop when a page returns fewer than 500 rows.
  8. Read `reports.rebuilt_at` again. If it differs from `v0`, return 409 with the same message as step 6. A rebuild committed during the read is caught here, so the response never mixes two versions of the data.
- **Response:** 200 with `Content-Type: text/csv; charset=utf-8`, `Content-Length`, and `Content-Disposition: attachment` with a filename built from the report name (sanitised) and the date. The body is built completely before the response starts, so a cut-off response can never look like a complete file.
- **Data moved:** replica rows to API memory to the response.
- **State:** none.
- **Memory:** bounded by `SMALL_MAX_BYTES` plus one 500-row page. With the concurrency cap, one API process holds at most 4 × (16 MB + page + encoding copies), about 100 MB. The API worker's memory limit must be checked against this in step 1.
- **On failure:** a replica error, or a request killed at the 60-second API limit, returns an error. The user sees a message and clicks again. Nothing is stored, so nothing needs cleanup. The small-path benchmark in step 13 checks the margin.

### 5. Large path: create or return the export

- **Starts:** step 3.6 chose the large path.
- **Steps:**
  1. Find the active row for `(user_id, report_id)`. If one exists, call H3 on it. If it is still active after H3, return it with 202 (substep 4 format). Start nothing new. If H3 failed it, continue to substep 2.
  2. Insert a row with status queued, `filters`, `cols`, `created_at` = now, and `updated_at` = now. If the insert hits the unique index because another click won the race, read the winning row and return it with 202.
  3. Enqueue job `csv_export` with the payload `{export_id}` only. The job reads everything else from the row. Save the returned `job_id` on the row.
  4. Return 202 with `export_id`, `status`, `attempt`, `filters` and `cols`. The page compares `filters` with the current URL (see step 10).
- **Data moved:** one row written to `report_exports`.
- **State:** `report_exports`, as in the state rules.
- **On failure:**
  - If enqueue raises, call H4 with "could not start" and notify = false, and return 503. The user is watching the request, so no email is sent.
  - If the process dies between the insert and the enqueue, the row stays queued with `job_id` null. The sweep re-enqueues it after `ENQUEUE_GRACE` (H3, substep 2). The user does not need to act. This replaces the earlier "90 minutes blocked" case.
  - If the process dies after the enqueue but before `job_id` is saved, the sweep enqueues a second job. Both jobs call the handler. The claim in step 6.6 fences one of them off, so the file is still built once.

### 6. Attempt start (the `csv_export` handler)

- **Starts:** the queue runs `csv_export(ctx, payload)` on a worker. `ctx.attempt` is 1, 2 or 3.
- **Steps:**
  1. Load the row by `export_id`. If it is missing, log it and return normally.
  2. If the status is `failed`, return normally. The export was cancelled, went stale, or this is a duplicate delivery.
  3. If the status is `done`, call H2 and return normally.
  4. If `file_key` is set and `object_exists(exports, file_key)` is true, an earlier attempt completed the file. Call H1. Return normally. This runs before the claim, so the stored `data_version` of the completed run is not overwritten.
  5. Check `report.view` for the user, and parse `filters` and `cols` again against the report's current columns. If access is gone, call H4 with "no access to this report" and notify = true. If the columns no longer parse, call H4 with "report columns changed" and notify = true. Return normally. Neither failure is retried, because the condition will not change.
  6. Claim: conditional update where status is queued or running. Set `status` = running, `attempt` = ctx.attempt, `run_token` = a new random value, `started_at` if null, `updated_at` = now, and `data_version` = `reports.rebuilt_at` read from the replica. If zero rows match, return normally. A later claim overwrites `run_token`, so any older attempt stops at its next heartbeat.
  7. Go to step 7.
- **Data:** the row, plus one value from `reports`.
- **State:** `status`, `attempt`, `run_token`, `started_at`, `updated_at`, `data_version`.
- **On failure:** a database error raises. The queue retries the attempt from step 6. The status remains queued or running.

### 7. Write the file in parts

- **Starts:** step 6.7.
- **Steps:**
  1. If `upload_id` is set from an earlier attempt, call `abort_multipart` on it. Ignore errors. The upload may already be complete or gone.
  2. Call `start_multipart(bucket=exports, key=report-{report_id}/export-{export_id}/{run_token}.csv)`. The key includes the run token, so no two attempts can ever write the same object. Save `upload_id` and `file_key` on the row before any part is uploaded. This save is a heartbeat (conditional on `run_token`).
  3. Put the header from step 2 into an in-memory buffer.
  4. Repeat until a page returns fewer than 1,000 rows:
     a. Heartbeat: conditional update of `updated_at` where status = running and `run_token` = own token. If zero rows match, the export was cancelled or taken over. Call `abort_multipart`, ignore errors, and return normally.
     b. Read the next 1,000 rows by keyset from the replica, with filters: `WHERE row_id > last ORDER BY row_id LIMIT 1000`. The query has a 30-second timeout. Format them with step 2 and append them to the buffer.
     c. When the buffer reaches 16 MB, do these checks, then upload the part:
        - Data version: read `reports.rebuilt_at` from the replica. If it differs from `data_version`, raise. The retry reads the new value.
        - Call `upload_part` with a 120-second timeout. Keep the returned etag with its part number. Clear the buffer.
  5. Upload the remaining buffer as the final part. It may be under 5 MB, because only non-final parts must be that large. Step 8 checks the export before completion.
- **Data moved:** replica rows to worker memory (CSV text) to bucket parts. No local disk.
- **Memory budget (the sum of the parts, not one estimate):**
  - Part buffer: 16 MB.
  - One page of 1,000 rows at the average row size (A6, under 1 KB): about 1 MB. If rows are as large as the worst case allowed by the schema (30 columns of 200 characters, 4 bytes each), one page could reach 24 MB. The benchmark measures the real largest row (A6).
  - Encoding copies of the buffer during `upload_part`: up to 16 MB more.
  - Interpreter and client libraries: assume 50 MB.
  - Total: about 60 MB at the average row size, about 100 MB at the schema's worst case. The design target is under 200 MB of the 512 MB worker.
- **Parallel-upload fallback:** with 4 parts in flight, the buffers add 4 × 16 MB = 64 MB. That keeps the total under the 200 MB target.
- **Parts:** 2 million rows at the average size is about 60 parts, far below the 10,000-part limit. Even at the worst-case row size, the part count stays under 3,000.
- **Replica use:** each page is a separate short query. No transaction is held open on the replica.
- **State:** `upload_id` and `file_key` on the row. Parts stay in the bucket until the upload is completed or aborted.
- **On failure:**
  - Exception (database, upload, timeout, or check error): make a best-effort `abort_multipart` in an exception handler, ignoring errors, then raise. The queue retries from step 6.
  - Timeout kill or worker death: no handler code runs. The unfinished upload is aborted by the next attempt's substep 1, or discarded by the bucket's 24-hour rule for unfinished uploads.
  - Throughout, nothing is visible at the final key until step 8.3 succeeds.

### 8. Finish the file

- **Starts:** the final part is uploaded (step 7.5).
- **Steps:**
  1. Data version: read `reports.rebuilt_at` from the replica. If it differs from `data_version`, raise.
  2. Heartbeat: the same conditional update as step 7.4a. If zero rows match, call `abort_multipart`, ignore errors, and return normally. The export was cancelled or taken over meanwhile.
  3. Save `file_expires_at` = now + 7 days on the row. Take the time just before the next call. The bucket counts from the object's creation, which is slightly later, so this estimate is conservative. Then call `complete_multipart(upload_id, etags)`. This joins the parts and makes the object visible at its key.
  4. Call H1 `finish_if_uploaded`. If it returns "not finished", the export was cancelled or failed during completion. Stop without sending email.
  5. Call H2 `send_email_once`. Return normally.
- **State:** the object in the bucket, and the row.
- **On failure:**
  - Step 8.1 or 8.2 finds a change: the attempt stops as described above.
  - `complete_multipart` fails: the object is not visible. The attempt raises. The retry aborts the upload (step 7.1) and starts over under a new run token.
  - `complete_multipart` succeeds but step 8.4 fails: the object is visible and the row still says running. The attempt raises. The retry's step 6.4 finds the object and calls H1, which marks the row done without rebuilding the file. The file came from a run that passed step 8.1.
  - `complete_multipart` succeeds but the row is cancelled or failed first: no row is done, so the app offers no download. The object sits under a per-run key and is deleted by the bucket's 7-day rule. Nothing is overwritten, because the key is unique to the run.

### 9. Email the download link

- **Starts:** H2 is called from step 8.5, from step 6.3 (a retry that finds `done`), from H1, or from the sweep.
- **Steps:** as H2 above.
- **On failure:**
  - If `send_email` raises, the attempt raises and the queue retries it. The retry reaches step 6.3, sees `done`, and sends again.
  - If the sweep finds a done row with no email after 24 hours, it alerts operations. The status stays `done`, so the page still offers the file.
  - A send that succeeds but whose `email_sent_at` update fails can send a second email on retry. This is accepted, because email delivery is at least once.

### 10. Show the export state, cancel, and download

- **Starts:** the page loads. It polls every 5 seconds while the latest export is active. Polling stops at done, failed or none.
- **Endpoints:**
  - `GET /api/reports/{report_id}/exports/latest`: checks `report.view`. Calls H3 on the caller's latest export for this report if that export is active. Then returns it: `export_id`, `status`, `attempt`, `filters`, `cols`, `created_at`, `completed_at`, `available_until`, and `download_url` (the download endpoint's path) when the export is done and still available. `available_until` = min(`completed_at` + 24 h, `file_expires_at`).
  - `POST /api/reports/{report_id}/exports/{export_id}/cancel`: only the export's owner may call it. Call H4 with "cancelled by user" and notify = false. A running attempt stops at its next heartbeat and does not finish the file. Like every export endpoint, this returns 404 when the flag is off. The sweep handles rows left behind.
  - `GET /api/reports/{report_id}/exports/{export_id}/download`: checks `report.view` and ownership. If the status is not done, return 404. If `now` is at or past `available_until`, return 410. Otherwise redirect to a fresh `signed_url` with TTL = `min(86400, completed_at + 86400 - now)`.
- **Filter comparison:** the page compares the export's `filters` and `cols` with the current URL after normalising both with the step 3 parser. Raw string comparison is not used.
- **Displayed states:**
  - queued: "Waiting to start." Cancel button.
  - running: "Building your CSV (attempt N of 3)." Cancel button. N is the last attempt that started.
  - queued or running with filters different from the current URL: "An export with different filters is running." Cancel button. The page does not start a new export. After Cancel, the user clicks Download CSV again.
  - done and available: "Download CSV" and "Available until {available_until}." The button goes to the download endpoint, which issues a fresh link each time.
  - done and no longer available: "This file is no longer available. Start a new export."
  - failed: "The export failed." If `error_summary` is "cancelled by user", show "Export cancelled." instead. Button to start a new export.
- **Data:** nothing new. Everything comes from the row.
- **State:** none.
- **On failure:** a failed poll keeps the last state on screen and tries again on the next tick. If storage has deleted the object early, the signed URL returns an error, and the page shows the no-longer-available message.

### 11. Final failure hook

- **Starts:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails. A1 guarantees that no attempt is still running.
- **Steps:**
  1. Load the row. If it is missing, stop.
  2. If the status is `done`, log the error, alert operations, and stop. The file exists, so the page still offers it. The sweep handles any unsent email.
  3. If the status is `failed`, stop. This is a duplicate call, or the export was cancelled or went stale.
  4. Call H1 `finish_if_uploaded`. If it returns "done", the last attempt completed the object. Stop.
  5. Otherwise call H4 with "The export could not be built after 3 attempts." and notify = true. Write the raw error to the logs only.
- **State:** the terminal status. The unique index covers only queued and running, so the user can start a new export at once.
- **Timing:** the worst case is three 30-minute attempts plus the 60 s and 300 s waits, which is 96 minutes, plus pickup delays (A2).
- **On failure:** if the hook itself raises, the row stays running. The sweep fails it through H3 once its `updated_at` is older than `STALE_AFTER`. The failure email then arrives late, but it is not lost. The hook's error is logged and operations are alerted.

### 12. Stale rule (H3)

- **Purpose:** recover rows whose job was lost, whose worker died, or whose attempt was ended without the hook running. The queue's own failure state does not cover these cases, because the hook never runs when a worker dies. So a time-based rule stays. It is the only rule that does not depend on a user returning.
- **Rule:** an active row whose `updated_at` is more than `STALE_AFTER` (120 minutes) old is stale. H3 fails it through H4 with notify = true. The winner of the conditional update is the only caller that sends the email.
- **Where it runs:** the sweep (every 5 minutes, for every active row), step 5.1 (on click) and step 10 (on poll). The sweep means a user who never returns still gets the failure email on time.
- **Heartbeats:** the row's `updated_at` moves at insert (5.2), at claim (6.6), at each page read (7.4a), at the part-start check and file save (7.2 and 7.4a), and at the final check (8.2).
- **Largest healthy gap between heartbeats.** Three cases:
  - Waiting for the first attempt: at most P_max = 50 min (A2), from the insert.
  - Running: each call has a timeout (30 s for a page read, 120 s for a part upload), so a healthy attempt heartbeats at least every 3 minutes. The gap is bounded by the call timeouts, not by the 30-minute kill.
  - Between attempts, when an attempt dies silently: the last heartbeat H is no earlier than the attempt's start S. The attempt ends by S + 30 min (A1). Then the retry wait R (at most 300 s) and pickup P (at most 50 min) follow. The gap is at most 30 + 5 + 50 = 85 min. The final-hook path is shorter: 30 + 50 = 80 min.
- **Why 120 minutes:** the largest gap is 85 minutes, which needs A1 and A2 to hold. The plan uses 120 minutes, leaving a 35-minute margin for measurement error. In general, `STALE_AFTER` must be at least 30 + 5 + P_max. If A2 measures a larger P_max, raise `STALE_AFTER` to that bound plus 35 minutes.
- **Healthy exports are never stale.** A healthy attempt heartbeats within about 3 minutes, far below 120. The benchmark (step 13) checks the heartbeat interval.
- **Zombie attempts.** Under A1, an attempt that wrote its last heartbeat at H ends by H + 30 min. The claim fences it off: its `run_token` no longer matches once a newer claim exists, and its output goes to a per-run key. So a zombie cannot overwrite another attempt's file or change the row. If A1 is false, the zombie can still finish its own object, but that object is never offered, because the download endpoint serves only the `file_key` on a done row. The 7-day bucket rule deletes it.
- **Effect on users:** a dead export blocks a new one for at most 120 minutes after its last heartbeat, and for about 5 minutes when the job was never enqueued (the sweep re-enqueues it first). The user can cancel it at once from the page (step 10).

### 13. Tests and rollout

- **Tests (all must pass before rollout):**
  - CSV (step 2): header order follows `cols`. Commas, quotes and newlines are escaped. Formula characters, including a leading minus, get an apostrophe. The byte-order mark is present. Surrogates are replaced. Zero matching rows still produce a header.
  - Path choice: 10,000 rows takes the small path. 10,001 takes the large path. Above `MAX_EXPORT_ROWS` returns 413. A stale `row_count` that hides more than 10,000 rows returns 409 from the small path.
  - Small-path byte cap: output over `SMALL_MAX_BYTES` returns 413. The concurrency cap returns 503 for the fifth concurrent build.
  - Small-path consistency: a rebuild that commits during the read returns 409 and never a mixed file.
  - Permissions: 403 on POST, latest, cancel and download without `report.view`. 404 on an unknown report. 403 on cancel and download by a user who is not the owner. In the job, revoked access marks the row failed and does not retry.
  - Flag: with the flag off, POST, latest, cancel and download all return 404. Emailed links still download until they expire.
  - Validation: 400 for an unknown column, too many columns, an over-long value, and an over-long query string.
  - Concurrency: two simultaneous large clicks create one row. The second returns the first with 202.
  - Stale rule: a running row with `updated_at` 121 minutes old is marked failed by a click, by a poll, and by the sweep, with one failure email. A row with `updated_at` 85 minutes old is left alone.
  - Sweep: a queued row with `job_id` null is re-enqueued after 2 minutes. A done row with no email is sent by the sweep. After 24 hours without a sent email, the sweep alerts operations.
  - Two jobs for one export: the second claim makes the first stop at its next heartbeat. Only one file is offered.
  - Storage: before `complete_multipart`, the key does not exist. After an injected part-upload failure, no object exists at the run's key.
  - Timeouts: a hung `upload_part` raises after 120 seconds. A hung page read raises after 30 seconds.
  - Retries: kill an attempt partway. The next attempt aborts the old upload and completes under its own run token.
  - Rebuild during a run: change `rebuilt_at` after the first page of attempt 1. Step 8.1 raises, and the retry completes with the new `data_version`. The file matches a fresh export of the new data.
  - Replica lag: rebuild commits on the primary and the replica shows it late. The export stays consistent with the data it read, and any change visible during the run is caught by step 8.1.
  - Completion recovery: `complete_multipart` succeeds and step 8.4 fails. The retry does not call `start_multipart` and marks the row done.
  - Cancel after completion: a cancelled attempt calls `complete_multipart` anyway. The row is not done, so the download endpoint returns 404, and no email is sent.
  - Duplicate delivery: run the handler twice on a done export. Only one email is sent.
  - Email failure after `done`: the retry sends only the email. The status stays `done`.
  - Final-failure hook: marks the export failed and sends one failure email. A second call does nothing. It marks `done` when the object already exists. It does nothing when the row is `done` or cancelled. If the hook raises, the sweep fails the row after 120 minutes.
  - Cancel: a running job stops at its next heartbeat and leaves no visible object.
  - Expiry: the page download window ends at `completed_at` + 24 hours. A download at or after `available_until` returns 410. The emailed link's TTL is the smaller of 24 hours and the time left until file expiry.
  - Benchmark (gate): 2,000,000 rows on a production-sized dataset, run once with a selective filter and once with a non-selective filter. Each keyset query must use an index, confirmed with EXPLAIN. The job must finish in under 15 minutes with peak memory under 200 MB. Record the largest row (A6) and the longest heartbeat gap during the run, which must stay under 5 minutes. If the time misses, apply the parallel-upload fallback and re-run. The benchmark owner must be named before this step starts.
  - Small-path benchmark: 10,000 rows at the widest allowed column count return well inside the 60-second API limit.
- **Rollout order and gates.** Each step moves on only when its gate passes. No calendar dates are set yet.
  1. Migration, `object_exists` helper, and the sweep. Gate: A3, A4, A5, A7 confirmed.
  2. Workers with the `csv_export` handler and final hook, flag off. Gate: A1 and A2 confirmed, and the stale-rule tests pass.
  3. API endpoints, flag off.
  4. Button and panel, flag off.
  5. Flag on for internal workspaces, then for everyone. Gate for each stage: the benchmark gate in step 13 has passed, and no export has been stuck longer than `STALE_AFTER` in the internal stage.
- **Feature flag:** required. When off, the button is hidden and every export endpoint returns 404, as the requirements state. Emailed links keep working until they expire. Exports already in progress keep running on the workers, or go stale under H3.
- **Rollback:** turn the flag off. Exports in progress finish, or are failed by H3. The table, handler and sweep stay in place, so no data needs to be undone.

## Open items before build

- Name the owner of `report_exports` retention and the review at 1 million rows.
- Name the owner of the benchmark gate in step 13.
- Confirm `MAX_COLUMNS`, `MAX_VALUE_CHARS`, `SMALL_MAX_BYTES`, `SMALL_MAX_CONCURRENT` and `MAX_EXPORT_ROWS` with the product owner. They are provisional.
- Product sign-off on three decisions this revision adds or changes: (a) the sweep job, which is a new scheduled job, although the brief forbids a file-cleanup job; (b) the 24-hour page download window, which matches the email; (c) the filter-mismatch panel, which returns an existing export rather than rejecting the click.
- Confirm A1 with the queue's owner, A2 from queue metrics, A5 from replica monitoring, A6 on production data during the benchmark, and A7 with the platform team.
- Name the owner for operations alerts from the final hook and the sweep.