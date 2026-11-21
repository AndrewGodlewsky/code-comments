## Offline product catalogue sync for the field-sales app

Our iOS and Android field-sales app needs the whole product catalogue on the device so reps can browse and quote while offline. The catalogue has about 400,000 products at roughly 2 KB each. Please plan the sync: a first full download, which must survive interruptions, followed by incremental updates.

**Existing system**
- The Catalogue service stores products in Postgres. Every insert, update or delete of a product stamps that row with a `change_seq` taken from one global, strictly increasing sequence. The value is assigned at commit, so rows become visible in `change_seq` order.
- Deletes are soft. The row stays as a tombstone (`deleted = true`) and tombstones are purged after 7 days.
- The app already has a local SQLite database, which it uses for user settings.
- There is no sync API yet. You design the endpoints.

**Fixed requirements**
- Full download: pages of 500 products, ordered by product id ascending, using keyset pagination. Pages are fetched one at a time, never in parallel.
- The full download runs only on Wi-Fi. If the device drops to cellular, it finishes the page it is on and pauses, then carries on when Wi-Fi returns. Incremental sync may use any network.
- If the download is interrupted (app killed, phone restarted, network lost), it must resume from the last page that was fully saved, not from page 1.
- Catalogue edits happen all day, including during a rep's first download, which can take hours. The device must not miss any of those changes.
- Incremental sync: changes come back in `change_seq` order, up to 1,000 per response, and include deletes. It runs at app launch and whenever the app returns to the foreground, at most once every 15 minutes.
- If a client asks for changes from a position older than the 7-day tombstone window, the server answers "resync required" and the client must do a full download again. Reps keep seeing their existing catalogue until the replacement is completely ready.
- Failures: after a network error or a 5xx response, the client retries the same request, waiting 2 s and then doubling the wait each time, with at most 5 attempts in total. After that it stops and waits for the next trigger, keeping everything it has already saved.

**Not decided**
Product has not decided yet whether reps may browse the partly downloaded catalogue during their *first* download, or should see a progress screen until it finishes. Do not decide this. Mark it as an open question.

**Deliverable**
Write a numbered, step-by-step plan in Markdown. For each step, say what starts it, what data moves, where state is kept and what happens on failure.
