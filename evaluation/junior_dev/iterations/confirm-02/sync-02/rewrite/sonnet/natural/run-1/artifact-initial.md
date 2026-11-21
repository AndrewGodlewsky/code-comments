# Offline product catalogue sync: plan

## Design in brief

- **Three server endpoints**:
  - A watermark endpoint.
  - A keyset-paged full download.
  - A change feed ordered by `change_seq`.
- **Watermark**: before the first page of any full download, the client records the server's current highest committed `change_seq`. The server assigns `change_seq` at commit, so everything at or below the watermark is already visible to any later page read. After the last page, the client replays the change feed from the watermark. This catches every edit made during a download that takes hours. That includes edits to products whose id is lower than the page position, and deletes.
- **Generations in SQLite**: every product row carries a `generation` number. The UI reads only the live generation. A first download or a resync builds a new staging generation beside it. Making it live is one small transaction that flips a pointer. Nothing is copied, and the old catalogue stays visible until the new one is complete.
- **Sizes**: 400,000 products at about 2 KB is about 800 MB raw, or 800 pages of about 1 MB each. An incremental response is at most about 2 MB. Responses should be gzip-compressed.

### Endpoints (to be built)

| Endpoint | Returns |
|---|---|
| `GET /v1/catalogue/watermark` | `{ watermark_seq }`, the highest committed `change_seq` at the moment of the call |
| `GET /v1/catalogue/products?after_id=<opaque>&limit=500` | `{ products: [...], last_id, done }`. Ordered by id ascending, tombstones excluded. Omit `after_id` for page 1. `done` is true when no rows remain after this page (use a limit+1 query), so a catalogue that is an exact multiple of 500 does not need a wasted empty request. |
| `GET /v1/catalogue/changes?after_seq=<n>&limit=1000` | 200: `{ changes: [{ seq, id, deleted, product? }], next_seq, has_more }`, ordered by `change_seq`, at most 1,000, with deletes as `deleted: true`. 410: `{ error: "resync_required" }` |

The `after_id` value is opaque to the client, so the server owns the id ordering and collation. Each product row has exactly one `change_seq`, its latest. The feed therefore shows the latest version of each changed product, not its history.

### Local state (SQLite, same database as user settings)

- **`product`**: primary key `(generation, id)`, plus `change_seq` and the payload.
- **`sync_state`** (one row):
  - `live_generation` (null before the first download completes)
  - `live_cursor_seq`
  - `staging_generation`
  - `staging_phase` (`none`, `downloading` or `catching_up`)
  - `staging_watermark_seq`
  - `staging_cursor_seq` (used while catching up)
  - `staging_last_saved_id`
  - `staging_started_at`
  - `last_incremental_started_at`
- **In memory only**: the current attempt counter, the backoff timer, the network type, and a single-flight lock.

### Assumptions to confirm (not given in the brief)

1. Catch-up after the last page uses the change feed, so it may run on any network. It is not subject to the 15-minute limit, which applies to the launch and foreground trigger of incremental sync.
2. The 15-minute limit is measured from the start of the last incremental run, including a run that failed.
3. The full download restarts on app launch, return to foreground, or Wi-Fi regained. The 15-minute limit does not apply to it.
4. The download runs while the app is running. Background execution (iOS background tasks, Android WorkManager with an unmetered-network constraint) is not planned here and would be a separate decision. Without it, a multi-hour download only progresses while the app is open.
5. Auth is existing and out of scope. A 401 triggers the app's normal re-authentication, not the retry policy.

---

## Steps

### 1. Build the server API and the purge horizon

- **Starts when**: engineering work, before any client work.
- **Data**: the three endpoints above. Needed indexes are the primary key on id and an index on `change_seq`. The tombstone purge job records `oldest_valid_seq`, the highest `change_seq` of any tombstone it has purged. The changes endpoint answers 410 `resync_required` when `after_seq < oldest_valid_seq`. It also answers 410 when `after_seq` is greater than the current maximum, for example after a database restore.
- **State**: `oldest_valid_seq` on the server, updated only by the purge job.
- **On failure**: a server error returns 5xx, which the client handles in step 3. A client with a cursor older than the horizon cannot be served safely, because it would silently miss purged deletes. So the server must answer 410, never a partial feed.

### 2. Migrate the local database

- **Starts when**: the first launch of the app version that contains sync.
- **Data**: create `product` and `sync_state`. `live_generation` is null and `staging_phase` is `none`. Existing settings tables are untouched.
- **State**: SQLite.
- **On failure**: the migration is one transaction. If it fails, the app starts without sync and retries on the next launch. Settings are unaffected.

### 3. Shared request rule (used by every network call below)

- **Starts when**: any sync request is sent.
- **Data**: the same request is repeated unchanged.
- **State**: the attempt counter is in memory and resets on each new trigger.
- **On failure**:
  - **Retried**: a network error or 5xx. Wait 2 s, then 4 s, 8 s, 16 s, with at most 5 attempts in total. This is 4 waits and about 30 s of waiting.
  - **After the 5th failure**: stop and keep everything already saved. Saved pages, cursors and generations are never rolled back. Wait for the next trigger.
  - **Not retried**: 410 `resync_required` goes to step 11. Other 4xx responses stop the run and are logged, with no backoff loop.
  - **Wi-Fi gate**: if a request is a full-download page and the network has moved to cellular, no further attempt starts on cellular. This is not counted as a failure, so the counter is reset when Wi-Fi returns (see step 6).

### 4. Sync coordinator: decide what a trigger does

- **Starts when**: app launch, return to foreground, or Wi-Fi regained.
- **Data**: none. It reads `sync_state` and the network type.
- **State**: `sync_state`. A single-flight lock ensures only one sync job runs at a time, so full-download pages are never fetched in parallel.
- **Routing, in order**:
  1. If `staging_phase` is `downloading`, go to step 6 (resume the download). If it is `catching_up`, go to step 8. If it is `none`, go to the next rule.
  2. If `live_generation` is null and there is no staging, go to step 5 (first download). This needs Wi-Fi. On cellular, do nothing and wait for Wi-Fi regained.
  3. Otherwise run incremental sync (step 10), if at least 15 minutes have passed since `last_incremental_started_at`.
- **On failure**: a trigger that arrives while a job runs is dropped. A job that was stopped is picked up by the next trigger.

### 5. Start a full download (first download, or resync)

- **Starts when**: step 4 finds no live catalogue, or step 11 found `resync_required`.
- **Data**: check free disk space first. A staging copy needs about 800 MB plus SQLite overhead, and during a resync the live copy remains as well. The threshold should be set by measuring a real database. Then call `GET /watermark`.
- **State**: one transaction creates a new `staging_generation`, sets `staging_watermark_seq` to the returned value, clears `staging_last_saved_id`, records `staging_started_at`, and sets `staging_phase = downloading`. The watermark is saved before any page is fetched.
- **On failure**:
  - **Not enough space**: do not start. Keep the live catalogue and tell the user.
  - **Watermark call fails**: retry per step 3. After the last attempt nothing has been created, so the next trigger starts here again.
  - **Crash after the transaction**: the next launch resumes at step 6, with no new watermark.

### 6. Download pages, with Wi-Fi gating and resume

- **Starts when**: step 5 completes, or a trigger finds `staging_phase = downloading`, for example after the app was killed, the phone restarted, the network was lost, or a pause ended.
- **Data**: loop, one request at a time. Before each request, check that the network is Wi-Fi. Call `GET /products?after_id=<staging_last_saved_id>&limit=500`. Each response is about 500 products and about 1 MB. After the response arrives, write the 500 rows into the staging generation and set `staging_last_saved_id` to the response's `last_id`, in a single SQLite transaction. Repeat until `done` is true.
- **State**: staging rows and `staging_last_saved_id`, always committed together. Because of that, "last fully saved page" is exactly what the database says. Rows are written as upserts, so refetching a page is harmless.
- **Cellular during a page**: if the network drops to cellular while a request is in flight, let that request finish, save the page, and then pause. Start no new request on cellular. Resume at this step when Wi-Fi returns, and reset the attempt counter.
- **On failure**:
  - **Network error or 5xx**: handled by step 3. After 5 attempts, stop and keep all saved pages. The next trigger resumes from `staging_last_saved_id`, not page 1.
  - **App killed, phone restarted, or network lost mid-page**: the unsaved page is simply fetched again. The partial response is discarded and never half-written.
  - **Paused for a long time**: if `staging_started_at` is more than 6 days old on resume, the watermark may fall outside the 7-day tombstone window. Discard the staging generation and go back to step 5. The server also checks this, in step 8. This restart is checked in code only if the 6-day margin is confirmed as acceptable.

### 7. Handling edits made during the download

This is not a separate runtime step. It explains why steps 5 and 8 are enough.

- **Edits that committed before the watermark**: every page is read after the watermark, so the pages already contain them.
- **Edits that commit after the watermark**:
  - **Updates and inserts**: the change feed returns them in step 8. This covers a new product whose id is lower than the current page position, which a keyset scan cannot find, and a product that changes after its page was saved.
  - **Deletes**: a product deleted after its page was saved appears in the feed as a tombstone and is removed in step 8. A product deleted before its page was fetched is never returned by the pages endpoint, and its feed entry is a harmless no-op.
- **Ordering guarantee**: the server assigns `change_seq` at commit and rows become visible in that order. So no change with a sequence number at or below the watermark can appear later, and the feed has no gaps.

### 8. Catch up from the watermark, still in staging

- **Starts when**: step 6 receives `done`. Set `staging_phase = catching_up` and `staging_cursor_seq = staging_watermark_seq`.
- **Data**: loop, one request at a time. Call `GET /changes?after_seq=<staging_cursor_seq>&limit=1000`, up to 1,000 changes (about 2 MB) per response. In one transaction per response, apply each change to the staging generation and set `staging_cursor_seq = next_seq`. Apply an upsert only when the incoming `change_seq` is at least the stored one. Apply a delete the same way, and treat a missing row as a no-op. Continue while `has_more` is true. This step may run on any network (assumption 1).
- **State**: staging rows and `staging_cursor_seq`, committed together.
- **On failure**:
  - **Network error or 5xx**: step 3. After 5 attempts, stop. The next trigger resumes from `staging_cursor_seq`.
  - **410 `resync_required`**: the watermark has aged out of the tombstone window. Delete the staging generation, set `staging_phase = none`, and go to step 5 for a fresh watermark. The live catalogue, if any, is untouched.

### 9. Make the new catalogue live

- **Starts when**: step 8 gets `has_more = false`.
- **Data**: none moves.
- **State**: one transaction sets `live_generation = staging_generation`, `live_cursor_seq = staging_cursor_seq`, and `staging_phase = none`, then clears the staging fields. The UI notices the new generation and refreshes. Any changes that arrive after this are picked up by step 10.
- **On failure**: the transaction either commits or does not. If the app is killed before it commits, the next launch finds `staging_phase = catching_up` and repeats step 8, which finds nothing new to apply before it swaps. The old catalogue stays visible until the commit.

### 10. Incremental sync on the live catalogue

- **Starts when**: step 4 routes here. That is app launch or return to foreground, with at least 15 minutes since `last_incremental_started_at`, a live generation, and no staging in progress. Any network is allowed. Set `last_incremental_started_at` at the start of the run, before the first request. If the device clock has moved backwards, treat the interval as elapsed.
- **Data**: loop, one request at a time. Call `GET /changes?after_seq=<live_cursor_seq>&limit=1000`. In one transaction per response, apply the changes to the live generation (upserts, and deletes by removing the row) and set `live_cursor_seq = next_seq`. Continue while `has_more` is true.
- **State**: live rows and `live_cursor_seq`, committed together.
- **On failure**:
  - **Network error or 5xx**: step 3. After 5 attempts, stop. Batches already applied stay applied, and the next trigger continues from `live_cursor_seq`. A failed run still counts toward the 15-minute limit (assumption 2).
  - **410 `resync_required`**: go to step 11.

### 11. Resync required

- **Starts when**: the changes endpoint returns 410 in step 10.
- **Data**: nothing is deleted. Start a full download exactly as in step 5, which creates a new staging generation.
- **State**: `live_generation` and `live_cursor_seq` stay untouched, so reps keep browsing and quoting from the existing catalogue. While `staging_phase` is not `none`, step 4 does not run incremental sync, because the live cursor is already known to be too old. The new generation goes live in step 9 only when it is completely ready.
- **On failure**: handled by steps 5, 6 and 8. If the app is killed, the next launch resumes from the saved `staging_last_saved_id`. If the full download keeps failing, the old catalogue stays in use, stale but usable.

### 12. Clean up old generations

- **Starts when**: after step 9, and at every app launch.
- **Data**: delete rows whose generation is neither live nor staging, in chunks of a few thousand rows per transaction so the UI is never blocked for long.
- **State**: SQLite only.
- **On failure**: stop and retry at the next launch. Leftover rows cost disk space but never affect correctness, because every read filters on `live_generation`.

### 13. Tests to run before release

- Kill the app after each commit in steps 5, 6, 8 and 9, and confirm resume from the saved point.
- Insert, update and delete products (including ids lower than the current page position) while a download is running, and confirm the final catalogue matches the server.
- Switch Wi-Fi to cellular mid-page, and confirm the page is saved and then paused.
- Force 5xx responses for 4 and then 5 attempts, and confirm the timing is 2, 4, 8, 16 s and the stop after the 5th.
- Make a live cursor older than the 7-day window, and confirm the old catalogue stays readable until the swap.
- Run every trigger path twice in quick succession, and confirm the single-flight lock and the 15-minute limit hold.

---

## Open question (not decided here)

**Can reps browse the partly downloaded catalogue during their first download, or do they see a progress screen until it finishes?**

Product has not decided this, and this plan does not decide it. The sync steps above are the same either way. The first download builds the staging generation, and the UI reads only the live generation, which is empty until step 9. Whichever answer product gives, it affects mainly the UI and one read rule. If browsing is allowed, the UI must read the staging generation during the first download. The staging data would then be partial, and edits made during the download would not be applied until step 8. Product should know about both consequences when it decides.
