# Plan: Download CSV on the reports page

## How it works

The browser sends the click to one new endpoint, `POST /api/reports/{report_id}/export`. The endpoint reads `reports.row_count` and picks a path.

- **Small report, 10,000 rows or fewer.** The endpoint builds the CSV and returns it in the response (`Content-Type: text/csv`). No job runs and nothing is stored. Because `row_count` can be stale, the endpoint reads at most 10,001 rows; if it finds more than 10,000 it drops what it read and switches to the large path (Step 4).
- **Large report, more than 10,000 rows.** The endpoint records an export row, enqueues a background job, and returns JSON describing the export (`202`). The job streams the CSV into the `exports` bucket in parts, publishes it, and emails a 24-hour link. The page shows the export's state throughout.

**Where state lives**

| State | Where | Why |
|---|---|---|
| What the user is viewing (filters, column order) | Page URL only. The click sends it with the request. | The server stores nothing about the current view today. |
| Large-export state (queued, running, done, failed) | New `exports` table in the primary database | This is app state, not report data. The "no report data from the primary" rule does not apply. |
| The file | `exports` bucket, key `reports/{report_id}/{export_id}.csv` | Created by the job. The existing 7-day lifecycle rule deletes it. |
| In-flight upload | Multipart upload in the bucket | It is invisible until completed. The existing 24-hour rule discards abandoned uploads. |

The two lifecycle rules are existing platform configuration on the bucket. This plan changes nothing there.

**Existing pieces this plan uses.** All of these already exist; the plan adds no new library.

| Piece | What it is |
|---|---|
| `reports.row_count` | The total, unfiltered number of rows in a report. It is rewritten each night when the report data is rebuilt, so it matches the data until the next rebuild and can differ from it for at most a day's changes. If the value is NULL or the row is absent, the plan treats it as "unknown" and takes the large path. A stale value that is too low is caught by the row cap in Step 3. A stale value that is too high just sends a small report down the large path, which is correct but slower. The same `reports` row also gives the report's name and workspace, which the endpoints and the job use for permission checks and emails. |
| Rows API | `GET /api/reports/{report_id}/rows?filters=&cols=&after=&limit=`. Checks `report.view`, reads `report_rows` from the read replica, pages by `row_id` (keyset). The page asks it for `limit=500` rows at a time. The export does not call this HTTP endpoint; it reuses the same parsing, query-building and value-formatting code (see Decisions to confirm, item 5). |
| Job queue (`jobs.py`) | `@job(name, on_final_failure=hook)` registers a handler `handler(ctx, payload)`. `enqueue(name, payload)` returns a `job_id`. `ctx.attempt` is 1, 2 or 3, set by the queue. The queue itself calls `on_final_failure(ctx, payload, error)` once, after the third failed attempt. An attempt fails only if the handler raises, times out, or its worker dies; a handler that returns normally counts as success and is not retried. |
| Object storage (`storage.py`) | `start_multipart(bucket, key)` returns an `upload_id`; `upload_part(upload_id, n, data)` returns an etag; `complete_multipart(upload_id, etags)` makes the object visible; `abort_multipart(upload_id)` discards the parts; `signed_url(bucket, key, ttl_seconds)` returns a download link (maximum 86,400 s). The `exports` bucket already exists. |
| `send_email(user_id, template, params)` | Existing email sender. The plan needs two templates, `export_ready` and `export_failed`. Whether templates must be created in a particular place is not known (see Decisions to confirm). |

**Existing constraints this plan relies on**

- `report_rows` is read only from the read replica, by keyset paging (`row_id > after ORDER BY row_id`), never OFFSET.
- API requests are killed after 60 seconds.
- A worker has 512 MB of memory.
- A job attempt is killed after 1800 s.
- A job is tried at most 3 times, with 60 s and 300 s of backoff.
- The queue keeps no progress between attempts.
- Delivery is at least once.

**CSV format (used by both paths).** UTF-8, no byte-order mark, written by a standard CSV writer (default quoting and line endings). The first row is the header, built from `cols`. Cell values are formatted by the rows API's existing formatting code.

**Response shapes of `POST /api/reports/{report_id}/export`.** The page tells them apart by the `Content-Type` header, then the status, then (for JSON) the `already_active` field. The POST never returns `null`; `null` appears only in the status `GET` (Step 11).

| Case | Status | Content-Type | Body |
|---|---|---|---|
| Small report | 200 | `text/csv` | The CSV file |
| New large export | 202 | `application/json` | `{export_id, status: "queued", filters, cols, created_at, already_active: false}` |
| Large export already active | 200 | `application/json` | The same shape for the active export, with `already_active: true` |
| Error | 400, 403, 500, 503 | `application/json` | `{error}` (short, user-safe text, for logs and as a fallback) |

**The export panel (page side).** The page gets one new component, the export panel, placed above the table and separate from it. It holds one piece of state: "the current export" (or none) for the report in the page URL. It does three things:

1. On page load it calls the status `GET` (Step 11) once and renders whatever comes back.
2. On a click of **Download CSV** it calls the POST and renders the response as described below.
3. While the current export is `queued` or `running` it polls the status `GET` every 5 s.

The **Download** button (Step 12) is shown only when the current export is `done` and not expired. It uses that export's `export_id` and the page's `report_id` from the URL, so it always refers to the export the panel is showing.

**What the page does with each error.** The click handler shows a message in the export panel. It shows the message from this table, not the server's `error` text. It never creates export state for an error, and the user can click again.

| Result | Message |
|---|---|
| 400 | "This view can't be exported. Reload the page and try again." |
| 403 | "You don't have access to export this report." |
| 500 or 503 | "Export failed, try again." |
| Network failure (no response) | "Export failed, check your connection and try again." |

**How the page renders a JSON export response.** If `already_active` is `false`, the panel shows the normal state label ("Queued") and starts polling. If `already_active` is `true`, the panel shows "Export in progress for: &lt;the export's filters&gt;" plus the state label, and polls the same way. The filters text is the active export's stored `filters` string, cut to 80 characters with "…" added if it was longer.

---

## Step 1. Add the `exports` table (one-off migration)

- **Starts when:** this change is deployed.
- **Data:** one row per large export, with these columns.
    - `export_id` (primary key)
    - `user_id`
    - `report_id`
    - `filters` and `cols` (the exact view the user clicked on). Both are text columns holding the strings from the page URL as sent, saved only after Step 2 has validated them. The job re-parses them with `build_rows_query`.
    - `status` (`queued`, `running`, `done` or `failed`)
    - `attempt` (the number of the latest attempt that claimed the export in Step 6; 0 until the first one does)
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

- **Starts when:** the user clicks **Download CSV**. The page calls `POST /api/reports/{report_id}/export?<the page's current query string>` with `fetch`, sending the session cookie. The filters and `cols` come from the URL.
- **Data:** the request carries the report id, the filters, `cols` and the user's session.
    1. Run the same `report.view` check as the rows API (the logged-in user against the report's workspace). Return **403** if it fails.
    2. Parse and validate `filters` and `cols` with the **same parsing and query-building code the rows API uses** (called `build_rows_query` below; that name is a placeholder for whatever the rows API uses). Do not write a second copy, or the CSV could drift from what the page shows. An unknown column or filter returns **400**.
    3. Read `reports.row_count`. Take the large path if it is **above 10,000, NULL or missing**. Unknown counts as large, because the safe default is the job. Otherwise take the small path.
- **State:** none written yet.
- **If it fails:** 403 or 400 as above. An unexpected error returns 500 and nothing has been created. The user can click again. The page shows the messages in the error table above.
- **Note:** `row_count` is the unfiltered total, as the brief fixes. A narrow filter on a large report still uses the job, which is correct but slower than strictly needed.

## Step 3. Small path: respond with the CSV

- **Starts when:** Step 2 chose the small path.
- **Data:** read rows from the **read replica** in keyset pages (`row_id > after ORDER BY row_id LIMIT 1000`) until a page comes back short.
    - **Row cap.** `row_count` can be up to a day stale, so it is only a hint. Stop reading as soon as the endpoint has **10,001 rows**. If it reaches 10,001, throw away what it has built and go to **Step 4 of this plan** (the large path), exactly as if Step 2 had chosen it. The user never sees an error for this. This also bounds memory whatever `row_count` says. (Example: `row_count` says 9,990 but the report really has 10,400 rows: the endpoint stops at 10,001 and starts a large export.)
    - The cap applies to the rows the user's filters return. A filtered view with 10,000 or fewer rows stays on the small path even if the unfiltered report is large and `row_count` is stale-low; that is fine.
    - Write a header row from `cols`, then each row, using a real CSV writer so quotes, commas and newlines are escaped. Apply the same value formatting as the page, by calling the same formatting code the rows API uses (see Decisions to confirm, item 5); this plan defines no formatting rules of its own.
    - **Build the whole CSV in memory** before sending anything. At most 10,000 rows is well under 1 MB (the largest report is about 450 bytes per row), and building first means an error gives a clean 500 rather than a truncated file with a 200 status.
    - Respond `200`, `Content-Type: text/csv`, `Content-Disposition: attachment; filename="report-{report_id}-{YYYY-MM-DD}.csv"`. The date is today's date in UTC.
    - **How the page saves it.** The page's click handler uses `fetch`, so the session cookie is sent. If the response `Content-Type` is `text/csv`, the handler reads the body as a Blob and takes the file name from the quoted `filename="..."` value in `Content-Disposition` (falling back to `report.csv` if it is missing). It makes a temporary object URL, clicks a hidden `&lt;a download="..."&gt;` link with that name, then releases the URL. If it is `application/json` with status 200 or 202, the handler treats the body as an export (see "How the page renders a JSON export response" above, and Step 11) and starts showing its state. Any other status shows the error messages above. The body is under 1 MB, so holding it in the browser is fine.
- **State:** none. No job, no table row, no storage.
- **If it fails:**
    - A replica error returns 500.
    - **The 45 s stop.** The endpoint records its start time. Before reading each page it checks the elapsed time, and if more than 45 s have passed it stops and returns 503. This is a check in the endpoint's own loop, not a separate timer. It can only act between pages, so a single page read that hangs is not interrupted by it; the 60 s server kill remains the backstop. If the database client supports a per-query timeout, set it to the time left until 45 s (whether it does is not known; see Decisions to confirm). At this size the stop should never trigger.
    - Nothing needs cleaning up.
- **Consistency note.** The small path reads in several pages, so if the nightly rebuild happens to run during the read, the page could mix old and new rows (see Step 7 for the open question). At this size the read takes well under a second, so the window is tiny.

## Step 4. Large path: create the export, or return the one already active

- **Starts when:** Step 2 chose the large path, or Step 3 hit the 10,001-row cap.
- **Data:** in one statement, `INSERT INTO exports (…, status='queued') … ON CONFLICT DO NOTHING RETURNING *`.
    - If a row is returned, this click created a new export. Continue to Step 5.
    - If nothing is returned, the partial unique index found an active export for this user and report. `SELECT` it, apply the repair check from Step 5, and return it as **HTTP 200** with `already_active: true` (body shape in the table above). No second export is created.
    - **If this click had different filters or columns** from the active export, the user does not get a CSV for the new view. The response still carries the active export's own `filters` and `cols`, and the page shows "Export in progress for: status=open…". The user must wait until that export is `done` or `failed`, then click again. This is the cost of the "one at a time" rule (see Decisions to confirm, item 1).
- **State:** `exports` row on the primary database.
- **If it fails:** a database error returns 500 and nothing was created.
- **Time:** Steps 4 and 5 are a few quick statements plus one `enqueue` call, so they finish far inside the 60 s API limit. If one of them hangs, the 60 s kill ends the request; the row may then be `queued` with no `job_id`, which the repair check in Step 5 handles.

## Step 5. Enqueue the job

- **Starts when:** Step 4 created a new row.
- **Data:** call `enqueue("export_report", {"export_id": ...})`. The payload holds **only the id**. Filters can be long and the payload limit is 64 KB, so the job loads everything else from the row. Save the returned `job_id` on the row, then respond **202** (body shape in the table above).
- **State:** `exports.job_id`.
- **If it fails:**
    - **`enqueue` raises.** Mark the row `failed` with a short error, so it does not block the user, and return 503. The user can click again.
    - **The API process dies between the insert and the enqueue (or the request is killed at 60 s).** The row would stay `queued` with no job and block the user. A **repair check** covers this. It runs whenever the API reads an active export: in Step 4's "already active" branch and in the status `GET` (Step 11), which the page also calls on every load and every poll. So a user who just reloads the page triggers it, without clicking again.
        - **The check:** the row is `queued`, `job_id` is NULL and `created_at` is more than 2 minutes ago (a named constant in the code).
        - **Claim it first:** `UPDATE exports SET updated_at = now() WHERE export_id = ? AND job_id IS NULL AND status = 'queued' AND created_at < now() - interval '2 minutes' RETURNING *`. Only the request that gets a row back calls `enqueue` again with the same `export_id` and stores the new `job_id`.
        - A concurrent double enqueue is still possible if a claimed request dies before storing the `job_id`; this is harmless because Step 6 lets only one copy of the job do the work.
        - **If the user never returns:** nobody triggers the check, the row stays `queued` and no file or email is produced. Accepted: the user has gone away, and their next visit repairs it.
    - **The job was enqueued but the queue never runs it.** Nothing in this plan detects that; it relies on the queue (see Decisions to confirm, item 11).

## Step 6. Job start: claim the export and guard against re-runs

- **Starts when:** the worker picks up `export_report(ctx, payload)`, registered as `@job("export_report", on_final_failure=export_failed_hook)`. The queue calls it on each of up to 3 attempts and sets `ctx.attempt` (1, 2 or 3). Occasionally it runs twice for the same attempt, even at the same time, because delivery is at least once. The queue does not start attempt N+1 until attempt N has finished, failed or been killed.
- **Data:** load the `exports` row by `export_id`.
    - If `status` is `failed`, return without doing anything.
    - If `status` is `done` and `email_sent_at` is set, return. This is a duplicate delivery.
    - If `status` is `done` but `email_sent_at` is empty, jump to Step 9. The file exists and only the email is missing.
    - **Claim the export with one conditional statement:** `UPDATE exports SET status='running', attempt=&lt;ctx.attempt&gt;, updated_at=now() WHERE export_id=? AND status IN ('queued','running') AND attempt &lt; &lt;ctx.attempt&gt; RETURNING *`. If no row comes back, another copy of this same attempt already claimed it (or the export is finished), so return without doing anything. This is what keeps two simultaneous copies from both building the file and both sending email: the database lets exactly one of them through. The `attempt &lt; ctx.attempt` condition also lets a later attempt take over from an earlier one that died while the row still said `running`.
    - **Re-check `report.view`** for the stored `user_id` on the report's workspace (read from the report's `reports` row), because permissions may have changed since the click. The job has no session, so it needs the permission check in a form that takes a user id (see Decisions to confirm, item 5). If it is now denied, set `failed` with the error "You no longer have access to this report" and **return normally**. A normal return counts as success for the queue, so it does not retry and does not call `on_final_failure`. No link and no email of any kind is sent in this case: the user no longer has access, and the page shows the export as failed.
    - **Every later write by this attempt** (Steps 8 and 9) is conditional on `attempt = &lt;ctx.attempt&gt;`, so a stale copy cannot overwrite a newer attempt's result.
- **State:** `exports.status`, `attempt`.
- **If it fails:** an error raised here is a normal failed attempt. The queue retries it (see Step 10).
- **Limit:** if the queue ever re-delivered the same attempt number after a worker died, this claim would skip it. The queue's documentation says a dead worker fails the attempt and a new attempt number is used, so this is not expected (see Decisions to confirm).

## Step 7. Job: stream the report into a multipart upload

This is the memory- and time-critical step. Each attempt starts from scratch, because the queue keeps no progress. The key is deterministic, so a retry overwrites the same object.

- **Starts when:** Step 6 passes.
- **Data:**
    1. `upload_id = start_multipart("exports", "reports/{report_id}/{export_id}.csv")`. Nothing is visible at that key yet.
    2. Write the header row into an in-memory buffer.
    3. Loop: read the next page of **5,000 rows** from the **read replica**, using `build_rows_query` with the **stored** `filters` and `cols` from the row and `row_id > after ORDER BY row_id`. This function needs only those stored values, not the user's session; permission was checked in Step 6. Encode the rows as CSV into the buffer (same writer, encoding and formatting as Step 3), then remember the last `row_id` as `after`.
    4. Whenever the buffer reaches **8 MiB of encoded bytes**, call `upload_part(upload_id, n, buffer)`, keep the returned etag, and **empty the buffer**.
    5. Repeat until a page comes back empty. Upload the remaining buffer as the last part. Because the header is always written, there is always at least one part, even for a filter that matches nothing.
- **Why these numbers:**
    - The minimum part is 5 MB, so 8 MiB is safe.
    - 8 MiB × 10,000 parts is about 80 GB, far above the largest report. The biggest (about 900 MB) needs about 113 parts.
    - Memory at any moment is one 8 MiB buffer, one page of rows and a list of at most ~113 etags. That is far below 512 MB and does not grow with report size.
    - 2 million rows is about 400 page reads, instead of 4,000 at the rows API's 500-row page size. The job queries the database directly, so it is not bound by that API limit.
- **Data consistency (the nightly rebuild).** The export is not a snapshot. The job reads the live `report_rows` a page at a time, so the file reflects whatever the replica returned as it paged. Each attempt rebuilds the file from scratch, so a retry can see different data from the first attempt, and only the last successful attempt's file is kept. It is **not known** how the nightly rebuild rewrites `report_rows` (in place, or into a new table swapped in) or whether `row_id` values stay stable across a rebuild. If the rebuild rewrites rows in place while a job pages, the file could miss, duplicate or mix old and new rows, and the user is not told. The plan does not defend against this. See Decisions to confirm, item 9. If the rebuild window is known, the simplest mitigation is to have the job fail and retry if it overlaps it.
- **State:** the in-progress multipart upload. Nothing is visible to anyone. The local variables `upload_id`, etags and `after` exist only inside this attempt.
- **Time limit:** the attempt is killed at 1800 s. The job sets its own deadline at about 1500 s. If it passes the deadline, it calls `abort_multipart` and raises a clear error, so it fails cleanly rather than being killed. Retrying a too-slow job will not make it faster, but the retries are bounded at 3. **Before launch**, measure the real throughput against a ~2-million-row test report to confirm there is headroom (see Step 13).
- **If it fails:**
    - **A replica or storage error raises.** The `except` block calls `abort_multipart(upload_id)` as best effort, then re-raises. The attempt fails and the queue retries after the backoff.
    - **The worker is killed or times out.** No cleanup code can run. The orphaned upload is harmless, because it is invisible and the bucket discards incomplete uploads after 24 hours. No cleanup job is needed.
    - **Result:** a half-written file can never be downloadable, because the object only appears at `complete_multipart` in Step 8.

## Step 8. Job: publish the file and mark the export done

- **Starts when:** the last part is uploaded.
- **Data:** `complete_multipart(upload_id, etags)` makes the object visible. Then update the row with `status='done'`, `object_key`, `rows_written` and `finished_at`, conditional on `attempt = &lt;ctx.attempt&gt;`.
- **State:** the object in the `exports` bucket, and `exports.status='done'`.
- **If it fails:**
    - **`complete_multipart` raises.** The attempt fails and is retried. Nothing is visible.
    - **The worker dies after `complete_multipart` but before the row update.** The next attempt rebuilds the file. The key is the same and `complete_multipart` replaces the object, so no duplicates result.

## Step 9. Job: email the download link

- **Starts when:** the row is `done`.
- **Data:** `url = signed_url("exports", object_key, 86_400)`. This is the 24-hour maximum, generated now so it lasts 24 hours from the email. Then call `send_email(user_id, "export_ready", {report name, url, row count})` (report name from the report's `reports` row, row count from `rows_written`), and set `email_sent_at`.
- **State:** `exports.email_sent_at`.
- **If it fails:**
    - **`send_email` raises.** The attempt fails and is retried. On retry, Step 6 sees `done` with no `email_sent_at` and goes straight to this step, so it does **not** rebuild the file. A new signed URL is generated each time. (Because that path skips the claim, two copies running at once there could each send an email; accepted, see below.)
    - **The worker dies between sending and setting `email_sent_at`, or two copies reach this step together.** The user may get a second email. This is accepted, because delivery is at least once and a duplicate email is harmless.

## Step 10. Retries and final failure

- **Starts when:** an attempt fails (raises, times out, or its worker dies). The queue itself detects this, because it owns the timeout and the worker; our code does not need to notice. This includes a worker that dies on the last attempt: that attempt counts as failed and `on_final_failure` still runs.
- **Data:**
    - **Between attempts.** The queue waits 60 s, then 300 s, then retries. Our code cannot run when a worker dies, so the row cannot be updated. It stays `running` with the `attempt` number of the attempt that died, so it still counts as active and the "one at a time" rule holds. The page therefore keeps showing "Running (attempt 1 of 3)" during the wait. This is accepted as slightly imprecise; the worst case from first start to final failure is about 95 minutes (3 × 1800 s plus 360 s of backoff).
    - **After the third failed attempt.** The queue calls `on_final_failure(ctx, payload, error)` once. It does the following.
        1. If the row is already `done`, there is a file but the email never went out. Do **not** mark it failed. Write an error-level log line with the `export_id` (how the platform routes error logs to alerts, and so whether anyone is told, is outside this plan; see Decisions to confirm, item 10) and stop. The page still shows `done` and Step 12 gives the user a download link.
        2. Otherwise set `status='failed'`, `error` to a short user-safe message (not a stack trace) and `finished_at`. Use a conditional update (`WHERE status IN ('queued','running')`) so a late duplicate cannot be overwritten.
        3. Call `send_email(user_id, "export_failed", {report name})`.
- **State:** `exports.status='failed'`. A `failed` row no longer matches the unique index, so the user can click **Download CSV** again for a fresh export.
- **If it fails:** if the failure email itself fails, the row is already `failed` and the page shows it. Log the email error. Do not raise, because the queue calls this hook only once.

## Step 11. Show the state on the page

- **Starts when:**
    - the report page loads (so a user who comes back later sees the state), and
    - the user clicks the button (so the page shows the new state immediately).
- **Data:**
    - **New endpoint `GET /api/reports/{report_id}/export`.** It checks `report.view`, runs the repair check from Step 5, and returns **the current user's most recent export for this report** (the row with the latest `created_at`) as `200 application/json` with body `{export_id, status, attempt, filters, cols, created_at, finished_at, error, expired}`. If the user has never exported this report, it returns `200` with the JSON body `null`, and the export panel shows no export state. It reads from the **primary**, not the replica. Replica lag could otherwise show "nothing" right after a click, and export state is not report data. Users only ever see their own exports.
    - **Which export the page shows.** Always the most recent one, whatever its state. A `done` export stays shown, with its Download button (Step 12), on every later page load until the user starts a newer export or the file expires. The server does not track whether the email link or the download was already used.
    - **On the click response.** The page uses the JSON body of the POST directly for its first render.
    - **Polling.** While the state is `queued` or `running`, the panel polls the endpoint every 5 s (a named constant in the page code). It stops on `done` or `failed` (and when the user leaves the page). The label reads "Queued", "Running (attempt 2 of 3)", "Done" or "Failed".
    - **Failed.** The label is "Failed" followed by the stored `error` text (it is short and user-safe by construction, see Steps 6 and 10). The user can click **Download CSV** again.
    - **Expiry.** Files are deleted after 7 days. If `status='done'` and `finished_at` is older than 7 days, return `expired: true`. The page shows "Done (file expired, export again)" and hides the download button.
- **State:** none new. It reads `exports` (the repair check may update one row).
- **If it fails:** a failed poll keeps the last known state and retries on the next tick. The page table is unaffected, since this panel is separate from it.

## Step 12. Download from the page when the email link has lapsed

- **Starts when:** the user clicks **Download** on a `done` export in the export panel.
- **Data:** `GET /api/reports/{report_id}/export/{export_id}/download` (ids as described in "The export panel") checks `report.view` and that the export belongs to the user, requires `done` and not `expired`, then returns a redirect to a new `signed_url(..., 86_400)`.
- **State:** none.
- **If it fails:** 403 or 404 as appropriate. If the object is already gone, return `expired`.
- **Note:** this step goes slightly beyond the brief, which only specifies the emailed link. I included it because otherwise a "Done" export is useless after the email link lapses at 24 hours. It can be dropped without affecting the other steps.

## Step 13. Verification before release

Cover each behaviour with an automated test.

- **Size boundary.** 10,000 rows returns the CSV with no job and no row in `exports`. 10,001 rows (and a NULL or missing `row_count`) returns 202 JSON and runs a job.
- **Stale `row_count`.** A report whose `row_count` says 9,990 but which has 10,400 rows: the endpoint stops reading at 10,001 rows, returns 202 JSON, and runs a job. No partial CSV is returned.
- **Response types.** The page saves a `text/csv` response as a file, renders a JSON response (202 or 200 with `already_active`) as export state, and shows the right message for 400, 403, 500, 503 and a network failure. The status GET returns `null` for a user who never exported, and a failed export shows its `error` text.
- **Correct contents.** The CSV matches the page for the same filters and column order, including a header row and values containing commas, quotes and newlines.
- **Replica only.** The row queries run against the replica. A guard fails the test if report data is read from the primary.
- **Permissions.** A user without `report.view` gets 403 from the POST, the status GET and the download GET. A job for a user who has lost access ends `failed` with no link, no email and no retry.
- **One at a time.** Fire two simultaneous POSTs for the same user and report. Exactly one export exists, and both responses reference it. A click with different filters returns the active export with its own filters. After it is `done` or `failed`, a new click creates a new export.
- **Orphan repair.** A `queued` row with no `job_id` older than 2 minutes is re-enqueued by the next POST or by the next status GET, and two simultaneous checks enqueue only once.
- **No partial file.** Kill the worker mid-upload. Nothing is readable at the key, and the retry produces a complete file.
- **Retries.** Fail attempts 1 and 2 and succeed on 3: the file is complete and one email is sent. Fail all three: the row is `failed` and one failure email is sent.
- **Duplicate delivery.** Run the job twice for a finished export. No second file is built and no second email is sent. A `done` export with no `email_sent_at` only resends the email. **Run two copies of the same attempt at the same time:** exactly one builds the file and sends the email.
- **Memory.** Run a synthetic 2-million-row report on a 512 MB worker. Peak memory stays flat (target well under 150 MB) and does not grow with row count.
- **Duration.** The same run finishes comfortably inside the 1800 s timeout. Record the real time. If it is above about 1000 s, raise the page size or investigate the replica query before launch.

---

## Decisions to confirm

1. **Different view while an export is active.** "One at a time" is per user and report, not per filter set. A click with different filters returns the active export with its own filters shown, and the user must wait for it to finish before exporting the other view. The alternative is to key the rule on the view as well, which allows parallel exports of different views.
2. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run as formulas when the CSV is opened in a spreadsheet. The brief does not mention this. The plan exports values exactly as the page shows them, and escaping would be a small addition to the shared CSV writer.
3. **`row_count` source.** The plan reads `reports.row_count` (and the report's name and workspace) the same way the page does. Which database holds the `reports` table is not stated in the files I was given. If it is only on the primary, one small metadata read there is needed, and it is not report data.
4. **Step 12 and the "expired" label** are additions beyond the brief, as noted above.
5. **Shared query, formatting and permission code.** The plan assumes the rows API's parsing, query-building and value formatting can be called from a job with only stored filters and `cols`, with no session, and that the `report.view` check can be called with a plain user id and the report's workspace. I have not seen that code, so the real names, signatures and formatting rules are unknown. If any of it depends on the request, it must be split first.
6. **Email templates.** `export_ready` and `export_failed` must exist. How new templates are added to `send_email` is not known.
7. **Queue redelivery semantics.** Step 6's claim assumes that when a worker dies, the queue's next try carries a higher `ctx.attempt`, and that a duplicate delivery repeats the same number. `jobs.py` says "at least once" but does not spell out the attempt number on a duplicate. Confirm with the queue owners. The plan also assumes a handler that returns normally is treated as success (`jobs.py` says an attempt fails if the handler raises); confirm this too.
8. **Per-query timeout.** Whether the database client can set a per-query timeout (used for the 45 s stop in Step 3) is not known. Without it, the stop works only between pages.
9. **Nightly rebuild versus a running export.** How the nightly rebuild rewrites `report_rows` is not stated in the files I was given: in place or swapped, at what time, and whether `row_id` is stable across a rebuild. The plan does not make exports snapshots, so an export that overlaps a rebuild could be inconsistent, and a retry could produce a different file from the first attempt. Needs an answer from whoever owns the rebuild. If it cannot be made safe, the cheapest options are to have the job fail and retry when it detects a rebuild during the run, or to document the limitation.
10. **Alerting for "done but email never sent".** Step 10 only writes an error-level log line. Whether the platform turns that into an alert, and who sees it, is not known.
11. **A queued job that never runs.** If `enqueue` succeeded but the queue never starts the job, the row stays `queued` and nothing in this plan notices. The plan relies on the queue running every job it accepts; confirm that with the queue owners.
