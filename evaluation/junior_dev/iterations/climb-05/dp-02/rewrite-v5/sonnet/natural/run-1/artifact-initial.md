# Clickstream ingestion: implementation plan

## Design decisions

- **Partition and replay key:** `received_at` (UTC, stamped by the collector) decides the day. Nothing else does.
- **Source of truth:** an immutable raw archive. It holds every accepted event, duplicates included, exactly as received. Everything downstream can be rebuilt from it.
- **Live deduplication:** an atomic set-if-absent on `event_id` in the key-value store, with an 8-day TTL.
- **Replay deduplication:** replay never touches the live key-value store. It recomputes the same winners from the raw archive.
- **Dashboard safety:** replay builds into a staging table and then swaps the day partition with one atomic replace.

```
client -> collector -> log (keyed by event_id) -+-> archiver -> object storage (raw, 90 d)
                                                 +-> dedup + enrich -> events_clean (today)
operator -> replay job: raw (D-8..D) -> own dedup + enrich -> staging -> atomic replace of day D
```

## Part A. Live path

1. **Define the log topic and the raw envelope.**
   - Create one topic. Key it by `event_id`, so every copy of an event lands in the same log partition and offset order is a total order for that event.
   - Fix the partition count. Resizing in place would break per-key ordering. A resize needs its own migration plan.
   - Each record has two parts.
     - **Payload:** the event bytes, byte-for-byte as received.
     - **Envelope:** `received_at`, collector instance, batch id, source IP, and the `User-Agent` and other headers.
   - The envelope has to be stored. Geo-IP and user-agent enrichment need those inputs, and replay cannot recover them later.

2. **Build the collector.**
   - Accept batches of up to 100 events. Set the body-size limit from 100 x 32 KB plus overhead.
   - Validate each event on its own. Reject it if `event_id` or `device_id` is missing, or if it is over 32 KB. Do not reject the whole batch.
   - Stamp `received_at` from the server clock. Use the same synchronized time source on every instance.
   - Write all accepted events to the log with full-replica acknowledgement. Only after every write is acknowledged, return **202** with the list of rejected events. Identify each rejected event by its batch index, plus its `event_id` when present, and give a reason.
   - Return 202 with the rejected list even when every event is rejected. This avoids SDKs treating a 4xx as retryable. Confirm this with the SDK owners.
   - If any log write fails or times out, return 5xx. Use 429 when shedding load. Events already written become duplicates on retry and are dropped later, so partial writes are safe.
   - Do not store rejected events. Record counts by reason as metrics only.

3. **Run the archiver, an independent log consumer.**
   - Write every record, duplicates included, to object storage under `raw/dt=<UTC day of received_at>/`. Include the log partition and offset in each record.
   - Write files atomically. Add them to a manifest only after the write completes.
   - Track a per-partition watermark: the highest offset archived, and the `received_at` it reached.
   - Alert if the archiver falls more than 15 minutes behind. The log keeps data for only 14 days, and the archive is the 90-day record.
   - Apply a lifecycle rule that expires objects 90 days after creation. Creation time is never earlier than `received_at`, so retention is at least 90 days.

4. **Run the dedup stage, a second consumer group.** It processes each log partition in offset order.
   - For each record, run `SET key=event_id value=(partition, offset) IF NOT EXISTS` with an **8-day TTL**.
     - The client buffer holds events for 7 days, and the last backoff is at most 5 minutes. A duplicate can therefore arrive about 7 days and 5 minutes after the first copy. The extra day is margin.
   - Interpret the result:
     - **Key created:** this copy is the winner. Continue.
     - **Key exists and its value equals this record's (partition, offset):** this is a redelivery after a crash. It is still the winner. Continue.
     - **Key exists with a different value:** this is a duplicate. Drop it from the clean path and count it. It stays in the raw archive.
   - If the key-value store is unavailable, stop and retry. Do not commit offsets and do not guess.

5. **Enrich the winners.**
   - Apply the geo-IP lookup and user-agent parsing, using the stored envelope as input.
   - Write `enrichment_version` (code and database versions) on every row.
   - The enrichment code must be pure over the envelope and payload. The replay job runs the same code.
   - Bot handling belongs in this stage. It is open (see "Open decision" below).

6. **Load into `events_clean`.**
   - Micro-batch every 60 seconds or 5,000 rows, whichever comes first.
   - Route each row to the partition for the UTC day of its `received_at`.
   - Make the load idempotent, either by merging on `event_id` or by loading under a batch id. Commit log offsets only after the load succeeds.
   - Before writing to a day, check the day-close control record (step 11). If the day is closed, send the rows to a dead-letter location and alert. Do not write them. A later replay of that day picks them up from raw.

7. **Meet the 5-minute freshness target.**
   - Budget: under 5 s from collector to log, under 30 s for dedup and enrichment, 60 s of micro-batch wait, and under 60 s for the warehouse load. The total is about 2.5 minutes.
   - Metric: `now - max(received_at)` of rows visible in the warehouse. Alert at 4 minutes.

8. **Operate the live path.**
   - Monitor consumer lag, the duplicate rate, the rejection rate by reason, key-value store errors, and archiver lag.

## Part B. Replay

9. **Replay inputs.**
   - The operator runs a command with a day `D` and an enrichment code version.
   - The job reads only the raw archive in object storage. It never reads the log, which expires after 14 days, and it never touches the live key-value store or live consumers.

10. **Check eligibility.** Refuse the replay unless all of these hold:
    - Now is past 02:00 UTC on D+1.
    - The archiver watermark on every partition has passed the end of D, so raw for D is complete.
    - Raw for D-8 through D still exists. This limits replay to days within about 82 days.
    - No other replay is running for D.

11. **Close the day.** When the first replay of D starts (or when the day-close job runs), write a "closed" control record for D. The live sink checks it (step 6), so live writes stop for D. This record is the fence between live ingestion and replay.

12. **Recompute the winners without live state.**
    - Load `(event_id, partition, offset, received_at)` for raw days D-8 through D.
    - For each `event_id`, the winner is the copy with the lowest (partition, offset). This matches the live outcome, because live processes each key's partition in offset order.
    - Keep a winner if its `received_at` falls in day D. Winners from earlier days are not replayed, and later copies are dropped.
    - Copies that arrive after D never affect D, because the first copy wins.

13. **Enrich and build staging.**
    - Run the new enrichment code over the winners' payloads and envelopes.
    - Write to a staging table, or a staging partition, of the same schema. Dashboards do not read it.
    - Run on a separate worker pool with a throttled warehouse write rate. Live ingestion is unaffected.

14. **Validate before swapping.**
    - `event_id` is unique in staging.
    - The staging `event_id` set equals the set currently in partition D. A replay is meant to change only enrichment. Any difference is reported as a drift report, and the swap needs an explicit operator override.
    - No null in required columns, and the row count is plausible.
    - Optionally, export the current partition D to object storage first, as a rollback copy.

15. **Atomically replace partition D.**
    - Use the warehouse's single-partition atomic replace. Dashboards see the old day until the swap and the new day after it, never a mix.
    - Record the replay (day, code version, row counts, drift) in an audit log.
    - Replaying again is idempotent and uses the same steps.

16. **Run drift checks (recommended).**
    - Run the replay in compare-only mode (steps 12-14, no swap) for each closed day.
    - This detects lost key-value keys, eviction, or live bugs without changing data.

## Part C. Delivery order

17. Build in this order, with a test at each step:
    1. Log topic and collector, with tests for partial rejection and for 5xx behavior on log failure.
    2. Archiver, with a test that duplicates are kept byte-for-byte.
    3. Dedup stage, with crash and redelivery tests, plus a duplicate-across-days test using a copy delayed up to 7 days.
    4. Enrichment and warehouse sink, with freshness measurement.
    5. Replay job, with tests for dashboard atomicity, live isolation, and the closed-day gate.

## Open decision (product)

**Suspected bot traffic: drop, or keep with a flag?** The plan does not choose.
- The raw archive keeps everything either way, so the decision is reversible for 90 days of raw data.
- It affects only the bot step in enrichment (step 5), the `events_clean` schema (a flag column or none), and the replay output.
- Owner: Product. Decide before the schema is frozen in step 6. Until then the bot step is a no-op placeholder.

## Assumptions to confirm

- The warehouse supports an idempotent micro-batch load, such as a merge on `event_id` or a load keyed by batch id. If it only supports partition replace, the fallback is for the live sink to rebuild today's partition every few minutes with atomic replace. That is heavier but meets the same constraints.
- The key-value store supports atomic set-if-absent with a per-key TTL.
- Collector clocks are synchronized. Skew only shifts events across the day boundary, and the live and replay paths use the same stamped `received_at`.
