# Plan: CSV export for the reports page

## Terms and decisions

- **Small export** means `reports.row_count <= 10,000`. The HTTP response is the CSV and nothing is stored.
- **Large export** means `reports.row_count > 10,000`. A background job builds the file.
- **View** is the filters and column order in the page URL (`?status=open&region=EU&cols=date,customer,amount`). The server stores nothing about it today, so the click must send it.
- **New state: an `exports` table in the primary database.** It holds job bookkeeping, not report data. The rule "report data never comes from the primary" still holds, because all report rows and `reports.row_count` are read from the **read replica**.

Columns of `exports`:

| Column | Purpose |
|---|---|
| `export_id` | Primary key. Also names the file: `exports/{export_id}/report-{report_id}.csv`. |
| `report_id`, `user_id` | Who asked for which report. |
| `filters`, `cols` | The normalised view, stored as JSON. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id` | Set after enqueue. |
| `upload_id` | The current multipart upload, kept so it can be aborted later. |
| `error` | Short failure text. |
| `notified` | Whether the completion email was sent. |
| `created_at`, `updated_at` | Timestamps. |

**One-at-a-time rule.** A partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')` makes the database enforce it. Two simultaneous clicks cannot both succeed.

**The job payload is only `{export_id}`.** The filters live in the table, so the 64 KB payload limit is never an issue. The handler reloads everything from the table.

---

## Step 1. The user clicks Download CSV

- **Starts it:** the click, from the page.
- **Data moves:** the browser sends `POST /api/reports/{report_id}/export` with the current `filters` and `cols` from the page URL.
- **State:** none yet.
- **Failure:**
  - If the request cannot be sent, the page shows an error toast and the user can click again.
  - Retrying is safe, because Step 3b never creates a second active export.

## Step 2. The API checks permission, validates the view and picks a path

- **Starts it:** the request from Step 1.
- **Data moves:**
  1. Check `report.view` on the report's workspace, using the same check as `GET /api/reports/{id}/rows`. Return 403 if the user lacks it.
  2. Parse `filters` and `cols` with the **same parsing and query-building code the rows API uses**, so the export matches the table. Reject unknown columns or malformed filters with 400.
  3. Read `reports.row_count` from the replica.
- **State:** none.
- **Failure:**
  - A replica error returns 503. Nothing is stored and the user can click again.
  - `row_count` is rewritten nightly, so it can be stale. Step 3a therefore re-checks the real row count while it reads, and does not rely on `row_count` alone.

## Step 3a. Small path (`row_count <= 10,000`): the response is the CSV

- **Starts it:** Step 2, small branch.
- **Data moves:**
  1. Page through the replica with keyset paging, not OFFSET:
     `WHERE row_id > :after AND <filters> ORDER BY row_id LIMIT 5000`.
  2. Build the header row (the requested columns, in order) plus the rows. Quote fields per RFC 4180. The result is under about 5 MB, so holding it in memory is fine.
  3. Respond `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{id}.csv"`. The page receives it and saves it as a download.
- **State:** none. No job runs and nothing is written to storage or to `exports`.
- **Failure:**
  - The whole CSV is built **before** any byte is sent, so a failure never gives the user a truncated file. A query error returns 503.
  - **Fallback to the large path.** If the read passes 10,000 rows (stale `row_count`) or passes a 40-second deadline (API servers kill requests at 60 s), discard the buffer and continue at Step 3b.

## Step 3b. Large path: create or return the export record

- **Starts it:** Step 2, large branch, or the fallback from Step 3a.
- **Data moves:**
  1. Insert a row into `exports` with `status='queued'`, a new `export_id`, and the normalised `filters` and `cols`.
  2. If the unique index rejects the insert, an export is already queued or running. Select that row and **return it** (`202` with `{export_id, status, filters, created_at}`) instead of starting a second one. If its filters differ from this click, the page shows which view that export covers.
  3. Otherwise call `enqueue("report_export", {"export_id": ...})`, save the returned `job_id` on the row, and respond `202` with `{export_id, status:'queued'}`. This returns immediately.
- **State:** the `exports` row, in the primary database.
- **Failure:**
  - If `enqueue` raises, set the row to `failed` straight away so it does not block the user, and return 503.
  - If the API process dies between the insert and the enqueue, the row stays `queued` with no `job_id`. On the next click, a conflicting row that has no `job_id` and is more than 2 minutes old is set to `failed`, and the insert is retried. So the user is never blocked for good.

## Step 4. The page shows the export's state

- **Starts it:** a `202` from Step 3b, or the page loading. Page load covers a user who comes back later.
- **Data moves:**
  - `GET /api/reports/{report_id}/export/status` returns this user's most recent `exports` row for the report (`status`, `created_at`, a short description of the filters, and `error` if failed). It uses the same `report.view` check.
  - The page shows queued, running, done or failed. While the state is queued or running, it polls every 5 seconds and stops on done or failed.
- **State:** read-only from the `exports` table.
- **Failure:**
  - If a poll fails, the page keeps the last known state and retries on the next tick.
  - "Running" covers the wait between retry attempts. The queue gives no hook for a failed attempt, and the user needs no distinction.
  - A done export's link was emailed and expires after 24 hours. The user can click again for a fresh one.

## Step 5. The worker starts the job (`report_export`)

- **Starts it:** the queue calling `handler(ctx, {"export_id"})`. This happens for attempt 1, for each retry (after the 60 s and 300 s backoffs), and possibly for a duplicate delivery.
- **Data moves:**
  1. Load the `exports` row.
  2. **Idempotency check.** If `status='done'`, the file is already complete. If `notified` is false, go to Step 8 to send the email. Otherwise return without doing anything. This makes duplicate deliveries harmless.
  3. Re-check `report.view` for `user_id`. Permission may have been revoked since the click. If it was, raise a failure and let it end in Step 9.
  4. Set `status='running'` and `updated_at`.
  5. If the row holds an `upload_id` from an earlier attempt, call `abort_multipart` on it and ignore errors. The lifecycle rule discards leftovers after 24 hours.
- **State:** `exports.status`, `exports.upload_id`.
- **Failure:** if the database is unavailable, the handler raises and the queue retries it.

## Step 6. Stream rows from the replica into a multipart upload

- **Starts it:** Step 5 completing.
- **Data moves:**
  1. `start_multipart("exports", "{export_id}/report-{report_id}.csv")` returns an `upload_id`. Save it on the row at once.
  2. Keep one buffer, flushed as a part at about **16 MiB** (the minimum part size is 5 MiB). Start the buffer with the header row.
  3. Loop over the replica with keyset paging: `WHERE row_id > :after AND <filters> ORDER BY row_id LIMIT 5000`. Set `after` to the last `row_id` of each page.
  4. Encode each page as CSV, append it to the buffer, and call `upload_part(upload_id, n, buffer)` when the buffer reaches 16 MiB. Keep the returned etag, empty the buffer and continue. The last part may be smaller.
  5. Memory stays at one 16 MiB buffer plus one 5,000-row page. This is far below the 512 MB limit, and independent of report size. A 900 MB file is about 57 parts, far below the 10,000-part cap.
- **State:**
  - The etag list and the `after` cursor live in memory only. The queue keeps no progress between attempts, so a retry **restarts from row 1 with a new upload**.
  - Nothing is visible in the bucket yet.
- **Failure:**
  - On any exception, call `abort_multipart(upload_id)` in a `finally` block, clear `upload_id`, and re-raise so the queue retries.
  - If the worker is killed or the attempt times out, the `finally` block never runs. The next attempt aborts the stale upload in Step 5, and the lifecycle rule discards it after 24 hours.
  - In every case no download exists, because nothing is visible at the key until Step 7.

## Step 7. Finish the upload and mark the export done

- **Starts it:** the replica loop in Step 6 returning no more rows.
- **Data moves:**
  1. Upload the final partial buffer (if the report has no rows, this is just the header row).
  2. `complete_multipart(upload_id, etags)` makes the whole object visible at the key.
  3. Update the row to `status='done'`, clear `upload_id`, and set `updated_at`. Do this as a conditional update, `WHERE status != 'done'`.
- **State:** the object in the `exports` bucket (deleted after 7 days by the existing rule, so no cleanup job). The `exports` row becomes `done`.
- **Failure:**
  - **A half-written file can never be downloaded.** The object only appears at `complete_multipart`, after every row is uploaded.
  - If the attempt dies after `complete_multipart` but before the row update, the retry rebuilds the file and replaces it with an equally complete one. The final state is still correct.
  - If two attempts overlap (a duplicate delivery), each uses its own upload. Whichever completes last replaces the other, and both objects are complete.

## Step 8. Email the download link

- **Starts it:** Step 7, or the early branch in Step 5.
- **Data moves:**
  1. `url = signed_url("exports", key, 86_400)`. **Generate it at this moment**, not at enqueue, so the 24 hours run from when the user receives the email regardless of queue wait.
  2. `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`.
  3. Set `notified=true`.
- **State:** `exports.notified`.
- **Failure:**
  - If the send raises, the handler raises, and the queue retries. The retry sees `done` and `notified=false` (Step 5) and only sends the email, with no rebuild. If the send succeeds but marking `notified` fails, the user may get a second email, which is acceptable.
  - If the final attempt fails here, the export stays `done`, because the file is good. Log an alert for a human instead of marking it failed.

## Step 9. Final failure (`on_final_failure`)

- **Starts it:** the queue, once, after the third attempt fails. The causes can be an exception, a timeout, or a worker death.
- **Data moves:**
  1. If the row is already `done`, stop (see Step 8).
  2. Set `status='failed'` with a short `error`. Do this **first**, so the page is correct even if the email fails.
  3. If an `upload_id` remains, call `abort_multipart`.
  4. `send_email(user_id, "report_export_failed", {report name})`.
- **State:** `exports.status='failed'`. This also frees the user to start a new export.
- **Failure:** if the failure email raises, log it. The page already shows `failed`, and the callback is not called again.

---

## Why the job fits the queue's limits

- **Time.** Each attempt has 30 minutes (`ATTEMPT_TIMEOUT_SECONDS=1800`). Reading 2 million rows takes 400 queries of 5,000 rows each, plus about 900 MB of upload. That needs roughly 1,100 rows per second, with no margin, so **measure it before building** (see below).
- **Retries.** There are 3 attempts in total, with 60 s and 300 s of backoff between them. Each attempt restarts from the beginning.

## Tests to write

- A report with exactly 10,000 rows takes the small path, and one with 10,001 takes the large path.
- A stale `row_count` falls back from Step 3a to Step 3b.
- Two simultaneous clicks produce one `exports` row.
- Handler runs twice for the same `export_id`: one file, one email.
- Kill the worker mid-upload: nothing is downloadable, and the retry succeeds.
- Final failure: the page shows `failed` and the failure email is sent.
- Memory stays flat on the 2-million-row report.

## Open questions for the team

1. **Throughput.** Benchmark the replica query and the upload on the 2-million-row report. If one attempt cannot finish in well under 30 minutes, retries cannot help and the design needs rethinking (for example, splitting by `row_id` range).
2. **Consistency.** The nightly rebuild may change rows while a long export runs. This plan accepts a possible mix of old and new rows.
3. **Spreadsheet formula injection.** Should fields starting with `=`, `+`, `-` or `@` be prefixed with a quote? This changes the data, so the product owner should decide.
