# Clickstream ingestion plan

## Summary

Clients send batches to a new collector. The collector stamps `received_at`, writes each accepted event to the replicated log, and only then returns 202. Two independent consumers read the log. One archives every copy, unmodified, to object storage for 90 days. The other deduplicates, enriches and loads `events_clean`.

Replay rebuilds one closed day from the archive alone. It never touches the log, the live dedup state, or the live partition until a single atomic swap.

```
clients -> collector -> log (keyed by event_id) -+-> archiver -> object storage (raw, 90 d)
                                                 +-> live processor -> events_clean (day partition)
                                                        |
                                                  KV dedup (TTL 8 d)

replay: object storage (raw) -> isolated job -> staging table -> atomic partition replace
```

## Design decisions that the steps rely on

- **Day assignment.** The UTC day of the winning copy's `received_at` decides the partition. Client timestamps are never used for partitioning.
- **Definition of "first copy".** The log is keyed by `event_id`, so all copies of one id sit in the same log partition. The copy with the lowest offset in that partition is the winner. Live ingestion and replay use this same rule, so they agree even when two collectors stamp times a few milliseconds out of order.
- **Dedup window.** Clients retry for up to 7 days, plus up to 5 minutes of backoff. Live dedup state therefore lives 8 days. Replay looks back 8 whole days.
- **Raw data includes the enrichment inputs.** The archived envelope holds the original event bytes plus `received_at`, client IP, User-Agent header, collector id, log partition and offset. Without the IP and User-Agent, a replay could not redo the geo-IP and user-agent enrichment.
- **The log is not the archive.** Log retention is 14 days and the raw requirement is 90, so object storage is the source of truth for replay.

## A. Live path

1. **Define the event envelope and archive layout.**
   - Envelope fields: raw event bytes (never re-serialised), `received_at`, client IP, User-Agent, collector id, batch id.
   - Archive path: `raw/dt=<UTC day of received_at>/part=<log partition>/<first offset>-<last offset>.parquet`. The file name is deterministic so a re-upload overwrites itself.
   - Lifecycle rule: expire `raw/` objects 90 days after creation.

2. **Build the collector (HTTPS, stateless, horizontally scaled).** For each batch of up to 100 events:
   1. Stamp one `received_at` from the server UTC clock (NTP-synced, with a clock-skew alarm).
   2. Validate each event on its own. Reject an event if it has no `event_id`, no `device_id`, or is over 32 KB. Rejected events never enter the log.
   3. Build the envelope for each accepted event.

3. **Make the write durable before answering.**
   - Produce every accepted event to the log, keyed by `event_id`, with all-replica acknowledgement (`acks=all`).
   - Wait for every acknowledgement, then return 202 with the list of rejected events. Identify each by its index in the batch, plus its `event_id` when it has one.
   - Return 202 even if every event in the batch was rejected. This is a choice I made, because the brief does not say, and it needs confirmation.
   - If any produce fails, return 503 for the whole batch. The client resends the full batch with the same ids. Events already written become duplicates and are dropped later.
   - Under overload, return 429 before accepting anything, so no partial acceptance occurs.

4. **Run the archiver.**
   - It is a separate consumer group on the log. It writes the envelopes to the archive path from step 1, and commits its log offsets only after the upload succeeds. This is at-least-once, and the deterministic file names make retries harmless.
   - It also writes a small index file per day and log partition, holding `(event_id, partition, offset)` only. Replay uses these indexes for its lookback.
   - Alert if archiver lag exceeds 1 hour. The 14-day log retention is the safety margin, and the alert fires long before it matters.
   - Once the archiver has passed the end of day D in every partition, it writes a per-day manifest. The manifest holds record counts and offset ranges per partition.

5. **Run the live processor** (separate consumer group). For each event, in this order:
   1. **Dedup.** Do an atomic set-if-absent in the KV store on `event_id`, with a value of `partition:offset` and a TTL of 8 days.
      - If the key is absent, or already holds this event's own `partition:offset`, the event is the winner. The second case makes crash-and-reprocess safe.
      - If the key holds a different `partition:offset`, the event is a duplicate. Drop it and count it. The raw copy remains in the archive.
   2. **Enrich.** Parse the User-Agent and do the geo-IP lookup. Stamp each output row with an `enrichment_version`.
   3. **Bot step.** This step is open (see section C). Dedup always runs before it.

6. **Load `events_clean` for freshness.**
   - Micro-batch winners every 60 seconds or 5,000 rows, whichever comes first. Split each batch by the UTC day of `received_at`, and append to that day's partition.
   - Make loads idempotent by `event_id`, using a merge or insert-if-absent, or a load keyed by batch id. Offsets and the load are then recoverable after a crash.
   - Latency budget: collector to log under 1 s, processor under 30 s, flush up to 60 s, warehouse visibility under 2 min. That totals about 3.5 min, inside the 5-minute requirement.
   - Alert on a p95 freshness lag over 3 minutes.

7. **Close each day.** At 02:00 UTC on D+1, the live writer writes a `closed` marker for day D, but only if its consumed offsets have passed the end of D in every partition. If the processor is behind, the marker waits. After the marker is written, live writes to D stop. A straggler event is raised as an alert and fixed by replaying D.

## B. Replay of one UTC day

8. **Operator starts a replay** with two inputs: the day D, and the enrichment code and geo-IP database version to use. Replay runs as a separate job, not in the live processor.

9. **Run preflight checks.** Refuse to proceed unless all of these hold:
   - Day D is closed: the time is past 02:00 UTC on D+1 and the live `closed` marker for D exists.
   - The archive manifest for D exists and matches the archived record counts.
   - Archive indexes exist for D-8 through D, and the day D-8 is still inside the 90-day retention. This makes the replayable window about 82 days. Older days are refused with a clear message.
   - No other replay of D holds the lock. Take a per-day lock as a KV key with a lease TTL, so a dead job cannot hold it forever.

10. **Resolve winners without touching live state.**
    - Read the `(event_id, partition, offset)` indexes for D-8 through D, plus the first two hours of D+1. The extra two hours cover the clock-skew case where a copy stamped D+1 has a lower offset than a copy stamped D.
    - An event copy stamped in D is kept only if it is the lowest offset for its `event_id` in its log partition. If an earlier copy exists in a previous day, the copy in D is a duplicate and is dropped.
    - Replay reads only the archive indexes. It does not read or write the KV dedup store.

11. **Enrich and apply the bot policy.** Run the chosen enrichment version over the winners in D. Use the same bot-policy setting as live ingestion (section C).

12. **Write to staging, not to `events_clean`.**
    - Load into a staging table or staging partition, for example `events_clean_staging_<D>_<run id>`.
    - The job runs on its own compute pool, with a concurrency of 1 and a read-rate cap on object storage. It never reads the log, so it cannot slow live ingestion.

13. **Validate before swapping.** Fail the replay if any check fails:
    - No duplicate `event_id` in staging.
    - Row count equals the number of distinct winners in D.
    - Schema and non-null checks pass.
    - A diff against the current partition shows the same set of `event_id`s, so only the enriched columns changed. Other differences, for example from the bot policy, must be explained.

    Show the diff summary to the operator for approval. Make that approval step optional by configuration.

14. **Swap atomically.** Use the warehouse's atomic single-partition replace to swap staging into `events_clean` partition D. Dashboards see either the old day or the new day, never a partial one. Record run id, operator, versions and row counts in an audit log, then release the lock.

15. **Roll back if the result is wrong.** Replay again with the previous enrichment version. The raw archive is the source of truth, so no separate backup of the old partition is needed.

16. **Recover lost dedup state.** If the KV store loses data, live ingestion will briefly admit duplicates. Re-seed the last 8 days of keys from the archive indexes. Then replay any days affected during the gap. Replay itself never writes dedup state, so this is a separate operator task.

## C. Open decision

| Question | Owner | Status |
|---|---|---|
| Should suspected bot traffic be dropped, or kept with a flag? | Product | **Open. Not decided here.** |

- **What is unaffected.** The decision touches only step 5.3 (live) and step 11 (replay). The raw archive keeps every accepted event either way, because that is a fixed requirement. Dedup also runs before the bot step in both paths.
- **How the plan keeps both options open.**
  - Bot-detection signals are computed in both paths.
  - The policy is a single setting, `bot_policy = drop | flag`, shared by live ingestion and replay.
  - Do not ship step 5.3 to production until the setting has a value.
  - If the answer is "flag", add a nullable `is_suspected_bot` column to `events_clean` then.
  - If product changes the answer later, replay fixes affected days within the replayable window.

## D. Assumptions to confirm

- The warehouse can append to or merge into a day partition, in addition to replacing one atomically.
- Collector clocks stay within a few seconds of each other.
- The SDK never retries later than 7 days plus 5 minutes after the first send. Copies arriving later than 8 days would be treated as new events live, and would also be treated as new by replay.
- The brief does not say whether a batch where every event is rejected should return 202 or a 4xx. This plan returns 202 with the full rejection list.
