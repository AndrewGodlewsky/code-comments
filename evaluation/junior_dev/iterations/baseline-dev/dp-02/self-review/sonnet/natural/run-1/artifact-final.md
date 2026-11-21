# Clickstream ingestion plan

Goal: take click and screen-view events from the website and the iOS and Android apps, remove duplicates, enrich them, and load them into the warehouse table `events_clean` (one partition per UTC day). Live events must be queryable within 5 minutes of reaching us. An operator must also be able to rebuild any closed day.

Data flow (arrows show the direction data moves):

```
LIVE PATH
clients -> collector -> raw log -+-> archiver -> archive (object storage, 90 days)
                                 |
                                 '-> live processor (dedup via KV store, then enrich)
                                       -> loader -> events_clean[day]

REPLAY PATH (one day, run by an operator)
archive -> replay job -> staging table -> atomic swap into events_clean[day]
```

## Terms used in this plan

- **Raw log**: the existing replicated append-only log (Kafka-style, 14-day retention). It is split into partitions. Each record in a partition has an increasing **offset**, so `(partition, offset)` identifies a record and gives its append order.
- **KV store**: the existing key-value store. It supports an atomic "set if absent" and a per-key TTL (expiry).
- **Archive**: object storage holding every accepted event for 90 days. Lifecycle rules expire old objects.
- **Enrichment**: adding derived fields to an event: a geo-IP lookup from the client IP, and user-agent parsing.
- **Closed day**: UTC day D closes at 02:00 UTC on D+1. Only closed days can be replayed.
- **Duplicate**: an event with the same `event_id` as an earlier one. The first copy we receive wins.
- **Micro-batch**: a small group of processed events (about 60 seconds' worth) sent to the warehouse in one load.
- **Watermark**: a per-log-partition value, defined in step 15, that says how far the archive is complete.

## Part A. Decisions that shape everything

1. **Day = UTC day of `received_at`.** The collector stamps `received_at` (server time). Nothing downstream uses the client timestamp to choose a partition or a replay.
2. **Partition the raw log by `hash(event_id)`.** All copies of one event land in the same log partition, in append order, and the first copy appended wins. This gives "first copy we receive" one deterministic meaning. Live dedup has no race between collector nodes, and replay can reproduce the live result exactly.
3. **The archive is the source of truth for 90 days. The log is only transport.** The log keeps 14 days, which is too short for the 90-day retention requirement and for the lookback replay needs. The archive keeps every accepted event, duplicates included, byte for byte.
4. **Enrichment is a pure function of the archived raw record plus pinned lookup versions** (geo-IP database, user-agent parser). This is what makes a replay after a bug fix meaningful.
5. **Replay is a batch job, separate from live.** It reads only the archive and writes only to a staging table. It never touches the log consumers or the dedup KV store. It goes live through one atomic partition replace.

## Part B. Live path

### Collector

6. **Receive and validate per event.** For each event in the batch (up to 100):
   - Reject it if `event_id` or `device_id` is missing, or if the event is over 32 KB.
   - Record each rejection with the event's position in the batch and a reason.
   - Valid events continue.
7. **Stamp the envelope.** For each valid event, record `received_at` (server UTC time, taken once per request), the client IP, the `User-Agent` header, the collector node ID and a batch ID. Store the IP and user-agent now, because enrichment needs them later and cannot recover them otherwise. Keep the event payload as the original bytes, not re-serialized.
8. **Append to the raw log and wait for full-replica acknowledgement.** Key each record by `event_id` (this routes copies of one event to the same partition). Wait for the acknowledgement of every record in the batch.
9. **Respond.**
   - If all appends succeeded, return **202** with the list of rejected events. Clients never retry rejected events. If every event was rejected, still return 202 with the full rejection list, because nothing needs storing.
   - If any append failed or timed out, return 5xx and never 202. The client resends the same batch. Events already appended become duplicates, which are archived and then dropped by dedup. This is expected and safe.
10. **Keep the collector stateless.** It holds no dedup state and does no enrichment, so it scales horizontally and stays fast.

### Archiver (raw retention)

11. **Run an archiver consumer on the raw log.** It writes records to object storage under `raw/received_day=YYYY-MM-DD/`. The day comes from each record's own `received_at`, not from when the file is written. Records within a log partition are not strictly ordered by `received_at`, so one batch of records may need to be split across days.
12. **Preserve everything.** Each archived record holds the raw payload bytes, the envelope, and the log partition and offset.
13. **Make writes idempotent.** Name each file deterministically from partition, day and offset range, so a retried or restarted archiver overwrites the same object instead of duplicating it. Replay also ignores any repeated `(partition, offset)`. Records with the same `event_id` but different offsets are real duplicates and are kept.
14. **Apply an object-storage lifecycle rule** that expires `raw/` after 90 days.
15. **Monitor archiver lag and publish a watermark.** Alert at 15 minutes of lag and page at 6 hours, because the log holds only 14 days and a long stall would lose data. For each log partition, publish a **watermark**: the highest time T such that every record in that partition with `received_at` up to T is already archived. The replay job checks it (step 25).

### Live processor (dedup and enrich)

16. **Run one consumer per log partition.** Because all copies of an `event_id` share a partition, processing in offset order is enough to decide the winner.
17. **Dedup with the KV store.** Do an atomic set-if-absent on key `event_id`, with value `(partition, offset, received_at)` and a **TTL of 8 days**. A client can resend up to 7 days after the first copy, so 8 days leaves a day of margin.
    - If the key was absent, this is the first copy, so continue.
    - If the key exists with the same `(partition, offset)`, this is a reprocess after a crash. Treat it as the first copy again, so at-least-once consumption never wrongly drops a winner.
    - If the key exists with a different `(partition, offset)`, drop the event as a duplicate. It is already archived, so nothing is lost.
18. **Enrich the first copies.** Run the geo-IP lookup and user-agent parsing using versioned lookup data. Record the enrichment version on each row.
19. **Bot traffic: placeholder only (see Part D).** Reserve a no-op step here, after dedup, so that whichever option product picks cannot change dedup behavior. Do not add a bot column or a drop rule yet.
20. **Send micro-batches to the loader** roughly every 60 seconds. Each micro-batch has a deterministic ID derived from partition and offset range.

### Loader and warehouse

21. **Append to the `events_clean` partition for the event's `received_at` UTC day.** Loading must be idempotent per micro-batch ID, so a retried batch never inserts twice. If the warehouse cannot do this natively, keep a small load-ledger table keyed by micro-batch ID.
22. **Stop appending to day D after it closes (02:00 UTC on D+1).** A straggler row for a closed day should be rare. When one occurs, alert and fix it by replaying that day.
23. **Latency budget for the 5-minute target:**

    | Stage | Budget |
    |---|---|
    | Collector to log | 1 s or less |
    | Processor lag | 30 s or less |
    | Micro-batch interval | 60 s |
    | Warehouse load | 90 s or less |

    The stages add up to about 3 minutes, leaving about 2 minutes of slack. Alert on end-to-end freshness at 4 minutes, measured as now minus the newest `received_at` visible in `events_clean`.

## Part C. Replay of one UTC day

An operator runs `replay --day D --enrichment-version V`.

24. **Check that the day is replayable.**
    - It must be closed: now is at or after 02:00 UTC on D+1.
    - It must be within the archive window. The job needs day D plus the 8 days before it (matching the live 8-day dedup memory), so the oldest replayable day is about 82 days back, not 90.
    - No other replay of D may be running (take a lock per day).
25. **Check the archive watermark.** Every log partition's watermark must be past 00:00 UTC on D+1. This confirms every record stamped on day D is archived. If not, wait.
26. **Pin the inputs.** Record the archive file list, the enrichment version V and the code version, so the run can be audited and repeated.
27. **Read the inputs.**
    - Read the `event_id`s from archive days D-8 to D-1. These are the events that could already have won earlier.
    - Read all of day D, ordered per `event_id` by `(partition, offset)`. This is the order the live processor used.
    - Ignore repeated `(partition, offset)` records from archiver retries.
28. **Dedup in the job's own memory or temp storage.** For each `event_id` in day D, keep a copy only if the `event_id` is not in the earlier-days set and this copy has the lowest offset among its copies in D. The job never reads or writes the live KV store.
29. **Enrich with the fixed code and lookups (version V).** Use the archived IP and user-agent, not current request data.
30. **Write to a staging table**, such as `events_clean_staging_D_<runid>`, not to the live partition.
31. **Validate before going live:**
    - No duplicate `event_id` in staging.
    - Every row's `received_at` falls on day D.
    - Rows kept + duplicates dropped = distinct archived records for D.
    - Compare against the live partition for D. Row counts should be equal or differ only by known stragglers, and other differences should be limited to the enrichment columns that were fixed. Produce a diff summary for the operator.
    - On any failure, stop and report. Nothing live has changed so far.
32. **Atomically replace the day partition** of `events_clean` for D with the staging table. Dashboards see the old complete day or the new complete day, never a half-built one.
33. **Record the result** in an audit log: run ID, versions, counts and diff summary. Drop the staging table after a retention period. Re-running a failed replay is safe, because nothing is visible before step 32.
34. **Protect live ingestion while the job runs:**
    - Run it on its own compute pool, with a cap on archive read throughput.
    - Allow only one concurrent replay by default.
    - It never reads the log, never touches the KV store, and writes only to staging until the single swap.

## Part D. Open decision

35. **Suspected bot traffic: drop, or keep with a flag?** Product has not decided, and this plan does not choose.
    - **Where it goes:** the no-op step after dedup (step 19) and the `events_clean` schema.
    - **If dropped:** the step filters those events out before load.
    - **If kept with a flag:** the step adds a nullable `is_bot` column, which is cheap to add later.
    - **Either way:** the archive keeps the raw events, so replay can apply the decision to closed days.
    - **What stays safe:** because the step sits after dedup, the choice never changes which copy wins.
    - **What stays open:** the detection method, and how to treat events in already-loaded days.

## Assumptions to confirm

- The warehouse can atomically replace one partition from a staging table, and can make appends idempotent per batch ID (otherwise a ledger table is acceptable).
- Append order within a log partition defines "first received". Under clock skew between collector nodes, a copy with a slightly earlier `received_at` could lose. Retries are at least 1 s apart, so only near-simultaneous copies are affected.
- The brief does not say what to do with a batch of more than 100 events, and this plan does not address it. It needs a decision: reject the whole batch with a 4xx, or accept it.