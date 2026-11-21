## Review of dp-02 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short goal and glossary (raw log, archive, KV store, event day) so a reader new to the stack can follow it.
- Split the plan into Live path, Replay, Monitoring and Open decision sections with continuous numbering.
- Stated that the event day comes from received_at and not the client timestamp, and that it decides the partition.
- Spelled out collector behavior: per-event rejection, 202 only after a durable write, and no dedup at the collector.
- Clarified client retry rules, including the 7-day on-device buffer.
- Made dedup explicit: atomic set-if-absent in the KV store, 8-day TTL, and a crash-safe rule for re-read positions.
- Explained the archive as the long-term record behind the 14-day log, with an archiver-lag alert.
- Expanded replay into numbered steps covering eligibility, reading from the archive, dedup in the job against the prior 7 days, a staging table, and an atomic swap, and tied each to a requirement (no live slowdown, no change to live dedup state, no half-rebuilt day).
- Flagged the assumption that the warehouse can append to a partition, and the roughly 83-day replay limit.
- Dropped the reject bucket, because the brief only requires listing rejects in the response.
- Rewrote the bot-filtering item as an open decision that says what it affects and where it would plug in, without choosing.
- Added 'First copy' to the terms and defined TTL and lifecycle rule for readers new to the stack.
- Reworded the crash-safety bullet to explain the mechanism and the failure it prevents.
- Explained why a day closes at 02:00 UTC next day (late processing of events near midnight).
- Clarified why replay needs the 7 prior days in the archive, and why that gives the 83-day limit.
- Made the swap step state what happens when a staging check fails and what is replaced with what.
- Fixed the ambiguous open-decision step references: now says right after dedup in step 4 and in step 7, and that replay can apply the decision to past days.
- Minor wording tightening (e.g. 'raw log position' instead of 'log position', 'between tries' for backoff).
- Added a short 'How it fits together' overview so a newcomer sees the whole flow before the steps.
- Added definitions for Enrich and Staging table, and a note in First copy that client retries cause duplicates.
- Restructured step 4 into numbered sub-steps (dedup, enrich, load) with the KV TTL and crash-safety notes under dedup.
- Step 3 now says the 90-day lifecycle rule meets the retention requirement.
- Step 5 now also requires the archiver to have written all of day D, since replay reads only from the archive.
- Moved the staging table definition out of step 8 into the terms list and shortened step 8.
- Smoothed wording in the open decision section.

### Holes
- None.
