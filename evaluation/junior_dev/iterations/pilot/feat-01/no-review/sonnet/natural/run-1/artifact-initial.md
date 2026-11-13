# Plan: CSV export for the reports page

## 0. Background and the new state

You need three facts about the current system.

- **Rows.** The page loads rows from `GET /api/reports/{report_id}/rows`. That endpoint checks `report.view` on the report's workspace (403 if missing) and reads the `report_rows` table on the **read replica only**. Report data is never read from the primary database.
- **Paging.** Rows are paged by keyset (`row_id > after ORDER BY row_id`), never by OFFSET. API requests are killed after 60 s.
- **View state.** Filters and column order exist only in the page URL. The server stores nothing about the current view.

The brief says the page and its API are "existing", but I have not seen their code. Where this plan says "reuse", it means to extract the filter and column parsing and the replica query from the rows endpoint into one shared function. Do not copy it, so the page and the export cannot drift apart.

**New state: one table, `report_exports`, in the primary database.** It holds export bookkeeping, not report data, so the replica rule does not apply. The primary is also where a unique constraint can be enforced.

| Column | Meaning |
|---|---|
| `id` | export id |
| `user_id`, `report_id` | owner and report |
| `filters`, `cols` | the normalised view captured at click time (the job needs them, because the URL is gone) |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | set after the job is enqueued; null until then |
| `object_key` | set once the file is completely written; null before |
| `error` | short user-safe reason, set only when `failed` |
| `created_at`, `updated_at`, `finished_at` | timestamps |

**Constraint: one active export per user per report.** Add a partial unique index:

`UNIQUE (user_id, report_id) WHERE status IN ('queued','running')`

The database enforces "one at a time", so two simultaneous clicks cannot both win. The rule is per user and report, whatever the filters are, because the brief says "of a given report".

**Object key.** `reports/{report_id}/{export_id}.csv` in the `exports` bucket. The key is deterministic per export, so a repeated run overwrites itself instead of leaving a second file.

---

## 1. User clicks **Download CSV**

- **Starts it:** the button on `/reports/{report_id}`.
- **Data moves:** the page sends `POST /api/reports/{report_id}/export` with the `filters` and `cols` taken from the current page URL. It uses `fetch`, not a form post, because the reply may be a file or a JSON status.
- **State:** none yet.
- **If it fails:** a network error or 5xx shows an inline error and the button re-enables. Nothing has been created, so a retry is safe.

## 2. API validates and authorises

- **Starts it:** step 1 arrives at the API.
- **Data moves:**
  1. Run the same `report.view` check on the report's workspace the rows API uses. Return 403 on failure, before doing anything else.
  2. Parse `filters` and `cols` with the shared parser. Return 400 if a filter or column is unknown.
  3. Read `reports.row_count` from the **replica**. This is a conservative assumption. If `reports` metadata is already read from the primary, say so in review.
- **State:** none.
- **If it fails:** 403 or 400 and nothing is created.

## 3. Choose the path by size

- **Rule:** `row_count <= 10,000` goes to step 4 (inline). `row_count > 10,000` goes to step 5 (background job). Exactly 10,000 is inline and 10,001 is a job.
- **Why the unfiltered count:** `row_count` is the unfiltered total, as the brief specifies. A tightly filtered view of a large report still takes the job path. This is accepted and costs only a short wait.

## 4. Small path: the response is the CSV

- **Starts it:** step 3 chose inline.
- **Data moves:**
  1. Fetch the first page from the replica with the shared keyset query, in the requested column order. Do this **before** sending headers, so a database error becomes a clean 500.
  2. Send `200`, `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment`.
  3. Write the header row, then the rows, streaming page by page (500 rows per page, about 20 pages at most). Do not build the whole file in memory.
  4. The page turns the response into a browser download.
- **State:** none. No `report_exports` row is created, no job runs, nothing is stored.
- **If it fails:**
  - Before the first byte: 500, and the page shows an error.
  - After streaming has begun: the status code can no longer change. Abort the connection so the download visibly fails, and the page shows an error. The user can click again.
  - At most 10,000 rows at 500 per page is far inside the 60 s request limit.

## 5. Large path: register the export

- **Starts it:** step 3 chose the job path.
- **Data moves:**
  1. `INSERT` into `report_exports` with `status='queued'`, the normalised `filters` and `cols`, and a null `job_id`.
  2. **If the insert hits the unique index**, an active export already exists. Select it and return it with `200`. Do not enqueue anything. The page then shows that export. This also happens if the existing one was started with different filters. The brief says clicking again "returns that export".
  3. Otherwise call `enqueue("report_export", {"export_id": id})`. The payload carries only the id (well under 64 KB). The job reads everything else from the row.
  4. Store the returned `job_id` on the row. Return `202` with `{export_id, status:"queued"}`. The click returns immediately.
- **State:** the `report_exports` row, in the primary database.
- **If it fails:**
  - If `enqueue` raises, set the row to `failed` (error "could not start") in the same request and return 500. This keeps a jobless row from blocking the user.
  - If the process dies between the insert and the enqueue, the row stays `queued` with a null `job_id`. On the next click, step 5.2 finds it. If it has a null `job_id` and is older than 60 s, re-enqueue it and store the new `job_id` instead of just returning it. The job is safe to run twice (step 6), so a double enqueue is harmless.

## 6. Job attempt starts

- **Starts it:** the queue calls the `report_export` handler `handler(ctx, payload)`. This happens up to 3 times in total, with waits of 60 s and then 300 s. The queue keeps no progress between attempts, so every attempt starts from the beginning. Delivery is at least once, so the handler can also run again after a success.
- **Data moves:**
  1. Load the row by `payload.export_id`.
  2. If `status` is `done` or `failed`, **return at once**. This is a duplicate delivery and nothing is sent twice.
  3. Re-check that the user still has `report.view`. If not, raise, so the normal failure path runs.
  4. Set `status='running'` and `updated_at=now`.
  5. If `object_key` is already set, the file was finished on an earlier attempt and only the email failed. **Skip to step 8** and do not rebuild.
- **State:** `report_exports.status`.
- **If it fails:** an exception is handled as in step 9.

## 7. Build and upload the file with bounded memory

- **Starts it:** step 6 found no finished file.
- **Data moves:**
  1. `upload_id = start_multipart("exports", key)`. Nothing is visible at `key` until step 8.
  2. Read rows from the **replica** with the shared keyset query, in the stored filters and column order. The job calls the query layer directly, not the HTTP API, so it can use a larger page of about 5,000 rows. This means about 400 queries for 2 million rows instead of 4,000.
  3. Encode CSV into a single in-memory buffer, with the header row first. Whenever the buffer reaches about 8 MB (above the 5 MB minimum part size), call `upload_part(upload_id, n, buffer)`, keep the returned etag, and **empty the buffer**. The final part may be smaller.
  4. Memory use is one page of rows plus one buffer of about 8 MB, plus a list of etags. The largest report (about 900 MB) is about 113 parts, far under `MAX_PARTS` (10,000). The whole report is never held in memory, so the 512 MB limit is not at risk.
  5. **Deadline guard.** Check elapsed time as pages are processed. If it passes about 25 minutes, `abort_multipart` and raise. This way the attempt fails cleanly before the queue's 30-minute kill (`ATTEMPT_TIMEOUT_SECONDS = 1800`).
  6. After the last row, `complete_multipart(upload_id, etags)`. Only now does the file appear at `key`.
- **State:** parts live in object storage under `upload_id`. They are not visible as a file. The `upload_id` is held in memory only.
- **If it fails:**
  - On any exception, call `abort_multipart(upload_id)` (ignore errors from that call) and re-raise.
  - If the worker dies or is killed, the abort cannot run. The orphan parts are discarded by the bucket's existing rule (multipart uploads not completed within 24 hours). Do not build a cleanup job.
  - In every case no half-written file is ever downloadable, because the object appears only when `complete_multipart` succeeds.
  - A rerun after a late failure overwrites the same key. `complete_multipart` replaces any existing object, so no duplicate files result.

## 8. Publish, email, mark done

- **Starts it:** step 7 completed, or step 6.5 found a finished file.
- **Data moves:**
  1. Set `object_key = key` on the row. This is the durable record that the file is complete.
  2. `url = signed_url("exports", key, 86400)`. This is the maximum, 24 hours, counted from the moment the email is sent.
  3. `send_email(user_id, "report_export_ready", {report name, url, ...})`.
  4. Set `status='done'` and `finished_at=now`. This frees the user to start another export.
- **State:** `object_key`, then `status='done'`.
- **If it fails:**
  - If the email raises, the attempt fails (step 9) and is retried. The retry reaches step 6.5 and goes straight to the email, with no 900 MB rebuild.
  - If the process dies after the email but before `done`, the retry sends a second email. This is rare and accepted, because the queue gives at-least-once delivery and `send_email` is not idempotent. The link in both emails is valid.
  - The file itself is deleted by the bucket 7 days after creation. The emailed link expires after 24 hours.

## 9. An attempt fails but retries remain

- **Starts it:** the handler raises, the 30-minute timeout hits, or the worker dies.
- **Data moves:** if the handler is still alive (it raised), set `status='queued'` for the wait before the next attempt (60 s, then 300 s) and re-raise. The queue retries it.
- **State:** `report_exports.status`.
- **If it fails:** if the worker was killed, nobody can reset the status, so the row shows `running` during the wait. This is slightly inaccurate but harmless. Both `queued` and `running` count as active for the one-at-a-time rule, so the user cannot start a duplicate meanwhile.

## 10. Final failure (attempt 3 fails)

- **Starts it:** the queue calls `on_final_failure(ctx, payload, error)`, once.
- **Data moves:**
  1. Set `status='failed'`, `error` to a short user-safe message (not the raw exception), and `finished_at=now`. Do this **first**, so the page is correct and the user can retry even if the email step breaks.
  2. `send_email(user_id, "report_export_failed", {report name})`. Wrap it in try/except and log on failure. Never raise out of this callback.
  3. If a file had somehow been finished earlier (`object_key` set, but the email kept failing), it is not used. The export is still reported as failed.
- **State:** `status='failed'` and `error` on the row.
- **If it fails:**
  - The failure email is best effort. The page still shows `failed`.
  - If the callback is invoked twice, step 1 is idempotent, and email only if the status was not already `failed`.

## 11. Page shows the export's state

- **Starts it:** two triggers.
  1. The page load of `/reports/{report_id}`.
  2. A 202 or 200 reply to step 5.
- **Data moves:**
  1. The page calls a new `GET /api/reports/{report_id}/exports/latest`.
  2. The API makes the same `report.view` check, then returns the **current user's** most recent export of that report from `report_exports` on the primary, as `{export_id, status, finished_at, error}`. It returns nothing if there has never been one.
  3. While the state is `queued` or `running`, the page polls every 5 s and stops on `done` or `failed`. No other server state is needed for this.
  4. The page shows queued, running, done or failed. This covers both the user still waiting and the user coming back later.
- **State:** read-only here. The truth is the `report_exports` row.
- **If it fails:** a failed poll leaves the last-known state on screen and retries on the next tick. If the status call keeps failing, show "status unavailable". It never affects the job.

---

## Checks before shipping

- **Throughput.** Run the job against the 2-million-row report on the replica in staging and confirm it finishes in about 25 minutes or less, with a safe margin. If it does not, raise the page size or the part size before anything else. If it still cannot fit, the timeout makes every attempt fail and the user gets the failure email after about 65 minutes in total.
- **Memory.** Confirm worker memory stays well under 512 MB during that run.
- **Boundaries.** Test `row_count` = 10,000 vs 10,001; two simultaneous clicks; a double-click after the export is done; an `enqueue` failure; a kill mid-upload (the file must not be downloadable); a final failure (the page shows failed, the email is sent).

## Decisions to confirm (assumptions, not in the brief)

1. **Expired link.** The page shows `done` after the emailed link has expired at 24 hours (the file lives until day 7). Do we want a "Download again" button on the page that mints a fresh signed link? I left it out.
2. **Spreadsheet formula cells.** Cells starting with `=`, `+`, `-` or `@` can run as formulas when the CSV is opened in a spreadsheet. We should decide whether to neutralise them with a leading `'`. That changes the data, so it is your call.
3. **Data changing mid-export.** The nightly rebuild could change the report while a long export runs. This plan reads without a snapshot, so a row may be missing or duplicated across that moment. Say if you need a consistent snapshot.
