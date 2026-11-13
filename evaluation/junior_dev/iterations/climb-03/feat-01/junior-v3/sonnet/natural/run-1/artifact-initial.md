# Plan: CSV export for the reports page

## Summary

The user clicks **Download CSV**. The server checks permission, then decides by `reports.row_count`.

- **10,000 rows or fewer:** the response to the click is the CSV. No job runs and nothing is stored.
- **More than 10,000 rows:** the click returns an export record straight away. A background job streams the file into the `exports` bucket with a multipart upload, then emails a 24-hour link. The page shows the export's state: queued, running, done or failed.

The one new piece of stored state is a table of export records, `report_exports`. It lives in the application database, not the report data.

## Terms used below

- **Rows API:** `GET /api/reports/{report_id}/rows?filters=...&cols=...&after={row_id}&limit=500`. It checks `report.view`, reads `report_rows` from the **read replica** only, and pages by `row_id` (keyset: `row_id > after ORDER BY row_id`, never OFFSET).
- **View state:** the filters and column order in the page URL, for example `?status=open&region=EU&cols=date,customer,amount`. The server stores none of it today.
- **Job queue** (`jobs.py`):
  - A job is tried at most 3 times, with 60 s then 300 s of backoff between attempts.
  - An attempt is killed after 1800 s.
  - The queue keeps no progress between attempts. Each attempt calls the handler again from the start with the same payload.
  - Delivery is at least once, so a handler can run again after it has already succeeded.
  - `on_final_failure(ctx, payload, error)` runs once after the last attempt fails.
- **Storage** (`storage.py`):
  - Multipart upload: `start_multipart`, `upload_part`, `complete_multipart`, `abort_multipart`. Nothing is visible at the key until `complete_multipart` succeeds. Every part except the last must be at least 5 MB.
  - `signed_url(bucket, key, ttl)` allows at most 86,400 s.
  - The `exports` bucket deletes every object 7 days after creation and discards multipart uploads not completed within 24 hours.

## New state: the `report_exports` table

Created by a migration in the application database. The rows hold export metadata, not report data, so the "never read report data from the primary" rule is not affected.

| Column | Meaning |
|---|---|
| `export_id` | Primary key. |
| `report_id`, `user_id` | Who asked, and for which report. |
| `filters`, `cols` | The view state captured at click time, stored as sent. The job reads them from here, so the 64 KB payload limit never matters. |
| `status` | `queued`, `running`, `done` or `failed`. |
| `job_id` | From `enqueue`. Null until the enqueue succeeds. |
| `object_key` | `{export_id}.csv` in the `exports` bucket. Set when done. |
| `notified_at` | Set after the success email is sent. |
| `error` | Short failure reason. |
| `created_at`, `finished_at` | Timestamps. |

**Partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')`. The database enforces "one large export at a time" with this index, so two simultaneous clicks cannot both succeed.

---

## Step 1. The click: build the request

- **Starts it:** the user clicks **Download CSV** on `/reports/{report_id}`.
- **Data moved:** the browser sends `POST /api/reports/{report_id}/export` with the same `filters` and `cols` it holds in the page URL. The parameter names and validation are the same as in the Rows API.
- **State kept:** none. View state stays in the URL only.
- **If it fails:** a network error shows "Export could not be started, try again". Nothing has been created.

## Step 2. Check permission and validate

- **Starts it:** the export request arrives at the API.
- **Data moved:**
  - The server checks `report.view` on the report's workspace, using the same check as the Rows API.
  - It validates `filters` and `cols` the way the Rows API does, so an unknown column is rejected.
  - It reads `reports.row_count` for the report. This is metadata, not report rows. It is read from the replica to be safe.
- **State kept:** none.
- **If it fails:** no `report.view` returns 403 and nothing is created. Bad parameters return 400. A missing report returns 404.

## Step 3. Choose the path by size

- **Starts it:** Step 2 succeeded.
- **Data moved:** compare `row_count` with 10,000.
  - 10,000 or fewer: go to Step 4 (small path).
  - Above 10,000: go to Step 5 (large path).
- **State kept:** none.
- **Note:** `row_count` is the unfiltered total, as defined in the page doc. A heavily filtered export of a big report therefore still takes the job path and may produce a small file. That is the rule as specified, and the result is still correct.

## Step 4. Small path: the response is the CSV

- **Starts it:** Step 3 chose the small path.
- **Data moved:**
  1. Write the header row first, using the requested column names in `cols` order.
  2. Read rows from the **read replica** in keyset pages of 500 (`row_id > after ORDER BY row_id`), applying the filters and the same query as the Rows API.
  3. Encode each row as RFC 4180 CSV in UTF-8, escaping quotes, commas and newlines.
  4. Keep the whole CSV in memory. At most 10,000 rows is a few MB, far below 512 MB.
  5. When all pages are read, return `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`.
  6. The browser saves the response body as a file.
- **State kept:** none. Nothing is written to the database or to storage.
- **If it fails:**
  - The CSV is built fully in memory before any byte is sent, so a failure gives a clean `500` and never a truncated file with a `200`.
  - The request carries a 45 s internal deadline, under the API servers' 60 s kill. If the deadline passes, return `500` with "Export took too long, try again".
  - The user can just click again.

## Step 5. Large path: create or return the export record

- **Starts it:** Step 3 chose the large path.
- **Data moved:**
  1. Insert a `report_exports` row: `status=queued`, `user_id`, `report_id`, `filters`, `cols`, `created_at`. Use `INSERT ... ON CONFLICT DO NOTHING` against the partial unique index.
  2. If the insert hit the index, a queued or running export for this user and report already exists. Select it and return it with `202` and `{export_id, status}`. No second export starts, which satisfies "clicking again returns that export". If the click used different filters, the existing export still wins, because the rule is one export per user and report. The UI can say "An export of this report is already running".
  3. If the insert succeeded, call `enqueue("report_export", {"export_id": ...})`. The payload is a few bytes. Store the returned id in `job_id`. Return `202` with `{export_id, status: "queued"}`.
  4. The click returns at once. The browser stops waiting and the page starts showing status (Step 11).
- **State kept:** the `report_exports` row, and the queued job in the job queue.
- **If it fails:**
  - **`enqueue` raises.** Mark the row `failed` with a short error, so it does not block the user. Return `503` with "Export could not be started, try again".
  - **The API process dies between insert and enqueue.** The row is `queued` with a null `job_id`, which would block the user. On the next click, if the existing row is `queued` with a null `job_id` and is older than 60 s, call `enqueue` again and fill in `job_id`.
  - **A stuck row.** A row `queued` or `running` for more than 3 hours is treated as dead. The worst legitimate case is 3 attempts of 1800 s plus 360 s of backoff, about 96 minutes, plus queue wait. On a click, the server first marks such a row `failed` (error "timed out") and then proceeds with a new export. This stops a lost `on_final_failure` call from blocking the user permanently.

## Step 6. Job start: the handler picks up the work

- **Starts it:** a worker runs `report_export(ctx, payload)`. It is registered as `@job("report_export", on_final_failure=...)`. It runs again on each retry, and may rarely run again after success.
- **Data moved:**
  1. Load the export row by `payload.export_id`.
  2. **If `status=done`:**
     - If `notified_at` is null, skip to Step 9 and send only the email.
     - Otherwise return without doing anything. This makes duplicate delivery harmless.
  3. **If `status=failed`:** return. The user has already been told, or the row timed out.
  4. Re-check that the user still has `report.view`. If not, set `failed` with "permission removed" and return without raising. Do not retry, and do not send a link.
  5. Set `status=running`. The row stays `running` through retries and backoff. This is simpler than flipping back to queued, which would not work if a worker died.
- **State kept:** `status=running`.
- **If it fails:** the database being unreachable raises, which the queue retries after the backoff. The row is left as it was.

## Step 7. Stream the report into storage

- **Starts it:** Step 6 passed on this attempt.
- **Data moved:**
  1. Compute `key = "{export_id}.csv"`. It is fixed per export, so retries and duplicate runs target the same object.
  2. `upload_id = start_multipart("exports", key)`.
  3. Write the header row from `cols` into a byte buffer.
  4. Loop with keyset paging on the **read replica**, with the stored `filters` and `cols`, and a job page size of 5,000 rows. The 60 s API limit does not apply to workers, and larger pages mean fewer queries.
     - Query `row_id > after ORDER BY row_id LIMIT 5000`, append the CSV bytes to the buffer, and set `after` to the last `row_id`.
     - When the buffer reaches **8 MB**, call `upload_part(upload_id, n, buffer)`, keep the etag, and empty the buffer. 8 MB is above the 5 MB minimum. The largest report (about 900 MB) needs roughly 115 parts, far below the 10,000-part limit.
     - Stop when a page returns fewer than 5,000 rows.
  5. Upload the remaining bytes as the last part. The last part may be under 5 MB. The header guarantees there is at least one part, even if the filters match nothing.
  6. **Memory:** only one 8 MB buffer, one 5,000-row page and the list of etags are held. This is tens of MB against the 512 MB limit and does not grow with report size.
  7. **Time:** the attempt timeout is 1800 s. For 2 million rows at 5,000 per page, that is 400 queries plus about 115 uploads. Measure this against the real 2 M-row report on staging before launch. A timeout would be deterministic, and all 3 attempts would hit it.
  8. The handler also sets its own deadline at about 1,700 s. If it is reached, call `abort_multipart(upload_id)` and raise a clear error. That is cleaner than being killed.
- **State kept:** the multipart upload with its parts (in storage, not visible). The `upload_id` is kept only in the running attempt, never in the database, because the queue keeps no progress between attempts and each attempt starts fresh.
- **If it fails:**
  - **Any error (replica error, upload error).** Call `abort_multipart(upload_id)` and re-raise. The queue retries after 60 s, then 300 s.
  - **Timeout or worker death.** The attempt is killed and cannot clean up. The orphaned parts are discarded by the bucket's rule after 24 hours, so no cleanup job is needed.
  - **A half-written file is never downloadable.** Nothing is visible at `key` until `complete_multipart` runs, and it is called only after every part has uploaded.
  - **Report rebuilt mid-export.** The data is rebuilt each night. If that happens during a run, the file could mix old and new rows. This is accepted. If it matters, see open question 3.

## Step 8. Publish the file and mark done

- **Starts it:** Step 7 uploaded every part.
- **Data moved:**
  1. `complete_multipart(upload_id, etags)`. The object becomes visible at `key` in one step, whole. It replaces any object already there. A duplicate run therefore swaps in a complete file, never a partial one.
  2. Update the row: `status=done`, `object_key=key`, `finished_at=now`.
- **State kept:** the finished object in the `exports` bucket (deleted by the bucket after 7 days), and `status=done` in the table.
- **If it fails:**
  - `complete_multipart` raises: abort and retry as in Step 7.
  - The database update fails after the object is complete: the attempt fails and is retried. The next attempt rebuilds the file and replaces it. This is safe but wasteful, and rare.

## Step 9. Email the download link

- **Starts it:** Step 8 set `done` (or a duplicate run found `done` with `notified_at` null).
- **Data moved:**
  1. `url = signed_url("exports", object_key, 86_400)`. It is signed at send time, so the full 24 hours starts when the email goes out. 86,400 is exactly the maximum allowed.
  2. `send_email(user_id, "report_export_ready", {report_id, url, expires_in: "24 hours"})`.
  3. Set `notified_at=now`.
- **State kept:** `notified_at` on the row. The link itself is not stored.
- **If it fails:**
  - If `send_email` raises, the attempt fails and is retried. The next attempt sees `done` with `notified_at` null and does only Step 9, without rebuilding the file.
  - If all attempts fail while the status is `done`, `on_final_failure` leaves the status `done` (see Step 10) because the file exists. The user can see "done" on the page but got no email. See open question 1.
  - If the email goes out and `notified_at` is not saved, a retry sends a second email. This is a rare, harmless duplicate under at-least-once delivery.

## Step 10. Final failure: tell the user

- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)` once, after attempt 3 fails.
- **Data moved:**
  1. Load the export row.
  2. If `status=done`, do nothing. The file exists and only the email failed.
  3. Otherwise set `status=failed`, `error=<short reason>`, `finished_at=now`.
  4. `send_email(user_id, "report_export_failed", {report_id})`. Do this after the status write, and catch and log any email error. The page shows failed even if the email cannot be sent.
- **State kept:** `status=failed` and `error` on the row. The failed row no longer matches the partial unique index, so the user can start a new export.
- **If it fails:**
  - If this callback itself crashes, the row stays `running` and the 3-hour staleness rule in Step 5 clears it on the next click.
  - Any multipart upload left behind by killed attempts is discarded by the bucket's 24-hour rule.

## Step 11. Show the status on the page

- **Starts it:** two triggers.
  - The page loads (including when the user comes back to the report later).
  - The user starts a large export.
- **Data moved:**
  1. The page calls `GET /api/reports/{report_id}/exports/latest`. The API checks `report.view` and returns the current user's most recent export for that report, with `{export_id, status, created_at, finished_at}`. It only returns exports from the last 7 days, because the file is gone after that. It reads the `report_exports` table.
  2. The page shows the state: queued, running, done or failed.
  3. While the state is queued or running, the page polls every 5 s and stops when the state is done or failed.
  4. On done, the page says "Done. We emailed you a download link". On failed, it says "Export failed. Try again", with a button that starts a new export.
- **State kept:** none on the page. The table is the single source of truth, so nothing is lost on reload.
- **If it fails:**
  - If a poll errors, keep the last known state and retry on the next tick.
  - A 403 hides the status block.
  - If the row is older than 7 days, the page shows nothing and the Download CSV button starts a new export. The partial unique index only covers queued and running, so this is allowed.

---

## States at a glance

| State | Meaning | Next |
|---|---|---|
| `queued` | Row created and job enqueued, not yet picked up. | `running`, or `failed` if enqueue failed or the row is stale. |
| `running` | An attempt has started. Stays `running` through retries and backoff. | `done`, or `failed` after the last attempt (or a stale timeout). |
| `done` | File complete in the bucket. The email may still be pending. | Final. |
| `failed` | Last attempt failed, enqueue failed, permission was removed, or the row went stale. | Final. The user may start a new export. |

## How each requirement is met

- **Same view as the page:** the filters and column order come from the page URL, and both paths use the same validation, `report.view` check and replica queries as the Rows API.
- **Replica only:** every report row is read from the read replica. The only primary-database access is to the `report_exports` metadata table.
- **One at a time:** the partial unique index, with the click path returning the existing export.
- **Memory:** a bounded 8 MB buffer, with streaming upload.
- **Time:** 5,000-row pages, a self-imposed deadline, and a staging measurement before launch.
- **No half-written file:** multipart upload is invisible until `complete_multipart`.
- **Retries:** the queue's normal retries, with idempotent handling via a fixed key and the `done` and `notified_at` checks.
- **No cleanup job:** the bucket's 7-day and 24-hour lifecycle rules do the cleanup.

## Tests to write

1. **Small path:** a report of exactly 10,000 rows returns the CSV inline. One with 10,001 rows returns 202 and enqueues. Header and column order match `cols`.
2. **Permission:** a user without `report.view` gets 403 on both the export and the status endpoints.
3. **Dedupe:** two simultaneous clicks produce one row and one job.
4. **Memory and time:** run the job on a 2 M-row report on staging. Record peak memory (must be well under 512 MB) and duration (must be well under 1800 s).
5. **Failure injection:**
   - Raise in the middle of the upload, and check that `abort_multipart` runs and no object appears at the key.
   - Fail all 3 attempts, and check for `failed` status plus the failure email.
   - Fail `send_email` once, and check the retry sends only the email.
6. **Duplicate delivery:** run the handler twice on the same export, and check that there is one file and one email.
7. **Stale row:** a `running` row older than 3 hours is cleared on the next click.

## Open questions for the owner

1. If all attempts fail only at the email step, the page shows "done" but the user has no link. Should the page offer a "Get link" button that generates a fresh 24-hour signed URL while the file exists (up to 7 days)?
2. Should an export with different filters from an already-running one be allowed? The brief says one per report, so this plan blocks it.
3. Should the job export a consistent snapshot if the nightly rebuild runs mid-export? This plan accepts a possible mix.
4. Cells starting with `=`, `+`, `-` or `@` can be run as formulas in spreadsheet programs. Do we escape them in the CSV? Escaping changes negative numbers, so this plan leaves them as they are.
