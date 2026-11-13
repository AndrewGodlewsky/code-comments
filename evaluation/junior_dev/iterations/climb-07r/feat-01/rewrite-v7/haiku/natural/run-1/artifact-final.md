# CSV export for the reports page: implementation plan

## Summary

Users want a **Download CSV** button on `/reports/{report_id}`. Today the page loads rows 500 at a time from the read replica, and the URL alone records the filters and columns. A report with 10,000 rows or fewer downloads straight from the click: the response is the CSV. A larger report starts a background job that writes the CSV in parts into object storage and emails a link that works for 24 hours. The page shows the job's status, and a retried attempt resumes from saved progress.

Out of scope: scheduled exports, formats other than CSV, and changes to the page's table. There is no cleanup job. Old files are deleted by the bucket's 7-day lifecycle rule.

## Terms

- **Report**: one table of rows, identified by `report_id`, inside a workspace. The largest report has about 2 million rows, about 900 MB as CSV.
- **Row count**: `reports.row_count`, the total number of rows before any filter. It is rewritten each night when report data is rebuilt.
- **Filters and columns**: the `filters` and `cols` settings in the page URL, for example `?status=open&cols=date,customer,amount`. The server stores no view state.
- **report.view**: the permission a user needs on the report's workspace to see its rows. Every endpoint in this plan checks it.
- **Read replica**: a read-only copy of the database. Report rows are read only from it, never from the primary.
- **Primary database**: the main database. It accepts writes. Export records live here.
- **Keyset paging**: read rows where `row_id` is greater than the last row seen, ordered by `row_id`, with a limit. `row_id` is unique and increases within a report. The plan never uses OFFSET, so every page is equally fast.
- **Encoder**: the one module that turns rows into CSV bytes. Both paths use it, so their output matches.
- **Job queue**: runs a handler function on a background worker. Each worker has 512 MB of memory and runs one attempt at a time. A job payload is JSON, under 64 KB.
- **Attempt**: one run of a job's handler. A job gets at most 3 attempts. The queue waits 60 seconds before attempt 2 and 300 seconds before attempt 3. An attempt still running after 30 minutes is killed. Each attempt starts from the beginning, and the queue saves no progress. Delivery is at least once, so a handler may run again after it already succeeded.
- **Exports bucket**: the existing object storage bucket `exports`. Its lifecycle rules delete each object 7 days after creation, and discard any multipart upload not completed within 24 hours.
- **Multipart upload**: object storage receives numbered parts. Nothing is visible at the object's key until the upload is completed, which joins the parts into one object. Every part except the last must be at least 5 MB. An upload can have at most 10,000 parts.
- **Signed link**: a download URL that expires. The plan uses 24 hours, the maximum allowed.
- **Export record**: one row per export on the primary database. It holds the id, user, report, filters, columns, status, job id, attempt number, upload id, checkpoint, heartbeat, last error, `email_sent_at`, `completed_at`, object key and timestamps.
- **Status**: one of `queued`, `running`, `done` or `failed`.
- **Heartbeat**: a timestamp that a running attempt sets each time it saves progress.
- **Lease**: the right to work on an export. It is held while the heartbeat is less than 5 minutes old. Another attempt may take over only after that.
- **Checkpoint**: saved progress on the export record. It holds `upload_id`, the list of `{part_number, etag}` for uploaded parts, `last_row_id`, and the attempt's start time. An etag is the ID storage returns for each uploaded part.
- **send_email(user_id, template, params)**: the existing function that emails a user from a named template.

## How the export runs

### 1. Choose the path on click

- **Starts**: the user clicks Download CSV.
- **Data moves**: `report_id`, and the `filters` and `cols` from the page URL. `row_count` is read from the read replica.
- **State**: nothing is written.
- **Next**: if `row_count` is 10,000 or fewer, the browser opens the small-export URL (step 2). Otherwise the page sends the large-export request (step 3).
- **On failure**: if `row_count` cannot be read, show an error and start no export. Do not guess a path.

### 2. Small export: the response is the CSV

- **Starts**: `GET /api/reports/{id}/export.csv?filters=...&cols=...`.
- **Checks**: the user needs `report.view` on the report's workspace, otherwise 403. Every column in `cols` must be a real column of the report, otherwise 400. Filters are parsed by the same code the page API uses.
- **Data moves**: the server reads keyset pages of 500 rows from the replica. It writes a header row first, with columns in URL order. Each page goes through the encoder and is streamed to the response with `Content-Disposition: attachment`.
- **State**: none. Nothing is stored.
- **Time limit**: the API kills any request that runs longer than 60 seconds. If the stream passes 50 seconds, or more than 10,000 rows turn up because `row_count` is stale, the server aborts the connection. It does not end the response cleanly. The browser then reports a failed download, not a short file. The page says "Try again later."
- **On failure**: 403 shows the page's existing permission message. A replica error before the first byte returns 503. A failure mid-stream aborts the connection, so the download fails.

### 3. Large export: the click starts a job

- **Starts**: the page sends `POST /api/reports/{id}/exports` when `row_count` is above 10,000. Filters and columns go in the JSON body, so long filter strings are safe.
- **Checks**: `report.view`, otherwise 403. The filters and columns JSON must be 8 KB or less, otherwise 400.
- **Order of work**:
  a. Run the stale-record check (step 12) for this user and report.
  b. Insert an export record with status `queued`. The partial unique index rejects the insert if this user already has a queued or running export of this report. If it does, read that active record and return it. No second job starts, so a double click gets the same export.
  c. Enqueue `export_report_csv` with payload `{export_id}` only. The job reads filters and columns from the record, which keeps the payload small.
  d. Save the returned `job_id` on the record.
  e. Return 202 with the export id and its status.
- **State**: the export record on the primary database.
- **On failure**: if the insert fails, nothing runs and the request returns 503. If the enqueue fails, set the record to `failed` with error "could not queue", and return 503. If the enqueue succeeded despite the error, the job later finds a `failed` record and exits (step 4). If saving `job_id` fails, the job still runs. The record just lacks that id.

### 4. Worker: start an attempt

- **Starts**: the queue runs `export_report_csv(ctx, payload)` on a worker. `ctx.attempt` is 1, 2 or 3.
- **Data moves**: `export_id` from the payload. The worker reads the record from the primary database.
- **Order of work**:
  a. If the record is `done` and `email_sent_at` is set, return. If it is `done` but `email_sent_at` is empty, go to step 10 and send only the email. If it is `failed`, return. This covers duplicate delivery and the enqueue error in step 3.
  b. Claim the record with one conditional update on the primary. Set status to `running`, `attempt` to `ctx.attempt`, `job_id`, and heartbeat to now. The update succeeds only if status is `queued`, or if status is `running` and the heartbeat is more than 5 minutes old (a lease left by a dead worker). If nothing matches, another live attempt owns the export. Raise, so the queue retries later.
  c. Check `report.view` again. If access was removed, set the record to `failed` with "no longer has access" and return normally. Do not retry, and send no link.
- **State**: the record moves to `running`, and its heartbeat is set.
- **On failure**: if the claim query fails, raise, and the queue retries.

### 5. Find the resume point and open the upload

- **Starts**: a successful claim in step 4b.
- **Data moves**: the checkpoint on the record: `upload_id`, the list of `{part_number, etag}`, `last_row_id`, and the attempt's start time. The start time is used for the time budget in step 8.
- **Order of work**: if there is no `upload_id`, call `start_multipart(exports, reports/{report_id}/exports/{export_id}.csv)`. Save the returned `upload_id` on the record before reading any rows, so the upload can be aborted later. If an `upload_id` already exists, continue that upload. It stays valid until its 24-hour lifecycle expiry.
- **State**: `upload_id` on the record.
- **On failure**: if `start_multipart` fails, raise and retry. If saving the id fails after the upload started, the orphaned upload is removed by the 24-hour lifecycle rule. The retry starts a new upload.

### 6. Read rows and fill the part buffer

- **Starts**: the loop after step 5.
- **Data moves**: each read is keyset paging from the replica: `row_id > last_row_id`, ordered by `row_id`, `LIMIT 5000`, with the record's filters and columns. Each page is encoded to CSV bytes and appended to an in-memory part buffer. The header row is written only when there is no checkpoint yet.
- **Memory**: one page of rows is about 2 to 3 MB for the largest report. The part buffer holds up to 8 MB. The job never holds more than about 12 MB of report data, far below the 512 MB worker limit. It never holds a whole report.
- **Stop**: when a read returns no rows.
- **State**: only the in-memory buffer. A crash loses it, and step 7 rebuilds it from the checkpoint.
- **On failure**: a replica error raises, and the retry resumes from the checkpoint. Nothing has been uploaded from the lost buffer, so storage is not affected.

### 7. Upload a part and save the checkpoint

- **Starts**: the buffer reaches 8 MB. At 8 MB, the largest report needs about 115 parts, far below the 10,000 limit.
- **Data moves**: `upload_part(upload_id, n, bytes)` returns an etag. `n` is the number of parts so far, plus one. Then one primary write appends `{n, etag}` to the record's parts, sets `last_row_id` to the last row in this buffer, and sets the heartbeat to now. Only rows inside uploaded parts count toward `last_row_id`.
- **State**: the checkpoint on the record.
- **On failure**: if `upload_part` fails, raise. The retry resumes from the last checkpoint and re-uploads the same part number, replacing any partial part. If the checkpoint write fails after a successful upload, the retry re-derives the same part number and the same rows, so it replaces the uploaded part. This holds only if re-reading from `last_row_id` returns the same rows. See open question 3.

### 8. Time budget: continue in a new job

- **Starts**: after each checkpoint in step 7.
- **Rule**: if this attempt has run for more than 20 minutes, stop here. The 10-minute margin below the 30-minute attempt timeout keeps each attempt inside the timeout.
- **Action**: set the record to `queued`, then enqueue `export_report_csv` with payload `{export_id}`. The new job gets its own 3 attempts. Return normally.
- **On failure**: if the enqueue raises, the attempt raises, and the retry resumes from the checkpoint just saved. The lease in step 4b stops two continuations from running at once. If the enqueue succeeded and the attempt then died, the retry may enqueue a second continuation. The second one cannot claim the record while the first holds the lease.
- **Note**: if a full run on the largest report measures well under 20 minutes, remove this step. Keep the checkpoint anyway.

### 9. Finish: complete the upload

- **Starts**: a read in step 6 returns zero rows.
- **Action**: upload the rest of the buffer as the last part. It may be smaller than 5 MB. Call `complete_multipart(upload_id, etags)`. This makes the object visible at its key and replaces any earlier object there. Then one primary write sets the record to `done`, `completed_at` to now, and the object key.
- **State**: the object appears at its key only at this moment. Before that, no partial file can be downloaded.
- **On failure**: before `complete_multipart` succeeds, raise and retry from the checkpoint. If `complete_multipart` reports that the upload is gone, it already finished but the `done` write was lost. Clear the checkpoint and start over with a new upload. That replaces the object with identical content. This is slow but rare. A storage helper that checks whether an object exists would avoid the full rerun.

### 10. Email the download link

- **Starts**: right after the `done` write in step 9, in the same attempt. It also starts on a retry where the record is `done` but has no `email_sent_at` (step 4a).
- **Data moves**: `send_email(user_id, "export_ready", {export_id, report_id, download_url: signed_url(exports, key, 86400), expires_at})`. The link works for 24 hours.
- **State**: `email_sent_at` is written after the send succeeds.
- **On failure**: if `send_email` raises, raise. The retry sees `done` with no `email_sent_at`, sends only the email, and does not rebuild the file. If every attempt fails, the final-failure handler (step 11) must not mark the export `failed`. The page still offers the download.

### 11. When an attempt fails

- **Starts**: any exception in an attempt, after the early returns in step 4.
- **Non-final attempt**: a wrapper around the handler writes a short error text to the record, sets the status to `queued`, and re-raises. The queue retries after 60 or 300 seconds. The upload is kept so the retry can resume. The page shows "queued, retry N of 3".
- **Final failure**: after the third attempt fails, the queue calls `on_final_failure(ctx, payload, error)` once.
  a. Load the record. If it is `done`, stop. The file exists, and only the email failed.
  b. Set the record to `failed`, with a short error text and `completed_at`. Do this first, so the page is right even if later steps fail.
  c. If an upload exists, call `abort_multipart` to free its parts now, instead of waiting 24 hours.
  d. Call `send_email(user_id, "export_failed", {export_id, report_id})`.
- **On failure**: if the abort or the email fails, log it. The 24-hour lifecycle rule removes the parts anyway, and the page shows `failed` regardless. If the handler cannot write `failed` at all, the record stays `running` with an old heartbeat, and the stale-record check (step 12) handles it. No failure email is sent in that case. This is a known gap.

### 12. Stale-record check, with no cleanup job

- **Starts**: a click (step 3a) or a status poll (step 13). This check runs on request only. It never runs on a schedule.
- **Rule**: a record that is `running` with a heartbeat older than 45 minutes is treated as failed. The 45 minutes is longer than the 30-minute attempt timeout plus the backoff margin. Mark it `failed` with "export stopped responding" in a conditional update. If an upload exists, call `abort_multipart`.
- **State**: the record moves to `failed`.
- **On failure**: if the conditional update fails, leave the record alone. The click returns it.
- **Known gap**: the queue has no status query. A long backlog can make a waiting continuation look stale. The continuation then finds `failed` in step 4a and exits. The result is a consistent failure, not a corrupt file, but the user gets no email for it.

### 13. Page status and download

- **Starts**: each page load, and polling every 5 seconds while the latest export is `queued` or `running`. Polling stops at `done` or `failed`.
- **Data moves**: `GET /api/reports/{id}/exports/latest` returns the most recent record for this user and report. It includes status, attempt, filters, columns, `completed_at` and error text. It checks `report.view`.
- **Display**:
  - `queued`, with "retry N of 3" when a retry is pending.
  - `running`.
  - `done`, with a Download button.
  - `failed`, with the error and a "Start again" button. That button sends the request in step 3.
  - "expired" when `completed_at` is more than 7 days old, because the bucket deletes objects 7 days after creation.
- **Download**: `GET /api/exports/{id}/download` checks `report.view` and that the record is `done`. It returns a fresh signed link valid for 24 hours. If the record is not `done`, it returns 409.
- **On failure**: a 403 or 404 shows a message on the page.

## What the user sees when things fail

| Situation | What the user sees |
|---|---|
| Small export, no `report.view` | 403 with the page's existing permission message |
| Small export, replica fails before the first byte | 503 |
| Small export, stream passes 50 seconds or more than 10,000 rows turn up | Failed download; page says "Try again later." |
| Large export, insert or enqueue fails | 503 |
| Large export, attempt fails and retries remain | "queued, retry N of 3" |
| Large export, final failure | `failed` with the error and "Start again"; failure email sent |
| Large export, file done but email failed | `done` with Download; no failure email |
| Large export, `failed` cannot be written | Stays `running` until the stale-record check; no email (known gap) |
| Download before the export is `done` | 409 |
| Download without permission, or unknown export | 403 or 404 with a message |
| Export older than 7 days | "expired" |

## Build and release

### New pieces to build

1. Table `report_exports` on the primary database, with a partial unique index on `(user_id, report_id)` where status is `queued` or `running`. This enforces one active export per user and report.
2. One shared CSV encoder module, used by both the small path and the job, so the two outputs match.
3. Job `export_report_csv`, with an `on_final_failure` handler.
4. Endpoints: `GET /api/reports/{id}/export.csv` (small path), `POST /api/reports/{id}/exports` (start a large export), `GET /api/reports/{id}/exports/latest` (status), and `GET /api/exports/{id}/download` (fresh signed link).
5. Email templates `export_ready` and `export_failed`. These do not exist yet.

### Checks before release

- **Encoder**: test quoting, commas, newlines, Unicode and formula prefixes. Both paths must produce the same output.
- **Paging**: a keyset walk across page boundaries returns every row exactly once, compared with a full sorted list.
- **Resume**: kill a worker between parts, then let the retry finish. The output bytes must match an uninterrupted run.
- **Memory**: a synthetic 2-million-row report stays well under 512 MB at peak.
- **Time**: run a full 2-million-row export on replica-like data and record the throughput. Confirm that each attempt stays within the 20-minute budget, or that continuations cover the rest.
- **Concurrency**: two simultaneous clicks produce one export record and one job.
- **Permission**: access removed before the job starts gives `failed`, and no link is sent.
- **Email**: a failing `send_email` on a `done` export leaves the export `done`, and a retry sends only the email.
- **Expiry**: the page shows "expired" after 7 days.

## Open questions

Confirm these before building.

1. **Threshold uses the unfiltered total.** The rule is fixed on `reports.row_count`, so a filter that leaves 50 rows of a 2-million-row report still takes the job path. Confirm this is acceptable.
2. **One active export per user and report, whatever the filters.** A click while one is active returns that export, which may have different filters from the current URL. Recommendation: the page shows the filters of the returned export.
3. **Nightly rebuild during an export.** The rebuild rewrites report data, so a running export could mix two versions. Options: refuse exports during the rebuild window, or record a data version at start and fail the export if it changes. Recommendation: pick one before release.
4. **Permission checks at three points**: click, job start and download, as the steps above describe. Recommendation: keep all three.
5. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run formulas when opened in a spreadsheet. Recommendation: the shared encoder prefixes such cells with an apostrophe.
6. **Run time is unmeasured.** Step 8 is the safety valve if a full run is slow. Measure on the largest report before release.