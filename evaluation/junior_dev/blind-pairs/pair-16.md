# Pair 16

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

# Offline catalogue sync plan

## Overview

The app needs the full catalogue (about 400,000 products at about 2 KB each, roughly 800 MB) in its local SQLite database, so reps can browse and quote offline. Sync has two parts:

- **Full download.** A bulk copy of the catalogue, fetched in pages. It takes hours, must survive interruptions, and must not miss edits made while it runs. It ends with a catch-up phase that replays those edits.
- **Incremental sync.** A small, frequent fetch of whatever changed since the device last synced.

### Terms

- **`change_seq`**: a number the server stamps on every product insert, update or delete. It comes from one global, strictly increasing sequence and is assigned at commit. Rows therefore become visible in `change_seq` order, and a lower number never appears after a higher one.
- **Tombstone**: a deleted product's row, kept with `deleted = true` for 7 days and then purged. Tombstones are how deletes reach devices.
- **Keyset pagination**: "give me the next 500 products with id greater than this one", instead of "give me page N".
- **Staging table**: a private copy of the products table that a full download fills while the UI keeps reading the live table.
- **Trigger**: what starts a step.
- **Wi-Fi only**: enforced by the client, which checks the network type before each request that belongs to a full download.

### The idea in five moves

1. **Note the position.** When a full download starts, the client asks the server for its current `change_seq` and stores it as `start_seq`.
2. **Download.** The client downloads all pages into the staging table. Edits made meanwhile may or may not be in the pages, depending on timing.
3. **Catch up.** When all pages are saved, the client fetches every change after `start_seq` and applies it to the staging table. This is sufficient because any edit committed after `start_seq` has a higher `change_seq` and so appears in the changes. Any edit committed before it was already visible when the pages were read.
4. **Swap.** The client swaps the staging table in for the live one in a single transaction.
5. **Ignore stale changes.** A change is applied only if its `change_seq` is higher than the one stored on the local row. A change that a page already included is skipped, so applying the same change twice is harmless.

## Rules that apply to every request

**Retry rule.** Only a network error or a 5xx response is retried, and the same request is repeated.

- The client makes at most 5 attempts in total, waiting 2 s, 4 s, 8 s, then 16 s between them.
- After the fifth failure the client stops and waits for the next trigger. Everything already saved is kept, and the next run continues from the saved cursor or position.
- An HTTP 410 is not retried. It goes to step 10.
- Other 4xx responses are not retried. The client logs them and stops until the next trigger.

Steps below say "retry per the retry rule" and do not repeat these details.

## Steps

### 1. Build three server endpoints

- **Trigger:** one-time server work, done before any client work.
- **Data:**
  - `GET /catalogue/position` returns `{ "seq": N }`, the highest `change_seq` committed so far.
  - `GET /catalogue/full?after=<product_id>` returns up to 500 non-deleted products ordered by product id ascending, plus `next_after` (the last id in the page, or `null` on the final page). Omit `after` for the first page.
  - `GET /catalogue/changes?since=<seq>` returns up to 1,000 changes with `change_seq > since`, ordered by `change_seq` ascending. Deletes are included as tombstones. The response also carries `has_more`, which is true when more changes exist beyond this batch.
- **Resync rule:** the server tracks `oldest_valid_seq`, the highest `change_seq` of any tombstone it has purged. If `since < oldest_valid_seq`, the client may have missed a purged delete, so the server answers **HTTP 410 with `resync_required`** instead of changes.
- **State:** Postgres only. The server keeps no per-client state. It needs indexes on `change_seq` and on product id (they may already exist).
- **On failure:** the server returns standard 5xx errors. The client handles them with the retry rule.

### 2. Create the client state

- **Trigger:** first launch after an app upgrade, as a SQLite migration.
- **Data:** three tables in the existing local SQLite database.
  - `products`: the live catalogue, which the UI reads. Each row includes its `change_seq`.
  - `products_staging`: same columns, used only while a full download is in progress.
  - `sync_state`: a single row holding:
    - `phase`: `none`, `downloading` or `catching_up`
    - `start_seq`: the server position taken when the download began
    - `after_id`: the keyset cursor for the full download
    - `catchup_seq`: how far the catch-up has got (starts equal to `start_seq`)
    - `last_seq`: the position of the live catalogue
    - `last_incremental_at`: when incremental sync last started
- **State:** all in SQLite, so everything survives an app kill or restart.
- **On failure:** if the migration fails, sync does not start. The app keeps working with whatever it had, and the error is reported.

### 3. Start a full download

- **Trigger:** the app launches, returns to the foreground, or Wi-Fi returns; the device is on Wi-Fi; and there is no catalogue yet (`phase = none` and no `last_seq`). Step 10 also runs this step directly after a 410.
- **Data:** the client calls `GET /catalogue/position` and receives `seq`.
- **State:** in one transaction, the client empties `products_staging` and writes `phase = downloading`, `start_seq = seq`, `catchup_seq = seq`, `after_id = null`. `products` is not touched.
- **On failure:** retry per the retry rule. If it still fails, nothing has changed, and the next trigger starts again from here.

### 4. Download pages, one at a time

- **Trigger:** `phase = downloading` and the device is on Wi-Fi.
- **Data:** `GET /catalogue/full?after=<after_id>`, 500 products per page (about 1 MB, so about 800 pages in all). Only one page request is ever in flight.
- **State:** after each page, the client writes its rows to `products_staging` and sets `after_id = next_after` **in the same SQLite transaction**. A page is therefore either fully saved with its cursor advanced, or not saved at all. When `next_after` is `null`, the same transaction also sets `phase = catching_up`.
- **On failure:** retry a failed request per the retry rule. If the transaction fails, it rolls back and the client requests the same page again.

### 5. Pause on cellular, resume on Wi-Fi

- **Trigger:** the network changes from Wi-Fi to cellular (or to none) while a download or catch-up is running.
- **Data:** none. The client finishes the request in flight, saves it as in step 4 (or step 7), then stops before making the next one.
- **State:** `sync_state` is already correct (`phase`, `after_id`, `catchup_seq`), so nothing extra is stored.
- **On resume:** the client carries on from the saved cursor when Wi-Fi returns (a network-change callback), or at the next launch or foreground.

### 6. Resume after an interruption

- **Trigger:** the app was killed, the phone restarted, or the network was lost, and the app then launches, returns to the foreground, or regains Wi-Fi with `phase` of `downloading` or `catching_up`.
- **Data:** the client reads `sync_state` and continues step 4 from `after_id`, or step 7 from `catchup_seq`. It never goes back to page 1.
- **State:** `after_id` always points just past the last fully saved page (step 4 guarantees this), and `catchup_seq` always matches the last saved batch (step 7). At worst, the one request that was in flight is made again.
- **On failure:** nothing specific. If `start_seq` has aged out of the 7-day window, the catch-up gets a 410, and step 10 restarts the whole download.

### 7. Catch up on edits made during the download

- **Trigger:** `phase = catching_up` (every page is saved) and the device is on Wi-Fi. Catch-up is part of the full download, so it follows the Wi-Fi-only rule (see assumptions).
- **Data:** `GET /catalogue/changes?since=<catchup_seq>`, repeated while `has_more` is true.
- **How each change is applied to `products_staging`:**
  - Apply it only if no local row exists, or its `change_seq` is greater than the row's.
  - An insert or update writes the row.
  - A tombstone deletes the row, if there is one.
  - A change that is not newer than the row is skipped. This happens when a page already held a newer version.
- **State:** after each batch, the client saves the batch and the new `catchup_seq` in one transaction, so a restart resumes mid-catch-up.
- **On failure:** retry per the retry rule. A 410 means `start_seq` is too old, so go to step 10.

### 8. Swap in the new catalogue

- **Trigger:** the catch-up receives a batch with `has_more = false`.
- **Data:** none.
- **State:** in a single SQLite transaction, the client:
  1. drops `products`, renames `products_staging` to `products`, and creates a new empty `products_staging`;
  2. sets `last_seq = catchup_seq` and `phase = none`, and clears `start_seq`, `catchup_seq` and `after_id`.

  The transaction makes the swap all-or-nothing. Reps see the old catalogue until it commits and the complete new one afterwards. Edits made after the catch-up finished arrive through step 9.
- **On failure:** the transaction rolls back and the old `products` stays in place. The next trigger retries the swap.

### 9. Run incremental sync

- **Trigger:** app launch or return to the foreground, at most once every 15 minutes. The client compares now with `last_incremental_at`, which is stored in SQLite so the limit holds across restarts. It needs `phase = none` and a `last_seq`, and it runs on any network. It does not run while a full download or catch-up is in progress.
- **Data:** `GET /catalogue/changes?since=<last_seq>`, up to 1,000 changes per response, repeated while `has_more` is true. Changes are applied to `products` with the same `change_seq` comparison as step 7. Tombstones delete the row.
- **State:** each batch is applied and `last_seq` advanced in one transaction. `last_incremental_at` is set when the sync starts, so a failed attempt still counts against the 15 minutes.
- **On failure:** retry per the retry rule. After that the client stops and keeps its progress. A 410 goes to step 10.

### 10. Handle "resync required" (410)

- **Trigger:** `GET /catalogue/changes` returns 410, from step 7 or step 9. The device's position is older than the 7-day tombstone window, so it may have missed deletes.
- **Data:** none, apart from the calls made by step 3.
- **State:** the client leaves `products` exactly as it is, so reps keep using their existing catalogue. It then runs step 3, which empties the staging table and takes a fresh `start_seq`, followed by steps 4 to 8 to build the replacement. Incremental sync stays off while `phase` is not `none`. The swap in step 8 is the only point where the old catalogue is replaced.
- **On failure:** the earlier steps handle their own failures. If step 3 fails, no flag is needed: the stale position still returns a 410 at the next trigger, which brings the client back here. The old catalogue is never removed before step 8 commits.

## Open question: browsing during the first download

Product has not decided whether reps may browse the partly downloaded catalogue during their first download, or must see a progress screen until it finishes. This plan does not decide it, and the sync steps are the same either way.

- **If browsing is allowed:** the UI reads `products_staging` for a first-time user. Pages arrive in product-id order, so reps would see an arbitrary slice, and the data would not yet include the catch-up from step 7.
- **If it is not allowed:** the UI shows a progress screen, using the number of rows in `products_staging` against the 400,000 total. (`after_id` is a product id, not a count, so it is a poor progress measure.)

Whichever is chosen, a resync (step 10) always keeps showing the old `products` table.

## Assumptions to confirm

- Catch-up (step 7) and the position request that starts a download (step 3) count as part of the full download, so they also run only on Wi-Fi.
- The full download leaves out tombstones. The client learns about deletes only from `/changes`.
- The 15-minute limit counts from the last sync attempt, not the last success.
- If a download is paused for more than 7 days, the catch-up gets a 410 and the download restarts.

---

# Document B

# Catalogue sync plan

The app keeps a full copy of the catalogue (about 400,000 products at roughly 2 KB each, about 800 MB) in its local SQLite database, so reps can browse and quote offline. Today the Catalogue service stores products in Postgres and there is no sync API, so this plan adds three endpoints. The first full download is built in a separate staging table, so an interrupted download resumes where it stopped and the live data is never half replaced. When the download is complete and caught up, one transaction swaps it in. After that, small incremental updates keep the copy current.

## Terms

- **change_seq**: a number the Catalogue service stamps on a product row at every insert, update or delete. It comes from one global, strictly increasing sequence and is assigned at commit, so rows become visible in change_seq order. A higher change_seq means a newer version of that product.
- **Tombstone**: a deleted product. The server keeps the row with `deleted = true` for 7 days and then purges it.
- **start_seq**: the highest committed change_seq on the server when a full download begins. Every change made after that has a higher change_seq, so replaying changes after start_seq catches everything the page-by-page download may have missed.
- **cursor**: the id of the last product in the last fully saved page. The next page request asks for products with a higher id.
- **last_seq**: the change_seq of the last change applied to the live `products` table. The next incremental sync asks for changes after it.
- **catchup_seq**: the same idea as last_seq, but for the catch-up applied to staging (step 4).
- **Staging**: the `products_staging` table, where a full download is built while `products` stays untouched.
- **Transaction**: a SQLite transaction. Everything in it is saved together or not at all.

## Server API (new)

- `POST /catalogue/full/start`: keeps no server state. Returns `{start_seq}`, the current highest committed change_seq.
- `GET /catalogue/full?after_id=<cursor>`: returns up to 500 non-deleted products, ordered by product id ascending (keyset pagination), each with its change_seq, plus `done: true` when no products remain.
- `GET /catalogue/changes?after_seq=<n>`: returns up to 1,000 changes with change_seq above n, in change_seq order, plus `next_seq` and `has_more`.
  - An update change is the full product row with its change_seq. A delete change is the product id, its change_seq and `deleted = true`.
  - `next_seq` is the change_seq of the last change returned. With no changes, the list is empty, `next_seq = n` and `has_more = false`, so the client's saved position stays where it was.
  - If n is older than the 7-day tombstone window, it returns `410 resync_required`.

## Client storage (the app's existing SQLite database)

- `products`: the live catalogue that reps browse. Every row stores its change_seq.
- `products_staging`: same columns, used only during a full download. While it exists the device holds two copies, so a full download needs about 1.6 GB of free space.
- `sync_state`: one row with `phase` (`idle`, `downloading`, `catching_up`), `start_seq`, `cursor`, `catchup_seq`, `last_seq` and `last_incremental_at`.

## How it runs

1. **Trigger.** App launch or return to the foreground. Wi-Fi returning is also a trigger, but only while `phase = downloading` (it ends a pause in step 3); when idle it starts nothing. Choose by `sync_state`:
   - `last_seq` empty and `phase = idle`: there is no catalogue yet, go to step 2.
   - `phase = downloading`: resume at step 3. Do not reset the download.
   - `phase = catching_up`: resume at step 4.
   - Otherwise (`phase = idle` with a `last_seq`): go to step 6, which waits until 15 minutes after `last_incremental_at`.
2. **Start a full download.** Call `POST /catalogue/full/start`. In one transaction, empty `products_staging`, save `start_seq`, set `cursor` empty and set `phase = downloading`. This is the only step that resets staging and the cursor. If the call fails, retry it (step 8). Nothing has been saved yet, so the next trigger starts again.
3. **Download pages.** Only on Wi-Fi, one page at a time, never in parallel. Call `GET /catalogue/full?after_id=<cursor>`. In one transaction, insert the page into `products_staging` and set `cursor` to its last product id. A page is either fully saved with its cursor or not saved at all, so after a kill or restart the next trigger resumes from the saved cursor, not from page 1. If the device leaves Wi-Fi, the current page finishes and the download pauses until Wi-Fi returns. When the server says `done`, set `phase = catching_up` and `catchup_seq = start_seq`.
4. **Catch up.** Edits continue all day, so staging may be missing changes made during the download, including a new product whose id is lower than the cursor (its change_seq is above start_seq, so catch-up delivers it). Call `GET /catalogue/changes?after_seq=<catchup_seq>` on any network. Apply each page to `products_staging` in one transaction together with `catchup_seq = next_seq`. Repeat while `has_more`; when it is false, go to step 5.
   - **Applying a change:** upsert the product if it is not deleted. If it is deleted, delete the staged row; if there is none (the product was deleted before its page was fetched, so the full endpoint never returned it), there is nothing to delete.
   - **Skip rule:** skip a change if the staged row already has an equal or higher change_seq, because the page download may already have fetched a newer version.
5. **Swap.** In one transaction: drop `products`, rename `products_staging` to `products`, create a new empty staging table, set `last_seq = catchup_seq`, clear `last_incremental_at` and set `phase = idle`. If the app dies mid-swap, the transaction rolls back and the next launch repeats step 4 (which finds nothing new) and the swap. Reps keep seeing the old `products` until the swap commits. Edits made after the last catch-up page are not in the swap. They arrive through step 6, which runs at the next trigger without waiting (because `last_incremental_at` is empty) and asks for changes after `last_seq`.
6. **Incremental sync.** Runs at app launch and on each return to the foreground, at most once every 15 minutes, on any network, and only when `phase = idle`. Call `GET /catalogue/changes?after_seq=<last_seq>`. Apply each page to `products` in one transaction with the same applying and skip rules as step 4, and set `last_seq = next_seq` in that transaction. Repeat while `has_more`, then set `last_incremental_at`. Reps can keep browsing and quoting during the sync, and each page becomes visible when its transaction commits, so they may briefly see a mix of old and new versions. If the app is killed part-way, the committed pages stay, and the next trigger continues from the saved `last_seq` without waiting 15 minutes, because `last_incremental_at` is only set at the end.
7. **Resync required.** If `/catalogue/changes` returns 410, either in step 4 (the request after `catchup_seq`, for example after a download that took more than 7 days) or in step 6 (a long offline gap), go back to step 2. Step 2 empties staging, clears the cursor, takes a new `start_seq` and sets `phase = downloading`. `products` and `last_seq` are not touched, so reps keep their existing catalogue until the swap in step 5 replaces it. A first download that takes more than 7 days will hit this repeatedly and never finish.
8. **Retries.** After a network error or a 5xx response, repeat the same request, waiting 2 s, then 4 s, 8 s and 16 s: at most 5 attempts in total. Other 4xx responses are not retried, except the 410 in step 7. After the 5th failure, stop and wait for the next trigger. Everything already saved (staging, cursor, catchup_seq, last_seq) is kept.

## What happens when things fail

| Failure | Result |
| --- | --- |
| App killed or phone restarted during step 3 | Resume from the saved cursor on the next trigger. |
| App killed during step 4 | Resume from the saved `catchup_seq`. |
| App killed during step 5 | The swap rolls back. Redo steps 4 and 5. |
| App killed during step 6 | Resume from the saved `last_seq` on the next trigger. |
| Network lost or 5xx | Retry as in step 8, then wait for the next trigger. |
| Cellular instead of Wi-Fi during a full download | Finish the current page, pause, resume on Wi-Fi. Incremental sync is unaffected. |
| 410 resync_required | Full download again (step 7). Existing `products` stay visible. |

## Build and rollout

Not decided yet: the order of delivery, a feature flag and a staged rollout. Build the three endpoints first, then the client.

## Open questions

- Product has not decided whether reps may browse the partly downloaded catalogue during their first download or should see a progress screen until it finishes. This plan does not decide it. As written, `products` stays empty until the swap, so a first-time rep sees no catalogue until it completes.
- How long the swap takes on an 800 MB table, and whether it blocks reads of `products` while it runs, has not been measured. It depends on the SQLite journal mode and needs a test on a real device.
