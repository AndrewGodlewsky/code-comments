# CSV export for the reports page: implementation plan

## Summary

A **Download CSV** button on `/reports/{report_id}`. Reports with `reports.row_count` of 10,000 or fewer return the CSV in the click response. Larger reports queue a background job that builds the CSV in parts in the `exports` bucket and emails a link valid for 24 hours. The page shows the state of the latest export for that report.

## Terms used in this plan

- **Report**: one table of rows, identified by `report_id`, inside a workspace.
- **Read replica**: a read-only copy of the database. Report rows are read only from it. The export record (step 3) is bookkeeping, not report data, so it lives on the primary database.
- **Keyset paging**: read rows with `row_id > last_seen ORDER BY row_id LIMIT n`. Never OFFSET.
- **Job queue**: `enqueue(name, payload)` runs a handler on a worker. Each attempt has a 30-minute timeout. A job gets at most 3 attempts, with waits of 60 s and 300 s before attempts 2 and 3. A retry starts from zero, and the queue stores no progress. Delivery is at least once.
- **Multipart upload**: object storage receives numbered parts that stay invisible until `complete_multipart` joins them into the object at its key. Every part except the last must be at least 5 MB. Incomplete uploads are discarded after 24 hours by the bucket's lifecycle rule.
- **Export record**: one row per export on the primary database. It holds the id, user, report, filters, columns, status, job id, attempt number, upload id, checkpoint, heartbeat, last error and timestamps.

## New pieces to build

1. Table `report_exports` on the primary, with a partial unique index on `(user_id, report_id) WHERE status IN ('queued','running')`. This enforces one active export per user and report.
2. One CSV encoder module, used by both the small path and the job, so the two outputs match.
3. Job `export_report_csv`, with an `on_final_failure` handler.
4. Endpoints: `GET /api/reports/{id}/export.csv` (small path), `POST /api/reports/{id}/exports` (start large export), `GET /api/reports/{id}/exports/latest` (status), and `GET /api/exports/{id}/download` (fresh signed link).
5. Email templates `export_ready` and `export_failed`. These do not exist yet.

## Decisions to confirm before building

1. **Threshold uses the unfiltered total.** The brief fixes the rule on `reports.row_count`, so a filter that leaves 50 rows of a 2-million-row report still takes the job path. Confirm this is acceptable.
2. **One active export per user and report, whatever the filters.** A click while one is active returns that export, which may have different filters from the current URL. Recommendation: the page shows the filters of the returned export.
3. **Nightly rebuild during an export.** The rebuild rewrites report data, so a running export could mix two versions. Options: refuse exports during the rebuild window, or record a data version at start and fail the export if it changes. Recommendation: pick one before release.
4. **Permission checks at three points**: click, job start and download. Recommendation: all three.
5. **Spreadsheet formula injection.** Cells starting with `=`, `+`, `-` or `@` can run formulas when opened in a spreadsheet. Recommendation: prefix such cells with an apostrophe in the shared encoder.
6. **Run time is unmeasured.** Step 8 is the safety valve if a full run is slow. Measure on the largest report before release.

## Steps

### 1. Choose the path on click

- **Starts**: the user clicks Download CSV.
- **Data moves**: `report_id`, and the `filters` and `cols` query parameters from the page URL. `reports.row_count` is read from the replica.
- **State**: nothing is written.
- **Next**: if `row_count <= 10,000`, the browser requests step 2's URL. Otherwise the page sends step 3's request.
- **On failure**: if `row_count` cannot be read, show an error and start no export. Do not guess a path.

### 2. Small export: the response is the CSV

- **Starts**: `GET /api/reports/{id}/export.csv?filters=...&cols=...`.
- **Checks**: `report.view` on the report's workspace, otherwise 403. Each column in `cols` must be a real column of the report, otherwise 400. Filters are parsed by the same code the page API uses.
- **Data moves**: keyset pages of 500 rows from the replica, starting with a header row whose columns follow the URL order. Each page goes through the shared encoder and is streamed to the response with `Content-Disposition: attachment`.
- **State**: none. Nothing is stored.
- **Time limit**: the API kills requests after 60 seconds. If the stream runs past 50 seconds, or more than 10,000 rows turn up (a stale `row_count`), the server aborts the connection instead of ending it cleanly. The browser then reports a failed download rather than saving a short file. The page says "Try again later."
- **On failure**: 403 shows the page's existing permission message. A replica error before the first byte returns 503. A failure mid-stream aborts the connection, so the download fails.

### 3. Large export: the click starts a job

- **Starts**: the page sends `POST /api/reports/{id}/exports` for `row_count > 10,000`. Filters and columns go in the JSON body, so long filter strings are safe.
- **Checks**: `report.view`, otherwise 403. The filters and columns JSON must be 8 KB or less, otherwise 400.
- **Order of work**:
  a. Run the stale check from step 12 for this user and report.
  b. Insert the export record with status `queued`. If the unique index rejects the insert, read the active record and return it. No second job starts. A double click therefore gets the same export.
  c. Enqueue `export_report_csv` with payload `{export_id}`. The payload stays small because the handler reads filters and columns from the record.
  d. Save the returned `job_id` on the record.
  e. Return 202 with the export id and its state.
- **State**: the export record on the primary.
- **On failure**: if the database insert fails, nothing runs and the request returns 503. If the enqueue fails, set the record to `failed` with error "could not queue" and return 503. If the enqueue actually succeeded despite an error, the job later finds a `failed` record and exits (step 4a). If saving `job_id` fails, the job still runs, and the record just lacks that id.

### 4. Worker: start an attempt

- **Starts**: the queue runs `export_report_csv(ctx, payload)` on a worker. `ctx.attempt` is 1, 2 or 3.
- **Data moves**: `export_id` from the payload. The record is read from the primary.
- **Order of work**:
  a. If the record is `done` and its email is sent, return. If it is `done` but `email_sent_at` is empty, go to step 10 and send only the email. If it is `failed`, return. This covers duplicate delivery and the enqueue-error case from step 3.
  b. Claim the record with one conditional update on the primary: set status `running`, `attempt = ctx.attempt`, `job_id`, and heartbeat to now. This succeeds only if status is `queued`, or status is `running` with a heartbeat older than 5 minutes (the lease from a dead worker). If the update matches nothing, another live attempt owns the export. Raise, so the queue retries later.
  c. Check `report.view` again. If access was removed, set the record to `failed` with "no longer has access", and return normally. Do not retry, and send no link.
- **State**: the record moves to `running`, and its heartbeat is set.
- **On failure**: if the claim query fails, raise, and the queue retries.

### 5. Find the resume point and open the upload

- **Starts**: a successful claim in step 4b.
- **Data moves**: the checkpoint on the record: `upload_id`, the list of `{part_number, etag}`, `last_row_id`, and the attempt's start time.
- **Order of work**: if there is no `upload_id`, call `start_multipart(exports, reports/{report_id}/exports/{export_id}.csv)`. Save the returned `upload_id` on the record before reading any rows, so the upload can be aborted later. If an `upload_id` already exists, continue with that upload. It stays valid until its 24-hour lifecycle expiry.
- **State**: `upload_id` on the record.
- **On failure**: if `start_multipart` fails, raise and retry. If saving the id fails after the upload started, the orphaned upload is removed by the 24-hour lifecycle rule. The retry starts a new one.

### 6. Read rows and fill the part buffer

- **Starts**: the loop after step 5.
- **Data moves**: each keyset read is `row_id > last_row_id ORDER BY row_id LIMIT 5000`, with the record's filters and columns, from the replica. Each page is encoded to CSV bytes. The header row is written only when there is no checkpoint yet.
- **Memory**: one page of rows, about 2 to 3 MB for the 2-million-row report (900 MB over 2 million rows), plus a part buffer of up to 8 MB. The job never holds more than about 12 MB of report data, far below the 512 MB limit.
- **Stop**: when a read returns no rows.
- **State**: only the in-memory buffer. It is lost on a crash, and step 7 rebuilds it from the checkpoint.
- **On failure**: a replica error raises, and the retry resumes from the checkpoint. Nothing has been uploaded from the lost buffer, so nothing in storage is affected.

### 7. Upload a part and save the checkpoint

- **Starts**: the buffer reaches 8 MB. Eight megabytes keeps the largest report at about 115 parts, far below the 10,000 limit.
- **Data moves**: `upload_part(upload_id, n, bytes)` returns an etag. `n` is the number of parts so far plus one. Then one primary write appends `{n, etag}` to the record's parts, sets `last_row_id` to the last row in this buffer, and sets the heartbeat to now. Only rows that are inside uploaded parts count toward `last_row_id`.
- **State**: the checkpoint on the record.
- **On failure**: if `upload_part` fails, raise. The retry resumes from the last checkpoint and re-uploads the same part number, replacing any partial part. If the checkpoint write fails after a successful upload, the retry re-derives the same part number and the same rows, so the uploaded part is simply replaced. This holds only if re-reading from `last_row_id` returns the same rows, which is why decision 3 matters.

### 8. Time budget: continue in a new job

- **Starts**: after each checkpoint in step 7.
- **Rule**: if this attempt has run for more than 20 minutes, a 10-minute margin below the 30-minute attempt timeout, stop here.
- **Action**: set the record to `queued`, then enqueue `export_report_csv` with payload `{export_id}`. A new job gets its own 3 attempts. Return normally.
- **On failure**: if the enqueue raises, the attempt raises, and the retry resumes from the checkpoint just saved. The step 4b lease stops two continuations from running at the same time. If the enqueue succeeded and the attempt then died, the retry may enqueue a second continuation, but the second one cannot claim the record while the first holds the lease.
- **Note**: if a full run on the largest report measures well under 20 minutes, this step can be removed. Keep the checkpoint anyway.

### 9. Finish: complete the upload

- **Starts**: a read in step 6 returns zero rows.
- **Action**: upload the remaining buffer as the last part. It may be smaller than 5 MB. Call `complete_multipart(upload_id, etags)`. This makes the object visible at its key and replaces any earlier object there. Then one primary write sets the record to `done`, `completed_at = now`, and the object key.
- **State**: the object appears at the key only at this moment. Before it, no partial file is downloadable.
- **On failure**: before `complete_multipart`, raise and retry from the checkpoint. If `complete_multipart` reports that the upload is gone (it finished, but the done write was lost), clear the checkpoint and start over with a new upload. That replaces the object with identical content. It is slow but rare. A storage helper that checks whether an object exists would avoid the full rerun.

### 10. Email the download link

- **Starts**: right after the `done` write in step 9, in the same attempt. It also starts a retry whose record is `done` but has no `email_sent_at`.
- **Data moves**: `send_email(user_id, "export_ready", {export_id, report_id, download_url: signed_url(exports, key, 86400), expires_at})`. The link works for 24 hours.
- **State**: `email_sent_at` is written after the send succeeds.
- **On failure**: if `send_email` raises, raise. The retry sees `done` with no `email_sent_at` and sends the email only. It does not rebuild the file. If all attempts fail, `on_final_failure` (step 11) must not mark the export failed. The page still offers the download.

### 11. Attempt failure, and final failure

- **Starts**: any exception in an attempt, after the early returns in step 4.
- **Non-final attempt**: a wrapper around the handler writes a short error text to the record, sets status to `queued`, and re-raises. The queue retries after 60 or 300 seconds. The upload is kept so the retry can resume. The page shows "queued, retry N of 3".
- **Final failure**: the queue calls `on_final_failure(ctx, payload, error)` once, after the third attempt fails.
  a. Load the record. If it is `done`, stop. The file exists, and only the email failed.
  b. Set the record to `failed`, with a short error text and `completed_at`. Do this first, so the page is right even if later steps fail.
  c. If an upload exists, call `abort_multipart` to free its parts now instead of waiting 24 hours.
  d. Call `send_email(user_id, "export_failed", {export_id, report_id})`.
- **On failure**: if (c) or (d) fails, log it. The 24-hour lifecycle removes the parts anyway, and the page shows `failed` regardless. If the handler cannot write `failed` at all, the record stays `running` with an old heartbeat, and step 12 handles it. In that case no failure email is sent, and this is an open gap.

### 12. Stale-record check, with no cleanup job

- **Starts**: a click (step 3a) or a status poll (step 13). This runs on request, never on a schedule.
- **Rule**: a record that is `running` with a heartbeat older than 45 minutes is treated as failed. The 45 minutes is more than the 30-minute attempt timeout plus the backoff margin. Mark it `failed` with "export stopped responding" in a conditional update, and call `abort_multipart` if an upload exists.
- **State**: the record moves to `failed`.
- **On failure**: if the conditional update fails, the record is left alone and the click returns it.
- **Open issue**: the queue has no status query, so a long backlog can make a waiting continuation look stale. If that happens, the continuation finds `failed` in step 4a and exits. The result is a consistent failure, not a corrupt file, but the user gets no email for it.

### 13. Page status and download

- **Starts**: each page load, and polling every 5 seconds while the latest export is `queued` or `running`. Polling stops at `done` or `failed`.
- **Data moves**: `GET /api/reports/{id}/exports/latest` returns the most recent record for this user and report: status, attempt, filters, columns, `completed_at` and error text. It checks `report.view`.
- **Display**:
  - `queued`, with "retry N of 3" when applicable.
  - `running`.
  - `done`, with a Download button.
  - `failed`, with the error and a "Start again" button. That button calls step 3.
  - "expired" when `completed_at` is more than 7 days old, because the bucket deletes objects 7 days after creation.
- **Download**: `GET /api/exports/{id}/download` checks `report.view` and that the record is `done`. It returns a fresh signed URL valid for 24 hours. A record that is not `done` returns 409.
- **On failure**: 403 or 404 shows a message on the page.

### 14. Checks before release

- **Encoder**: test quoting, commas, newlines, Unicode and formula prefixes. The same output must come from both paths.
- **Paging**: a keyset walk across page boundaries returns every row exactly once, compared with a full sorted list.
- **Resume**: kill a worker between parts, then let the retry finish. The output bytes must match an uninterrupted run.
- **Memory**: a synthetic 2-million-row report stays well under 512 MB at peak.
- **Time**: a full 2-million-row run on replica-like data, with throughput recorded. Confirm that each attempt stays within the 20-minute budget, or that continuations cover the rest.
- **Concurrency**: two simultaneous clicks produce one export record and one job.
- **Permission**: access removed before the job starts gives `failed`, and no link is sent.
- **Email**: a failing `send_email` on a `done` export leaves the export `done`, and a retry sends only the email.
- **Expiry**: the page shows "expired" after 7 days.