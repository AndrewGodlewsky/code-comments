# Offline product catalogue sync for the field-sales app: plan

## Summary

The Catalogue service keeps products in Postgres. Each insert, update and delete gives the row a `change_seq`, and deletes stay as tombstones for 7 days. The app has one SQLite file, used for settings, and there is no sync API yet. This plan adds one.

The device downloads the whole catalogue (about 400,000 products) in pages of 500, over Wi-Fi only, into a staging table. Before the first page, it records a watermark W. After the last page, it replays every change made since W. Then it swaps the finished copy in as the table reps browse, in one transaction, so reps never see a half-built catalogue. After that, it pulls changes in order at launch and when the app returns to the foreground, at most once every 15 minutes.

## Terms

- **Catalogue file:** a separate SQLite database for catalogue data. Settings stay in the existing file, so large catalogue writes and rebuilds never touch them.
- **Postgres:** the server's database, which holds all products.
- **change_seq:** a number from one global counter on the server that only goes up. Each insert, update or delete gives the row a new, higher number, assigned when the change is committed. Changes become visible in this order, so "every change above N" has no gaps.
- **Tombstone:** the row a delete leaves on the server (`deleted = true`), so devices learn about the delete. The server purges tombstones 7 days after the delete.
- **Purge horizon H:** the highest `change_seq` among the tombstones the server has purged.
- **Watermark W:** the highest `change_seq` committed when a download starts.
- **Cursor:** a saved `change_seq` that shows how far a table has been brought up to date.
- **Keyset pagination:** each page asks for products with an id greater than the last id of the previous page, not for a page number.
- **product_next:** the staging table that a download fills. Reps do not browse it.
- **product_live:** the table reps browse.
- **Swap:** in one transaction, drop `product_live` and rename `product_next` to `product_live`.
- **sync_state:** one row in the catalogue file that records what the sync is doing and how far it has got.
- **410 resync_required:** the server's answer when a device's cursor is older than the purge horizon.
- **gzip:** compresses a response so that it downloads faster.
- **Retry:** sending the same request again.
- **NWPathMonitor:** the iOS API that reports the current network type.
- **WorkManager:** Android's background job scheduler.
- **Background URL session:** the iOS mechanism that lets a download continue while the app is in the background.

## Server endpoints

| Endpoint | Purpose | Response |
|---|---|---|
| `GET /sync/watermark` | Current highest committed `change_seq` | `{ "watermark": W }` |
| `GET /sync/products?after_id=&limit=500` | One page of live products, ordered by id ascending. Each item carries its `change_seq`. | `{ "items": [{ "id", "change_seq", "product" }], "next_after_id", "done" }` |
| `GET /sync/changes?since=N&limit=1000` | Changes with `change_seq > N`, ascending, including tombstones | `{ "changes": [{ "change_seq", "id", "deleted", "product" or null }], "next_since", "has_more" }`, or `410 resync_required` |

- The server answers `410 resync_required` when `N < H`. `N = H` is safe. Every purged tombstone has a `change_seq` at most H, so none of them comes after N, and every change above N is still stored.
- The page endpoint keeps no session. Its only cursor is `after_id`.
- Purging creates no change rows and stamps no `change_seq`.
- These server behaviours are assumptions to confirm (see open questions).

## Client state

`sync_state` is one row in the catalogue file:

- **download_state:** `idle` (no download running), `downloading`, `paused_cellular` or `failed_exhausted`. It describes only the download. A device has a catalogue once `live_cursor` is set, whatever this value is.
- **watermark_W:** the W that this download started from.
- **download_last_id:** the id of the last product on the last fully saved page.
- **download_pages_saved:** how many pages are saved.
- **pages_complete:** true once the last page is saved. After that, the download is in catch-up.
- **next_cursor:** the `change_seq` that `product_next` is caught up to. Starts at W.
- **live_cursor:** the `change_seq` that `product_live` is caught up to. Null until the first swap, so null means the device has no catalogue.
- **last_incremental_at:** when the last incremental run started.

Every `sync_state` update is written in the same transaction as the page or batch it describes. A cursor therefore never runs ahead of the rows it describes.

## The Wi-Fi gate

The gate applies to the watermark request, every page request and every catch-up batch. Incremental sync (step 6) is not gated and may use any network.

- Before each request, check that the device is on unmetered Wi-Fi. On Android, the network must have `NET_CAPABILITY_NOT_METERED`. On iOS, NWPathMonitor must report a Wi-Fi interface.
- On cellular or no network, set `download_state = paused_cellular` and stop. The page or batch in progress is already saved, so the pause falls on a boundary.
- If the link drops during a request, that request is a network error, and step 9 applies. Its retries wait for Wi-Fi and keep their count.
- When Wi-Fi returns, step 8 resumes the download.

## Steps

Steps 1 to 6 are the main flow. Steps 7 to 10 apply to the steps above them.

### 1. Start a full download

- **Triggers:** one of three things.
  - First install: `live_cursor` is null and `download_state` is `idle`.
  - A resync (step 7) has set `download_state = downloading`.
  - A resume (step 8) finds `watermark_W` null.
- **What happens:** pass the Wi-Fi gate. Then call `GET /sync/watermark` to get W. Write nothing before W arrives. Then, in one transaction, drop any old `product_next`, create an empty one, and set `download_state = downloading`, `watermark_W = W`, `download_last_id = null`, `download_pages_saved = 0`, `pages_complete = false` and `next_cursor = W`. Any change made after this point has a `change_seq` above W, so step 4 delivers it.
- **Data moved:** W only.
- **Kept in:** `sync_state` and the staging table, in that one transaction.
- **On failure:** a network error or 5xx goes to step 9. If the app is killed before the transaction, nothing has changed, and the next start fetches W again. A staging table left by an earlier run is dropped here, so a failed earlier cleanup cannot affect the catalogue.

### 2. Fetch one page

- **Triggers:** step 1 has finished; or step 3 has saved a page and `pages_complete` is false; or step 8 resumes the page phase. The Wi-Fi gate must pass first.
- **What happens:** request `GET /sync/products?after_id=download_last_id&limit=500`. The first page omits `after_id`. Pages are about 1 MB, so request them gzipped. Pages are requested one at a time, never in parallel.
- **Data moved:** up to 500 products, each with its `change_seq`.
- **Kept in:** nothing. Nothing is written until the whole response has arrived and passed the check in step 3.
- **On failure:** a network error, a timeout or a 5xx goes to step 9. A timeout counts as a network error. A partly received body is discarded, and the same page is requested again.

### 3. Save the page

- **Trigger:** a complete page has arrived and passes the check. The check is: an array of at most 500 items, each with an `id` and a `change_seq`, with ids strictly increasing and greater than `download_last_id`.
- **What happens:** in one transaction, write each product to `product_next` by id, set `download_last_id` to the page's last id, and add one to `download_pages_saved`. If `done` is true, also set `pages_complete = true` and go to step 4. Otherwise go to step 2.
- **Data moved:** the page's rows.
- **Kept in:** the staging table and `sync_state`, in the same transaction.
- **On failure:** if the app is killed during the transaction, SQLite rolls it back. The cursor still points at the previous page, so that page is fetched again. Writing a page twice is harmless, because it writes the same rows. A page that fails the check is treated as a 5xx and goes to step 9.

### 4. Catch up on changes made during the download

- **Triggers:** `pages_complete` is true. Repeat while `has_more` is true.
- **What happens:** for each batch, pass the Wi-Fi gate. Then call `GET /sync/changes?since=next_cursor&limit=1000` and apply the changes to `product_next`. Each batch is one transaction that also sets `next_cursor = next_since`. Apply each change by these rules:
  - **Upsert:** write the product only if its row is missing, or its stored `change_seq` is lower than the change's.
  - **Delete:** remove the row with that id, if it exists. If there is no such row, nothing happens.
- When `has_more` is false, go to step 5.
- **Why nothing is missed:** W is the highest committed `change_seq`, and `change_seq` order is commit order. So every change not already in W has a `change_seq` above W, and catch-up replays all of them in order. A page may read a product before or after a later change. Either way the result is right:
  - The product changed before its page was read. The page has the new state. The replayed change is not newer, so it is skipped.
  - The product changed after its page was read. The page has the old state. The replayed change is newer, so it is applied.
  - The product was created with an id the pages had already passed. No page has it. Catch-up adds it.
  - The product was deleted. The tombstone removes the row if the page already had it. If the delete came before the page was read, the page does not have it, and nothing is removed.
  - Changes replay in order, after all pages, so no older upsert can follow a delete for the same id. Repeating a batch is harmless for the same reasons.
  - This relies on product ids never being reused (see open questions).
- **Data moved:** batches of up to 1,000 changes, tombstones included.
- **Kept in:** the staging table and `next_cursor`, in each batch's transaction.
- **On failure:** a network error or 5xx goes to step 9, and the cursor stays at the last applied batch. `410 resync_required` goes to step 7. If the app is killed, step 8 resumes from the saved cursor.

### 5. Swap in the finished copy

- **Triggers:** the last catch-up batch returns `has_more` false. A resync (step 7) reaches the same swap the same way.
- **What happens:** in one transaction, drop the old `product_live` (there is none on first install), rename `product_next` to `product_live`, set `live_cursor = next_cursor`, set `download_state = idle`, and clear `watermark_W`, `download_last_id`, `download_pages_saved`, `pages_complete` and `next_cursor`. The app always reads the name `product_live`. The rename commits with the swap, so a read sees the old table or the new one, never neither. The implementer must check how a read that is already open during the rename behaves.
- **Data moved:** none over the network.
- **Kept in:** the catalogue file.
- **On failure:** if the app is killed before the commit, the old `product_live` and the staging table both remain intact, and step 8 resumes catch-up. What reps see before the first swap is an open question.
- After the swap, the copy is only as current as its last catch-up batch. Step 6 covers what happens next.

### 6. Incremental sync

- **Triggers:** the app launches or returns to the foreground, and all of these hold: `live_cursor` is set, `download_state` is `idle`, and `last_incremental_at` is at least 15 minutes ago. Any network may be used.
- **What happens:** write `last_incremental_at` = now when the run starts. Then call `GET /sync/changes?since=live_cursor&limit=1000` and apply each batch to `product_live`, using the rules in step 4. A delete removes the row, so reps stop seeing that product. Each batch is one transaction that also sets `live_cursor = next_since`. Repeat while `has_more` is true. One run covers all of its batches, and the 15-minute limit applies to the whole run. A run that fails still counts, so the next run waits for the 15-minute gate.
- **While a download runs** (`download_state` is not `idle`), this step does not run. `product_live` stays at its last cursor, and `last_incremental_at` is not changed. The old cursor is never applied to a rebuild.
- **After a swap,** `last_incremental_at` is not reset. If it is older than 15 minutes, the next trigger runs incremental sync at once. That is correct, because the new copy is only as current as its last catch-up batch.
- **Data moved:** batches of up to 1,000 changes, including deletes.
- **Kept in:** `product_live`, `live_cursor` and `last_incremental_at`, each batch in one transaction.
- **On failure:** a network error or 5xx goes to step 9. The cursor stays at the last applied batch, and the next trigger continues from there. `410 resync_required` goes to step 7.

### 7. Resync required

- **Trigger:** step 4 or step 6 gets `410 resync_required`. The device's cursor is older than the purge horizon, which happens when it has been offline for longer than the 7-day window.
- **What happens:** in one transaction, set `download_state = downloading` and clear `watermark_W`, `download_last_id`, `download_pages_saved`, `pages_complete` and `next_cursor`. Then step 1 runs, subject to the Wi-Fi gate. It fetches a new W and rebuilds the staging table. `product_live` is not touched, so reps keep the old catalogue until the swap in step 5.
- **Data moved:** a full download, steps 1 to 5 again.
- **Kept in:** `sync_state`, the staging table and the existing `product_live`.
- **On failure:** the same as steps 1 to 5. If the rebuild is interrupted, reps keep the old catalogue, and step 8 resumes the rebuild.

### 8. Resume after interruption

- **Triggers:** the app launches, returns to the foreground, or starts after being killed. Also when Wi-Fi returns after a pause or a `failed_exhausted` download. This applies while `download_state` is `downloading`, `paused_cellular` or `failed_exhausted`. A first-install launch, with `live_cursor` null, goes to step 1, because nothing is in progress.
- **What happens:** pass the Wi-Fi gate first. Then:
  - if `watermark_W` is null, go to step 1 (the app was killed after step 7 cleared the state but before W arrived);
  - otherwise set `download_state = downloading`. If `pages_complete` is false, go to step 2 with `after_id = download_last_id`. If it is true, go to step 4 with `since = next_cursor`.
- **Data moved:** none until the next request.
- **Kept in:** everything saved in the last committed transaction. A download that has a watermark never restarts from page 1.
- **On failure:** a resume into catch-up that gets `410` goes to step 7. A resume that fails again waits for the next trigger (step 9).

### 9. Retries for network errors and 5xx responses

- **Triggers:** a request in steps 1, 2, 4 or 6 fails with a network error, a timeout or a 5xx response. Or step 3 finds a page that fails the check.
- **What happens:** send the same request again after waits of 2 s, 4 s, 8 s and 16 s. That is at most 5 attempts in total, with a 30-second total wait. Nothing new is requested. If the device moves to cellular during the retries, the retry waits for Wi-Fi and keeps its count.
- **Data moved:** the same request.
- **Kept in:** memory only, for that one request. The count is not saved.
- **If all 5 attempts fail:**
  - for a download, set `download_state = failed_exhausted`;
  - for incremental sync, leave `live_cursor` where it is.

  Everything already saved is kept. There are no more automatic retries. The next trigger starts a fresh count of 5. The triggers are app launch or foreground, Wi-Fi returning (for a download), and the 15-minute gate (for incremental sync).
- **Other 4xx responses** (not `410`) are not retried. The request counts as failed, and the same end state applies.

### 10. Connectivity and background work

- **Triggers:** the OS reports a connectivity change, or the app goes to the background during a download.
- **What happens:** a download runs only on Wi-Fi. On iOS, a background URL session carries it. On Android, WorkManager runs it with an `UNMETERED` constraint. If Wi-Fi is lost between requests, the Wi-Fi gate pauses the download. If it is lost during a request, step 9 applies.
- **Data moved:** none.
- **Kept in:** `download_state`, the cursors and the counters. They are saved at every step boundary.
- **On failure:** the OS may stop background work at any time. Each page or batch is saved atomically, so only the one in flight is lost. The next launch resumes at step 8.

## What the rep sees

| Device state | What the rep sees | Next trigger |
|---|---|---|
| First install, download running | No catalogue until the first swap (see open questions) | Launch, foreground, Wi-Fi returns |
| First install, `failed_exhausted` | No catalogue. The first-download screen is decided with open question 1. | Launch, foreground, Wi-Fi returns |
| Has catalogue, steady state | The catalogue, updated at launch and foreground | Launch or foreground, after 15 minutes |
| Has catalogue, resync running | The old catalogue, unchanged, until the swap | Launch, foreground, Wi-Fi returns |
| Has catalogue, `failed_exhausted` | The old catalogue, unchanged. Nothing tells the rep (open question 8). It gets no incremental updates (open question 9). | Launch, foreground, Wi-Fi returns |

## Open questions (not decided)

1. **Browsing during the first download.** Product has not decided whether reps can browse the partly downloaded catalogue during their first download, or should see a progress screen until it finishes. The design above works either way. Browsing during the download would mean reads come from `product_next` or a partial view of it. That changes the swap (step 5) and the first-install screen. This plan does not choose.
2. **Server behaviour.** Confirm that `GET /sync/watermark` returns the highest committed `change_seq`, that the watermark and change queries read only committed rows, that purging creates no change rows and stamps no `change_seq`, and that product ids are never reused.
3. **Other 4xx responses.** The brief does not cover responses such as 401 or 429. Decide whether 401 triggers re-authentication, and whether 429 uses `Retry-After`.
4. **Downloads longer than 7 days.** If a download, or a long run of pauses, takes more than 7 days from W, catch-up gets `410` on every attempt. Decide whether the server keeps a long download's window open, or whether the client accepts the failure and restarts.
5. **The 15-minute limit.** The plan treats one incremental run, including all its batches, as one run. It also counts a failed run. Confirm this reading of "at most once every 15 minutes".
6. **Images and media.** Product images and documents are not in the brief and are not covered. Their size would change the Wi-Fi-only and storage limits.
7. **Storage budget.** About 400,000 products at roughly 2 KB is about 800 MB of JSON before SQLite overhead. The staging copy briefly doubles this during a rebuild. Confirm that devices have room, or consider a more compact representation.
8. **Telling the rep.** When a download stops at `failed_exhausted`, nothing in this plan tells the rep. Decide whether the app shows a message, and what it says.
9. **Stale catalogue during a failed resync.** While a resync is running or `failed_exhausted`, the old catalogue gets no incremental updates. Decide whether incremental sync should keep the old copy current during a rebuild, or accept that it stays frozen until the rebuild finishes.