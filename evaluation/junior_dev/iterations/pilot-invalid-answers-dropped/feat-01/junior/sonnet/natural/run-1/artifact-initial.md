# Plan: Download CSV on the reports page

## How it works

The browser sends the click to one new endpoint, `POST /api/reports/{report_id}/export`. The endpoint reads `reports.row_count` and picks a path.

- **Small report, 10,000 rows or fewer.** The endpoint builds the CSV and returns it in the response. No job runs and nothing is stored.
- **Large report, more than 10,000 rows.** The endpoint records an export row, enqueues a background job, and returns `202` with the export. The job streams the CSV into the `exports` bucket in parts, publishes it, and emails a 24-hour link. The page shows the export's state throughout.

**Where state lives**

| State | Where | Why |
|---|---|---|
| What the user is viewing (filters, column order) | Page URL only. The click sends it with the request. | The server stores nothing about the current view today. |
| Large-export state (queued, running, done, failed) | New `exports` table in the primary database | This is app state, not report data. The "no report data from the primary" rule does not apply. |
| The file | `exports` bucket, key `reports/{report_id}/{export_id}.csv` | Created by the job. The existing 7-day lifecycle rule deletes it. |
| In-flight upload | Multipart upload in the bucket | It is invisible until completed. The existing 24-hour rule discards abandoned uploads. |

**Existing constraints this plan relies on**

- `report_rows` is read only from the read replica, by keyset paging (`row_id > after ORDER BY row_id`), never OFFSET.
- API requests are killed after 60 seconds.
- A worker has 512 MB of memory.
- A job attempt is killed after 1800 s.
- A job is tried at most 3 times, with 60 s and 300 s of backoff.
- The queue keeps no progress between attempts.
- Delivery is at least once.

---

## Step 1. Add the `exports` table (one-off migration)

- **Starts when:** this change is deployed.
- **Data:** one row per large export, with these columns.
  - `export_id` (primary key)
  - `user_id`
  - `report_id`
  - `filters` and `cols` (the exact view the user clicked on)
  - `status` (`queued`, `running`, `done` or `failed`)
  - `attempt` (the number of the latest attempt that started; 0 until the first one starts)
  - `job_id`
  - `object_key`
  - `rows_written`
  - `error` (short, user-safe text)
  - `email_sent_at`
  - `created_at`, `updated_at`, `finished_at`
- **Constraint that enforces "one at a time":** a **partial unique index** on `(user_id, report_id) WHERE status IN ('queued','running')`. The database enforces the rule, so two simultaneous clicks cannot both create an export. Rows that are `done` or `failed` fall outside the index, so the user can export again.
- **State:** primary database.
- **If it fails:** the migration fails and the deploy stops. Nothing else depends on it yet.

## Step 2. Export endpoint: authorise, validate, choose a path

- **Starts when:** the user clicks **Download CSV**. The page calls `POST /api/reports/{report_id}/export?<the page's current query string>`, so the filters and `cols` come from the URL.
- **Data:** the request carries the report id, the filters, `cols` and the user's session.
  1. Run the same `report.view` check as the rows API. Return **403** if it fails.
  2. Parse and validate `filters` and `cols` with the **same parsing and query-building code the rows API uses**. Do not write a second copy, or the CSV could drift from what the page shows. An unknown column or filter returns **400**.
  3. Read `reports.row_count`. Take the large path if it is **above 10,000 or missing**. "Missing" counts as large, because the safe default is the job.
- **State:** none written yet.
- **If it fails:** 403 or 400 as above. An unexpected error returns 500 and nothing has been created. The user can click again.
- **Note:** `row_count` is the unfiltered total, as the brief fixes. A narrow filter on a large report still uses the job, which is correct but slower than strictly needed.

## Step 3. Small path: respond with the CSV

- **Starts when:** step 2 chose the small path.
- **Data:** read rows from the **read replica** in keyset pages (`row_id > after ORDER BY row_id LIMIT 1000`) until a page comes back short.
  - Write a header row from `cols`, then each row, using a real CSV writer so quotes, commas and newlines are escaped. Apply the same value formatting as the page.
  - **Build the whole CSV in memory** before sending anything. At most 10,000 rows is well under 1 MB (the largest report is about 450 bytes per row), and building first means an error gives a clean 500 rather than a truncated file with a 200 status.
  - Respond `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{id}-{date}.csv"`.
  - The page receives this response, sees `text/csv`, and saves it as a file.
- **State:** none. No job, no table row, no storage.
- **If it fails:**
  - A replica error returns 500 and the page shows "Export failed, try again".
  - Stop at 45 s (inside the 60 s kill) with 503. This should never happen at this size.
  - Nothing needs cleaning up.

## Step 4. Large path: create the export, or return the one already active

- **Starts when:** step 2 chose the large path.
- **Data:** in one statement, `INSERT INTO exports (…, status='queued') … ON CONFLICT DO NOTHING RETURNING *`.
  - If a row is returned, this click created a new export. Continue to step 5.
  - If nothing is returned, the partial unique index found an active export for this user and report. `SELECT` it and return it with `already_active: true` and **HTTP 200**. No second export is created.
  - If the existing export has different filters or columns from this click, the response says so, because the active export is the one the brief requires returning. The page shows its filters ("Export in progress for: status=open…").
- **State:** `exports` row on the primary database.
- **If it fails:** a database error returns 500 and nothing was created.

## Step 5. Enqueue the job

- **Starts when:** step 4 created a new row.
- **Data:** call `enqueue("export_report", {"export_id": ...})`. The payload holds **only the id**. Filters can be long and the payload limit is 64 KB, so the job loads everything else from the row. Save the returned `job_id` on the row, then respond **202** `{export_id, status: "queued", ...}`.
- **State:** `exports.job_id`.
- **If it fails:**
  - **`enqueue` raises.** Mark the row `failed` with a short error, so it does not block the user, and return 503. The user can click again.
  - **The API process dies between the insert and the enqueue.** The row would stay `queued` with no job and block the user. To cover this, step 4's "already active" branch applies a repair rule. If the active row is `queued`, has no `job_id`, and is more than 2 minutes old, call `enqueue` again with the same `export_id` and store the new `job_id`. The job is safe to run twice (steps 6 to 9), so this is harmless.

## Step 6. Job start: load the row and guard against re-runs

- **Starts when:** the worker picks up `export_report(ctx, payload)`. This happens on each of up to 3 attempts, and occasionally twice for the same attempt because delivery is at least once.
- **Data:** load the `exports` row by `export_id`.
  - If `status` is `failed`, return without doing anything.
  - If `status` is `done` and `email_sent_at` is set, return. This is a duplicate delivery.
  - If `status` is `done` but `email_sent_at` is empty, jump to step 9. The file exists and only the email is missing.
  - Otherwise set `status='running'`, `attempt=ctx.attempt` and `updated_at`.
  - **Re-check `report.view`** for the stored `user_id`, because permissions may have changed since the click. If it is now denied, set `failed` with the error "You no longer have access to this report" and return normally. Do not retry and do not send the link.
- **State:** `exports.status`, `attempt`.
- **If it fails:** an error raised here is a normal failed attempt. The queue retries it (see step 10).

## Step 7. Job: stream the report into a multipart upload

This is the memory- and time-critical step. Each attempt starts from scratch, because the queue keeps no progress. The key is deterministic, so a retry overwrites the same object.

- **Starts when:** step 6 passes.
- **Data:**
  1. `upload_id = start_multipart("exports", "reports/{report_id}/{export_id}.csv")`. Nothing is visible at that key yet.
  2. Write the header row into an in-memory buffer.
  3. Loop: read the next page of **5,000 rows** from the **read replica** with the same view query as the page (stored filters and `cols`, keyset `row_id > after ORDER BY row_id`). Encode the rows as CSV into the buffer, then remember the last `row_id` as `after`.
  4. Whenever the buffer reaches **8 MiB**, call `upload_part(upload_id, n, buffer)`, keep the returned etag, and **empty the buffer**.
  5. Repeat until a page comes back empty. Upload the remaining buffer as the last part. Because the header is always written, there is always at least one part, even for a filter that matches nothing.
- **Why these numbers:**
  - The minimum part is 5 MB, so 8 MiB is safe.
  - 8 MiB × 10,000 parts is about 80 GB, far above the largest report. The biggest (about 900 MB) needs about 113 parts.
  - Memory at any moment is one 8 MiB buffer, one page of rows and a list of at most ~113 etags. That is far below 512 MB and does not grow with report size.
  - 2 million rows is about 400 page reads, instead of 4,000 at the page's 500-row size.
- **State:** the in-progress multipart upload. Nothing is visible to anyone. The local variables `upload_id`, etags and `after` exist only inside this attempt.
- **Time limit:** the attempt is killed at 1800 s. The job sets its own deadline at about 1500 s. If it passes the deadline, it calls `abort_multipart` and raises a clear error, so it fails cleanly rather than being killed. Retrying a too-slow job will not make it faster, but the retries are bounded at 3. **Before launch**, measure the real throughput against a ~2-million-row test report to confirm there is headroom (see step 13).
- **If it fails:**
  - **A replica or storage error raises.** The `except` block calls `abort_multipart(upload_id)` as best effort, then re-raises. The attempt fails and the queue retries after the backoff.
  - **The worker is killed or times out.** No cleanup code can run. The orphaned upload is harmless, because it is invisible and the bucket discards incomplete uploads after 24 hours. No cleanup job is needed.
  - **Result:** a half-written file can never be downloadable, because the object only appears at `complete_multipart` in step 8.

## Step 8. Job: publish the file and mark the export done

- **Starts when:** the last part is uploaded.
- **Data:** `complete_multipart(upload_id, etags)` makes the object visible. Then update the row with `status='done'`, `object_key`, `rows_written` and `finished_at`.
- **State:** the object in the `exports` bucket, and `exports.status='done'`.
- **If it fails:**
  - **`complete_multipart` raises.** The attempt fails and is retried. Nothing is visible.
  - **The worker dies after `complete_multipart` but before the row update.** The next attempt rebuilds the file. The key is the same and `complete_multipart` replaces the object, so no duplicates result.
  - **A duplicate delivery produces the same file.** Replacing the object with identical content is harmless.

## Step 9. Job: email the download link

- **Starts when:** the row is `done`.
- **Data:** `url = signed_url("exports", object_key, 86_400)`. This is the 24-hour maximum, generated now so it lasts 24 hours from the email. Then call `send_email(user_id, "export_ready", {report name, url, row count})`, and set `email_sent_at`.
- **State:** `exports.email_sent_at`.
- **If it fails:**
  - **`send_email` raises.** The attempt fails and is retried. On retry, step 6 sees `done` with no `email_sent_at` and goes straight to this step, so it does **not** rebuild the file. A new signed URL is generated each time.
  - **The worker dies between sending and setting `email_sent_at`.** The user may get a second email. This is accepted, because delivery is at least once.

## Step 10. Retries and final failure

- **Starts when:** an attempt fails (raises, times out, or its worker dies).
- **Data:**
  - **Between attempts.** The queue waits 60 s, then 300 s, then retries. The row stays `running` (with `attempt` updated), so it still counts as active and the "one at a time" rule holds.
  - **After the third failed attempt.** The queue calls `on_final_failure(ctx, payload, error)` once. It does the following.
    1. If the row is already `done`, there is a file but the email never went out. Do **not** mark it failed. Log an alert and stop. The page still shows `done` and step 12 gives the user a download link.
    2. Otherwise set `status='failed'`, `error` to a short user-safe message (not a stack trace) and `finished_at`. Use a conditional update (`WHERE status IN ('queued','running')`) so a late duplicate cannot be overwritten.
    3. Call `send_email(user_id, "export_failed", {report name})`.
- **State:** `exports.status='failed'`. A `failed` row no longer matches the unique index, so the user can click **Download CSV** again for a fresh export.
- **If it fails:** if the failure email itself fails, the row is already `failed` and the page shows it. Log the email error. Do not raise, because the queue calls this hook only once.

## Step 11. Show the state on the page

- **Starts when:**
  - the report page loads (so a user who comes back later sees the state), and
  - the user clicks the button (so the page shows the new state immediately).
- **Data:**
  - **New endpoint `GET /api/reports/{report_id}/export`.** It checks `report.view` and returns **the current user's most recent export for this report** (or `null`) as `{export_id, status, attempt, filters, cols, created_at, finished_at, expired}`. It reads from the **primary**, not the replica. Replica lag could otherwise show "nothing" right after a click, and export state is not report data. Users only ever see their own exports.
  - **On the click response.** The page uses the response body of the POST directly for its first render.
  - **Polling.** While the state is `queued` or `running`, the page polls the endpoint every 5 s. It stops on `done` or `failed` (and when the user leaves the page). The label reads "Queued", "Running (attempt 2 of 3)", "Done" or "Failed".
  - **Expiry.** Files are deleted after 7 days. If `status='done'` and `finished_at` is older than 7 days, return `expired: true`. The page shows "Done (file expired, export again)" and hides the download button.
- **State:** none new. It reads `exports`.
- **If it fails:** a failed poll keeps the last known state and retries on the next tick. The page table is unaffected, since this panel is separate from it.

## Step 12. Download from the page when the email link has lapsed

- **Starts when:** the user clicks **Download** on a `done` export.
- **Data:** `GET /api/reports/{report_id}/export/{export_id}/download` checks `report.view` and that the export belongs to the user, requires `done` and not `expired`, then returns a redirect to a new `signed_url(..., 86_400)`.
- **State:** none.
- **If it fails:** 403 or 404 as appropriate. If the object is already gone, return `expired`.
- **Note:** this step goes slightly beyond the brief, which only specifies the emailed link. I included it because otherwise a "Done" export is useless after the email link lapses at 24 hours. It can be dropped without affecting the other steps.

## Step 13. Verification before release

Cover each behaviour with an automated test.

- **Size boundary.** 10,000 rows returns the CSV with no job and no row in `exports`. 10,001 rows (and a missing `row_count`) returns 202 and runs a job.
- **Correct contents.** The CSV matches the page for the same filters and column order, including a header row and values containing commas, quotes and newlines.
- **Replica only.** The row queries run against the replica. A guard fails the test if report data is read from the primary.
- **Permissions.** A user without `report.view` gets 403 from the POST, the status GET and the download GET. A job for a user who has lost access fails without a link.
- **One at a time.** Fire two simultaneous POSTs for the same user and report. Exactly one export exists, and both responses reference it. After it is `done` or `failed`, a new click creates a new export.
- **Orphan repair.** A `queued` row with no `job_id` older than 2 minutes is re-enqueued by the next click.
- **No partial file.** Kill the worker mid-upload. Nothing is readable at the key, and the retry produces a complete file.
- **Retries.** Fail attempts 1 and 2 and succeed on 3: the file is complete and one email is sent. Fail all three: the row is `failed` and one failure email is sent.
- **Duplicate delivery.** Run the job twice for a finished export. No second file is built and no second email is sent. A `done` export with no `email_sent_at` only resends the email.
- **Memory.** Run a synthetic 2-million-row report on a 512 MB worker. Peak memory stays flat (target well under 150 MB) and does not grow with row count.
- **Duration.** The same run finishes comfortably inside the 1800 s timeout. Record the real time. If it is above about 1000 s, raise the page size or investigate the replica query before launch.

---

## Decisions to confirm

1. **Different view while an export is active.** "One at a time" is per user and report, not per filter set. A click with different filters returns the active export with its own filters shown. The alternative is to key the rule on the view as well, which allows parallel exports of different views.
2. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas when the CSV is opened in a spreadsheet. The brief does not mention this. The plan exports values exactly as the page shows them, and escaping would be a small addition to the shared CSV writer.
3. **`row_count` source.** The plan reads `reports.row_count` the same way the page does. If that table is only on the primary, one small metadata read there is needed, and it is not report data.
4. **Step 12 and the "expired" label** are additions beyond the brief, as noted above.
