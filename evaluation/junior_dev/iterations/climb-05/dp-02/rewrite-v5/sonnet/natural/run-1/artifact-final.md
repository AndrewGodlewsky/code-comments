# Clickstream ingestion: implementation plan

## Summary

This pipeline takes click and screen-view events from the website and the iOS and Android apps and lands them, deduplicated and enriched, in the warehouse table `events_clean`, with one partition per UTC day. Nothing exists today, so this is new.

The flow: clients send batches of up to 100 events to a new collector. The collector stamps each event with the server time `received_at` and writes it to a replicated log. Two independent readers consume the log. The archiver copies every event, duplicates included, to object storage for 90 days. The dedup stage keeps the first copy of each `event_id`, enriches it (geo-IP, user agent) and loads it into `events_clean`, which is queryable within 5 minutes. When an enrichment bug is fixed, an operator replays one closed day. The replay rebuilds that day from the archive alone and swaps it in with one atomic replace.

It is shaped this way for three reasons. Clients retry for up to 7 days, so duplicates are normal. The log keeps data only 14 days, so the archive is the long-term record. Replay must not disturb live traffic or live dedup state, so it never reads the log or the live key-value store.

```
client -> collector -> log (keyed by event_id) -+-> archiver -> object storage (raw, 90 d)
                                                +-> dedup + enrich -> events_clean (today)
operator -> replay job: raw (D-8..D) -> own dedup + enrich -> staging -> atomic replace of day D
```

## Terms

- **Event:** one click or screen view. It carries a client-made `event_id` (UUID), a `device_id` and a client timestamp.
- **`received_at`:** the collector's server time (UTC) on arrival. It alone decides an event's day, partition and replay. The client timestamp is never used for this.
- **Duplicate:** a later copy of an event with the same `event_id`. The first copy received wins. Duplicates exist because clients resend a batch after a timeout, 429 or 5xx, and the mobile SDK can resend for up to 7 days.
- **Log:** the replicated append-only log (Kafka-style) with 14-day retention. It is split into partitions, and each record has an offset, its position within its partition.
- **Raw archive:** every accepted event, duplicates included, exactly as received, in object storage for 90 days. All other data can be rebuilt from it.
- **Envelope:** the metadata the collector stores next to the event bytes: `received_at`, collector instance, batch id, source IP, `User-Agent` and other headers. Enrichment needs it, and it cannot be recovered later.
- **Key-value store (KV):** the existing store with per-key TTL. Live dedup uses it to remember which `event_id`s were seen.
- **Closed day:** day D is closed from 02:00 UTC on D+1. Only closed days can be replayed.
- **Replay:** rebuilding one closed UTC day, usually after an enrichment fix.
- **Staging:** a table with the same schema as `events_clean`, which dashboards never read.

## How the system runs

### Live path

1. **Define the log topic and record format.**
   - Starts: once, at setup.
   - Create one topic keyed by `event_id`. All copies of an event then land in the same log partition, in order.
   - Fix the partition count. Resizing in place breaks that ordering and would need its own migration plan.
   - Each record holds the **payload** (event bytes exactly as received) and the **envelope**.
   - Data lives in: the log.

2. **Collector: receive and validate a batch.**
   - Starts: a client sends a batch of up to 100 events over HTTPS. Set the body limit from 100 x 32 KB plus overhead.
   - Check each event on its own. Reject it if `event_id` or `device_id` is missing, or if it is over 32 KB. The rest of the batch is still accepted. Clients never retry rejected events.
   - Stamp `received_at` from the server clock. All instances use the same synchronized time source.
   - Write every accepted event to the log and wait for full-replica acknowledgement. Only then return **202**, with the list of rejected events (batch index, `event_id` if present, reason). This is the only point where 202 is allowed, because it means the batch is durably stored.
   - Return 202 even when every event is rejected, so SDKs do not treat a 4xx as retryable. Confirm this with the SDK owners.
   - Rejected events are not stored. Count them by reason as metrics only.
   - Data lives in: the log.
   - If it goes wrong: if any log write fails or times out, return 5xx (or 429 when shedding load). The client resends the whole batch. Events already written become duplicates and are dropped later, so partial writes are safe.

3. **Archiver: copy everything to object storage.**
   - Starts: it is an independent log consumer and runs continuously.
   - Write every record, duplicates included, under `raw/dt=<UTC day of received_at>/`, with its log partition and offset.
   - Write each file atomically and add it to a manifest only after the write completes.
   - Per log partition, track a watermark: the highest offset archived and the `received_at` it reached. Replay uses it to know a day is complete.
   - A lifecycle rule expires objects 90 days after creation. Creation is never earlier than `received_at`, so retention is at least 90 days.
   - Data lives in: object storage.
   - If it goes wrong: it resumes from its last committed offset. Alert if it falls more than 15 minutes behind, because the log drops data after 14 days.

4. **Dedup: keep the first copy of each event.**
   - Starts: a second consumer group reads each log partition in offset order.
   - For each record, run `SET key=event_id value=(partition, offset) IF NOT EXISTS` with an **8-day TTL**. A duplicate can arrive about 7 days and 5 minutes after the first copy (7-day device buffer plus the last 5-minute backoff). The extra day is margin.
   - Key created: this copy is the winner, so continue.
   - Key exists with this record's own (partition, offset): this is a redelivery after a crash. It is still the winner, so continue.
   - Key exists with a different value: a duplicate. Drop it from the clean path and count it. It stays in the raw archive.
   - Data lives in: the KV store.
   - If it goes wrong: if the KV store is unavailable, stop and retry. Do not commit offsets and do not guess.

5. **Enrich the winners.**
   - Starts: for each winner from step 4.
   - Apply the geo-IP lookup and user-agent parsing, using the payload and the stored envelope as input.
   - Write `enrichment_version` (code and database versions) on every row.
   - The enrichment code must give the same output for the same payload and envelope, because replay runs this same code.
   - Bot handling belongs here but is undecided (see Open questions). Until it is decided, the bot step does nothing.
   - If it goes wrong: the batch is not committed and is retried.

6. **Load into `events_clean`.**
   - Starts: every 60 seconds or 5,000 rows, whichever comes first.
   - Send each row to the partition for the UTC day of its `received_at`.
   - Make the load idempotent, by merging on `event_id` or by loading under a batch id. Commit log offsets only after the load succeeds.
   - First check the day-close record (step 11). If the day is closed, send the rows to a dead-letter location and alert. A later replay of that day picks them up from the archive.
   - Data lives in: the warehouse.
   - If it goes wrong: the load is retried without committing offsets, and idempotency makes the retry safe.

7. **Freshness and monitoring.**
   - Time budget: under 5 s from collector to log, under 30 s for dedup and enrichment, up to 60 s of micro-batch wait, under 60 s for the warehouse load. The total is about 2.5 minutes against the 5-minute target.
   - Metric: `now - max(received_at)` of rows visible in the warehouse. Alert at 4 minutes.
   - Also watch consumer lag, duplicate rate, rejection rate by reason, KV errors and archiver lag.

### Replay

8. **Start a replay.**
   - Starts: an operator runs a command with a day `D` and an enrichment code version.
   - The job reads only the raw archive. It never reads the log or the live KV store, and it does not touch live consumers.

9. **Check eligibility.** Refuse unless all of these hold:
   - Now is past 02:00 UTC on D+1.
   - The archiver watermark on every partition has passed the end of D, so the archive for D is complete.
   - Raw data for D-8 through D still exists. Raw copies of D-8 are needed because a copy received on D can be a duplicate of an event first received up to 8 days earlier. This limits replay to days within about 82 days.
   - No other replay of D is running.

10. **Close the day.** Write a "closed" control record for D when the first replay starts, or earlier if a day-close job runs. The live loader checks it (step 6). This record is the fence between live ingestion and replay, so live writes to D stop.

11. **Choose the winners without live state.**
    - Read `(event_id, partition, offset, received_at)` for raw days D-8 through D.
    - For each `event_id`, the winner is the copy with the lowest (partition, offset). This matches the live result, because live reads each key's partition in offset order.
    - Keep a winner only if its `received_at` is in day D. Copies arriving after D never affect D, because the first copy wins.

12. **Enrich into staging.**
    - Run the new enrichment code over the winners' payloads and envelopes.
    - Write to staging. Dashboards do not read it.
    - Use a separate worker pool and a throttled warehouse write rate, so live ingestion is unaffected.

13. **Validate.**
    - `event_id` is unique in staging.
    - The staging `event_id` set equals the set now in partition D. Replay is meant to change only enrichment. Any difference is written to a drift report, and the swap then needs an explicit operator override.
    - No nulls in required columns, and the row count is plausible.
    - Optionally export the current partition D to object storage first, as a rollback copy.
    - If it goes wrong: do not swap. Staging is discarded or fixed and the replay is re-run.

14. **Swap atomically.**
    - Use the warehouse's single-partition atomic replace. Dashboards see the old day until the swap and the new day after it, never a mix.
    - Record the replay (day, code version, row counts, drift) in an audit log.
    - Replaying again uses the same steps and gives the same result.
    - If it goes wrong: the replace is atomic, so a failure leaves the old partition in place. Re-run the replay.

15. **Drift checks (recommended).** Run steps 11 to 13 for each closed day in compare-only mode, with no swap. This reveals lost KV keys, eviction or live bugs without changing data.

## What happens when things fail

| Failure | Result |
|---|---|
| Malformed event | Rejected alone and listed in the 202 response. Not retried by the client. |
| Log write fails or times out | Collector returns 5xx or 429. Client resends. Earlier writes become duplicates and are dropped. |
| Client resends a batch | Duplicates are dropped by dedup. The raw archive keeps them. |
| Dedup crashes mid-batch | Redelivery finds its own (partition, offset) in the KV store and is treated as the winner. |
| KV store unavailable | Dedup stops and retries. Nothing is committed. |
| Warehouse load fails | Retried without committing offsets. The load is idempotent. |
| Archiver lags | Alert at 15 minutes. It resumes from its last offset. |
| Live row for a closed day | Sent to dead-letter and alerted. A replay of that day picks it up. |
| Replay validation fails | No swap. Dashboards keep the old day. |

## How to build it

Build in this order, with a test at each stage:

1. Log topic and collector. Test partial rejection and 5xx on log failure.
2. Archiver. Test that duplicates are kept byte for byte.
3. Dedup stage. Test crash and redelivery, and a duplicate-across-days case with a copy delayed up to 7 days.
4. Enrichment and warehouse loader. Measure freshness.
5. Replay job. Test dashboard atomicity, live isolation and the closed-day gate.

## Assumptions to confirm

- The warehouse supports an idempotent micro-batch load (merge on `event_id` or a load keyed by batch id). If it only supports partition replace, the live loader rebuilds today's partition every few minutes with atomic replace. That is heavier but meets the same constraints.
- The KV store supports atomic set-if-absent with a per-key TTL.
- Collector clocks are synchronized. Skew only shifts events across the day boundary, and live and replay use the same stamped `received_at`.
- SDKs do not retry a 202 that lists rejected events.

## Open questions

- **Suspected bot traffic: drop, or keep with a flag?** Product has not decided, and this plan does not choose. The raw archive keeps everything either way, so the choice can be reversed for 90 days of data. It affects only the bot step in step 5, whether `events_clean` has a flag column, and the replay output. Owner: Product. Decide before the `events_clean` schema is frozen (step 6).
