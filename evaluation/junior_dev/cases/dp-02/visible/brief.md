## Clickstream ingestion: plan request

We need a pipeline that takes click and screen-view events from our website and our iOS and Android apps and lands them, deduplicated and enriched, in a warehouse table `events_clean` with one partition per UTC day. Live events must be queryable within 5 minutes of reaching us.

### Fixed requirements

- Every event carries a client-generated `event_id` (UUID), a `device_id` and a client timestamp. Clients send batches of up to 100 events over HTTPS to a new collector service.
- The collector stamps each event with `received_at` (server time). An event belongs to the UTC day of `received_at`, never of the client timestamp. That day decides its partition and which replay covers it.
- The collector may return 202 only once the batch is durably stored. Malformed events (missing `event_id` or `device_id`, or over 32 KB) are rejected one at a time and listed in the response. The rest of the batch is still accepted. Clients never retry rejected events.
- On a timeout, 429 or 5xx, clients resend the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can reach us up to 7 days after the first copy.
- Duplicates are identified by `event_id` alone. The first copy we receive wins and later copies are dropped.
- Every accepted event, duplicates included, must be kept exactly as received for 90 days.
- Replay: an operator must be able to rebuild one UTC day, usually after we fix an enrichment bug (geo-IP lookup, user-agent parsing). Only closed days can be replayed. A day closes at 02:00 UTC the following day. A replay must not slow live ingestion or change live deduplication state, and dashboards must never see a half-rebuilt day.

### Existing infrastructure you can use

A replicated append-only log (Kafka-style, 14-day retention), object storage with lifecycle rules, a key-value store with per-key TTL, and the warehouse, which can atomically replace a single day partition of a table.

### Not decided

Product has not decided yet whether suspected bot traffic should be dropped or kept with a flag. Do not choose for them. Show it as open in the plan.

### Format

Write it as a numbered, step-by-step plan in Markdown, covering both the live path and replay.
