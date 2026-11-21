# Offline product catalogue sync: plan for the field-sales app

## Terms and rules used by every step

- **Anchor**: the server's visible `change_seq` watermark, taken before the first page of a full download. The plan relies on the brief's guarantee that rows become visible in `change_seq` order, so the highest visible value has no gaps below it.
- **Generations**: the local catalogue database has two product tables, `products_a` and `products_b`. One is **active** (browsed by reps, and kept current by incremental sync). The other is **staging** (filled by a full download). The pointer that says which is which lives in `sync_state`, and changing it is the swap.
- **Atomic pairing**: every write of product rows is in the same SQLite transaction as the cursor that records it. Rows are never committed without their cursor, and a cursor is never committed without its rows. A killed app therefore loses at most the page or batch in progress.
- **Single runner**: one sync runner holds a lock. Pages and change batches run one at a time, never in parallel.
- **Idempotent apply**: a product or delete is applied only if the incoming `change_seq` is greater than the stored one. Replaying a batch is therefore harmless.
- **Retry policy** (applies to every request in steps 4, 5, 7, 10 and 11): on a network error or 5xx, retry the same request (same `after_id` or `since`). Waits are 2 s, 4 s, 8 s and 16 s before attempts 2 to 5. After the fifth failed attempt, stop, keep all saved state, and wait for the next trigger. The attempt budget resets when the next trigger starts a run.
- **Other responses**: 4xx other than 410 is not retried. The run stops, state is kept, and the error is logged. 410 `RESYNC_REQUIRED` is not retried either; it triggers a resync (step 10). Token refresh is assumed to be handled by the existing client networking layer.

### Statuses in `sync_state`

`no_catalogue`, `downloading`, `paused_wifi`, `catching_up`, `idle`, `resync_pending` (the active table is still served while staging fills). `resync_pending` is a flag on top of `downloading`, not a separate download path.

## Server contract (three endpoints)

- `GET /v1/catalogue/sync-anchor` returns `{anchor_seq, estimated_product_count}`.
- `GET /v1/catalogue/products?after_id=&limit=500` returns `{items: [{id, change_seq, ...body}], next_after_id, has_more}`. Items are ordered by `id` ascending, use keyset pagination, exclude tombstones, and `limit` is capped at 500.
- `GET /v1/catalogue/changes?since=&limit=1000` returns `{changes: [{change_seq, id, deleted, body?}], next_since, has_more}`. Changes are ordered by `change_seq` ascending. `since` is exclusive. Deleted rows have `deleted: true` and no body. The endpoint returns HTTP 410 with `RESYNC_REQUIRED` when `since` is older than the retained window.

Each row carries its current `change_seq`, so the feed returns each product's latest state, at most once per product per response.

---

## Step 1. Server contract and purge horizon

- **Starts**: deployment of the three endpoints.
- **Data moved**: none at deploy time.
- **State**: the server keeps no per-device session. The tombstone purge job records a *purge horizon*, the highest `change_seq` whose tombstone has been removed. The changes endpoint returns 410 for any `since` below that horizon, because deletes below it can no longer be reported. Indexes are needed on `change_seq` (feed) and `id` (keyset pages).
- **On failure**: if the anchor cannot be computed, the client gets an error and stores nothing. If the purge horizon is not recorded, deletes can be silently lost, so the purge job must not ship without it.

## Step 2. Local catalogue store

- **Starts**: first launch of the version that includes this feature, before any sync runs.
- **Data moved**: none.
- **State**: create `catalogue.sqlite` in WAL mode with `products_a`, `products_b` (`id` primary key, `change_seq`, `body`) and `sync_state` (key/value). The existing settings database is not touched, so catalogue size and locking never affect user settings.
- **On failure**: if the file cannot be created, the catalogue feature is disabled for this session and settings keep working. Creation is retried at the next launch.

## Step 3. Dispatcher

- **Starts**: app launch (including cold start after a kill or reboot), return to foreground, and a network change to Wi-Fi. This is the only entry point; every other step is started from here or from the step before it.
- **Data moved**: none; it reads `sync_state`.
- **Logic**:
  1. If status is `downloading` or `catching_up`, resume at step 11. No 15-minute throttle applies.
  2. Else if an active generation exists and status is `idle`, run incremental sync (step 9) only if `last_run_started_at` is more than 15 minutes ago.
  3. Else if no active generation exists, start a first download (step 4).
- **State**: reads only.
- **On failure**: if `sync_state` or the catalogue file cannot be opened, mark the catalogue unavailable and retry at the next trigger. Never delete data automatically.

## Step 4. Start or restart a full download into staging

- **Starts**: step 3 with no active generation, step 10 on `RESYNC_REQUIRED`, or step 11 when the anchor probe returns 410.
- **Gate**: the device must be on Wi-Fi. Before starting, check free storage. The estimate is `estimated_product_count` times about 2 KB, plus margin, which is about 800 MB before index overhead for 400,000 products. When resyncing, the active generation stays on disk, so the requirement is roughly double. If space is short, stop and tell the rep before any download starts.
- **Data moved**: one small request, `GET /sync-anchor`.
- **State**: after the response arrives, one transaction clears the inactive table, sets `staging_gen` to it, and stores `anchor_seq`, `estimated_product_count`, `last_id = null`, `pages_done = 0`, `status = downloading`, and `resync_pending` if this is a resync. The active table is not touched.
- **On failure**: the anchor request follows the retry policy. Nothing is stored until a response arrives. If the app is killed before the transaction commits, the previous state is unchanged. During a resync, reps keep seeing the active table.

## Step 5. Fetch and save one product page (repeats)

- **Starts**: step 4 has committed, or the previous page has committed, or step 11 resumes the download.
- **Gate**: before each request, check for Wi-Fi. If there is none, set `paused_wifi` and stop without sending the request (step 6).
- **Data moved**: `GET /products?after_id=<last_id>&limit=500`, about 500 x 2 KB, or roughly 1 MB per page.
- **State**: one transaction upserts each item into the staging table (guarded by `change_seq`), sets `last_id = next_after_id`, and increments `pages_done`. If `has_more` is true, repeat. If false, go to step 7.
- **Cellular rule**: if Wi-Fi drops while a request is in flight, let that request finish and save its page, then pause at the next gate. If the in-flight request fails, the retry in step 12 checks for Wi-Fi before each retry and pauses instead of retrying on cellular.
- **On failure**: a network error or 5xx retries the same `after_id`, which is safe because the request is idempotent. A 4xx stops the run. If the app is killed before the commit, the page is lost, and the download resumes by re-requesting from the last committed `last_id`. A half-saved page is never visible. Resume is never from page 1.

## Step 6. Pause on cellular and resume on Wi-Fi

- **Starts**: Wi-Fi is detected again (network-change event), or the app launches or comes to the foreground while Wi-Fi is present.
- **Data moved**: none until step 5 continues.
- **State**: `paused_wifi` with `last_id` and `pages_done` preserved in `sync_state`.
- **On failure**: if Wi-Fi flickers, the gate in step 5 is checked again before every request, so no page is started on cellular.

## Step 7. Catch up on changes made during the download

- **Starts**: step 5 reports `has_more = false`, meaning every page has been saved.
- **Gate**: Wi-Fi, because this is part of the full download.
- **Why it is needed**: the pages show each product as it was when read. Edits to products the walk had already passed, inserts with ids below the cursor, and deletes are only visible in the change feed. Because the anchor was taken before the first page, nothing is missed.
- **Data moved**: `GET /changes?since=<catchup_seq>&limit=1000`, starting with `catchup_seq = anchor_seq`. Each batch is applied to the staging table: upserts, and deletes that remove the row.
- **State**: each batch commits together with `catchup_seq = next_since`. When `has_more` is false, go to step 8. The catch-up keeps going while the server head moves, and stops when a response says there is nothing more.
- **On failure**: 410 means the staging copy cannot be completed. Discard it and restart at step 4 with a new anchor. The active table is untouched. Network or 5xx errors follow step 12. On resume, batches already committed are kept and the catch-up continues from `catchup_seq`.

## Step 8. Swap to the new generation

- **Starts**: step 7 reports caught up.
- **Data moved**: none.
- **State**: one transaction sets `active_gen = staging_gen`, `incremental_cursor = catchup_seq`, `staging_gen = null`, `status = idle`, and clears `resync_pending`. After commit, browsing reads the new table.
- **Reps**: before the commit they see the previous active table, or nothing on a first download (see Open question 1).
- **On failure**: if the app is killed before the commit, staging is complete but not active. On restart, status is `catching_up`, step 7 runs from `catchup_seq`, returns `has_more = false` almost immediately, and the swap runs again. If the app is killed after the commit, step 9 cleans up.

## Step 9. Incremental sync

- **Starts**: app launch or foreground (step 3), with status `idle`, an active generation present, and `last_run_started_at` more than 15 minutes ago. Any network may be used. This never runs while a download is in progress, because step 7 covers that case.
- **Throttle**: `last_run_started_at` is written when the run starts. A run that fails still counts, so repeated foregrounding cannot cause repeated requests (see Open question 3).
- **Data moved**: `GET /changes?since=<incremental_cursor>&limit=1000`. Each batch applies upserts and deletes (tombstones remove the row) to the active table. Repeat while `has_more` is true.
- **State**: each batch commits with `incremental_cursor = next_since`. A run that stops midway keeps every committed batch, and the next run continues from the cursor.
- **On failure**: network or 5xx follows step 12. If the budget is spent, stop and wait for the next trigger after the 15-minute window. A 410 `RESYNC_REQUIRED` sets `resync_pending`, leaves the active table in place, and starts step 4. Reps keep seeing the existing catalogue until the replacement is complete.

## Step 10. Resync handoff

- **Starts**: step 9 receives 410 (`RESYNC_REQUIRED`), or step 11 receives 410 on its anchor probe.
- **Data moved**: none beyond step 4.
- **State**: `resync_pending = true`. The active generation is kept and still served. Staging is cleared and refilled from step 4.
- **On failure**: the failure path of step 4 applies. The active table is never removed until step 8 has committed.

## Step 11. Resume an interrupted full download

- **Starts**: cold start after a kill or reboot, network recovery, Wi-Fi returning, or foreground (step 3).
- **Gate**: Wi-Fi.
- **Data moved**: one probe, `GET /changes?since=<anchor_seq>&limit=1`, to confirm the anchor is still inside the retained window. This catches a download that has been away for more than 7 days early, before hours of pages are fetched. A 410 goes to step 4 (discard staging and restart). A success continues from the saved state.
- **State**: read `status`, `last_id`, `pages_done`, `catchup_seq`. Continue at step 5 if pages remain, or at step 7 if all pages are saved.
- **On failure**: a probe network error or 5xx follows step 12. Nothing in the active table is touched in any case.

## Step 12. Retry and failure handling (shared rule)

- **Starts**: any request in steps 4, 5, 7, 9 or 11 fails with a network error or 5xx.
- **Logic**: retry the same request after 2 s, 4 s, 8 s and 16 s, for at most five attempts in total. Before each retry, if the job is a full download and the device is not on Wi-Fi, pause at step 6 without spending the attempt.
- **Data moved**: none of its own. It repeats the request that failed.
- **State**: nothing is rolled back. Committed pages and batches stay. Status is unchanged (`downloading`, `catching_up` or `idle`).
- **After the fifth failure**: stop the run and wait for the next trigger. Staging is not discarded, the active table is not touched, and the next trigger resumes from the saved cursor.

---

## Open questions (not decided here)

1. **Browsing during a first download.** Product has not decided whether reps may browse the partly downloaded catalogue or should see a progress screen until step 8 completes. This plan only reads the active table. Until step 8 there is no active table on a first download, so the read path must go through the decision. If partial browsing is allowed, reads would come from staging during steps 5 and 7, and the visible set would be incomplete and ordered by id. That needs a product decision before the read path is built.
2. **Storage peak during a resync.** The active and staging generations are both on disk, roughly doubling the footprint (about 1.6 GB or more for 400,000 products). Product and engineering need to accept this, or choose another approach. The plan does not remove the requirement that reps keep seeing the existing catalogue until the replacement is ready.

## Assumptions to confirm

3. **Throttle after a failed run.** The plan counts failed incremental runs toward the 15-minute throttle, so repeated foregrounding cannot cause repeated retry bursts. The alternative is to let the next trigger run immediately, at the cost of more requests.
4. **Other errors.** 401 and token refresh are assumed to be handled by the existing client layer. 4xx responses other than 410 are not retried and are logged for investigation.
5. **Visibility guarantee.** The plan relies on the brief's guarantee that `change_seq` values become visible in order. If that stops holding, the anchor must be computed as the lowest in-flight `change_seq` minus one, not the highest visible value.
6. **Platform Wi-Fi signal.** "Wi-Fi" means the platform's Wi-Fi transport (iOS path monitor interface type Wi-Fi, Android `TRANSPORT_WIFI`), not merely "not cellular".