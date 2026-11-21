## Review of sync-02 (rewrite, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Kept every stated fact from the brief: about 400,000 products at 2 KB, pages of 500 by ascending product id with keyset pagination, one page at a time, Wi-Fi-only full download with the finish-the-page pause and resume, resume from the last saved page, no missed edits during long downloads, changes in change_seq order up to 1,000 per response including deletes, the launch and foreground trigger throttled to once per 15 minutes, the 7-day tombstone window and resync required, reps keeping the old catalogue until the replacement is ready, and the retry timings (2 s doubling, 5 attempts total, then wait for the next trigger). The first version had none of these in full, so they were added.
- Left the open question about browsing during the first download undecided and kept it under open questions.
- Replaced the first version's eight numbered items with six steps, each stating its trigger, what it does, which data it writes, and what happens on failure, as the brief requires. Merged the separate 'retries' and '410' items into the retry rule, the failure table and step 6 (resync), so each rule is stated once.
- Added a summary and a terms list (Postgres, SQLite, change_seq, tombstone, keyset pagination, cursor, start_seq, last_seq, staging, swap, newer-wins rule, resync required), and a short endpoint list, so a newcomer can follow the steps.
- Added a device state section (the sync_state fields and the storage needed for two copies, about 0.8 GB each) and a shared rules section (position saved with data in one transaction, Wi-Fi-only for the full download and its catch-up, no incremental sync during a full download, one request at a time).
- Made explicit the step 3 catch-up, which the first version named but did not explain: it replays changes since start_seq because a product whose id the cursor has passed, or an edit made during a long download, would otherwise be missed. The catch-up runs before the swap, and the swap sets last_seq so the next incremental sync covers any change committed after the last catch-up request.
- Decided, and recorded in the rules and steps, that incremental sync is skipped during a full download, with the reason that the step 3 catch-up already covers the same changes and running both would conflict over last_seq. Also decided that the catch-up runs on Wi-Fi only because it is part of the full download.
- Added open questions the brief leaves unstated: background running on iOS and Android, and HTTP answers other than network error, 5xx and 410.
- Removed the first version's shorthand wording, such as 'compare change_seq when applying' and 'swap', in favour of the newer-wins rule and a defined swap. Nothing stated in the brief was cut.

### Holes
- None.
