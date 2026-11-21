# Offline product catalogue sync: implementation plan

## Design in brief

The app keeps a full copy of the catalogue (about 400,000 products, 2 KB each) in its local SQLite database. It builds that copy with a paged download, then keeps it current with incremental updates.

The core idea: before downloading, the client records a server position (the watermark). After downloading, it replays every change made since that position. That way edits made during a long download are not missed.

The lifecycle has three parts:

1. **Build.** Download every product page by page (steps 4 to 7). Replay the changes that happened during the download (step 8). Switch the app to the new copy (step 9).
2. **Incremental sync.** Fetch recent changes and apply them to the copy the reps are using (step 10).
3. **Resync.** If the server says the device is too far behind, run a new build and swap it in (step 11).

Steps 1 to 3 are setup and routing. Step 12 is the retry rule shared by all requests. Step 13 is the open question for Product.

**Terms used below**

- **Tombstone:** a deleted product. The row stays in Postgres with `deleted = true` and is purged after 7 days.
- **`change_seq`:** a number stamped on every product insert, update or delete. It comes from one global, strictly increasing sequence and is assigned at commit, so rows become visible in `change_seq` order.
- **Watermark (W):** the highest committed `change_seq` at the moment it is read. Because rows become visible in order, every change with a lower `change_seq` is already visible by then.
- **Purge floor:** the highest `change_seq` of any tombstone the 7-day purge has removed. A changes request whose `since` is below it would miss deletes, so the server refuses it.
- **Generation:** one complete copy of the catalogue in SQLite, identified by a number. Reps read only the *active* generation. A first download or a resync builds a *new* generation (the *build* generation) beside it and never touches the active one.
- **Run:** one execution of the sync logic, started by a trigger (step 3). Only one run exists at a time.
- **Trigger:** an event that starts a run: app launch, return to foreground, or Wi-Fi becoming available.

**Endpoints (new, on the Catalogue service)**

| Endpoint | Returns |
|---|---|
| `GET /sync/watermark` | `{ "watermark": <current max committed change_seq> }`. |
| `GET /catalogue/products?after_id=<id>&limit=500` | Live (non-deleted) products with `id > after_id`, ordered by `id` ascending, each with its `change_seq`. It also returns `has_more`. `after_id` is empty for page 1. |
| `GET /catalogue/changes?since=<change_seq>&limit=1000` | Rows with `change_seq > since`, ordered by `change_seq` ascending. Tombstones are included as `{id, change_seq, deleted: true}`. It also returns `last_seq` and `has_more`. If `since` is below the purge floor, it returns HTTP 410 with code `resync_required`. |

**Why no changes are missed during a long download.** The client reads a watermark W and saves it before it fetches page 1. Every change committed after that has a `change_seq` above W, so `/changes?since=W` returns it. After the last page is saved, the client replays those changes ("catch-up").

A page may already contain a newer version of a row than W, so replay must be harmless. It is, because each change is applied as an upsert or delete keyed by `id`, and only if the incoming `change_seq` is at least the stored one.

- A row inserted behind the page cursor is caught by the replay.
- A row deleted after it was paged is removed by its tombstone.
- A row deleted before it was paged is never served, and its tombstone replay does nothing.

**Local storage (existing SQLite database, new tables)**

- `products(generation, id, change_seq, payload)`, primary key `(generation, id)`. About 800 MB per generation.
- `sync_state`, a single row:
  - `active_generation`: the generation reps read (null until the first download finishes).
  - `active_stale`: true after a `resync_required`.
  - `build_generation`: the generation being built (null when no build is in progress).
  - `build_phase`: `none`, `downloading` or `catching_up`.
  - `build_watermark`: W for the current build.
  - `build_cursor`: the id of the last saved product (null before the first page).
  - `change_cursor_build`: the catch-up position for the build.
  - `change_cursor_active`: the incremental position for the active generation.
  - `last_incremental_run_at`: when the last incremental run started.

**Assumptions I am making (flag if wrong)**

- The sync runs while the app process is alive. OS background tasks are out of scope.
- 4xx responses other than 410 are not retried, because the brief lists only network errors and 5xx.
- The 15-minute throttle counts from the start of the last incremental run, whether or not it succeeded.
- A page request that fails after the device left Wi-Fi is not retried on cellular. The download pauses at the same cursor.

---

## Steps

### 1. Server: build the three endpoints and their indexes
- **Starts it:** Delivery work, before any client work.
- **Data moves:** None yet. Create:
  - An index on `products(id)` where `deleted = false`, for the page query.
  - An index on `products(change_seq)`, for the changes query.
  - A stored `purge_floor`, updated inside the 7-day purge job.
- **State kept:** Postgres, including `purge_floor`.
- **On failure:** If `purge_floor` is missing or wrong, a client could silently miss deletes. Treat that as a release blocker. Add a server test that creates a tombstone, purges it, requests `since` below the floor, and expects 410.

### 2. Client: create the local schema and the single-flight sync runner
- **Starts it:** App upgrade to the version containing this feature, via a SQLite migration.
- **Data moves:** None. Create the tables above, with `sync_state` empty (`active_generation = null`).
- **State kept:** SQLite.
- **On failure:** If the migration fails, the app starts without a catalogue and settings are unaffected. The migration runs again on the next launch.
- **One run at a time:** A mutex allows exactly one run. A trigger that arrives while a run is active is dropped, not queued.

### 3. Trigger handler: decide what to run
- **Starts it:** Any of these triggers:
  - App launch.
  - App returns to foreground.
  - Wi-Fi becomes available.

  A run that stops early (for example after the retries in step 12 run out) does not restart itself. Its unfinished work waits for the next trigger.
- **Data moves:** Read `sync_state` only. Choose the first branch that matches:
  1. `build_generation` is not null (a build is in progress): go to step 5 if `build_phase = downloading`, or step 8 if `catching_up`.
  2. `active_generation` is null (first download), or `active_stale` is true (resync needed): go to step 4.
  3. Otherwise a usable catalogue exists: go to step 10 (incremental sync), but only for launch and foreground triggers. A Wi-Fi-available trigger does nothing here.
- **State kept:** Read from SQLite.
- **On failure:** If the SQLite read fails, abort the run and wait for the next trigger.

### 4. Start a full build (first download or resync)
- **Starts it:** Step 3 found no catalogue or a stale one, or step 8 had to discard a build.
- **Data moves:**
  1. Check free disk space. A build needs about 1 GB, and a resync keeps the old copy, so it needs roughly double. If space is short, do not start: show a "not enough storage" message and keep any existing catalogue.
  2. Check that the device is on Wi-Fi. If not, stop. The Wi-Fi-available trigger will restart this step.
  3. Call `GET /sync/watermark` (retry policy in step 12). Call the result W.
  4. In one SQLite transaction, write `build_generation = (highest existing generation) + 1`, `build_phase = downloading`, `build_watermark = W`, `build_cursor = null`, `change_cursor_build = null`.
- **State kept:** `sync_state` in SQLite. W is committed before page 1 is requested.
- **On failure:**
  - If the app dies before the transaction commits, nothing is saved and the next trigger starts again with a new W.
  - If the watermark call fails after 5 attempts, stop and keep whatever exists.
- **Next:** Step 5.

### 5. Download pages (loop, one page at a time)
- **Starts it:** Step 4 finished, or step 3 found `build_phase = downloading`.
- **Data moves:** Before each page, check that the device is on Wi-Fi. If it is not, go to step 7. Otherwise request `GET /catalogue/products?after_id=<build_cursor>&limit=500`. Each page is about 1 MB. Requests are strictly sequential, never parallel.
- **State kept:** Nothing is written until the response has fully arrived (step 6).
- **On failure:**
  - A network error or 5xx follows the retry policy in step 12. After 5 attempts the run stops, keeping the saved pages and `build_cursor`.
  - If the device drops to cellular while a page is in flight, let that request finish and save it (step 6). The Wi-Fi check before the next page then sends the run to step 7.
  - If the in-flight request fails after the device left Wi-Fi, do not retry it on cellular. Go to step 7 at the same cursor.

### 6. Save a page atomically
- **Starts it:** A complete page response arrived.
- **Data moves:** In one SQLite transaction:
  1. Upsert the page's rows (up to 500) into `products` under `build_generation`, so a repeated page is harmless.
  2. Set `build_cursor` to the last `id` in the page.
- **State kept:** SQLite. The page and the cursor commit together, or neither does.
- **On failure:**
  - If the app is killed or the phone restarts mid-transaction, SQLite rolls the page back. The cursor still points to the previous fully saved page, so the next run re-requests the following page from there. Resuming never goes back to page 1.
  - If the write fails (for example, the disk is full), stop the run, show a storage message, and keep the saved pages.
- **Next:** If `has_more` is true, return to step 5. If false, go to step 8.

### 7. Pause while off Wi-Fi
- **Starts it:** Step 5 found the device is on cellular or offline.
- **Data moves:** None while paused.
- **State kept:** Nothing extra. `build_cursor` already holds the position.
- **Resume:** When Wi-Fi returns, the Wi-Fi-available trigger runs step 3, which resumes at step 5.
- **On failure:** If the app is killed while paused, the next launch trigger resumes from `build_cursor` once Wi-Fi is present.

### 8. Catch up on changes made during the download
- **Starts it:** The last page was saved (`has_more = false`), or step 3 found `build_phase = catching_up`.
- **Data moves:**
  1. If `build_phase` is still `downloading`, in one transaction set `build_phase = catching_up` and `change_cursor_build = build_watermark`.
  2. Request `GET /catalogue/changes?since=<change_cursor_build>&limit=1000`. This may use any network.
  3. In one transaction, apply every change in the response to `build_generation`: upsert live rows, delete tombstoned ids, and skip any change whose `change_seq` is lower than the stored row's. Then set `change_cursor_build = last_seq`.
  4. Repeat steps 2 and 3 while `has_more` is true.
  5. When the loop ends, go to step 9.
- **State kept:** SQLite: `change_cursor_build` and the build rows.
- **On failure:**
  - Retry policy as in step 12. After a stop, the next trigger resumes from `change_cursor_build`.
  - If the server answers `resync_required`, the download took too long (W fell below the purge floor). Discard the build generation (delete its rows in batches) and go to step 4 for a fresh build. The old catalogue stays visible.

### 9. Promote the new copy
- **Starts it:** Catch-up is complete.
- **Data moves:** In one transaction, set `active_generation = build_generation`, `active_stale = false`, `change_cursor_active = change_cursor_build`, `build_generation = null`, `build_phase = none`, `last_incremental_run_at = now`. After the commit, delete the previous generation's rows in batches in the background.
- **State kept:** `sync_state`. The switch is a single transaction, so reps see either the old catalogue or the complete new one, never a mixture.
- **On failure:**
  - If the app dies before the commit, the next trigger finds `catching_up` and runs step 8 again, which is safe because applying changes is idempotent.
  - If the app dies after the commit, leftover old rows are invisible, because reads use `active_generation` only. A cleanup job removes them on the next launch.

### 10. Incremental sync
- **Starts it:** App launch or return to foreground (routed here by step 3), when all of these hold:
  - `active_generation` is not null and `active_stale` is false.
  - No build is in progress.
  - At least 15 minutes have passed since `last_incremental_run_at`, or it is null. If the system clock has moved backwards, treat the throttle as elapsed.

  Otherwise skip silently.
- **Data moves:**
  1. Set `last_incremental_run_at = now`.
  2. Request `GET /catalogue/changes?since=<change_cursor_active>&limit=1000`, on any network.
  3. In one transaction, apply the changes to the active generation exactly as in step 8, then set `change_cursor_active = last_seq`.
  4. Repeat steps 2 and 3 while `has_more` is true.
- **State kept:** SQLite: `change_cursor_active` and `last_incremental_run_at`.
- **On failure:**
  - Retry policy as in step 12. After a stop, the data already applied stays, the cursor points at the last saved response, and the next trigger resumes there. The 15-minute throttle still applies to that trigger.
  - A 410 `resync_required` goes to step 11.

### 11. Resync required
- **Starts it:** The server answers 410 `resync_required` to an incremental changes request (step 10), for example because the device was idle for more than 7 days.
- **Data moves:** None to the old catalogue. Set `active_stale = true` and go to step 4 to build a new generation.
- **State kept:** `active_stale` in `sync_state`. While it is true, incremental sync is skipped, because it would only get 410 again. Reps keep seeing the existing catalogue until step 9 switches generations.
- **On failure:**
  - If storage is short, step 4 refuses to start and the old catalogue stays in use. Show a message that a refresh needs space. Each later trigger tries step 4 again, because `active_stale` is still true.
  - Interrupted builds resume as in steps 5 to 8.

### 12. Retry policy (applies to every request in steps 4, 5, 8 and 10)
- **Starts it:** A request ends in a network error or a 5xx response.
- **Data moves:** Re-send the identical request. The waits are 2 s, 4 s, 8 s and 16 s, which gives at most 5 attempts in total.
- **State kept:** The attempt counter lives in memory only, for the current request. It resets on each new request and each new run.
- **On failure:**
  - After the 5th failed attempt, stop the run. Keep everything already saved and wait for the next trigger.
  - Do not retry 4xx responses. A 410 from an incremental request goes to step 11, a 410 during catch-up goes to step 8's discard path, and any other 4xx stops the run.
  - Do not retry a page request on cellular (see step 5).

### 13. Open question for Product (not decided here)
- **Question:** During the first download, may reps browse the partly downloaded catalogue, or do they see a progress screen until it finishes?
- **What this plan does:** It leaves the choice open. The build generation lives in the same tables either way, and promotion in step 9 happens only after catch-up.
  - If Product allows browsing, the UI could read the build generation while it is `downloading`. It would show a "still downloading" banner, and some products and all later changes would be missing until catch-up finished.
  - If not, the UI reads only the active generation and shows a progress screen based on `build_cursor`.
- **Decision needed before:** Building the first-run UI.

---

## Verification to plan

- Kill the app between a page insert and its cursor update (using a test hook), and confirm it resumes from the last saved page.
- Edit, delete and insert products on the server, both behind and ahead of the page cursor, during a download. Confirm that after catch-up the device matches the server.
- Switch Wi-Fi to cellular mid-page, and confirm the page finishes and the download then pauses.
- Test the retry waits (2, 4, 8, 16 s) against a stub that returns 503.
- Request `since` below `purge_floor` and confirm the old catalogue stays visible until the new copy is promoted.