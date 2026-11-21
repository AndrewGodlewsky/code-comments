## Review of dp-01 (rewrite-v7, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a summary (what the job does, the main flow, and why the lookback and merge are shaped that way) and a terms list for the names a newcomer would not know, such as replica, watermark, lookback, staging, merge, commit, checksum and etl_runs.
- Rebuilt the Mermaid flowchart so it shows what starts each step (scheduler at 02:00, 06:00 check, Sunday reconciliation), which data moves where, where state lives (etl_watermark, etl_runs, stg_orders, fact_orders), and the failure and retry loop with the third-failure page.
- Spelled out the merge in steps: newest row per order_id in staging, update only when newer, insert new orders, is_deleted set from deleted_at, watermark moved forward only within the commit transaction.
- Added a failure table covering extract, merge, commit, third failure, the 06:00 staleness alert and the Sunday reconciliation mismatch, with the watermark state for each.
- Expanded the Sunday reconciliation into three numbered steps, including that a mismatch on either count or checksum triggers a reload and that reconciliation does not move the watermark.
- Kept every stated fact from the first version and the brief: 02:00 UTC start, read-only replica, bookkeeping in the warehouse, updated_at and deleted_at as writes, no hard deletes, is_deleted flag, 90-minute bulk imports, 2-hour lookback, one row per order_id with the latest version, idempotent re-runs, watermark advancing only after a successful load, two retries 15 minutes apart, page after the third failure, 06:00 dashboards, staleness alert to #data-alerts, and 30-day Sunday reconciliation.
- Decided, within the brief's allowance: staging is emptied at the start of each attempt; a retry repeats the whole night from the same watermark; etl_runs logs one row per attempt; reconciliation does not move the watermark.
- Removed the repeated bullet list of the first version, since each rule now appears once in the steps or the failure table.
- Moved unknowns into an open-questions list: the creation-date column name, the first-run watermark, ties on updated_at, rows more than 30 days late, and failed Sunday reloads.

### Holes
- None.
