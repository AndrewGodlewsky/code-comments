# Offline product catalogue sync: plan for the field-sales app

## What this plan does

The field-sales app (iOS and Android) keeps the full product catalogue on the phone, so reps can browse and quote while offline. The catalogue has about 400,000 products of about 2 KB each. The plan covers two things:

1. A **first full download**. It must survive interruptions: the app being killed, the phone restarting, or the network dropping.
2. **Incremental updates** after that. They fetch only what changed.

## Background for readers new to this system

**Parts of the system**

- **Catalogue service**: the server that stores products in Postgres, a database server.
- **Device database**: the app already has a local SQLite database, a single-file database on the phone, used for user settings. The catalogue gets its own separate SQLite file, so large catalogue writes cannot slow down or lock the settings.
- **WAL mode**: a SQLite setting that lets reads continue while a write is in progress.

**Words used in the plan**

- **`change_seq`**: every insert, update or delete of a product stamps that product's row with a number from one global counter. The counter only goes up. The number is given when the change is committed, and readers see changes in `change_seq` order. So if the highest visible number is N, every change numbered below N is also visible. There are no gaps.
- **Tombstone**: a soft delete. The row stays in the database with `deleted = true`, so clients can learn that a product was removed. Tombstones are purged after 7 days.
- **Purge horizon**: the highest `change_seq` whose tombstone has been purged. A request for changes from before this point cannot be answered in full, because some deletes are gone.
- **Keyset pagination**: a page is requested as "the next 500 products with an id after X", not by page number. Each page is quick, and asking for the same page again is safe.
- **Cursor**: a saved position in a download or feed, such as the last product id saved or the last `change_seq` applied. Cursors are stored on the device so work can resume.
- **Transaction**: a group of writes that are saved together or not at all.
- **Upsert**: insert the row if it is new, or update it if it exists.
- **Idempotent**: running the same step twice gives the same result as running it once.
- **HTTP status codes**: 5xx means a server error. 4xx means the client sent something the server rejected. 410 (here, `RESYNC_REQUIRED`) means the server can no longer answer from the requested position. A **network error** means no response arrived at all.
- **Wi-Fi**: the phone's Wi-Fi connection itself, not just "not cellular". See Assumption 4.

## Terms used by every step

- **Anchor**: the server's `change_seq` value, read once before the first page of a full download. The pages show products as they are when each page is read. Changes made after the anchor are not necessarily in the pages, so the change feed (step 7) covers everything after the anchor. Because changes become visible in order, no change falls between the two.
- **Generations**: the local catalogue has two product tables, `products_a` and `products_b`. At any time:
  - One is **active**. Reps browse it, and incremental sync keeps it current.
  - One is **staging**. A full download fills it. It is empty or unused when no download is running.
  - The table that is neither active nor staging is the **inactive** table.

  A pointer in `sync_state` records which table plays which role. Changing that pointer is the **swap** (step 8).
- **Atomic pairing**: every write of product rows is in the same transaction as the cursor that records it. Either both are saved or neither is. So if the app is killed, at most the page or batch being written is lost.
- **Single runner**: one sync runner holds a lock. Requests and batches run one at a time, never in parallel.
- **Idempotent apply**: a product is written only when its incoming `change_seq` is greater than the value already stored for that product. A delete removes the row only under the same rule. If the row is already absent, a delete does nothing. Applying the same data twice does no harm.
- **Retry policy** (steps 4, 5, 7, 9 and 11): on a network error or 5xx, send the same request again (same `after_id` or `since`). Wait 2 s before attempt 2, then 4 s before attempt 3, 8 s before attempt 4 and 16 s before attempt 5. That is five attempts in total. After the fifth failure, stop, keep all saved state, and wait for the next trigger. A new trigger starts a new budget of five attempts.
- **Other responses**:
  - Any 4xx other than 410 is not retried. The run stops, state is kept, and the error is logged.
  - 410 `RESYNC_REQUIRED` is not retried. It starts a resync (step 10).
  - Token refresh is handled by the existing client networking layer.

### Statuses in `sync_state`

`no_catalogue`, `downloading`, `paused_wifi`, `catching_up`, `idle`.

- `no_catalogue`: no catalogue has been downloaded yet.
- `downloading`: pages are being saved into staging.
- `paused_wifi`: a full download is waiting for Wi-Fi. The stored cursors are kept.
- `catching_up`: every page is saved. The download is applying changes made during the download (step 7).
- `idle`: the active table is current, and incremental sync may run.

`resync_pending` is a flag that can be set on top of `downloading` or `paused_wifi`. It is not a status and not a separate download path. While the flag is set, the active table is still served while staging fills.

## Server contract (three endpoints)

- `GET /v1/catalogue/sync-anchor` returns `{anchor_seq, estimated_product_count}`.
- `GET /v1/catalogue/products?after_id=&limit=500` returns `{items: [{id, change_seq, ...body}], next_after_id, has_more}`.
  - Items are ordered by `id`, ascending.
  - Tombstones are excluded.
  - `limit` is capped at 500.
- `GET /v1/catalogue/changes?since=&limit=1000` returns `{changes: [{change_seq, id, deleted, body?}], next_since, has_more}`.
  - Changes are ordered by `change_seq`, ascending.
  - `since` is exclusive. The response contains only changes numbered after it.
  - A deleted product has `deleted: true` and no body.
  - If `since` is older than the retained window, the endpoint returns HTTP 410 with `RESYNC_REQUIRED`.

Each row carries its current `change_seq`. So the feed returns each product's latest state, at most once per product per response.

---

## Steps

### Step 1. Server contract and purge horizon

- **Starts**: deployment of the three endpoints.
- **Data moved**: none at deploy time.
- **State**: the server keeps no session for each device. The tombstone purge job records the purge horizon. The changes endpoint returns 410 for any `since` below that horizon. Indexes are needed on `change_seq` (for the feed) and on `id` (for the pages).
- **On failure**: if the anchor cannot be computed, the endpoint returns an error and the client stores nothing. If the purge horizon is not recorded, deletes can be lost with no error at all. So the purge job must not ship without it.

### Step 2. Local catalogue store

- **Starts**: first launch of the version that includes this feature, before any sync runs.
- **Data moved**: none.
- **State**: create `catalogue.sqlite` in WAL mode. It contains:
  - `products_a` and `products_b`, each with `id` (primary key), `change_seq` and `body`;
  - `sync_state`, a key/value table.

  The existing settings database is not touched.
- **On failure**: if the file cannot be created, the catalogue feature is turned off for this session and settings keep working. Creation is tried again at the next launch.

### Step 3. Dispatcher

- **Starts**: app launch (including a cold start after a kill or reboot), return to the foreground, and a network change to Wi-Fi. This is the only entry point. Every other step starts from here or from the step before it.
- **Data moved**: none. It reads `sync_state`.
- **Logic**:
  1. If status is `downloading`, `paused_wifi` or `catching_up`, resume at step 11. The 15-minute throttle does not apply.
  2. Else, if an active generation exists and status is `idle`, run incremental sync (step 9), but only if `last_run_started_at` is more than 15 minutes ago.
  3. Else, if no active generation exists and status is `no_catalogue`, start a first download (step 4).
  4. Otherwise, do nothing.
- **State**: reads only.
- **On failure**: if `sync_state` or the catalogue file cannot be opened, mark the catalogue as unavailable and try again at the next trigger. Never delete data automatically.

### Step 4. Start or restart a full download into staging

- **Starts**: step 3 with no active generation, step 10 (resync), or step 11 when the anchor probe returns 410.
- **Gate 1, Wi-Fi**: if the device is not on Wi-Fi, send no request. Set status to `paused_wifi`, keep `resync_pending` if it is set, and stop. Step 11 resumes this at the next Wi-Fi trigger.
- **Gate 2, storage**: check free storage before starting. The estimate is `estimated_product_count` times about 2 KB, plus a margin. For 400,000 products that is about 800 MB before index overhead. During a resync the active table also stays on disk, so the requirement is roughly double. If there is not enough space, stop and tell the rep before any download starts.
- **Data moved**: one small request, `GET /sync-anchor`.
- **State**: when the response arrives, one transaction:
  - clears the inactive table;
  - sets `staging_gen` to that table;
  - stores `anchor_seq`, `estimated_product_count`, `last_id = null`, `pages_done = 0`, and `status = downloading`;
  - keeps `resync_pending` if this is a resync.

  The active table is not touched.
- **On failure**: the anchor request follows the retry policy. Nothing is stored until a response arrives. If the app is killed before the transaction commits, the previous state is unchanged. During a resync, reps keep seeing the active table.

### Step 5. Fetch and save one page of products (repeats)

- **Starts**: step 4 has committed, the previous page has committed, or step 11 resumes the download.
- **Gate**: before each request, check for Wi-Fi. If there is none, set status to `paused_wifi` and stop without sending the request (step 6).
- **Data moved**: `GET /products?after_id=<last_id>&limit=500`. That is about 500 x 2 KB, or roughly 1 MB per page.
- **State**: one transaction:
  - upserts each item into the staging table, under the idempotent apply rule;
  - sets `last_id = next_after_id`;
  - increments `pages_done`.

  If `has_more` is true, repeat. If it is false, set status to `catching_up` in the same transaction as the last page, then go to step 7.
- **Cellular rule**: if Wi-Fi drops while a request is in flight, let that request finish and save its page. The next gate then pauses the download. If the in-flight request fails, the retry in step 12 checks for Wi-Fi before each retry, and pauses instead of retrying on cellular.
- **On failure**:
  - A network error or 5xx retries the same `after_id`. This is safe because the request is idempotent: repeating it gives the same result.
  - A 4xx stops the run.
  - If the app is killed before the commit, that page is lost. The download resumes by requesting again from the last committed `last_id`.
  - A half-saved page is never visible.
  - The download never restarts from page 1.

### Step 6. Pause on cellular and resume on Wi-Fi

- **Starts**: Wi-Fi is detected again (a network-change event), or the app launches or comes to the foreground while Wi-Fi is present.
- **Data moved**: none until the download continues.
- **State**: status `paused_wifi`. `last_id`, `pages_done`, `catchup_seq` and the other cursors are kept in `sync_state`.
- **Resume point**: if `last_id` shows that pages remain, resume at step 5. If every page is saved, resume at step 7.
- **On failure**: if Wi-Fi drops and returns repeatedly, the Wi-Fi gate in steps 5 and 7 is checked again before every request or batch, so nothing starts on cellular.

### Step 7. Catch up on changes made during the download

- **Starts**: step 5 saves the last page, so status is `catching_up`.
- **Gate**: Wi-Fi, checked before each batch. The full download includes this step, so it follows the same Wi-Fi rule.
- **Why this step exists**: each page shows products as they were when that page was read. Changes made after that are visible only in the change feed. These include:
  - edits to products the walk has already passed;
  - new products with ids below the cursor;
  - deletes.

  The anchor was read before the first page. The feed starts from the anchor, so every change made after it is replayed here, and none is missed.
- **Data moved**: `GET /changes?since=<catchup_seq>&limit=1000`, starting with `catchup_seq = anchor_seq`. Each batch is applied to the staging table. Upserts and deletes follow the idempotent apply rule from step 5.
- **State**: each batch commits together with `catchup_seq = next_since`. When `has_more` is false, go to step 8. The server keeps receiving edits, so catch-up may take several batches. It ends when a response says there is nothing more.
- **On failure**:
  - 410 means the staging copy cannot be completed. Discard it and restart at step 4 with a new anchor. The active table is untouched.
  - A network error or 5xx follows step 12.
  - On resume, batches already committed are kept, and catch-up continues from `catchup_seq`.

### Step 8. Swap to the new generation

- **Starts**: step 7 reports that catch-up is complete.
- **Data moved**: none.
- **State**: one transaction sets:
  - `active_gen = staging_gen`;
  - `incremental_cursor = catchup_seq`;
  - `staging_gen = null`;
  - `status = idle`;
  - clears `resync_pending`.

  After the commit, browsing reads the new table.
- **Reps**: before the commit they see the previous active table. On a first download there is no previous table, so what reps see depends on Open question 1.
- **On failure**: if the app is killed before the commit, staging is complete but not yet active, and status is still `catching_up`. On restart, step 7 runs from `catchup_seq`, returns `has_more = false` almost at once, and the swap runs again. If the app is killed after the commit, step 9 takes over.

### Step 9. Incremental sync

- **Starts**: app launch or foreground (step 3), with status `idle`, an active generation present, and `last_run_started_at` more than 15 minutes ago. Any network may be used.
- **Never during a download**: incremental sync does not run while a full download is in progress. Step 7 covers that case.
- **Throttle**: `last_run_started_at` is written when the run starts. A run that fails still counts. So repeated foregrounding cannot cause repeated requests (see Assumption 1).
- **Data moved**: `GET /changes?since=<incremental_cursor>&limit=1000`. Each batch applies upserts, and deletes that remove rows, to the active table. Repeat while `has_more` is true.
- **State**: each batch commits together with `incremental_cursor = next_since`. A run that stops midway keeps every committed batch. The next run continues from the cursor.
- **On failure**:
  - A network error or 5xx follows step 12. If the retry budget is spent, stop and wait for the next trigger after the 15-minute window.
  - A 410 `RESYNC_REQUIRED` starts a resync (step 10). The active table stays in place. Reps keep seeing the existing catalogue until the replacement is complete.

### Step 10. Resync handoff

- **Starts**: step 9 receives 410 (`RESYNC_REQUIRED`), or step 11 receives 410 on its anchor probe.
- **Data moved**: none beyond step 4.
- **State**: set `resync_pending = true`. The active generation is kept and still served. Staging is cleared and refilled from step 4. If the device is not on Wi-Fi, step 4 records `paused_wifi` with the flag still set, and the active table keeps being served.
- **On failure**: the failure path of step 4 applies. The active table is never removed before step 8 has committed.

### Step 11. Resume an interrupted full download

- **Starts**: cold start after a kill or reboot, network recovery, Wi-Fi returning, or foreground (step 3).
- **Gate**: Wi-Fi.
- **Logic**:
  - If no anchor is stored yet, go to step 4.
  - Otherwise, send one probe: `GET /changes?since=<anchor_seq>&limit=1`. This checks that the anchor is still inside the retained window. It catches a download that has been away for more than 7 days before hours of pages are fetched.
  - A 410 goes to step 4, which discards staging and restarts.
  - A success continues from the saved state.
- **State**: read `status`, `last_id`, `pages_done` and `catchup_seq`. Continue at step 5 if pages remain, or at step 7 if every page is saved.
- **On failure**: a probe that fails with a network error or 5xx follows step 12. The active table is not touched in any case.

### Step 12. Retry and failure handling (shared rule)

- **Starts**: any request in steps 4, 5, 7, 9 or 11 fails with a network error or 5xx.
- **Logic**: retry the same request after 2 s, 4 s, 8 s and 16 s, for five attempts in total. Before each retry, if the job is a full download and the device is not on Wi-Fi, pause at step 6 without using up an attempt.
- **Data moved**: none of its own. It repeats the request that failed.
- **State**: nothing is rolled back. Committed pages and batches stay. Status is unchanged.
- **After the fifth failure**: stop the run and wait for the next trigger. Staging is not discarded, the active table is not touched, and the next trigger resumes from the saved cursor.

---

## Open questions (not decided here)

1. **Browsing during a first download.** Product has not decided whether reps may browse the partly downloaded catalogue, or whether they should see a progress screen until step 8 completes.
   - This plan reads only the active table. On a first download there is no active table until step 8, so the browse screen cannot be built until this is decided.
   - If partial browsing is allowed, reads would come from staging during steps 5 and 7. The visible set would then be incomplete and ordered by id. That needs a product decision before the read path is built.
2. **Storage peak during a resync.** The active and staging tables are both on disk. That roughly doubles the footprint, to about 1.6 GB or more for 400,000 products. Product and engineering need to accept this, or choose another approach. The plan keeps the requirement that reps see the existing catalogue until the replacement is ready.

## Assumptions to confirm

1. **Throttle after a failed run.** Failed incremental runs count toward the 15-minute throttle, so repeated foregrounding cannot cause bursts of retries. The alternative is to let the next trigger run at once, at the cost of more requests.
2. **Other errors.** 401 responses and token refresh are assumed to be handled by the existing client layer. 4xx responses other than 410 are not retried and are logged for investigation.
3. **Visibility order.** The plan relies on the brief's guarantee that `change_seq` values become visible in order. If that stops holding, the anchor must be the lowest in-flight `change_seq` minus one, not the highest visible value.
4. **Wi-Fi signal.** "Wi-Fi" means the platform's Wi-Fi transport: on iOS, the path monitor reports a Wi-Fi interface type; on Android, `TRANSPORT_WIFI`. It does not mean "not cellular".