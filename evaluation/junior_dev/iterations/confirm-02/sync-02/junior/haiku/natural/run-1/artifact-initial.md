# Offline product catalogue sync for the field-sales app: plan

## Context and assumptions

- The Catalogue service stores about 400,000 products (about 2 KB each) in Postgres. Each insert, update or delete stamps the row with a global `change_seq`, assigned at commit. Rows become visible in `change_seq` order, so any read of `change_seq > N` is gap-free.
- Deletes are tombstones (`deleted = true`), purged 7 days after deletion.
- The app's existing SQLite database holds user settings. This plan puts the catalogue in a **separate SQLite file** so that large catalogue writes and rebuilds never touch settings.
- Both iOS and Android use the same logical design. Platform details (Wi-Fi detection, background execution) are noted where they matter.
- A "page" is 500 products, fetched by keyset on product id.
- Two stores are used. `product_live` is what reps browse. `product_next` is the staging copy being built. Swapping the two is one database transaction.

## Core idea

The full download and the incremental sync are linked by a **watermark** `W`. Before the first page is fetched, the client records `W`, the highest committed `change_seq` at that moment. Every change committed after `W` is picked up by the incremental sync that runs after the last page. This covers edits made during a download that lasts hours. The keyset pages may show some rows before or after an edit, but any row changed after `W` is re-delivered by the incremental pass, so nothing is missed.

## Server endpoints

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /sync/watermark` | Current highest committed `change_seq` | `{ "watermark": W }` |
| `GET /sync/products?after_id=&limit=500` | One full-download page of live products, ordered by id ascending | `{ "items": [...], "next_after_id": id or null, "done": bool }` |
| `GET /sync/changes?since=N&limit=1000` | Changes with `change_seq > N`, ordered ascending, including tombstones | `{ "changes": [{ "change_seq", "id", "deleted", "product" or null }], "next_since", "has_more" }` or `410 resync_required` |

The server answers `resync_required` when `N` is older than the tombstone purge horizon (`N < purge_horizon`). The purge horizon is the `change_seq` below which tombstones have been purged. If a tombstone with `change_seq > N` had been purged, the purge horizon would be above `N`, so this check catches every case where a delete could be missing.

The page endpoint is stateless. The only cursor is `after_id`, so the server keeps no per-download session.

## Client state (catalogue SQLite file)

- `sync_state` (one row): `mode` (`idle`, `downloading`, `paused_cellular`, `failed_exhausted`, `applying`), `watermark_W`, `download_last_id` (last fully saved page's last id), `download_pages_saved`, `live_cursor` (last applied `change_seq` for `product_live`), `last_incremental_at`.
- `product_live`: the catalogue reps see. Indexed by id.
- `product_next`: staging copy, created at the start of a download. Dropped after a swap or an abandoned download.
- `sync_state` and the page data are written in the same transaction, so the cursor can never run ahead of the rows it describes.

## Numbered plan

### 1. Record the watermark and start a download

- **Starts when:** no `product_live` exists (first install), or a `resync_required` answer arrives (step 9), and a Wi-Fi connection is available (step 4 applies from here on).
- **Data moved:** one request to `GET /sync/watermark` returns `W`.
- **State:** in one transaction, create `product_next` (dropping any older staging table), then write `sync_state.mode = downloading`, `watermark_W = W`, `download_last_id = null`, `download_pages_saved = 0`. Record `W` before the first page request, so all later changes are after `W`.
- **Failure:** network error or 5xx → retry policy (step 10). Nothing has been saved except the empty staging table, so a restart is harmless. If the device is on cellular, do not call the endpoint; wait for Wi-Fi.

### 2. Fetch one page

- **Starts when:** the previous step completed, or a resume (step 6) is triggered, and the device is on Wi-Fi.
- **Data moved:** `GET /sync/products?after_id=download_last_id&limit=500`. The first request uses no `after_id`. About 1 MB per page; request gzip. Pages are requested one at a time, never in parallel.
- **State:** nothing is written until the response has been fully received and parsed.
- **Failure:** network error or 5xx → retry policy (step 10). A timeout during the request is treated as a network error. A partly received body is discarded, so the same page is requested again.

### 3. Save the page atomically

- **Starts when:** a complete page has been received and validated (an array of at most 500 items, ids strictly increasing and greater than `download_last_id`).
- **Data moved:** each product is upserted into `product_next` by id.
- **State:** in one transaction, upsert the 500 rows, set `download_last_id` to the page's last id, and increase `download_pages_saved` by one. If `done` is true, go to step 5. Otherwise go to step 4.
- **Failure:** if the app is killed during the transaction, SQLite rolls it back. On restart the cursor is still on the previous page, so that page is fetched again. Re-saving a page is harmless because upserts are idempotent. A failed validation (for example, ids out of order) is treated as a server error (retry policy, step 10). If it fails all five attempts, the download stops with `failed_exhausted`.

### 4. Wi-Fi gate between pages

- **Starts when:** a page has been saved and `done` is false.
- **Data moved:** none.
- **State:** `sync_state.mode` stays `downloading`. Before requesting the next page, check the connection type.
- **Behaviour:**
  - On Wi-Fi (on Android, a network with `NET_CAPABILITY_NOT_METERED`; on iOS, `NWPathMonitor` reporting a Wi-Fi interface), go to step 2.
  - On cellular or no network, set `mode = paused_cellular` and stop. The current page has already been finished and saved, so the device pauses at a page boundary.
  - If the link drops in the middle of a request, that request is treated as a network error (step 2 and step 10). A retry only runs when Wi-Fi is still available. If the device is on cellular, the retry is suspended until Wi-Fi returns.
- **Failure:** none beyond the cases above. Wi-Fi returning (a connectivity callback, or the next app launch or foreground event) moves `paused_cellular` back to `downloading` and goes to step 2.

### 5. Catch up on changes made during the download

- **Starts when:** the last page has been saved (`done` true).
- **Data moved:** `GET /sync/changes?since=W&limit=1000`, repeated while `has_more` is true, applied to `product_next`. This is the same loop as the steady-state incremental sync (step 7), but it targets staging.
- **State:** each batch of up to 1,000 changes is applied in one transaction. A change is a delete (remove the row by id) or an upsert (write the product). Only apply it if `change_seq` is greater than the change_seq already stored on that row. This keeps the apply step idempotent when a batch is repeated. Set `sync_state.mode = applying` and advance a cursor (`download_catchup_since`) in the same transaction as each batch.
- **Failure:**
  - Network error or 5xx → retry policy (step 10). The cursor is kept, so the catch-up resumes from the last applied batch.
  - `410 resync_required` → the download took longer than the tombstone window. Discard `product_next` and restart from step 1. Reps keep the old `product_live`.
  - Interruption → resume at step 6.

### 6. Resume after interruption

- **Starts when:** the app launches, returns to the foreground, or is restarted after being killed, and `sync_state.mode` is `downloading`, `paused_cellular`, `failed_exhausted` or `applying`.
- **Data moved:** none immediately. The next request starts from `download_last_id` (pages) or `download_catchup_since` (catch-up).
- **State:** everything saved up to the last complete transaction is kept. Pages are never restarted from page 1 unless the watermark or cursor is invalid.
- **Failure:** if the resume request gets `410 resync_required`, go to step 1 and discard the staging table. If a `failed_exhausted` state is reached again, it waits for the next trigger (step 10).

### 7. Steady-state incremental sync

- **Starts when:** the app launches or returns to the foreground, and `live_cursor` is set (a download has completed). Runs at most once every 15 minutes, measured from `last_incremental_at`. The trigger is ignored if the last run was less than 15 minutes ago. Any network may be used.
- **Data moved:** `GET /sync/changes?since=live_cursor&limit=1000`, repeated while `has_more` is true. Changes are applied to `product_live` in order.
- **State:** each batch is applied in one transaction, with the same "only apply if newer" rule, and `live_cursor = next_since` in the same transaction. Deletes remove the local row, so reps stop seeing the product. `last_incremental_at` is written when a run starts. One run may span several batches, and the 15-minute limit covers the whole run.
- **Failure:** network error or 5xx → retry policy (step 10). The cursor is kept, so the next trigger continues from the last applied batch. `410 resync_required` → go to step 9.

### 8. Atomic swap at the end of the first download

- **Starts when:** step 5 has finished with `has_more` false.
- **Data moved:** none over the network.
- **State:** in one transaction, drop or rename `product_live` out of the way, rename `product_next` to `product_live`, and set `sync_state.mode = idle` and `live_cursor = last change_seq applied`. Either the old catalogue or the complete new one is visible; there is no in-between state.
- **Failure:** if the app is killed before the commit, the old `product_live` and the staging table are both intact and step 6 resumes the catch-up. This plan does not decide what reps see before the swap. See open question 1.

### 9. Resync required in steady state

- **Starts when:** an incremental call (step 7) returns `410 resync_required`. This means the device has been offline for longer than the 7-day tombstone window.
- **Data moved:** a full download starts again (steps 1 to 8).
- **State:** `product_live` stays in place and keeps serving reps until the swap in step 8. Only `product_next` is rebuilt.
- **Failure:** the same as steps 1 to 8. If the new download is interrupted, reps keep the old catalogue.

### 10. Retry policy for network errors and 5xx responses

- **Starts when:** any request in steps 1, 2, 5 or 7 fails with a network error or a 5xx response.
- **Data moved:** the same request is sent again. Nothing new is requested.
- **State:** the attempt count is kept in memory for that request only. It is not persisted.
- **Behaviour:** up to 5 attempts in total for each request. Waits between attempts are 2 s, 4 s, 8 s and 16 s, a 30-second total. If all 5 attempts fail, the client sets `mode = failed_exhausted` (for downloads) or leaves `live_cursor` where it is (for incremental sync). It keeps everything it has already saved and waits for the next trigger (app launch, foreground, Wi-Fi returning, or the 15-minute gate for incremental sync). No further automatic retries.
- **Note:** 4xx responses other than `410` are not in the brief. This plan treats them as failures that do not retry, so the client waits for the next trigger. See open question 3.

### 11. Connectivity and background behaviour

- **Starts when:** the OS reports a connectivity change, or the app is backgrounded during a download.
- **Data moved:** none.
- **State:** the mode is saved at every step boundary. Downloads may run in the background only while on Wi-Fi, using the OS background mechanism for the platform (background URL session on iOS, WorkManager with a `UNMETERED` constraint on Android). If the OS stops the work, the next launch resumes at step 6.
- **Failure:** the OS may stop a background task at any time. Because every page is saved atomically (step 3), no work is lost beyond the page in flight.

### 12. Tombstone purge and the server side of the window

- **Starts when:** the server's scheduled purge removes tombstones older than 7 days.
- **Data moved:** none to the client directly.
- **State:** the server keeps the purge horizon, the highest `change_seq` that has been purged. The `/sync/changes` check (step table above) compares each `since` value with this horizon.
- **Failure:** a client that has not synced for more than 7 days gets `410`, which leads to step 9. A download that takes more than 7 days, measured from `W`, will also end at step 5 with `410`, and this can repeat. See open question 4.

### 13. Clean up

- **Starts when:** the swap (step 8) has succeeded, or a download has been abandoned for a resync (step 9).
- **Data moved:** none.
- **State:** the staging table is removed once it is no longer needed. Abandoned download state is cleared only when a new download begins, so an interrupted download can still resume.
- **Failure:** if cleanup fails, the next start drops the leftover table. The catalogue is not affected.

## Open questions (not decided)

1. **Browse during the first download.** Product has not decided whether reps can browse the partly downloaded catalogue during their first download or should see a progress screen until it finishes. The design above works either way. Under the "browse during download" option, reads would have to come from `product_next` or from a partial view of it, which changes how step 8 and the first-install UI behave. This plan does not choose.
2. **Watermark on the server.** The plan assumes `GET /sync/watermark` returns the highest committed `change_seq`, and that the visibility-order guarantee holds at read time. Confirm that the watermark query and the change queries read only committed rows.
3. **4xx responses.** The brief covers network errors, 5xx and `resync_required`, but not other 4xx responses (for example, 401 or 429). Decide whether 401 triggers re-authentication and whether 429 uses `Retry-After`.
4. **Downloads longer than 7 days.** If a download, or a long run of pauses, takes more than 7 days from `W`, step 5 can fail with `410` on every attempt. Decide whether the server should keep a long-running download's window open, or whether the client should accept that the download has failed and restart.
5. **15-minute limit and continued pages.** The plan treats one incremental run, including all its `has_more` batches, as one run. Confirm this reading of "at most once every 15 minutes".
6. **Image or media assets.** Product images or documents are not in the brief and are not covered. Their size would change the Wi-Fi-only and storage limits.
7. **Storage budget.** About 400,000 rows at roughly 2 KB is about 800 MB of JSON before SQLite overhead, and the staging copy briefly doubles this during a rebuild. Confirm that devices have room for this, or consider a compact representation.