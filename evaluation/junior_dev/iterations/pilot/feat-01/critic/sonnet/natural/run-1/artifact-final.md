# Plan: CSV export for the reports page

## Overview

The Download CSV button calls one new endpoint. The server picks a path by `reports.row_count`:

- **Small report (10,000 rows or fewer).** The response to the click is the CSV. No job runs and nothing is stored.
- **Large report (more than 10,000 rows).** The server records an export, queues a background job and returns HTTP 202 at once. The job streams the rows into the `exports` bucket and emails a 24-hour link. The page shows the export's state.

The brief fixes these two paths, so this plan does not collapse them into one. The small path has no state of its own: no table row, no job, no counters. The click can get a CSV body or a 202 with JSON, and the client handles both (step 1).

The page URL is the only place the current view lives and the server stores nothing about it. So the click sends the page's filters and column order, and the server copies them into the export record.

Names used below: the **replica** is the read replica, where all `report_rows` reads go and never the primary. The **App DB** is the primary application database. It holds the new `report_exports` table, because export state must not be read from a lagging replica. An **active** export has status `queued` or `running`.

**Assumption on `reports.row_count`.** The brief forbids reading report *rows* from the primary. It does not say where the `reports` metadata row lives. This plan reads `row_count` exactly as the page does today (same connection, same query), and treats it as metadata rather than report data. Confirm this with the page's owners before building. If it is wrong, the only change is where that one read goes.

**Assumption on the queue.** `jobs.py` says a failed attempt (raise, timeout or dead worker) is retried after the backoff. This plan reads that as "attempt n+1 starts only after attempt n has failed". The queue cannot prove a worker is dead if it is only partitioned, so the plan does not depend on that guarantee for correctness. It fences instead (step 5). Confirm the queue's behaviour with its owners (open question 1).

**Time and memory targets, and the numbers derived from them (stated once, used throughout).**
- Time: one attempt has 1,800 s. For 2 million rows that needs at least about 1,100 rows/s including upload time. The design target is 900 s or less (half the budget), to leave room for a slow day. Nothing proves this is reachable yet, so step 9.1 is a benchmark that comes first and decides whether the resumable fallback in step 5 is built.
- Memory: the worker has 512 MB. The design target is a peak under 100 MB. The estimate is about 30 MB (step 5.4), and the benchmark checks it. Row size is not a guess: 900 MB over 2 million rows is 450 bytes per row. The 3x object overhead is a guess that the benchmark replaces with a measurement.
- **P, the per-call timeout** for each replica page query and each `upload_part`. Default 120 s. The benchmark sets the final value at no less than 4 times the slowest page latency it observes, **including filtered views of the largest report**, which are the slowest case.
- **H, the heartbeat bound.** A heartbeat follows every page and every part upload, so the longest silent stretch in a live attempt is one call (at most P) plus encoding. H = 2 minutes at the default P.
- **L, the lease lengths.** See the next section. They are derived from H and the queue's constants, not chosen separately.

## State: table `report_exports` (App DB)

| Column | Meaning |
|---|---|
| `id` | UUID |
| `user_id`, `report_id` | Who asked and for which report |
| `filters`, `cols` | Validated copy of the view at click time |
| `status` | `queued`, `running`, `done` or `failed` |
| `job_id` | Returned by `enqueue`. Null until the job is queued. |
| `attempt` | Number of the queue attempt that currently owns the row. Null until the first attempt starts. |
| `lease_expires_at` | The one liveness field. Until this time the row is considered alive. Every stuck-row case in step 4 is decided by it alone. |
| `object_key` | Null until `done`. Then `{report_id}/{id}-{attempt}.csv` in the `exports` bucket. Each attempt writes its own key, and only the attempt that wins the `done` update records its key (step 5, fencing). |
| `rows_written`, `error` | Filled in at the end. `error` is a short generic reason with no filter values. |
| `notified_at` | Set once the success email has been sent |
| `created_at`, `updated_at`, `finished_at` | Timestamps |
| `resume_upload_id`, `resume_row_id`, `resume_parts` | **Only if the resumable fallback in step 5 is built.** Left null otherwise. |

**Unique partial index** on `(user_id, report_id) WHERE status IN ('queued','running')`. The database enforces "one at a time", because application code alone cannot do that safely when two clicks race.

### Lease lengths

| Lease | Set when | Length | Why this length |
|---|---|---|---|
| Not yet enqueued | Row inserted, or a recovery claim (step 4) | 2 minutes | An insert and an `enqueue` call take milliseconds. 2 minutes is a wide margin. |
| Queued | `job_id` saved after `enqueue` | 2 hours | A stated assumption about the worst queue backlog (open question 1). The only number here not derived. |
| Running | Attempt claim (5.1) and every heartbeat (5.5) | 10 minutes | Must cover the longest quiet period of a live job: the retry gap. That is H (2 min, the heartbeat could be that old when the attempt dies) plus the largest backoff (300 s) plus about 3 minutes for the queue to pick the job up. 2 + 5 + 3 = 10. If the benchmark changes P, recompute H and this value together. |

### Two shared routines

Everything that moves a stuck row uses these two routines. No other code writes `failed` or re-enqueues.

**`fail(id, error)`**: `UPDATE ... SET status='failed', error=?, finished_at=now() WHERE id=? AND status IN ('queued','running')`. It always writes `error` and `finished_at`. It returns whether a row changed. Callers: the final-failure handler (step 7), the worker on permission loss (5.2), a click whose `enqueue` raised, and `reclaim`.

**`reclaim(row)`**: decides what to do with an active row that a click has found.
1. If the row is not active or `lease_expires_at` is in the future, return it unchanged.
2. If `job_id` is null (never enqueued): claim it with `UPDATE ... SET lease_expires_at=now()+2 min WHERE id=? AND job_id IS NULL AND lease_expires_at < now()`. Only the caller whose update changes 1 row goes on. It calls `enqueue`, then saves `job_id` and sets the queued lease. If `enqueue` raises, it calls `fail`. Callers that lose the claim just return the row. If the winner dies before saving `job_id`, its claim lease expires after 2 minutes and the next click claims again.
3. Otherwise (`job_id` set, lease expired) the job is lost: call `fail(id, "export lost")`. The slot is now free.

This is deliberately click-driven, with one addition in step 8: the status read also applies rule 3, so a user who just returns to the page sees a lost job as failed. A periodic sweeper was considered and rejected: it is a new scheduled component for a rare case, and the lease makes a sweeper unnecessary.

### Allowed status changes

Every status write is a conditional `UPDATE ... WHERE id=? AND ...`. A write that changes 0 rows means someone else already moved the row, and the writer stops. This table is the only place the rules live.

| From | To | Done by | Condition |
|---|---|---|---|
| (none) | `queued` | click (step 4) | Insert accepted by the unique index |
| `queued` | `running` | worker, start of an attempt (5.1) | Row is `queued`. Sets `attempt` to this attempt's number. |
| `running` | `running` | worker, start of a later attempt (5.1) | Row's `attempt` is lower than this attempt's number. Takes the row over from an earlier attempt that the queue has already declared failed. |
| `running` | `done` | worker (step 6) | Row is `running` and `attempt` is this attempt's number. Also sets `object_key`. |
| `queued` or `running` | `failed` | `fail` (see above) | Row is still `queued` or `running` |
| `done`, `failed` | nothing | | Final. A new click makes a new row. |

Every later write by a worker (heartbeat, done) also requires `attempt` to be its own number, so an older attempt that is somehow still running cannot write over a newer one.

## Steps

### 1. The user clicks Download CSV
- **Starts it:** the click. The page sends `POST /api/reports/{report_id}/export` with the current URL's `filters` and `cols`. It sends no row count and makes no choice of path.
- **Data moves:** filters and column order go to the server. The response is one of:
  - `200` with `Content-Type: text/csv`. The browser saves it as a file.
  - `202` with JSON `{export_id, status, created_at, filters, cols}`. The page switches to the status display in step 8. This also happens for a small report whose `row_count` turned out to be stale (step 3). If the returned `filters` or `cols` differ from the click's, the page says so: "An export with different filters is already in progress" (step 4.2). The user never silently gets something other than what they asked for.
- **State:** none.
- **If it fails:** the button shows an error and can be clicked again. Nothing has been created yet.

### 2. The server checks permission, validates the view and picks a path
- **Starts it:** step 1 arriving at the API.
- **Data moves:**
  1. Check `report.view` on the report's workspace, with the same check as the rows API. Return 403 if missing.
  2. Validate `filters` and `cols` with the rows API's parser, so export and page cannot disagree. Unknown columns or bad filters return 400.
  3. Read `reports.row_count` (see the assumption above). If it is 10,000 or less, go to step 3. Otherwise go to step 4.
- **Note:** `row_count` is the unfiltered total, so a heavily filtered view of a big report still takes the large path. That is what was specified. It is correct, only slower than needed.
- **State:** none written.
- **If it fails:** 403 or 400, and nothing else happens.

### 3. Small path: the response is the CSV
- **Starts it:** step 2.
- **Data moves:**
  1. Read the replica with the rows API's keyset query (`row_id > after ORDER BY row_id`, never OFFSET), in pages of 500. Read at most 10,001 rows. That is about 21 queries, far inside the 60-second request limit.
  2. Write the header (columns in URL order) and each row with the shared CSV writer (step 5) into an in-memory buffer.
  3. When the rows run out, send the buffer with `Content-Type: text/csv; charset=utf-8` and `Content-Disposition: attachment; filename="report-{id}.csv"`.
- **Memory and abuse.** 10,000 rows at 450 bytes is about 5 MB per request. The plan adds no counter or cap of its own. A per-process counter does not bound a fleet and cannot see one user's requests across servers, so it would be mechanism without a guarantee. Total memory is bounded by the API servers' existing concurrent-request limit times 5 MB, and abuse by whatever per-user rate limit the platform applies to the rows API. The export endpoint should sit behind the same limit (open question 4). Small exports are not covered by the one-export-per-user rule, since no state exists to enforce it, and the brief only asks for that rule on large exports.
- **State:** none. Nothing is stored and no job runs.
- **If it fails:**
  - A replica error returns 500. Nothing is sent until the CSV is complete, so the user never receives a partial file. This is why the response is buffered and not streamed.
  - **Stale `row_count`.** It is rewritten only nightly, so the report may have grown. If the read reaches a 10,001st row, discard the buffer and continue with step 4 *in the same request*. The response is then the 202 from step 4, not a CSV. The cost is bounded (about 21 wasted queries) and only reports that sit near the threshold can hit it.

### 4. Large path: record the export, or return the existing one
- **Starts it:** step 2 (or the stale-count fallback in step 3).
- **Data moves:**
  1. `INSERT` a `report_exports` row: status `queued`, the validated `filters` and `cols`, a new `id`, `job_id` null, and the 2-minute not-yet-enqueued lease.
  2. If the unique index rejects the insert, an export is already active. Load it and run `reclaim` on it.
     - If `reclaim` freed the slot (a lost job), go back to 1 once. If the second insert is also rejected, load the winner and return it.
     - Otherwise return the existing export with `202` and the same JSON shape, including its `filters` and `cols`. This covers double-clicks and racing requests. If its filters differ from this click's, the user still gets the existing export, since the rule is one per user per report, and the page tells them so (step 1).
  3. If the insert succeeded, call `enqueue("report_export", {"export_id": id})`. The payload is tiny. Filters and columns stay in the row, which is the single source of truth.
  4. Save the returned `job_id` and set the 2-hour queued lease in one update, then return `202` with `{export_id, status, created_at, filters, cols}`.
- **State:** one App DB row, `queued`.
- **If it fails:**
  - `enqueue` raises: call `fail(id, "could not queue")` and return 500. The slot is free again.
  - The server dies after the insert, or between `enqueue` and saving `job_id`: the row has a null `job_id` and a lease that runs out in 2 minutes. The next click (or a page read, which only reports it) hits `reclaim` rule 2 and one caller re-enqueues. If the first `enqueue` actually succeeded, the second queues a duplicate job for the same row. That is harmless: the second job's claim in 5.1 either takes the row over or finds it `done`, and at-least-once delivery already forces handlers to tolerate this.
  - The job is lost after being queued: the lease runs out and `reclaim` rule 3 fails the row. A job that is only slow stays `queued`. If it later starts it finds the row `failed` and returns (5.1).

### 5. The worker runs the job (`report_export`, attempts 1 to 3)
- **Starts it:** the queue. If an attempt fails, the queue retries after 60 s, then 300 s. It keeps no progress, so every attempt starts from the beginning with the same payload.
- **Data moves, in order:**
  1. **Load and claim.** Read the export row. Then:
     - Not found: return.
     - `done`: skip to step 6.2 (send the email if `notified_at` is empty) and return. This is a duplicate delivery or a retry after an email failure.
     - `failed`: return.
     - Otherwise run the claim from the status table: `queued` to `running`, or `running` with a lower `attempt` taken over, setting `attempt` to this attempt's number and the lease to 10 minutes from now. If it changes 0 rows, another worker with the same attempt number already owns the row (the queue delivered the same attempt twice). Return without doing anything.
  2. **Recheck permission.** If the user no longer has `report.view`, call `fail(id, "access removed")` (no retry can help), send no data and return. Permission is checked here only. See the permission stance below.
  3. **Start the upload.** `start_multipart("exports", key)` where `key = {report_id}/{id}-{attempt}.csv`. Nothing is visible at the key until `complete_multipart`.
  4. **Stream rows.**
     - Read the replica with keyset pagination in pages of 5,000 rows, applying the view's filters. This is the job's own query and is not bound by the rows API's 500 cap. For the largest report it makes about 400 queries instead of 4,000.
     - Encode each row with the CSV writer and append it to a byte buffer. The first row is the header.
     - When the buffer reaches **8 MB** (the minimum part size is 5 MB), call `upload_part(upload_id, n, data)`, keep the etag and clear the buffer.
     - Upload the rest as the last part. The header guarantees at least one part, even for an empty result.
     - **Memory estimate.** Data held at once: the 8 MB buffer, one page of 5,000 rows as database objects (assume up to 3 times the 450-byte CSV size, so about 7 MB), and the encoded copy of that page (about 2.3 MB). That is about 18 MB, and about 30 MB with interpreter and library overhead, against the 100 MB target and the 512 MB limit. The benchmark in 9.1 replaces this estimate with a measurement. The 900 MB file is about 113 parts, well under the 10,000-part limit.
  5. **Heartbeat.** After every page and after every part upload, run `UPDATE ... SET lease_expires_at=now()+10 min WHERE id=? AND status='running' AND attempt=?`. Every replica page query and every `upload_part` call runs with the timeout P. If one times out, the attempt raises and the queue retries. So the gap between heartbeats in a live attempt is at most H. If the update changes 0 rows, someone failed the export or a newer attempt took over. Abort this attempt's upload and return without raising.
  6. **Publish.** Run the heartbeat check again, then call `complete_multipart(upload_id, etags)`. This is the only moment the file becomes downloadable, so a half-written file can never be fetched. Then go to step 6.1.
- **Fencing: what if an old attempt is still running.** The plan assumes the queue starts attempt n+1 only after attempt n failed or was killed. It does not rely on that. If two attempts ever overlap:
  - Each has its own `upload_id` and its own object key (it includes the attempt number), so their bytes never mix and neither overwrites the other.
  - Only the attempt whose conditional `done` update succeeds (step 6.1) writes its key into `object_key`. The other object is never linked from anywhere, and the bucket's 7-day lifecycle rule deletes it. This is the fence: `complete_multipart` has no condition of its own, so the condition is placed on the row that decides which object counts.
  - The older attempt notices at its next heartbeat (within H) that its `attempt` no longer matches, aborts its upload and exits. Worst case is wasted work for up to H, not a wrong or duplicate result.
- **CSV writer (shared with step 3).** UTF-8, RFC 4180 quoting. A cell starting with `=`, `+`, `-` or `@` gets a leading `'` to block spreadsheet formula injection.
- **Permission stance.** Permission is checked at the click, at job start, on the status read and on every in-app download. It is not rechecked when the file is finished. The emailed link works for 24 hours whatever happens to the user's access in that time. The brief asks for exactly that, so this plan accepts it. The in-app Download button is stricter on purpose, because it is our own control and the email link is not.
- **State:** the row is `running` with this `attempt`. The upload exists only inside the bucket until 5.6.
- **If it fails:**
  - On any exception, call `abort_multipart(upload_id)` (best effort) and re-raise so the queue retries. A retry starts a new upload at its own key.
  - If the worker is killed or times out, nothing can clean up. The bucket discards an unfinished multipart upload after 24 hours, so no cleanup job is needed.
  - **Gap between publish and done.** If the worker dies after `complete_multipart` and before the `done` update in step 6.1, the retry re-streams the whole file to its own key. The earlier object is unlinked and expires in 7 days. The window is a few milliseconds, so it is accepted. A click cannot fail the row inside that window, because the heartbeat just before publishing set a 10-minute lease.
- **Resumable fallback (built only if the benchmark in 9.1 fails the time target, or the queue owners will not raise the timeout instead).** It changes only this step. Design and its correctness conditions:
  - *What is saved.* After each `upload_part`, in one conditional update (`attempt` must match), append `{part_number, etag}` to `resume_parts` and set `resume_upload_id` and `resume_row_id`. `resume_row_id` is the `row_id` of the last row inside that part. Parts are cut only at row boundaries, so the next row is always `row_id > resume_row_id`.
  - *Crash between upload and save.* The part was uploaded but not recorded. The retry re-uploads the same part number from the same row boundary. This relies on a repeated part number replacing the earlier one, as in common object stores. The benchmark verifies it on our storage before the fallback is chosen.
  - *A retry continues.* It reads the saved state, resumes with `row_id > resume_row_id` and the saved etags, and keeps the same `upload_id` and key. Its object key stays the first attempt's key (stored with the resume state), so fencing still holds. A retry that finds the upload gone or rejected starts over.
  - *24-hour expiry.* The bucket discards an upload not completed within 24 hours of its start. The three attempts and two backoffs span at most about 3 x 30 min + 6 min, under 2 hours, so a retry always finds the upload alive.
  - *Pagination consistency across attempts.* Keyset order by `row_id` is stable, and the filters come from the saved row, so a resumed read continues where the first one stopped. The one thing that can change rows between attempts is the nightly rebuild (open question 2). That risk exists with or without resume, because a single attempt already reads for up to 15 minutes.

### 6. Mark the export done and email the link
- **Starts it:** step 5.6 succeeding (go to 6.1), or step 5.1 finding the row already `done` (go to 6.2 directly).
- **Data moves:**
  1. `UPDATE report_exports SET status='done', object_key=?, rows_written=..., finished_at=now() WHERE id=? AND status='running' AND attempt=?`. This frees the user's slot and records which object is the real one. If it changes 0 rows, stop (see the fencing note in step 5). The orphan object is never linked.
  2. If `notified_at` is empty: build the link with `signed_url("exports", object_key, 86400)`. That is the maximum the helper allows and exactly the 24 hours required. Call `send_email(user_id, "report_export_ready", {report name, url, expires_in: "24 hours"})`, then set `notified_at`. If `notified_at` is already set, do nothing.
- **State:** the row is `done`, then `notified_at` is set.
- **If it fails:**
  - If `send_email` raises, the attempt fails and the queue retries. The retry finds the row `done` (step 5.1) and runs only 6.2.
  - If the job dies between sending and recording `notified_at`, the user may get one duplicate email. That is acceptable.
  - **If the email never succeeds** (all attempts fail at this step), the export stays `done` and the user is not emailed. The page still shows `done` with a Download button (step 8), which is how they get the file. That button is therefore required, not optional.
  - The file stays in the bucket for 7 days under the existing lifecycle rule, and nothing deletes it sooner.

### 7. Final failure handler (`on_final_failure`)
- **Starts it:** the queue, once, after attempt 3 fails.
- **Data moves:**
  1. Call `fail(id, "export failed")`. This frees the slot. If it changes 0 rows because the row is already `done`, the failure was the email step in step 6. Log it and stop.
  2. Otherwise call `send_email(user_id, "report_export_failed", {report name})`.
- **State:** the row is `failed`, with `error` and `finished_at` set.
- **If it fails:** update the status first, so the page is right even if the email fails. Catch and log email errors rather than raising, because the queue calls this handler only once. No bad file can exist, since only `complete_multipart` creates an object and only the `done` update links one.

### 8. The page shows the export state
- **Starts it:** the page load for `/reports/{id}`, or a 202 from step 4.
- **Data moves:**
  1. `GET /api/reports/{report_id}/exports/current` checks `report.view` and returns 403 without it. A user who has lost access therefore sees no status, no filters and no error text, so nothing about their earlier view leaks. If allowed, it reads the user's most recent export for this report from the **App DB**. If that row is active with an expired lease and a non-null `job_id`, it first applies `reclaim` rule 3, so a lost job shows as failed. It returns `{id, status, created_at, finished_at, filters, cols}`.
  2. **Retention.** A `done` export is hidden once `finished_at` is more than 6 days old. The bucket deletes an object 7 days after it was created, and the upload may have started up to about 2 hours before `finished_at`, so 6 days leaves a margin of a day. Other states are hidden once `created_at` is more than 7 days old.
  3. The page shows a status chip: queued, running, done or failed. If the returned `filters` or `cols` differ from the current view, it adds a line such as "Showing your earlier export with different filters".
  4. While the status is queued or running, the page polls every 5 seconds, and it pauses while the tab is hidden. It stops on done or failed.
  5. For `done`, the page shows a Download button. It calls `GET /api/reports/{report_id}/exports/{id}/download`, which re-checks `report.view`, returns 410 if the export is past the retention above, and otherwise redirects to `signed_url("exports", object_key, 300)`. The 5-minute link is only for the immediate click and is generated fresh each time, so it is independent of the 24-hour emailed link.
- **State:** none new, apart from the possible `fail` in item 1.
- **If it fails:** a failed poll keeps the last known state and tries again at the next interval. A user who comes back later sees the same state, because it lives in the App DB.

### 9. Tests and rollout
- **Starts it:** development. **First task:** the benchmark in 9.1, done by the engineer who builds step 5, before the rest of the work is built on it.
- **Tests:**
  1. **Benchmark.** Run step 5 against the largest report on the replica, once unfiltered and once with the slowest filter set the page offers. Record total time, peak memory, the latency distribution of every page query and every part upload, and the real object overhead per row. Set P from the slowest page latency (at least 4 times), then recompute H and the running lease. Pass if the time is 900 s or less and peak memory is under 100 MB. If not, build the resumable fallback or ask for a longer timeout (step 5). Also check whether repeating a part number replaces the part, which the fallback needs.
  2. **Both paths.** Test both sides of the 10,000-row boundary and the stale-count fallback, including that the client handles the 202. Check header, column order and CSV escaping.
  3. **Parity.** The export's rows equal the rows API's rows for the same filters.
  4. **Replica only.** No query on the export path reads report rows from the primary.
  5. **Concurrency.** Two simultaneous clicks give one export row and one job. Two clicks on a never-enqueued row with an expired lease give one `enqueue`, and a failing winner leaves the row `failed` with `error` and `finished_at` set. A stale-count fallback that meets an existing export with other filters returns that export and the page says so. Deliver the same attempt twice and check only one worker streams.
  6. **Failure injection.** Fail the job on attempts 1, 2 and 3, and kill the worker mid-upload. Check that no object exists at the key before `complete_multipart`, that retries take over the row, and that a failure on attempt 3 marks `failed`, sends the failure email and frees the slot. Run two overlapping attempts on purpose (a paused older one) and check that only the attempt that wins the `done` update is linked and the other aborts within H. Mark a live job `failed` mid-run and check it stops at the next heartbeat. Stall a replica page past P and check the attempt fails rather than going silent. Let a running lease expire with no worker and check the next click frees the slot.
  7. **Duplicate delivery.** Run the handler twice for one export and check there is one email. Fail only the email and check the row ends `done` with a working Download button.
  8. **Access and retention.** Remove a user's `report.view` and check the status endpoint returns 403 with no filter details. Check a `done` export disappears from the page after 6 days and the download returns 410.
- **Rollout:** ship behind a flag, enable for one workspace, then widen. The flag controls only whether the Download CSV button is shown. The status endpoint, the download endpoint and the job stay on whatever the flag says, so turning it off never strands an in-flight export: it finishes, emails its link, and shows its state on the page.

## Out of scope
Scheduled exports, formats other than CSV, changes to the table on the page, and any cleanup job for old files.

## Open questions
1. **Queue behaviour.** (a) Confirm attempt n+1 never starts while attempt n may still be running; the plan is safe either way, but it wastes work if they overlap. (b) The 2-hour queued lease assumes the queue never waits that long. Confirm with the queue owners.
2. **Nightly rebuild.** A rebuild during a large export could give a mix of old and new rows. This plan does not prevent it. Accept it, or ask the owners of the rebuild job.
3. **Where `reports.row_count` is read from.** Confirm that reading it the way the page does is acceptable under the "never from the primary" rule.
4. **Rate limit on the small path.** Confirm the platform's per-user limit that covers the rows API also covers the export endpoint. If there is none, a simple per-user limit is needed, because the small path keeps no state of its own.