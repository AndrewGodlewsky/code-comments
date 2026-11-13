# Plan: CSV export for the reports page

## Summary

The user clicks **Download CSV** on the reports page. The server checks permission, then decides by `reports.row_count`. At 10,000 rows or fewer, the response to the click is the CSV, with no job and nothing stored. Above that, the click creates an export record and returns at once. A background job streams the file into the `exports` bucket, emails a 24-hour link, and the page shows the export's state (queued, running, done or failed) from the record.

## Terms

- **Rows API:** `GET /api/reports/{report_id}/rows?filters=...&cols=...&after={row_id}&limit=500`. It checks `report.view`, reads `report_rows` from the **read replica** only (never the primary), and pages by `row_id` (keyset: `row_id > after ORDER BY row_id`, never OFFSET). API servers kill requests running over 60 s.
- **View state:** the filters and column order in the page URL, e.g. `?status=open&region=EU&cols=date,customer,amount`. The server stores none of it today.
- **`reports.row_count`:** the unfiltered total rows in a report. Rewritten nightly, so it can be up to a day old.
- **Job queue** (`jobs.py`): `enqueue(name, payload)` returns a `job_id`. Workers (512 MB memory, one attempt at a time) call `handler(ctx, payload)`, where `ctx` has `job_id` and `attempt` (1 to 3).
  - A job gets at most 3 attempts, with 60 s then 300 s of backoff. An attempt is killed after 1800 s.
  - The queue keeps no progress between attempts. Each attempt starts again from the beginning.
  - Delivery is at least once, so a handler may run again after succeeding.
  - `on_final_failure(ctx, payload, error)` runs once after the last attempt fails.
  - The queue's own job states are not used. The export row's `status` is the only state the page reads.
- **Storage** (`storage.py`): multipart upload (`start_multipart`, `upload_part`, `complete_multipart`, `abort_multipart`). Nothing is visible at the key until `complete_multipart` succeeds. Each part except the last must be at least 5 MB. `signed_url(bucket, key, ttl)` allows at most 86,400 s. The `exports` bucket deletes objects after 7 days and discards multipart uploads not completed within 24 hours.
- **`report_exports`:** the one new table, in the application database (export metadata only, not report data).

| Column | Meaning |
|---|---|
| `export_id` | Primary key. |
| `report_id`, `user_id` | Who asked, and for which report. |
| `filters`, `cols` | View state captured at click time. The job reads them from here, so the 64 KB payload limit never matters. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id` | From `enqueue`. Null until enqueue succeeds. |
| `object_key` | `{export_id}.csv` in the `exports` bucket. Set when done. |
| `notified_at` | Set after the success email is sent. |
| `error` | Short failure reason. |
| `created_at`, `finished_at` | Timestamps. |

A **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')` enforces "one large export at a time", so two simultaneous clicks cannot both succeed.

## States

| State | Meaning | Next |
|---|---|---|
| `queued` | Row created and job enqueued. | `running`, or `failed` if enqueue failed or the row went stale. |
| `running` | An attempt has started. Stays `running` through retries and backoff. | `done`, or `failed` after the last attempt or a stale timeout. |
| `done` | File complete in the bucket. The email may still be pending. | Final. |
| `failed` | Final failure, enqueue failure, permission removed, or stale. | Final. The user may start a new export. |

## Steps

### 1. The click
- **Starts it:** the user clicks **Download CSV** on `/reports/{report_id}`.
- **Data moved:** the browser sends `POST /api/reports/{report_id}/export` with the `filters` and `cols` from the page URL.
- **State kept:** none.
- **If it fails:** on a network error the page shows "Export could not be started, try again". Nothing was created.

### 2. Check permission and validate
- **Starts it:** the request arrives at the API.
- **Data moved:** check `report.view` as the Rows API does. Validate `filters` and `cols` as the Rows API does (an unknown column is rejected). Read `reports.row_count` from the replica.
- **State kept:** none.
- **If it fails:** 403 with no permission, 400 for bad parameters, 404 for a missing report. Nothing is created.

### 3. Choose the path
- **Starts it:** Step 2 passed.
- **Data moved:** compare `row_count` with 10,000. At most 10,000 goes to Step 4, above goes to Step 5.
- **State kept:** none.
- **Note:** `row_count` is unfiltered, so a heavily filtered export of a big report still takes the job path and may give a small file. That is the rule as specified.

### 4. Small path: the response is the CSV
- **Starts it:** Step 3 chose the small path.
- **Data moved:**
  1. Write the header row (requested column names, in `cols` order).
  2. Read rows from the replica in keyset pages of 500, with the same filtered query as the Rows API.
  3. Encode each row as RFC 4180 CSV in UTF-8 and keep the whole CSV in memory (a few MB at most).
  4. If more than 10,000 rows are read, `row_count` was stale. Discard the buffer and go to Step 5.
  5. When all pages are read, return `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. The download starts only when the whole body arrives.
- **State kept:** none. Nothing is written to the database or storage.
- **If it fails:** nothing is sent until the CSV is complete, so a failure gives a clean `500`, never a truncated file. A 45 s deadline is checked after each page, under the 60 s kill. If passed, return `500` "Export took too long, try again". The user can click again.

### 5. Large path: create or return the export record
- **Starts it:** Step 3 chose the large path, or the Step 4 guard fired.
- **Data moved:**
  1. If the user has a `queued` or `running` export of this report older than 3 hours, mark it `failed` ("timed out"). See the failure list below.
  2. Insert a `report_exports` row (`status=queued`, `user_id`, `report_id`, `filters`, `cols`, `created_at`) with `INSERT ... ON CONFLICT DO NOTHING` against the partial unique index.
  3. If the insert hit the index, an export is already active. Select it and return it with `202` and `{export_id, status}`. It wins even if this click used different filters, since the rule is one per user and report.
  4. If the insert succeeded, call `enqueue("report_export", {"export_id": ...})`, store the `job_id`, and return `202` with `{export_id, status: "queued"}`.
- **State kept:** the `report_exports` row and the queued job.
- **If it fails:**
  - `enqueue` raises: mark the row `failed` with a short error and return `503` "Export could not be started, try again".
  - The API process dies between insert and enqueue: the row stays `queued` with a null `job_id`. On the next click, if it is older than 60 s, call `enqueue` again and fill in `job_id`.
  - A row stuck `queued` or `running` for over 3 hours (a lost `on_final_failure`) is treated as dead, since the worst legitimate case is about 96 minutes plus queue wait. The sweep in item 1 marks it `failed` before the new insert. The new export has a different `export_id` and so a different file key. If the old job is somehow still alive, Step 8 refuses to mark a `failed` row `done`.

### 6. The job starts
- **Starts it:** a worker runs `report_export(ctx, payload)`, registered as `@job("report_export", on_final_failure=...)`. It runs again on each retry, and may rarely run again after success.
- **Data moved:**
  1. Load the export row by `payload.export_id`.
  2. If `status=done`: when `notified_at` is null, go straight to Step 9 and send only the email. Otherwise return. This makes duplicate delivery harmless.
  3. If `status=failed`: return.
  4. Re-check `report.view` for the user. If gone, set `failed` ("permission removed") and return without raising. No retry, no link, no email.
  5. Set `status=running`. It stays `running` through retries.
- **State kept:** `status=running`.
- **If it fails:** an unreachable database raises and the queue retries after backoff.

### 7. Stream the report into storage
- **Starts it:** Step 6 passed.
- **Data moved:**
  1. `key = "{export_id}.csv"`. It is fixed per export, so retries target the same object.
  2. `upload_id = start_multipart("exports", key)`.
  3. Write the header row into a byte buffer.
  4. Page through the replica with the stored `filters` and `cols`, 5,000 rows per page (`row_id > after ORDER BY row_id LIMIT 5000`). Append CSV bytes to the buffer. When it reaches 8 MB, call `upload_part`, keep the etag and empty the buffer. Stop when a page returns fewer than 5,000 rows. The largest report (about 900 MB) needs about 115 parts, far below the 10,000-part limit.
  5. Upload the remaining bytes as the last part. The header guarantees at least one part.
  6. Memory stays at one 8 MB buffer, one page and the etag list: tens of MB, independent of report size.
  7. The handler sets its own deadline at about 1,700 s. If reached, call `abort_multipart` and raise.
- **State kept:** the invisible multipart upload in storage. `upload_id` lives only in the running attempt.
- **If it fails:**
  - Any error: call `abort_multipart` and re-raise. The queue retries after 60 s, then 300 s.
  - Timeout or worker death: the orphaned parts are discarded by the bucket's 24-hour rule. No cleanup job.
  - A half-written file is never downloadable, because `complete_multipart` runs only after every part uploaded.
  - If the nightly rebuild runs mid-export, the file may mix old and new rows. This is accepted (open question 3).
  - A timeout would repeat on every attempt, so measure a 2 million row export on staging before launch.

### 8. Publish the file and mark done
- **Starts it:** Step 7 uploaded every part.
- **Data moved:**
  1. `complete_multipart(upload_id, etags)`. The whole object appears at `key` in one step, replacing any earlier one.
  2. Update the row to `status=done`, `object_key=key`, `finished_at=now`, only `WHERE status='running'`. If no row changed (it was marked `failed`), return without emailing.
- **State kept:** the object in the bucket and `status=done`.
- **If it fails:** if `complete_multipart` raises, abort and retry as in Step 7. If the database update fails afterwards, the attempt fails and the next one rebuilds and replaces the file. This is wasteful but safe.

### 9. Email the download link
- **Starts it:** straight after Step 8, or from Step 6 on a retry that finds `done` with `notified_at` null.
- **Data moved:**
  1. `url = signed_url("exports", object_key, 86_400)`, signed at send time so the 24 hours start when the email goes out.
  2. `send_email(user_id, "report_export_ready", {report_id, url, expires_in: "24 hours"})`.
  3. Set `notified_at=now`.
- **State kept:** `notified_at`. The link is not stored.
- **If it fails:** if `send_email` raises, the attempt fails, and the next attempt sends only the email. If every attempt fails here, the status stays `done` (the file exists) and the user gets no email (open question 1). If the email is sent but `notified_at` is not saved, a retry sends a harmless duplicate.

### 10. Final failure
- **Starts it:** the queue calls `on_final_failure` once after the last attempt fails.
- **Data moved:**
  1. Load the row. If `status=done`, do nothing.
  2. Otherwise set `status=failed`, `error`, `finished_at=now`.
  3. `send_email(user_id, "report_export_failed", {report_id})`, after the status write. Catch and log email errors.
- **State kept:** `status=failed` and `error`. The row leaves the unique index, so a new export can start.
- **If it fails:** if the callback crashes, the row stays `running` and the 3-hour rule in Step 5 clears it on the next click.

### 11. Show the status on the page
- **Starts it:** the page loads (including a later return to the report), or the user starts a large export.
- **Data moved:**
  1. The page calls `GET /api/reports/{report_id}/exports/latest`. It checks `report.view` and returns the user's latest export for that report from the last 7 days as `{export_id, status, created_at, finished_at}`.
  2. The page shows the state next to the button.
  3. While queued or running, the button is disabled and the page polls every 5 s, stopping on done or failed.
  4. Done shows "Done. We emailed you a download link". Failed shows "Export failed. Try again" and re-enables the button.
- **State kept:** none on the page. The table is the source of truth.
- **If it fails:** a failed poll keeps the last state and retries next tick. A 403 hides the status block. After 7 days nothing is shown and a click starts a new export. A click from a second tab during an active export gets the existing export back from Step 5.

## Tests to write

1. **Small path:** exactly 10,000 rows returns the CSV inline. 10,001 returns 202 and enqueues. Header and column order match `cols`. A stale low `row_count` falls through to the job path.
2. **Permission:** no `report.view` gives 403 on the export and status endpoints.
3. **Dedupe:** two simultaneous clicks make one row and one job.
4. **Memory and time:** run a 2 million row export on staging. Peak memory must be well under 512 MB and duration well under 1800 s.
5. **Failure injection:** an error mid-upload runs `abort_multipart` and leaves no object at the key. Three failed attempts give `failed` plus the failure email. One `send_email` failure makes the retry send only the email.
6. **Duplicate delivery:** running the handler twice gives one file and one email.
7. **Stale row:** a `running` row older than 3 hours is cleared on the next click.

## Open questions

1. If all attempts fail only at the email step, the page shows "done" but the user has no link. Should the page offer a "Get link" button that signs a fresh URL while the file exists (up to 7 days)?
2. An export with different filters from an active one is blocked, per the brief's one-per-report rule. Is that right?
3. Should the job export a consistent snapshot if the nightly rebuild runs mid-export? This plan accepts a possible mix.
4. Cells starting with `=`, `+`, `-` or `@` can run as formulas in spreadsheets. Escaping would change negative numbers, so this plan leaves them as they are. Should it escape?
