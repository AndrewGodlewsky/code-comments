## Review of dp-02 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary and a terms section. The original used none, and terms such as received_at, archive and first copy needed defining for a newcomer.
- Added the rule that the UTC day of received_at decides the partition and which replay covers an event. The brief fixes this rule and the original left it out.
- Added the first-copy dedup rule and a 7-day KV TTL, because clients can retry up to 7 days after the first copy.
- Added a 7-day lookback to the replay's dedup check. Without it, a replay could keep a copy that live processing dropped.
- Changed archive retention from 90 days to 97 days, so the 7-day lookback still has data for a day that is 90 days old. The 90-day rule is treated as a minimum. Listed as an open question for confirmation.
- Changed the live processor order to load before writing the KV key, so a crash duplicates an event rather than losing it. Replay repairs such a day.
- Added log partitioning by event_id, so all copies of one event are handled in order by one processor.
- Expanded the original one-line replay into four steps: closed-day check, archive-only read, staging table, and atomic partition swap. The replay does not read the raw log or write to the KV store.
- Added a failure table. The choice that the live processor pauses when the KV store is down is my decision, not from the brief.
- Cut the original standalone monitoring step and folded it into the failure table as lag alerts. The brief gives no thresholds, so they stay open.
- Moved bot filtering out of a bare TBD line into the open questions. It remains undecided, as the brief requires.
- Added the 5-minute live target and the 14-day raw log limit, both from the brief.
- The document is longer than the 1.5x guideline from the earlier loop. The original omitted the replay and failure rules the brief requires, so the added length was needed. Nothing was cut from the brief's requirements.

### Holes
- None.
