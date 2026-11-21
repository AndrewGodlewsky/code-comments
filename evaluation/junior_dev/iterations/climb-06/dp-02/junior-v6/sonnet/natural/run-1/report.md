## Review of dp-02 (junior-v6, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Fixed rules: clarified the day of an event for a retry after midnight, added a fixed partition count rule, and defined the log, topic and in-sync replicas.
- Step 1.5-1.6: explained the all-in-sync-replicas acknowledgement and stated client retry behaviour on 5xx or 429.
- Step 3.4: added that a redelivered record always gets the same answer.
- Step 4.4-4.5: fixed non-deterministic batching. Batches are offset ranges recorded in a load ledger before loading and retried with the exact recorded range. Defined the ledger as a warehouse table owned by the processor, with the append and loaded status in one transaction.
- Step 5: defined who runs the closer job and what it checks (offset snapshot after 02:01, archiver and ledger caught up), and tied the 60 s staleness bound to it.
- Steps 5.4 and 9.3: stated that no live load can race with a replay swap.
- Step 8.5: stated that offsets are comparable across days because the partition count is fixed.
- Step 10.4: added a crash-recovery test.
- Step 13: added assumptions about clock synchronisation and web retry duration, and updated the warehouse transaction assumption.
- Step 2.2: archiver files now hold one partition and one hour; names use partition, hour and first/last offset; same record in two files is harmless (fixes the hour/offset-range mismatch).
- Step 8.5: replay treats records with the same (partition, offset) as one record.
- Steps 4.4 and 4.5: load ledger is now one row per (partition, offset range, day), each loaded in its own transaction; closed-day rows go to dead-letter with status dead-lettered; offset commits when all rows are loaded or dead-lettered.
- Step 5.1: closing check counts ledger rows loaded or dead-lettered.
- Fixed rules (dedup lookback): explained how the 8-day live TTL and the D-8..D replay scan line up and why they cannot disagree.
- Step 5.4: defined the dead-letter location, who reads it, and that replay recovers the event.
- Fixed rules and step 4.2, 7.1: defined enrichment_version and how live stamps it and replay chooses it; added assumption 13.8.
- Steps 9.1, 9.4, 9.6: defined what happens on validation failure (notify, lock released, staging kept, live untouched, run marked failed).
- Steps 1.3 and 1.7: stated that received_at is restamped on every retry and that a stale-append refusal is an ordinary retryable 5xx.
- Assumption 13.7: noted the 8-day lookback depends on web clients also stopping within about 7 days.
- Reordered into the required layout: summary paragraph, terms, fixed rules, steps, a failure table, rollout kept separate from how the system runs, open questions at the end.
- Added a Terms section defining log, topic, partition, offset, in-sync replicas, envelope, received_at, day of an event, duplicate/winner, enrichment, enrichment version, load ledger, closed day, replay, and the existing stores.
- Removed numbered cross-references (step 1.7, 3.4, 5.4, 9.2 and so on) and replaced them with named references so each step stands alone.
- Merged the repeated explanations of the 60 s rule, dead-letter handling and replay-versus-live agreement into single statements.
- Added a failure table covering collector, archiver, dedup, processor, load, closing and replay.
- Gave each live step an explicit trigger and data owner. Added the summary of how the system works today, namely that there is no pipeline yet.
- Moved safety checks and order of work into a separate build and rollout section.
- Kept every stated fact: 5 minute target, 100 event batches, 32 KB limit, 7-day buffer, 1 s to 5 min backoff, 90-day raw retention, 14-day log, 02:00 close, 8-day lookback, 82-day replay limit, alert thresholds (1 h, 6 h, 3 min), latency budget, and the bot decision left open.
- Added assumption 9 (on-call team is not stated). Moved the assumptions into a single end section, with the bot open decision.

### Holes
- Q14: What are the geo-IP database and user-agent parser here, and where does the live processor get their version? How does the live path know which enrichment_version to stamp, and what changes when an operator submits a new version for replay? (author: The brief names no geo-IP database or user-agent parser, only the lookups, so I cannot say which products they are or how their versions are deployed. Decided in the plan: enrichment_version is one string covering the code, geo-IP database version, parser version and bot classifier version; the live processor stamps the version it is deployed with. For replay the operator names a version and the replay job runs with that version's code and databases; to change what live does, deploy the new code. Added to the terms, steps 4.2 and 7.1, and assumption 13.8.)
