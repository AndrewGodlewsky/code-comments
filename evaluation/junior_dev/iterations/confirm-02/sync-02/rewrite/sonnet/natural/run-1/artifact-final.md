# Offline product catalogue sync: plan

## Summary

Today the field-sales app has no catalogue sync. It has a local SQLite database that holds only user settings. The Catalogue service keeps products in Postgres. Every insert, update or delete stamps the row with a `change_seq` from one global, strictly increasing sequence, assigned at commit, so rows become visible in `change_seq` order. Deletes are soft: the row stays as a tombstone (`deleted = true`) and is purged after 7 days.

This plan adds three server endpoints and a local sync engine. A first download first records a watermark, then downloads all products in pages of 500 into a hidden staging copy, then replays the change feed from the watermark to catch every edit made meanwhile, and only then flips a pointer so the new copy becomes the visible one. Later syncs just apply the change feed to the visible copy. If the feed says the client is too old, the client builds a new copy the same way while reps keep using the old one. Staging copies exist so that nobody ever sees a half-built catalogue and a failed download loses nothing.

Size: 400,000 products at about 2 KB is about 800 MB raw, or 800 pages of about 1 MB. An incremental response is at most about 2 MB. Responses should be gzip-compressed.

## Terms

- **`change_seq`**: the server's global, increasing version number. Each product row has exactly one, its latest. The change feed therefore shows the latest version of each changed product, not its history.
- **Watermark**: the highest committed `change_seq` on the server when a full download starts. Because `change_seq` is assigned at commit, everything at or below it is already visible to any later page read.
- **Keyset pagination**: paging by "ids after the last id I saw", not by page number.
- **Tombstone**: a soft-deleted row (`deleted = true`) kept for 7 days so clients can learn about the delete.
- **Generation**: a number on every local product row. The UI reads only the **live** generation. A first download or resync builds a **staging** generation beside it. Going live flips a pointer, so nothing is copied.
- **Single-flight lock**: an in-memory lock so only one sync job runs at a time.

## Rules that apply everywhere

- **Request rule** (every sync request): repeat the same request unchanged. Retry only after a network error or a 5xx. Wait 2 s, 4 s, 8 s, then 16 s: at most 5 attempts in total, 4 waits, about 30 s of waiting. After the 5th failure, stop, keep everything already saved (saved pages, cursors and generations are never rolled back) and wait for the next trigger. The attempt counter lives in memory and resets on each new trigger.
- **Not retried**: a 410 `resync_required` goes to the resync step. A 401 triggers the app's normal re-authentication (auth is existing and out of scope). Any other 4xx stops the run and is logged, with no backoff loop.
- **Wi-Fi rule**: the full download (watermark call, pages) runs only on Wi-Fi. The catch-up step and incremental sync may use any network.
- **One request at a time**: pages and changes are never fetched in parallel.
- **15-minute limit**: launch and foreground incremental sync runs at most once every 15 minutes, measured from the start of the last incremental run, including a failed one. If the device clock has moved backwards, treat the interval as elapsed. The limit does not apply to the full download or to catch-up.

## Server API (to be built)

| Endpoint | Returns |
|---|---|
| `GET /v1/catalogue/watermark` | `{ watermark_seq }`, the highest committed `change_seq` at the moment of the call |
| `GET /v1/catalogue/products?after_id=<opaque>&limit=500` | `{ products: [...], last_id, done }`. Ordered by id ascending, tombstones excluded. Omit `after_id` for page 1. `done` is true when no rows remain after this page (use a limit+1 query), so a catalogue that is an exact multiple of 500 needs no wasted empty request. |
| `GET /v1/catalogue/changes?after_seq=<n>&limit=1000` | 200: `{ changes: [{ seq, id, deleted, product? }], next_seq, has_more }`, ordered by `change_seq`, at most 1,000, deletes as `deleted: true`. 410: `{ error: "resync_required" }` |

- `after_id` is opaque to the client, so the server owns id ordering and collation.
- Indexes needed: the primary key on id, and an index on `change_seq`.
- The tombstone purge job records `oldest_valid_seq`: the highest `change_seq` of any tombstone it has purged. Only the purge job updates it.
- The changes endpoint answers 410 when `after_seq < oldest_valid_seq`, because that client would silently miss purged deletes, so the server never sends a partial feed. It also answers 410 when `after_seq` is above the current maximum, for example after a database restore.

## Local state

SQLite, the same database as user settings.

- **`product`**: primary key `(generation, id)`, plus `change_seq` and the payload.
- **`sync_state`** (one row): `live_generation` (null until the first download completes), `live_cursor_seq`, `staging_generation`, `staging_phase` (`none`, `downloading` or `catching_up`), `staging_watermark_seq`, `staging_cursor_seq` (used while catching up), `staging_last_saved_id`, `staging_started_at`, `last_incremental_started_at`.
- **In memory only**: attempt counter, backoff timer, network type, single-flight lock.

## How it runs

### 1. A trigger arrives: decide what to do

- **Starts when**: app launch, return to foreground, or Wi-Fi regained.
- **Data**: none. It reads `sync_state` and the network type.
- **State**: `sync_state`, plus the single-flight lock. A trigger that arrives while a job runs is dropped. A stopped job is picked up by the next trigger.
- **Routing, in order**:
  1. `staging_phase = downloading`: go to step 3 (resume). On cellular, wait for Wi-Fi.
  2. `staging_phase = catching_up`: go to step 4.
  3. `staging_phase = none` and `live_generation` is null: go to step 2 (first download). On cellular, do nothing and wait for Wi-Fi regained.
  4. Otherwise, run step 6 if at least 15 minutes have passed since `last_incremental_started_at`.
- While staging is in progress, incremental sync does not run. After a resync, the live cursor is already known to be too old.

### 2. Start a full download (first download, or resync)

- **Starts when**: step 1 finds no live catalogue, or step 7 found `resync_required`.
- **Data**: check free disk space first. A staging copy needs about 800 MB plus SQLite overhead, and during a resync the live copy stays as well. Set the threshold by measuring a real database. Then call `GET /watermark`.
- **State**: one transaction creates a new `staging_generation`, sets `staging_watermark_seq` to the returned value, clears `staging_last_saved_id`, records `staging_started_at`, and sets `staging_phase = downloading`. The watermark is saved before any page is fetched.
- **On failure**:
  - Not enough space: do not start. Keep the live catalogue and tell the user.
  - Watermark call fails: retry per the request rule. Nothing has been created, so the next trigger starts here again.
  - Crash after the transaction: the next launch resumes at step 3 with no new watermark.

### 3. Download pages, with Wi-Fi gating and resume

- **Starts when**: step 2 completes, or step 1 finds `staging_phase = downloading` (after the app was killed, the phone restarted, the network was lost, or a pause ended).
- **Data**: loop, one request at a time. Before each request, check the network is Wi-Fi. Call `GET /products?after_id=<staging_last_saved_id>&limit=500` (about 500 products, about 1 MB). When the response arrives, write its rows into the staging generation as upserts and set `staging_last_saved_id` to `last_id`, in one SQLite transaction. Repeat until `done` is true, then go to step 4.
- **State**: staging rows and `staging_last_saved_id`, always committed together. So "last fully saved page" is exactly what the database says, and refetching a page is harmless.
- **Cellular during a page**: let the request in flight finish, save the page, then pause. Start no new request on cellular. This is not a failure. When Wi-Fi returns, resume here and reset the attempt counter.
- **On failure**:
  - Network error or 5xx: request rule. After 5 attempts, stop and keep all saved pages. The next trigger resumes from `staging_last_saved_id`, not page 1.
  - App killed, phone restarted, or network lost mid-page: the unsaved page is fetched again. A partial response is discarded, never half-written.
  - Paused too long: if `staging_started_at` is more than 6 days old on resume, the watermark may fall outside the 7-day tombstone window. Discard the staging generation and go back to step 2. The server also checks this in step 4. The 6-day check is added in code only if that margin is confirmed as acceptable.

### 4. Catch up from the watermark, still in staging

- **Starts when**: step 3 receives `done`, or step 1 finds `staging_phase = catching_up`. On entry from step 3, set `staging_phase = catching_up` and `staging_cursor_seq = staging_watermark_seq`.
- **Data**: loop, one request at a time, on any network. Call `GET /changes?after_seq=<staging_cursor_seq>&limit=1000` (up to 1,000 changes, about 2 MB). In one transaction per response, apply each change to the staging generation and set `staging_cursor_seq = next_seq`. Apply an upsert only when the incoming `change_seq` is at least the stored one. Apply a delete the same way, and treat a missing row as a no-op. Continue while `has_more` is true, then go to step 5.
- **State**: staging rows and `staging_cursor_seq`, committed together.
- **On failure**:
  - Network error or 5xx: request rule. After 5 attempts, stop. The next trigger resumes from `staging_cursor_seq`.
  - 410 `resync_required`: the watermark has aged out of the tombstone window. Delete the staging generation, set `staging_phase = none`, and go to step 2 for a fresh watermark. The live catalogue, if any, is untouched.

**Why this catches every edit made during a long download.** Edits committed before the watermark are already in every page, because pages are read after the watermark. Edits committed after it come through this feed. That covers a new product whose id is lower than the current page position (a keyset scan cannot find it), a product changed after its page was saved, and a product deleted after its page was saved (it arrives as a tombstone and is removed). A product deleted before its page was fetched is never returned by the pages endpoint, and its feed entry is a harmless no-op. No change at or below the watermark can appear later, so the feed has no gaps.

### 5. Make the new catalogue live

- **Starts when**: step 4 gets `has_more = false`.
- **Data**: none moves.
- **State**: one transaction sets `live_generation = staging_generation` and `live_cursor_seq = staging_cursor_seq`, sets `staging_phase = none`, and clears the staging fields. The UI notices the new generation and refreshes. Changes that arrive later are picked up by step 6. Then run step 8.
- **On failure**: the transaction either commits or does not. If the app is killed before it commits, the next launch finds `catching_up` and repeats step 4, which has nothing new to apply before it swaps. The old catalogue stays visible until the commit.

### 6. Incremental sync on the live catalogue

- **Starts when**: step 1 routes here: launch or foreground, at least 15 minutes since `last_incremental_started_at`, a live generation, and no staging. Any network is allowed. Set `last_incremental_started_at` at the start of the run, before the first request.
- **Data**: loop, one request at a time. Call `GET /changes?after_seq=<live_cursor_seq>&limit=1000`. In one transaction per response, apply the changes to the live generation (upserts, and deletes by removing the row) and set `live_cursor_seq = next_seq`. Continue while `has_more` is true.
- **State**: live rows and `live_cursor_seq`, committed together.
- **On failure**:
  - Network error or 5xx: request rule. After 5 attempts, stop. Batches already applied stay applied, and the next trigger continues from `live_cursor_seq`. A failed run still counts toward the 15-minute limit.
  - 410 `resync_required`: go to step 7.

### 7. Resync required

- **Starts when**: the changes endpoint returns 410 in step 6.
- **Data**: nothing is deleted. Start a full download as in step 2, which creates a new staging generation.
- **State**: `live_generation` and `live_cursor_seq` stay untouched, so reps keep browsing and quoting from the existing catalogue. The new generation goes live in step 5 only when completely ready.
- **On failure**: handled by steps 2, 3 and 4. If the app is killed, the next launch resumes from the saved `staging_last_saved_id`. If the full download keeps failing, the old catalogue stays in use, stale but usable.

### 8. Clean up old generations

- **Starts when**: after step 5, and at every app launch.
- **Data**: delete rows whose generation is neither live nor staging, in chunks of a few thousand rows per transaction so the UI is never blocked for long.
- **State**: SQLite only.
- **On failure**: stop and retry at the next launch. Leftover rows cost disk space but never affect correctness, because every read filters on `live_generation`.

## What happens when things fail (summary)

| Situation | Result |
|---|---|
| Network error or 5xx | Retry 2, 4, 8, 16 s, 5 attempts total, then stop and keep all saved data |
| 410 during incremental sync | Resync (step 7); live catalogue stays visible |
| 410 during catch-up | Discard staging, new watermark (step 2) |
| Cellular during full download | Finish the page, save it, pause until Wi-Fi |
| App killed or phone restarted | Resume from `staging_last_saved_id` or the cursor |
| Not enough disk space | Do not start; keep live catalogue; tell the user |
| Cleanup fails | Retry next launch |

## Assumptions to confirm (not given in the brief)

1. Catch-up uses the change feed, so it may run on any network, and the 15-minute limit does not apply to it.
2. The 15-minute limit is measured from the start of the last incremental run, including a failed one.
3. The full download restarts on app launch, return to foreground, or Wi-Fi regained, with no 15-minute limit.
4. The download runs only while the app is running. Background execution (iOS background tasks, Android WorkManager with an unmetered-network constraint) is not planned here and is a separate decision. Without it, a multi-hour download only progresses while the app is open.
5. The 6-day staging age limit in step 3 is acceptable.

## Build and rollout (not part of the running system)

1. **Build the server API** (endpoints, indexes, `oldest_valid_seq` in the purge job) before any client work.
2. **Migrate the local database** on the first launch of the app version with sync: create `product` and `sync_state` with `live_generation` null and `staging_phase = none`. Settings tables are untouched. The migration is one transaction. If it fails, the app starts without sync and retries on the next launch, and settings are unaffected.
3. **Tests before release**:
   - Kill the app after each commit in steps 2, 3, 4 and 5, and confirm resume from the saved point.
   - Insert, update and delete products (including ids lower than the current page position) while a download runs, and confirm the final catalogue matches the server.
   - Switch Wi-Fi to cellular mid-page, and confirm the page is saved and then paused.
   - Force 5xx responses for 4 and then 5 attempts, and confirm the timing is 2, 4, 8, 16 s and the stop after the 5th.
   - Make a live cursor older than the 7-day window, and confirm the old catalogue stays readable until the swap.
   - Run every trigger path twice in quick succession, and confirm the single-flight lock and the 15-minute limit hold.

## Open question (not decided here)

**Can reps browse the partly downloaded catalogue during their first download, or do they see a progress screen until it finishes?**

Product has not decided this, and this plan does not decide it. The sync steps are the same either way. The first download builds the staging generation, and the UI reads only the live generation, which is empty until step 5. The answer affects mainly the UI and one read rule. If browsing is allowed, the UI must read the staging generation during the first download. That data would be partial, and edits made during the download would not be applied until step 4. Product should know both consequences when it decides.
