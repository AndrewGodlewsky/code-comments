## Review of dp-02 (junior-v7, author haiku, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the whole plan for a newcomer: summary, terms, numbered live path, numbered replay path, failure table and open questions, because the first version was too short for the questions to be answered from it.
- Removed the reject bucket. Rejected events are only listed in the 202 response, since the brief does not require a bucket.
- Partitioned the raw log by event_id so all copies of one event stay in order for dedup.
- Set the KV value to the first copy's log position and the TTL to 8 days, so reprocessing after a crash is safe.
- Made the live load delete and replace its own log range's rows, so a rerun does not double load.
- Made replay dedup with a 7-day lookback over the archive and stated that replay never writes to the KV store or offsets.
- Added replay preconditions: the day is closed, the live processor is past 02:00 UTC, and the archive files still exist.
- Added the 14-day log retention failure cases for the archiver and the live processor.
- Added the expired-KV-key and KV-store-down failure cases.
- Kept the bot-traffic decision open and added the unverified archive timing and dedup order questions to Open questions.
- Summary cut to three sentences. It now says what the system is, the main flow, and why it is shaped that way (the log is the shared durable buffer, the archive is the source for replay, and replay is separate so it cannot slow live work).
- Added a terms section with one plain line per name a newcomer would not know: event, batch, HTTP 202/429/5xx, received_at, UTC day, partition, replicated log (also called the raw log, per the junior's first question), log position, offset, consumer lag, archive, KV store and TTL, dedup, enrichment (geo-IP and user agent), staging table, and closed day.
- Merged the failure table into each step as an 'If it goes wrong' line, so each failure is stated once, in the step where it happens. Every row of the original table is kept.
- Removed the reject bucket from the first version, as decided in round 1. Rejected events are not stored and are listed in the reply, as the brief requires.
- Added one-clause reasons: why the KV write comes after the load, why the TTL is 8 days, why replay uses a 7-day lookback (it matches live dedup), why the closed-day check exists, why the collector writes duplicates, and why the partition swap is atomic.
- Moved the rule that replay never writes to the KV store or to any offset to the top of the replay path, and kept the rule that dashboards never see a half-built day.
- Kept every stated fact from the brief and the first version: 100-event batches, 32 KB limit, 1 s to 5 min backoff, 7-day on-device buffer, 14-day log retention, 90-day archive, 02:00 UTC close, 5-minute freshness alert, 8-day TTL, 7-day lookback, and the 14-day replay precondition. The 'events stay in order by event_id' partitioning and the 'Write only if the key is missing' rule are also kept.
- Removed repeated statements, such as the same duplicate-keeping rule written in the collector, archiver and live processor steps, and the separate summary-and-steps repetition of the replay rules.
- Kept the five open questions unchanged and did not choose on bot traffic.
- Added a separate note that replay runs on its own compute, placed in the replay step where it applies, rather than in a separate section.
- No new mechanism was added. No lock, lease, retry queue or takeover rule was introduced, and the plan's behaviour is unchanged.

### Holes
- None.
