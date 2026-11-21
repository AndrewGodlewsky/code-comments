# Clickstream ingestion: plan

## What this is

Today there is no pipeline. This plan builds one that takes click and screen-view events from our website and our iOS and Android apps and lands them, deduplicated and enriched, in the warehouse table `events_clean`. The table has one partition per UTC day, and live events must be queryable within 5 minutes of reaching us.

The live path works like this. Clients send batches to a new collector service. The collector stamps each event with the server time and appends it to a replicated log, and only then answers 202. Two independent readers consume that log. The archiver copies every event, duplicates included, to object storage and keeps it 90 days. The live processor drops duplicates, enriches the first copy of each event and loads it into `events_clean`. Once a day is finished, a closer job marks it closed. An operator can then replay a closed day. Replay rebuilds the day from the raw archive, using a new enrichment version, and swaps it in atomically. The log is the buffer, the archive is the permanent record, and `events_clean` can always be rebuilt from the archive.

Items that are undecided or rest on an assumption are marked **OPEN** or **ASSUMPTION** and listed at the end.

## Terms

- **Event:** one click or screen view. It carries a client-generated `event_id` (UUID), a `device_id` and a client timestamp.
- **Batch:** up to 100 events a client sends in one HTTPS request.
- **Collector:** the new service that receives batches over HTTPS.
- **Log:** the existing replicated append-only log (Kafka-style, 14-day retention). `events-raw` is a new topic on it. A topic is split into partitions. Each partition is an ordered list of records, and each record has an offset, which is its position in that partition.
- **In-sync replicas:** the copies of a partition that are fully caught up with its leader. Waiting for all of them means one broker loss cannot lose an acknowledged record.
- **Envelope:** what the collector appends for one event: the original bytes plus `received_at`, collector instance ID, client IP and User-Agent.
- **`received_at`:** the server time the collector stamps on an event. The client timestamp is never used for the day.
- **Day of an event:** the UTC day of the winning copy's `received_at`. It decides the partition and which replay covers the event.
- **Duplicate and winner:** copies of one `event_id` are duplicates. The winner is the copy with the lowest offset in its partition. The winner is the first copy durably accepted, and the others are dropped.
- **Key-value store:** the existing store with per-key TTL. Live dedup uses it.
- **Warehouse:** the existing analytics store. It can atomically replace one day partition of a table.
- **Object storage:** the existing store with lifecycle rules. It holds the raw archive.
- **Enrichment:** adding geo-IP and user-agent fields from the stored client IP and User-Agent.
- **Enrichment version:** one string naming the enrichment code, the geo-IP database version, the user-agent parser version and, if bots are dropped, the bot classifier version. Every `events_clean` row carries it. The brief names no specific geo-IP database or parser.
- **Load ledger:** a small warehouse table owned by the live processor. It records which offset ranges and days the processor has planned and loaded.
- **Closed day:** a day D whose partition no longer takes live writes. It closes after 02:00 UTC on D+1 (see step 5). Only closed days can be replayed.
- **Replay:** an operator-triggered rebuild of one closed day, usually after an enrichment bug fix.

## Fixed rules the design relies on

- **Same-event rule across midnight:** a resend after midnight of an event first received before midnight is a duplicate. It is dropped, and the event stays in its first day.
- **Fixed partition count:** `events-raw` has a fixed number of partitions that never changes. All copies of one `event_id` go to the same partition, so offset order is the order they were durably accepted. A changed count would split copies across partitions and break this. Offsets keep growing across days, so they compare across days within a partition. Changing the count or recreating the topic needs a new plan.
- **Dedup lookback:** 8 days. Clients retry up to 7 days after the first copy, plus at most 5 minutes of backoff, plus margin. The live key lives 8 days. Replay scans days D-8 through D, which reaches back at least as far. Live and replay therefore cannot disagree about an event whose first copy is near 8 days old, provided web clients also stop within about 7 days (assumption 7).
- **Raw retention:** 90 days, longer than the 14-day log retention. The log is never the source for replay.
- **Keep everything accepted:** every accepted event, duplicates included, is kept exactly as received for 90 days.

## How the system runs

### Live path

#### 1. Collector service

Starts on each client HTTPS request. Keeps no data of its own. Everything durable goes to the log.

1. Expose one endpoint for web, iOS and Android. Accept batches of up to 100 events. Reject a larger batch as a whole with a non-retryable 4xx. **ASSUMPTION:** the brief does not say how to handle this.
2. Validate each event on its own. Reject an event if `event_id` or `device_id` is missing, or if it is over 32 KB.
   - Valid events in the same batch are still accepted. List each rejected event with a reason in the response body.
   - Clients never retry rejected events.
   - Rejected events are counted in metrics and not stored, because only accepted events must be kept.
3. Stamp each accepted event with `received_at` from the server clock (UTC), immediately before appending. A resent batch is stamped again on each attempt. Only the first copy durably appended matters, because it wins.
4. Build an envelope for each event: the original bytes untouched, `received_at`, collector instance ID, client IP and User-Agent. Replay needs the IP and User-Agent for enrichment and cannot get them later.
5. Append each envelope to `events-raw`, keyed and partitioned by `event_id`. Use the strongest durability setting: the append is acknowledged only when all in-sync replicas have it.
6. Return **202 only after every accepted event in the batch is acknowledged by the log.**
   - If any append fails or times out (for example a partition is unavailable), return 5xx, or 429 under load. Do not return 202. Other partitions are not affected.
   - On a timeout, 429 or 5xx, the client resends the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events on the device for up to 7 days, so a retry can arrive up to 7 days after the first copy.
   - Events that did get appended are harmless. The resend repeats them and dedup removes the extra copies.
7. Refuse to append an envelope whose `received_at` is more than 60 s old at append time (for example the collector stalled between stamping and appending). Fail the request with 5xx. The client resends like for any 5xx and gets a fresh `received_at`. This bounds how late a record for a finished day can reach the log: any record stamped before 02:00 is in the log by 02:01. Day closing relies on that.

#### 2. Raw archive

Starts when the archiver, a dedicated consumer group on `events-raw`, reads records. It is independent of the live processor. Its data is object storage.

1. Write every envelope, before any dedup or filtering, to object storage as immutable files under `raw/dt=<UTC day of received_at>/hour=<HH>/`.
2. A file holds records of one partition and one hour only. If a consumed range spans hours, write one file per hour. Each record carries `received_at`, log partition and log offset next to the original bytes.
3. Name files by partition, hour and the first and last offset in the file. A re-run that cuts the same range overwrites the same file. If a re-run cuts differently and a record lands in two files, that is harmless, because replay treats records with the same `(partition, offset)` as one.
4. Commit the consumer offset only after the files are durably written. If the archiver crashes, it re-reads and rewrites.
5. A lifecycle rule expires objects 90 days after creation. Files are created after receipt, so no event is deleted before 90 days.
6. Alert on archiver lag at 1 hour and page at 6 hours. The log keeps data only 14 days, so lag beyond that loses raw data.

#### 3. Live deduplication

Starts when the live processor, a separate consumer group on `events-raw`, reads a record. Its data is the key-value store.

1. Do a conditional "set if absent" on the key-value store, keyed by `event_id`. The value is the record's `partition:offset`. The TTL is 8 days from creation and is not refreshed on later hits.
2. Key was absent: this copy is the winner and goes on to enrichment.
3. Key exists and holds this record's own `partition:offset`: treat it as the winner again. This is a redelivery after a crash. Without this check, a crash between writing the key and loading the warehouse would drop the event forever. The same record always gets the same answer, so a re-read range yields the same winners.
4. Key exists with a different value: this copy is a duplicate. Drop it. It stays in the raw archive.
5. If the key-value store is unavailable, pause consumption and do not fail open. Lag grows and alerts fire. The 5-minute target is breached visibly instead of silently producing duplicates.

#### 4. Enrichment and load into `events_clean`

Starts with each winner from dedup. Its data is the load ledger and `events_clean`, both in the warehouse.

1. Run geo-IP lookup and user-agent parsing from the stored IP and User-Agent.
2. Add `enrichment_version` and `received_day` (UTC day of `received_at`). The live processor stamps the version of the code and databases it is deployed with. To change the live version, deploy new code. Replay rebuilds past days with the version the operator names.
3. **OPEN:** the bot-handling stage goes here (see the open decision below). Everything else works with either outcome.
4. Cut the stream into micro-batches per log partition. A batch is a range of offsets and includes records that dedup drops. Close a batch every 60 s or at N records.
   - Before loading, write the batch to the load ledger: one row per UTC `received_day` found among the range's records, each with partition, offset range, day and status `planned`. Days are read from `received_at` before dedup. A batch is identified by partition, offset range and day.
   - The ledger exists because cutting by time or count is not repeatable on its own. After a crash, the processor restarts each partition from the end of its last ledger range, and first retries any `planned` row with exactly the recorded range. It does not cut new batches over that range. Dedup gives the same rows for the same range.
   - Commit the consumer offset only after every ledger row of the range is `loaded` or `dead-lettered`.
5. Load each ledger row (one range, one day) into that day's `events_clean` partition as one warehouse transaction that appends the rows and sets the status to `loaded`. A batch spanning midnight makes two separate loads. A row already `loaded` is skipped on retry, so rows are never inserted twice.
   - If that day is already closed, do not load. Send the rows to the dead-letter location (see day closing) and set the status to `dead-lettered`. Other days of the range load normally.
   - **ASSUMPTION:** the warehouse supports transactional appends to a single day partition together with a ledger update. Confirm before building. The brief guarantees only atomic partition replace.
6. Latency budget for the 5-minute target: collector to log under 1 s; processor under 10 s; micro-batch wait up to 60 s; warehouse load and visibility up to 120 s; slack about 100 s.
7. Alert when the age of the oldest unloaded winner exceeds 3 minutes.

#### 5. Day closing

Starts on a schedule: a closer job run by the platform team's scheduler. Its data is a `closed` marker ledger.

1. Day D closes no earlier than 02:00 UTC on D+1. Closing needs all of these:
   - the clock is past 02:01 (02:00 plus the 60 s bound from the collector);
   - the job has taken a snapshot, at or after 02:01, of the end offset of every `events-raw` partition;
   - the archiver has committed past every snapshot offset, and the load ledger shows every row up to those offsets as `loaded` or `dead-lettered`. Nothing for D is then in flight.
2. If a check fails, the day stays open, the job retries and an alert fires. Closing never happens on the clock alone.
3. On close, write a `closed` marker for D to a ledger. Replay checks it.
4. After close, the live loader refuses to write to that partition. A late record whose `received_at` is in a closed day goes to the dead-letter location, `dead-letter/dt=<day>/` in object storage, which holds the enriched rows that were refused, and raises an alert.
   - The on-call operator reads the alert. The 60 s rule and the closing check should make this impossible, so any record there is an incident to investigate. Which team is on call is not stated in the brief.
   - The event is not lost. It is in the raw archive, so a replay of that day puts it into `events_clean`.
   - Late duplicates of old events are dropped by dedup and never touch a closed partition.
   - Because no live load for D can be in flight at close, a replay swap never races with a live load.
5. **ASSUMPTION:** collector clocks are time-synchronised (NTP), so the 60 s bound is meaningful.

#### 6. Live-path operations

1. Scale collector instances on request rate. Scale processor and archiver by log partition count.
2. Size the key-value store for 8 days of unique `event_id`s. **Input needed:** daily event volume, which the brief does not give.
3. Build dashboards and alerts for: collector 202 and reject rates; append latency; archiver lag; processor lag; dedup drop rate; freshness of `events_clean`; dead-letter count.

### Replay

#### 7. Triggering a replay

Starts when an operator submits a day D and an enrichment version, normally new code or a new geo-IP database. The replay job runs with that version's code and databases. Its data is a per-day lock and a run ledger.

1. Refuse the request unless all hold:
   - D has the `closed` marker;
   - D is no older than 82 days (90 days of raw retention minus the 8-day lookback), so the full lookback still exists in the archive;
   - no other replay holds the lock for D.
2. Take a per-day lock and create a run ID. Different days may replay in parallel, up to a small cap.

#### 8. Rebuild (isolated from live)

1. Run on separate compute from the collector and live processor.
2. Read only from the raw archive in object storage. Do not read the log and do not join the live consumer groups.
3. Rate-limit reads and cap concurrency, so replay cannot take bandwidth or warehouse capacity from live ingestion.
4. **Replay never reads or writes the key-value store.** It builds its own dedup from the archive, so live dedup state is untouched.
5. Read raw for days D-8 through D. Treat records with the same `(partition, offset)` as one record. For each `event_id`, pick the copy with the lowest `(partition, offset)`. Keep the event only if that winning copy has `received_at` in day D.
   - An event first received on D-3 and resent on D is dropped, as it was live.
   - A resend on D+2 of an event first received on D is outside the scan. It is a duplicate and not in the result, as it was live.
   - This gives the same winners as live dedup, because both use log order.
6. Enrich the winners with the chosen version, from the stored IP and User-Agent.
7. Apply the same bot policy as live, whichever way the open decision goes. The policy is part of the enrichment version.
8. Write the result to a staging table or location named by the run ID. Dashboards cannot see it.

#### 9. Validate, then swap

1. Validate the staging data. Fail the run if any of these is true:
   - `event_id` is not unique;
   - any `received_at` falls outside day D;
   - the row count differs from the number of winners computed from raw (after the bot policy, if it drops rows);
   - the row count differs from the current live partition by more than a threshold, apart from changes explained by the enrichment fix.
2. On failure no swap happens, so the live partition for D is untouched. Mark the run `failed` with the reason in the run ledger, notify the submitting operator, fire an alert and release the lock so the operator can fix the cause and resubmit. Staging data stays for inspection until its retention window ends.
3. Copy the current partition D to object storage as a backup.
4. Use the warehouse's atomic single-partition replace to swap staging into `events_clean` for D. Readers see the old data or the new data, never a partial rebuild. Live ingestion cannot be writing to D, because D is closed.
5. Record the run in the run ledger: run ID, operator, enrichment version, status, row counts before and after, and swap time.
6. To roll back, atomically replace the partition with the backup.
7. Delete the staging data after a retention window. Release the lock on success or failure.

### What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Collector | Malformed event | Rejected alone and listed in the response. The rest of the batch is accepted. |
| Collector | Batch over 100 events | Whole batch rejected with a non-retryable 4xx. |
| Collector | Append fails or times out | 5xx or 429. Client resends. Extra copies are removed by dedup. |
| Collector | Envelope stale by more than 60 s | 5xx. Client resends and gets a fresh `received_at`. |
| Archiver | Crash or lag | Offset not committed, so it re-reads and overwrites the same files. Alert at 1 hour, page at 6. |
| Dedup | Key-value store unavailable | Consumption pauses. Lag alerts fire. No duplicates are let through. |
| Processor | Crash before load | Restart retries `planned` ledger rows with the recorded range. Winners are the same, and the load is one transaction, so the event lands once. |
| Load | Day already closed | Rows go to dead-letter, an alert fires, and the replay of that day recovers them. |
| Closing | Check fails | Day stays open, job retries, alert fires. |
| Replay | Validation fails | No swap. Run marked failed, operator told, lock released. |
| Replay | Bad swap result | Roll back from the backup. |

## How we build and roll it out

### 10. Safety checks

1. Acceptance test, before first use and on every enrichment-code change: replay a recent closed day with the enrichment version unchanged. The result must equal the live partition row for row. This proves replay dedup matches live dedup.
2. Load test: replay a large day while live runs at full traffic. Live freshness must stay under the 5-minute target.
3. Closing test: delay the processor past 02:00. The day must stay open.
4. Crash test: kill the processor after a batch is `planned` but before it is `loaded`. After restart, `events_clean` must hold each event exactly once.

### 11. Order of work

1. Collector and log topic, with the stamping, validation and 202 rules.
2. Archiver, so raw data is kept from day one.
3. Key-value dedup and the live processor, with the redelivery handling.
4. Load ledger, load into `events_clean` and the freshness alerts.
5. Day closing.
6. Replay, then the acceptance and load tests.
7. Mobile and web clients send to the new endpoint with the retry behaviour already specified.

## Open questions

### OPEN: suspected bot traffic

Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose. **Decision needed from product** before the bot stage is built. The rest of the plan is not blocked.

- The raw archive keeps every accepted event either way, as required.
- Only `events_clean` is affected, and only in the bot stage of live enrichment.
- Dedup runs before the bot stage in both cases, so dedup behaviour does not change.
- **If dropped:** bot events are absent from `events_clean`. Row counts in replay validation must account for them. The bot classifier's version becomes part of the enrichment version, because replay would change which rows exist.
- **If kept with a flag:** add an `is_suspected_bot` column. Dashboards must filter on it. Row counts do not change.

### Assumptions to confirm

1. The key-value store supports an atomic set-if-absent with a per-key TTL.
2. The warehouse supports transactional appends into a single day partition (with the ledger update in the same transaction), plus atomic partition replace.
3. The log supports acknowledgement from all in-sync replicas and partitioning by key, with order kept within a partition.
4. Daily event volume is unknown. It is needed to size the key-value store, the log partitions and the replay compute.
5. A batch of more than 100 events is rejected as a whole and not retried. The brief does not state this.
6. Collector clocks are synchronised closely enough for the 60 s bound.
7. How long web clients keep retrying is not stated. Only the mobile 7-day buffer is. The 8-day lookback assumes web clients also stop within about 7 days.
8. The brief does not name the geo-IP database or user-agent parser, or say how their versions are deployed. This plan assumes each is versioned and bundled into the enrichment version.
9. Which team is on call for the dead-letter alert is not stated.
