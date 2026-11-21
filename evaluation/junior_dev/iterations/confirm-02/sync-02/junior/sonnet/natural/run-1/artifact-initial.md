# Offline product catalogue sync: implementation plan

## Design summary

**Constants**
- About 400,000 products at about 2 KB each is roughly 800 MB on the device.
- A full download is 800 pages of 500 products, about 1 MB per page before compression.
- Servers should gzip responses.

**Core idea.** `change_seq` is assigned at commit, so rows become visible in `change_seq` order. That makes `MAX(change_seq)` a gap-free high-water mark.

The client records that mark (the **watermark**) before it fetches page 1. It then downloads pages by product id. When the pages are done, it replays every change after the watermark in `change_seq` order. Any edit made during the download is covered one of two ways:
- The edit happened after the page containing that product was read, so the change feed delivers it.
- The edit happened before the page was read, so the page already holds it.

The change feed is applied with a "newer `change_seq` wins" rule, so replaying a change the page already contains does no harm.

**Endpoints (new)**

| Endpoint | Returns |
|---|---|
| `POST /sync/begin` | `{ watermark_seq, server_time }`. `watermark_seq` is the current max committed `change_seq`. |
| `GET /catalogue/products?after_id=<id or empty>&limit=500` | Non-deleted products ordered by `id` ascending, each with its `change_seq`, plus `{ last_id, is_last_page }`. Keyset pagination only, with no offset. |
| `GET /catalogue/changes?after_seq=<n>&limit=1000` | Rows with `change_seq > n`, in `change_seq` order, including tombstones as `{id, deleted:true, change_seq}`. Also returns `{ next_seq, has_more }`. Answers **HTTP 410** with `{"error":"resync_required"}` if `n` is older than the retained tombstones. |

**Client state (local SQLite).** This is kept in the existing database, in new tables.

| Table | Contents |
|---|---|
| `product_g0`, `product_g1` | Two copies of the catalogue (generations). Columns are `id` (PK), `change_seq`, and the payload. |
| `sync_state` (single row) | `active_gen` (0, 1, or none); `live_cursor_seq` (last change applied to the active generation); `last_incremental_attempt_at`; `download_status` (`none` / `running` / `paused_cellular` / `stopped_error` / `draining` / `ready_to_swap`); `download_gen`; `download_watermark_seq`; `download_watermark_taken_at`; `download_last_saved_id`; `download_drain_seq`. |

**Two-generation scheme.** All downloads go into the generation that is not active. Swapping means updating one `sync_state` row inside a single transaction. This avoids copying 800 MB of rows. It also means reps see the old catalogue until the new one is complete. The app reads products from `active_gen` only.

**Assumptions** (flagged where they matter)
- A1. The 15-minute limit counts from the start of the last incremental attempt, stored persistently. It applies to launch and foreground triggers alike.
- A2. A page that has already started is allowed to finish, including its retries, if the network drops to cellular. Its retries are not abandoned just because of the network type.
- A3. Client errors (4xx) other than 410 are not retried. They stop the sync and are logged.
- A4. The first Wi-Fi-only download can continue only while the app is running. Background execution (iOS BGProcessingTask, Android WorkManager) is optional and out of scope for this plan.

## Shared rule: how every request is sent

Every request in every step below goes through this wrapper.

- The wrapper makes up to **5 attempts in total** at the same request.
- It waits 2 s, 4 s, 8 s, then 16 s between attempts. No wait follows the fifth attempt.
- A network error or a 5xx response triggers a retry.
- A 410 on the changes endpoint is not an error. It is the "resync required" answer (step 11).
- After the fifth failure the wrapper reports "gave up". The caller leaves everything already saved untouched. The sync sets its status to `stopped_error` and waits for the next trigger.
- The next trigger is one of the following:
  - app launch;
  - the app returning to the foreground;
  - the network returning to Wi-Fi (full download only).

## Server steps

### 1. Add the sync endpoints and indexes
- **Starts it:** a one-off build task.
- **Data:** none moves yet. Add an index on `change_seq` for the changes feed. The primary key on `id` serves keyset pagination. The page query filters `deleted = false`.
- **State kept:** Postgres only.
- **On failure:** none at runtime.
- **Consistency check:** the begin endpoint reads `MAX(change_seq)` in its own transaction, and page queries are separate read-committed statements. Because rows become visible in `change_seq` order, any row with `change_seq <= watermark` is visible to every page read made after the watermark was returned.

### 2. Record how far tombstone purging has gone
- **Starts it:** the existing 7-day tombstone purge job, each run.
- **Data:** before deleting tombstones, the job stores `purged_through_seq` as the highest `change_seq` among the tombstones it purges. The store is a one-row table.
- **State kept:** Postgres, one row.
- **On failure:** if the job fails, nothing is purged and the value is unchanged. The changes endpoint answers 410 whenever `after_seq < purged_through_seq`. This is the exact test for "older than the tombstone window". It cannot be wrong in the dangerous direction, because a client below that value may have missed a delete.

## Client steps

### 3. Create the local state tables
- **Starts it:** an app update that runs a migration at launch.
- **Data:** create `product_g0`, `product_g1` and `sync_state` (see above). Set `active_gen` to none, `download_status` to `none` and `live_cursor_seq` to null.
- **State kept:** SQLite.
- **On failure:** the migration runs in a transaction. If it fails, the app keeps its existing settings database untouched and retries the migration at the next launch. Sync stays disabled until it succeeds.

### 4. Decide what to do at a trigger
- **Starts it:** app launch, app returns to foreground, or the network changes to Wi-Fi.
- **Data:** read the `sync_state` row. Only one sync runs at a time. If one is already running, the new trigger is ignored.
- **State kept:** the in-memory "sync running" flag, plus `sync_state`.
- **Decision:**
  - If `active_gen` is none and `download_status` is `none`, go to step 5, only if Wi-Fi is on.
  - If a download is in progress (`running`, `paused_cellular`, `stopped_error`, `draining`), go to step 8 (Wi-Fi only for page downloads). Do not run incremental sync, because the live catalogue (if any) would just receive a 410 again. A fresh install with no live catalogue has nothing to update anyway.
  - If `active_gen` is set and no download is in progress, go to step 10, if at least 15 minutes have passed since `last_incremental_attempt_at`.
- **On failure:** an unexpected exception is logged. The flag is cleared so a later trigger can try again.

### 5. Begin a full download
- **Starts it:** step 4, when the app has no catalogue and Wi-Fi is on. Also step 11 (resync) and step 12 (stale watermark).
- **Data:** one `POST /sync/begin`. The response gives `watermark_seq`.
- **State kept:** in one transaction, write to `sync_state`: `download_gen` (the generation that is not active, or 0 on first run), `download_watermark_seq`, `download_watermark_taken_at`, `download_last_saved_id = null`, `download_drain_seq = download_watermark_seq` and `download_status = running`. Empty the target generation's table first, inside the same transaction.
- **On failure:** if the request gives up, nothing is written. The next trigger starts again at this step. If the transaction fails, the state is unchanged. Before starting a resync, check that free disk space is at least about 1 GB beyond the live catalogue. If it is not, do not start. Show the existing catalogue and log the reason. Mark this as an open question (see below).

### 6. Download pages, one at a time
- **Starts it:** step 5 completing, or step 8 resuming.
- **Data:** repeat the following until `is_last_page`:
  1. Check the network. If it is not Wi-Fi, go to step 7. This check is made only before starting a page.
  2. Request `GET /catalogue/products?after_id=<download_last_saved_id>&limit=500`, using the shared wrapper. The request is never sent in parallel with another page.
  3. Save the 500 rows (upsert by `id`, keeping the row with the higher `change_seq`) and set `download_last_saved_id` to the last id in the page, **in one SQLite transaction**.
- **State kept:** `download_last_saved_id` is the resume point. It advances only when its page is fully saved.
- **On failure:**
  - A failed request that gives up after 5 attempts sets `download_status = stopped_error`. All saved pages remain. The next trigger resumes at step 8.
  - A crash after the response arrives but before the transaction commits loses that page. It is fetched again on resume, which is harmless because the save is an upsert.
  - If the save transaction itself fails (for example the disk is full), stop with `stopped_error`. Do not advance the cursor.
  - A 4xx other than 410 stops with `stopped_error` and is logged (A3).

### 7. Pause on cellular, resume on Wi-Fi
- **Starts it:** the network type becomes cellular while a download is running.
- **Data:** none.
- **State kept:** `download_status = paused_cellular`. The page in progress is allowed to finish and be saved (A2). Then no further page is requested. On a return to Wi-Fi, step 4 fires and the download resumes through step 8. While paused, incremental sync does not run, because a download is in progress (step 4). Incremental sync may use any network once the download has finished.
- **On failure:** if the in-progress page gives up while on cellular, it is treated as in step 6: `stopped_error`. The next Wi-Fi trigger resumes. If the app is killed while paused, the stored status resumes via step 8.

### 8. Resume an interrupted download
- **Starts it:** step 4, when `download_status` is `running`, `paused_cellular`, `stopped_error` or `draining`. This includes the first launch after the app was killed, the phone restarted, or the network was lost. On a launch, a stored status of `running` means the previous run died.
- **Data:** none. The client reads `download_last_saved_id` and `download_watermark_taken_at`.
- **State kept:** `sync_state`. If the watermark is older than 6 days, treat it as stale and go to step 12. Otherwise, if the status is `draining` or `ready_to_swap`, continue at step 9. If not, continue at step 6 from `download_last_saved_id`, not from page 1. Page downloads happen only when Wi-Fi is on. If it is not, stay paused.
- **On failure:** the same as step 6.

### 9. Catch up and swap in the new catalogue
- **Starts it:** step 6 receiving the last page, or step 8 resuming a drain.
- **Data:**
  1. Set `download_status = draining`.
  2. Loop `GET /catalogue/changes?after_seq=<download_drain_seq>&limit=1000`, starting at `download_watermark_seq`, until `has_more` is false. Allow any network for this loop.
  3. For each response, in one transaction, apply the changes to the **download** generation and save `download_drain_seq`.
  4. Rule for each change: apply it only if its `change_seq` is greater than or equal to the stored row's. An upsert for a normal change. A delete removes the row if present and does nothing if absent.
  5. When `has_more` is false, set `download_status = ready_to_swap`.
  6. Then, in **one transaction**, set `active_gen = download_gen`, set `live_cursor_seq = download_drain_seq`, and set `download_status = none`. The reps now see the new catalogue.
  7. In the background, empty the old generation to free space.
- **State kept:** the drain cursor persists with each batch. A crash during draining resumes at the saved drain cursor.
- **On failure:**
  - A request that gives up leaves `download_status = draining`. Nothing is swapped. The next trigger resumes the drain through step 8.
  - If the feed answers **410** because the download took long enough for the watermark to fall outside the tombstone window, go to step 12.
  - A crash after the swap transaction commits is safe, because the swap is one transaction. A crash before it leaves the old catalogue active.

### 10. Incremental sync
- **Starts it:** app launch or foreground (step 4), at most once every 15 minutes (A1), and only when `active_gen` is set and no download is in progress.
- **Data:**
  1. Store `last_incremental_attempt_at = now` before the first request.
  2. Loop `GET /catalogue/changes?after_seq=<live_cursor_seq>&limit=1000` on any network, until `has_more` is false.
  3. For each response, in one transaction, apply the changes to the active generation (the same rule as step 9) and set `live_cursor_seq` to `next_seq`.
- **State kept:** `live_cursor_seq`, committed together with the changes it covers.
- **On failure:**
  - After a request gives up, stop. Everything applied so far stays, and the cursor sits at the last committed response. The next trigger (at least 15 minutes later) continues from there.
  - A 410 goes to step 11.
  - A crash between responses is safe, because the cursor is advanced in the same transaction as the changes.

### 11. Resync required
- **Starts it:** a 410 from the changes endpoint in step 10.
- **Data:** none yet.
- **State kept:** the live generation and `live_cursor_seq` are left alone. Reps keep seeing the existing catalogue.
- **Action:** if Wi-Fi is on, go to step 5, which downloads into the inactive generation. If it is not, leave `download_status = none` and start the download when Wi-Fi returns. Do not run incremental sync while the replacement download is in progress (step 4). The swap happens only in step 9.
- **On failure:** the same as steps 5 to 9. An abandoned replacement download never affects the active generation.

### 12. Watermark too old during a download
- **Starts it:** step 8 (watermark older than 6 days) or step 9 (the feed answers 410).
- **Data:** none.
- **State kept:** discard the partial download. Empty the target generation. Set `download_status = none`. Keep the active generation.
- **Action:** go to step 5 for a new full download with a fresh watermark. This is the only case where a download restarts from page 1.
- **On failure:** the same as step 5.

## Open question for Product (not decided here)

**Can reps browse the partly downloaded catalogue during their first download, or should they see a progress screen until it finishes?**

This plan does not decide it. It only makes both options possible:
- If browsing is allowed, the app reads the download generation during the first run. That generation holds only products with ids up to `download_last_saved_id`, so search and browse results would be incomplete and quotes could miss products. It also contains rows that the drain step has not yet corrected.
- If a progress screen is required, the app reads only `active_gen` and shows progress as `download_last_saved_id` against the total.

Either way, steps 5 to 9 are the same. Only what the UI reads differs.

## Other open items to confirm
- Free-disk-space threshold, and the message to show when a resync cannot start (step 5).
- Whether background download is required (A4).
- How "Wi-Fi" is detected, for example a phone hotspot or a metered Wi-Fi network.
- Whether launch should bypass the 15-minute limit (A1).
