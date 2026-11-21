# Offline product catalogue sync

## Summary

The field-sales app keeps a full local copy of about 400,000 products (about 2 KB each) in SQLite, so reps can browse and quote offline. The copy is built in two phases: a full download in pages of 500, then small incremental updates that replay changes in order. The full download fills a separate staging table and swaps it in only after it has replayed every change made since the download began, so no change is missed. Today the catalogue exists only on the server. There is no sync API yet, so the endpoints below are new.

## Terms

- **Postgres**: the server database that holds the products.
- **SQLite**: a small database file on the phone. The app already uses it for settings.
- **change_seq**: a number the server stamps on every product insert, update or delete. It comes from one counter that only goes up, so a larger number means a later change.
- **Tombstone**: a deleted product, kept as a row marked deleted for 7 days so devices can learn about the delete. After 7 days the server purges it.
- **Keyset pagination**: each page asks for the products with ids after the last id of the previous page, rather than asking for "page 7".
- **Cursor**: the id of the last product in the last page the device saved.
- **start_seq**: the latest change_seq when a full download begins.
- **last_seq**: the change_seq of the last change the device has applied.
- **Staging table** (`products_staging`): holds the new catalogue while it downloads. The app's browsing screens read only `products`.
- **Swap**: replacing all of `products` with the contents of `products_staging` in one SQLite transaction, which either completes fully or not at all.
- **Newer-wins rule**: a product row or delete is applied only if its change_seq is higher than the change_seq the device already holds for that product. This stops an older change from overwriting newer data.
- **Resync required**: the server's answer (HTTP 410) when the device asks for changes older than the 7-day tombstone window.

## Server endpoints

- `POST /catalogue/full/start` returns `start_seq`, the latest change_seq. Because change_seq is assigned at commit and rows become visible in change_seq order, every change up to `start_seq` is already visible to readers.
- `GET /catalogue/full?after_id=<id>&limit=500` returns the next 500 live products (no tombstones), ordered by id ascending, each with its change_seq. Leave `after_id` out for the first page.
- `GET /catalogue/changes?since=<seq>` returns up to 1,000 changes after `since`, in change_seq order, including deletes. If `since` is older than the 7-day window, it answers 410 with "resync required".

## Device state

One `sync_state` row in SQLite holds: `download_state` (none, downloading or complete), `start_seq`, `cursor`, `last_seq`, and `last_incremental_started_at`.

The first download needs room for two full copies of the catalogue (roughly 0.8 GB each at 2 KB per product) until the swap.

## Rules that apply to every step

- Each saved page writes its rows and its new cursor or last_seq in one transaction, so the saved position never runs ahead of the saved data. This means a killed app can only lose work that was not yet saved.
- The newer-wins rule applies to every row and delete the device writes.
- The full download and its catch-up run only on Wi-Fi. Incremental sync may use any network.
- Incremental sync does not run while a full download is in progress. The catch-up in step 3 already covers the same changes, and running both would fight over last_seq.
- Pages and change requests are made one at a time, never in parallel.
- **Retry rule**: after a network error or a 5xx response, retry the same request. Wait 2 s before the first retry, then double the wait each time (2 s, 4 s, 8 s, 16 s). Make at most 5 attempts in total. After the fifth failure, stop, keep everything already saved, and wait for the next trigger.

## Steps

1. **Start a full download.**
   - Trigger: first launch with no local catalogue, or a resync (step 6).
   - Does: on Wi-Fi, call `POST /catalogue/full/start`. Save `start_seq` in `sync_state`, set `cursor` to empty and `download_state` to downloading. Empty `products_staging`.
   - Data: `start_seq` is saved. Staging starts empty. The live `products` table is not touched.
   - If it fails: the retry rule applies. Nothing has been saved yet, so nothing is lost.

2. **Download pages.**
   - Trigger: step 1 finishes, Wi-Fi returns during a paused download, or the app launches with a download in progress.
   - Does: request `GET /catalogue/full` with `after_id` set to the saved cursor, one page at a time. Write each product into `products_staging` under the newer-wins rule, and save the id of the page's last product as the new cursor, in the same transaction. Repeat until a page comes back empty.
   - Wi-Fi: before each page, check the network. If the device has dropped to cellular, let the page in progress finish and save, then pause until Wi-Fi returns.
   - Data: rows go to staging. The cursor is kept in `sync_state`.
   - If it fails: if the app is killed, the phone restarts or the network is lost, the cursor still points at the last saved page. The next run requests from that cursor, and the unsaved page is downloaded again. On a network error or 5xx, the retry rule applies. If it still fails, stop and keep everything saved.

3. **Catch up on changes.**
   - Trigger: step 2 reaches an empty page.
   - Does: call `GET /catalogue/changes?since=<last_seq>`, starting from `start_seq`. Apply each change to staging: an insert or update is an upsert, and a delete removes the row. Both follow the newer-wins rule. Save the change_seq of the last change applied as `last_seq`, in the same transaction. Repeat while each response is full (1,000 changes), and stop on a response with fewer.
   - Why: a product whose id the cursor has already passed, or a product edited after `start_seq`, is corrected only by this step. Without it, edits made during a long download would be missed.
   - Wi-Fi: this is part of the full download, so it runs only on Wi-Fi.
   - Data: staging is updated, and `last_seq` tracks the catch-up's progress.
   - If it fails: a 410 resync required answer goes to step 6. On a network error or 5xx, the retry rule applies. If it still fails, stop and keep staging and `last_seq`. The next run continues from `last_seq`.

4. **Swap.**
   - Trigger: step 3 receives a response with fewer than 1,000 changes.
   - Does: in one SQLite transaction, replace all rows of `products` with the rows of `products_staging`, empty staging, and set `download_state` to complete. `last_seq` already holds the change_seq of the last change applied, so it stays as it is.
   - Data: `products` now holds the new catalogue. Reps see it from this point on.
   - If it fails: the transaction is rolled back. Reps keep the old catalogue (or see none, on a first download), staging is kept, and the swap runs again at the next trigger. Changes committed after the last catch-up request are not in staging, but the first incremental sync after the swap fetches them, because it starts from `last_seq`.

5. **Incremental sync.**
   - Trigger: app launch or the app returning to the foreground. It runs at most once every 15 minutes. If `last_incremental_started_at` is less than 15 minutes ago, skip. It also does not run while a full download is in progress (see the rules).
   - Does: call `GET /catalogue/changes?since=<last_seq>`. Apply the changes in order under the newer-wins rule, where a delete removes the row. Save `last_seq` with each page's rows, in the same transaction. If a response is full (1,000 changes), request the next page straight away. Stop on a response with fewer.
   - Network: any network.
   - Data: `products`, `last_seq`, and `last_incremental_started_at`.
   - If it fails: a 410 resync required answer goes to step 6. On a network error or 5xx, the retry rule applies. If it still fails, stop and keep `last_seq`. The next trigger after 15 minutes starts from `last_seq`, so no change is skipped.

6. **Resync.**
   - Trigger: a changes request (in step 3 or step 5) answers 410 resync required. This happens when the device has been out of sync for more than 7 days.
   - Does: leave `products` as it is, so reps keep seeing the old catalogue. Empty staging, clear the cursor and `last_seq`, and go to step 1 for a new full download. That download runs only on Wi-Fi.
   - Data: the old `products` table stays in place until the swap in step 4 replaces it.
   - If it fails: the failure rules of step 1 apply. The old catalogue stays on the device.

## What goes wrong

| Event | What happens |
|---|---|
| Device drops to cellular during the full download | The page in progress finishes and is saved. The download pauses and resumes when Wi-Fi returns. |
| App killed, phone restarted or network lost mid-download | The download resumes from the saved cursor on its next run. The unsaved page is downloaded again. Saved pages are kept. |
| Network error or 5xx response | The retry rule applies. If all 5 attempts fail, the device keeps what it has saved and waits for the next trigger. |
| 410 resync required | Go to step 6. The old catalogue stays visible until the new one is swapped in. |
| Swap transaction fails | It is rolled back. The old catalogue stays, and the swap is retried at the next trigger. |
| A change whose change_seq is not higher than the stored row's | Ignored, under the newer-wins rule. |
| A delete for a product the device does not hold | Nothing to remove, so nothing happens. |
| Any other HTTP answer, such as a 4xx other than 410 | Not covered by the brief. See the open questions. |

## Open questions

- Can reps browse the partly downloaded catalogue during a first download, or should they see a progress screen until it finishes? Not decided. This is for product to decide.
- Should the full download keep running in the background on iOS and Android, or run only while the app is open? The brief does not say.
- What should the device do with HTTP answers other than a network error, a 5xx and a 410? The brief does not say.