# Clickstream ingestion plan

Website, iOS and Android apps send click and screen-view events to a collector. The collector stores each accepted event in a replicated log before it replies. Two readers consume that log: an archiver keeps every accepted copy for 90 days, and a live processor drops duplicates, enriches events and loads them into `events_clean` within 5 minutes. A replay rebuilds one closed day from the archive, so an enrichment fix can be applied without touching live deduplication or live rows.

An event belongs to the UTC day it was received. A late retry therefore lands in today's partition, and past partitions change only through replay.

## Terms

- **Event**: one click or screen view. It carries a client-made `event_id` (a random UUID, unique per event), a `device_id` and a client timestamp (the time the device says it happened).
- **Batch**: up to 100 events sent together in one HTTPS request.
- **HTTP replies**: 202 means "accepted and stored". 429 means "too busy, try again later". 5xx means "server error, try again".
- **received_at**: the server time the collector stamps on each accepted event.
- **UTC day**: a calendar day in UTC. An event's day is the day of its `received_at`, never of its client timestamp.
- **Partition**: one day's share of `events_clean`. The warehouse can replace one partition in one atomic step, so readers see either the old rows or the new rows.
- **Replicated log** (also called the raw log): an ordered, append-only record store, copied across machines and kept for 14 days. Entries are never changed.
- **Log position**: where an entry sits in the log.
- **Offset**: a reader's own position in the log. Each reader keeps its own and moves it forward only after its work is saved.
- **Consumer lag**: how far a reader's offset is behind the newest log entry, measured in time.
- **Archive**: object storage holding accepted events as files. A lifecycle rule deletes each file 90 days after it is written.
- **KV store**: a key-value store where each key expires after its TTL (time to live).
- **Dedup**: keeping the first copy of an `event_id` and dropping later copies.
- **Enrichment**: adding a country and city found from the client IP address (geo-IP lookup), and browser and OS fields parsed from the user-agent string.
- **Staging table**: a temporary copy of one day, built by replay before it replaces the live partition.
- **Closed day**: a UTC day that is over. A day closes at 02:00 UTC the following day.

## Live path

1. **SDK sends a batch.** It starts when an app or the website has events to send. The web, iOS and Android SDKs (the client code inside each app) group up to 100 events and send them to the collector over HTTPS. Each event keeps its `event_id`, `device_id` and client timestamp.
   - On a timeout, 429 or 5xx, the SDK resends the same batch with the same `event_id`s. It waits 1 s before the first retry, doubles the wait each time, and stops growing the wait at 5 minutes.
   - The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can arrive up to 7 days after the first copy.
   - The SDK never resends an event that was rejected.

2. **Collector validates and stores.** It starts when a batch arrives. It rejects any event that has no `event_id` or `device_id`, or that is over 32 KB. Rejected events are not stored. They are listed one by one, with a reason, in the reply. The collector stamps every other event with `received_at` and writes it to the replicated log, partitioned by `event_id` so all copies of one event stay in order. It does not dedup, so duplicates are written too, and the archive keeps every copy. It replies 202 only after the log confirms the batch is replicated. The rest of the batch is accepted even when some events are rejected.
   - If the log write fails, the collector replies 429 or 5xx, and the SDK resends the batch. Some copies from the failed attempt may already be in the log. Dedup removes them later.

3. **Archiver keeps every copy.** It starts on its own and reads the log from its own offset. It writes each accepted event, exactly as received and with its `received_at`, into hourly files in object storage. Duplicates are kept. Each file is deleted 90 days after it is written. The archiver moves its offset forward only after the file is written.
   - If a write fails, it retries without moving its offset. The log keeps entries for 14 days, so the archiver can catch up.
   - If it falls more than 14 days behind, unread entries are gone from the log.

4. **Live processor loads `events_clean`.** It starts on its own and reads the log from its own offset, in small batches. For each record, in log order:
   1. Look up the `event_id` in the KV store. Dedup uses `event_id` alone. If the key holds a different log position, the record is a duplicate and is dropped. If the key is missing, or holds this record's log position, the record is a first copy. A later copy of an event already seen earlier in the same batch is also dropped.
   2. Enrich each first copy with geo-IP location and parsed user-agent fields.
   3. Delete any rows already written for this log range, across every day partition it touches. Then insert the new rows into the partition of each row's `received_at` day. A rerun replaces rows instead of adding them.
   4. Write each first copy's `event_id` to the KV store, with its log position as the value and a TTL of 8 days. The 8 days cover the 7-day retry window plus one day of margin. Write only if the key is missing.
   5. Move the offset forward.
   - The KV write comes after the load, so a crash cannot lose or double a row. If the processor crashes before the KV write, the rerun still treats the record as a first copy. If it crashes after the KV write, the stored position matches this record, so the rerun also treats it as a first copy.
   - If the processor crashes, it restarts from its last committed offset. Its reruns replace their own rows and are not treated as duplicates.
   - If enrichment fails, the batch is not committed and is retried, so nothing is dropped.
   - If the KV store is unavailable, the processor stops without committing, and events wait in the log.
   - If a key has expired (more than 8 days after the first copy), a copy arriving after expiry is loaded as a first copy. The 7-day retry window should prevent this.
   - If the processor falls more than 14 days behind, unread log entries are deleted. The archive still holds them, so replay the affected days.

5. **Monitoring.** Track consumer lag for the archiver and the live processor. Alert when the live processor is more than 5 minutes behind, which is the freshness target for live events.

## Replay path

Replay rebuilds one closed UTC day after an enrichment fix, for example a geo-IP or user-agent bug. It never writes to the KV store or to any reader's offset, so live deduplication state and live ingestion are unchanged. Dashboards see either the old day or the new day, never a half-built one.

1. **Operator starts a replay** for one closed day, by hand. Nothing starts it automatically.
2. **Job checks the preconditions** before it writes anything. It stops if any check fails.
   - The day is closed: it is at least 02:00 UTC on the following day. This is required because no new event can belong to a closed day, since `received_at` is server time.
   - The live processor's offset is past 02:00 UTC on the following day, so no live row for that day can still be written.
   - The archive files for the day and the 7 days before it still exist. The 90-day lifecycle may already have deleted older files.
   - If a check fails, the job stops, and the live partition is unchanged.
3. **Job rebuilds the day from the archive.** It reads the archive for the day and the 7 days before it. It keeps the first copy of each `event_id`, by `received_at`, and drops later copies. The 7-day lookback matches live dedup, which also drops copies of events first seen earlier. It keeps only first copies whose `received_at` falls in the day. It enriches them with the current enrichment code and writes the result to a staging table for that day. It runs on its own compute, so live ingestion is not slowed.
   - If the job fails before the swap, the live partition is unchanged. Rerun the job.
4. **Job swaps the partition.** It replaces the day's partition in `events_clean` with the staging partition in one atomic step. If the swap fails, the swap does not happen and the old partition stays in place. After a successful swap, the job drops the staging table.

## Open questions

- **Bot traffic.** Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose.
- **Archive timing.** Does the archiver finish a day's hourly files before 02:00 UTC? Replay depends on it. This is not verified.
- **Dedup order.** Live dedup uses log order and replay uses `received_at`. They should agree, but this is not verified.
- **Rejects.** Does anyone review rejected events? Not decided.
- **Archiver alert.** No lag threshold is set for the archiver.