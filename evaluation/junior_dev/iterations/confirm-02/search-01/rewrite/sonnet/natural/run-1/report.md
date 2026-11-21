## Review of search-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-sentence account of how the cron job works today and its three gaps, and moved the summary to the top as three short paragraphs; removed the old bullet summary that retold the steps.
- Added a Terms section defining WAL, replication slot, Debezium, event, commit_lsn, topic, consumer group and offsets, alias, versioned write, DLQ, refresh interval, repeatable-read snapshot, resurrection and the search rule.
- Replaced the ten 'Decisions that matter' with numbered live-path and rebuild steps, each with its trigger, action and failure handling; merged retry, DLQ, batching, version, search rule and offset rules into those steps.
- Moved the replay-order reasoning (why snapshot first, stream second) into rebuild step 3 and the freshness table into live step 7; stated that each fact appears once.
- Added a worked example of the LSN-to-integer conversion, and a note that unparseable events go to the DLQ.
- Added the 'active row count' field to the rebuild-state node in the diagram and the 'target index' to the DLQ payload, which the first version stated in text; added 'for 5 min' to the freshness alert node.
- Merged the 'Where progress is kept' decision into one short section; merged slot-health handling into one section; merged the two snapshot and index-down failure notes plus the gate-abandon rule into the failure table.
- Separated rollout (first migration to products_v4, products_v3 as unclean rollback target) from how the system runs.
- Folded the old open items into one end list; moved the first-migration item to Rolling it out and kept the remaining open items (TOAST, new Kafka objects, row count sign-off, vacuum, refresh interval, versioned deletes).
- Cut the duplicate statements of the same rules (alias-per-group, idempotent replay, 5 s target) that appeared in the summary, decisions, diagram and table.

### Holes
- None.
