# Catalogue sync plan

## Summary

Today the Catalogue service stores products in Postgres and stamps every change with a sequence number. The field-sales app has no catalogue sync yet, and its SQLite database holds only user settings. The app will keep the whole catalogue on the device, about 400,000 products at about 2 KB each (roughly 800 MB), so reps can browse and quote offline. A first download fills a staging table in pages of 500, replays the edits made during the download, and then swaps the staging table in as the live catalogue, so reps never see a half-built one. After that, the app pulls changes in order at launch and whenever it returns to the foreground.

## Terms

- **change_seq**: a number from one global, strictly increasing Postgres sequence. The server stamps each insert, update and delete when it commits. A higher number is a later change.
- **Tombstone**: a deleted product, kept as a row with `deleted = true`. Tombstones are purged after 7 days. That 7-day period is the **tombstone window**.
- **Keyset pagination**: each page asks for products with an id above the last id of the previous page. It does not use page numbers.
- **Resync required**: the server's answer when the device's position is older than the tombstone window. The brief says only 'resync required'. The HTTP status 410 is this plan's choice.
- **products**: the live catalogue. Reps read only this table.
- **products_staging**: the new catalogue being built during a download.
- **Swap**: replacing `products` with `products_staging` in one step.
- **sync_state**: one row in the app's SQLite database, holding `mode`, `start_seq`, `cursor`, `catch_up_seq`, `last_seq` and `last_attempt_at`.
- **mode**: `full` from the start of a download until its swap, including a re-download after a 410. `incremental` otherwise.
- **start_seq**: the highest change_seq when a full download starts.
- **cursor**: the id of the last product on the last fully saved page. Empty means no page is saved yet.
- **catch_up_seq**: the last change_seq applied to staging during catch-up. It starts at `start_seq`.
- **last_seq**: the last change_seq applied to `products`.
- **last_attempt_at**: when the latest incremental attempt started.

Reading `sync_state`:
- No row means first run.
- `mode` `full` with `start_seq` set is an unfinished download.
- `mode` `full` with no `start_seq` means a re-download is needed.
- `mode` `incremental` means `products` is complete and live.

## Server endpoints (Catalogue service)

There is no sync API yet, so this plan defines three endpoints.

- `POST /catalogue/full/start` returns `start_seq`. The server keeps no state for a download.
- `GET /catalogue/full?after_id=<id>&limit=500` returns up to 500 live products with an id above `after_id`, in id order, each with its `change_seq`. A page with fewer than 500 products is the last page. The plan assumes tombstones are not returned here.
- `GET /catalogue/changes?since=<seq>&limit=1000` returns products and tombstones with `change_seq` above `since`, in `change_seq` order, each with its `change_seq`. Fewer than 1,000 items means the device has reached the latest change. If `since` is older than the tombstone window, the server returns 410.

## How the sync runs

One sync routine reads `sync_state` and picks the step from it:

- No row, or `mode` `full` with no `start_seq`: step 1.
- `mode` `full` with `start_seq` set: steps 2, 3 and 4, in order, each when its trigger fires.
- `mode` `incremental`: step 5.

The routine runs only while the app is in the foreground. When the app leaves the foreground, no new request starts.

## Rules used by several steps

- **Apply rule.** For each item, compare its `change_seq` with the stored row for the same product id. If there is no row, or the item's `change_seq` is higher, apply it: a product inserts or replaces the row, and a tombstone deletes it. A tombstone with no stored row changes nothing and is not stored. Otherwise skip the item. Replayed items are therefore harmless.
- **Retry rule.** Retry only network errors and 5xx responses, never a 410. Retry the same request after 2 s, 4 s, 8 s and 16 s, with five attempts in total. After the fifth failure, stop, keep everything already saved, and wait for the next trigger. For a download, the next trigger is app launch, return to the foreground, or Wi-Fi returning. For incremental sync, it is launch or foreground, at least 15 minutes after `last_attempt_at`.
- **Wi-Fi rule.** The full download's start, pages and catch-up run only on Wi-Fi. Incremental sync may use any network.
- **One writer.** Incremental sync does not run while `mode` is `full`.

## Steps

### Full download

1. **Start.**
   - Trigger: `sync_state` has no row (first run), or `mode` is `full` with no `start_seq` (after a 410 from step 3 or step 5). Wi-Fi only.
   - What it does: calls `POST /catalogue/full/start`. In one SQLite transaction, it creates `products_staging` if missing and empties it, sets `mode` to `full`, saves the response as `start_seq`, sets `catch_up_seq` to `start_seq`, and clears `cursor`. `start_seq` is taken before the first page, so no edit is missed. `products` is not touched.
   - Data: `products_staging` and `sync_state`.
   - On failure: retry rule. Nothing was saved, so nothing is lost. The next trigger repeats this step.

2. **Fetch pages.**
   - Trigger: step 1 has saved its state, or the previous page was saved, or the app launches, returns to the foreground, or Wi-Fi returns while `mode` is `full` with `start_seq` set. Wi-Fi only.
   - What it does: calls `GET /catalogue/full?after_id=<cursor>&limit=500`, one page at a time, never in parallel. With no cursor, it omits `after_id` to get the first page. It applies each product to `products_staging` with the apply rule. In the same transaction, it saves the id of the page's last product as `cursor`, so a page and its cursor are saved together or not at all. If the page has fewer than 500 products, go to step 3. An empty page also goes to step 3, so a resume after the last page moves on.
   - Data: `products_staging` and `sync_state.cursor`.
   - On failure: retry rule. If the phone moves to cellular, the page in flight finishes and saves, then the download pauses. No new page starts until Wi-Fi returns, and the download continues from `cursor`. If the app is killed or the phone restarts mid-page, that page's transaction rolls back, and the next launch fetches the page again after the saved `cursor`.

3. **Catch up.**
   - Trigger: step 2 has saved the last page. Wi-Fi only.
   - What it does: calls `GET /catalogue/changes?since=<catch_up_seq>&limit=1000`. It applies each item to `products_staging` with the apply rule. In the same transaction, it saves the last change_seq applied as `catch_up_seq`. It repeats while responses have 1,000 items, and stops at a response with fewer.
   - Why this is enough:
     - Each page carries the version of each product that was current when the page read it.
     - An edit committed after `start_seq` has a change_seq above `start_seq`, so catch-up returns it and it replaces the page copy. An edit already in the page comes back as an equal copy and is skipped.
     - A delete made after `start_seq` comes back as a tombstone. It removes the row if the page copied the product, and does nothing otherwise.
     - A product deleted before `start_seq` and re-created later is not in the tombstone range that catch-up covers. Its re-creation has a change_seq above `start_seq`, so catch-up returns it as a plain insert, because staging has no row for it. If a page already copied the re-created row, catch-up returns an equal copy and skips it.
   - Data: `products_staging` and `sync_state.catch_up_seq`.
   - On failure: retry rule. If the app is killed, the next launch goes to step 2, which finds no new page, and then catches up from `catch_up_seq`. On a 410, the download outlived the tombstone window: clear `start_seq`, `cursor` and `catch_up_seq`, and go to step 1. That empties staging and sets them again. `mode` stays `full`, and `products` keeps serving reps throughout.

4. **Swap.**
   - Trigger: the last catch-up response had fewer than 1,000 items, and no catalogue read is open. The app tracks its own open reads.
   - What it does: in one SQLite transaction, it drops `products`, renames `products_staging` to `products`, sets `last_seq` to `catch_up_seq`, sets `mode` to `incremental`, and clears `start_seq`, `cursor` and `catch_up_seq`. SQLite runs schema changes inside a transaction, so reps see either the old catalogue or the complete new one.
   - If a read is open: the swap waits. It is not retried on a timer. It runs when the last open read closes, after steps 2 and 3 run again, which needs Wi-Fi. Reps keep the old catalogue until then. A screen keeps the rows it has already loaded until it reloads its query.
   - Data: `products` is replaced.
   - On failure: nothing changes, and the complete staging table is kept. `mode` stays `full`, so incremental sync does not run on the old products. The next launch, foreground or Wi-Fi return resumes at step 2, which catches up again before the swap, so staging is never stale. That retry needs Wi-Fi and a network. Edits committed after the last catch-up response are fetched by step 5 after the swap.

### Incremental sync

5. **Fetch changes.**
   - Trigger: app launch or return to the foreground, with `mode` `incremental`, and `last_attempt_at` more than 15 minutes ago or never set. Wi-Fi returning does not trigger this step. Any network may be used.
   - What it does: sets `last_attempt_at` to now when the attempt starts. Calls `GET /catalogue/changes?since=<last_seq>&limit=1000`. It applies each item to `products` with the apply rule. In the same transaction, it saves the last change_seq applied as `last_seq`. It repeats while responses have 1,000 items.
   - Data: `products` and `sync_state.last_seq`.
   - On failure: retry rule. `last_attempt_at` was set when the attempt started, so a failed or exhausted attempt still counts toward the 15 minutes. The next launch or foreground event at least 15 minutes later runs the sync again from `last_seq`. If the app is killed, the same applies. On a 410, the device has been away longer than the tombstone window: set `mode` to `full`, clear `start_seq` and `cursor`, and go to step 1. That re-download waits for Wi-Fi. `products` keeps serving reps until the swap in step 4.

## What happens when things fail

| Situation | What happens | Resumes at |
|---|---|---|
| Network error or 5xx in any step | Retry rule. After the fifth failure, saved data is kept. | The next trigger for that step |
| Phone moves to cellular during a download | The page in flight is saved, then the download pauses. | Wi-Fi returns (step 2) |
| App killed or phone restarts mid-page | That page rolls back. | Next launch, from the saved `cursor` |
| App killed during catch-up | The saved `catch_up_seq` is kept. | Next launch: step 2, then step 3 |
| 410 in step 3 | Staging is emptied. `products` is kept. | Step 1, on Wi-Fi |
| 410 in step 5 | `mode` becomes `full`. `products` is kept. | Step 1, on Wi-Fi |
| Swap fails, or waits for an open read | Staging is kept and `mode` stays `full`. | Next launch, foreground or Wi-Fi return: steps 2, 3, 4, on Wi-Fi |
| App leaves the foreground | No new request starts. The page in flight finishes, or rolls back if the OS stops the app. | Next foreground or launch |

## Open questions

- Can reps browse the partly downloaded catalogue during their first download, or should they see a progress screen until it finishes? Not decided. Until the first swap there is no finished `products` table, so this plan gives reps nothing to browse.
- After a 410, reps keep the old catalogue until the re-download swaps in. That can take hours, and longer without Wi-Fi. The plan shows no out-of-date notice. Whether to show one is not decided.
- What does the user see when the client stops after five failed attempts? The brief does not say.
- What does the client do with responses other than network errors, 5xx and 410, such as other 4xx codes? The brief does not say, and the retry rule does not cover them.
- Does `/catalogue/full` leave out tombstones? The plan assumes it does. The brief does not say.
- Does the app's SQLite driver block the swap while a read is open? Not verified. The plan assumes the app tracks its own open reads.
- Can downloads and incremental sync run while the app is in the background? The plan assumes not. The brief does not say.