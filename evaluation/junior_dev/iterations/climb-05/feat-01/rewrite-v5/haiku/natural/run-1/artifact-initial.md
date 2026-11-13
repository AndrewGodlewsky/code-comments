# CSV export for the reports page: implementation plan

## Summary

The reports page gets a **Download CSV** button. The export contains the rows the user is looking at: the filters and column order from the page URL, plus a header row. Reports up to 10,000 rows are returned in the click's own response. Larger reports are built by a background job that writes the file to the `exports` bucket in parts, then emails the user a 24-hour download link. The page shows the state of that job. Only one large export per user and report can be queued or running at a time.

## Terms used in this plan

- **Read replica:** a read-only copy of the database. Report rows must be read from it, never from the primary.
- **Keyset paging:** each page asks for rows with `row_id > last_seen_row_id ORDER BY row_id LIMIT n`. It never uses OFFSET.
- **Multipart upload:** object storage receives a file as numbered parts (each part except the last is at least 5 MB). Nothing is visible at the final key until the parts are joined with `complete_multipart`. Until then, the upload can be discarded with `abort_multipart`.
- **Attempt:** one run of a job handler. The queue allows 3 attempts. Each attempt starts from the beginning, because the queue keeps no progress.
- **Heartbeat:** a timestamp (`heartbeat_at`) that a running export writes after each page, so other code can tell whether its job is still alive.
- **Expired:** a finished export whose file the bucket has already deleted. Files are deleted 7 days after they are created.

## Fixed values

| Name | Value | Meaning |
|---|---|---|
| `SMALL_LIMIT` | 10,000 | `reports.row_count` at or below this is the synchronous path |
| `API_PAGE` | 500 | Rows per query on the synchronous path (same as the page) |
| `JOB_PAGE` | 5,000 | Rows per query inside the job |
| `PART_BYTES` | 8 MiB | Buffer size before each `upload_part` call (above the 5 MB minimum) |
| `LINK_TTL` | 86,400 s | Lifetime of the signed download link (24 hours, the maximum allowed) |
| `FILE_RETENTION` | 7 days | Set by the bucket's lifecycle rule; no code deletes files |
| `QUEUED_STALE` | 5 min | A queued export with no job id is considered abandoned after this |
| `RUNNING_STALE` | 60 min | A running export with no heartbeat for this long is considered abandoned |

`RUNNING_STALE` must be longer than the 30-minute attempt timeout plus the longest retry backoff (300 s) plus the queue's worst delay. Confirm the queue delay with the queue owners.

## Shared state: the `exports` table

This table lives on the **primary** database. It holds export state, not report data, so writing to it is allowed.

| Column | Set when | Notes |
|---|---|---|
| `id` (UUID) | created | Used in the storage key and the job payload |
| `user_id`, `report_id` | created | Exports belong to the user who clicked |
| `filters`, `cols` | created | Copied from the request, so the export always knows its own view |
| `status` | every transition | `queued`, `running`, `done`, `failed` |
| `attempt` | each job attempt starts | 0 to 3 |
| `job_id` | after enqueue | Empty means the enqueue has not been recorded yet |
| `upload_id` | each attempt starts an upload | Cleared on complete or abort |
| `file_key` | on completion only | Empty until the file is visible in the bucket |
| `rows_written` | every page | Informational, shown on the page |
| `heartbeat_at` | every page | Used for staleness checks |
| `completed_at` | on completion | Starts the 7-day expiry |
| `email_sent_at` | after the final email | Prevents duplicate emails |
| `error` | on failure | Short reason shown to the user |
| `created_at`, `updated_at` | automatic | |

**Constraint:** a partial unique index on `(user_id, report_id)` where `status` is `queued` or `running`. This stops two concurrent clicks from creating two active exports, even when the requests race.

**Rule for every state write:** the write is conditional on the expected current status and includes the attempt number. A stale attempt cannot overwrite a newer one.

## Steps

### 1. Confirm the assumptions before coding

**Starts:** the start of the work, before any code changes.

**Data moves:** nothing moves. Check these facts with the people who own each system:

- The `report_rows` table has an index that supports `(report_id, row_id)` and the filter columns. Run `EXPLAIN` on the replica for the largest report with a typical filter.
- How the nightly rebuild writes `report_rows`. If it replaces rows in place while a job is reading, an export could mix two versions of the data (see Open questions).
- Whether `reports.row_count` lives only on the primary. If so, decide how the click handler reads it without breaking the replica-only rule for report data.
- That workers can open a connection to the read replica and to the `exports` bucket.
- That the email templates named in step 11 can be created, and what `send_email` does when it is called twice with the same arguments.

**State:** none.

**On failure:** if the index is missing, add it before step 3. If the rebuild replaces rows in place, resolve the open question before step 7. Do not start coding the job until this is settled.

### 2. Add the `exports` table and the one-at-a-time rule

**Starts:** a migration run on the primary, as part of the deploy.

**Data moves:** none at run time.

**State:** creates the table and the partial unique index described above.

**On failure:** a failed migration stops the deploy. Nothing else depends on the table yet, so rollback is to drop the table.

### 3. Move the row query into one shared module

**Starts:** a code change. The existing `GET /api/reports/{id}/rows` handler is refactored, and the export code uses the same module. This guarantees the export matches what the page shows.

**Data moves:** the module takes `filters` and `cols` and returns a keyset query over `report_rows` on the read replica. It does the following:

- Parses `filters` with the same parser the page uses.
- Checks that every name in `cols` is a column of the report. Unknown names are rejected with 400.
- Builds the `SELECT` with `WHERE report_id = ? AND row_id > ?` plus the filter predicates, ordered by `row_id`, with a `LIMIT` argument.

**State:** none.

**On failure:** if the refactor changes page output, the existing page tests catch it. Roll back the refactor, not the export.

### 4. Build the click endpoint and the size check

**Starts:** the user clicks **Download CSV**. The page sends `POST /api/reports/{id}/export` with a JSON body of `{filters, cols}`, copied from the page URL.

**Data moves:**

1. Check `report.view` on the report's workspace. Return 403 if the check fails. This is the same check the page uses.
2. Validate `filters` and `cols` through the shared module (step 3). Return 400 if either is invalid.
3. Read `reports.row_count` from the replica.
4. If `row_count <= 10,000`, go to step 5.
5. Otherwise, go to step 6.

**State:** none at this point.

**On failure:** a database error returns 500. Nothing has been written, so the user can click again.

### 5. Small path: stream the CSV in the response

**Starts:** step 4 found `row_count <= 10,000`.

**Data moves:** the response is the CSV itself, with `Content-Type: text/csv` and `Content-Disposition: attachment`. The handler reads pages of 500 rows from the replica through the shared module, writes the header row first, and writes each page to the response as it is read. Nothing is stored and no job runs. At most 10,000 rows are read, which fits well inside the 60-second API limit.

**State:** none. Nothing is written to any table or bucket.

**On failure:**

- An error before the first byte is sent returns a JSON 500.
- An error or a 60-second cut-off after streaming has started breaks the connection. The page's `fetch` call rejects, so the page does not save the partial body. The user sees an error message and can try again.

### 6. Large path: create a queued export and enqueue the job

**Starts:** step 4 found `row_count > 10,000`.

**Data moves:**

1. Look for an active export for this user and report (`queued` or `running`).
   - If one exists and it is not stale, return it with 202. The user gets the same export, not a second one.
   - If one exists and is stale (rules in the Fixed values table), mark it `failed` with error `abandoned`, conditional on its current status. Then continue.
2. Insert a row in `exports` with status `queued`, the request's `filters` and `cols`, and `job_id` empty.
   - If the insert fails on the unique index, another click just won the race. Read the winning row and return it with 202.
3. Call `enqueue("report_export", {"export_id": id})`. This returns a `job_id`.
4. Save `job_id` on the row, conditional on `status = queued`.
5. Return 202 with the export's state.

**State:** one new row in `exports`.

**On failure:**

- If `enqueue` raises, mark the row `failed` with error `could not queue`, conditional on `status = queued`. Return 503. The user can click again.
- If the process crashes between step 2 and step 4, the row stays `queued` with no `job_id`. After 5 minutes the stale rule in step 1 lets the next click take it over. If the enqueue did succeed late, the orphaned job finds the row is no longer `queued` and exits without doing work (step 7, claim).

### 7. The export job: one attempt, start to finish

**Starts:** the queue runs the `report_export` handler for attempt 1, 2 or 3. The payload is only `{"export_id": ...}`. Filters and columns are read from the row, so the database is the only source of truth. The payload stays far below the 64 KB limit.

**Data moves:** rows go from the replica into a memory buffer, and from the buffer into the bucket as parts. Only one part and one page are in memory at a time, at most about 8 MiB for the part plus a few MB for the page. This keeps the job far below the 512 MB worker limit even for a 2-million-row report, which is about 900 MB of CSV.

**State:** the `exports` row, updated as described below. The etags for uploaded parts are held in memory only. A failed attempt's parts are simply abandoned.

**Attempt sequence:**

1. **Claim.** Set `status = running`, `attempt = ctx.attempt`, `heartbeat_at = now`, conditional on the row existing and its status being `queued` or `running`, with attempt not newer than this one. If no row matches, the job is stale or a duplicate, so exit without doing work.
2. **Done check.** If the row is already `done`, go to step 4 of this list to resend the email if needed, then exit. The queue may deliver a job more than once.
3. **Permission check.** Re-check `report.view` for `user_id`. If it fails, set `failed` with error `access removed`, send the failure email (step 11), and return normally. Returning normally avoids a retry, since the access will not come back on its own.
4. **Abort the old upload.** If `upload_id` is set, call `abort_multipart` on it and ignore "not found" errors.
5. **Start the upload.** Call `start_multipart(exports, key)`, where `key = "{report_id}/{export_id}.csv"`. Save `upload_id` on the row. Nothing is visible at the key yet.
6. **Write the rows.** Add the header row to the buffer. Then loop: fetch the next `JOB_PAGE` rows from the replica through the shared module, starting after the last `row_id`. Append each row as CSV (RFC 4180 quoting). When the buffer reaches `PART_BYTES`, call `upload_part` with the next part number and keep the returned etag. After each page, update `rows_written` and `heartbeat_at`. Stop when a page returns no rows.
7. **Flush and complete.** Upload the remaining buffer as the last part, which may be smaller than 5 MB. Then call `complete_multipart(upload_id, etags)`. This makes the file visible at its key, and only now.
8. **Mark done.** Set `status = done`, `file_key = key`, `completed_at = now`, `upload_id = null`, conditional on `attempt = N` and `status = running`.
9. **Send the email.** Call `signed_url(exports, key, 86400)` and then `send_email(user_id, "report_export_ready", {...})`. Set `email_sent_at` on success.

**On failure (at any point):** an exception, a timeout at 30 minutes, or a worker death ends the attempt. The queue schedules the next attempt. Partial parts stay in the bucket as an uncompleted multipart upload. The next attempt aborts that upload (step 4), and the lifecycle rule discards it after 24 hours regardless. Because the file only becomes visible at step 7, no half-written file can be downloaded. If the failure happens after step 8, the next attempt sees `done` and only resends the email, without rebuilding the file.

**Time budget:** the attempt timeout is 1,800 s. To finish 2 million rows in that time, the job must sustain at least about 1,100 rows per second, including upload. The target is 3,000 rows per second, which gives about 11 minutes for the largest report. Step 12 measures this.

### 8. Retries and the final failure handler

**Starts:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails (or after a retry-stopping failure, per the queue's rules).

**Data moves:**

1. Load the row by `export_id`.
2. If the row is already `done` (the file was finished, only the email failed), leave it `done`. Try the ready email once more if `email_sent_at` is empty. Do not mark it failed.
3. Otherwise, abort `upload_id` if set (ignore "not found"), then set `status = failed`, `error = "build failed after 3 attempts"` (or the short reason), `upload_id = null`, conditional on `status` not being `done`.
4. Send `report_export_failed` (step 11) and set `email_sent_at`.

**State:** the row moves to `failed`.

**On failure:** if the handler itself fails, the row stays `running` with a heartbeat that stops advancing. The staleness rule in step 1 of the click path (step 6) lets a new export start after `RUNNING_STALE`. The user sees the export as queued or running until then.

Between attempts, the page shows a running export whose heartbeat is more than 2 minutes old as "waiting to retry", so a user is not told the job is progressing when it is in backoff.

### 9. Status endpoint and page states

**Starts:** the page loads (the user opens or returns to the report), and while a large export is `queued` or `running`.

**Data moves:** `GET /api/reports/{id}/exports/latest` checks `report.view` and returns the caller's most recent export for this report, with any status. The response includes its `filters` and `cols`, because a user who clicked with different filters while an export was running will receive the earlier export.

The page shows one of these states:

- **Queued:** "Waiting to start." Poll every 5 seconds.
- **Running:** "Building file, attempt N of 3, X rows so far." Poll every 5 seconds. Show "waiting to retry" when the heartbeat is more than 2 minutes old.
- **Done:** "Download" button (step 10), plus the date the file expires (`completed_at + 7 days`).
- **Done, expired:** "This file has expired. Export again." The click starts a new export.
- **Failed:** the `error` text and a "Try again" button.

Polling stops at `done` or `failed`. The table on the page is unchanged.

**State:** none written. The page keeps no state of its own beyond what the server returns.

**On failure:** if the status endpoint fails, the page still renders the report and shows "export status unavailable". Polling continues with a backoff, up to 30 seconds between attempts.

### 10. Download endpoint for a finished export

**Starts:** the user clicks **Download** on a `done` export.

**Data moves:** `GET /api/reports/{id}/exports/{export_id}/download` checks `report.view` and that the export belongs to the caller. If `status = done` and the file has not expired, it returns a redirect to `signed_url(exports, file_key, 86400)`. The browser then downloads from the bucket directly.

**State:** none written.

**On failure:**

- Not `done`: 409, with the current status.
- Expired: 410, with a message to export again.
- Object missing from the bucket before expiry (deleted outside the plan): 410, and set the row's `error` to `file missing`. Show the user the export-again message.

### 11. Email templates

**Starts:** the job (step 7, step 9) or the final failure handler (step 8, step 4) calls `send_email(user_id, template, params)`.

**Data moves:**

- `report_export_ready` with `{report_name, download_url, expires_at}`. The URL is the signed link from step 7.
- `report_export_failed` with `{report_name, export_url}`. `export_url` is the report page, where the user can start again. No internal error details are included.

**State:** `email_sent_at` on the export row.

**On failure:** if `send_email` raises, the attempt fails and the queue retries. The retry sees `done` and resends only the email (step 7, step 2). If the email still fails on the last attempt, the final handler keeps `done` and logs the failure (step 8, step 2). The user can still download from the page.

### 12. Tests and measurements

**Starts:** before the deploy, and again after any change to the job.

**Checks:**

- **Parity:** for a set of filters and column orders, the export file and the page's rows match exactly, from the shared module.
- **Boundaries:** `row_count` of 10,000 takes the small path; 10,001 takes the job.
- **CSV rules:** commas, quotes, line breaks and non-ASCII text are quoted and encoded correctly.
- **Memory:** run the job on the largest report with a 512 MB limit. Peak memory must stay well below the limit.
- **Time:** run on the largest report, with other jobs running, and record total duration per attempt. It must finish well under 1,800 s. Target: about 11 minutes.
- **Storage:** confirm the object is absent until completion. Kill the worker in the middle of the upload. Confirm no `done` row, no `file_key`, and no downloadable file. Confirm the next attempt aborts the old upload.
- **Retries:** raise in `upload_part` on attempt 1 and confirm attempt 2 completes. Make all three attempts fail and confirm the failure email and `failed` row.
- **Duplicates:** deliver the same job twice and confirm one file, one email, and no error.
- **Races:** send two clicks at the same moment and confirm one active export.
- **Stale rows:** create a `queued` row with no job id, and a `running` row with an old heartbeat, and confirm a new click takes them over.
- **Access:** revoke `report.view` while a job is queued and confirm it fails without retrying.
- **Rebuild:** simulate the nightly rebuild during a job (see Open questions).

**State:** test data only.

**On failure:** do not deploy. Each failed check names the step above that owns the behaviour.

### 13. Rollout

**Starts:** the deploy after step 12 passes.

**Data moves:** none.

**State:** none beyond the table from step 2.

**Checks:** enable for a small group of users first if the team has a feature flag system. Watch these numbers: large export durations, the failure rate, the number of exports stuck in `queued` or `running`, and the email send failures.

**On failure:** turn the button off. Existing exports keep their state, and the status endpoint keeps working so users can still download finished files.

## Open questions for the owners

1. **Filtered views of big reports.** The 10,000-row decision uses `reports.row_count`, which is unfiltered. A user who filters a 2-million-row report down to 50 rows still gets the job path. This follows the brief. Confirm it is acceptable.
2. **One export per user and report, not per filter set.** A second click with different filters returns the first export. The page must show that export's filters so the user is not misled. Confirm this trade-off.
3. **Nightly rebuild during an export.** If the rebuild replaces `report_rows` in place, a job that spans it can produce a file that mixes two versions. Options: store a data version or generation on the report and fail the attempt when it changes between pages; or schedule large exports away from the rebuild window. The first is planned unless the owners know a better option.
4. **Throughput.** If step 12 shows the largest report cannot finish in about 15 minutes, the job must be split into segments that run as separate jobs and are joined in a final step. That needs its own design, because each part except the last must be at least 5 MB. It is not in this plan.
5. **Signed links are bearer links.** Anyone who gets the emailed link can download the file for 24 hours. Confirm this is acceptable, or require a login for downloads.
6. **Spreadsheet safety.** Cells that begin with `=`, `+`, `-` or `@` can run as formulas in spreadsheet software. Decide whether to prefix such cells with an apostrophe.
7. **Format details.** Decide the encoding (UTF-8, with or without a byte-order mark for Excel), whether the header uses column keys or the labels shown on the page, and whether values are exported raw or formatted the way the page shows them.
8. **Staleness thresholds.** Confirm `RUNNING_STALE` against the queue's worst delay between attempts.

## Not in this plan

Scheduled exports, formats other than CSV, changes to the table on the page, and any cleanup job for old files. The bucket's 7-day lifecycle rule handles old files.