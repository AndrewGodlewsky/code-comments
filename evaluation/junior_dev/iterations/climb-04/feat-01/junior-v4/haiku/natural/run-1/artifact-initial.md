# CSV export for the reports page: implementation plan

## Overview

The reports page gets a **Download CSV** button. The button exports the rows the user is viewing: the filters and column order in the page URL, plus a header row. Two paths, decided by `reports.row_count`:

- **Small (10,000 rows or fewer):** the click's HTTP response is the CSV. Nothing is queued or stored.
- **Large (more than 10,000 rows):** the click returns at once with an export ID. A background job writes the CSV to the `exports` bucket and emails the user a 24-hour download link. The page shows the export's state until it finishes.

Terms used below:

- **Replica**: the read replica of the database. All report rows are read from it. Writes go to the primary.
- **Checkpoint**: progress the export job saves in its own database row, so a retry can resume where the last attempt stopped.
- **Lease token**: a random value written at the start of each job attempt. A job attempt writes its progress only while its token is still the current one, so a stale attempt cannot overwrite a newer one.

---

## Step 0: Preparation (before any runtime behaviour)

0.1. **Extract the row query and CSV formatting into shared functions.** Move the logic that turns `filters` and `cols` into a replica query, and the logic that checks `cols` against the report's columns, into one function. The page API and the export code both call it, so they cannot drift apart. Add a CSV writer that quotes fields per RFC 4180 and writes UTF-8 (with a BOM, so Excel opens it cleanly).

0.2. **Create the export table on the primary.** Table `report_exports`:

- `id` (UUID, primary key)
- `user_id`, `report_id`, `filters`, `cols` (the request, stored here, not in the job payload, because the job payload must stay under 64 KB)
- `state`: one of `queued`, `running`, `done`, `failed`
- `job_id`, `attempt`, `lease_token`, `started_at`, `heartbeat_at`
- `upload_id`, `parts` (JSON list of `{part_number, etag}`), `last_row_id` (the checkpoint)
- `object_key`, `completed_at`, `expires_at` (completion time + 24 h), `emailed_at`
- `error` (short text), `created_at`, `updated_at`

Add a **partial unique index** on `(user_id, report_id)` where `state IN ('queued', 'running')`. The database enforces "one active export per user per report", so two quick clicks cannot both succeed.

0.3. **Add two email templates** to the existing email system: `export_ready` (params: report name, download URL, expiry time) and `export_failed` (params: report name). If the templates already exist under other names, reuse those.

0.4. **Fix the constants:** `SYNC_MAX_ROWS = 10_000`, `EXPORT_PAGE_ROWS = 5_000` (rows per replica query inside the job), `PART_BYTES = 8 MiB` (at least the 5 MB minimum, and well under the 10,000-part limit).

---

## Step 1: The user clicks Download CSV

**Starts:** the user clicks the button on `/reports/{report_id}`.

**What happens:** the browser sends `POST /api/reports/{report_id}/exports`. The body holds the `filters` and `cols` read from the page URL. The browser does not decide whether the export is small or large. The server does that.

**Data moved:** the filters and column list (a few hundred bytes).

**State:** none yet.

**Failure:**

- The caller lacks `report.view` on the report's workspace: return **403**, the same check as the page.
- `cols` names a column the report does not have, or a filter is malformed: return **400**. Use the same validation as the page API.
- The report does not exist: return **404**.

Next, the server reads `reports.row_count` from the replica and branches. If that read fails, return **503**. Do not guess a path.

---

## Step 2: Small export (10,000 rows or fewer)

**Starts:** Step 1 found `row_count <= 10,000`.

**What happens:** the server reads the rows from the replica in keyset pages (`row_id > after ORDER BY row_id LIMIT 1000`), formats them with the shared CSV writer, and returns `200` with `Content-Type: text/csv` and `Content-Disposition: attachment; filename="<report>.csv"`.

**Data moved:** at roughly 450 bytes per row, 10,000 rows is about 4.5 MB. The server builds the whole CSV in memory before sending any byte. This is deliberate. Once headers are sent, an error cannot be reported to the user, and a truncated CSV looks complete. Buffering the full response means any failure returns a real error code.

**State:** nothing is written to the database or to storage.

**Failure:**

- Replica query fails or times out (the API kills requests after 60 s): return **503**, and the page shows "Export failed, try again". Nothing is stored, so a retry is safe.
- A `row_count` that is stale (see the open questions) can send a few more than 10,000 rows here. That is acceptable: the page still gets a full file, and the memory cost stays small.

The browser saves the blob as a file. No status panel is shown.

---

## Step 3: Large export is requested (more than 10,000 rows)

**Starts:** Step 1 found `row_count > 10,000`.

**What happens, in order:**

3.1. **Find or create the active export.** In one transaction, insert a row into `report_exports` with `state = 'queued'`, the user, the report, `filters` and `cols`.

- If the insert hits the partial unique index, an active export already exists for this user and report. Read it and return it (see 3.4).

3.2. **Queue the job.** Call `enqueue("report_export", {"export_id": "<id>"})`. The payload holds only the ID.

- Store the returned `job_id` on the row.
- If `enqueue` raises, set the row to `state = 'failed'` with `error = "could not queue"` and return **503**. Do not leave a `queued` row behind with no job.

3.3. **Return 202** with `{ "export_id": "<id>", "state": "queued" }`. The click returns straight away.

3.4. **Duplicate click, or an export already running.** Return **202** with the existing export's ID and state. The response includes the existing export's filters and columns, so the page can show what that export covers. The spec says a second click returns the existing export, so the page must show this.

**Data moved:** one row written to the primary; the job payload (an ID).

**State:** `report_exports` row, `queued`.

**Failure:**

- Insert fails for a reason other than the unique index: return **500**. No job is queued, so there is nothing to clean up.
- Job is queued but the row update that stores `job_id` fails: the job still runs, because it reads the row by `export_id`. The missing `job_id` only affects debugging. Log it and continue.

---

## Step 4: Job attempt starts

**Starts:** the queue runs the `report_export` handler (attempt 1, 2 or 3). The retry schedule is 60 s, then 300 s.

**What happens:**

4.1. **Load the row by `export_id`.** If the row is missing, return normally (nothing to do). If `state` is `done` or `failed`, return normally. Delivery is at least once, so this is expected.

4.2. **Take the lease.** In one conditional update (`WHERE id = ? AND state IN ('queued', 'running')`), set `state = 'running'`, `attempt = ctx.attempt`, a new random `lease_token`, `started_at = now`, `heartbeat_at = now`. Keep the existing `upload_id`, `parts` and `last_row_id`. These are the checkpoint from earlier attempts.

4.3. **Re-check permission.** Confirm the user still has `report.view`. If not, set `state = 'failed'` with `error = "no access"`, send `export_failed`, and **return normally**. This avoids retrying a request that can never succeed.

**Data moved:** one row updated on the primary.

**State:** `running`, with the lease token and checkpoint.

**Failure:**

- The conditional update changes zero rows: another attempt already holds the lease or the export has ended. Return normally. If the row is still `running` and `heartbeat_at` is fresh, another attempt is working on it. If the heartbeat is stale, raise, so the queue retries later.

---

## Step 5: The job streams rows into a multipart upload

**Starts:** Step 4 took the lease.

**What happens:**

5.1. **Start or resume the upload.** If `upload_id` is empty, call `start_multipart("exports", "<export_id>.csv")` and store the returned `upload_id` on the row before writing any data. The key is per export, so a retry always targets the same object key.

Note: `start_multipart` makes nothing visible until `complete_multipart` succeeds. A half-written file cannot be downloaded.

5.2. **Read a page of rows.** Run the shared row query on the **replica**, with `row_id > last_row_id ORDER BY row_id LIMIT 5000`. `last_row_id` starts empty, so the first page begins at the first row. The job calls the query function directly. It does not go through the HTTP API, which caps pages at 500 rows.

5.3. **Format and buffer.** Write the rows as CSV into an in-memory buffer. Write the header row first, but only when `parts` is empty (part 1 begins with the header).

5.4. **Upload a part when the buffer reaches `PART_BYTES`.** Call `upload_part(upload_id, part_number, buffer)`. Then, in one update that checks `lease_token`, append `{part_number, etag}` to `parts`, set `last_row_id` to the last row in the buffer, and set `heartbeat_at = now`. Clear the buffer. Parts are only cut at row boundaries, so `last_row_id` always marks a complete row.

5.5. **Repeat** 5.2 to 5.4 until a replica page returns no rows. Then upload the remaining buffer as the last part. The last part may be smaller than 5 MB. That is allowed.

**Data moved:** replica rows in, about 5,000 at a time (about 2 MB). Uploaded parts go out at 8 MB each.

**Size and time:**

- Largest report: about 2 million rows, about 900 MB of CSV. At 8 MB per part that is about 115 parts, far below the limit of 10,000.
- Memory per worker: one 8 MB part buffer plus one 5,000-row page (about 2 MB). The job never holds the report.
- Time: one attempt has a 30-minute limit. Replica throughput must be measured before launch (see open questions). A 900 MB export needs an average of about 0.5 MB/s to finish in one attempt. If it does not, the checkpoint lets the next attempt resume from `last_row_id`, so each attempt gets 30 minutes of new progress.

**State:** `upload_id`, `parts`, `last_row_id` and `heartbeat_at` are updated after every part. These survive a worker death.

**Failure:**

- Replica query fails: raise. The queue retries after the backoff, and the next attempt resumes from the checkpoint.
- `upload_part` fails: raise. The part that failed was not recorded, so the next attempt re-reads from `last_row_id` and re-uploads that part. The rows are not lost, and the upload is never made visible.
- Attempt killed at the 30-minute timeout, or worker dies: the job code does not run. The row stays `running` with a stale `heartbeat_at`. The page treats a stale heartbeat as "retrying" (see Step 9). The next attempt resumes from the checkpoint.
- The lease token no longer matches (another attempt took over): the checkpoint write affects zero rows. Raise. The current attempt stops, and the newer attempt's work stands.

---

## Step 6: Finish the file (make it visible)

**Starts:** Step 5 uploaded the last part.

**What happens:**

6.1. **Mark completing.** In an update that checks `lease_token`, set `state = 'completing'`. This marks the point where the object may become visible. A retry must know whether the previous attempt got this far.

6.2. **Complete the upload.** Call `complete_multipart(upload_id, etags)`. The object appears at `exports/<export_id>.csv`. It replaces any object already at that key, which cannot happen in practice because the key is per export.

6.3. **Record success.** In an update that checks `lease_token`, set `state = 'done'`, `object_key`, `completed_at = now`, `expires_at = now + 24 h`. Clear `upload_id` and `parts`.

**Data moved:** the list of part ETags (a few kilobytes). Storage assembles the final object. The worker does not move the file itself.

**State:** `completing`, then `done`.

**Failure:**

- `complete_multipart` fails: raise and retry. Parts are still in storage, because the upload is discarded only after 24 hours without completion. The next attempt sees `state = 'completing'` and repeats 6.2.
- `complete_multipart` succeeded but the update in 6.3 failed: the retry sees `completing`, calls `complete_multipart` again, and the call fails because the upload no longer exists. On that error, check whether an object exists at the key. Because the key belongs to this export alone, an existing object means the file is complete. Then continue to 6.3.
- Lease check fails in 6.1 or 6.3: raise. Another attempt owns the export now.

---

## Step 7: Send the download email

**Starts:** Step 6.3 recorded `done`.

**What happens:**

7.1. Create a download link: `signed_url("exports", object_key, ttl_seconds = 86400)`. The 86,400-second limit is the maximum the storage helper allows, and the spec asks for 24 hours.

7.2. Call `send_email(user_id, "export_ready", {report, url, expires_at})`.

7.3. Set `emailed_at = now`.

**Data moved:** a URL and a timestamp in the email.

**State:** `done` plus `emailed_at`.

**Failure:**

- `send_email` raises: the attempt raises and the queue retries. The retry finds `state = 'done'` with `emailed_at` empty. It skips steps 4 to 6 and sends the email again. The file is not rebuilt.
- Retries are exhausted while `state = 'done'`: `on_final_failure` must not mark the export failed, because the file exists. It logs the case and alerts operators. The user can still see the export as done on the page, and can download it from there (Step 9).

---

## Step 8: The job fails for good

**Starts:** the queue calls `on_final_failure(ctx, payload, error)` after attempt 3 fails. This happens on any failure that is not a `done` email failure.

**What happens:**

8.1. Load the row. If `state` is already `done`, follow the note in Step 7 and stop.

8.2. Otherwise, in an update that checks `lease_token`, set `state = 'failed'` and `error` to a short summary.

8.3. If `upload_id` is set, call `abort_multipart(upload_id)` to discard the parts now. Failure to abort is logged and ignored. The lifecycle rule removes any leftover parts after 24 hours.

8.4. Call `send_email(user_id, "export_failed", {report})`.

**Data moved:** none, beyond the email.

**State:** `failed`, with the error text, and `upload_id` cleared.

**Failure:**

- The email fails here: log it. The page still shows `failed` (Step 9), so the user is not left waiting for an email that never comes.
- The row update fails: `on_final_failure` raises. The state stays `running` with a stale heartbeat, and the page shows a stale run. Operators can see this in logs.

Nothing is ever downloadable in this path, because no object was made visible.

---

## Step 9: The page shows the export's state

**Starts:** the report page loads, or the user clicks Download CSV (Step 3.3).

**What happens:**

9.1. **Read the latest export.** The page calls `GET /api/reports/{report_id}/exports/latest`. The server returns the user's active export if one exists (`queued` or `running`), otherwise the most recent export for this report. It applies the same `report.view` check and returns only the caller's own exports.

9.2. **Show the state:**

- `queued`: "Export queued."
- `running`: "Export running, attempt N of 3." If `heartbeat_at` is older than about 35 minutes, show "Export retrying" instead, because the previous attempt was killed.
- `done`: a **Download** button. Clicking it calls `GET /api/exports/{id}/download`. That endpoint checks that the caller owns the export and still has `report.view`, then redirects to a fresh signed URL. The URL's lifetime is the smaller of 24 hours and the time left until `expires_at`.
- `failed`: "Export failed" with the error text and a "Try again" button. Try again starts a new export through Step 1.

9.3. **Expired exports.** The `exports` bucket deletes each object 7 days after creation. When `done` is more than 7 days old, or the download endpoint's storage read reports the object missing, show "This export has expired. Start a new one." and offer the button.

9.4. **Polling.** While the state is `queued` or `running`, poll `latest` every 3 seconds. Stop when the state is `done` or `failed`, or when the user leaves the page.

**Data moved:** a small JSON status response.

**State:** read only.

**Failure:**

- Status request fails: show the last known state and retry on the next poll. Do not clear the panel.
- Download redirect fails because the object is gone: show the expired message in 9.3.
- The user lost access: the download endpoint returns **403**, and the page shows "You no longer have access to this report."

No browser storage is used. The server holds all export state, so reloading the page or opening it on another device shows the same status.

---

## Open questions

These must be decided before implementation. Each one can change a step above.

1. **Replica throughput.** Measure how many rows per second a 5,000-row keyset page sustains on the replica with the real report. If 2 million rows cannot finish in 30 minutes, the checkpoint design still works, but the largest exports will need two or three attempts. The queue's limit of 3 attempts then applies to the whole export, so confirm this is acceptable. The alternative is a larger timeout for this job type, which the queue does not currently offer.

2. **Nightly rebuild during an export.** `report_rows` is rebuilt each night and `row_id` may be reassigned. A long export that spans a rebuild could mix two snapshots or skip rows. Options: pin the export to a report build ID, skip or delay exports while a rebuild runs, or accept the risk and document it. Recommend deciding this before Step 5.

3. **Emailed link versus revoked access.** The 24-hour signed link works for anyone who has it, even after the recipient loses `report.view`. Decide whether this is acceptable. The page download endpoint (Step 9) does re-check access, so only the emailed link is affected.

4. **Different filters on a second click.** The spec returns the active export on a second click, even if the user has changed filters. Step 3.4 returns the existing export and its filters so the page can say what it covers. Decide whether to show a message ("An export of this report is already running with different filters") or return **409** instead.

5. **`row_count` is unfiltered.** The size decision uses the total row count, so a filter that matches 50 rows of a 2-million-row report still takes the large path, and the user waits for an email. The spec fixes this rule. Confirm the product owner accepts this, or decide whether a filtered count is worth the cost of computing it.

6. **Stale `row_count`.** It is rewritten once a night. Between rebuilds, the size decision may be off by the amount of data added that day. Step 2 tolerates a small overrun. Decide whether a much larger overrun needs handling.

7. **Email templates.** Step 0.3 assumes `export_ready` and `export_failed` can be added to the existing email system. Confirm this.

8. **Export history.** `report_exports` rows are never deleted, since the spec rules out a cleanup job. The rows are small, so this is probably fine, but record the decision.

9. **Truncated downloads on the small path.** Step 2 buffers the whole CSV before sending, which avoids silent truncation. This uses about 4.5 MB of API server memory per request at the threshold. Confirm the API servers can take that under concurrent load.