## Review of search-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short glossary (WAL, replication slot, LSN, Debezium, Kafka partition and offset, alias, DLQ, repeatable-read snapshot) so a reader outside the project can follow.
- Rebuilt the Mermaid flowchart as two labelled subgraphs, live sync and rebuild, with each edge labelled by its trigger, data, progress store or failure path. Added the search API and alias, the switch, the 48-hour dual-write and the rollback edge.
- Added the rules the draft left out: the version rule and what a conflict means, offsets committed only after acknowledgement, retry backoff (1 s doubling to a 60 s cap, never skip ahead), the DLQ path, WAL alerts at 20 GB and 50 GB, and the switch criteria.
- Explained how commit_lsn becomes a whole-number version, and why backfill rows use the snapshot's WAL position as their version.
- Added the cron retirement order, the note that rows hard-deleted before cutover can remain in products_v3 until the first rebuild, and the 7-day Kafka retention check.
- Chose to keep writing to products_v3 for 48 hours after the switch (dual write), so that rollback loses no changes. The brief required this result but did not name a method; please confirm the method.
- Flagged two open items: confirm the store keeps versions of deleted documents, and get DBA approval for a second snapshot if a backfill must resume after a crash.
- Opened with a plain statement of what the cron job gets wrong and why it is being replaced, so a reader knows the problem before the design.
- Expanded the word list: added index, document, version, stale write, lag, active row count and snapshot, and defined each in plain terms.
- Made the version rule concrete: the 2^32 formula now has a worked example (0/16B3748 = 23,803,720) and a plain explanation of the stale-write case.
- Added that the WAL position S and the snapshot, and the Kafka offsets, must be taken at the same moment, which the original did not state.
- Rewrote the backfill safety argument in plain steps: live changes after S win, and replayed changes older than S are rejected because the snapshot already has them.
- Fixed the 48-hour dual-write paragraph, which said products_v3 'is current' in a confusing order; it now says both indexes receive every change during the window and products_v3 is deleted afterwards.
- Rewrote the job-crash failure: any restart needs a second snapshot, so approval comes first; a restart must use the new snapshot's position as its version; if approval is refused the rebuild stops and is re-planned, rather than 'restart from the beginning', which also needs a snapshot.
- Stated the consequences of the open check (a late write could resurrect a deleted product) and that it must be resolved before cutover.
- Mermaid diagram: moved products_v4 into the rebuild block, changed the rebuild start and backfill labels to match the snapshot-at-S wording, clarified the DUAL and rollback labels, and clarified the hard-delete label. The flow itself is unchanged.
- Turned the speed target into a measurable statement (95% searchable within 5 seconds of commit) and noted that batch size and wait time are the tuning knobs.
- Kept the required format: a Mermaid flowchart covering live sync and rebuild, with short notes before and after it.
- Opening: explained what the search index and alias are and listed the three problems of the cron job in plain terms, before describing the fix.
- Words section: added plain definitions for topic, partition, offset, consumer offset, stale write, and shadow-style dual writes; clarified that equal versions are accepted.
- Diagram: kept the same flow and labels, added the numbered start steps (record offsets, then read S), and labelled that the indexer writes to both indexes after the switch. Mermaid syntax unchanged in structure.
- Correction: the rebuild start now records the Kafka offsets before reading the WAL position S. The brief's order could miss a change that committed after S but reached Kafka before the offsets were recorded, because the snapshot cannot show it and the catch-up would start after it.
- Clarified that the backfill takes about 2.2 hours for about 40 million rows at 5,000 rows/s, with the brief's 2.5 hours as a safe upper bound.
- Live sync: explained that changes from one transaction share a commit_lsn and apply in read order because equal versions are accepted.
- Live sync: explained that after the switch an offset is committed only after both indexes acknowledge, and why rollback is lossless only because products_v3 receives every change.
- Open check: added that the deleted-document version check must also be repeated for products_v4 before the switch.
- Rebuild step 2: made the backfill math explicit and kept the version and resume rules unchanged.
- Rebuild failures: kept all failure cases; no change in meaning.

### Holes
- None.
