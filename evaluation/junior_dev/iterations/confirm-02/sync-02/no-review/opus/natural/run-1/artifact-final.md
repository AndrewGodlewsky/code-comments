# Offline product catalogue sync: plan

## Summary

The device builds a complete copy of the catalogue in a **staging table** while reps keep using whatever **live table** they already have. Before it fetches the first page, the client records a **watermark**: the highest `change_seq` the server has committed at that moment. It then downloads every product page by page in product id order. Each page and its cursor are saved in a single SQLite transaction, so the download can always resume after the last saved page. When the last page is in, the client asks for every change after the watermark and applies them to staging. It then swaps staging into live in one transaction. From that point, incremental sync continues from the position the catch-up reached.

**Why no edits are missed.** `change_seq` is assigned at commit, and rows become visible in `change_seq` order. So once the server reports watermark *W*, every change committed after that has `change_seq > W`, and `GET /changes?since=W` returns it. That covers products edited behind the cursor, products inserted with a lower id than the cursor, and products deleted after their page was saved. A page can also contain rows newer than *W*. Replaying those is harmless because the client applies a row only when its `change_seq` is at least the one it already holds.

**Sizes.** 400,000 products × 2 KB is about 800 MB of raw data, or around 1 GB in SQLite with indexes. That is 800 pages of about 1 MB each. During a resync the old live table and the new staging table exist side by side, so the device briefly needs about twice that space.

## State kept on the device

The catalogue gets its own SQLite file, `catalogue.db`, separate from the existing settings database. It is too big to share a file with settings, and the sync state has to sit in the same file as the product rows so that one transaction can update both. The file runs in WAL mode, so the UI can keep reading `products` while sync writes to `products_staging`.

| Table / key | Contents |
|---|---|
| `products` | Live catalogue that reps browse: product columns plus `change_seq`. |
| `products_staging` | The catalogue being built by a full download. Same columns as `products`. |
| `sync_state.live_position` | `change_seq` that `products` is current to. Null if no live catalogue exists yet. |
| `sync_state.download_status` | `none` or `in_progress`. |
| `sync_state.download_id` | Random id for the current download, used in index names and logs. |
| `sync_state.download_watermark` | The `change_seq` position that `products_staging` is guaranteed complete to once all pages are in. |
| `sync_state.watermark_taken_at` | Device time when the watermark was last set or advanced. |
| `sync_state.download_cursor` | Id of the last product in the last fully saved page. Null before page 1. |
| `sync_state.pages_saved`, `expected_count` | Used for progress display. |
| `sync_state.last_incremental_started_at` | Enforces the 15-minute limit. |

---

## Part A: Server

### 1. Record the tombstone purge horizon

- **What starts it:** the existing job that purges tombstones older than 7 days, each time it runs.
- **What data moves:** in the same transaction that deletes the tombstones, the job writes the highest `change_seq` it purged to a single-row table, `catalogue_sync_meta.purge_horizon`. The new value is `max(old value, highest purged change_seq)`.
- **Where state is kept:** Postgres, in `catalogue_sync_meta`.
- **On failure:** the transaction rolls back, so the tombstones and the horizon stay consistent. The job retries on its next scheduled run. If tombstones stay unpurged for longer, that is harmless.

A client position `since` is valid exactly when `since >= purge_horizon`. Only then is every change after `since` still in the table.

### 2. Endpoint: `GET /v1/catalogue/position`

- **What starts it:** the client, at the start of a full download (step 8).
- **What data moves:** the response is `{ "position": <max(change_seq) over all product rows, tombstones included>, "product_count": <count of non-deleted products> }`. Because rows become visible in `change_seq` order, every change at or below `position` is already visible. The count is only used for progress and the storage check.
- **Where state is kept:** nowhere new. The endpoint is a read-only query.
- **On failure:** a 5xx response. The client applies the retry policy (step 6).

### 3. Endpoint: `GET /v1/catalogue/products?after_id={id}`

- **What starts it:** the client, once for each page of a full download (step 9).
- **What data moves:** the query is `WHERE deleted = false AND id > :after_id ORDER BY id LIMIT 501`. The server returns up to 500 products, each with `change_seq`, plus `next_after_id` (the id of the 500th product) and `has_more` (true when a 501st row was found). The first request omits `after_id`. The page size is fixed at 500 on the server. Responses are gzip-compressed. The query uses the primary key index, and there is no offset.
- **Where state is kept:** the server keeps none. The cursor lives on the client.
- **On failure:** a 5xx response. The client retries the identical URL (step 6). Because the request carries the same `after_id`, the retry is idempotent.

### 4. Endpoint: `GET /v1/catalogue/changes?since={seq}`

- **What starts it:** the client, during incremental sync (step 14), during catch-up of a download (steps 11 and 12), and during the server-side check for an expired position.
- **What data moves:**
  - If `since < purge_horizon`, the server returns `410 Gone` with `{ "error": "resync_required" }`.
  - Otherwise it runs `WHERE change_seq > :since ORDER BY change_seq LIMIT 1001` and returns up to 1,000 entries, plus `next_since` (the `change_seq` of the last entry) and `has_more`.
  - Each entry is either a full product with `change_seq`, or a delete in the form `{ "id", "change_seq", "deleted": true }`. Each product appears at most once, in its current state, because a row holds only its latest `change_seq`.
  - This query needs a new index on `change_seq`.
- **Where state is kept:** none on the server.
- **On failure:** a 5xx response triggers the retry policy (step 6). A 410 is not retried: it starts a resync (step 15).

---

## Part B: Client foundations

### 5. Create the catalogue database

- **What starts it:** the first app launch after the release that ships this feature.
- **What data moves:** the client creates `catalogue.db` with the `products` and `sync_state` tables and turns on WAL mode. The settings database is not touched.
- **Where state is kept:** `catalogue.db`.
- **On failure:** if the file cannot be created (for example, the disk is full), sync stays off for this launch and the app tries again at the next launch. Settings keep working.

### 6. Retry policy, shared by every request

- **What starts it:** any sync request that fails with a network error (no connection, timeout, connection reset) or a 5xx response.
- **What data moves:** the client re-sends the same request with the same parameters. It makes at most 5 attempts in total, waiting 2 s, 4 s, 8 s and 16 s between them.
- **Where state is kept:** the attempt counter is kept in memory only. Whatever was already committed to `catalogue.db` stays.
- **On failure:**
  - After the 5th failed attempt, the sync job stops and waits for its next trigger (step 7). Saved pages, the cursor and the positions are all kept.
  - A 410 or any other 4xx response is not retried. A 410 starts step 15. Any other 4xx is logged and stops the job until its next trigger.
  - During a full download, the client checks the network before each retry. If the device is no longer on Wi-Fi, it pauses (step 10) instead of retrying.

### 7. Sync coordinator: choose what to run

- **What starts it:**
  - app launch;
  - the app returning to the foreground;
  - Wi-Fi becoming available while the app is running;
  - an OS background task, while a download is `in_progress`. On Android this is WorkManager with an unmetered-network constraint. On iOS it is a `BGProcessingTask` that requires connectivity; the client still checks for Wi-Fi itself, because iOS cannot require Wi-Fi specifically.
- **What data moves:** none. The coordinator reads `sync_state` and decides what to run:
  1. If a sync job is already running in this process, it does nothing. A single in-memory lock means only one job runs at a time.
  2. If `download_status = in_progress`, it continues the download (step 9), but only on Wi-Fi.
  3. If `live_position` is null (no catalogue yet), it starts a full download (step 8), but only on Wi-Fi.
  4. Otherwise, on a launch or foreground trigger, it runs incremental sync (step 14) if at least 15 minutes have passed since `last_incremental_started_at`.
- **Where state is kept:** the lock is kept in memory. It is lost if the process is killed, which is correct, because the job dies with the process. The decision inputs come from `sync_state`.
- **On failure:** if the coordinator itself fails, it does nothing and the next trigger runs it again.

---

## Part C: Full download

### 8. Start a full download

- **What starts it:** the coordinator, either on a first install (step 7, case 3) or after a resync (step 15), while the device is on Wi-Fi.
- **What data moves:**
  1. The client drops any leftover `products_staging` table and creates an empty one, without search indexes. Inserting rows is faster without them.
  2. It calls `GET /position` (step 2). This call **must come before the first page request**.
  3. It checks free space against `product_count × 2 KB × 1.5`. During a resync it also leaves room for the live table, which is still there.
  4. In one transaction it writes `download_status = in_progress`, a new `download_id`, `download_watermark = position`, `watermark_taken_at = now`, `download_cursor = null`, `pages_saved = 0` and `expected_count = product_count`.
- **Where state is kept:** `sync_state` and `products_staging` in `catalogue.db`.
- **On failure:**
  - If `/position` fails, the retry policy applies (step 6). The download is not marked as started, so the next trigger starts again cleanly.
  - If there is not enough space, the client does not start. It tells the rep how much space is needed and checks again at the next trigger. During a resync the existing catalogue stays in use.

### 9. Fetch and save one page (repeat until done)

- **What starts it:** step 8 completing, the previous page being saved, or a resume (step 11). Before each request the client checks that the device is on Wi-Fi. If it is not, it goes to step 10.
- **What data moves:**
  1. The client sends `GET /products?after_id={download_cursor}`. The first page omits `after_id`.
  2. It receives up to 500 products.
  3. In **one SQLite transaction**, it upserts the rows into `products_staging` and sets `download_cursor = next_after_id` and `pages_saved += 1`. The upsert overwrites a row only if the incoming `change_seq` is at least the stored one; that only matters after a catch-up (step 11).
  4. If `has_more = false`, it goes to step 12. Otherwise it fetches the next page. Pages are always fetched one at a time.
- **Where state is kept:** `products_staging` and `sync_state.download_cursor`, updated together in one transaction.
- **On failure:**
  - Network errors and 5xx responses follow the retry policy, using the same `after_id` (step 6).
  - If the app is killed before the commit, the transaction is lost and the cursor still points at the previous page. The page is fetched again on resume.
  - A response that does not parse, or a failed write, rolls back the transaction. It is handled as a failed attempt.

### 10. Pause when the device moves to cellular

- **What starts it:** the device switches from Wi-Fi to cellular, as reported by a network-path or connectivity listener.
- **What data moves:**
  - A page request already in flight is allowed to finish, and its page is saved as in step 9.
  - No new request is started on cellular. Retries count as new requests (step 6).
  - The job then stops, with `download_status` still `in_progress`.
- **Where state is kept:** `sync_state`, which is unchanged apart from the page that was just saved.
- **On failure:** if the in-flight request breaks during the handover, its page was not saved. The cursor still points at the last saved page, so that page is fetched again once Wi-Fi returns.

### 11. Resume after an interruption

- **What starts it:** any coordinator trigger (step 7) while `download_status = in_progress` and the device is on Wi-Fi. This covers a killed app, a phone restart, a network loss and a pause for cellular.
- **What data moves:**
  1. If `watermark_taken_at` is more than 3 days old, the client first catches up staging. It calls `GET /changes?since={download_watermark}` (step 4) until `has_more = false`. It applies each response in one transaction: changed rows are upserted with the `change_seq` check from step 9, deletes remove the row if it is present, and `download_watermark` and `watermark_taken_at` are advanced. This keeps the watermark well inside the 7-day tombstone window, even when a download is paused for days.
  2. The client then continues with step 9 from `download_cursor`, not from page 1.
- **Where state is kept:** `sync_state` and `products_staging`.
- **On failure:**
  - Catch-up errors follow the retry policy, and the download stays paused until the next trigger.
  - If the catch-up returns 410 because the watermark has already expired, staging can no longer be trusted. The client discards it and starts again from step 8.

Why a catch-up in the middle of a download is safe:
- Changes to products the cursor has already passed are needed, so applying them is correct.
- Changes to products ahead of the cursor are written early. The page that later contains those products carries their current state, and the `change_seq` check keeps the newest version.
- A delete ahead of the cursor removes nothing. The page then leaves that product out, because the page query skips deleted rows.

### 12. Finish: bring staging up to date

- **What starts it:** step 9 saving a page with `has_more = false`.
- **What data moves:**
  1. The client runs the same catch-up loop as step 11, from `download_watermark` until `has_more = false`. This delivers every edit, insert and delete made during the download.
  2. It then builds the search indexes on `products_staging`. The index names include `download_id`, so they do not clash with the live table's indexes.
  3. It checks that the row count is plausible against `expected_count` and the changes it has applied.
- **Where state is kept:** `products_staging` and `sync_state.download_watermark`, which ends at the position of the last change applied.
- **On failure:**
  - Network errors and 5xx responses follow the retry policy, and the next trigger re-runs this step from the stored watermark.
  - A 410 discards staging and restarts from step 8.
  - If building the indexes fails, for example because the disk is full, the indexes are dropped and the step is retried at the next trigger.
- **Network:** the catch-up uses the incremental endpoint, so it runs on any network, like incremental sync. This is an interpretation; see the assumptions.

### 13. Swap staging into live

- **What starts it:** step 12 completing.
- **What data moves:** in **one SQLite transaction**, the client:
  1. drops `products`;
  2. renames `products_staging` to `products`;
  3. sets `live_position = download_watermark`;
  4. sets `download_status = none`;
  5. clears the cursor, the page count and the watermark.

  Until this transaction commits, reps see the old catalogue (during a resync) or no catalogue (on a first install). After it commits, they see the new catalogue. Screens that show products are told to reload.
- **Where state is kept:** `catalogue.db`.
- **On failure:** if the transaction fails or the app is killed, SQLite rolls it back. The old live table is still there, and staging is still complete. The next trigger finds `download_status = in_progress` with `has_more` already reached and repeats steps 12 and 13. The client tracks this case with a `pages_complete` flag in `sync_state`, set in the same transaction as the last page in step 9.

---

## Part D: Incremental sync

### 14. Incremental sync run

- **What starts it:** the coordinator, on app launch or a return to the foreground, when a live catalogue exists, no download is in progress, and at least 15 minutes have passed since `last_incremental_started_at`. Any network type is allowed.
- **What data moves:**
  1. The client writes `last_incremental_started_at = now`. A failed run also counts towards the 15-minute limit.
  2. It calls `GET /changes?since={live_position}`.
  3. It applies each response to `products` in one transaction: changed rows are upserted when the incoming `change_seq` is at least the stored one, delete entries remove the row, and `live_position` is set to `next_since` in the same transaction.
  4. While `has_more = true`, it requests the next 1,000 changes straight away, so one run continues until it is caught up.
- **Where state is kept:** `products` and `sync_state.live_position`, always committed together.
- **On failure:**
  - Network errors and 5xx responses follow the retry policy for the request that failed (step 6). Responses already applied stay applied.
  - After 5 failed attempts, the run stops until the next trigger that is allowed by the 15-minute limit.
  - A 410 goes to step 15.

### 15. Handle "resync required"

- **What starts it:** a `410 resync_required` from `GET /changes` during incremental sync. This happens when the device has not synced for more than the tombstone window.
- **What data moves:**
  - `products` and `live_position` are left exactly as they are, and reps keep browsing the existing catalogue.
  - The client sets the state so that step 8 runs on the next Wi-Fi trigger, or immediately if the device is already on Wi-Fi.
  - Incremental sync is suspended until the swap in step 13. Any `live_position` it could use would get a 410 again.
  - The UI may show a small "catalogue update in progress" notice. The wording is for Product to decide.
- **Where state is kept:** `sync_state`.
- **On failure:** nothing is lost. If the download that follows is interrupted, steps 9 to 11 resume it, and the old catalogue stays live throughout.

---

## Part E: Verification

### 16. Test the failure cases before release

- **What starts it:** the feature branch is complete. These tests run in CI against a seeded test server, with 400k products available for the soak test.
- **What data moves:** scripted scenarios, each checking that the final device catalogue matches the server exactly (ids, `change_seq` values and deleted rows):
  - **Edits during the download:** products are updated, inserted with ids both lower and higher than the cursor, and deleted on both sides of the cursor while a download is running.
  - **App killed:** the process is killed before, during and after a page commit, and during the swap.
  - **Cellular handover:** the device switches to cellular in the middle of a request, and the test checks that no new request is sent until Wi-Fi returns.
  - **Long pause:** the download is paused for more than 3 days, which must produce a catch-up, and the watermark is expired, which must restart the download cleanly.
  - **Resync:** a 410 during incremental sync, with the old catalogue visible until the swap.
  - **Retries:** the exact sequence 2, 4, 8 and 16 s, with 5 attempts and then a stop.
  - **Rate limit:** the 15-minute limit across repeated foreground events.
- **Where state is kept:** test fixtures.
- **On failure:** a failing scenario blocks release.

---

## Open question (for Product)

**May reps browse the partly downloaded catalogue during their first download, or should they see a progress screen until it finishes?** This plan does not decide.

- The swap in step 13 is the moment the live catalogue becomes complete. Either answer fits the plan without changing the sync steps.
- If browsing is allowed, the UI would read from `products_staging` during a first install only. It would have to say that the list is incomplete, and searches would run without the indexes, which are built in step 12.
- If browsing is not allowed, the UI shows a progress screen driven by `pages_saved` and `expected_count`.
- A resync is not affected: the brief already requires the existing catalogue to stay visible.

## Assumptions and interpretations to confirm

- **"Finishes the page it is on"** means a request already in flight may complete and be saved on cellular, but no new request or retry starts on cellular.
- **The catch-up after the last page (step 12)** runs on any network, because it uses the incremental endpoint. If Product wants a new catalogue to be swapped in only over Wi-Fi, step 12 should get the same Wi-Fi check as step 9.
- **The 15-minute limit** counts from the start of the last incremental run, whether or not that run succeeded.
- **Storage:** devices are expected to have about 1 GB free, and about 2 GB during a resync. Devices without that space cannot sync until space is freed.
- **Product ids** have a stable sort order, so keyset pagination by `id` is well defined.
