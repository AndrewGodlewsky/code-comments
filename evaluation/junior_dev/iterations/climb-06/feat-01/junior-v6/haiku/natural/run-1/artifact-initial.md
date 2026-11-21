# CSV export for the reports page: implementation plan

## Context and fixed decisions

Users want a **Download CSV** button on the reports page (`/reports/{report_id}`). The page shows one report as an infinite-scroll table. Its rows come from `GET /api/reports/{report_id}/rows`, which checks `report.view`, reads the `report_rows` table on the **read replica**, and pages by `row_id` with keyset pagination. The page's filters and column order live only in the URL, and the server stores no view state.

The export must match what the user sees when they click. Two paths are chosen by size:

- **Small (`reports.row_count` <= 10,000):** the click's HTTP response is the CSV. Nothing is queued or stored.
- **Large (`reports.row_count` > 10,000):** the click returns at once, and a background job writes the file to the `exports` bucket and emails a 24-hour download link.

Terms used below:

- **Queue job / attempt:** the background queue (`jobs.py`) runs a handler. An attempt that raises, times out at 1,800 s, or loses its worker is retried after 60 s, then 300 s, up to 3 attempts in total. Each attempt starts the handler from the beginning with the same payload. Delivery is at least once, so a handler can run again after it has succeeded.
- **Multipart upload:** the object store only shows an object at its key after `complete_multipart`. Parts other than the last must be at least 5 MB. Incomplete uploads are discarded after 24 hours.
- **Export row:** a new row in a small metadata table on the primary database (described in the next section). It is not report data, so the rule that report data is read only from the replica does not apply to it. All report rows still come from the replica.
- **Lifecycle rule:** the bucket deletes each object 7 days after it is created. We do not write any cleanup code.

## Data kept for an export

One table, `export_jobs`, on the primary database. Each export has one row:

| Field | Purpose |
|---|---|
| `export_id` (UUID, primary key) | Names the export and its object key |
| `user_id`, `report_id` | Owner and report |
| `filters`, `cols` | The normalised URL strings, parsed by the same code the rows API uses |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | Queue job that currently owns the export |
| `attempt` | Last attempt number seen |
| `upload_id`, `upload_started_at` | The open multipart upload |
| `next_row_id` | Checkpoint: last `row_id` already written to a committed part |
| `finished` | True once every row is in a committed part |
| `storage_key`, `object_created_at` | Set when the upload completes |
| `email_sent_at` | Set after the ready email is sent |
| `error` | Short message for a failed export |
| `created_at`, `updated_at` | `updated_at` moves on every state change and checkpoint |

A second table, `export_parts` (`export_id`, `part_number`, `etag`, `last_row_id`), holds one row per committed part, about 60 rows for the largest report.

A **partial unique index** on `(user_id, report_id)` where `status` is `queued` or `running` enforces the one-at-a-time rule even when two clicks race.

Object key: `reports/{report_id}/exports/{export_id}.csv`. The key is unique per export, so no export ever overwrites another.

---

## Step 0. Measure before building the job (gate)

- **Starts:** a decision before coding. Owner: whoever builds the job.
- **Data moves:** a copy or staging replica of the 2-million-row report. The measurement reads it in keyset pages of 5,000 rows, formats CSV, and uploads 16 MB parts to a test bucket.
- **State:** none. Record rows per second, the time for one part, and the replica query time per page.
- **What the numbers decide:** the time budget per attempt in Step 8. The total run takes about 900 MB divided by the measured bytes per second. If the total exceeds about 4 hours, stop and reconsider the design (for example, splitting the report into row ranges handled by parallel jobs) before building.
- **On failure:** if the replica cannot be reached from a worker, that is a blocker. Do not build the job against the primary as a workaround.

## Step 1. The click checks permission and parameters

- **Starts:** the user clicks **Download CSV**. The page calls `GET /api/reports/{report_id}/export?filters=...&cols=...`, using the same values as the page URL.
- **Data moves:** only the URL parameters.
- **State:** none.
- **On failure:**
  - No `report.view` on the report's workspace: 403, the same answer the page gets.
  - Unknown report: 404.
  - Invalid `filters` or `cols`: 400, from the same validator the rows API uses. The parameters are never parsed a second way.

## Step 2. Decide the path by size

- **Starts:** Step 1 passes.
- **Data moves:** reads `reports.row_count` from the read replica. This is report metadata, so it follows the replica rule.
- **State:** none.
- **Branches:** a count of 10,000 or less goes to Step 3. A count above 10,000 goes to Step 4.
- **On failure:** the replica is unreachable. Return 503 with a retry message. Do not fall back to the primary.
- **Note:** `row_count` is the unfiltered total, so a small filtered view of a large report takes the large path. This is correct, but slower. See the open questions.

## Step 3. Small path: build the CSV inside the request

- **Starts:** Step 2 chooses the small path.
- **Data moves:** reads `report_rows` from the replica in keyset pages of 500 rows (`row_id > after ORDER BY row_id`), with the URL filters applied. Writes a header row, then one CSV line per row, using the columns in URL order. The whole body is held in API-server memory. At 10,000 rows this is a few megabytes.
- **Cap:** if more than 10,000 rows come back (the replica's `row_count` was stale), drop the buffer and go to Step 4 as if the count had been large. The user gets the same 202 response either way.
- **State:** nothing is stored. The request writes no export row and enqueues no job.
- **Response:** `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="report-{report_id}.csv"`. The body is sent only after it is complete, so the browser never saves a partial file.
- **On failure:** a database error or the 60-second API limit before the body is complete returns an error with no body. The user clicks again. Buffering is chosen on purpose: a stream that fails halfway would leave a truncated file that looks complete.

## Step 4. Large path: create or return the export

- **Starts:** Step 2 chooses the large path, or Step 3 hit its cap.
- **Data moves:** inserts one `export_jobs` row on the primary with `status = queued` and the normalised `filters` and `cols`.
- **State:** the row is written to the primary in one statement. A conflict on the partial unique index means an active export already exists for this user and report.
  - **Dedupe:** return that existing export with `202` and its `export_id`, `status`, and `filters`. The spec says a second click returns the existing export instead of starting another. The response includes the filters so the page can show which view that export covers.
  - **Stale guard:** if the conflicting row's `updated_at` is more than 6 hours old, treat it as dead. Abort its `upload_id` if one is set, mark it `failed` with "stalled", and insert the new row.
- **Response:** `202 Accepted` with `{export_id, status, filters}`. The page starts polling (Step 11).
- **On failure:**
  - Insert fails: 500. No row, no job.
  - Insert succeeds but Step 5 fails: mark the row `failed` with "could not queue" and return 503. The user can click again.

## Step 5. Queue the job

- **Starts:** Step 4 inserted a new row.
- **Data moves:** `enqueue("csv_export", {"export_id": ...})`. The payload is a UUID, far under the 64 KB limit. The job reads filters and columns from the row, not from the payload, so the payload cannot drift from the row.
- **State:** the returned `job_id` is saved on the row. Until it is saved, the stale guard is the backstop.
- **On failure:** enqueue raises. Handled in Step 4.

## Step 6. Each attempt starts: load, check, resume or start

- **Starts:** the queue calls the handler with `ctx.attempt` (1, 2 or 3) and `{export_id}`.
- **Data moves:** reads the export row from the primary. Permission is checked again for `row.user_id`, because the user may have lost access while the job waited in the queue.
- **State changes, in order:**
  1. The row is missing: return. Nothing to do.
  2. `status = done` and `email_sent_at` is null: skip to Step 10.
  3. `status = done` and `email_sent_at` is set: return. This is a duplicate delivery.
  4. `status = failed`: return.
  5. `report.view` lost, or the report was deleted: set `failed` with "no access" (or "report not found"), send the failure email from Step 12, and **return normally**. Returning rather than raising stops the queue from retrying a failure that will not change.
  6. Otherwise set `status = running`, `attempt = ctx.attempt`, `job_id = ctx.job_id`, and `updated_at = now`.
  7. If `upload_id` is set and `upload_started_at` is less than 20 hours ago, resume it. Continue from `next_row_id`, or from the start if `next_row_id` is null.
  8. If `upload_id` is missing or too old: abort any old upload, call `start_multipart(exports, storage_key)`, and save the new `upload_id` and `upload_started_at` on the row. Start from the beginning.
- **On failure:** a database error or a permission-lookup error raises. The queue retries after 60 seconds. Nothing has been uploaded yet, so the retry starts from the checkpoint.

## Step 7. Stream rows into committed parts

- **Starts:** Step 6 has set up the upload.
- **Data moves:** for each page of 5,000 rows from the replica (`row_id > checkpoint ORDER BY row_id LIMIT 5000`, with the filters and columns from the row), format the lines and append them to a byte buffer. When the buffer reaches **16 MB** after a complete row, upload it with `upload_part(upload_id, part_number, data)` and get an etag. Then, in **one primary transaction**, insert the `export_parts` row and set `next_row_id` to the buffer's last `row_id`, `updated_at` to now, and only if `status = running`.
- **Header:** the header row is the first line of part 1.
- **Memory:** at most one page of 5,000 rows and one 16 MB buffer are held at a time, far under the 512 MB limit. The whole report is never in memory, and the file is never written to local disk.
- **Part boundaries:** a flush happens only after a full row, at a fixed byte threshold. Given the same checkpoint and the same data, the same rows and boundaries come out again. That is what makes a retry safe.
- **Part numbers:** count from 1, so 2 million rows at about 450 bytes each is about 57 parts, far under the 10,000 limit. Every part except the last is at least 5 MB, since parts are 16 MB.
- **On failure:**
  - Crash before `upload_part`: the buffer is lost. The retry resumes from `next_row_id`.
  - Crash after `upload_part` but before the transaction: an uncommitted part exists. The retry regenerates the same rows and re-uploads the same `part_number`, which replaces the part. Nothing is lost.
  - Replica query error: retry the page query up to 3 times within the attempt, then let the attempt fail.
  - Storage error on `upload_part`: the attempt fails and the queue retries from the checkpoint.

## Step 8. Time budget: continue in a new job when the attempt runs long

- **Starts:** at each part boundary, after the checkpoint transaction in Step 7, the handler checks the attempt's elapsed time.
- **Rule:** an attempt starts no new part after **20 minutes** (the budget is tuned by Step 0). That leaves about 10 minutes of margin under the 1,800-second kill. A part takes seconds to minutes, so the margin is ample. The check happens only at part boundaries, so an interim part is never short. A short part would break the 5 MB minimum.
- **Data moves:** none beyond Step 7.
- **State:** the checkpoint is committed. The row stays `running`.
- **Action:** if rows remain, call `enqueue("csv_export", {"export_id": ...})` as the handler's last action, then return normally. The new job starts with fresh attempts and resumes from the checkpoint. This is why a 2-million-row export can finish even though no single attempt is guaranteed to do all of it.
- **On failure:**
  - Enqueue raises: the attempt fails and the retry resumes from the same checkpoint. Work is not lost.
  - A duplicate continuation may run if the queue delivers twice. Both runs regenerate identical parts, so the result is the same. The extra work is wasted but harmless. The status check in Step 6 and the conditional writes in Steps 7 and 9 stop a superseded run from changing a finished export.

## Step 9. Finish: complete the upload

- **Starts:** the query returns no rows after the last checkpoint.
- **Data moves:** flush the final buffer as the last part. It may be under 5 MB, which is allowed for the last part. Commit its `export_parts` row with `finished = true` in the same transaction. Then call `complete_multipart(upload_id, etags)`, with etags in `part_number` order from `export_parts`. Completing makes the object visible at `storage_key` in one step, replacing nothing, since the key is unique.
- **Then:** conditionally set `status = done`, `storage_key`, `object_created_at = now`, and `updated_at`, only if `status = running`.
- **State:** `done` is written only after the object is complete, so a half-written file can never be linked or downloaded.
- **On failure:**
  - Complete raises: the attempt fails. On retry, `finished` is already true, so Step 6 goes straight to completing the upload again. No rows are reread.
  - The upload is gone (older than 24 hours, so the bucket discarded it): the retry sees the error and restarts from scratch in Step 6, branch 8.

## Step 10. Email the ready link

- **Starts:** `status = done` and `email_sent_at` is null. This happens right after Step 9, or on a retry (Step 6, branch 2).
- **Data moves:** call `signed_url(exports, storage_key, ttl = min(86400, object_created_at + 7 days - now))`, then `send_email(user_id, "export_ready", {report_id, report_name, download_url, expires_at})`. The link lasts up to 24 hours and never outlives the object.
- **State:** on success, set `email_sent_at = now`.
- **On failure:** `send_email` raises. The attempt fails without redoing the export, because the file is already done. The retry runs Step 6 branch 2 and sends the email again. If all 3 attempts fail, `on_final_failure` (Step 12) leaves `status` as `done`. The page still offers the download (Step 11), so the file is not lost.

## Step 11. The page shows state and offers the link

- **Starts:** the report page loads. While an export is `queued` or `running`, the page polls every 5 seconds. It stops on `done` or `failed`.
- **Endpoint:** `GET /api/reports/{report_id}/exports/latest` returns the caller's most recent export for this report. Its fields are `status`, `filters`, `created_at`, `attempt` (while running), `error` (if failed), and, if `done` and the object still exists, a **fresh** `download_url`.
- **Link minting:** every page load mints a new signed URL with `ttl = min(86400, object_created_at + 7 days - now)`. Once that is zero or less, the URL is no longer offered. The page then says "This export has expired. Export again."
- **Permission:** the endpoint checks `report.view` and returns only rows where `user_id` matches the caller.
- **Click while active:** the button calls Step 4, which returns the active export. It does not start another.
- **State:** a read of the primary, since this is export state and not report data.
- **On failure:** if the endpoint errors, the page shows "Export status unavailable" and keeps polling. A failed poll never changes the export.

## Step 12. Failure handling and final failure

- **Ordinary attempt failure** (raise, timeout, or worker death): the queue waits 60 seconds, then 300 seconds, and retries. Status stays `running` while the job waits. The page shows the attempt number. The checkpoint is kept, so no finished work is repeated.
- **Final failure:** after the 3rd attempt fails, the queue calls `on_final_failure(ctx, payload, error)`. The handler:
  1. Reloads the row. If `status = done`, make no change. The file is complete, and only the email failed.
  2. Otherwise sets `status = failed`, `error` = a short summary (no stack trace), and `updated_at`.
  3. Calls `abort_multipart(upload_id)` if `upload_id` is set, so the parts are dropped now and not after 24 hours.
  4. Calls `send_email(user_id, "export_failed", {report_id, report_name, retry_hint})`. If this send fails, log it. The page still shows `failed`.
- **Handler itself fails** (for example, the database is down during `on_final_failure`): the row stays `running`. The stale guard in Step 4 clears it after 6 hours of no updates, and the user can click again then.
- **Permission lost or bad input:** handled in Step 6 branch 5 without retrying. The handler sets `failed`, sends the failure email, and returns normally.

## Step 13. Expiry and cleanup

- **Starts:** time passing.
- **Files:** the bucket's lifecycle rule deletes each object 7 days after `object_created_at`. The page treats an export as expired from that point. Emailed links last 24 hours, and page links are capped at the time left on the object, so a link never works after the object is gone.
- **Uploads:** multipart uploads that are never completed are discarded after 24 hours by the bucket. Step 12 aborts them sooner when a failure is final.
- **Rows:** `export_jobs` and `export_parts` rows stay. No cleanup job is built, as specified. They are small, a few hundred bytes per export plus about 60 part rows for the largest report.

---

## Open questions for the owner

1. **Dedupe ignores filters.** The spec says one active export per user per report. A user who changes a filter and clicks again gets the existing export with the old filters. Step 4 returns the filters so the page can say so. Confirm this is acceptable, or change the key to include filters.
2. **Nightly rebuild during a long export.** `reports.row_count` is rewritten when the data is rebuilt each night. A multi-hour export that spans a rebuild could mix two versions of the report. Is there a report generation or rebuild timestamp? If yes, store it on the row at the start of the export and restart from scratch in Step 6 if it changes. If not, consider holding large exports during the rebuild window.
3. **Access after the link is sent.** The emailed link is a bearer link for 24 hours. If `report.view` is revoked after the email, the link still works until it expires. Is that acceptable?
4. **Filtered size decision.** Choosing the path by unfiltered `row_count` (as specified) sends small filtered views of large reports to the job. Would counting filtered rows, at extra cost, be worth it?
5. **CSV details.** The spec does not say whether to write a UTF-8 byte-order mark (helps Excel show non-ASCII characters) or how to neutralise cells beginning with `=`, `+`, `-` or `@` (spreadsheet formula injection). Both need a decision before Step 7 is coded.
6. **Stale threshold.** The 6-hour stale guard in Step 4 assumes queue delay plus retries stays well under 6 hours. Confirm this against the queue's real backlog.
7. **New email templates.** `export_ready` and `export_failed` must exist before the feature ships. Their parameters are listed in Steps 10 and 12.

## Test plan (summary)

- **Unit:** the keyset page query; part boundaries are deterministic for a fixed checkpoint; the state branches in Step 6; the single-active rule under two simultaneous clicks.
- **Integration with a fake object store:** resume after a crash at each point in Step 7 (before upload, after upload, after checkpoint) produces a byte-identical file; an interim part is never under 5 MB; a timed-out attempt resumes; a final failure aborts the upload and sends one failure email.
- **Scale:** the Step 0 report, run end to end, with peak memory under 512 MB and every attempt under 1,800 seconds.
- **Permission:** a user who loses `report.view` between click and run gets a failed export and no file.