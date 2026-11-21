# Catalogue sync plan

The field-sales app keeps the whole product catalogue on the device, so reps can browse and quote offline. The catalogue has about 400,000 products of about 2 KB each, so one full copy is about 800 MB.

The plan has two kinds of sync:

- A **full download** builds a complete copy of the catalogue on the device. It reads the server one page at a time, and reps keep using their old copy until the new one is ready.
- **Incremental sync** then keeps that copy current. It asks the server for the list of changes made since the last time it ran.

## Terms used in this plan

- **Product**: one catalogue item.
- **Page**: a batch of up to 500 products returned by one server request.
- **change_seq**: a number the server gives to every product insert, update or delete. All changes share one counter, and each new change gets a larger number than the one before it. A change becomes visible to the app only after the server has saved it, and visible changes always appear in `change_seq` order. So the server never shows change 105 while change 104 is still being saved.
- **Tombstone**: a row that marks a deleted product (`deleted = true`). The server keeps tombstones for 7 days, then removes them. A device that asks for changes from before that window may have missed some deletes.
- **Keyset pagination**: each page asks for products whose id comes after the last id of the previous page. The server does not count rows from the start, so a download can resume from the last id the device saved.
- **SQLite**: the small database file the app already uses on the device, mainly for user settings. This plan adds two tables to it.
- **Transaction**: a group of database writes that either all happen or none happen. If the app is killed in the middle, none of the writes are kept.
- **Staging**: a second table on the device (`products_staging`) where the new copy is built. Reps never see it.
- **Swap**: one transaction that replaces the live copy with the staging copy.
- **Wi-Fi only**: the app does not start these requests on cellular data.
- **Positions**: three saved `change_seq` numbers.
  - `start_seq` is the highest change number when a full download began.
  - `catchup_seq` is how far the staging copy has been brought up to date with changes.
  - `last_seq` is how far the live `products` table has been brought up to date.
- **HTTP status codes**: a **5xx** is a server error. A **410** with the body `resync_required` means the saved position is too old. Other **4xx** codes mean the request itself was wrong.

## Why the two parts fit together

The full download reads the catalogue page by page while edits keep happening. A product might be missed, or read in a state that is older or newer than the one on the server. The change feed fixes this. It starts from `start_seq`, the position taken when the download began, so it covers every edit made since then.

When the device has two versions of the same product, the version with the higher `change_seq` is the newer one. The device keeps that version and ignores older ones. Step 5 describes this rule.

## Plan

### 1. Server endpoints

The server provides three endpoints. The device calls them; the server has no steps of its own here.

- **`POST /catalogue/full/start`** begins a full download. The reply contains `start_seq`, the highest `change_seq` visible at that moment. The device saves it.
- **`GET /catalogue/full?after_id=X&limit=500`** returns up to 500 live products (no tombstones) whose id is greater than X, in id order. Each product includes its `change_seq`. The reply includes `next_after_id`. On the last page there is no `next_after_id`.
- **`GET /catalogue/changes?since=N`** returns up to 1,000 changes whose `change_seq` is greater than N, in `change_seq` order. Deletes come back as tombstones. The reply includes `has_more`. The server returns only visible changes, so a change that is saved late is not skipped. If N is older than the 7-day tombstone window, the server replies `410 resync_required`.

### 2. Device database (SQLite)

- **`products`**: the live catalogue that reps browse. Each row holds the product fields and its `change_seq`.
- **`products_staging`**: the copy being built during a full download. It has the same columns as `products`.
- **`sync_state`**: one row that records:
  - `mode`: `full` or `incremental`
  - `phase`: during a full download, either `downloading` (step 3) or `catching_up` (step 4). This tells a resumed run where to continue.
  - `start_seq`: from step 1
  - `cursor`: the id of the last product saved in staging
  - `catchup_seq`: the last change applied to staging
  - `last_seq`: the last change applied to `products`
  - `last_incremental_at`: when the last incremental run started

The app's existing settings tables do not change.

**Storage:** during a full download both copies exist, so the device needs room for about 1.6 GB (two copies of about 800 MB).

### 3. Full download into staging (Wi-Fi only)

- **Starts:** the app finds no complete catalogue (first install, or a resync from step 6), or finds an unfinished download at launch or on returning to the foreground (step 8). A download can also resume when Wi-Fi returns during an open session.
- **Data:**
  1. If there is no saved `start_seq`, call `POST /catalogue/full/start` and save the result as `start_seq`.
  2. Set `phase` to `downloading`.
  3. Request one page at a time, never two at once. Set `after_id` to the saved `cursor`. On the first page the cursor is empty.
  4. In one transaction, write the page's products into `products_staging` and set `cursor` to the id of the page's last product.
  5. Repeat steps 3 and 4 until a page has no `next_after_id`. Then go to step 4.
- **Wi-Fi:** the device checks the connection before each request. If the connection switches to cellular, the request already in flight may finish and be saved. The download then pauses. When Wi-Fi returns, the download resumes, whether or not the app is open.
- **Interruption:** a page is saved all at once or not at all. If the app is killed or the phone restarts during a page, that page is not saved. On the next run the app requests the same page again, using the saved `cursor`. It never starts again from page 1.
- **Failure:** follow step 7. If the retries run out, nothing is deleted. Staging and `cursor` are kept, and the download waits for the next trigger.

### 4. Catch up, then swap

- **Starts:** the last page of step 3 has been saved.
- **Data:**
  1. Set `phase` to `catching_up`. Set `catchup_seq` to `start_seq` if it is not already set.
  2. Call `GET /catalogue/changes?since=catchup_seq`. Apply each change to `products_staging` using the rule in step 5. In the same transaction, save the new `catchup_seq`.
  3. Repeat while `has_more` is true.
- **Swap:** when a catch-up call returns no more changes, one transaction does the following:
  - deletes the old rows in `products`, then copies every row from `products_staging` into `products`
  - sets `last_seq` to `catchup_seq`
  - sets `mode` to `incremental`
  - empties `products_staging`
- **Why reps are not affected:** `products` is not touched until the swap. Reps keep their existing catalogue until the new one is complete. On a first install the catalogue stays empty until the swap.
- **Edits during the swap:** an edit saved after the last catch-up page is not in the new copy yet. The next incremental sync picks it up, because `last_seq` records the last change applied.
- **Wi-Fi:** the plan treats catch-up as part of the full download, so it also runs on Wi-Fi only.
- **Failure:** network errors and 5xx responses follow step 7. A `410 resync_required` goes to step 6.

### 5. Incremental sync from `last_seq`

- **Starts:** a trigger from step 8 when `mode` is `incremental`.
- **Data:** call `GET /catalogue/changes?since=last_seq`. Apply the changes in order, then repeat while `has_more` is true. The changes include deletes.
- **Apply rule for each change, matched by product id:**
  1. If a row already exists and the change's `change_seq` is not greater than the stored row's `change_seq`, skip the change. Old or repeated changes do nothing.
  2. If the change is a tombstone, delete the row. If there is no row, do nothing.
  3. Otherwise, insert the row, or replace the existing row.
- **State:** the changes from each page and the new `last_seq` are written in one transaction.
- **Network:** any network may be used.
- **Failure:** follow step 7. Because `last_seq` is saved with each page, the next run continues from the last change applied.

Step 4 applies changes to the staging table with this same rule.

### 6. Resync required (`410`)

- **Starts:** a change-feed request in step 4 or step 5 gets `410 resync_required`. The saved position is older than the 7-day tombstone window, so some deletes may have been lost.
- **Action:**
  1. Set `mode` to `full` and `phase` to `downloading`.
  2. Empty `products_staging`, and clear `cursor` and `catchup_seq`.
  3. Call `POST /catalogue/full/start` and save the new `start_seq`.
  4. Run step 3 from the beginning.
- **State:** `products` is not changed. Reps keep the old copy, which may be out of date, until the next swap.
- **Failure:** follow step 7. The old copy stays in use until a new swap completes.

### 7. Retries after failures

- **Starts:** a network error or a 5xx response on any request in steps 3 to 6.
- **Data:** send the same request again, unchanged.
- **Waits:** 2 s, then 4 s, 8 s and 16 s. That is 5 attempts in total: the first try and 4 retries. Each request has its own count.
- **After 5 failed attempts:** stop. Nothing already saved is removed. The app waits for the next trigger from step 8.
- **Other errors:** a 4xx response other than `410` is not retried. The app stops and waits for the next trigger. The brief does not cover this case, so this is the plan's choice.

### 8. Triggers: launch and return to the foreground

- **Starts:** the app launches, or returns to the foreground.
- **Action:**
  - If `mode` is `full`, resume the download at the step recorded in `phase`: step 3 if it is `downloading`, or step 4 if it is `catching_up`. On cellular this does nothing, because the download is paused.
  - If `mode` is `incremental`, run step 5, unless `last_incremental_at` is less than 15 minutes ago. This limits incremental runs to at most one every 15 minutes. Save `last_incremental_at` when a run starts. The 15 minutes are counted from that moment, including a run that later fails.
- **Network:** a full download needs Wi-Fi. Incremental sync may use any network.
- **Failure:** follow step 7.

## Open question

**Can reps browse the catalogue during their first download?** The product team has not decided. The options are:

- let reps browse the partly filled staging copy, or
- show a progress screen until the download finishes.

This plan does not choose. As written, reps see nothing from the new catalogue until the swap in step 4.