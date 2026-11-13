# CSV export for the reports page: implementation plan

## Summary

The reports page shows one report as a table. It loads rows in pages from a read-only copy of the database. The view (filters and column order) lives only in the page URL. This plan adds a **Download CSV** button. The file holds the rows the user is looking at, plus a header row.

The button has two paths, chosen by the report's row count:

- **Up to 10,000 rows:** the server builds the CSV and sends it in the response to the click. Nothing is stored. This is fast enough to finish inside one request.
- **Above 10,000 rows:** the click starts a background job. The job reads the rows in pages and writes the file to object storage in parts, so it never holds the whole report in memory. When the file is complete, the job emails the user a download link that works for 24 hours. The page shows the job's progress.

A user can have only one large export of a given report queued or running at a time. A second click returns the first export.

## How the system works today

- **The reports page** is at `/reports/{id}`. It calls `GET /api/reports/{id}/rows` with the filters, columns and a `row_id` cursor. The API checks the `report.view` permission, reads rows from the `report_rows` table on the read replica, and pages by `row_id`. The server stores nothing about what a user is viewing.
- **Row count.** `reports.row_count` holds the unfiltered total number of rows. The nightly rebuild rewrites it. The largest report has about 2 million rows, about 900 MB as CSV.
- **The job queue** runs jobs on a `worker` pool. Each worker has 512 MB of memory and runs one attempt at a time. An attempt times out after 30 minutes. A failed attempt is retried after 60 seconds, then after 300 seconds, up to 3 attempts in total. Each retry starts again from the beginning, because the queue saves no progress. Delivery is at least once, so a job can run more than once.
- **Object storage** has an `exports` bucket. The bucket deletes every file 7 days after it was created. A multipart upload that is not finished within 24 hours is discarded.

## Terms

- **Primary database:** the main database. It accepts writes. Export state is stored here.
- **Read replica:** a read-only copy of the primary. Report rows are read only from it, never from the primary.
- **Keyset paging:** each page asks for rows with `row_id > last_row_id`, ordered by `row_id`, with a limit. This stays fast on any page. OFFSET is never used.
- **Multipart upload:** storage receives a file as numbered parts. The parts become one object only when they are joined with `complete_multipart`. Until then, nothing is visible at the final key, and the upload can be discarded with `abort_multipart`.
- **Attempt:** one run of the export job. The queue allows 3 attempts.
- **Heartbeat:** a timestamp (`heartbeat_at`) that a running export updates after each page. It shows the job is still alive.
- **Stale:** a queued or running export that has made no progress for longer than the limits in the table below.
- **Expired:** a finished export whose file has been deleted by the bucket, 7 days after it was created.
- **Export row:** one record in the `exports` table, for one export.

## Fixed values

| Name | Value | Meaning |
|---|---|---|
| `SMALL_LIMIT` | 10,000 | Rows at or below this count use the small path |
| `API_PAGE` | 500 | Rows per query on the small path (same as the page) |
| `JOB_PAGE` | 5,000 | Rows per query inside the job |
| `PART_BYTES` | 8 MiB | Buffer size before each part is uploaded (the minimum is 5 MB) |
| `LINK_TTL` | 86,400 s | Lifetime of a download link (24 hours, the maximum allowed) |
| `FILE_RETENTION` | 7 days | Set by the bucket's lifecycle rule. No code deletes files. |
| `QUEUED_STALE` | 5 min | A queued export with no job id is abandoned after this |
| `RUNNING_STALE` | 60 min | A running export with no heartbeat for this long is abandoned |

`RUNNING_STALE` must be longer than the 30-minute attempt timeout, plus the longest retry wait (300 s), plus the queue's worst delay. The queue owners must confirm that delay.

## The `exports` table

The table lives on the primary. It holds export state, not report data.

| Column | Set when | Notes |
|---|---|---|
| `id` (UUID) | created | Used in the storage key and the job payload |
| `user_id`, `report_id` | created | The export belongs to the user who clicked |
| `filters`, `cols` | created | Copied from the request, so the export knows its own view |
| `status` | every change | `queued`, `running`, `done` or `failed` |
| `attempt` | each attempt starts | 0 to 3 |
| `job_id` | after enqueue | Empty means the enqueue is not yet recorded |
| `upload_id` | each attempt starts an upload | Cleared on complete or abort |
| `file_key` | on completion | Empty until the file is visible in the bucket |
| `rows_written` | every page | Shown on the page |
| `heartbeat_at` | every page | Used to detect stale exports |
| `completed_at` | on completion | Starts the 7-day expiry |
| `email_sent_at` | after the ready or failed email | Prevents duplicate emails |
| `error` | on failure | Short reason shown to the user |
| `created_at`, `updated_at` | automatically | |

A partial unique index covers `(user_id, report_id)` where `status` is `queued` or `running`. Two clicks that race cannot create two active exports.

Every write to this table checks the row's expected current status, and includes the attempt number. An old attempt therefore cannot overwrite a newer one.

## Shared parts

These parts are used by more than one step below.

### Row query module

The page and the export both use one module, so the export matches what the page shows. Given `filters` and `cols`, it returns a keyset query over `report_rows` on the read replica. It does four things:

1. Parses `filters` with the same parser the page uses.
2. Checks that every name in `cols` is a column of the report. An unknown name is rejected with 400.
3. Builds the query as `WHERE report_id = ? AND row_id > ?`, plus the filter conditions, ordered by `row_id`, with a limit.
4. Returns the rows in column order.

Changing the page's handler to use this module is a build step (see Building and rolling out). If that change alters the page's output, the existing page tests catch it. Roll back that change, not the export.

### Email

The job and the failure handler call `send_email(user_id, template, params)`. There are two templates:

- `report_export_ready` with `{report_name, download_url, expires_at}`. The URL is a signed download link.
- `report_export_failed` with `{report_name, export_url}`. The URL is the report page, where the user can start again. No internal error details are included.

When an email is sent successfully, `email_sent_at` is set on the export row.

## How the export runs

### Step 1. The click is checked and sized

**Starts:** the user clicks **Download CSV**. The page sends `POST /api/reports/{id}/export` with a JSON body `{filters, cols}`, copied from the page URL.

**What it does:**

1. Checks `report.view` on the report's workspace. Returns 403 if the check fails. This is the same check the page uses.
2. Validates `filters` and `cols` with the row query module. Returns 400 if either is invalid.
3. Reads `reports.row_count` from the replica.
4. If `row_count` is 10,000 or less, runs step 2. Otherwise runs step 3.

**Keeps its data:** nothing. This step writes nothing.

**If it goes wrong:** a database error returns 500. Nothing was written, so the user can click again.

### Step 2. Small path: the CSV is the response

**Starts:** step 1 found 10,000 rows or fewer.

**What it does:** the response body is the CSV itself, with `Content-Type: text/csv` and `Content-Disposition: attachment`. The handler reads pages of 500 rows through the row query module, writes the header row first, and writes each page to the response as it is read. No job runs. At most 10,000 rows are read, which fits well inside the 60-second API limit.

**Keeps its data:** nothing. No table or bucket is written.

**If it goes wrong:**

- An error before the first byte is sent returns a JSON 500.
- An error, or the 60-second cut-off, after streaming has started breaks the connection. The page's `fetch` call fails, so the page does not save the partial file. The user sees an error and can try again.

### Step 3. Large path: create the export and queue the job

**Starts:** step 1 found more than 10,000 rows.

**What it does:**

1. Looks for an active export (status `queued` or `running`) for this user and report.
   - If one exists and is not stale, returns it with 202. The user gets the same export, not a second one.
   - If one exists and is stale, marks it `failed` with error `abandoned`, only if its status has not changed. Then continues.
2. Inserts a row with status `queued`, the request's `filters` and `cols`, and an empty `job_id`.
   - If the insert fails on the unique index, another click won the race. Reads the winning row and returns it with 202.
3. Calls `enqueue("report_export", {"export_id": id})`, which returns a `job_id`.
4. Saves `job_id` on the row, only if its status is still `queued`.
5. Returns 202 with the export's state.

**Keeps its data:** one new row in `exports`.

**If it goes wrong:**

- If `enqueue` raises, marks the row `failed` with error `could not queue`, only if it is still `queued`. Returns 503. The user can click again.
- If the process crashes between steps 2 and 4, the row stays `queued` with no `job_id`. After 5 minutes, the next click takes it over, as in item 1. If the enqueue did succeed late, the orphaned job finds that its row is no longer `queued` or no longer matches, and exits without doing work (step 4, item a).

### Step 4. The export job: one attempt, start to finish

**Starts:** the queue runs the `report_export` handler for attempt 1, 2 or 3. The payload is only `{"export_id": ...}`. The filters and columns are read from the row, so the database is the only source of truth. The payload is far below the 64 KB limit.

**What it does, in order:**

a. **Claim.** Sets `status = running`, `attempt` to this attempt, and `heartbeat_at` to now. This happens only if the row exists, its status is `queued` or `running`, and its attempt is not newer than this one. If no row matches, the job is stale or a duplicate, so it exits without doing work.

b. **Done check.** If the row is already `done`, the file is finished. Skip to the email in item i, then exit. The queue can deliver a job more than once.

c. **Permission check.** Re-checks `report.view` for `user_id`. If the check fails, sets `failed` with error `access removed`, sends the failure email, and returns normally. Returning normally stops the retries, because the access will not come back on its own.

d. **Abort the old upload.** If `upload_id` is set, calls `abort_multipart` on it and ignores "not found" errors. This clears parts left by an earlier attempt.

e. **Start the upload.** Calls `start_multipart(exports, key)`, where `key = "{report_id}/{export_id}.csv"`. Saves the `upload_id` on the row. Nothing is visible at the key yet.

f. **Write the rows.** Adds the header row to a memory buffer. Then loops:
   - Fetches the next `JOB_PAGE` (5,000) rows through the row query module, starting after the last `row_id`.
   - Appends each row as CSV, with RFC 4180 quoting.
   - When the buffer reaches `PART_BYTES` (8 MiB), uploads it with `upload_part`, using the next part number. Keeps the returned etag.
   - After each page, updates `rows_written` and `heartbeat_at`.
   - Stops when a page returns no rows.

g. **Finish the upload.** Uploads the rest of the buffer as the last part, which may be smaller than 5 MB. Then calls `complete_multipart(upload_id, etags)`. This makes the file visible at its key. Only now.

h. **Mark done.** Sets `status = done`, `file_key = key`, `completed_at = now`, and `upload_id` to empty. This happens only if `attempt` is this attempt and `status` is `running`.

i. **Send the ready email.** Calls `signed_url(exports, key, 86400)`, then `send_email(user_id, "report_export_ready", {...})`. Sets `email_sent_at` on success.

**Keeps its data:**

- The `exports` row, updated as above.
- Memory: one 8 MiB part and one page of rows, plus a few MB of overhead. The list of etags is small and kept in memory. This stays far below the 512 MB worker limit, even for a 2-million-row report.
- Storage: uploaded parts sit in an unfinished upload until step g or until they are aborted.

**Time budget:** the attempt timeout is 1,800 seconds. Finishing 2 million rows in that time needs at least about 1,100 rows per second, including upload. The target is 3,000 rows per second, which takes about 11 minutes for the largest report.

**If it goes wrong:** an exception, a 30-minute timeout, or a worker death ends the attempt. The queue schedules the next attempt. The parts already uploaded stay in an unfinished upload. The next attempt aborts that upload (item d). The bucket also discards it after 24 hours. The file becomes visible only at item g, so a half-written file can never be downloaded. If the failure happens after item h, the next attempt sees `done` and only resends the email (item b).

### Step 5. Final failure: after the last attempt

**Starts:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.

**What it does:**

1. Loads the row by `export_id`.
2. If the row is `done`, the file was finished and only the email failed. Leaves it `done`. Sends the ready email again if `email_sent_at` is empty. Does not mark it failed.
3. Otherwise, aborts `upload_id` if it is set (ignoring "not found"). Then sets `status = failed`, `error = "build failed after 3 attempts"`, and `upload_id` to empty. This happens only if the status is not `done`.
4. Sends the failed email and sets `email_sent_at`.

**Keeps its data:** the row moves to `failed`.

**If it goes wrong:** if this handler itself fails, the row stays `running` and its heartbeat stops moving. After `RUNNING_STALE`, the next click takes the export over (step 3, item 1). Until then, the page shows the export as running, and then as waiting to retry.

### Step 6. The page shows the export's state

**Starts:** the page loads (the user opens the report or comes back to it). It also starts while a large export is `queued` or `running`.

**What it does:** calls `GET /api/reports/{id}/exports/latest`. This checks `report.view` and returns the caller's most recent export for this report, with any status. The response includes that export's own `filters` and `cols`. A user who clicked with different filters while an export was running gets the earlier export, and the page shows that export's filters so the user knows which view the file holds.

The page shows one of these states:

- **Queued:** "Waiting to start." Polls every 5 seconds.
- **Running:** "Building file, attempt N of 3, X rows so far." Polls every 5 seconds. If the heartbeat is more than 2 minutes old, shows "waiting to retry" instead, because the job is in its backoff.
- **Done:** a **Download** button (step 7), and the expiry date (`completed_at` + 7 days).
- **Done, expired:** "This file has expired. Export again." Clicking starts a new export (step 1).
- **Failed:** the `error` text and a **Try again** button.

Polling stops at `done` or `failed`. The table on the page does not change.

**Keeps its data:** nothing is written. The page keeps no state beyond what the server returns.

**If it goes wrong:** if the status endpoint fails, the page still shows the report and says "export status unavailable". Polling continues, backing off up to 30 seconds between attempts.

### Step 7. Download a finished export

**Starts:** the user clicks **Download** on a `done` export.

**What it does:** calls `GET /api/reports/{id}/exports/{export_id}/download`. This checks `report.view` and that the export belongs to the caller. If the status is `done` and the file has not expired, it redirects to `signed_url(exports, file_key, 86400)`. The browser then downloads from the bucket directly.

**Keeps its data:** nothing is written.

**If it goes wrong:**

- Status is not `done`: 409, with the current status.
- Expired: 410, with a message to export again.
- File missing from the bucket before it expired (deleted outside this plan): 410. Sets the row's `error` to `file missing`. Shows the user the export-again message.

## What happens when things fail

| Situation | What happens | Step |
|---|---|---|
| Two clicks at the same moment | The unique index lets one win. The other gets the winning export. | 3 |
| The server crashes during a click | After 5 minutes, the next click takes over the queued row. | 3 |
| A worker dies or times out mid-job | The next attempt aborts the old upload and starts again. No file is visible until it is complete. | 4 |
| The same job is delivered twice | The done check or the claim stops the second run from doing duplicate work. | 4 |
| Access is revoked while queued | The job fails at once with `access removed`, with no retry. The user gets the failed email. | 4 |
| All 3 attempts fail | The row becomes `failed`, and the user gets the failed email. | 5 |
| The job hangs with no heartbeat | After 60 minutes, the next click takes the export over. Late writes from the hung job are refused. | 3, 5 |
| The ready email fails | The attempt retries and resends the email. If the last attempt still fails, the row stays `done` and the user downloads from the page. | 4, 5 |
| The file is deleted early | Download returns 410, and the row's error is set to `file missing`. | 7 |

## Building and rolling out

These are not part of how the export runs. They are the work to build it and turn it on.

1. **Confirm the facts before coding.** Ask the owners of each system to confirm:
   - The `report_rows` table has an index that covers `(report_id, row_id)` and the filter columns. Check with `EXPLAIN` on the replica, for the largest report with a typical filter. If the index is missing, add it before the job work.
   - How the nightly rebuild writes `report_rows`. If it replaces rows in place while a job is reading, an export could mix two versions of the data. Resolve open question 3 before the job is built.
   - Whether `reports.row_count` lives only on the primary. If it does, decide how step 1 reads it without breaking the replica-only rule for report data.
   - That workers can connect to the read replica and to the `exports` bucket.
   - That the two email templates can be created, and what `send_email` does when it is called twice with the same arguments.

2. **Add the `exports` table.** Run a migration on the primary as part of the deploy. It creates the table and the partial unique index. If the migration fails, the deploy stops. Nothing else depends on the table yet, so rollback is to drop it.

3. **Move the page's handler onto the row query module.** The page and the export must share one query path. If the page's output changes, roll back this change, not the export.

4. **Test and measure before deploying.** Each failed check names the step that owns the behaviour. Do not deploy if any check fails.
   - **Parity:** for a set of filters and column orders, the export file and the page's rows match exactly. (Step 3 and the row query module.)
   - **Boundaries:** a `row_count` of 10,000 takes the small path. 10,001 takes the job. (Step 1.)
   - **CSV rules:** commas, quotes, line breaks and non-ASCII text are quoted and encoded correctly. (Step 4, item f.)
   - **Memory:** run the job on the largest report with a 512 MB limit. Peak memory stays well below the limit. (Step 4.)
   - **Time:** run the job on the largest report while other jobs run. Record the duration of each attempt. It must finish well under 1,800 seconds. The target is about 11 minutes. (Step 4.)
   - **Storage:** the object is absent until completion. Kill the worker in the middle of the upload. Confirm there is no `done` row, no `file_key`, and no downloadable file. Confirm the next attempt aborts the old upload. (Step 4, items d to g.)
   - **Retries:** make `upload_part` raise on attempt 1, and confirm attempt 2 completes. Make all three attempts fail, and confirm the failed email and the `failed` row. (Steps 4 and 5.)
   - **Duplicates:** deliver the same job twice. Confirm one file, one email, and no error. (Step 4, item b.)
   - **Races:** send two clicks at the same moment. Confirm one active export. (Step 3.)
   - **Stale rows:** create a `queued` row with no job id, and a `running` row with an old heartbeat. Confirm a new click takes both over. (Step 3.)
   - **Access:** revoke `report.view` while a job is queued. Confirm the job fails without retrying. (Step 4, item c.)
   - **Rebuild:** simulate the nightly rebuild during a job. (Open question 3.)

5. **Roll out.** Turn it on for a small group of users first, if the team has a feature flag system. Watch these numbers: large export durations, the failure rate, the number of exports stuck in `queued` or `running`, and email send failures. If something goes wrong, turn the button off. Existing exports keep their state, and the status endpoint keeps working, so users can still download finished files.

## Open questions for the owners

1. **Filtered views of big reports.** The 10,000-row decision uses `reports.row_count`, which is unfiltered. A user who filters a 2-million-row report down to 50 rows still gets the job path. This follows the brief. Confirm this is acceptable.
2. **One export per user and report, not per filter set.** A second click with different filters returns the first export. The page shows that export's filters so the user is not misled. Confirm this trade-off.
3. **Nightly rebuild during an export.** If the rebuild replaces `report_rows` in place, a job that spans it can produce a file that mixes two versions. Options: store a data version or generation on the report, and fail the attempt when it changes between pages; or schedule large exports away from the rebuild window. The first option is planned, unless the owners know a better one.
4. **Throughput.** If the timing check shows the largest report cannot finish in about 15 minutes, the job must be split into segments that run as separate jobs and are joined in a final step. That needs its own design, because each part except the last must be at least 5 MB. It is not in this plan.
5. **Signed links are bearer links.** Anyone who gets the emailed link can download the file for 24 hours. Confirm this is acceptable, or require a login for downloads.
6. **Spreadsheet safety.** Cells that begin with `=`, `+`, `-` or `@` can run as formulas in spreadsheet software. Decide whether to prefix such cells with an apostrophe.
7. **Format details.** Decide the encoding (UTF-8, with or without a byte-order mark for Excel), whether the header uses column keys or the labels shown on the page, and whether values are exported raw or formatted the way the page shows them.
8. **Staleness thresholds.** Confirm `RUNNING_STALE` against the queue's worst delay between attempts.

## Not in this plan

Scheduled exports, formats other than CSV, changes to the table on the page, and any cleanup job for old files. The bucket's 7-day lifecycle rule handles old files.