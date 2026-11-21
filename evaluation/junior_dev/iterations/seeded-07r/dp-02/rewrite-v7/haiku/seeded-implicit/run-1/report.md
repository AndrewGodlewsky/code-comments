## Review of dp-02 (rewrite-v7, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- No junior questions or answers were shown, so the rewrite is based on the brief and the first draft only. No question-driven changes were applied.
- Added the fixed requirements the first draft dropped: batches of up to 100 events, the 32 KB limit, 202 only after durable storage, per-event rejection listed in the response, no SDK retry of rejected events, the 1 s to 5 min backoff, the 7-day SDK buffer, first-copy-wins deduplication, 90-day keep-as-received for duplicates too, the 5-minute queryability target, the 14-day raw log, and the UTC day rule based on received_at.
- Added the replay rules the first draft dropped: closed days only (02:00 UTC the next day), no effect on live ingestion or live dedup state, and no half-rebuilt day visible to dashboards.
- Added a terms section defining SDK, collector, raw log, archive, lifecycle rule, reject bucket, KV TTL, partition, staging table, atomic replace and closed day.
- Split the flow into a live path and a replay path, each step saying what starts it, what it does, what keeps the data, and what happens on failure.
- Added a KV TTL of at least 7 days, derived from the 7-day retry window. The first draft had no TTL.
- Specified that replay decides first-copy-wins across the whole archive and never writes to the KV store. The first draft did not say how replay handles duplicates.
- Replaced the bare 'Bot filtering: TBD' line with an open question that states the decision is open and that the plan does not choose.
- Merged the monitoring line into the live path as step 5, and added a failure table so failure handling is not repeated across steps.
- Added open questions on the write order between the KV key and the warehouse load, the archiver outage limit of 14 days, the exact TTL value, and reject bucket retention. These are holes the brief leaves open.

### Holes
- None.
