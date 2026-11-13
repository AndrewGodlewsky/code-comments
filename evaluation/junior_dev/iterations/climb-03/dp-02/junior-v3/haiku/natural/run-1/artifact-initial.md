# Clickstream ingestion plan: `events_clean`

## Terms and fixed values

- **Event day D**: the UTC date of `received_at`, stamped by the collector when the request arrives. It sets the partition, and it decides which replay covers the event. Client timestamps are never used for partitioning.
- **Dedup window W = 8 days**: the 7-day SDK buffer plus one day of margin. It is anchored on the first accepted copy of an event and is not refreshed by later copies.
- **Day close**: day D closes at 02:00 UTC on D+1.
- **Raw archive**: every accepted event, duplicates included, stored as received for at least 90 days from its `received_at`.
- **Source of truth**: the raw archive. `events_clean` is derived from it and can be rebuilt.

## Design summary

Kafka is the durable acceptance point. A live consumer deduplicates and enriches events into `events_clean`. A separate archive sink writes raw events to object storage. Replay rebuilds one closed day from the archive into a staging table and then atomically replaces that day's partition.

## Part A: Live path

1. **Stamp at the collector.** For each request, the collector records `received_at` (server UTC clock, NTP-synced), a collector-generated `batch_id`, and each event's `position` in the batch. It stores each event's JSON bytes exactly as received. The envelope wraps those bytes and never edits them.

2. **Validate per event.** An event is rejected if it lacks `event_id` or `device_id`, or if its bytes exceed 32 KB. Each rejected event gets a reason and goes to a reject log. It is not sent downstream. The rest of the batch continues. (Confirm whether `event_id` must also be a valid UUID; the brief names only presence.)

3. **Make the batch durable, then answer.** Append accepted events to a replicated Kafka topic `events_raw`, keyed by `event_id`, with `acks=all`. Return 202 only after the producer acknowledges, and list the rejected events in the response. If Kafka is unavailable, return 503 so the client retries. Keying by `event_id` keeps all copies of an event in one partition, so their order within that partition follows receipt order.

4. **Archive sink.** A separate consumer group reads `events_raw` and writes envelope plus raw bytes to object storage under `received_date=YYYY-MM-DD/`, rolling files hourly and by size. Nothing is deduplicated here. Set a lifecycle rule that expires objects 90 days after they are written. Because the expiry runs from write time, it is never shorter than 90 days from `received_at`. Alert when sink lag exceeds about 1 hour. Kafka's 14-day retention is the backstop, and the alert must fire long before it matters.

5. **Claim each event for dedup.** The live consumer does an atomic set-if-absent on a KV key `event_id`, with value `{state: pending, first_received_at, kafka_offset, owner, claimed_at}` and TTL = W. If the claim fails, the copy is a duplicate and is not written. Later copies do not refresh the TTL.

6. **Enrich and write.** Accumulate claimed events into micro-batches of roughly 60 seconds. Enrich them (geo-IP lookup, user-agent parsing) using pinned code and reference-data versions. Write them to `events_clean` in partition `received_date = D`, idempotently keyed by `event_id`, so a retried batch cannot insert twice. Record `enrichment_version`, `reference_data_version`, and `pipeline_version` on each row. Verify that the warehouse supports keyed idempotent writes. If it does not, use a per-batch staging step and a claim-state check instead. Apply the bot-traffic rule here once it is decided (see Open decisions).

7. **Commit claims and offsets.** After the warehouse write succeeds, set each claim to `committed` and only then commit the Kafka offset. If a consumer crashes after claiming, the claim stays `pending`. A pending claim older than about 10 minutes can be taken over by another consumer through a compare-and-set on the claim's version. The taking consumer then re-runs step 6 from the stored offset. This gives at-least-once consumption with effectively-once rows.

8. **Latency budget.** Target: 5 minutes at p99 from collector receipt to queryable. Rough budget: collector to Kafka under 1 second; micro-batch of about 60 to 90 seconds; warehouse load. Alert when p99 reaches 4 minutes. Measure `warehouse_commit_time - received_at` for each row. The target applies to first-arrival copies only.

9. **Late copies.** A copy that arrives within W of the first accepted copy is dropped. A copy that arrives after W has no live claim, so it is admitted as new and lands in today's partition under its own `received_at`. Count these as delivery-SLA violations and make sure replay handles them. Mobile events buffered for days are first arrivals, so they land in the partition for the day they arrived, with their old client timestamps. This is intended.

## Part B: Replay of one closed day D

R1. **Gate.** Refuse unless the current time is at or after 02:00 UTC on D+1, and the archive for days D-8 through D still exists under the 90-day lifecycle. Take a per-day replay lock so only one replay of D runs at a time.

R2. **Pin versions.** Choose the enrichment code version and the geo-IP and user-agent reference-data versions. Record them in the run log.

R3. **Read the archive only.** Read raw objects for `received_date` in [D-8, D]. Do not read Kafka, do not touch KV, and do not commit live consumer offsets. Run on a separate compute pool with capped read rate, so live ingestion is not slowed.

R4. **Choose winners.** For each `event_id` that has a copy in D, the winner is the copy with the minimum `(received_at, batch_id, position)`. Keep the winner only if its `received_at` falls in D. Under the delivery SLA, all copies of an event lie within the 7-day retry span from its first send. So the 8-day lookback contains every earlier copy that could change the outcome. Live uses first-processed order and replay uses earliest `received_at`. The two agree except for sub-second reordering across collector nodes. Replay is authoritative, so any such difference is corrected here.

R5. **Enrich.** Run the pinned enrichment on the winners' original bytes from the archive.

R6. **Write to staging.** Write rows to a staging table or partition for this run. Dashboards never read it.

R7. **Validate.** Check that the row count equals the winner count, `event_id` is unique within the staging rows, every `received_at` falls in D, and the schema matches. Produce a diff against the current partition D (rows added, removed, and changed, with reasons). The operator sets the threshold above which a large removal needs sign-off.

R8. **Confirm no live writes to D.** Confirm there are no pending claims or buffered micro-batches with `received_at` in D. After close there should be none. If any exist, abort and raise an alert.

R9. **Atomic replace.** Replace partition D of `events_clean` from staging in a single warehouse operation. Dashboards see either the old partition or the new one, never a mix.

R10. **Record and clean up.** Log D, the versions, counts, the diff, the operator, and the time. Drop the staging data.

R11. **Failure.** Any failure before R9 leaves `events_clean` untouched, so the run can be aborted and restarted from R1. Replay of D does not depend on `events_clean`, so replays of different days can run in any order.

## Part C: Operations and gates

- Replay never writes to `events_raw`, KV, or live consumer offsets.
- **Monitoring:** collector 202 and 503 rates; reject rate by reason; Kafka consumer lag; sink lag; pending-claim age; end-to-end latency p99; count of late copies beyond W, which should be near zero; and per-day archive completeness.
- **Close gate:** at 02:00 UTC on D+1, verify that the sink has flushed all objects for D. Any event with `received_at` in D that arrives after close is an incident. It means the collector or sink fell behind, and the day must not be treated as complete until it is investigated.
- **Retention:** a day can only be replayed while its archive, and the lookback days, are within the 90-day window. Expired days cannot be rebuilt.

## Open decisions

1. **Suspected bot traffic: drop or keep with a flag. Not decided. This plan does not choose.** Either option is applied in step 6 and must be applied identically in replay (R5). Dropping removes bot events from `events_clean`. Flagging adds a column to `events_clean`. The archive keeps every accepted event under either option. The rule must be versioned so that a replay of D uses the same rule version that was in force when the replay was requested. Product needs to decide before the enrichment stage ships.
2. **Window size.** W = 8 days relies on the delivery SLA. A 90-day window would match the archive and remove that dependency, at a higher KV cost. Confirm the choice against the SLA.
3. **Winner tie-breaking.** Confirm that replay's earliest-`received_at` rule is acceptable as the authoritative definition, given the sub-second reordering difference in R4.
4. **Warehouse capabilities.** Confirm keyed idempotent writes (step 6), atomic partition replace from a staging table (R9), and KV atomic set-if-absent with TTL and compare-and-set (steps 5 and 7).
5. **Reject log retention.** The brief does not specify it.