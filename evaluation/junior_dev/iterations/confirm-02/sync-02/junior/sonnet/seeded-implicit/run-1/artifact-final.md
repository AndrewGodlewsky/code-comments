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
