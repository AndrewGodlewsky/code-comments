# Clickstream ingestion: plan

This plan covers the live path (steps 1-6), replay (steps 7-10) and rollout (step 11). Items that are not decided, or that rest on assumptions, are marked **OPEN** or **ASSUMPTION** and collected in steps 12 and 13.

## Fixed rules the design relies on

- **Day of an event:** the UTC day of the winning copy's `received_at`.
- **Winner among duplicates:** the copy with the lowest log offset within its `event_id` partition. All copies of one `event_id` go to the same partition, so offset order is the order in which the copies were durably accepted.
- **Dedup lookback:** 8 days. Clients can retry up to 7 days after the first copy, plus a maximum 5-minute backoff, plus margin.
- **Raw retention:** 90 days, which is longer than the 14-day log retention. The log is therefore never the source for replay.

## Live path

### 1. Collector service

1. Expose one HTTPS endpoint for web, iOS and Android. Accept batches of up to 100 events.
   - Reject a batch of more than 100 events as a whole with a non-retryable 4xx. **ASSUMPTION:** the brief does not say how to handle this.
2. Validate each event on its own.
   - Reject an event if `event_id` or `device_id` is missing, or if it is over 32 KB.
   - Valid events in the same batch are still accepted. List the rejected events, with a reason each, in the response body.
   - Rejected events are counted in metrics. They are not stored, because only accepted events must be kept.
3. For each accepted event, stamp `received_at` from the server clock (UTC), immediately before appending to the log.
4. Build a raw envelope for each event. It holds:
   - the original event bytes, untouched;
   - `received_at`;
   - the collector instance ID;
   - the client IP and the User-Agent header, because replay needs them for geo-IP and user-agent enrichment and cannot get them later.
5. Append each envelope to the `events-raw` log topic.
   - Key and partition by `event_id`.
   - Use the strongest durability setting: acknowledgement from all in-sync replicas.
6. Return **202 only after every accepted event in the batch is acknowledged by the log.**
   - If any append fails or times out, return 5xx (or 429 under load) and do not return 202.
   - Events that did get appended are harmless. The client resends the same `event_id`s and dedup removes the extra copies.
7. Refuse to append an envelope whose `received_at` is more than 60 s old at append time. Fail the request with 5xx instead.
   - This bounds how late a record for a finished day can reach the log, which the day-closing check in step 5 relies on.

### 2. Raw archive (all accepted events, duplicates included)

1. Run a dedicated archiver consumer group on `events-raw`. It is independent of the live processor.
2. It writes every envelope, before any dedup or filtering, to object storage as immutable files.
   - Path prefix: `raw/dt=<UTC day of received_at>/hour=<HH>/`.
   - Each record carries `received_at`, log partition and log offset next to the original bytes.
   - File names are derived from partition and offset range, so a re-run overwrites the same file instead of adding a copy.
3. Commit the consumer offset only after the file is durably written.
4. Add a lifecycle rule that expires objects 90 days after creation. Files are created after receipt, so no event is deleted before 90 days.
5. Alert on archiver lag at 1 hour, and page at 6 hours. The log keeps data for only 14 days, so any lag beyond that loses raw data.

### 3. Live deduplication

1. The live processor is a separate consumer group on `events-raw`.
2. For each record, do a conditional "set if absent" on the key-value store, keyed by `event_id`.
   - The value is `partition:offset` of the copy that won.
   - The TTL is 8 days from creation. Do not refresh the TTL on later hits.
3. If the key was absent, this copy is the winner and goes on to enrichment.
4. If the key exists and its value is this record's own `partition:offset`, treat it as the winner again. This is a redelivery after a crash, and it makes processing safe to retry.
   - Without this check, a crash between writing the key and loading the warehouse would drop the event forever.
5. If the key exists with a different value, this copy is a duplicate and is dropped. It stays in the raw archive.
6. If the key-value store is unavailable, pause consumption. Do not fail open. Lag grows and alerts fire, and the 5-minute target is breached visibly instead of silently producing duplicates.

### 4. Enrichment and load into `events_clean`

1. For each winner, run geo-IP lookup and user-agent parsing from the stored IP and User-Agent.
2. Add the fields `enrichment_version` and `received_day` (UTC day of `received_at`).
3. **OPEN (step 12):** the bot-handling stage goes here. Everything else in this plan works with either outcome.
4. Group output into micro-batches, closed every 60 s or at N records.
   - Each batch has a deterministic ID: log partition plus offset range.
   - Record the batch ID in a load ledger before loading.
5. Load each batch into `events_clean`, into the partition for each row's `received_day`, so a batch spanning midnight is split by day.
   - The load is idempotent per batch ID. A retried batch cannot insert its rows twice.
   - **ASSUMPTION:** the warehouse supports transactional appends to a single day partition. Confirm this before building. Only atomic partition replace is guaranteed by the brief.
6. Latency budget for the 5-minute target:
   - collector to log: under 1 s;
   - processor: under 10 s;
   - micro-batch wait: up to 60 s;
   - warehouse load and visibility: up to 120 s;
   - slack: about 100 s.
7. Alert when the age of the oldest unloaded winner exceeds 3 minutes.

### 5. Day closing

1. Day D closes at 02:00 UTC on D+1. Closing needs both of these to be true:
   - the clock is past 02:00;
   - both consumer groups have processed every record appended before 02:00, so that nothing for day D is still in flight.
2. If the second check fails, the day stays open and an alert fires. Closing never happens on the clock alone.
3. On close, write a `closed` marker for D to a ledger. Replay checks this marker.
4. After a day is closed, the live loader refuses to write to that partition. A late record with `received_at` in a closed day goes to a dead-letter location and raises an alert.
   - Step 1.7 should make this impossible.
   - Duplicates of old events arriving later are not a problem. They are dropped by dedup and never touch a closed partition.

### 6. Live-path operations

1. Scale collector instances on request rate. Scale processor and archiver by log partition count.
2. Size the key-value store for 8 days of unique `event_id`s. **Input needed:** daily event volume, which the brief does not give.
3. Dashboards and alerts to build:
   - collector 202 and reject rates;
   - append latency;
   - archiver lag;
   - processor lag;
   - dedup drop rate;
   - freshness of `events_clean`;
   - dead-letter count.

## Replay

### 7. Triggering a replay

1. An operator submits the day D to rebuild and the enrichment version to use, normally the new code or geo-IP database.
2. Refuse the request unless all of these hold:
   - D has the `closed` marker from step 5;
   - D is no older than 82 days (90 days of raw retention minus the 8-day dedup lookback), so the full lookback still exists;
   - no other replay holds the lock for D.
3. Take a per-day lock and create a run ID. Different days may replay in parallel, up to a small cap.

### 8. Rebuild (isolated from live)

1. Run on separate compute from the collector and live processor.
2. Read only from the object-storage raw archive. Do not read the log and do not join the live consumer groups.
3. Rate-limit reads and cap concurrency, so replay cannot take bandwidth or warehouse capacity from live ingestion.
4. **The replay never reads or writes the key-value store.** It builds its own dedup from the raw archive.
5. To dedup, read raw for days D-8 through D. For each `event_id`, pick the copy with the lowest `(partition, offset)`.
   - Keep the event only if that winning copy has `received_at` in day D.
   - An event first received on D-3 and resent on D is dropped, as it was live.
   - A resend on D+2 of an event first received on D is not in the D-8..D scan. It is a duplicate and not in the result, as it was live.
   - This rule gives the same winners as live dedup in step 3, because both use log order.
6. Enrich the winners with the chosen enrichment version, from the stored IP and User-Agent.
7. Apply the same bot policy as live, whichever way step 12 is decided. The policy is part of the enrichment version.
8. Write the result to a staging table or location named by the run ID. It is not visible to dashboards.

### 9. Validate, then swap

1. Validate the staging data before any swap. Fail the run on any of these:
   - `event_id` is not unique;
   - any `received_at` falls outside day D;
   - the row count differs from the number of winners computed from raw (after the bot policy, if it drops rows);
   - the row count differs from the current live partition by more than a threshold, apart from changes explained by the enrichment fix.
2. Copy the current partition D to object storage as a backup, so the swap can be reversed.
3. Use the warehouse's atomic single-partition replace to swap staging into `events_clean` for D.
   - Readers see the old data or the new data, never a partial rebuild.
4. Record the run in a ledger: run ID, operator, enrichment version, row counts before and after, and swap time.
5. Roll back by atomically replacing the partition with the backup from step 9.2.
6. Delete the staging data after a retention window. Release the lock.

### 10. Replay safety checks

1. Run one acceptance test before first use and on every enrichment-code change. Replay a recent closed day with the enrichment version unchanged. The result must equal the live partition row for row. This proves the replay dedup matches the live dedup.
2. Run a load test with a replay of a large day running at full live traffic. Live freshness must stay under the 5-minute target.
3. Test the day-closing check by delaying the processor past 02:00. The day must stay open.

## Rollout

### 11. Order of work

1. Collector and log topic, with the stamping, validation and 202 rules.
2. Archiver, so raw data is kept from day one.
3. Key-value dedup and the live processor, with the redelivery handling from step 3.4.
4. Load into `events_clean` and the freshness alerts.
5. Day closing.
6. Replay, then the acceptance and load tests from step 10.
7. Mobile and web clients send to the new endpoint with the retry behaviour already specified.

## Open decisions and assumptions

### 12. OPEN: suspected bot traffic

Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose.

- The raw archive keeps every accepted event either way, as required.
- Only `events_clean` is affected, and only in the bot stage of step 4.3.
- **If dropped:**
  - bot events are absent from `events_clean`;
  - row counts in step 9 must account for them;
  - the bot classifier's version and any change to it become part of the enrichment version, because replay would change which rows exist.
- **If kept with a flag:**
  - add an `is_suspected_bot` column;
  - dashboards must filter on it;
  - no row-count changes.
- Dedup runs before the bot stage in both cases, so the choice does not change dedup behaviour.
- **Decision needed from product** before the bot stage is built. The rest of the plan is not blocked.

### 13. Assumptions to confirm

1. The key-value store supports an atomic set-if-absent with a per-key TTL.
2. The warehouse supports transactional appends into a single day partition, plus atomic partition replace.
3. The log supports acknowledgement from all in-sync replicas and partitioning by key, with order kept within a partition.
4. Daily event volume is unknown. It is needed to size the key-value store, the log partitions and the replay compute.
5. A batch of more than 100 events is rejected as a whole and not retried. The brief does not state this.
