# CSV export for the reports page: implementation plan

## What this is

The reports page gets a **Download CSV** button. It exports the rows the user sees: the filters and column order from the page URL, plus a header row. Today the page loads rows through a paged API and the server stores nothing about the view. The export adds one table, one background job and two endpoints. The table on the page does not change.

Small exports (10,000 rows or fewer) download straight from the click. Large exports run as a background job. The job writes the file to the `exports` bucket and emails a 24-hour download link. The page shows the export's state while it runs.

## Terms

- **Replica:** a read-only copy of the database. All report rows are read from it. Writes go to the primary.
- **Export:** one CSV of one report, with one set of filters and columns. It is one row in `report_exports`.
- **Attempt:** one run of the export job. The queue allows up to 3 attempts.
- **Queue retry:** the queue runs the job again after a failed attempt. It waits 60 seconds before attempt 2 and 300 seconds before attempt 3. An attempt fails if it raises an error, runs past 30 minutes (the queue kills it), or its worker dies.
- **Lease:** an attempt's claim on an export. Each attempt writes a new random `lease_token` when it starts. Only the attempt holding the current token may write progress.
- **Heartbeat:** `heartbeat_at`, the last time the running attempt wrote to show it is alive.
- **Checkpoint:** saved progress (`upload_id`, `parts`, `last_row_id`). A later attempt resumes from it.
- **Multipart upload:** storage receives a file in parts. Nothing is visible at the final key until the upload is completed.
- **Stale:** a `running` export whose heartbeat is more than 5 minutes old. The server computes this.

## Steps

Each step says what starts it, what it does, which data it keeps, and what happens when it goes wrong.

### Step 1: The user clicks Download CSV

- **Starts:** the user clicks the button. The browser sends `POST /api/reports/{report_id}/exports` with the `filters` and `cols` from the page URL.
- **Does:** checks `report.view` on the report's workspace. Validates `filters` and `cols` the same way the page does. Reads `reports.row_count` from the replica. If `row_count` is 10,000 or less, go to Step 2. Otherwise go to Step 3.
- **Keeps:** nothing.
- **When it fails:** no permission gives 403. Bad `cols` or `filters` gives 400. An unknown report gives 404. A failed `row_count` read gives 503. The server does not guess a path.

The page tells the responses apart by status and `Content-Type`. A `200` with `text/csv` saves the file. A `202` with JSON (`export_id`, `state`, `filters`, `cols`) shows the status panel (Step 9). Any error with JSON `{"error": ...}` shows the message.

### Step 2: Small export (10,000 rows or fewer)

- **Starts:** Step 1 found `row_count` at 10,000 or less.
- **Does:** reads the replica in pages of 1,000 rows, keyed by `row_id`. Formats the rows with the shared CSV writer and builds the whole file in memory. Returns `200` with `Content-Disposition: attachment; filename="<report>.csv"`. The file is built before any byte is sent. Once headers are sent, an error cannot reach the user, and a cut-off file looks complete. At the limit, the file is about 4.5 MB.
- **Keeps:** nothing. Nothing is written to the database or to storage.
- **When it fails:** a replica error or the 60-second API limit gives 503. The page shows "Export failed, try again." A retry is safe because nothing was stored. A stale `row_count` may let a few more rows through. This is accepted.

### Step 3: Large export (more than 10,000 rows)

- **Starts:** Step 1 found `row_count` above 10,000.
- a. **Create the row.** Insert into `report_exports` with `state = 'queued'`, the user, the report, `filters` and `cols`. If the partial unique index rejects the insert, an active export already exists for this user and report. Return that export as in sub-step d. Any other insert error gives 500. No job was queued, so nothing needs cleaning up.
- b. **Queue the job.** Call `enqueue("report_export", {"export_id": ...})`. The payload holds only the ID, because the filters and columns are in the row. Store the returned `job_id` on the row. If that update fails, log it and continue, because the job finds the row by its ID. If `enqueue` raises, set the row to `failed` with `error = "could not queue"` and return 503. Never leave a `queued` row with no job.
- c. **Return 202** with `export_id`, `state: "queued"`, `filters` and `cols`.
- d. **Duplicate click.** Return 202 with the active export's ID, state, `filters` and `cols`, so the page shows what that export covers.
- **Keeps:** one `report_exports` row in state `queued`. Rows are never deleted. The brief rules out a cleanup job, and the rows are small.
- **When it fails:** see sub-steps a and b.

### Step 4: A job attempt starts

- **Starts:** the queue runs the `report_export` job for an export ID. The job gets the attempt number (1, 2 or 3).
- a. **Load the row.** If the row is missing, return normally. If it is `failed`, or `done` with `emailed_at` set, return normally. If it is `done` with `emailed_at` empty, the file exists but the email was not sent. Go to Step 7. No lease is needed. Otherwise continue.
- b. **Take the lease.** Run one conditional update. It applies only if the row is `queued`, or `running` and stale. It sets `state = 'running'`, the attempt number, a new random `lease_token`, and `started_at` and `heartbeat_at` to now. It keeps the checkpoint. If no row changed, a live attempt holds the lease. Raise so the queue retries later, and change nothing.
- c. **Re-check access.** If the user no longer has `report.view`, set `failed` with `error = "no access"`, send the `export_failed` email (Step 8), and return normally. A retry cannot fix this.
- **Keeps:** the lease token, `state = running`, the attempt number and `heartbeat_at`.
- **When it fails:** once the lease is taken, if the attempt raises, it first sets `state = 'queued'` and `error = "attempt N failed, retrying: <short text>"`, using its own lease token. Then it re-raises. This lets the page show that a retry is pending. If that update fails, raise anyway.

### Step 5: Write the file in parts

- **Starts:** Step 4 took the lease.
- a. **Start or resume the upload.** If `upload_id` is empty, start a multipart upload at the key `<export_id>.csv` in the `exports` bucket. Save `upload_id` on the row before writing any data. Every retry uses the same key.
- b. **Read a page.** Query the replica for rows with `row_id > last_row_id`, ordered by `row_id`, 5,000 at a time. With no checkpoint yet, start at the first row. The job calls the query function directly, not the HTTP API, which caps pages at 500 rows. Then write the heartbeat, checking the lease token.
- c. **Format into a buffer.** Write the rows as CSV into an in-memory buffer. Write the header row only when `parts` is empty, so part 1 always starts with the header.
- d. **Upload a part at 8 MiB.** Cut only at row boundaries, so the buffer holds whole rows. Upload the buffer as part number `len(parts) + 1`. Then, in one update that checks the lease token, append `{part_number, etag}` to `parts`, set `last_row_id` to the last row in the part, and set `heartbeat_at` to now. Clear the buffer.
- e. **Repeat** sub-steps b to d until a page returns no rows. Upload the remaining buffer as the last part. It may be under 5 MB, which is allowed. Skip it if empty.
- **Keeps:** `upload_id`, `parts`, `last_row_id` and `heartbeat_at`. These are updated after every page and every part. Nothing is visible at the final key yet.
- **Size:** the largest report has about 2 million rows, about 900 MB of CSV. That is about 115 parts, far under the 10,000 limit. A worker holds one 8 MiB buffer and one 5,000-row page, about 2 MB. It never holds the whole report.
- **When it fails:**
  - A replica read fails: raise. The next attempt resumes from `last_row_id`.
  - A part upload fails: raise. The part was not recorded, so the next attempt re-reads from `last_row_id` and uploads it again. No rows are lost, and nothing becomes visible.
  - The attempt runs past 30 minutes, or its worker dies: the code stops and runs no more. The row stays `running` with an old heartbeat, so it becomes stale. The queue retries from the checkpoint.
  - The lease is lost (a checkpoint or heartbeat update changes no rows): raise. Another attempt owns the export now.

### Step 6: Finish the file

- **Starts:** the last part is uploaded.
- a. **Complete the upload.** Call `complete_multipart(upload_id, etags)`. The object appears at `exports/<export_id>.csv`.
- b. **Record success.** In one update that checks the lease token, set `state = 'done'`, `object_key`, `completed_at = now` and `expires_at = now + 24 hours`. Clear `upload_id` and `parts`.
- **Keeps:** the finished object in storage. The row moves from `running` to `done`.
- **When it fails:**
  - Sub-step a fails: raise. The parts stay in storage for 24 hours. `upload_id` is still set, so the retry runs sub-step a again.
  - Sub-step a succeeded but b failed: the retry runs a again, and that call fails because the upload is gone. On that error, check whether `exports/<export_id>.csv` exists. If it does, the file is complete, so run b. If not, raise. Only this export writes that key, so an existing object is this export's file.
  - The lease is lost: raise.

### Step 7: Send the download email

- **Starts:** the row is `done` and `emailed_at` is empty. This happens right after Step 6, or on a retry through Step 4a.
- a. **Make a link.** Create a signed URL for the object. Its lifetime is the smaller of 24 hours and `expires_at` minus now.
- b. **Send the email.** Call `send_email(user_id, "export_ready", {report, url, expires_at})`.
- c. **Record it.** Set `emailed_at = now`.
- **Keeps:** `emailed_at`.
- **When it fails:** if `send_email` raises, the attempt raises. The retry goes straight to Step 7 through Step 4a. The file is not rebuilt. If attempts run out while the row is `done`, Step 8 does not mark the export failed, because the file exists. It logs the case and alerts operators. The user still sees Download on the page.

### Step 8: The job fails for good

- **Starts:** the queue calls the final-failure handler after attempt 3 fails.
- a. **Load the row.** If `state` is `done`, this is the email case from Step 7. Log it, alert operators and stop.
- b. **Mark it failed.** Otherwise set `state = 'failed'` and `error` to a short summary. This update does not check the lease token, because the last attempt may have died before it took a lease.
- c. **Clean up the upload.** If `upload_id` is set, abort the upload and clear `upload_id`. If the abort fails, log it. The bucket's lifecycle rule removes leftover parts after 24 hours.
- d. **Send the email.** Call `send_email(user_id, "export_failed", {report})`.
- **Keeps:** `state = failed` and `error`.
- **When it fails:** if the email fails, log it. The page still shows `failed`, so the user is not left waiting for an email that never comes. If the row update fails, the handler raises. The row keeps its last state and an old heartbeat, and operators see it in the logs. Nothing is downloadable on this path, because no object was made visible.

### Step 9: The page shows the export's state

- **Starts:** the report page loads, or the user gets a `202` from Step 3.
- a. **Read the latest export.** `GET /api/reports/{report_id}/exports/latest` checks `report.view`. It returns only the caller's own exports. It returns the active export (`queued` or `running`) if there is one. Otherwise it returns the most recent export for this report. The response has `state`, `attempt`, `error`, `expires_at`, `filters`, `cols` and `stale`.
- b. **Show the state.**
  - `queued`: "Export queued." If `error` is set, add "Retrying after an error."
  - `running`, not stale: "Export running, attempt N of 3."
  - `running`, stale: "Export retrying." An attempt was killed or its worker died.
  - `done`: a **Download** button. It calls `GET /api/exports/{id}/download`. That checks ownership, `report.view`, and that `expires_at` has not passed. It then redirects to a fresh signed URL that lasts until `expires_at`.
  - `failed`: "Export failed: <error>", with a **Try again** button. Try again starts Step 1 again.
- c. **Expired.** When the time is past `expires_at`, or the download finds the object missing, show "This export has expired. Start a new one" and offer the button. The page and the link both end at 24 hours, even though the bucket keeps files for 7 days.
- d. **Poll.** While the state is `queued` or `running`, poll `latest` every 3 seconds. Stop on `done` or `failed`, or when the user leaves the page.
- **Keeps:** nothing in the browser. The server holds all export state, so reloading or opening the page on another device shows the same status. No browser storage is used.
- **When it fails:** a failed status request keeps the last state and tries again on the next poll. A download that returns 403 shows "You no longer have access to this report." A download that finds no object shows the expired message.

## What the user sees when things fail

| Where | What happens | What the user sees |
|---|---|---|
| Step 1, `row_count` read | 503 | "Export failed, try again" |
| Step 2, replica read | 503, nothing stored | "Export failed, try again" |
| Step 3a, insert | 500, no job queued | Error message |
| Step 3b, enqueue | Row set to `failed` | "Export failed: could not queue" |
| Step 4b, live lease held | Raise, queue retries | Queued or running |
| Step 4c, no access | `failed`, email sent | "Export failed: no access" |
| Step 5, read or part upload error | Raise, retry from checkpoint | "Retrying after an error" |
| Step 5, killed or worker died | Queue retries from checkpoint | "Export retrying" once stale |
| Step 6, completion error | Raise, retry | "Retrying after an error" |
| Step 7, email error | Raise, email retried, file kept | Download still shown |
| Step 8, final failure | `failed`, upload aborted, email sent | "Export failed" |

## Build steps (one time, not part of how the system runs)

1. **Shared query and CSV writer.** Move the logic that turns `filters` and `cols` into a replica query, and the check of `cols` against the report's columns, into shared functions. The page API and the export both call them. Add a CSV writer that follows RFC 4180 and writes UTF-8 with a BOM, so Excel opens it cleanly.
2. **Table `report_exports`** on the primary. Columns: `id` (UUID, primary key), `user_id`, `report_id`, `filters`, `cols`, `state` (`queued`, `running`, `done` or `failed`), `error`, `attempt`, `job_id`, `lease_token`, `started_at`, `heartbeat_at`, `upload_id`, `parts` (JSON list of `{part_number, etag}`), `last_row_id`, `object_key`, `completed_at`, `expires_at`, `emailed_at`, `created_at` and `updated_at`. Add a partial unique index on `(user_id, report_id)` where `state` is `queued` or `running`. The database then allows only one active export per user per report.
3. **Email templates.** Add `export_ready` (report name, URL, expiry time) and `export_failed` (report name). Reuse existing templates if they already exist under other names.
4. **Constants.** `SYNC_MAX_ROWS = 10_000`, `SMALL_PAGE_ROWS = 1_000`, `EXPORT_PAGE_ROWS = 5_000`, `PART_BYTES = 8 MiB`, `STALE_AFTER = 5 minutes` (provisional, see open questions).
5. **Storage helpers.** Add an "object exists" check, which Step 6 needs. Confirm that uploading a part number again replaces the earlier part, because Step 5d relies on it.

## Open questions

- **Speed and time per attempt.** Measure rows per second for 5,000-row pages on the replica, using the largest real report. Also measure part upload and page read times. If a 2-million-row export cannot finish in one 30-minute attempt, later attempts resume from the checkpoint. But the 3-attempt limit then applies to the whole export, so a large export could fail. Decide whether that is acceptable or whether the job needs a longer timeout. Set `STALE_AFTER` from the same measurements.
- **Nightly rebuild during an export.** `row_id` may change when `report_rows` is rebuilt. An export that spans a rebuild could mix two snapshots or skip rows. Options: pin the export to a build ID, pause exports during a rebuild, or accept and document the risk. Decide before Step 5.
- **Emailed link after access is lost.** The 24-hour link works for anyone who has it, even after `report.view` is revoked. The page download does re-check access. Is this acceptable?
- **Second click with different filters.** Sub-step 3d returns the active export and its filters. Decide whether to show a message ("An export of this report is already running with different filters") or return 409.
- **Row count accuracy.** `row_count` is unfiltered, so a filter that matches 50 rows of a 2-million-row report still takes the large path. The count is also rebuilt nightly, so a stale count can let a few more rows through the small path. Does the product owner accept both? Decide whether a large overrun needs handling.
- **Duplicate job delivery.** Delivery is at least once. A second copy that runs while the first is live raises at Step 4b and uses up an attempt. If the live copy dies after the queue has stopped retrying, nothing restarts the export, and it stays `running` and stale. Check whether the queue delivers duplicates in practice.
- **Email system.** Confirm that `export_ready` and `export_failed` can be added to the existing email system.
- **API memory.** Each small export holds about 4.5 MB at the threshold. Confirm the API servers can take this under concurrent load.