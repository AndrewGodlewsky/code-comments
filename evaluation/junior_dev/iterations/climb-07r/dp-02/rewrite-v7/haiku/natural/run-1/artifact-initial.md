# Clickstream ingestion: plan

## Scope and fixed rules

- Sources: website, iOS and Android clients send batches of up to 100 events over HTTPS to a new collector service.
- Target: warehouse table `events_clean`, one partition per UTC day, where the day is the UTC date of `received_at` (collector time), never the client timestamp.
- Live SLA: an accepted event is queryable within 5 minutes of reaching the collector.
- Replay: an operator rebuilds one closed UTC day. A day N closes at 02:00 UTC on N+1.
- Dedup: by `event_id` alone. The first copy wins. Retries can arrive up to 7 days after the first copy.
- Retention: every accepted event, duplicates included, is kept exactly as received for 90 days.

## Assumptions to confirm

1. The replicated log acknowledges a write only after it is stored on enough replicas to survive a broker loss. A log ack is treated as "durably stored".
2. The log is keyed by `device_id`, so all copies of one `event_id` land in the same log partition in the order they were appended. "First" is defined as the lowest `(log_partition, log_offset)`.
3. The key-value store supports atomic set-if-absent (SETNX) with a per-key TTL, and reads return the stored value.
4. The warehouse can atomically replace one day partition of a table from a staging table, and dashboards see either the old or the new partition.
5. Object storage supports prefix listing and lifecycle rules based on object creation time.

## Live path

1. **Collector receives a batch.** Parse the JSON body. Reject the whole request with 400 if it is not valid JSON or has more than 100 events. Keep the original bytes of each event so it can be archived exactly as received.

2. **Validate each event on its own.** An event is malformed if it lacks `event_id` or `device_id`, or if its serialized size exceeds 32 KB. Recommended, to confirm: also reject an `event_id` that is not a UUID. Malformed events are dropped from this batch and listed in the response. Valid events in the same batch continue.

3. **Stamp `received_at`.** Set it to collector server time (UTC) once per accepted event at the moment of acceptance. Keep the client timestamp as a plain field. Do not use it for partitioning or replay selection.

4. **Append accepted events to the replicated log.** Use `device_id` as the key. Do not deduplicate here, because every copy must be kept. The batch write is one append, so a timeout after a successful append is possible and is handled by dedup.

5. **Return the response.** Return 202 only after the log acknowledges the append. The body lists `accepted` (count) and `rejected` (for each: index, `event_id` if present, reason such as `missing_event_id`, `missing_device_id`, or `oversize`). A batch in which every event is malformed still returns 202 with all events listed, so clients do not loop. This is a proposed choice to confirm. If the append fails or times out, return 503 with no acknowledgment. Clients will resend the same `event_id`s, and dedup absorbs any copy that did land.

6. **Archive raw copies.** An archiver consumes the log independently of the live consumer. It writes each record, with its log partition, log offset, `received_at`, and original bytes, to object storage under `raw/dt=YYYY-MM-DD/`, where the date is the UTC day of `received_at`. Each object is written once and never rewritten. The archive is the replay source of truth. The log's 14-day retention is too short for the 90-day requirement and the 8-day replay lookback.

7. **Live deduplication and enrichment.** A live consumer, in its own consumer group, reads the log in order. For each event:
   - Call SETNX on `event_id` with value = its log position `(partition, offset)` and TTL = 8 days. Set once, never refreshed.
   - If SETNX succeeds, or the existing value equals this event's own log position (the redo case after a crash), the event is a winner. Enrich it with geo-IP and user-agent parsing, record `enrichment_version`, and pass it to the writer.
   - Otherwise it is a duplicate. Count it as dropped and do not write it to `events_clean`. The raw copy stays in the archive.
   - The 8-day TTL covers the 7-day retry window plus a 1-day margin.

8. **Write winners to the open partition.** A live writer collects winners into micro-batches every 60 to 90 seconds and appends them to the partition for the event's `received_at` day. Each row carries `log_partition` and `log_offset`. Writes are idempotent on `(log_partition, log_offset)`, so a redo after a crash cannot insert a row twice. Rows from a redo are not lost either, because the KV claim was made against the same log position.

9. **Latency budget (target p95 under 3 minutes, alert at 4).** Collector ack: well under 1 second. Log to consumer: seconds. Enrichment and KV: seconds. Micro-batch wait: up to 90 seconds. Warehouse load and visibility: roughly 30 to 60 seconds. Monitor end-to-end lag as the difference between `now` and the newest `received_at` visible in `events_clean`.

10. **Seal a closed day.** Day N is sealed only when all of the following hold, and never before 02:00 UTC on N+1:
    - Collectors have stopped stamping day N, and in-flight writes have drained.
    - The live consumer has processed every log record appended before 02:00 UTC.
    - The archiver has finished writing `raw/dt=N/` and reports a complete watermark.
    - The live writer has committed its last micro-batch for day N.

    The 02:00 rule is the grace window for in-flight and late writes.

11. **Late records after seal.** A record with `received_at` on a sealed day that reaches the archive after the seal is archived as usual and raises an alert. The live path does not write it into the sealed partition. A later replay of that day picks it up from the archive, so the archive is the one place that stays complete.

12. **Operational guardrails for the live path.**
    - Alert if archive lag exceeds 12 hours. The log only keeps 14 days, so archive failure beyond that means permanent loss.
    - Alert if KV TTL writes fail or if the SETNX error rate rises.
    - Alert if end-to-end lag exceeds 4 minutes.
    - Track counts per day: accepted, rejected by reason, duplicates dropped, winners written. These counts are the baseline for replay validation.

## Replay path (one closed UTC day N)

13. **Request and gate.** An operator submits "replay day N". Reject the request unless:
    - Now is at or after 02:00 UTC on N+1, and day N is sealed.
    - The archive is complete for `raw/dt=N-8` through `raw/dt=N`.
    - No other replay of day N is running. Allow at most one replay per day at a time, and cap concurrent replays across days.

14. **Create a run record.** Record run ID, day N, requested enrichment version, operator, and start time. The record lives outside `events_clean`.

15. **Read only from the archive.** Read `raw/dt=N-8` through `raw/dt=N`. Do not read the log, and do not call the KV store. A replay must not change live dedup state or add load to ingestion.

16. **Recompute winners.** Group all copies by `event_id`. The winner is the copy with the lowest `(log_partition, log_offset)`, the same rule as live. Keep a winner only if its `received_at` is on day N. Because the 7-day retry bound means a day-N winner's earliest copy is no earlier than day N-7, the 8-day lookback is enough.

17. **Enrich with the new version.** Apply the fixed geo-IP and user-agent code or data. Pin the exact database and parser versions. Write `enrichment_version` into every row. Do not change the winner set in this step.

18. **Write to staging.** Write the rebuilt rows to a staging table with the same schema as `events_clean`, in a schema that dashboards cannot read. Include the run ID.

19. **Validate before any visible change.** All checks must pass:
    - Row count equals the number of recomputed winners. Each `event_id` appears exactly once. Every `received_at` falls on day N.
    - The set of `event_id`s equals the set currently in the live partition N, unless a bot-traffic policy was applied (see open decisions). Any difference means dedup or archive coverage is wrong, so stop.
    - The daily accepted, rejected, and dropped counts match the live baseline from step 12.
    - Enrichment-column differences are the only changes. Sample rows show the expected fixes.

    If any check fails, drop the staging table, mark the run failed, and leave the live partition alone.

20. **Atomic swap.** Replace partition N of `events_clean` from the staging table in one warehouse operation. Dashboards see the old partition before the swap and the new one after, never a mix. Record the run as complete.

21. **Clean up and keep the rollback path.** Drop staging after the swap is verified. If the warehouse supports partition snapshots or time travel, keep the pre-swap snapshot until the replay is signed off. If not, a rollback means rerunning the replay with the previous enrichment version, which is always possible inside the 90-day raw window.

22. **Confirm live state is untouched.** Before and after the replay, compare the KV key count and a sample of values, and check that the live consumer's offsets did not move. Keep this check in the run record.

## Changing enrichment for a day that is still open

- Deploying an enrichment fix changes output for new events right away. Earlier events from the same day keep the old enrichment until the day is closed and replayed. Dashboards can show mixed `enrichment_version` values for the open day. This is expected, and the plan should say so.
- Do not replay the open day. Wait until it closes.

## Open decisions (not decided, not chosen here)

- **Suspected bot traffic: drop it, or keep it with a flag.** This is open and this plan does not choose. Either option fits the design. Option A, flag: enrichment adds a `bot_suspected` column and dashboards filter it; the event set is unchanged, so replay validation in step 19 is unchanged. Option B, drop: a filter is applied in step 7 or 17, and the validation in step 19 must compare against the post-filter set. Either way the decision must be recorded in the enrichment version so a replay can reproduce it. The raw archive keeps every event for 90 days, so a drop can still be reversed by replay inside that window but not after it.
- Whether to store rejected event bodies. The brief does not require it. Storing metadata only, or bodies for 90 days, are both possible.
- Response codes for whole-batch errors (400 for a bad body or more than 100 events) and for an all-malformed batch (202 with all rejected, as proposed in step 5).
- The exact dedup TTL (8 days proposed) and the exact archive lag alert threshold (12 hours proposed).
- Whether the warehouse supports partition snapshots (affects step 21).
- Whether a UUID format check on `event_id` is required (proposed in step 2).

## Verification

1. Duplicate arriving 7 days after the first copy is dropped. A duplicate arriving 8 days after is also dropped only if the TTL covers it, so test the boundary against the chosen TTL.
2. An event with a client timestamp on day N+1 but `received_at` on day N lands in partition N.
3. A batch with one malformed event returns 202, lists that event, and writes the others.
4. A crash between SETNX and the warehouse write, followed by redo, produces exactly one row.
5. A replay of an open day is refused. A replay of a closed day leaves the KV store and consumer offsets unchanged.
6. A dashboard query running during the swap sees only complete old or complete new data.
7. Replay validation fails when one `event_id` is removed from staging, and the live partition is unchanged.
8. Live end-to-end lag stays under 4 minutes while a replay runs at full configured rate.
