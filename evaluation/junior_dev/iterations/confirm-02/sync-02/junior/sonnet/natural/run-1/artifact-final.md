# Offline product catalogue sync: implementation plan

## Summary

Today the Catalogue service keeps products in Postgres and stamps every insert, update and delete with a `change_seq`. Deletes are soft: the row stays as a tombstone and is purged after 7 days. The app has a local SQLite database, used only for settings. There is no sync API yet.

This plan adds one. The app first records a watermark, then downloads the whole catalogue (about 400,000 products at about 2 KB each, roughly 800 MB) into a spare copy of the catalogue table. Then it replays every change made since the watermark and swaps the spare copy in as the live one. After that it syncs incrementally from the swap point. Two copies let reps keep using the old catalogue until the new one is complete.

## Terms

- **`change_seq`**: a number from one global, strictly increasing sequence, set on every product insert, update or delete. The Catalogue service assigns it at commit, so rows become visible in `change_seq` order. This plan relies on that guarantee and has not checked how Postgres provides it (see open items).
- **Watermark**: the highest committed `change_seq` at the moment a full download begins. Every change up to the watermark is already visible to every page read made afterwards.
- **Drain**: after all pages are saved, replaying every change after the watermark, in `change_seq` order, into the downloaded copy.
- **Generation**: one of two copies of the catalogue table in SQLite, `product_g0` and `product_g1`. The **active** generation is the one reps see. The other is the **download** generation.
- **Swap**: one transaction that makes the download generation the active one.
- **Tombstone**: a soft-deleted product row (`deleted = true`) that the server keeps for 7 days.
- **Apply rule**: write an incoming row only if its `change_seq` is greater than or equal to the stored row's, or no row is stored. An incoming delete removes the row if present and does nothing if absent. Equal means the same version, so writing it again is harmless. Page rows, feed changes and a page fetched again after a crash all use this one rule.
- **Wrapper**: the one function every request goes through (see "How every request is sent").

## Why the watermark approach is safe

Edits happen all day, including during a download that may take hours. For each product, one of two things is true:
- It was edited after its page was read. The change feed then carries the edit, and the drain applies it. Keyset pagination only moves forward, so the page endpoint never returns that product again. The client first sees the new version in the drain.
- It was edited before its page was read. The page already holds that version. The feed may replay it, and the apply rule makes that harmless. The client does not need to tell the two cases apart.

Deletes work the same way. A product deleted after its page was read arrives as a tombstone and its row is removed. A product deleted before its page was read is missing from the page. The feed delete then finds no row and does nothing.

The drain starts only after every page is saved, so no feed change ever arrives for a page not yet read. Edits made after the drain's last response are not part of the swap. At the swap, `live_cursor_seq` is set to the drain's final position, so the first incremental sync fetches them.

## Endpoints (new)

| Endpoint | Returns |
|---|---|
| `POST /sync/begin` | `{ watermark_seq, server_time, approx_total }`. `watermark_seq` is the current max committed `change_seq`. `approx_total` is an estimate of the product count (from table statistics, no full count), used only for a progress display. |
| `GET /catalogue/products?after_id=<id or empty>&limit=500` | Non-deleted products ordered by `id` ascending, each with its `change_seq`, plus `{ last_id, is_last_page }`. Keyset pagination only, no offset. A full download is 800 pages of 500 products, about 1 MB per page before compression. Servers should gzip responses. |
| `GET /catalogue/changes?after_seq=<n>&limit=1000` | Rows with `change_seq > n`, in `change_seq` order, including tombstones as `{id, deleted:true, change_seq}`. Also returns `{ next_seq, has_more }`. Answers **HTTP 410** with `{"error":"resync_required"}` if `after_seq < purged_through_seq`. |

## Server behaviour

- **Tombstone purge.** The existing 7-day purge job, before deleting tombstones, stores `purged_through_seq` (the highest `change_seq` among the tombstones it purges) in a one-row Postgres table. If the job fails, nothing is purged and the value is unchanged. The changes endpoint compares `after_seq` with this value. The test is exact and cannot be wrong in the dangerous direction: a client below the value may have missed a delete.
- **Consistency.** The begin endpoint reads `MAX(change_seq)` in its own transaction, and each page query is a separate read-committed statement. Because rows become visible in `change_seq` order, any row with `change_seq <= watermark` is visible to every page read after the watermark was returned.

## Client state (local SQLite, new tables in the existing database)

| Table | Contents |
|---|---|
| `product_g0`, `product_g1` | The two generations. Columns: `id` (PK), `change_seq`, the payload. The app displays only the active generation. |
| `sync_state` (single row) | `active_gen` (0, 1, or none); `live_cursor_seq` (last change applied to the active generation; null until the first swap); `last_incremental_attempt_at`; `download_status`; `download_gen`; `download_watermark_seq`; `download_watermark_taken_at`; `download_last_saved_id`; `download_drain_seq`; `download_approx_total`. |

`download_status` is one of:
- `none`: no download wanted or running.
- `resync_pending`: the live catalogue needs a full replacement and no download has started yet. This is how the app remembers a needed resync until Wi-Fi is available.
- `running`: pages are being downloaded.
- `paused_cellular`: waiting for Wi-Fi.
- `stopped_error`: the download gave up and waits for the next trigger.
- `draining`: all pages are saved and the drain is under way.
- `ready_to_swap`: the drain is finished.

The "sync running" flag is held in memory only, never stored. It is set when a sync pass starts and cleared whenever that pass ends for any reason: finished, paused, gave up, stopped on an error or an unexpected exception. A killed app starts with it cleared, and a paused or stopped download does not block the next trigger.

## Assumptions

- A1. The 15-minute limit counts from the start of the last incremental attempt, stored persistently. It applies to launch and foreground triggers alike.
- A2. A page that has already started is allowed to finish, including its retries, if the network drops to cellular.
- A3. Client errors (4xx) other than 410 are not retried. They stop the sync and are logged.
- A4. The first Wi-Fi-only download continues only while the app is running. Background execution (iOS BGProcessingTask, Android WorkManager) is optional and out of scope.

## How every request is sent

Every request below goes through the wrapper.
- It makes up to **5 attempts in total** at the same request, waiting 2 s, 4 s, 8 s, then 16 s between attempts. No wait follows the fifth attempt.
- A network error or a 5xx response triggers a retry.
- A 410 on the changes endpoint is not an error. It means "resync required".
- After the fifth failure the wrapper reports "gave up". The caller leaves everything already saved untouched and waits for the next trigger. During page download it sets `download_status = stopped_error`. During the drain the status stays `draining`. During incremental sync no status changes.

A **trigger** is app launch, the app returning to the foreground, or the network returning to Wi-Fi (full download only).

## Steps at run time

### 1. A trigger arrives
- **Starts it:** a trigger.
- **What it does:** if a sync pass is already running, ignore the trigger. Otherwise read `sync_state` and choose, in this order:
  1. `download_status` is `resync_pending`, or `active_gen` is none and `download_status` is `none`: go to step 2 if Wi-Fi is on. On a first install this happens automatically at launch, with no user action. If Wi-Fi is off, do nothing. A first install then shows a "connect to Wi-Fi to download the catalogue" message (wording is Product's). A rep with a live catalogue keeps using it.
  2. A download is in progress (`running`, `paused_cellular`, `stopped_error`, `draining`, `ready_to_swap`): go to step 5. Incremental sync does not run, because a replacement download is already under way, and a catalogue that needs replacing would only get a 410 again.
  3. `active_gen` is set and `download_status` is `none`: go to step 7 if at least 15 minutes have passed since `last_incremental_attempt_at`.
- **State kept:** `sync_state` in SQLite, plus the in-memory flag.
- **On failure:** an unexpected exception is logged and the flag is cleared, so a later trigger can try again.

### 2. Begin a full download
- **Starts it:** step 1, when a download is due and Wi-Fi is on.
- **What it does:** send one `POST /sync/begin`. Then, in one transaction, empty the `download_gen` table and write to `sync_state`: `download_gen` (the generation that is not active, or 0 when `active_gen` is none), `download_watermark_seq`, `download_watermark_taken_at`, `download_approx_total`, `download_last_saved_id = null`, `download_drain_seq = download_watermark_seq`, `download_status = running`. Emptying is always safe: that table is never the active one, so it holds only leftovers (a partial earlier download, or the old catalogue after a swap whose cleanup did not finish).
- **State kept:** SQLite.
- **On failure:** if the request gives up, nothing is written and the status stays as it was. If the transaction fails, the state is unchanged. Either way the next trigger tries again. Before a resync, check that free disk space is at least about 1 GB beyond the live catalogue. If it is not, do not start. Leave the status `resync_pending`, keep showing the existing catalogue, log the reason, and check again at each later trigger.

### 3. Download pages, one at a time
- **Starts it:** step 2 completing, or step 5 resuming.
- **What it does:** repeat until `is_last_page`:
  1. Check the network. If it is not Wi-Fi, go to step 4. This check is made only before starting a page.
  2. Request `GET /catalogue/products?after_id=<download_last_saved_id>&limit=500` through the wrapper. Pages are fetched one at a time, never in parallel.
  3. In one SQLite transaction, save the rows with the apply rule and set `download_last_saved_id` to the last id in the page. If this was the last page, the same transaction sets `download_status = draining`. Then go to step 6.
- **State kept:** `download_last_saved_id` is the resume point. It advances only when its page is fully saved.
- **On failure:**
  - A request that gives up sets `stopped_error`. All saved pages remain.
  - A crash after the response but before the commit loses that page. It is fetched again on resume, which is harmless.
  - If the save transaction fails (for example the disk is full), stop with `stopped_error` and do not advance the cursor.
  - A 4xx other than 410 stops with `stopped_error` and is logged. If the server keeps returning it, each trigger makes one more request and stops again. There is no lockout.

### 4. Pause on cellular
- **Starts it:** the network becomes cellular while a download is running.
- **What it does:** the page in progress finishes and is saved. Then no further page is requested and `download_status = paused_cellular`. Incremental sync does not run meanwhile, because a download is in progress. When Wi-Fi returns, the trigger in step 1 leads to step 5.
- **State kept:** `sync_state`.
- **On failure:** if the in-progress page gives up, treat it as in step 3 (`stopped_error`). If the app is killed while paused, the stored status resumes through step 5.

### 5. Resume an interrupted download
- **Starts it:** step 1, when a download is in progress. This includes the first launch after the app was killed, the phone restarted or the network was lost. On launch, a stored `running` means the previous run died.
- **What it does:** decide from the stored state only:
  1. If the watermark is older than 6 days, go to step 9. The server answers 410 beyond 7 days. Six days leaves a one-day margin for the drain to finish before the watermark expires.
  2. If the status is `draining` or `ready_to_swap`, all pages are saved. Go to step 6 on any network. Step 3 sets `draining` in the same transaction as the last page, so `stopped_error` always means pages are still missing.
  3. Otherwise continue step 3 from `download_last_saved_id`, not from page 1. Page downloads need Wi-Fi. If Wi-Fi is off, set `paused_cellular` and wait.
- **State kept:** `sync_state`.
- **On failure:** as in step 3.

### 6. Drain and swap
- **Starts it:** step 3 saving the last page, or step 5 resuming a drain.
- **What it does:**
  1. Loop `GET /catalogue/changes?after_seq=<download_drain_seq>&limit=1000`, starting at the watermark, until `has_more` is false. Any network is allowed, even after a pause for cellular, because the pages are done and the responses are small.
  2. For each response, in one transaction, apply the changes to the **download** generation with the apply rule and save `download_drain_seq = next_seq`. A feed change for a product the table does not hold (created after its page range passed) is written, or ignored if it is a delete.
  3. When `has_more` is false, set `ready_to_swap`.
  4. In one transaction, set `active_gen = download_gen`, `live_cursor_seq = download_drain_seq` and `download_status = none`. Reps now see the new catalogue. On a first install this is where `live_cursor_seq` first gets a value.
  5. In the background, empty the old generation to free space. This is housekeeping only. If the app is killed first, or a new resync starts first, the old rows stay until step 2 empties that table. Nothing displays the inactive generation, so leftovers cost only disk space.
- **State kept:** the drain cursor is saved with each batch. A crash during the drain resumes from the saved cursor.
- **On failure:**
  - A request that gives up leaves `draining`. Nothing is swapped, and the next trigger resumes through step 5.
  - A 410 means the download took so long that the watermark fell outside the tombstone window. Go to step 9.
  - A crash before the swap transaction commits leaves the old catalogue active. A crash after it is safe, because there is no state between "swapped" and "status none".

### 7. Incremental sync
- **Starts it:** step 1, at most once every 15 minutes (A1), only when `active_gen` is set and `download_status` is `none`.
- **What it does:**
  1. Store `last_incremental_attempt_at = now` before the first request.
  2. Loop `GET /catalogue/changes?after_seq=<live_cursor_seq>&limit=1000` on any network until `has_more` is false.
  3. For each response, in one transaction, apply the changes to the active generation and set `live_cursor_seq = next_seq`.
- **State kept:** `live_cursor_seq`, committed together with the changes it covers.
- **On failure:** after a request gives up, stop. Everything applied stays, and the cursor sits at the last committed response. The next trigger at least 15 minutes later continues from there. A crash between responses is safe, because the cursor moves in the same transaction as the changes. A 410 goes to step 8.

### 8. Resync required
- **Starts it:** a 410 in step 7.
- **What it does:** leave the live generation and `live_cursor_seq` alone, so reps keep seeing the existing catalogue. Set `download_status = resync_pending`. If Wi-Fi is on, go to step 2, which downloads into the inactive generation. If not, stop. Step 1 starts the download at the next trigger with Wi-Fi. Incremental sync does not run meanwhile. The swap happens only in step 6.
- **State kept:** `sync_state`.
- **On failure:** as in steps 2 to 6. An abandoned replacement download never affects the active generation.

### 9. Watermark too old during a download
- **Starts it:** step 5 (watermark older than 6 days) or step 6 (the feed answers 410).
- **What it does:** discard the partial download, empty the download generation, set `download_status = resync_pending`, and keep the active generation if there is one. If Wi-Fi is on, go to step 2 for a new download with a fresh watermark. Otherwise stop, and step 1 starts it when Wi-Fi returns. This is the only case where a download restarts from page 1.
- **State kept:** `sync_state`.
- **On failure:** as in step 2.

## Build and rollout

1. **Server.** Add the three endpoints. Add an index on `change_seq` for the changes feed. The primary key on `id` serves keyset pagination. The page query filters `deleted = false`. Add the one-row `purged_through_seq` table and have the purge job write it.
2. **App migration.** An app update runs a migration at launch, inside a transaction. It creates `product_g0`, `product_g1` and `sync_state`, with `active_gen` none, `download_status` `none` and `live_cursor_seq` null. If it fails, the existing settings database is untouched, the migration is retried at the next launch, and sync stays disabled until it succeeds.

## Open questions

- **For Product (not decided here): can reps browse the partly downloaded catalogue during their first download, or should they see a progress screen until it finishes?** The plan makes both possible, and steps 2 to 6 are the same either way. If browsing is allowed, the app reads the download generation on the first run. It holds only products up to `download_last_saved_id` and rows the drain has not yet corrected, so search results would be incomplete and quotes could miss products. If a progress screen is required, the app reads only `active_gen` and shows rows saved against `download_approx_total`, an estimate.
- Free-disk-space threshold, and the message shown when a resync cannot start.
- Whether background download is required (A4).
- How "Wi-Fi" is detected, for example a phone hotspot or a metered Wi-Fi network.
- Whether launch should bypass the 15-minute limit (A1).
- How the Catalogue service guarantees that rows become visible in `change_seq` order. This plan relies on the guarantee as stated.
