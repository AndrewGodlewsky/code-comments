# Catalogue sync plan

The app keeps the whole product catalogue (about 400,000 products at roughly 2 KB each, so about 800 MB) in its local SQLite database, so reps can browse and quote offline. Today there is no sync API: the Catalogue service stores products in Postgres, and the app uses SQLite only for user settings. The client first downloads everything into a staging table, then applies the edits made while it downloaded, then swaps staging in as the live catalogue. After that it stays current with small incremental updates. Staging exists so that a rep who already has a catalogue keeps seeing it until the replacement is completely ready.

## Terms

- **`change_seq`**: a number on every product row in Postgres. Each insert, update or delete takes the next value from one global, strictly increasing sequence. The value is assigned at commit, so rows become visible in `change_seq` order. A higher number means a newer change.
- **Tombstone**: a deleted product. The row stays with `deleted = true` and is purged after 7 days.
- **Keyset pagination**: each page request says "give me the products after this product id" instead of "page number N". The cursor is the last product id already received.
- **`start_seq`**: the highest `change_seq` that exists when a full download begins. Every edit made after it is fetched later as a change.
- **`last_seq`**: the `change_seq` of the last change the client has applied. Incremental sync asks for changes after it.
- **Staging**: the client table `products_staging`. A full download fills it. The live table is `products`.
- **Resync required**: the server's answer (HTTP 410, body `resync_required`) when a client asks for changes from a position older than the 7-day tombstone window. The server can no longer list every delete since then, so the client must download everything again.

## Rules that apply to several steps

- Full-download pages hold 500 products, ordered by product id ascending, and are fetched one at a time, never in parallel.
- Incremental responses hold up to 1,000 changes, in `change_seq` order, including deletes.
- The full download runs only on Wi-Fi. Incremental sync may use any network.
- Retries: after a network error or a 5xx response, the client retries the same request. It waits 2 s, then 4 s, 8 s and 16 s, with at most 5 attempts in total. After that it stops, keeps everything already saved, and waits for the next trigger.
- Every write to SQLite that records progress is one transaction together with the data it describes. A crash never leaves a cursor or `last_seq` that is ahead of the saved data.

## Server endpoints

1. `POST /catalogue/full/start` returns `start_seq`, the current highest `change_seq`. It is safe because rows become visible in order: no change with a lower number can appear later. Its trigger is the client beginning a new full download. If it fails, the client retries it under the retry rule and no state has changed.
2. `GET /catalogue/full?after_id=<id>` returns the next 500 products after that id, live (non-deleted) products only, each carrying its `change_seq`. A product edited since `start_seq` may arrive already in its newer state. The last page is the one with fewer than 500 products.
3. `GET /catalogue/changes?after_seq=<n>` returns up to 1,000 changes with `change_seq` greater than `n`, in order, including deletes, plus a `has_more` flag. If `n` is older than the 7-day tombstone window it returns 410 `resync_required`.

## Client state

The client has three SQLite tables. `products` is the live catalogue that reps see. `products_staging` is filled by a full download. `sync_state` holds `last_seq`, `start_seq`, the full-download cursor, the time of the last incremental attempt, and whether a full download is in progress.

## Steps

1. **Start a full download.**
   - Trigger: first launch with no catalogue, or step 7 below.
   - Do: clear `products_staging`, call `POST /catalogue/full/start`, and save `start_seq` and an empty cursor in `sync_state`.
   - Fails: the retry rule applies. The next trigger starts again from here.
2. **Download pages into staging.**
   - Trigger: a full download is in progress and the device is on Wi-Fi.
   - Do: fetch one page after the saved cursor. In one transaction, write its products to `products_staging` and move the cursor to the last product id of the page. Then fetch the next page.
   - State: staging and the cursor in SQLite. Because page and cursor are saved together, an interruption (app killed, phone restarted, network lost) resumes from the last fully saved page, not page 1.
   - Fails: the retry rule applies. After five failed attempts it stops and keeps the saved pages. If the device drops to cellular, it finishes the page it is on, then pauses. It carries on from the cursor when Wi-Fi returns.
3. **Catch up on edits made during the download.**
   - Trigger: the last page has arrived. Edits continue all day, and the download can take hours, so some products in staging are out of date and some have been deleted.
   - Do: call `/catalogue/changes` repeatedly from `start_seq` until `has_more` is false, applying each change to staging. A change is applied only when its `change_seq` is higher than the one on the staging row (or when no row exists, for an update). Otherwise it is skipped, because the page already held a newer copy. A delete removes the staging row. This apply rule also guards against a page that arrived already newer than `start_seq`.
   - State: staging, plus the highest `change_seq` applied so far, saved in the same transaction as each batch.
   - Fails: the retry rule applies, and the catch-up resumes from the saved position on the next trigger. A 410 means the download took more than 7 days or was paused that long. Go back to step 1.
4. **Swap.**
   - Trigger: catch-up has finished.
   - Do: in one SQLite transaction, replace the contents of `products` with `products_staging`, set `last_seq` to the last `change_seq` applied, clear staging, and mark the full download finished. Reps see the new catalogue all at once.
   - Fails: the transaction either happens completely or not at all. If the app dies first, the old catalogue is untouched and the next launch redoes the swap or resumes step 3.
5. **Incremental sync.**
   - Trigger: app launch, or the app returning to the foreground, but at most once every 15 minutes (measured from the last attempt, saved in `sync_state`, whether it succeeded or not). It is skipped while a full download is in progress.
   - Do: call `/catalogue/changes?after_seq=<last_seq>` and apply each change to `products` with the same rule as step 3 (higher `change_seq` wins, delete removes the row). In one transaction per response, write the changes and the new `last_seq`. Repeat while `has_more` is true. Any network may be used.
   - Fails: the retry rule applies. Progress already saved stays, and the next trigger continues from `last_seq`.
6. **Resync required.**
   - Trigger: step 5 receives 410 `resync_required`.
   - Do: start a full download (step 1). Reps keep seeing the existing `products` table until the swap in step 4 replaces it. If the device is not on Wi-Fi, the download waits, and the old catalogue stays visible in the meantime.
   - Fails: as in steps 1 to 4.

## What happens when things fail

| Failure | Result |
|---|---|
| Network error or 5xx on any request | Retry the same request, waiting 2 s doubling each time, 5 attempts in total. Then stop, keep saved data, wait for the next trigger. |
| App killed or phone restarted mid-download | Resume from the saved cursor (step 2), or from the saved catch-up position (step 3). |
| Wi-Fi lost during a full download | Finish the current page, pause, resume on Wi-Fi. |
| 410 `resync_required` during catch-up | Restart the full download from step 1. |
| 410 `resync_required` during incremental sync | Full download again, old catalogue stays visible until the swap. |
| Crash during the swap | Nothing changed. The old catalogue is intact. |

## Open questions

- Product has not decided whether reps may browse the partly downloaded catalogue during their first download, or must see a progress screen until it finishes. This plan does not decide it. If browsing is allowed, the screen would have to read from `products_staging`, which is not yet caught up on edits.
- Not known: whether the Postgres service can serve the full-download query efficiently while it also excludes tombstones. This plan assumes it can.