# Clickstream ingestion: plan for `events_clean`

## Goal and key decisions

- Events from web, iOS and Android land in `events_clean`, deduplicated and enriched, partitioned by the UTC day of `received_at`. Live events are queryable within 5 minutes of reaching the collector.
- Deduplication uses `event_id` alone. The first copy processed wins. Later copies are kept in the raw archive but never reach `events_clean`.
- Every accepted event, duplicates included, is kept exactly as received for 90 days in object storage. This raw archive is the source for replay, so replay does not depend on the 14-day Kafka retention.
- Replay rebuilds one closed UTC day and replaces that day's partition atomically. It reads only from object storage and never writes to dedup state.
- Bot traffic handling is **open** (see Open decisions). The plan keeps a hook for it and does not choose.

## Live path

1. **Client send and retry.** Clients send batches of up to 100 events over HTTPS. On timeout, 429 or 5xx, they resend the same batch with the same `event_id`s, backing off from 1 s to a 5-minute cap. Retries can arrive up to 7 days after the first copy, so the server must handle duplicates at every stage.

2. **Collector validation and durable write.** For each batch:
   1. Stamp `received_at` with server UTC time when the request arrives.
   2. Validate each event. Reject one at a time if `event_id` or `device_id` is missing or the event is over 32 KB. Do not reject the batch.
   3. Append the accepted events to the replicated log in one durable write. Partition the log by `hash(event_id)` so every copy of an event goes to the same partition, which gives a single ordering point for dedup.
   4. Return 202 only after the log write is acknowledged. The body lists rejected events by index and `event_id`, and the client does not retry them.
   5. Return 429 or 5xx on failure, so the client retries the whole batch.
   Because the log write can succeed while the response is lost, a retry can create a second copy with a new `received_at`. Step 4 handles that.

3. **Raw archive sink.** A sink consumer copies each accepted event, as received plus the collector envelope (`received_at`, batch id), into object storage under `raw/received_day=YYYY-MM-DD/`. Files are gzip-compressed and are never rewritten. Lifecycle rule: expire objects 90 days after creation. This sink is the durable record that replay uses.

4. **Deduplication.** A dedup consumer processes each log partition in order:
   1. For each event, run an atomic `SET event_id NX` with TTL 9 days in the key-value store. TTL must exceed the 7-day retry window plus log and processing lag. Alert when observed lag approaches that margin.
   2. If the set succeeds, the event is the winner. Mark it `winner` and pass it on.
   3. If the key already exists, mark it `duplicate` and drop it from the clean path. The raw archive still holds it.
   4. Write one decision row per event (`event_id`, `received_day`, `decision`) to a **decision manifest** in object storage under `manifest/received_day=YYYY-MM-DD/`. Replay reads these manifests. Replay never writes to the key-value store.

5. **Enrichment.** For winners only, apply geo-IP lookup and user-agent parsing. Stamp each row with `enrichment_version`, `geoip_db_version` and `ua_parser_version`. Insert a placeholder stage where the bot-traffic decision will apply (see Open decisions).

6. **Clean write.** Write enriched winners to `events_clean` in micro-batches, at most one minute apart, into the partition for the event's `received_at` day. For the open day, the write is an append. Closed days are changed only by the seal (step 7) and by replay.

7. **Freshness and day close.** Track freshness as the time from `received_at` to the row being queryable. Alert at 4 minutes against the 5-minute target.
   - Day D closes at 02:00 UTC on D+1. Close requires that every log record with `received_at` before that time is consumed, archived and written to the manifest. Check this with the sink and dedup consumer offsets, and with the collector's confirmation that no write stamped before close is still in flight.
   - At close, run a **seal** for day D. It rebuilds D from its raw archive and manifest, using the replay procedure below, and atomically replaces partition D. This makes the day's final contents deterministic and equal to a replay.
   - Any event stamped with a day-D `received_at` that is archived after seal is handled as a late event. It triggers a replay of D, because D is then closed and replay is allowed.

## Replay path

8. **Eligibility.** An operator requests a replay of UTC day D. Refuse unless the current time is at or after 02:00 UTC on D+1, and the day is sealed or the seal's completeness check has passed. Record the request (who, day, reason, target enrichment version).

9. **Build into staging.** A replay job runs on separate compute with its own quota.
   1. Read raw objects for `received_day=D` from object storage. Do not read the live Kafka topic.
   2. Read the manifest for D and keep only events marked `winner`. This keeps the live dedup decisions and does not re-decide them, so duplicates stay out and winners stay the same.
   3. Re-run enrichment with the target versions.
   4. Write the result to a staging table or staging partition that dashboards do not read.

10. **Verify before publishing.** Check that the staging row count equals the manifest's winner count for D. Check that `event_id` is unique in staging. Check that every row has the expected enrichment versions. Record counts and checksums in the replay ledger. Fail the replay and leave `events_clean` unchanged if any check fails.

11. **Atomic swap.** Use the warehouse's atomic replace of a single day partition to replace `events_clean` partition D with the staging contents. Readers see either the old or the new day, never a partial rebuild. Drop the staging data after the swap.

12. **Isolation and idempotence.**
    - The replay job uses object storage and the warehouse only. It does not touch the collector, the log consumers, the key-value store or live partitions other than D.
    - Rate-limit replay reads and writes, and run them in a separate warehouse pool, so live freshness is not affected.
    - The replay is idempotent. Running it twice for the same day and versions produces the same partition.
    - Log the replay in the ledger: day, requester, versions before and after, row counts, checksums, and start and end times.

## Retention

- Raw archive: 90 days from object creation, by lifecycle rule. Manifests use the same rule, so replay can still reach any day held in the raw archive.
- `events_clean`: retention is not specified in the brief. Keep it as an open item.
- Key-value dedup state: 9-day TTL. This is not a retention requirement and does not hold history.
- Kafka: 14 days. Used only as the transport buffer and for recovery of the sink and dedup consumers.

## Open decisions

- **Bot traffic (not decided by product).** Options are to drop suspected bot events or keep them with a flag column. The plan does not choose. Both options fit the design:
  - Either way, raw archiving keeps every accepted event for 90 days, as required.
  - Dropping would happen at enrichment (step 5) and would be recorded in the manifest or a separate decision log so replay stays deterministic.
  - Keeping would add a flag to the clean schema.
  - Product should decide before the enrichment stage is built.
- **Close-time guarantee.** The plan assumes a 2-hour gap between the 02:00 close and in-flight collector writes. Confirm the collector's maximum write latency, and define the late-event policy (replay the day, or accept and report).
- **"First copy" definition.** The plan defines it as first in log order within the `event_id` partition, not by `received_at`, because `received_at` is stamped by several collector instances. Confirm the ordering guarantee with the log vendor.
- **Dedup TTL sizing.** The 9-day TTL assumes the 7-day retry window is measured from the first copy's receipt. If the mobile SDK measures it from event creation, the window may be longer. Confirm with the mobile team.
- **Warehouse semantics.** Confirm that the warehouse can atomically replace a day partition while live appends to the open day continue, and that seal and replay use the same partition-replace operation.

## Assumptions to verify

- The key-value store supports atomic set-if-absent with per-key TTL at the required scale.
- The warehouse can load micro-batches with enough throughput to meet the 5-minute freshness target.
- Object storage lifecycle rules act on object creation time with enough precision for a 90-day guarantee.
- The collector's durable write is a replicated log acknowledgement, not an in-memory buffer.