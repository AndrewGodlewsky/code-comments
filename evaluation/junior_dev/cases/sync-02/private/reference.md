# Plan: Catalogue delta sync for the field-sales app

## State and endpoints

**Server (Catalogue service, Postgres)**
- `products`: `product_id` (primary key), product fields, `change_seq`, `deleted`. Add an index on `change_seq`.
- `purge_horizon_seq`: the highest `change_seq` among tombstones purged so far. The 7-day purge job updates it.

**New endpoints**

| Endpoint | Returns |
|---|---|
| `POST /catalogue/full/start` | `{ start_seq }`: the current highest `change_seq`. |
| `GET /catalogue/full?after_id=X&limit=500` | Non-deleted products with `product_id > X`, in ascending id order, plus `is_last`. |
| `GET /catalogue/changes?since=N&limit=1000` | Rows (tombstones included) with `change_seq > N`, in ascending `change_seq` order, plus `has_more`. Each product appears once, with its latest state. If `N < purge_horizon_seq`, returns **410 resync_required** instead. |

**Device (SQLite)**
- `products`: the live catalogue the app reads.
- `products_staging`: filled during a full download.
- `sync_state`: a single row holding `mode` (`full` or `incremental`), `start_seq`, `cursor` (last saved product id), `pages_done`, `last_seq`, `last_sync_at`.

A page or batch of data and the `sync_state` change that records it are always written in **one SQLite transaction**, so saved progress is never ahead of or behind the saved data.

**Retry rule (applies to every network call below)**
- **Network error or 5xx:** retry the same request after 2 s, 4 s, 8 s and 16 s, with at most 5 attempts in total. Then stop. Everything already committed stays, and the next trigger resumes from `sync_state`.
- **410:** go to step 8.
- **Any other 4xx:** stop and log. Try again at the next trigger.

## Steps

1. **Choose what to run**
   - *Starts:* app launch, or the app returning to the foreground.
   - *Does:* reads `sync_state` and goes to:
     - no row, or `mode = full` with no `start_seq`: step 2;
     - `mode = full`, `start_seq` set, `pages_done = false`: step 3 (resume paging);
     - `mode = full`, `pages_done = true`: step 6 (resume catch-up);
     - `mode = incremental` and `last_sync_at` less than 15 minutes ago: do nothing;
     - otherwise: step 7.
   - *State:* read only.
   - *If it fails:* nothing has changed; the next trigger runs it again.

2. **Start a full download**
   - *Starts:* step 1 or step 8. Wi-Fi only; if the device is not on Wi-Fi, it waits for Wi-Fi.
   - *Data:* `POST full/start` returns `start_seq`.
   - *State:* one transaction empties `products_staging` and writes `sync_state`: `mode = full`, `start_seq`, `last_seq = start_seq`, `cursor = null`, `pages_done = false`.
   - *If it fails:* retry rule. Nothing is written until the call succeeds, so the next trigger starts this step again.

3. **Fetch the next page**
   - *Starts:* the commit in step 2 or step 4, or a resume (step 1 or step 5).
   - *Does:* first checks the network. If the device is not on Wi-Fi, go to step 5.
   - *Data:* `GET full?after_id=<cursor>&limit=500` returns up to 500 products and `is_last`. Only one request is in flight at a time.
   - *State:* nothing is written in this step.
   - *If it fails:* retry rule. The `cursor` has not moved, so the same page is requested next time.

4. **Save the page**
   - *Starts:* a page response arrives. A request already in flight when Wi-Fi drops is allowed to finish, and its page is saved here.
   - *State:* one SQLite transaction:
     - upsert the page's rows into `products_staging`;
     - set `cursor` to the page's last `product_id`;
     - if `is_last`, set `pages_done = true`.
   - *Then:* if `pages_done`, go to step 6; otherwise go to step 3. The next page is never requested before this commit.
   - *If it fails:* if the app dies or the write fails before the commit, nothing from that page is kept. `cursor` still points at the previous page, so this page is fetched again on resume.

5. **Pause and resume**
   - *Starts:* step 3 finds the device off Wi-Fi, or the download stopped because the app was killed, the phone restarted or retries ran out.
   - *Does:* waits. When Wi-Fi returns (while the app is running), or at the next launch or foreground (step 1), it continues at step 3 from the saved `cursor`.
   - *State:* only the committed `cursor` in `sync_state`. It never restarts from page 1.

6. **Catch up and swap**
   - *Starts:* step 4 sets `pages_done`, or step 1 finds `pages_done = true`. This step may use any network.
   - *Data:* runs the step 7 loop against `products_staging`, from `since = last_seq` (which is `start_seq` the first time). This replays every change made while the download was running: updates, inserts with an id behind the cursor, and deletes.
   - *State:* each batch commits together with its new `last_seq`. When `has_more` is false, one transaction replaces `products` with `products_staging` and sets `mode = incremental`, `cursor = null`, `pages_done = false` and `last_sync_at`. Until this commit, the app keeps showing the old `products`.
   - *If it fails:* retry rule. The next trigger resumes the catch-up from the saved `last_seq`. A 410 (for example, a download that took more than 7 days) goes to step 8.

7. **Incremental pull**
   - *Starts:* step 1 (`mode = incremental` and 15 minutes or more since `last_sync_at`), or step 6 for the catch-up. Runs on any network.
   - *Data:* `GET changes?since=<last_seq>&limit=1000` returns up to 1,000 rows in `change_seq` order and `has_more`.
   - *Apply each row:*
     - if `deleted`: delete the local row (a no-op if the row is missing);
     - otherwise: upsert it only if the incoming `change_seq` is greater than or equal to the local row's `change_seq`.
   - *State:* in the same transaction, set `last_seq` to the batch's highest `change_seq`. Repeat while `has_more`, then set `last_sync_at`.
   - *If it fails:* retry rule. Committed batches stay, and the next trigger continues from `last_seq`. A 410 goes to step 8.

8. **Resync required (410)**
   - *Starts:* the changes endpoint returns 410 in step 6 or step 7.
   - *State:* leave `products` unchanged so reps keep their catalogue. Set `mode = full`, clear `start_seq` and `cursor`, and set `pages_done = false`.
   - *Then:* go to step 2, which waits for Wi-Fi, empties `products_staging` and starts again.

## Why nothing is missed
Paging over live data can miss a product inserted with an id behind the cursor, and can return stale rows. Every such change has `change_seq > start_seq`, so step 6 replays it before the catalogue goes live. `change_seq` is assigned at commit, so the feed has no gaps. A change can arrive twice (once in a page and again in the catch-up); the `change_seq >=` rule makes the second copy harmless.

## Open question (not decided)
- **Browsing during the first download.** Product has not decided whether reps may browse the partial catalogue during their first download (reading from `products_staging`, which would be incomplete and filled in id order) or should see a progress screen until step 6 commits.
  - This only matters for the first download. During a forced re-download, the old `products` table is always shown.
