# Offline product catalogue sync: plan

## Context and assumptions

- The Catalogue service stores about 400,000 products in Postgres. Each insert, update or delete stamps the row with a global `change_seq`, assigned at commit. Rows become visible in `change_seq` order, so every value at or below the current maximum is already committed.
- Deletes are soft tombstones, purged 7 days after deletion.
- The device keeps the catalogue in a **separate SQLite file** (`catalogue.db`). The existing settings database is not touched.
- Reads come from one **active generation** of the catalogue. A full download writes into a **staging generation** and becomes active in one transaction (the "swap"). Reps see the old catalogue until the swap.
- Terms: `H0` is the snapshot sequence captured at the start of a full download. `since` is the change-feed cursor.

## Server contract

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /v1/catalogue/snapshot` | Capture `H0` before the first page | `{ snapshot_seq }`, the current maximum committed `change_seq` |
| `GET /v1/catalogue/products?after_id=A&limit=500` | Full download page | Live products with `id > A`, ordered by id ascending, excluding tombstones. Returns `items`, `next_after_id`, `has_more`. Keyset pagination on the id index. |
| `GET /v1/catalogue/changes?since=S&limit=1000` | Change feed | Changes with `change_seq > S`, ascending. Each item is `{ change_seq, product_id, op: upsert or delete, product? }`. Returns `next_since` and `has_more`. |

Server rules:

- The change feed is keyed on each row's **current** `change_seq`, so a product appears once, at its latest position. An `upsert` carries the row's current state. A tombstone is sent as `delete`.
- The server keeps `purge_floor`, the highest `change_seq` whose tombstone has been purged. If `S < purge_floor`, the changes endpoint returns **HTTP 410** with `code: resync_required`.
- A purge is 7 days after deletion. A download whose `H0` is at most 7 days old therefore never loses a delete that happened after `H0`.

## Shared rules

**Apply rule** (used by steps 7 and 10). Process changes in `change_seq` order, inside one transaction per batch, and advance the generation's cursor in the same transaction:

- `upsert`: insert or replace the row keyed by `(gen, product_id)`.
- `delete`: remove the row keyed by `(gen, product_id)`.

Replaying a change is safe. Each change carries the row's latest state, or is a delete, so replay converges to the same result.

**Retry policy** (applies to every request). A network error or 5xx response is retried after waits of 2 s, 4 s, 8 s and 16 s. That is at most 5 attempts in total. The backoff timer runs only while on Wi-Fi during a full download, so it pauses on cellular and resumes on Wi-Fi. After the fifth failure, the worker stops, keeps all saved state, and waits for the next trigger. 4xx responses and 410 are not retried.

**Local state** (`catalogue.db`, WAL mode):

- `product(gen, id, payload, PRIMARY KEY(gen, id))`. Every read filters on `gen = active_gen`.
- `generation(gen PRIMARY KEY, status, snapshot_seq, after_id, since_seq, updated_at)`, where status is `downloading`, `catching_up`, `active` or `retired`.
- `meta(key, value)`, holding `active_gen` and `last_incremental_started_at`. Both survive restarts.

## Steps

### 1. Trigger and gate the sync worker

- **Triggers:** app launch, return to foreground, Wi-Fi becoming available (resumes a paused download), or a resync signal from step 9.
- **Gates:**
  - Full-download work (steps 2 to 9, including catch-up) runs only on Wi-Fi.
  - Incremental sync (step 10) runs on any network. It is skipped if `last_incremental_started_at` is less than 15 minutes ago.
  - One worker per device issues **one request at a time**, so pages are never fetched in parallel.
- **Data moved:** none.
- **State:** `meta`.
- **Failure:** if the worker is already running, a new trigger only sets a "re-check" flag. The running worker re-reads state before it stops.

### 2. Start a full download and capture the snapshot

- **Starts when:** there is no active generation (first install), or step 9 requires a rebuild.
- **Action:**
  1. Check free storage. A rebuild needs room for a second full copy, roughly 0.8 GB of data plus indexes. If there is not enough room, keep the active generation, record the reason, and stop.
  2. Create generation `N+1` with status `downloading`.
  3. Call `GET /snapshot` and store `snapshot_seq = H0`, `after_id = null`, `since_seq = H0`, all in one transaction.
- **Why `H0` comes first:** any change committed after `H0` has `change_seq > H0`. Step 7 replays it, so no edit made during the download is missed.
- **Data moved:** one small response.
- **Failure:** if the snapshot call fails after the retries, only the generation row exists. The active generation is untouched. The next trigger repeats this step.

### 3. Fetch one page

- **Starts when:** `generation.status = downloading`, and the device is on Wi-Fi.
- **Action:** call `GET /products?after_id=A&limit=500`, where `A` is the stored `after_id`. Pages are requested one at a time.
- **Data moved:** up to 500 products, about 1 MB.
- **Failure:** the retry policy applies. If retries are exhausted, the stored `after_id` stays at the last saved page. The next trigger requests the same page again.

### 4. Save each page as one transaction

- **Action:** in one SQLite transaction, upsert the page's rows with `gen = N+1`, set `after_id = next_after_id`, and, if `has_more` is false, set status to `catching_up`. Commit, then go to step 3 or step 7.
- **Why:** a page is either saved together with its cursor, or not at all. The cursor never gets ahead of the stored rows.
- **Failure:**
  - Crash before commit: the transaction rolls back. After restart the page is fetched again from the old `after_id`.
  - Disk full: roll back, leave the status unchanged, and stop until the condition clears.

### 5. Resume after an interruption

- **Triggers:** app killed, phone restarted, network lost.
- **Action:** on the next trigger, read generation `N+1`. If its status is `downloading`, continue at step 3 from the stored `after_id` with the same `H0`. The download never restarts from page 1.
- **Why edits made during the outage are safe:** `H0` is unchanged, so step 7 still replays everything after it.
- **Failure:**
  - Corrupt staging database: delete generation `N+1` and start again at step 2. The active generation is unaffected.
  - Staging older than 7 days: step 7 gets a 410, which leads to step 9.

### 6. Pause on cellular

- **Action:** the worker checks the network before every page request in step 3 and every batch in step 7. If the device is not on Wi-Fi, it stops issuing requests and waits for a Wi-Fi trigger.
- **Mid-page drop:** a page request already in flight is allowed to finish and is saved by step 4. This matches "finish the page it is on." No further request is made until Wi-Fi returns.
- **Failure:** a network error during a retry on cellular does not count as an attempt. The backoff resumes on Wi-Fi.

### 7. Catch up on edits made during the download

- **Starts when:** the last page is saved and status is `catching_up`.
- **Action:** call `GET /changes?since=S&limit=1000`, starting with `S = H0`. Apply each batch with the apply rule, and store `since_seq = next_since` in the same transaction. Repeat while `has_more` is true.
- **Why this covers the gaps in pages:**
  - A product inserted after `H0` with an id below the paging cursor is never in a page. Its change has `change_seq > H0`, so the replay includes it.
  - A product updated after `H0` is replayed with its latest state.
  - A product deleted after `H0` is removed, even if an earlier page had included it.
  - All pages are saved before catch-up begins, so an older page can never overwrite a newer replay.
- **Data moved:** every change made during the download. The volume depends on how long the download takes.
- **Failure:** the retry policy applies, and the download resumes from `since_seq`. A 410 leads to step 9.

### 8. Swap the staging generation to active

- **Trigger:** a changes call returns an empty batch with `has_more = false`. The generation is caught up as of that moment.
- **Action:** in one transaction, set generation `N+1` to `active`, set `meta.active_gen = N+1`, and set generation `N` to `retired`.
- **Result:** reps see the new catalogue all at once. Any change committed after the empty response is picked up by step 10 on the new generation. Its `since_seq` moved with it.
- **Failure:** the swap is a single transaction, so it either happens fully or not at all. If it fails, generation `N` stays active. Catch-up runs again and returns an empty batch.

### 9. Handle resync required

- **Trigger:** the changes endpoint returns 410 `resync_required`, because `since < purge_floor`.
- **Case A, 410 during catch-up of a staging generation:** delete that generation's rows, then go to step 2 to build a new one. The active generation is not touched.
- **Case B, 410 on the active generation in step 10:** the active generation's cursor is no longer valid, so incremental sync for it stops. Mark generation `N` as needing replacement. Reps keep reading generation `N`, unchanged, and no incremental updates reach it until the swap. Then go to step 2.
- **Data moved:** a full download, on Wi-Fi only, following steps 2 to 8.
- **Failure:** the same as a first download. If the storage check fails, keep `N` active and retry on a later trigger.

### 10. Incremental sync (steady state)

- **Triggers:** app launch or return to foreground, on any network. Skipped if `last_incremental_started_at` is less than 15 minutes ago. Only runs when an active generation exists and is not waiting for a rebuild.
- **Action:** write `last_incremental_started_at = now`. Then loop: call `GET /changes?since=S&limit=1000`, where `S` is the active generation's `since_seq`. Apply each batch with the apply rule, storing `since_seq = next_since` in the same transaction. Stop when `has_more` is false.
- **Data moved:** normally a few changes per launch.
- **Failure:** the retry policy applies. If retries are exhausted, the worker stops and keeps `since_seq`, so no change is lost. The next trigger, after the 15-minute gate, resumes from the same cursor. A batch is either fully applied with its cursor or not at all, so a half-applied batch cannot happen.

### 11. Clean up the retired generation

- **Trigger:** after the swap, as a background task.
- **Action:** delete the rows of generation `N` in batches of 500, each in its own transaction. Then reclaim space with incremental vacuum while the device is idle and charging.
- **Why it is safe:** every read filters on `gen = active_gen`, so leftover rows are invisible to reps.
- **Failure:** the task is idempotent and resumes at the next launch. Its only cost is temporary disk use.

### 12. Verify the plan

Test these scenarios against a staging server:

- Kill the app while page 137 is being saved. After restart, the download resumes from the `after_id` stored for page 136, not from page 1.
- Switch to cellular after page 50 is saved. Exactly one more page completes, and no further request is made until Wi-Fi returns.
- During a download, insert, update and delete products, including ids below the paging cursor. Compare the final local state with the server.
- Return 5xx responses four times, then success. The waits must be 2, 4, 8 and 16 s, and the fifth attempt succeeds. Return 5xx five times and confirm the worker stops and keeps its state.
- Age `H0` past `purge_floor`. The response is 410, the rebuild runs, and the active catalogue is unchanged throughout.
- Trigger two incremental syncs less than 15 minutes apart. The second is skipped.
- Simulate insufficient storage at the start of a rebuild. The active catalogue must stay readable.

## Open questions

1. **Browsing during the first download (not decided).** Should reps browse the partly downloaded catalogue, or see a progress screen until the swap? The design supports either option. Staging rows are invisible until step 8, so the choice only controls what the UI shows while generation `N+1` is `downloading` or `catching_up`. This plan does not decide it.
2. **Frozen catalogue during a rebuild.** After a resync, generation `N` stops receiving updates until the swap, which can take hours. Should reps see a staleness notice, or is silent staleness acceptable?
3. **Gating catch-up.** The plan exempts step 7 from the 15-minute throttle because it is part of the download. Product should confirm this.
4. **Storage threshold.** What free-space margin should the rebuild check require? The estimate is roughly 0.8 GB of data plus indexes per copy, so about 1.6 GB during a rebuild.
5. **Purge clock.** Confirm that the 7-day purge runs from deletion time, so that `purge_floor` is the right server signal.
6. **Other status codes.** The spec does not cover 429 or other 4xx responses. This plan does not retry them. Confirm that is the intended behaviour.

## Risks

- **A download that outlasts the window.** If the device is mostly on cellular, or the download takes more than 7 days, `H0` ages past `purge_floor`. Every catch-up then returns 410 and the rebuild repeats indefinitely. Mitigations: measure Wi-Fi availability and the time to complete a download on real devices, and add server metrics for 410s by device.
- **Storage doubling.** A rebuild needs a second full copy while the active one is still readable. The storage check in step 2 is essential.
- **Replay volume.** A long first download means a long catch-up. Batches of 1,000 keep each transaction small.
