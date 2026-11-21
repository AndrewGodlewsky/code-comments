# Offline product catalogue sync: plan

## What this is

The field-sales app keeps a full local copy of the product catalogue (about 400,000 products, about 2 KB each) so reps can browse and quote offline. The first download fills a new copy in pages, in the background, and reps switch to it in one step only when it is complete and up to date. After that, the app fetches the small list of changes since its last check and applies them.

## How the system works today

- The Catalogue service stores products in Postgres, a server database. Every insert, update or delete stamps the row with `change_seq`, a number from one global sequence that only goes up. Rows become visible in `change_seq` order, so every value at or below the current maximum is already committed.
- Deletes are soft. A deleted product stays as a tombstone (a row marked `deleted = true`). Tombstones are purged after 7 days.
- The app has a local SQLite database, a small database file on the phone, used for user settings. This plan does not change it.
- There is no sync API yet. This plan designs the endpoints.

## Terms

- **Product**: one catalogue item, with an `id` and its data.
- **change_seq**: the server number on each change. A bigger number is a later change.
- **Change feed**: the server's list of changes, in `change_seq` order, that the app reads to catch up.
- **Tombstone**: the server row for a deleted product, kept for 7 days.
- **Generation**: one complete local copy of the catalogue, numbered `N`. The **active generation** is the copy reps read. A **staging generation** is the copy being built.
- **Swap**: making the staging generation the active one, in one transaction.
- **H0** (snapshot sequence): the highest `change_seq` at the moment a full download starts.
- **since** (cursor): the `change_seq` up to which a generation has applied changes.
- **after_id**: the id of the last product saved by a download. The next page starts after it.
- **Keyset pagination**: each page asks for ids greater than the last id received, instead of counting rows to skip.
- **purge_floor**: the highest `change_seq` whose tombstone the server has purged. A `since` below it is too old to use.
- **Resync required**: the server's HTTP 410 answer with `code: resync_required`. It means the app's cursor is too old, so a full download is needed.
- **WAL mode**: a SQLite setting (write-ahead log) that makes writes safer and lets reads continue during a write.

## Server contract

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /v1/catalogue/snapshot` | Capture `H0` before the first page | `{ snapshot_seq }`, the current maximum committed `change_seq` |
| `GET /v1/catalogue/products?after_id=A&limit=500` | Full download page | Live products with `id > A`, ordered by id ascending, excluding tombstones. Returns `items`, `next_after_id`, `has_more`. Keyset pagination on the id index. |
| `GET /v1/catalogue/changes?since=S&limit=1000` | Change feed | Changes with `change_seq > S`, ascending. Each item is `{ change_seq, product_id, op: upsert or delete, product? }`. Returns `next_since` and `has_more`. |

Server rules:

- The change feed uses each row's **current** `change_seq`, so a product appears once, at its latest position. An `upsert` carries the row's current state. A tombstone is sent as `delete`.
- The server keeps `purge_floor`. If `S < purge_floor`, the changes endpoint returns **HTTP 410** with `code: resync_required`.
- A purge happens 7 days after deletion. A download whose H0 is at most 7 days old therefore never loses a delete that happened after H0.

## Local storage

The app keeps the catalogue in a separate SQLite file, `catalogue.db`, in WAL mode.

- `product(gen, id, payload, PRIMARY KEY(gen, id))`: the products. Every read filters on `gen = active_gen`.
- `generation(gen PRIMARY KEY, status, snapshot_seq, after_id, since_seq, updated_at)`: one row per copy. Status is `downloading`, `catching_up`, `active` or `retired`.
- `meta(key, value)`: holds `active_gen` and `last_incremental_started_at`. Both survive restarts.

## Shared rules

**Apply rule.** Used by steps 7 and 10. Process changes in `change_seq` order, one transaction per batch. Store the new cursor in the same transaction.

- `upsert`: insert or replace the row keyed by `(gen, product_id)`.
- `delete`: remove the row keyed by `(gen, product_id)`.

Replaying a change is safe. Each change carries the row's latest state, or is a delete, so a replay ends in the same result.

**Retry policy.** Applies to every request. After a network error or a 5xx response, retry after waits of 2 s, 4 s, 8 s and 16 s. That is at most 5 attempts in total. The backoff timer runs only while on Wi-Fi during a full download, so it pauses on cellular and resumes on Wi-Fi. After the fifth failure, the worker stops, keeps all saved state, and waits for the next trigger. 4xx responses and 410 are not retried.

## Steps

Each step names its trigger, what it does, which data moves, where its state is kept, and what happens on failure.

### 1. Trigger and gate the sync worker

- **Triggers:** app launch, return to foreground, Wi-Fi becoming available (this resumes a paused download), or a resync signal from step 9.
- **Gates:**
  - Full-download work (steps 2 to 9, including catch-up) runs only on Wi-Fi.
  - Incremental sync (step 10) runs on any network. It is skipped if `last_incremental_started_at` is less than 15 minutes ago.
  - One worker runs per device and sends one request at a time, so pages are never fetched in parallel.
- **Data moved:** none. **State:** `meta`.
- **Failure:** if the worker is already running, a new trigger only sets a "re-check" flag. The running worker re-reads state before it stops.

### 2. Start a full download and capture the snapshot

- **Trigger:** there is no active generation (first install), or step 9 requires a rebuild.
- **Action:**
  1. Check free storage. A rebuild needs room for a second full copy, about 0.8 GB of data plus indexes. If there is not enough room, keep the active generation, record the reason, and stop.
  2. Create generation `N+1` with status `downloading`.
  3. Call `GET /v1/catalogue/snapshot`. In one transaction, store `snapshot_seq = H0`, `after_id = null` and `since_seq = H0`.
- **Why H0 comes first:** any change committed after H0 has `change_seq > H0`, and step 7 replays it. So no edit made during the download is missed.
- **Data moved:** one small response.
- **Failure:** if the snapshot call fails after retries, only the generation row exists. The active generation is untouched. The next trigger repeats this step.

### 3. Fetch one page

- **Trigger:** `generation.status` is `downloading`, and the device is on Wi-Fi.
- **Action:** call `GET /v1/catalogue/products?after_id=A&limit=500`, where `A` is the stored `after_id` (null for the first page). Pages are requested one at a time.
- **Data moved:** up to 500 products, about 1 MB.
- **Failure:** the retry policy applies. If retries run out, `after_id` stays at the last saved page. The next trigger requests the same page again.

### 4. Save each page as one transaction

- **Action:** in one SQLite transaction, upsert the page's rows with `gen = N+1` and set `after_id = next_after_id`. If `has_more` is false, also set status to `catching_up`. Commit. Then go to step 3, or to step 7 if the download is complete.
- **Why:** a page is saved together with its cursor, or not at all. The cursor never gets ahead of the stored rows.
- **Data moved:** the page, about 1 MB. **State:** `product` and `generation`.
- **Failure:**
  - Crash before commit: the transaction rolls back. After restart the page is fetched again from the old `after_id`.
  - Disk full: roll back, leave the status unchanged, and stop until the condition clears.

### 5. Resume after an interruption

- **Triggers:** app killed, phone restarted, network lost.
- **Action:** on the next trigger, read generation `N+1`. If its status is `downloading`, continue at step 3 from the stored `after_id`, with the same H0. The download never restarts from page 1.
- **Why edits made during the outage are safe:** H0 is unchanged, so step 7 still replays everything after it.
- **Failure:**
  - Corrupt staging database: delete generation `N+1` and start again at step 2. The active generation is unaffected.
  - H0 older than 7 days: step 7 gets a 410, which leads to step 9.

### 6. Pause on cellular

- **Action:** before every page request (step 3) and every batch (step 7), the worker checks the network. If the device is not on Wi-Fi, it stops sending requests and waits for a Wi-Fi trigger.
- **Mid-page drop:** a page request already in flight finishes and is saved by step 4. This is "finish the page it is on." No further request is made until Wi-Fi returns.
- **Failure:** a network error during a retry on cellular does not count as an attempt. The backoff resumes on Wi-Fi.

### 7. Catch up on edits made during the download

- **Trigger:** the last page is saved and status is `catching_up`.
- **Action:** call `GET /v1/catalogue/changes?since=S&limit=1000`, starting with `S = H0`. Apply each batch with the apply rule, and store `since_seq = next_since` in the same transaction. Repeat while `has_more` is true.
- **Why this covers the gaps in the pages:**
  - A product inserted after H0 with an id below the paging cursor is never in a page. Its change has `change_seq > H0`, so the replay includes it.
  - A product updated after H0 is replayed with its latest state.
  - A product deleted after H0 is removed, even if an earlier page included it.
  - All pages are saved before catch-up starts, so an older page can never overwrite a newer replay.
- **Data moved:** every change made during the download. The volume depends on how long the download took.
- **Failure:** the retry policy applies, and the download resumes from `since_seq`. A 410 leads to step 9.

### 8. Swap the staging generation to active

- **Trigger:** a changes call returns an empty batch with `has_more = false`. The generation is caught up as of that moment.
- **Action:** in one transaction, set generation `N+1` to `active`, set `meta.active_gen = N+1`, and set generation `N` to `retired`.
- **Result:** reps see the new catalogue all at once. Any change committed after the empty response is picked up by step 10 on the new generation, whose `since_seq` moved with it.
- **Failure:** the swap is one transaction, so it happens fully or not at all. If it fails, generation `N` stays active. Catch-up runs again and returns an empty batch.

### 9. Handle resync required

- **Trigger:** the changes endpoint returns 410 `resync_required`, because `since < purge_floor`.
- **Case A: 410 during catch-up of a staging generation.** Delete that generation's rows, then go to step 2 to build a new one. The active generation is not touched.
- **Case B: 410 on the active generation in step 10.** That generation's cursor is no longer valid, so incremental sync for it stops. Mark generation `N` as needing replacement. Reps keep reading generation `N`, unchanged. No incremental updates reach it until the swap. Then go to step 2.
- **Data moved:** a full download, on Wi-Fi only, following steps 2 to 8.
- **Failure:** the same as a first download. If the storage check fails, keep `N` active and retry on a later trigger.

### 10. Incremental sync (steady state)

- **Triggers:** app launch or return to foreground, on any network. The 15-minute gate in step 1 applies. It runs only when an active generation exists and is not waiting for a rebuild.
- **Action:** write `last_incremental_started_at = now`. Then loop: call `GET /v1/catalogue/changes?since=S&limit=1000`, where `S` is the active generation's `since_seq`. Apply each batch with the apply rule, storing `since_seq = next_since` in the same transaction. Stop when `has_more` is false.
- **Data moved:** normally a few changes per launch.
- **Failure:** the retry policy applies. If retries run out, the worker stops and keeps `since_seq`, so no change is lost. The next trigger after the 15-minute gate resumes from the same cursor. A batch is either fully applied with its cursor or not at all, so a half-applied batch cannot happen.

### 11. Clean up the retired generation

- **Trigger:** after the swap, as a background task.
- **Action:** delete generation `N`'s rows in batches of 500, each batch in its own transaction. Then reclaim space with incremental vacuum (a SQLite step that returns free space to the system) while the device is idle and charging.
- **Why it is safe:** every read filters on `gen = active_gen`, so leftover rows are invisible to reps.
- **Failure:** the task is idempotent and resumes at the next launch. Its only cost is temporary disk use.

## How to test it

Test these against a staging server:

- Kill the app while page 137 is being saved. After restart, the download resumes from the `after_id` stored for page 136, not from page 1.
- Switch to cellular after page 50 is saved. Exactly one more page completes, and no further request is made until Wi-Fi returns.
- During a download, insert, update and delete products, including ids below the paging cursor. Compare the final local state with the server.
- Return 5xx responses four times, then success. The waits must be 2, 4, 8 and 16 s, and the fifth attempt succeeds. Return 5xx five times and confirm the worker stops and keeps its state.
- Age H0 past `purge_floor`. The response is 410, the rebuild runs, and the active catalogue is unchanged throughout.
- Trigger two incremental syncs less than 15 minutes apart. The second is skipped.
- Simulate insufficient storage at the start of a rebuild. The active catalogue must stay readable.

## Risks

- **A download that outlasts the window.** If the device is mostly on cellular, or the download takes more than 7 days, H0 ages past `purge_floor`. Every catch-up then returns 410 and the rebuild repeats indefinitely. Mitigations: measure Wi-Fi availability and the time to complete a download on real devices, and add server metrics for 410s by device.
- **Storage doubling.** A rebuild needs a second full copy while the active one is still readable. The storage check in step 2 is essential.
- **Replay volume.** A long first download means a long catch-up. Batches of 1,000 keep each transaction small.

## Open questions

1. **Browsing during the first download (not decided).** Should reps browse the partly downloaded catalogue, or see a progress screen until the swap? The design supports either. Staging rows are invisible until step 8, so the choice only controls what the UI shows while generation `N+1` is `downloading` or `catching_up`. This plan does not decide it.
2. **Frozen catalogue during a rebuild.** After a resync, generation `N` stops receiving updates until the swap, which can take hours. Should reps see a staleness notice, or is silent staleness acceptable?
3. **Gating catch-up.** Step 7 is exempt from the 15-minute gate because it is part of the download. Product should confirm this.
4. **Storage threshold.** What free-space margin should the rebuild check require? The estimate is about 0.8 GB of data plus indexes per copy, so about 1.6 GB during a rebuild.
5. **Purge clock.** Confirm that the 7-day purge runs from deletion time, so `purge_floor` is the right server signal.
6. **Other status codes.** The spec does not cover 429 or other 4xx responses. This plan does not retry them. Confirm that this is the intended behaviour.