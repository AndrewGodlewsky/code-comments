# Plan: CSV export for the reports page

## Summary

Today the reports page at `/reports/{report_id}` loads rows from `GET /api/reports/{report_id}/rows`. That API checks the `report.view` permission and reads from the read replica. The view (filters and column order) lives only in the page URL, and the server stores nothing about it.

This plan adds a **Download CSV** button. The click sends the view to a new endpoint. The API checks permission, then picks a path by size. A small report (10,000 rows or fewer) is built inside the request, and the response is the CSV. Nothing is stored. A large report cannot be built inside a request (API servers kill requests after 60 seconds, and the biggest report is about 900 MB). So the API records an export and queues a background job. The job streams rows into a multipart upload, so memory stays small. It then emails a 24-hour download link. The page shows the export's state: queued, running, done or failed.

## Terms

- **Small export**: `reports.row_count <= 10,000`. The HTTP response is the CSV and nothing is stored.
- **Large export**: `reports.row_count > 10,000`. A background job builds the file.
- **View**: the filters and column order in the page URL, for example `?status=open&region=EU&cols=date,customer,amount`. The click must send it, because the server does not store it.
- **Replica**: the read replica database. All report rows and `reports.row_count` are read only from it, never from the primary.
- **Job queue**: our existing system in `jobs.py`. `enqueue(name, payload)` adds a job and returns a `job_id`. Workers are separate processes with 512 MB of memory each. A worker calls the registered handler `handler(ctx, payload)` once per attempt. A job gets at most 3 attempts, with 60 s and 300 s waits between them. Each attempt has a 30-minute timeout and restarts from the beginning, because the queue keeps no progress. After the last attempt fails, the queue calls `on_final_failure` once. Delivery is at least once, so a handler may run again for a job that already succeeded.
- **Storage helpers**: our existing wrappers in `storage.py` around the object store. The `exports` bucket already exists. A multipart upload sends a file in parts. The object appears at its key only when `complete_multipart` succeeds, and `abort_multipart` discards the parts. `signed_url` makes a temporary download link. A bucket rule deletes every object after 7 days and discards unfinished uploads after 24 hours. That rule is the only cleanup, so we build no cleanup job.
- **`exports` table**: new, in the primary database. It holds job bookkeeping, not report data, so the rule that report data never comes from the primary still holds.

| Column | Purpose |
|---|---|
| `export_id` | Primary key. Names the file: `exports/{export_id}/report-{report_id}.csv`. |
| `report_id`, `user_id` | Who asked for which report. |
| `filters`, `cols` | The normalised view, as JSON. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id` | Set after enqueue. |
| `upload_id` | The current multipart upload, kept so it can be aborted. |
| `error` | Short failure text. |
| `notified` | Whether the completion email was sent. |
| `created_at`, `updated_at` | Timestamps. |

- **One-at-a-time rule**: a partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')`. The database enforces it, so two simultaneous clicks cannot both succeed.
- **Job payload**: only `{export_id}`. The handler reloads the view and everything else from the table.
- **Getting a large file**: only through the emailed link. The page shows the state but has no download button. Once the link expires, the user clicks again.

## How the system runs

### Step 1. The user clicks Download CSV

- **Starts it:** the click on the page.
- **What it does:** the page sends `POST /api/reports/{report_id}/export` with the `filters` and `cols` from the page URL. It then reads the response. A `200` with `Content-Type: text/csv` is saved as a file download (Step 3a). A `202` means a large export, and the page starts showing its state (Step 4).
- **Data kept:** none.
- **If it fails:** if the request cannot be sent, the page shows an error toast and the user can click again. Retrying is safe, because Step 3b never creates a second active export.

### Step 2. The API checks permission, validates the view and picks a path

- **Starts it:** the request from Step 1.
- **What it does:**
  1. Check `report.view` on the report's workspace, with the same check the rows API uses. Return 403 if the user lacks it.
  2. Parse `filters` and `cols` with the same parsing and query-building code the rows API uses, so the export matches the table. Return 400 for unknown columns or malformed filters.
  3. Read `reports.row_count` from the replica. At 10,000 or fewer go to Step 3a. Above that, go to Step 3b.
- **Data kept:** none.
- **If it fails:** a replica error returns 503, nothing is stored, and the user can click again. `row_count` is rewritten only nightly, so it can be stale. Step 3a therefore counts the real rows as it reads.

### Step 3a. Small path: the response is the CSV

- **Starts it:** Step 2, small branch.
- **What it does:**
  1. Read the replica with keyset paging (no OFFSET): `WHERE row_id > :after AND <filters> ORDER BY row_id LIMIT 5000`. `row_id` is unique and increasing within a report, so every page is equally fast. After each page, count rows and check elapsed time.
  2. Build the header row (requested columns, in order) plus the rows, quoted per RFC 4180. This is under about 5 MB, so holding it in memory is fine.
  3. Respond `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
- **Data kept:** none. No job runs and nothing is written to storage or to `exports`.
- **If it fails:** the whole CSV is built before any byte is sent, so a failure never gives the user a truncated file. A query error returns 503. **Fallback:** if the count passes 10,000 rows (stale `row_count`) or the elapsed time passes 40 seconds (the API is killed at 60 s), discard the buffer and continue at Step 3b. The user sees the normal `202` and queued state.

### Step 3b. Large path: create or return the export record

- **Starts it:** Step 2, large branch, or the fallback from Step 3a.
- **What it does:**
  1. Insert an `exports` row with `status='queued'`, a new `export_id`, and the normalised `filters` and `cols`.
  2. If the unique index rejects the insert, an export is already queued or running. Select that row and return it (`202` with `{export_id, status, filters, created_at}`) instead of starting a second one. If its filters differ from this click, the page shows which view that export covers.
  3. Otherwise call `enqueue("report_export", {"export_id": ...})`, save the `job_id` on the row, and respond `202` with `{export_id, status:'queued'}`. This returns immediately.
- **Data kept:** the `exports` row, in the primary database.
- **If it fails:** if `enqueue` raises, set the row to `failed` at once so it does not block the user, and return 503. If the API process dies between the insert and the enqueue, the row stays `queued` with no `job_id`. On the next click, a conflicting row with no `job_id` that is more than 2 minutes old is set to `failed` and the insert is retried. So the user is never blocked for good.

### Step 4. The page shows the export's state

- **Starts it:** a `202` from Step 3b, or the page loading (this covers a user who comes back later).
- **What it does:** `GET /api/reports/{report_id}/export/status` returns this user's most recent `exports` row for the report: `status`, `created_at`, a short description of the filters, and `error` if failed. It uses the same `report.view` check. The page shows queued, running, done or failed. While queued or running, it polls every 5 seconds and stops on done or failed.
- **Data kept:** read-only from the `exports` table.
- **If it fails:** if a poll fails, the page keeps the last known state and retries on the next tick. "Running" also covers the wait between retry attempts, because the queue gives no hook for a failed attempt and the user needs no distinction.

### Step 5. The worker starts the job (`report_export`)

- **Starts it:** the queue calling `handler(ctx, {"export_id"})`. This happens for attempt 1, for each retry, and possibly for a duplicate delivery.
- **What it does:**
  1. Load the `exports` row.
  2. If `status='done'`, the file is already complete. If `notified` is false, go to Step 8 to send the email. Otherwise return. This makes duplicate deliveries harmless.
  3. Re-check `report.view` for `user_id`. If it was revoked, retrying cannot help. Set `status='failed'` with `error='Permission to view this report was removed'` and return normally, so the queue does not retry and `on_final_failure` is not called. No email is sent, because the user can no longer view the report. The page shows `failed` with that error.
  4. Set `status='running'` and `updated_at`.
  5. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore errors. This avoids leaving a stale upload.
- **Data kept:** `exports.status`, `exports.upload_id`.
- **If it fails:** if the database is unavailable, the handler raises and the queue retries.

### Step 6. Stream rows from the replica into a multipart upload

- **Starts it:** Step 5 completing.
- **What it does:**
  1. `start_multipart("exports", "{export_id}/report-{report_id}.csv")` returns an `upload_id`. Save it on the row at once.
  2. Keep one buffer, flushed as a part at about 16 MiB (the minimum part size is 5 MiB). Start the buffer with the header row.
  3. Loop over the replica with the same keyset paging as Step 3a, setting `after` to the last `row_id` of each page.
  4. Encode each page as CSV and append it to the buffer. When the buffer reaches 16 MiB, call `upload_part(upload_id, n, buffer)`, keep the returned etag, and empty the buffer. The last part may be smaller.
  5. Memory stays at one 16 MiB buffer plus one 5,000-row page, far below 512 MB and independent of report size. A 900 MB file is about 57 parts, far below the 10,000-part cap.
- **Data kept:** the etag list and the `after` cursor live in memory only. A retry restarts from row 1 with a new upload. Nothing is visible in the bucket yet.
- **If it fails:** on any exception, call `abort_multipart(upload_id)` in a `finally` block, clear `upload_id`, and re-raise so the queue retries. If the worker is killed or the attempt times out, the `finally` block never runs. The next attempt aborts the stale upload in Step 5, and the bucket rule discards it after 24 hours. In every case no download exists, because nothing is visible at the key until Step 7.

### Step 7. Finish the upload and mark the export done

- **Starts it:** the replica loop in Step 6 returning no more rows.
- **What it does:**
  1. Upload the final partial buffer. If the report has no rows, this is just the header row.
  2. `complete_multipart(upload_id, etags)` makes the whole object visible at the key.
  3. Update the row to `status='done'`, clear `upload_id`, and set `updated_at`, with `WHERE status != 'done'`. If it matches zero rows, an overlapping attempt already marked it done, which is fine. Either way, go on to Step 8.
- **Data kept:** the object in the `exports` bucket (deleted after 7 days by the bucket rule), and the `exports` row now `done`.
- **If it fails:** a half-written file can never be downloaded, because the object appears only at `complete_multipart`, after every row is uploaded. If the attempt dies after `complete_multipart` but before the row update, the retry rebuilds the file and replaces it with an equally complete one. If two attempts overlap, each uses its own upload, whichever completes last replaces the other, and both are complete.

### Step 8. Email the download link

- **Starts it:** Step 7, or the early branch in Step 5.
- **What it does:**
  1. `url = signed_url("exports", key, 86_400)`. Generate it now, not at enqueue, so the 24 hours run from when the user receives the email regardless of queue wait.
  2. `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`.
  3. Set `notified=true`.
- **Data kept:** `exports.notified`.
- **If it fails:** if the send raises, the handler raises and the queue retries. The retry sees `done` and `notified=false` (Step 5) and only sends the email. If the send succeeds but marking `notified` fails, the user may get a second email, which is acceptable. If the final attempt fails here, the export stays `done` because the file is good. Log an alert for a human instead of marking it failed.

### Step 9. Final failure (`on_final_failure`)

- **Starts it:** the queue, once, after the third attempt fails (exception, timeout or worker death).
- **What it does:**
  1. If the row is already `done` (Step 8) or `failed` (Step 5, permission revoked), stop.
  2. Set `status='failed'` with a short `error`. Do this first, so the page is correct even if the email fails. This also frees the user to start a new export.
  3. If an `upload_id` remains, call `abort_multipart`.
  4. `send_email(user_id, "report_export_failed", {report name})`.
- **Data kept:** `exports.status='failed'`.
- **If it fails:** if the failure email raises, log it. The page already shows `failed`, and the callback is not called again.

## What happens when things fail

Each step above lists its own failures. The main cases:

| Case | Result |
|---|---|
| Replica or query error on a small export | 503, nothing stored, user clicks again. |
| Stale `row_count` or slow small export | Falls back to the large path. |
| Second click while an export is active | Returns the active export. |
| Attempt fails, times out or worker dies | Queue retries from the start with a new upload. No partial file is downloadable. |
| Permission revoked before the job runs | Export marked `failed`, no retry, no email. |
| Email send fails | Retry only re-sends the email. |
| All 3 attempts fail | Export marked `failed`, user emailed. |

## Fit with the queue's limits

- **Time.** An attempt has 30 minutes. Reading 2 million rows takes 400 queries of 5,000 rows, plus about 900 MB of upload. That needs roughly 1,100 rows per second with no margin, so measure it before building.
- **Retries.** There are 3 attempts, each restarting from the beginning, with 60 s and 300 s waits. The next attempt starts only after a failed one is over and its wait has passed.

## Tests to write

- A report with exactly 10,000 rows takes the small path, and 10,001 takes the large path.
- A stale `row_count` falls back from Step 3a to Step 3b.
- Two simultaneous clicks produce one `exports` row.
- The handler runs twice for the same `export_id`: one file, one email.
- Kill the worker mid-upload: nothing is downloadable, and the retry succeeds.
- Permission revoked before the job runs: the export is `failed` and no retry happens.
- Final failure: the page shows `failed` and the failure email is sent.
- Memory stays flat on the 2-million-row report.

## Open questions

1. **Throughput.** Benchmark the replica query and upload on the 2-million-row report. If one attempt cannot finish well under 30 minutes, retries cannot help and the design needs rethinking (for example, splitting by `row_id` range).
2. **Consistency.** The nightly rebuild may change rows while a long export runs. This plan accepts a possible mix of old and new rows.
3. **Spreadsheet formula injection.** Should fields starting with `=`, `+`, `-` or `@` be prefixed with a quote? This changes the data, so the product owner should decide.
4. **Bucket access.** `storage.py` does not say who can read the `exports` bucket directly. The plan assumes downloads go only through signed links.
5. **Queue internals.** `jobs.py` does not say how the queue detects a dead worker or a timeout. The plan relies only on its stated behaviour.
