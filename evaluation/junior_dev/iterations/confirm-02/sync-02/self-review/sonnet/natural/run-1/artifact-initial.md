# Offline product catalogue sync: implementation plan

## Design in brief

**Endpoints (new, on the Catalogue service)**

| Endpoint | Returns |
|---|---|
| `GET /sync/watermark` | `{ "watermark": <current max committed change_seq> }`. |
| `GET /catalogue/products?after_id=<id>&limit=500` | Live (non-deleted) products with `id > after_id`, ordered by `id` ascending, each with its `change_seq`. It also returns `has_more`. `after_id` is empty for page 1. |
| `GET /catalogue/changes?since=<change_seq>&limit=1000` | Rows with `change_seq > since`, ordered by `change_seq` ascending. Tombstones are included as `{id, change_seq, deleted: true}`. It also returns `last_seq` and `has_more`. If `since` is older than the purge floor, it returns HTTP 410 with code `resync_required`. |

The purge floor is the highest `change_seq` of any tombstone the 7-day purge has removed. A request whose `since` is below that floor can no longer be answered completely, so the server refuses it. Because `change_seq` is assigned at commit and rows become visible in that order, a watermark read at time T guarantees that every change with a lower `change_seq` is already visible. This is the basis for not missing changes.

**Why no changes are missed during a long download.** The client records a watermark W before it fetches page 1. Any change committed after W is returned by `/changes?since=W`. The client replays those changes once the last page is saved. A page may already contain a newer version of a row than W, and replaying is harmless because every apply is an idempotent upsert or delete keyed by `id`. It is guarded by "only apply if the incoming `change_seq` is at least the stored one".

- A row inserted behind the cursor is caught by the replay.
- A row deleted after it was paged is removed by its tombstone.
- A row deleted before it was paged is never served, and its tombstone replay does nothing.

**Local storage (existing SQLite database, new tables)**
- `products(generation, id, change_seq, payload)`, primary key `(generation, id)`.
  - A `generation` is one complete copy of the catalogue.
  - Reads use only the active generation.
  - The new copy built for a first download or a resync is written under a new generation number. The active generation is never touched.
  - The size is about 800 MB per copy.
- `sync_state`, a single row:
  - `active_generation`
  - `build_generation` (nullable)
  - `build_phase`: `none`, `downloading`, `catching_up`
  - `build_watermark`
  - `build_cursor` (last saved product id)
  - `build_started_at`
  - `change_cursor_active` (position for the active generation)
  - `change_cursor_build` (position for the build during catch-up)
  - `last_incremental_run_at`

**Assumptions I am making (flag if wrong)**
- The sync runs while the app process is alive. OS background tasks are out of scope.
- 4xx responses other than 410 are not retried, because the brief lists only network errors and 5xx.
- The 15-minute throttle counts from the start of the last incremental run, whether or not it succeeded.
- An unfinished page request that fails after the device left Wi-Fi is not retried on cellular. The download pauses at the same cursor.

---

## Steps

### 1. Server: build the three endpoints and their indexes
- **Starts it:** Delivery work, before any client work.
- **Data moves:** None yet.
  - Index `products(id)` where `deleted = false` for the page query.
  - Index `products(change_seq)` for the changes query.
  - Record `purge_floor`, the highest `change_seq` among tombstones removed by the 7-day purge, and update it inside the purge job.
- **State kept:** Postgres, plus the `purge_floor` value.
- **On failure:** If `purge_floor` is missing or wrong, a client could silently miss deletes. Treat it as a release blocker. Add a server test that creates a tombstone, purges it, then requests `since` below the floor and expects 410.

### 2. Client: create the local schema and the single-flight sync runner
- **Starts it:** App upgrade to the version containing this feature, via a SQLite migration.
- **Data moves:** None. Create the tables above, with `sync_state` empty (`active_generation = null`).
- **State kept:** SQLite.
- **On failure:** If the migration fails, the app starts without a catalogue and settings are unaffected. The migration runs again on the next launch. There is exactly one sync job at a time (a mutex). A trigger that arrives while a job runs is dropped, not queued.

### 3. Decide what to run (the trigger handler)
- **Starts it:** Any of these:
  - App launch.
  - App returns to foreground.
  - Wi-Fi becomes available.
  - A previous run ended and needs follow-up.
- **Data moves:** Read `sync_state` only. Choose one branch:
  1. `build_generation` is not null, so a build is in progress. Go to step 5, or step 8 if the phase is `catching_up`.
  2. `active_generation` is null, so this is a first download. Go to step 4.
  3. A catalogue exists and no build is in progress. Go to step 9, the incremental sync.
- **State kept:** Read from SQLite.
- **On failure:** If the SQLite read fails, abort the run and wait for the next trigger.

### 4. Start a full build (first download or resync)
- **Starts it:** Step 3 found no catalogue, or step 10 received `resync_required`.
- **Data moves:**
  1. Check free disk space for about 1 GB. A resync keeps the old copy, so it needs roughly double. If space is short, do not start. Show a "not enough storage" message, and keep any existing catalogue.
  2. Check that the device is on Wi-Fi. If not, mark the build as pending and stop. The Wi-Fi-available trigger will restart it.
  3. Call `GET /sync/watermark` (with the retry policy in step 11).
  4. In one SQLite transaction, write `build_generation = max(generation)+1`, `build_phase = downloading`, `build_watermark = W`, `build_cursor = null`, `build_started_at = now`.
- **State kept:** `sync_state` in SQLite. W is saved before page 1 is requested.
- **On failure:**
  - If the app dies before the transaction commits, nothing is saved and the next trigger starts again with a new W.
  - If the watermark call fails after 5 attempts, stop and keep whatever exists.

### 5. Download pages (loop, one page at a time)
- **Starts it:** Step 4 finished, or a trigger found `build_phase = downloading`.
- **Data moves:** Before each page, check that the device is on Wi-Fi. Then request `GET /catalogue/products?after_id=<build_cursor>&limit=500`. Each page is about 1 MB. Requests are strictly sequential.
- **State kept:** Nothing is written until the response has fully arrived (step 6).
- **On failure:**
  - A network error or 5xx follows the retry policy in step 11. After 5 attempts the run stops, keeping the saved pages and the `build_cursor`.
  - If the device drops to cellular while a page is in flight, let the request complete and save it (step 6). Then pause at step 7 instead of requesting the next page.
  - If the in-flight request fails after leaving Wi-Fi, do not retry it on cellular. Pause at the same cursor.

### 6. Save a page atomically
- **Starts it:** A complete page response arrived.
- **Data moves:** In one SQLite transaction:
  1. Insert the 500 rows into `products` under `build_generation`, using upsert so a repeated page is harmless.
  2. Set `build_cursor` to the last `id` in the page.
- **State kept:** SQLite. The page and the cursor commit together, or neither does.
- **On failure:**
  - If the app is killed or the phone restarts mid-transaction, SQLite rolls the page back. The cursor still points to the previous fully saved page, so the next run re-requests that page. Resuming never goes back to page 1.
  - If the write fails (for example the disk is full), stop the run, show a storage message, and keep the saved pages.
  - When `has_more` is false, go to step 8.

### 7. Pause and resume on network changes
- **Starts it:** The network type changes to cellular or offline during the download, detected between pages (see step 5).
- **Data moves:** None while paused.
- **State kept:** `build_cursor` already holds the position. No extra state is needed.
- **On failure:** If the app is killed while paused, the next launch trigger resumes from `build_cursor` once Wi-Fi is present. When Wi-Fi returns, the Wi-Fi-available trigger runs step 3, which resumes step 5.

### 8. Catch up on changes made during the download
- **Starts it:** The last page was saved (`has_more = false`).
- **Data moves:**
  1. In one transaction, set `build_phase = catching_up` and `change_cursor_build = build_watermark`.
  2. Loop `GET /catalogue/changes?since=<change_cursor_build>&limit=1000`. This may use any network.
  3. For each response, in one transaction, apply every change to `build_generation`: upsert live rows, delete tombstoned ids, skip a change whose `change_seq` is lower than the stored row's. Then set `change_cursor_build = last_seq`.
  4. Repeat while `has_more` is true.
  5. When the loop ends, go to step 8a (promote).
- **State kept:** SQLite: `change_cursor_build` and the build rows.
- **On failure:**
  - Retry policy as in step 11. After a stop, the next trigger resumes from `change_cursor_build`.
  - If the server answers `resync_required`, the download was left too long. Discard the build generation (delete its rows in batches) and go to step 4 for a fresh build. The old catalogue stays visible.

**8a. Promote the new copy**
- **Starts it:** Catch-up is complete.
- **Data moves:** In one transaction: `active_generation = build_generation`, `change_cursor_active = change_cursor_build`, `build_generation = null`, `build_phase = none`, `last_incremental_run_at = now`. After the commit, delete the previous generation's rows in batches in the background.
- **State kept:** `sync_state`. The switch is a single transaction, so reps see either the old catalogue or the complete new one, never a mixture.
- **On failure:** If the app dies before the commit, the next trigger finds `catching_up` and runs step 8 again, which is safe because the apply is idempotent. If the app dies after the commit, leftover old rows are invisible, because reads use `active_generation` only. A cleanup job removes them on the next launch.

### 9. Incremental sync
- **Starts it:** App launch or return to foreground, when `active_generation` is not null, no build is in progress, and at least 15 minutes have passed since `last_incremental_run_at` (or the value is null). If the system clock has moved backwards, treat the throttle as elapsed. Otherwise skip silently.
- **Data moves:**
  1. Set `last_incremental_run_at = now` at the start of the run.
  2. Loop `GET /catalogue/changes?since=<change_cursor_active>&limit=1000`, on any network.
  3. For each response, in one transaction, apply the changes to the active generation exactly as in step 8, then set `change_cursor_active = last_seq`.
  4. Repeat while `has_more` is true.
- **State kept:** SQLite: `change_cursor_active` and `last_incremental_run_at`.
- **On failure:**
  - Retry policy as in step 11. After a stop, the data already applied stays, the cursor points at the last saved response, and the next trigger resumes there. The 15-minute throttle still applies to that next trigger.
  - A 410 `resync_required` goes to step 10.

### 10. Resync required
- **Starts it:** The server answers 410 `resync_required` to a changes request, for example if the device was idle for more than 7 days.
- **Data moves:** None to the old catalogue. Go to step 4 to build a new generation.
- **State kept:** Mark the active generation as stale. Incremental sync on it stops while the build runs, because it would only get 410 again. Reps keep seeing the existing catalogue until step 8a switches generations.
- **On failure:**
  - If storage is short, step 4 refuses to start and the old catalogue stays in use. Show a message that a refresh needs space.
  - Interrupted builds resume as in steps 5 to 8.

### 11. Retry policy (applies to every request in steps 4, 5, 8 and 9)
- **Starts it:** A request ends in a network error or a 5xx response.
- **Data moves:** Re-send the identical request. Waits are 2 s, 4 s, 8 s, 16 s, which allows at most 5 attempts in total.
- **State kept:** The attempt counter lives in memory only, for the current request. It resets on a new request, and on a new run.
- **On failure:**
  - After the 5th failed attempt, stop the run. Keep everything saved and wait for the next trigger.
  - Do not retry 4xx responses. 410 is handled by step 10, and any other 4xx stops the run.
  - Do not retry a page request on cellular (see step 5).

### 12. Open question for Product (not decided here)
- **Question:** During the first download, may reps browse the partly downloaded catalogue, or do they see a progress screen until it finishes?
- **What this plan does:** It leaves the choice open. The build generation lives in the same tables either way, and promotion in step 8a happens only after catch-up. If Product allows browsing, the UI could read the build generation while it is `downloading`. It would show a "still downloading" banner, and some products and any later changes would be missing until catch-up finished. If not, the UI reads only the active generation, and shows progress based on `build_cursor`.
- **Decision needed before:** Building the first-run UI.

---

## Verification to plan

- Kill the app between a page insert and its cursor update (a test hook), and confirm it resumes from the last saved page.
- Edit, delete and insert products on the server, behind and ahead of the cursor, during a download. Confirm that after catch-up the device matches the server.
- Switch Wi-Fi to cellular mid-page, and confirm the page finishes and the download then pauses.
- Test the failure waits (2, 4, 8, 16 s) against a stub that returns 503.
- Request `since` below `purge_floor` and confirm the old catalogue stays visible until the new copy is promoted.
