# Clickstream ingestion: plan for `events_clean`

**Goal.** Collect click and screen-view events from our website and our iOS and Android apps. Remove duplicates, add enrichment (location from the IP address, browser and device details from the User-Agent header), and store the result in the warehouse table `events_clean`. That table has one partition per UTC day. An event's day is the UTC date on which our collector received it. Live events must be queryable within 5 minutes of arrival. An operator can also rebuild one closed day. This rebuild is called a **replay**.

**The flow in brief.**

```
Clients --HTTPS batches--> Collector --appends--> Replicated log (clickstream.raw)
                                                    |                    |
                                              Archiver               Deduplicator
                                     (keeps a 90-day copy)     (writes events_clean)
```

- **Clients** (website, iOS, Android) send batches of events to the collector.
- **The collector** writes every accepted event to the replicated log before it answers the client.
- **The archiver** reads the log and keeps a 90-day copy of every event, duplicates included.
- **The deduplicator** reads the log and writes the clean table, keeping only the first copy of each event.
- **A replay** rebuilds one closed day from the archive and the ledger. It never touches live deduplication state.

## Terms used in this plan

- **Event:** one click or screen view. Each event has a client-generated `event_id` (a UUID), a `device_id`, and a timestamp set by the client (the **client timestamp**).
- **Batch:** up to 100 events sent together in one HTTPS request.
- **Collector:** the new service that receives batches from clients.
- **Replicated log (`clickstream.raw`):** a durable, append-only stream of records. It is split into numbered lanes called **partitions** (these are log partitions, not warehouse partitions). Each record has a position within its log partition, called an **offset**. Records are kept for 14 days.
- **Consumer group:** a named set of readers that share the work of reading a log. Different groups read the same log independently, and each keeps its own position in it.
- **Acks = all:** a write counts as successful only after every copy (replica) of the log has stored it.
- **Idempotent producer:** a writer whose retries do not create duplicate log records.
- **Key-value store:** a fast lookup store where each key can expire after a set time. That time limit is the key's **TTL** (time to live).
- **Warehouse:** the analytics database. It can replace one whole day partition in a single atomic step, so readers see either the old data or the new data, never a mix.
- **Enrichment:** adding derived fields, such as location from an IP address. It uses pinned database versions, so the same input always gives the same output.
- **Watermark:** for each log partition, the offset up to which a process has finished its work.
- **Manifest:** a file that lists the offset ranges the archiver has written for a day.
- **Shadow table:** a temporary table that holds a replay's output before it replaces the real partition. Dashboards never read it.
- **Closed day:** a UTC day D becomes closed at 02:00 UTC on D+1. Only closed days can be replayed.

## Names used in this plan

- `clickstream.raw`: the replicated log, keyed by `event_id`, kept 14 days.
- `archive`: object storage under `raw/received_day=YYYY-MM-DD/`. Objects expire 90 days after they are created.
- `dedup:{event_id}`: a key-value key with an 8-day TTL. The TTL is the brief's 7-day retry window plus one day of margin. It is written once, when the first copy is processed. Later copies never refresh it.
- `dedup_ledger`: a warehouse table with one row per `event_id`. It records the first copy: its log partition, its log offset, and its received day. It is kept 90 days, so a replay makes the same first-copy decisions that live processing made.
- `events_clean`: the warehouse table, partitioned by the received day of the first copy.
- `events_clean_rebuild_D`: the shadow table for a replay of day D.

## Part A: Live path

Each step below runs for every batch, in this order.

1. **Receive the batch.** The collector accepts HTTPS batches of up to 100 events. Each event is at most 32 KB, so a batch is at most about 3.2 MB. Requests much larger than that are refused before parsing. This is a safety limit in the implementation. It is not part of the brief's contract, and it is not a per-event rejection.

2. **Check each event on its own.** An event is malformed if any of these is true:
   - `event_id` is missing or empty.
   - `device_id` is missing or empty.
   - Its serialized form is over 32 KB.

   Each malformed event goes onto a **rejected list**, with its position in the batch and a reason. The other events in the batch continue through the steps. Malformed events are not stored. (Open item 3 covers one case the brief does not list.)

3. **Set the time and the day.** Read the collector's UTC clock once per request. Set `received_at` on every accepted event to that value. An event's day is the UTC date of its `received_at`. Client timestamps are stored as data only. They never decide the partition or which replay covers the event.

4. **Store the batch durably before answering.** Append every accepted event to `clickstream.raw`, duplicates included. Use `event_id` as the key, acks = all, and an idempotent producer. Each record holds:
   - the event's exact received JSON bytes, and
   - an envelope with `received_at`, `collector_id`, `batch_id`, the client IP, and the User-Agent header.

   Enrichment needs the IP and the User-Agent, which is why they are kept. The log assigns each record its log partition and offset when it is appended. The archiver copies those values into the archive.

5. **Respond.** Return 202 only after the log confirms the append. The response body includes the rejected list. If the append fails or times out, return 5xx or 429 for the whole batch. Clients then resend the same `event_id`s. Resending is safe, because step 7 drops copies that are already known. Clients never retry rejected events.

6. **Archive for 90 days (its own consumer group).** The archiver reads `clickstream.raw` and writes files under `archive/raw/received_day=D/log_partition=P/`. Each record becomes one envelope line, which also includes its log partition and offset. Each day, the archiver writes a manifest listing the offset range it has archived for each log partition. Objects expire 90 days after they are created. An object is always created after the `received_at` of the records in it, so each record stays for at least its full 90 days. Alert when archiver lag exceeds 1 day. Log retention is 14 days, so lag must never come close to that.

7. **Deduplicate (consumer group `dedup-live`, partitioned by `event_id`).** Each `event_id` is handled by exactly one consumer, so its copies are processed in log order. For each event:
   1. Read `dedup:{event_id}`.
   2. If the key exists, this is a later copy. Do not write it to `events_clean`. The archive already holds it, so nothing is lost.
   3. If the key does not exist, this is the first copy. Continue to steps 8 and 9. The key is written only after the output is durable (step 9.3). If the process crashes before that, no key exists, so the event is processed again.

8. **Enrich.** Run the geo-IP lookup and the User-Agent parse, using pinned database versions. Enrichment reads only the archived envelope and body. It never reads clocks or live services, so a replay can reproduce its output exactly. Each row stores `enrichment_version` and the database versions used. There is a reserved slot for bot classification at this step. The slot stays empty until open item 1 is decided.

9. **Write in micro-batches** (every 60 seconds or every 1,000 rows, whichever comes first):
   1. Insert-if-absent into `dedup_ledger`: `event_id`, `first_received_at`, `first_log_partition`, `first_log_offset`, `day`. Existing rows are never overwritten.
   2. MERGE into `events_clean` on `event_id`, in the partition for the received day of the copy being written.
   3. After both writes succeed, set `dedup:{event_id}` with an 8-day TTL.

10. **Latency budget.** The steps add up roughly as follows:
    - collector, about 1 s
    - log append, about 1 s
    - deduplication and enrichment, a few seconds
    - micro-batch wait, up to 60 s
    - warehouse commit

    The target is p99 under 3 minutes. Alert at 4 minutes, so on-call response starts before the 5-minute promise is at risk.

11. **Monitor.** Track:
    - rejects, by reason
    - key-value hit rate
    - deduplication and archiver lag
    - copies arriving more than 7 days after their first copy (any such copy means a client broke the retry contract)
    - each day's live row count, compared with the `dedup_ledger` count for that day

    The last check is an early warning of live drift. It catches problems before anyone runs a replay.

## Part B: Replay one closed day

A replay rebuilds one closed UTC day D of `events_clean`, usually after an enrichment fix. A replay never touches live deduplication state. It does not read or write the key-value store, does not read the log, does not create consumer groups, and does not write to `dedup_ledger`. It reads only the archive and the ledger.

**R1. Request and preconditions.** The operator names day D and the enrichment version to rebuild with. Refuse the request unless all of these hold:
1. D is closed: the current time is at or after D+1 02:00 UTC.
2. Live ingestion has passed D+1 02:00 UTC on every log partition, so no live writes for D are still pending. The length of this grace period depends on open item 6.
3. The archive for D is sealed. Its manifests exist, and the archiver has passed the live watermark on every partition.
4. D is within 90 days, so the archive and the ledger still hold it.
5. No other rebuild of D is running. Take a lock per day.

**R2. Select the first copies.** Read only archive records whose `received_at` falls on D. Join them to `dedup_ledger` on `event_id`. Keep a record only if its (log partition, log offset) equals the ledger's first copy. This does two things:
- It drops the later copies that arrived on D.
- It drops copies of events whose first copy arrived on an earlier day.

The result is exactly the set of events whose first copy arrived on D. Live processing also picks the first copy by log offset, so the live path and the replay agree.

Why use the ledger instead of the archive to decide? The first-copy history can reach back 7 days before a given copy, but the archive keeps only 90 days. For a day near the end of its window, earlier copies may already be gone from the archive. The ledger lasts as long as the replay window, so every decision is still available.

**R3. Re-enrich into the shadow table.** Write the kept records into `events_clean_rebuild_D` with the new `enrichment_version`. Use only envelope and body data from the archive. The shadow table is invisible to dashboards.

**R4. Validate before the swap.** If any check fails, abort and leave `events_clean` untouched.
1. The shadow row count equals the number of `dedup_ledger` rows with day = D. A mismatch means the archive has a gap.
2. `event_id` is unique in the shadow table.
3. Every row has the new `enrichment_version` and non-null required fields.
4. Compare the shadow table with the current partition. Count the rows added, the rows removed, and the changed fields. Save this as the run report. Changes in membership should be explained by live lag or late copies. A person reviews them.

**R5. Swap atomically.** Replace partition D of `events_clean` with the contents of the shadow table, in one warehouse operation (the atomic partition replace). Dashboards read the old partition until the swap, and the new one afterward. They never see a partly rebuilt day. Then drop the shadow table.

**R6. Record the run.** Store the run ID, D, the enrichment version, the manifest versions, the ledger snapshot time, the row counts, the diff summary, and the requester.

**R7. Isolate from live ingestion.** Run replays on their own compute queue, with at most one rebuild at a time and a lower priority than live ingestion. A replay's only warehouse writes are to the shadow table and the single swap. Live ingestion keeps its own queue.

**R8. Replay window.** Day D can be replayed only while its archive and ledger rows still exist, which is up to 90 days after D. R1.4 enforces this. After that, the day cannot be rebuilt, and its partition stays as it was last written.

**R9. Fixes ship as code.** Deploying an enrichment fix changes live events immediately. The current open day cannot be replayed until it closes. Each closed day that was written with the old version must be rebuilt by replay.

## Failure cases the design covers

- **Crash after receipt but before the log acknowledges.** No 202 is sent. The client retries with the same IDs, and deduplication absorbs the repeats.
- **Crash after step 9.1 or 9.2 but before 9.3.** No key-value key exists, so the batch is processed again. The insert-if-absent into the ledger and the MERGE on `event_id` absorb the repeats.
- **Late copy arriving after the 8-day TTL.** Live processing treats it as a first copy and writes it to the partition for its own received day. The ledger keeps the original first-copy row. The extra row stays in that partition until the affected day is replayed, and replay removes it through R2. Any such copy means a client broke the retry contract, so the affected day should be replayed once it closes.
- **Archive gap for D.** The count check in R4.1 fails, and nothing is published.
- **Clock skew across collectors.** When two copies of one event reach different collectors, their `received_at` order can disagree with their log order. Both paths choose the first copy by log order, so they agree. The event's partition is the received day of that first copy.

## Open items (not decided)

1. **Suspected bot traffic: drop, or keep with a flag.** Product has not decided. The plan keeps a slot in step 8 that fits either outcome, and it does not choose between them. The archive keeps every accepted copy either way. If the bot rule is deterministic from archived data, a replay can apply a changed decision within the 90-day window. Product must decide before the bot rule ships.
2. **Response when every event in a batch is rejected.** The plan assumes 202 with the full rejected list, since the brief ties 202 to durable storage and nothing needs storing. Confirm.
3. **Non-UUID `event_id`.** The brief's list of malformed conditions does not include this case. The plan therefore accepts such events and deduplicates them as strings. Confirm.
4. **Retention of `events_clean` partitions.** The brief does not say how long they are kept.
5. **Client IP and User-Agent in the archive.** Enrichment needs them, so the plan keeps them for the same 90 days. Confirm the privacy treatment.
6. **Maximum time from collector receipt to log append.** This sets the grace period after 02:00 before a day can be replayed. The brief does not give a value.

## Assumptions to verify

- **Key-value store:** per-key TTL works as described. Because each `event_id` has one owning consumer, get-then-set is safe. If a rebalance causes two consumers to overlap, output cannot be duplicated, because both warehouse writes are idempotent.
- **Warehouse:** it supports frequent micro-batch writes, MERGE (for both the ledger and `events_clean`), and the atomic partition replace described above. It also needs a separate compute queue for replays.
- **Log:** it supports keyed partitions, acks = all, and an idempotent producer.
- **Object storage:** lifecycle expiry counts from the object's creation time.