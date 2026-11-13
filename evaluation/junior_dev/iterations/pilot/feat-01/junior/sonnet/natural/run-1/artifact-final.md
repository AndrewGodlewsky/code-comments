# Plan: CSV export for the reports page

## Terms and sources

"The request" means the feature request this plan answers. It fixes these rules, and this plan does not change them:

- The CSV holds the current view: filters and column order from the page URL, plus a header row.
- Export uses the same `report.view` permission check as the page.
- Report rows are read only from the read replica.
- The path is chosen by `reports.row_count`: 10,000 rows or fewer returns the CSV in the response, with no job and nothing stored. More than 10,000 returns at once and a background job builds the file.
- The job writes to the `exports` bucket and emails a link that works for 24 hours. Old files are deleted by the bucket's existing lifecycle rule, and no cleanup job is built.
- The page shows the state (queued, running, done or failed), including when the user returns later.
- A user can have only one large export of a given report queued or running.
- A worker has 512 MB of memory, the largest report is about 2 million rows, and the job must never hold a whole report in memory and must finish inside the attempt timeout.
- Failure uses the queue's normal retries. A half-written file is never downloadable. After the last failed attempt the user gets a failure email and the page shows `failed`.
- Out of scope: scheduled exports, other formats, changes to the table on the page.

Everything else below is a choice made in this plan: the `report_exports` table, the page size of 2,000, the 8 MB buffer, the 25-minute soft deadline, the 2-minute and 2-hour stale checks, 5-second polling, the key format, using `fetch` with a JSON body for the click, reading the status endpoint from the primary, the error body shape, the export JSON shape, the `expiry` format, and where `row_count` is read from. Each is explained where it appears.

**Clock.** Every timestamp in this plan (`created_at`, `updated_at`, the 2-minute and 2-hour checks, "now") comes from the primary database's clock (`now()` in SQL), never from an app server or worker clock, so the machines cannot disagree. The only exception is the email `expiry`, which is the sending process's UTC time plus 24 hours; a few seconds of drift there does not matter.

### Holes that cannot be settled from the files

Some facts about the existing system are not known to the author: how the caller is identified, the `report.view` signature and whether it works with only a `user_id`, the filter encoding and where its parser lives, whether the replica holds `reports`, the report name column, whether the email templates exist, what `send_email` does internally, what the queue guarantees if a job is lost or if `on_final_failure` fails, and whether a 2-million-row export is fast enough and small enough in memory. These are deliberate holes, not omissions. Each is listed in "Open questions for the reviewer" at the end and marked where it matters. The plan states what it assumes for each and what to do if the assumption is wrong.

## Existing building blocks

The plan relies on three existing descriptions, called here `reports_page.md` (the current page and rows API), `jobs.py` (the job queue) and `storage.py` (object storage). Those files are the source for everything in this table, except `send_email` and the permission check, whose code was not shown.

| Name | What it is | Status |
|---|---|---|
| `GET /api/reports/{id}/rows` | Rows API. Checks `report.view` on the report's workspace, reads `report_rows` from the replica, pages by `row_id` (`row_id > after ORDER BY row_id`). Requests over 60 s are killed. | Exists |
| `reports.row_count` | A column on the `reports` table: total unfiltered row count, rewritten by the nightly rebuild. Which database holds it is not stated (see Step 1). | Exists |
| `@job(name, on_final_failure)` | Decorator in `jobs.py` that registers a handler `handler(ctx, payload)`. | Exists |
| `ctx` (`JobContext`) | Passed to the handler: `ctx.job_id` and `ctx.attempt` (1, 2 or 3). | Exists |
| `enqueue(name, payload)` | `jobs.py`. Queues a job and returns its `job_id`. Payload is JSON, under 64 KB. | Exists |
| Queue rules | At most 3 attempts. Backoff 60 s then 300 s. An attempt is killed after 1800 s. No progress is kept between attempts. Delivery is at least once. An attempt fails only if the handler raises, times out, or its worker dies; a handler that returns normally is a successful attempt and is not retried. `on_final_failure(ctx, payload, error)` is called once after the last attempt fails. | Exists |
| `start_multipart`, `upload_part`, `complete_multipart`, `abort_multipart`, `signed_url` | `storage.py`. Nothing is visible at the key until `complete_multipart`. Each part except the last must be at least 5 MB, with at most 10,000 parts. `signed_url` allows at most 86,400 s. | Exist |
| `exports` bucket | Deletes objects 7 days after creation and discards multipart uploads not completed within 24 hours. | Exists |
| `send_email(user_id, template, params)` | Sends a templated email to a user. Named in the request. | Exists (code not shown) |
| `report_exports` table, `iter_report_rows`, the CSV writer, the two email templates, the export endpoints, the job handler | Described in this plan. | **To build** |

## How the pieces fit

A click on **Download CSV** sends the page's current view state to a new endpoint. The endpoint picks one of two paths by `reports.row_count`.

- **Small report (10,000 rows or fewer):** the response is the CSV, streamed from the read replica. Nothing is stored.
- **Large report (more than 10,000 rows):** a row in the new `report_exports` table records the request and a background job is queued. The job streams rows from the replica into a multipart upload in the `exports` bucket. When it finishes, it emails a 24-hour signed link. The page shows the export's state by reading `report_exports`.

The emailed link is the only way to get a large export's file. The page never offers a download for it (see Step 7).

**Error bodies.** Every non-2xx response from the export endpoints is JSON `{"error": "<short message>"}`. The page shows that message.

**Export JSON shape.** Wherever an export is returned as JSON (the POST in Step 3 with 200 or 202, and the GET in Step 7), the body is one object with exactly these fields: `{"export_id": "...", "state": "queued|running|done|failed", "filters": "...", "cols": "...", "created_at": "<ISO-8601 UTC>", "error_message": "..." or null}`. `filters` and `cols` are the text the export was started with. When the GET finds no export, it returns 200 with `{"export": null}`; otherwise it returns `{"export": {...the object above...}}`. The POST returns the bare object (not wrapped).

**Rule for every write to a `report_exports` row after it is created:** the `UPDATE` names the `export_id` it is about and states which current states it may change (`WHERE export_id=? AND state IN (...)`). If it changes zero rows, the row was moved by someone else (for example marked `failed`), and the writer must not overwrite that. This stops one export's code from touching a newer export of the same user and report.

## Step 0. Prerequisites (build once)

**Starts:** before any endpoint work.

**Data and state:**

1. **A new table `report_exports` on the primary database.** This is application state, not report data, so the primary is allowed. Columns:
   - `export_id` (uuid, primary key)
   - `user_id`
   - `report_id`
   - `filters` and `cols`: the text values exactly as the page sent them (text, not parsed). Their exact encoding is not shown in `reports_page.md` (see open questions), so store what arrives and let the shared parser read it.
   - `state` (`queued`, `running`, `done` or `failed`)
   - `job_id`
   - `object_key`
   - `error_message`
   - `emailed_at`
   - `created_at` and `updated_at` (`updated_at` is set on every state change)
2. **Two indexes on that table:**
   - A partial unique index on `(user_id, report_id) WHERE state IN ('queued','running')`. This is what enforces "one at a time". The database enforces it, so two simultaneous clicks cannot both win.
   - A plain index on `(user_id, report_id, created_at)`, for the status lookup in Step 7.
3. **A shared generator `iter_report_rows(report_id, filters, cols)`.**
   - It yields **one page at a time**: each item is a list of up to about 2,000 CSV-ready rows in the requested column order. The caller gets control back between pages, which is where the job runs its deadline and cancellation checks (Step 4, part 5).
   - It pages by `row_id` from the read replica. Turning filters into a query and running it on the replica happens here, using the rows API's existing filter parsing and column validation, so it also rejects invalid input.
   - Both the small path and the job use it, so the two paths cannot disagree about contents.
4. **A shared CSV writer.** It writes a header row, quotes fields correctly, and neutralises cells that start with `=`, `+`, `-` or `@` so spreadsheets do not run them as formulas. Use one writer everywhere.
5. **Two email templates for `send_email`:** `export_ready` (params: report name, link, expiry) and `export_failed` (params: report name). `expiry` is an ISO-8601 UTC timestamp string equal to the send time plus 24 hours. The plan fixes only the parameters; the subject and body wording belong to whoever owns email copy, and any wording is fine if it uses those parameters. Check whether these templates exist; this plan assumes they do not.
6. **Two lookups the job needs without a live request:**
   - the report's name, read from the `reports` table by `report_id` (the column is assumed to be `reports.name`; confirm);
   - a `report.view` check that takes a `user_id` and a report, not only the current HTTP caller. If the existing check only works inside a request, wrap its underlying logic in a function that takes a `user_id`.

**Failure:** none at runtime. These are build-time items.

## Step 1. The click: `POST /api/reports/{report_id}/export`

**Starts:** the user clicks Download CSV. The page calls the endpoint with `fetch` (not a form submit).

- **Request body:** JSON `{"filters": "...", "cols": "..."}`, where each value is the text the page already sends to the rows API for the current view. The server holds no view state, so the page must send it. The report id is in the URL path.
- **Who the caller is:** the `fetch` sends the same credentials the page uses for the rows API (the logged-in session), and the endpoint identifies the caller the same way the rows API does. `reports_page.md` does not describe that mechanism; this plan assumes it is the same and the endpoint reuses it (see open questions).

The page tells the two paths apart by the response's `Content-Type`:

- `text/csv` is the small-path file. The page reads the body into a blob and saves it as a download, using the filename from `Content-Disposition`. Only the small path sends `Content-Disposition`; the large path has no file in the response.
- `application/json` with status 200 or 202 is a large-path export status, in the Export JSON shape (Step 3). The page shows it in the status line as in Step 7.
- Any non-2xx response: the page shows the `error` message from the JSON body.

A `fetch` is used so the page can read either kind of response and show errors; a form submit would navigate away on a JSON reply.

**Data:** report id, filters and cols from the page, plus the caller's identity.

**Actions, in order:**

1. Check `report.view` by calling the same check the rows API calls. `reports_page.md` says the check is made "on the report's workspace", so the check must find the workspace from the report (presumably a workspace reference on the `reports` row) and test the caller against it. How the rows API does this lookup, and the check's exact signature, are not shown: reuse that code as it is, and do not write a second version (see open questions). Return 403 if the caller lacks it.
2. Validate filters and cols with the same parser as the rows API. Return 400 if they are invalid. This keeps a bad request from becoming a job that fails three times.
3. Read `reports.row_count`, from the read replica.
   - 10,000 or fewer: go to Step 2.
   - More than 10,000: go to Step 3.

**State kept:** none yet.

**Failure:** 403 or 400 as above. A database error returns 500 and the user can click again.

**Notes:**

- `row_count` is the unfiltered total and is refreshed nightly. A filtered view of a big report therefore still takes the large path, and a report that grew after the rebuild can be slightly over 10,000 rows on the small path. Both are acceptable, and the 60-second limit has plenty of margin at about 10,000 rows. This follows the request's rule.
- Why the replica: `row_count` is a count of report data, and the request says report data comes only from the replica. Reading it there is safe under either reading of that rule, and nightly staleness makes replica lag irrelevant. Open question: it is not known whether the replica holds the `reports` table. If it does not, read `row_count` from the primary, because it is a column on `reports`, not a report row.

## Step 2. Small path: stream the CSV in the response

**Starts:** Step 1, with `row_count <= 10,000`.

**Data moves:** replica rows to the CSV writer to the HTTP response, a page at a time.

**Actions:**

1. Respond 200 with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
2. Write the header row, then each page from `iter_report_rows`.
3. Nothing is stored and no job is queued.

**State kept:** none.

**Failure:**

- If the replica errors before the first byte is sent, return 500.
- If it errors mid-stream, abort the connection so the page's `fetch` fails and the page shows an error. Never end the response normally with partial data. The user clicks again. "Abort" means: do not write the final chunk that marks a streamed response as complete; instead let the exception escape the streaming code (or destroy the socket) so the web framework drops the connection. The exact call depends on the web framework, which this plan does not name; the check in Step 8, item 10 proves it works.
- The 60-second kill applies. About 10,000 rows is a few seconds, so it is not a concern.

## Step 3. Large path: create or return the export

**Starts:** Step 1, with `row_count > 10,000`.

**Data moves:** one new row in `report_exports`, then a job payload of `{"export_id": ...}`. The payload is tiny and well under 64 KB. Filters and cols live in the table row, not the payload.

**Actions:**

1. Try to insert a `report_exports` row with `state='queued'`, `user_id`, `report_id`, `filters`, `cols` and a generated `object_key`.
   - Use `exports/{report_id}/{export_id}.csv` for the key. The key is unique per export and fixed across retries.
2. If the unique index rejects the insert, an export for this user and report is already queued or running. Select that row.
   - If the row is dead (see "Dead-row rule" below), mark it `failed` (`UPDATE ... WHERE export_id=? AND state IN ('queued','running')`) and repeat the insert once.
   - Otherwise return it as JSON (Export JSON shape) with 200. No second job is started. The JSON carries the existing export's own filters, which may differ from the view the user clicked on (see Notes and Step 7).
3. Otherwise call `enqueue("report_export", {"export_id": ...})`, then save the returned `job_id` on the row.
4. Return 202 as JSON (Export JSON shape) with state `queued` and the filters it was started with. The response is immediate. The page uses this response to show the state at once (see Step 7).

**Dead-row rule.** An active row (`queued` or `running`) is treated as dead if either:

- (a) its `job_id` is empty and it was created more than 2 minutes ago. The API process probably died before or during `enqueue`. A row that the job set back to `queued` for a retry already has a `job_id`, so this never applies to it.
- (b) its `updated_at` is more than 2 hours ago. A healthy export never lasts that long: three 30-minute attempts plus 60 s and 300 s of backoff is about 96 minutes, and every state change sets `updated_at`. This is the safety net for a job that was lost, or whose final failure could not be recorded (see Step 6).

Both comparisons use the database clock (see "Clock" at the top).

**State kept:** the `report_exports` row on the primary. This row is the single source of truth for the page.

**Failure:**

- **`enqueue` raises.** Mark the row `failed` with a message and return 503, so the user is not locked out. The user can click again.
- **The API process dies between the insert and the enqueue.** The row stays `queued` with no job. After 2 minutes rule (a) lets the next click replace it.
- **The API process dies after `enqueue` but before `job_id` is saved.** The row looks the same as in the case above, so after 2 minutes it can be marked `failed` while a real job exists. Two things then can happen to that first job:
  - It has not started yet: it loads the row, sees `failed` and returns without doing anything (Step 4, part 1).
  - It is already running: it checks the row's state between pages (Step 4, part 5), sees `failed`, aborts its upload and stops. Until it notices (at most one page) it runs alongside the new export's job. They write to different keys because the key contains the `export_id`, so they cannot collide. If the first job somehow reaches the end anyway, Step 5 sees that its row is not `running`, so it sends no email.

  In both cases the user can click again and gets a new export.

**Notes:**

- If the user clicks again with different filters while an export of the same report is active, they get the existing export, with its original filters, and no new export starts. The request says one per user per report, so this is by design. The page compares the returned filters with its current view and, if they differ, says so (Step 7, part 2), so the user is not left thinking their current view is being exported.

## Step 4. The job: `report_export` (runs on a worker)

**Starts:** the queue calls `handler(ctx, {"export_id"})`, once per attempt. Attempt 1 runs at once, and attempts 2 and 3 run after 60 s and 300 s. The handler is registered with `@job("report_export", on_final_failure=...)`, which is Step 6.

**Data moves:** replica to a bounded in-memory buffer to object-storage parts. At most one buffer of about 8 MB plus one page of rows is in memory at a time. Never collect a whole report in a list.

**Actions:**

1. **Load the row** by `export_id`.
   - If `state='done'`, skip to the email step (Step 5, part b). This handles at-least-once delivery and a retry after a failure that came after the state was set to `done`.
   - If the row is `failed`, return without doing anything.
2. **Re-check `report.view`** for the row's `user_id` (there is no live request, so the check uses the stored user). If access was removed, raise an error. This is rare and costs only a quick failure. The filters and cols from the row are not re-validated by the handler itself; they were validated at click time, and `iter_report_rows` applies the same validation again and raises if they no longer fit.
3. **Mark the row `running`:** `UPDATE ... SET state='running', updated_at=now WHERE export_id=? AND state IN ('queued','running')`. If it changed zero rows, the row was marked `failed` since part 1 (Step 3 dead-row rule). Return without doing anything, and do not start an upload.
4. **Start the upload:** `upload_id = start_multipart("exports", object_key)`. Keep `upload_id` only in the handler's local variables. Each attempt starts a fresh one.
5. **Stream the file:**
   - Start the buffer with the header row.
   - Loop over the pages that `iter_report_rows` yields (it pages by `row_id` from the replica). For each page, append its rows to the buffer.
   - Whenever the buffer reaches 8 MB, call `upload_part(upload_id, n, bytes)`, keep the returned etag, increment `n`, and empty the buffer.
   - After each page (the generator hands control back to the loop here), run two checks:
     - Soft deadline: if 25 minutes have passed since the attempt started (measured on the worker with a monotonic timer, since this is a duration), call `abort_multipart` and raise an error. This stops the attempt cleanly before the queue's 30-minute kill.
     - Cancellation: reload the row's state. If it is `failed` (marked dead by a later click, Step 3), call `abort_multipart` and return without raising. This is one cheap primary query per page, about 1,000 for the largest report.
   - At the end, upload the remainder as the last part. The last part may be under 5 MB.
   - The largest report is about 900 MB, so that is about 113 parts, well under the 10,000-part limit. Each part except the last must be at least 5 MB (`MIN_PART_BYTES`), so the 8 MB threshold is safe.
6. **Finish:** `complete_multipart(upload_id, etags)`. Only now does the object appear at `object_key`. Then go to Step 5.

**State kept:**

- The row's state moves to `running`.
- The multipart parts live in storage and are invisible until completion.
- The `upload_id` and etags are in memory only.

**Failure:**

- **Returning without raising.** Several paths above return quietly (part 1 with a `failed` row, part 3 with zero rows changed, the cancellation check in part 5). The queue treats a handler that returns normally as a successful attempt: it does not retry and does not call `on_final_failure`. This is intended, because in each case the row is already `failed` and nobody should retry it. (This follows from `jobs.py`, which says an attempt fails only if the handler raises, hits the timeout, or its worker dies.)
- **Any exception** (replica error, storage error, soft deadline): call `abort_multipart(upload_id)` if one was started, then re-raise.
  - If `ctx.attempt < 3`, first try to set the row back to `queued` so the page shows that a retry is waiting: `UPDATE ... SET state='queued', updated_at=now WHERE export_id=? AND state='running'`. If it changes zero rows (the row is `failed`), leave it alone. If the database update itself fails (for example the database is down), log it and re-raise the original error anyway. The row then still says `running` during the backoff, which is accurate enough and still counts as active, and the next attempt sets it to `running` anyway. The queue retries after the backoff and starts again from the beginning, because it keeps no progress.
  - If `ctx.attempt == 3`, the handler does not change the row. It stays `running` for the moment between the last failure and the queue calling `on_final_failure`, and that function (Step 6) is the only place that sets `failed` after the job has started. The only other writers of `failed` are the `enqueue` failure and the dead-row rule in Step 3.
- **Worker killed or attempt timed out:** the handler cannot clean up, so the multipart upload is orphaned. The bucket discards it after 24 hours. The next attempt uses a new `upload_id`, so there is no conflict. The row stays `running` through the backoff wait, which is accurate enough for the page and still counts as active. The queue counts the dead attempt as failed, so after at most 3 attempts `on_final_failure` runs and the row should not stay `running` forever. (This assumes the queue always delivers or finally fails every enqueued job. That is not stated in `jobs.py`; see the open questions. The 2-hour dead-row rule in Step 3 is the backstop if it does not.)
- **Crash between `complete_multipart` and the `done` update (Step 5a):** the row is still `running`, so the retry does not take the shortcut in part 1. It rebuilds the whole file and overwrites the object at the same key. Slow but correct. There is no storage helper to ask whether the object already exists, so the plan does not try to skip the rebuild.
- **A half-written file is never downloadable.** The key holds nothing until `complete_multipart`, and that call is the last step of building the file.
- **Duplicate run of a finished job:** the check in part 1 returns early when the row is `done`. If two attempts overlap, both write the same key and the last `complete_multipart` wins. Both produce a complete file, never a partial one.
- **Timeout risk:** 2 million rows is about 1,000 page queries plus about 113 part uploads, run one after another. Before release, measure a 2-million-row export in staging. If it takes more than about 15 minutes, change the design before shipping. Retries cannot fix a job that is too slow, because every attempt does the same work. This is unmeasured today.

**Note:** the scan is not a snapshot. If the nightly rebuild rewrites rows while a job runs, the file can mix old and new data. This risk is accepted, as the rebuild runs overnight and exports are mostly daytime.

## Step 5. Finish: mark done, then email

**Starts:** `complete_multipart` returned in Step 4. This step also runs at the start of a retry when the row is already `done` (see Step 4, part 1).

**Data moves:** the state change in the database, then the link in an email.

**Actions:**

a. Update the row with `UPDATE ... SET state='done', updated_at=now WHERE export_id=? AND state='running'`. Then reload the row.
   - If its state is `done`, continue to part b. (This is also the case when another overlapping attempt got there first.)
   - If its state is anything else (in practice `failed`, set by the dead-row rule), stop here: send no email and return. The finished file is left for the lifecycle rule to delete. The page shows `failed` and the user can click again.

b. If `emailed_at` is empty:

   - `url = signed_url("exports", object_key, 86400)`. 86,400 s is the 24-hour maximum.
   - `send_email(user_id, "export_ready", {report name, url, expiry})`. The report name comes from the `reports` table (Step 0, item 6). `expiry` is send time plus 24 hours as an ISO-8601 UTC string.
   - Set `emailed_at`.
   - The link is generated at send time and never stored. It is valid for 24 hours from the email.

**State kept:** `state='done'` and `emailed_at` on the row. The file stays in the bucket for 7 days and the lifecycle rule deletes it. No cleanup job is built.

**Failure:**

- **`send_email` raises:** the attempt fails and is retried. The retry sees `done` with no `emailed_at` and only resends the email. It does not rebuild the file. (What `send_email` does internally and how it fails is not shown; the plan only relies on it raising on failure.)
- **Crash after sending but before `emailed_at` is set:** the user may get a second email. That is acceptable under at-least-once delivery.
- **If all three attempts fail at the email step,** the file exists but the user has no link. Step 6 handles this case.

## Step 6. Final failure: `on_final_failure(ctx, payload, error)`

**Starts:** the queue calls it once, after attempt 3 has failed. `payload` is `{"export_id": ...}`, and everything here is about that one export.

**Data moves:** the error text goes to the row and the failure email.

**Actions:**

1. Load the row by `payload.export_id`. If `state='done'`, the file was built but the email kept failing.
   - Leave the state as `done`.
   - Log the error for engineers.
   - Do not send a failure email, as the export itself succeeded. The user can click Download CSV again, which starts a new export (a `done` row is not active).
2. Otherwise run `UPDATE ... SET state='failed', error_message=?, updated_at=now WHERE export_id=? AND state IN ('queued','running')`, using the `export_id` from the payload. Without the `export_id` condition it could fail a newer export of the same user and report.
3. If that update changed a row, call `send_email(user_id, "export_failed", {report name})`. If it changed none, the row was already `failed` (for example by the dead-row rule) and nothing more is done.

**State kept:** `state='failed'` with the error message. A failed row leaves the partial unique index, so the user can start a new export.

**Failure:** if the failure email also fails, the row is still `failed`, so the page is correct, and the error is logged. There is no further retry here. If this function cannot write to the database at all, the row stays active until the 2-hour dead-row rule (Step 3) lets the user's next click replace it. Whether the queue retries a failing `on_final_failure` is not stated in `jobs.py`.

## Step 7. Status on the page

**Starts:** the report page loads, and the user clicks Download CSV on a large report.

**Where it shows:** a status line directly beside the Download CSV button. It shows the state word (`queued`, `running`, `done` or `failed`) with a short message: for `done`, "Check your email for the download link"; for `failed`, the `error_message`. It is empty when the user has no export for this report.

**Data moves:** `GET /api/reports/{report_id}/export` returns `{"export": {...}}` in the Export JSON shape for the caller's most recent export for that report, or `{"export": null}` if there is none. "Most recent" means the row with the latest `created_at` for that `user_id` and `report_id` (`ORDER BY created_at DESC LIMIT 1`, using the index from Step 0, item 2). This endpoint reads `report_exports` from the primary, not the replica: the table is application state, and the page reads it right after the POST, so replica lag could show a stale or missing export.

**Actions:**

1. On page load, call the GET endpoint. This also covers a user coming back to the report later. If an export exists, show its state in the status line.
2. After a click on a large report, the page does not wait for a GET. The 202 (or 200) JSON response from the POST already carries the export's id, state and filters, and the page shows that state immediately, then starts polling (part 3). The page also compares the returned `filters` and `cols` strings with the `filters` and `cols` strings it just sent, by exact string equality (the server stores them unparsed, so no normalising is needed). If either differs (the 200 case from Step 3), it shows the export's filters with a line such as "An export with different filters is already in progress. Started with: ...". It starts no new export; the user can click again once that export is `done` or `failed`.
3. While the state is `queued` or `running`, poll the GET endpoint every 5 seconds, and stop when it reaches `done` or `failed`. Also stop when the user leaves the page: the polling timer is cancelled when the report page is unloaded or the user navigates to another route (in a single-page app, in the page's teardown hook; otherwise on `pagehide`). Nothing is needed on the server, since an export continues without the page.
4. While an export is active, the button reuses the existing export (Step 3) instead of starting another.
5. Apply the `report.view` check to this endpoint too, and return only the caller's own exports.

**State kept:** none on the client. The `report_exports` row is the truth.

**Failure:** if a poll fails, keep the last known state and retry on the next tick.

**Notes:**

- The only way to get a large export's file is the emailed link. The page shows a state, not a download button, and the request asks for no more. If the email is lost or the link expires after 24 hours, the user clicks Download CSV again: a `done` export is not active, so this starts a new one and a new email. The row shows `done` even after the link expires or the file is deleted after 7 days. If users later need to re-download from the page, add an endpoint that checks `report.view` and returns a fresh `signed_url` while the object still exists. This is out of scope here.
- Only the latest export per user and report is shown.

## Step 8. Checks before release

1. **Contents match:** for the same view, the small-path CSV equals the large-path CSV. Cover column order, filters, the header row, and values containing commas, quotes and newlines.
2. **Dedupe:** two simultaneous clicks produce one row and one job.
3. **Retries:** force a failure on attempt 1 and confirm that:
   - the multipart upload is aborted;
   - the row goes back to `queued`;
   - attempt 2 succeeds;
   - one email is sent.
4. **Final failure:** force all three attempts to fail and confirm the page shows `failed`, the user gets one failure email, and no object exists at the key.
5. **Duplicate delivery:** run the handler twice for the same export and confirm there is one valid file. The second run sends no email, because `emailed_at` is already set.
6. **Worker death:** kill a worker mid-job and confirm the row ends as `done` or `failed`, never `running` forever.
7. **Row marked dead mid-job:** mark a running export `failed` by hand and confirm its job aborts the upload within one page, sends no `export_ready` email, and does not touch a new export started by the next click.
8. **Final failure of an old export:** with export A failing its last attempt while a newer export B of the same user and report is active, confirm A's `on_final_failure` leaves B unchanged and sends no email about B.
9. **Failed before start:** mark a queued export `failed`, then run its job, and confirm it returns at part 3 without overwriting the state or starting an upload.
10. **Click handling:** confirm the page saves a file for a small report, shows status for a large one, shows an error when the small-path stream is cut mid-way (this proves the abort in Step 2 works), and shows the "different filters" message when an active export has other filters than the current view.
11. **Memory:** run a 2-million-row export on a 512 MB worker and watch peak memory.
12. **Duration:** the same run must finish well inside the 1800 s limit. Aim for under 15 minutes (see the timeout note in Step 4).
13. **Replica only:** confirm no report row query reaches the primary. (`report_exports` reads and writes, including the Step 7 status lookup, are application state and do use the primary.)

## Open questions for the reviewer

- Are the `export_ready` and `export_failed` email templates available, or do they need to be created?
- Does the read replica carry the `reports` table, so `row_count` can be read there? If not, the primary is used for that one column.
- Can the existing `report.view` check be called with a `user_id` and no HTTP request? Which column holds the report's name?
- How does the existing `report.view` check find the report's workspace (a column on `reports`, or a lookup), and what does it take as input? The plan reuses the rows API's code and does not assume more.
- Does the queue guarantee that every enqueued job eventually runs and, if it keeps failing, reaches `on_final_failure`? Does it retry `on_final_failure` itself if that fails? The 2-hour dead-row rule limits the damage if either answer is no.
- What exactly is the encoding of `filters` and `cols` in the page URL and the rows API (`reports_page.md` shows both a `filters=...` parameter and separate `status=open&region=EU` style values), and where does the existing parser live? The plan stores the text as received and sends it in the POST body.
- How does the rows API identify the caller (session cookie, token)? The plan assumes the export endpoints reuse that exactly.
- Is a stale `row_count` (refreshed nightly) acceptable for choosing the path?
- Does the page need a download button for a finished export, given the link only lives 24 hours?
- Does a 2-million-row export finish well inside the 30-minute limit and within 512 MB? Unmeasured; Step 8 checks 11 and 12 measure it.
