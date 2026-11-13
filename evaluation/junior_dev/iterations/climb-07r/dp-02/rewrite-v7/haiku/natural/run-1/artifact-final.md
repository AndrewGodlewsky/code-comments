# Clickstream ingestion: plan

## Summary

Click and screen-view events from the website and the iOS and Android apps are sent in batches to a new collector service. The collector stores each accepted event in a replicated log and also archives a raw copy of it. A live consumer keeps only the first copy of each event, enriches it, and writes it to the open day's partition of `events_clean` within minutes. A replay rebuilds one closed day from the archive only, builds it in a staging table, checks it, and swaps it in with one atomic step. The archive is kept for 90 days, so any closed day can be rebuilt after an enrichment fix without touching live ingestion.

## Terms

- **Event:** one click or screen view. It has a client-made `event_id` (a UUID), a `device_id`, and a client timestamp.
- **Batch:** up to 100 events sent in one HTTPS request.
- **Collector:** the new HTTPS service that receives batches.
- **received_at:** the collector's server time (UTC) when it accepts an event. It decides the event's UTC day.
- **UTC day:** a calendar day in UTC. Day N is the 24 hours of date N in UTC.
- **Partition:** one day's slice of a table. `events_clean` has one partition per UTC day.
- **Replicated log:** an append-only queue that copies each record to several machines and keeps records for 14 days. Each record has a partition number and an offset, which together are its position. Records with the same key stay in order inside one partition.
- **Consumer group:** a named reader of the log that keeps its own read position.
- **Archive:** files in object storage that hold every accepted event exactly as received. Lifecycle rules delete files by their creation time.
- **KV store:** a key-value store where each key can expire after a set time (its TTL). SETNX means "set if not exists": it writes only when the key is empty and reports whether it wrote.
- **Duplicate:** a later copy of an event whose `event_id` has already been claimed.
- **Winner:** the copy of an event that claims its `event_id` first. "First" means the lowest (log partition, log offset).
- **Enrichment:** adding a geo-IP location and parsed user-agent fields (browser and OS) to an event. `enrichment_version` names the exact code and data versions used.
- **Micro-batch:** a group of winners that the live writer sends together.
- **Seal:** the point at which a closed day is declared final and live writes to it stop.
- **Staging table:** a table with the same layout as `events_clean` that dashboards cannot read. A replay builds a day there before it goes live.
- **Atomic swap:** replacing a whole day partition in one step, so readers see the old day or the new day, never a mix.
- **Watermark:** a marker the archiver publishes that says all files up to a point are written.
- **Run record:** a row describing one replay: run ID, day, enrichment version, operator, start time and status.

## Assumptions to confirm

1. A log acknowledgement means the record is stored on enough replicas to survive the loss of a broker. An ack counts as "durably stored".
2. The log is keyed by `device_id`, so every copy of one `event_id` lands in the same log partition, in the order it was appended. "First" is the lowest (log partition, log offset).
3. The KV store supports SETNX with a per-key TTL, and reads return the stored value.
4. The warehouse can atomically replace one day partition of a table from a staging table. Dashboards see either the old or the new partition.
5. Object storage supports listing by prefix and lifecycle rules based on creation time.

## Rules that apply everywhere

- An event belongs to the UTC day of its `received_at`, never its client timestamp. That day decides its partition and which replay covers it.
- Deduplication uses `event_id` alone. The first copy wins.
- Every accepted event is kept exactly as received for 90 days. This includes duplicates.
- An accepted event is queryable within 5 minutes of reaching the collector.
- Only closed days can be replayed. Day N closes at 02:00 UTC on N+1.
- A replay must not slow live ingestion or change live dedup state. Dashboards must never see a half-rebuilt day.

## How the live path runs

1. **The collector receives a batch.** A client's HTTPS request starts this step. The collector parses the JSON body. It rejects the whole request with 400 if the body is not valid JSON or holds more than 100 events. It keeps the original bytes of each event, so the archive can store the event exactly as received.

2. **Each event is validated alone.** An event is malformed if it lacks `event_id` or `device_id`, or if its serialized size is over 32 KB. Proposed, to confirm: also reject an `event_id` that is not a UUID. Malformed events are dropped from the batch and listed in the response. The other events in the batch continue.

3. **The collector stamps received_at.** It sets `received_at` to its UTC server time, once per accepted event, at the moment of acceptance. The client timestamp stays as a plain field. Nothing uses it for partitioning or replay.

4. **Accepted events are appended to the log.** The collector appends the batch in one write, keyed by `device_id`. It does not deduplicate here, because every copy must be kept. If the append succeeds but the reply times out, the client's retry adds a second copy. Step 7 handles that.

5. **The collector responds.** It returns 202 only after the log acknowledges the append. The body lists `accepted` (a count) and `rejected`. Each rejected item gives its index, its `event_id` if it has one, and a reason: `missing_event_id`, `missing_device_id` or `oversize`. Clients never retry rejected events. Proposed, to confirm: a batch where every event is malformed still returns 202 with all events listed, so clients stop retrying. If the append fails or times out, the collector returns 503 with no acknowledgement. The client then resends the same `event_id`s, and dedup absorbs any copy that did land.

6. **The archiver writes raw copies.** The archiver is a consumer group of its own, separate from the live consumer. For each log record it writes one object under `raw/dt=YYYY-MM-DD/`. The date is the UTC day of `received_at`. The object holds the log partition, log offset, `received_at` and the original bytes. Each object is written once and never rewritten. The archiver publishes a watermark once everything up to a point is written. The archive is the replay source of truth. The log keeps only 14 days, which is too short for the 90-day retention and the 8-day replay lookback. If the archive falls behind, see the alert in step 12.

7. **Live dedup and enrichment.** A live consumer, in its own consumer group, reads the log in order. For each event:
   - It calls SETNX on `event_id`, with the value set to the event's (partition, offset) and a TTL of 8 days. The value is set once and never refreshed. The 8 days cover the 7-day retry window plus a 1-day margin.
   - If SETNX succeeds, or the stored value equals this event's own position (a redo after a crash), the event is a winner. The consumer enriches it with geo-IP and user-agent parsing, records `enrichment_version`, and passes it to the writer.
   - Otherwise the event is a duplicate. It is counted as dropped and not written to `events_clean`. Its raw copy stays in the archive.

8. **The live writer stores winners.** Every 60 to 90 seconds the writer collects winners into a micro-batch. It appends each winner to the partition for its `received_at` day. Each row carries `log_partition` and `log_offset`. Writes are idempotent on (`log_partition`, `log_offset`), so a redo after a crash cannot insert a row twice. Rows from a redo are not lost either, because the KV claim was made against the same log position.

9. **Latency budget.** The target is a p95 end-to-end lag under 3 minutes, with an alert at 4 minutes. The parts are: collector ack well under 1 second; log to consumer, seconds; enrichment and KV, seconds; micro-batch wait, up to 90 seconds; warehouse load and visibility, 30 to 60 seconds. End-to-end lag is `now` minus the newest `received_at` visible in `events_clean`.

10. **A closed day is sealed.** Day N is sealed only when all four of these hold, and never before 02:00 UTC on N+1. The wait until 02:00 is the grace window for in-flight and late writes.
    - Collectors have stopped stamping day N, and in-flight writes have drained.
    - The live consumer has processed every log record appended before 02:00 UTC.
    - The archiver has finished `raw/dt=N/` and reports a complete watermark.
    - The live writer has committed its last micro-batch for day N.

11. **A late record is archived and alerted.** A record with a `received_at` on a sealed day may reach the archive after the seal. The archiver stores it as usual and raises an alert. The live path does not write it into the sealed partition. A later replay of that day picks it up from the archive, so the archive stays the one complete copy.

12. **Guardrails.** Raise an alert when:
    - archive lag exceeds 12 hours (proposed threshold). The log keeps only 14 days, so archive failure beyond that means permanent loss;
    - KV TTL writes fail, or the SETNX error rate rises;
    - end-to-end lag exceeds 4 minutes.

    Track these counts per day: accepted, rejected (by reason), duplicates dropped and winners written. They are the baseline that replay validation checks against.

## How the replay path runs (one closed UTC day N)

An operator starts a replay by submitting "replay day N". The steps are:

13. **Gate.** Reject the request unless all of these hold:
    - It is at or after 02:00 UTC on N+1, and day N is sealed.
    - The archive is complete for `raw/dt=N-8` through `raw/dt=N`.
    - No other replay of day N is running. At most one replay per day runs at a time.
    - The number of concurrent replays across all days is capped. The cap value is not yet set.

14. **Create a run record.** Record the run ID, day N, the requested enrichment version, the operator and the start time. The record lives outside `events_clean`.

15. **Read only from the archive.** Read `raw/dt=N-8` through `raw/dt=N`. Do not read the log and do not call the KV store. A replay must not change live dedup state or add load to ingestion.

16. **Recompute winners.** Group all copies by `event_id`. The winner is the copy with the lowest (`log_partition`, `log_offset`), the same rule as live. Keep a winner only if its `received_at` falls on day N. The 7-day retry bound means the earliest copy of a day-N winner is no earlier than day N-7. The 8-day lookback therefore covers it.

17. **Enrich with the new version.** Apply the fixed geo-IP and user-agent code and data. Pin the exact database and parser versions. Write `enrichment_version` into every row. Do not change the winner set in this step.

18. **Write to staging.** Write the rebuilt rows to a staging table with the same schema as `events_clean`. Dashboards cannot read this table. Include the run ID.

19. **Validate before anything visible changes.** All of these checks must pass:
    - The row count equals the number of recomputed winners. Each `event_id` appears exactly once. Every `received_at` falls on day N.
    - The set of `event_id`s equals the set in the live partition N. The only exception is when a bot-traffic policy was applied (see open questions). Any other difference means dedup or archive coverage is wrong, so stop.
    - The daily accepted, rejected and dropped counts match the live baseline from step 12.
    - Only enrichment columns differ, and sample rows show the expected fixes.

    If any check fails, drop the staging table, mark the run failed and leave the live partition alone.

20. **Atomic swap.** Replace partition N of `events_clean` from the staging table in one warehouse operation. Dashboards see the old partition before the swap and the new one after it, never a mix. Mark the run complete.

21. **Clean up and keep a way back.** Drop staging once the swap is verified. If the warehouse supports partition snapshots or time travel, keep the pre-swap snapshot until the replay is signed off. If it does not, a rollback means running the replay again with the previous enrichment version. That is always possible inside the 90-day raw window.

22. **Confirm live state is untouched.** Before and after the replay, compare the KV key count and a sample of KV values. Check that the live consumer's offsets did not move. Keep this check in the run record.

## Changing enrichment for an open day

- Deploying an enrichment fix changes the output for new events right away. Earlier events from the same day keep the old enrichment until the day is closed and replayed. Dashboards can therefore show mixed `enrichment_version` values for the open day. This is expected.
- Do not replay an open day. Wait until it closes.

## What happens when things fail

| Where | What happens |
|---|---|
| Body is not valid JSON, or has more than 100 events | Collector returns 400 and rejects the whole request. Response code still open. |
| One event is malformed | It is listed in the response. The other events are accepted. |
| Every event in a batch is malformed | Proposed: 202 with every event listed. Clients do not retry. |
| Log append fails or times out | Collector returns 503 with no acknowledgement. Client resends the same `event_id`s. Dedup absorbs any copy that landed. |
| Crash after append, before the response | The client retries. Dedup absorbs the extra copy. |
| Crash between SETNX and the warehouse write | The redo finds its own position in the KV store and is a winner again. The idempotent write leaves exactly one row. |
| Archive falls behind | Alert at 12 hours of lag. Beyond 14 days, the log has dropped the data and it is lost. |
| KV TTL writes fail, or SETNX errors rise | Alert. |
| End-to-end lag exceeds 4 minutes | Alert. |
| Late record after the seal | Archived and alerted. Not written to the sealed partition. Picked up by a later replay. |
| Replay gate fails | Request is rejected. |
| Replay validation fails | Staging is dropped, the run is marked failed, and the live partition is untouched. |
| Swap | Atomic. Dashboards keep seeing the old partition until the swap completes. |

## Open questions

- **Suspected bot traffic: drop it, or keep it with a flag.** This plan does not choose. Both options fit the design.
  - Option A, flag: enrichment adds a `bot_suspected` column, and dashboards filter on it. The event set is unchanged, so step 19 is unchanged.
  - Option B, drop: a filter runs in step 7 or step 17. Step 19 must compare against the post-filter set.
  - Either way, the decision must be recorded in `enrichment_version`, so a replay can reproduce it. The archive keeps every event for 90 days. A drop can be reversed by replay inside that window, but not after it.
- **Storing rejected event bodies.** The brief does not require it. Options: store metadata only, or store bodies for 90 days.
- **Response codes.** Proposed: 400 for a bad body or more than 100 events, and 202 for an all-malformed batch (step 5).
- **Dedup TTL and archive lag threshold.** Proposed: 8 days and 12 hours.
- **Partition snapshots.** Does the warehouse support them? The answer decides how step 21 rolls back.
- **UUID check.** Is rejecting a non-UUID `event_id` required? Proposed in step 2.
- **Concurrent replay cap.** The value is not set.
- **SETNX errors.** When SETNX fails, the brief does not say whether the consumer retries the event or stops. This needs an answer before build.
- **Copies after the KV entry expires.** A copy that arrives after its key has expired would be treated as a new winner, and written to a later day's partition. The plan assumes the 7-day retry bound holds. This needs a decision before build.

## Build and rollout: verification

1. A duplicate arriving 7 days after the first copy is dropped. A duplicate arriving 8 days after is dropped only if the TTL still covers it. Test the boundary against the chosen TTL.
2. An event with a client timestamp on day N+1 and a `received_at` on day N lands in partition N.
3. A batch with one malformed event returns 202, lists that event and writes the others.
4. A crash between SETNX and the warehouse write, followed by a redo, produces exactly one row.
5. A replay of an open day is refused. A replay of a closed day leaves the KV store and the consumer offsets unchanged.
6. A dashboard query running during the swap sees only complete old data or complete new data.
7. Replay validation fails when one `event_id` is removed from staging, and the live partition is unchanged.
8. Live end-to-end lag stays under 4 minutes while a replay runs at the full configured rate.