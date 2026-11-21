# Clickstream ingestion plan

## What this is

Today there is no pipeline. This plan adds one. Clients send batches of events to a new collector. The collector stamps each event with `received_at`, writes it to a replicated log, and only then returns 202. Two separate consumers read the log. The archiver saves every copy, unmodified, to object storage for 90 days. The live processor drops duplicates, enriches the winners and loads them into the warehouse table `events_clean`, one partition per UTC day. Events are queryable within 5 minutes.

Replay rebuilds one closed day from the archive alone. It never reads the log or touches live dedup state. It writes to a staging table, and one atomic partition swap puts the result live.

```
clients -> collector -> log (keyed by event_id) -+-> archiver -> object storage (raw, 90 d)
                                                 +-> live processor -> events_clean (day partition)
                                                        |
                                                  KV dedup (TTL 8 d)

replay: object storage (raw) -> isolated job -> staging table -> atomic partition replace
```

## Terms

- **Event**: one click or screen view. It has a client-made `event_id`, a `device_id` and a client timestamp.
- **Copy**: one received instance of an event. Clients resend batches, so one event can have many copies.
- **`received_at`**: server UTC time stamped by the collector. Its UTC day is the event's day. Client timestamps are never used for the day.
- **Envelope**: the archived record. It holds the original event bytes (never re-serialised), `received_at`, client IP, User-Agent, collector id and batch id. The IP and User-Agent are kept because replay needs them to redo the geo-IP and user-agent enrichment.
- **Log**: the replicated append-only log, kept 14 days. Copies of one `event_id` all land in the same log partition.
- **Winner**: the copy with the lowest log offset in its log partition for that `event_id`. Live ingestion and replay both use this rule, so they agree even if two collectors stamp times slightly out of order. Every other copy is a duplicate and is dropped from `events_clean`. It stays in the archive.
- **Dedup window**: 8 days. Clients retry for up to 7 days, plus up to 5 minutes of backoff.
- **Closed day**: day D is closed once the time is past 02:00 UTC on D+1 and the live processor has written a `closed` marker for D. Only closed days can be replayed.

## Live path

**1. Collector receives a batch**
- Starts: a client sends up to 100 events over HTTPS.
- Does: stamps one `received_at` from the server clock (NTP-synced, with a clock-skew alarm). Checks each event on its own. It rejects an event with no `event_id`, no `device_id`, or over 32 KB. Rejected events never enter the log. It builds an envelope for each accepted event.
- Data: none. The collector is stateless and scaled horizontally.
- If it goes wrong: under overload it returns 429 before accepting anything, so a batch is never half-accepted.

**2. Collector writes durably and answers**
- Starts: step 1 finishes.
- Does: produces every accepted event to the log, keyed by `event_id`, with all-replica acknowledgement (`acks=all`). It waits for every acknowledgement, then returns 202 with the rejected events. Each is identified by its index in the batch, plus its `event_id` if it has one. Clients never retry rejected events.
- Data: the log.
- If it goes wrong: if any write fails, it returns 503 for the whole batch. The client resends the same batch with the same ids. Events already written become duplicates and are dropped later.
- Choice to confirm: a batch where every event is rejected still returns 202 with the full list. The brief does not say.

**3. Archiver saves raw copies**
- Starts: it reads the log as its own consumer group.
- Does: writes envelopes to `raw/dt=<UTC day of received_at>/part=<log partition>/<first offset>-<last offset>.parquet`. The file name is fixed, so a re-upload overwrites itself. It commits its log offsets only after the upload succeeds. It also writes a small index per day and log partition holding `(event_id, partition, offset)`. When it has passed the end of day D in every partition, it writes a manifest for D with record counts and offset ranges per partition.
- Data: object storage. A lifecycle rule expires `raw/` objects 90 days after creation.
- If it goes wrong: it re-reads from its last committed offset. The fixed file names make this harmless. An alert fires if lag exceeds 1 hour. The 14-day log retention is the safety margin.

**4. Live processor removes duplicates**
- Starts: it reads the log as a second, separate consumer group.
- Does: for each event, runs an atomic set-if-absent in the KV store on `event_id`, with value `partition:offset` and TTL 8 days. If the key is absent, or already holds this event's own `partition:offset`, the event is the winner. The second case makes reprocessing after a crash safe. If the key holds a different value, the event is a duplicate. It is dropped and counted.
- Data: the KV dedup store.
- If it goes wrong: see "If the KV store loses data" below.

**5. Live processor enriches**
- Starts: step 4 marks the event a winner.
- Does: parses the User-Agent and does the geo-IP lookup. Each output row gets an `enrichment_version`. Bot handling goes here, after dedup. It is undecided (see Open questions). Bot signals are computed either way.
- Data: none beyond the row in flight.
- If it goes wrong: the processor retries from its last committed offset. Nothing is lost, because the log and archive hold the event.

**6. Live processor loads `events_clean`**
- Starts: every 60 seconds or 5,000 rows, whichever comes first.
- Does: splits the batch by the UTC day of `received_at` and appends each part to that day's partition. The load is idempotent by `event_id` (merge or insert-if-absent), so a reload after a crash adds no duplicates.
- Data: the warehouse table `events_clean`.
- If it goes wrong: the batch is reloaded safely. An alert fires if p95 freshness lag exceeds 3 minutes.
- Latency budget: collector to log under 1 s, processor under 30 s, flush up to 60 s, warehouse visibility under 2 min. That is about 3.5 minutes, inside the 5-minute requirement.

**7. Live processor closes the day**
- Starts: 02:00 UTC on D+1.
- Does: writes a `closed` marker for D, but only if it has consumed past the end of D in every log partition. After the marker, live writes to D stop.
- Data: the marker, stored with the live pipeline's state.
- If it goes wrong: if the processor is behind, the marker waits. An event that arrives for D after the marker raises an alert and is fixed by replaying D.

## Replay of one UTC day

**8. Operator starts a replay**
- Starts: the operator gives day D, the enrichment code version and the geo-IP database version. The replay runs as a separate job, not in the live processor.
- Does: runs the preflight checks in step 9.
- Data: an audit log records run id, operator, versions and row counts.
- If it goes wrong: nothing has changed yet. The operator fixes the input and starts again.

**9. Preflight checks**
- Starts: step 8.
- Does: refuses to continue unless all of these hold:
  - Day D is closed.
  - The archive manifest for D exists and matches the archived record counts.
  - Archive indexes exist for D-8 through D, and D-8 is still inside the 90-day retention. So the replayable window is about 82 days. Older days are refused with a clear message.
  - No other replay of D is running. The job takes a per-day lock, a KV key with a lease TTL so a dead job cannot hold it forever.
- Data: the lock key in the KV store.
- If it goes wrong: the job stops with the reason. Nothing has changed.

**10. Resolve winners**
- Starts: step 9 passes.
- Does: reads the `(event_id, partition, offset)` indexes for D-8 through D, plus the first two hours of D+1. The extra hours cover the case where a copy stamped D+1 has a lower offset than a copy stamped D. A copy stamped D is kept only if it has the lowest offset for its `event_id` in its log partition. If an earlier copy exists, in D or an earlier day, it is dropped.
- Data: reads archive indexes only. It never reads or writes the live KV dedup store.
- If it goes wrong: the job fails and releases the lock. Nothing live has changed. Rerun it.

**11. Enrich and apply the bot policy**
- Starts: step 10 finishes.
- Does: runs the chosen enrichment version over the winners in D, reading the raw envelopes from the archive. It uses the same `bot_policy` setting as live ingestion.
- Data: reads the archive.
- If it goes wrong: the job fails and the live partition is untouched. Rerun it.

**12. Write to staging**
- Starts: step 11 output.
- Does: loads rows into a staging table, for example `events_clean_staging_<D>_<run id>`. The job has its own compute pool, a concurrency of 1 and a read-rate cap on object storage. It never reads the log, so it cannot slow live ingestion.
- Data: the staging table.
- If it goes wrong: drop the staging table and rerun.

**13. Validate**
- Starts: step 12 finishes.
- Does: fails the replay if any check fails.
  - No duplicate `event_id` in staging.
  - Row count equals the number of distinct winners in D.
  - Schema and non-null checks pass.
  - A diff against the current partition shows the same `event_id`s, so only enriched columns changed. Other differences, such as from the bot policy, must be explained.

  The operator sees a diff summary and approves. This approval is optional by configuration.
- Data: reads staging and the live partition.
- If it goes wrong: the job stops before the swap. The live partition is unchanged.

**14. Swap**
- Starts: validation passes and approval is given, if required.
- Does: uses the warehouse's atomic single-partition replace to swap staging into `events_clean` partition D. Dashboards see the old day or the new day, never a partial one. It records the run in the audit log and releases the lock.
- Data: `events_clean` and the audit log.
- If it goes wrong: the swap is atomic, so a failure leaves the old partition in place.

## Operator tasks

- **Roll back a bad replay.** Replay the day again with the previous enrichment version. The raw archive is the source of truth, so no backup of the old partition is needed.
- **If the KV store loses data.** Live ingestion briefly admits duplicates. Re-seed the last 8 days of keys from the archive indexes. Then replay any days affected during the gap. Replay never writes dedup state, so this is a separate task.

## What happens when things fail

| Where | Failure | Handling |
|---|---|---|
| Collector | Overload | 429 before accepting anything. The client retries. |
| Collector | Log write fails | 503 for the whole batch. The client resends. Repeats become duplicates. |
| Archiver | Upload fails or crashes | Offsets are not committed. It reprocesses and overwrites the same files. Alert at 1 hour lag. |
| Live processor | Crash | It resumes from the last committed offset. Dedup and load are both idempotent. |
| Live processor | Behind at 02:00 | The `closed` marker waits. |
| Live processor | Late event after day close | Alert, then replay that day. |
| KV store | Data lost | Re-seed keys from archive indexes, then replay affected days. |
| Replay | Preflight, validation or any step fails | The job stops. The live partition is untouched. |
| Replay | Job dies holding the lock | The lock lease expires. |

## Rollout

- Build the archive and collector first, then the live processor, then replay. The archive is needed by replay.
- Do not ship the bot step to production until `bot_policy` has a value.

## Open questions

- **Bot traffic.** Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose. The decision touches only the bot step in live ingestion and in replay. The archive keeps every accepted event either way, and dedup always runs first. The policy is one setting, `bot_policy = drop | flag`, shared by live and replay. If the answer is "flag", add a nullable `is_suspected_bot` column to `events_clean` then. If product changes the answer later, replay fixes affected days within the replayable window.
- **All-rejected batch.** Should it return 202 or a 4xx? This plan returns 202 with the full rejection list.
- **Warehouse append.** Can the warehouse append to or merge into a day partition, as well as replace one atomically? Live loads assume it can.
- **Clock skew.** Collector clocks are assumed to stay within a few seconds of each other.
- **Late retries.** The SDK is assumed never to retry later than 7 days plus 5 minutes after the first send. A copy arriving after 8 days would be treated as new, by live ingestion and by replay.
