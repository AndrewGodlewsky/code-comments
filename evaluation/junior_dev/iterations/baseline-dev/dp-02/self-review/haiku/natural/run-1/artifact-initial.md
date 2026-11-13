# Clickstream ingestion: plan for `events_clean`

Scope: click and screen-view events from the website and the iOS and Android apps are collected, deduplicated and enriched, and landed in `events_clean`, one partition per UTC day of `received_at`. Live events must be queryable within 5 minutes. An operator can rebuild one closed UTC day by replay.

## Names used in this plan

- `clickstream.raw`: replicated log, keyed by `event_id`, 14-day retention.
- `archive`: object storage under `raw/received_day=YYYY-MM-DD/`, lifecycle expiry 90 days after object creation.
- `dedup:{event_id}`: key-value keys with an 8-day TTL. The TTL is the brief's 7-day retry window plus one day of margin. It is set once and never refreshed by later copies.
- `dedup_ledger`: warehouse table with one row per event_id recording the first copy (log partition, log offset, received day). Kept 90 days so replay can make the same first-copy decisions as live.
- `events_clean`: warehouse table partitioned by received day of the first copy.
- `events_clean_rebuild_D`: shadow table for one replay. Dashboards never read it.

## Part A: Live path

1. **Receive the batch.** The collector accepts HTTPS batches of up to 100 events. At the 32 KB event limit a batch is at most about 3.2 MB, so requests far beyond that are refused before parsing. That refusal is an implementation guard outside the brief's contract, not a per-event rejection.

2. **Validate each event on its own.** An event is malformed if `event_id` or `device_id` is missing or empty, or if its serialized form is over 32 KB. Each malformed event goes into a rejected list with its batch index and a reason. The other events in the batch continue. The brief defines malformed only by these three conditions (see open item 3).

3. **Stamp time and choose the partition.** Read the collector's UTC clock once per request and set `received_at` on every accepted event from that value. The event's day is the UTC date of `received_at`. Client timestamps are stored as data only. They never decide the partition or the replay that covers the event.

4. **Make the batch durable before answering.** Append every accepted event, duplicates included, to `clickstream.raw` with key = `event_id`, acks = all, and an idempotent producer. Each record carries the event's exact received JSON bytes and an envelope with `received_at`, `collector_id`, `batch_id`, client IP and User-Agent header (both needed by geo-IP and UA enrichment). The log partition and offset are assigned at append, so the archiver adds them when it writes the archive.

5. **Respond.** Return 202 only after the log acknowledges the append, with the rejected list in the body. If the append fails or times out, return 5xx or 429 for the whole batch. Clients resend the same `event_id`s. This is safe because step 7 drops the copies that are already known. Clients never retry rejected events, and the rejected events are not stored.

6. **Archive for 90 days (separate consumer group).** The archiver reads `clickstream.raw` and writes files under `archive/raw/received_day=D/log_partition=P/`. Each record is one envelope line with its log partition and offset. The archiver also writes a daily manifest listing the offset range it has archived per log partition. Lifecycle expiry is 90 days after object creation. Creation never happens before `received_at`, so no record expires before its 90 days are up. Alert when archiver lag passes 1 day. Log retention is 14 days, so lag must never reach that.

7. **Deduplicate (consumer group `dedup-live`, partitioned by `event_id`).** Each `event_id` has one owning consumer, so its copies are processed in log order. For each event:
   1. Read `dedup:{event_id}`. If it exists, this is a later copy. Drop it from `events_clean`. The archive already holds it.
   2. If it does not exist, this is the first copy. Continue with steps 8 and 9. The key is written only after the output is durable (step 9c). A crash therefore leaves no key, and the event is reprocessed.

8. **Enrich.** Run the geo-IP lookup and UA parse against pinned database versions. Enrichment reads only the archived envelope and body. It never reads clocks or live services, so replay can reproduce it. Each row stores `enrichment_version` and the database versions used. Bot classification has a reserved slot here, which stays open (open item 1).

9. **Write in micro-batches** (about every 60 seconds or 1,000 rows, whichever comes first):
   1. Insert-if-absent into `dedup_ledger`: `event_id`, `first_received_at`, `first_log_partition`, `first_log_offset`, `day`. Existing rows are never overwritten.
   2. MERGE into `events_clean` on `event_id` in the day partition of the first copy.
   3. After both writes succeed, set `dedup:{event_id}` with an 8-day TTL.

10. **Latency budget.** Collector about 1 s, log append about 1 s, dedup and enrichment a few seconds, micro-batch up to 60 s, warehouse commit. Target p99 under 3 minutes. Alert at 4 minutes so the on-call response starts before the 5-minute promise is at risk.

11. **Monitor.** Track rejects by reason, key-value hit rate, dedup and archiver lag, and each day's live row count against the `dedup_ledger` count for that day. The last check is an early warning of live drift, before anyone runs a replay.

## Part B: Replay one closed day

Replay never touches live dedup state. It does not read or write the KV store, does not read the log, does not create consumer groups, and does not write to `dedup_ledger`.

1. **Request and preconditions.** The operator names a day D and the enrichment version to rebuild with. Refuse unless all of these hold:
   1. D is closed: current time is at or after D+1 02:00 UTC.
   2. The live watermark has passed D+1 02:00 UTC on every log partition, so no live writes for D are pending. The grace needed for in-flight appends depends on open item 6.
   3. The archive is sealed for D: manifests exist and the archiver has passed the live watermark on every partition.
   4. D is still within 90 days, so both the archive and the ledger still hold it.
   5. No other rebuild of D is running. Take a lock per day.

2. **Select the first copies.** Read only archive records whose `received_at` falls on D. Join them to `dedup_ledger` on `event_id` and keep a record only if its (log partition, log offset) equals the ledger's first copy. Later copies on D are dropped, and so are copies of events whose first copy came on an earlier day. The result is exactly the events first received on D. Live uses the same rule, since it also picks the first copy by log offset.
   - Why the ledger and not the archive: first-copy history can reach back 7 days before a copy, and the archive keeps only 90 days. For a day near the end of its window, earlier copies may already be gone from the archive. The ledger lasts as long as the day's replay window, so every decision stays available.

3. **Re-enrich into the shadow table.** Write the kept records into `events_clean_rebuild_D` with the new `enrichment_version`, using envelope data only. The shadow table is invisible to dashboards.

4. **Validate before the swap.** If any check fails, abort and leave `events_clean` untouched.
   1. The shadow row count equals the count of `dedup_ledger` rows with day = D. A mismatch means the archive has a gap.
   2. `event_id` is unique in the shadow table.
   3. Every row has the new `enrichment_version` and non-null required fields.
   4. Compare with the current partition: rows added, rows removed, and changed fields. Save this as the run report. Membership changes should be explained by live lag or late copies, and a person should review them.

5. **Swap atomically.** Replace partition D of `events_clean` with the shadow contents in one warehouse operation, using the atomic partition replace the warehouse provides. Dashboards read the old partition until the swap and the new one after it. They never see a partial day. Then drop the shadow table.

6. **Record the run.** Store run ID, D, enrichment version, manifest versions, ledger snapshot time, row counts, the diff summary, and the requester.

7. **Isolate from live.** Run replay on its own compute queue with at most one rebuild at a time, and a lower priority than live ingestion. Its only warehouse writes are the shadow table and the single swap. Live ingestion keeps its own queue.

8. **Replay window.** Closed days within 90 days of D can be replayed. After that the archive and ledger have expired, the day cannot be rebuilt, and its partition stays as last written.

9. **Fixes ship as code.** Deploy an enrichment fix and live events pick it up immediately. The open day cannot be replayed until it closes. Each closed day written with the old version is rebuilt by replay.

## Failure cases the design covers

- **Crash after receipt but before the log acknowledges:** no 202 is sent, the client retries with the same IDs, and dedup absorbs the repeats.
- **Crash after step 9.1 or 9.2 but before 9.3:** no KV key exists, so the batch is reprocessed. The ledger insert-if-absent and the MERGE on `event_id` absorb the repeats.
- **Late copy after the 8-day KV TTL:** live treats it as a first copy and writes it to the current day's partition. The ledger keeps the original first-copy row. The error stays in that partition until the day is replayed, and replay removes it through step R2. Monitor the count of copies arriving more than 7 days after the first copy. Any hit means clients broke the retry contract, and the affected day should be replayed.
- **Archive gap for D:** the count check in R4.1 fails and nothing is published.
- **Clock skew across collectors:** when two copies of one event hit different collectors, `received_at` order can disagree with log order. Both paths choose the first copy by log order, so they agree. The event's partition is the `received_at` day of that first copy.

## Open items (not decided)

1. **Suspected bot traffic: drop or keep with a flag.** Product has not decided. The plan keeps a slot in step 8 that fits either outcome and does not choose. The archive keeps every accepted copy either way. If the bot rule is deterministic from archived data, replay can change the decision within the 90-day window. Product must decide before the bot rule ships.
2. **Response when every event in a batch is rejected.** The plan assumes 202 with the full rejected list, since the brief ties 202 to durable storage and nothing needs storing. Confirm.
3. **Non-UUID `event_id`.** The brief's malformed list does not include it, so the plan accepts such events and dedups them as strings. Confirm.
4. **Retention of `events_clean` partitions.** The brief does not say how long they are kept.
5. **Handling of client IP and User-Agent in the archive.** Enrichment needs them, so the plan keeps them for the same 90 days. Confirm the privacy treatment.
6. **Maximum time from collector receipt to log append.** This sets the grace after 02:00 before a day is eligible for replay. The brief does not give it.

## Assumptions to verify

- **Key-value store:** per-key TTL works as described. One owner per `event_id` partition makes get-then-set safe. A rebalance overlap cannot create duplicate output, because both warehouse writes are idempotent.
- **Warehouse:** supports frequent micro-batch writes, MERGE for the ledger and for `events_clean`, and the atomic partition replace the brief describes. It also needs a separate compute queue for replay.
- **Log:** keyed partitions, acks = all, and an idempotent producer are available.
- **Object storage:** lifecycle expiry is by age since object creation.