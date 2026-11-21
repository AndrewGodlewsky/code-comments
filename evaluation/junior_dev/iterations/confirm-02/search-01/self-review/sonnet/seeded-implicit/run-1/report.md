## Review of search-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Expanded the thin outline into a full plan: the original diagram and notes did not cover triggers, data moved, progress storage or failure handling, so the document could not stand alone.
- Added a plain-language overview and short definitions of slot, commit_lsn, alias, feeder and DLQ for a reader new to the stack.
- Added explicit event-handling rules: upsert vs delete by status and op, commit_lsn converted to an integer version, stale-conflict handling, safe replays, ordering, offset commits.
- Rewrote the Mermaid flowchart with subgraphs for live sync, failures, rebuild and serving, labelled edges showing data moved, and dotted edges for each failure kind.
- Spelled out the rebuild as eight ordered steps, with the control record that stores progress, the replay_from margin, the gate, the alias swap, the 48 h hold and cleanup.
- Resolved the rebuild design: the backfill runs first at version 0 and Feeder B then replays from replay_from, which avoids a deleted row being resurrected by an older snapshot row.
- Made the 48-hour rollback concrete: Feeder A keeps v3 current while Feeder B keeps v4 current, so swapping back loses nothing.
- Clarified the WAL behaviour: a slow indexer does not grow the WAL, only a stopped Debezium or Kafka does. Added the 20 GB and 50 GB handling and the recovery path through a rebuild.
- Added a failure summary table, a latency budget marked as an estimate, and an open-items list that flags the versioned-delete and first-rollout assumptions.
- Defined Debezium, Kafka offset, and feeder (A fills v3, B fills v4) up front so later sections read without prior knowledge.
- Moved the transient-error and invalid-document rules into the indexer rules section so all event handling lives in one place.
- Fixed diagram step numbering: step 1 (Prepare) is now one node matching the prose; step 2 is its own node; labels for steps 6 and 8 match the prose names.
- Renamed 'before/after the swap' on the alias edges to 'switch' for consistent wording.
- Defined last_id where first mentioned.
- Clarified the gate's lag measure (no unread events, or newest applied event under 5 s old), which previously failed on quiet periods, and stated both conditions must hold on 3 consecutive checks.
- Made replay start concrete: Feeder B seeks to the first offset at or after replay_from by timestamp.
- Replaced 'a few hours of events takes minutes' with the actual figure (about 2.7 million events at peak rate).
- Clarified that Feeder A writes v3 by real name and that the WAL does not grow when only the indexer is down.
- Added a short note on when a rebuild is used, and minor wording trims throughout.
- Added a one-line 'how to read the diagram' key and a 'Refresh' term, since refresh latency was used without explanation
- Explained the commit_lsn to integer conversion with a worked example (0/16B3748 = 23,803,720)
- Spelled out the event fields (op, id, after, commit_lsn) where the write rules start
- Split the write rule into short sub-bullets and clarified that a version conflict is a stale event, not an error
- Replaced the confusing gate wording 'less than 5 s old when it was written' with 'when it was applied'
- Turned the gate and replay explanations into sub-bullets and gave the replay duration an explicit assumed rate (10,000 events/s)
- Clarified the backfill-crash row: replay still starts from the original replay_from
- Noted in First rollout that Feeder A does not exist today, to resolve the apparent conflict with 'always running'
- Replaced '409 conflict' in the diagram with 'version conflict' and 'treat as success' with 'treat as done'; made 'ops drops the slot' mention it is to protect the primary
- Tightened wording throughout and used 'None' in the failure table

### Holes
- None.
