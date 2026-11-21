# Clickstream ingestion plan: `events_clean`

## Definitions

- **Received day**: the UTC date of the collector-stamped `received_at`. It sets the partition and the replay coverage of an event.
- **Winning copy**: the first copy of an `event_id` to claim it in the dedup store. Its `received_at` is the event's partition day. Later copies never change it.
- **Dedup window**: the TTL on each `event_id` claim in the key-value store.
- **Closed day**: a UTC day D that is marked closed at 02:00 UTC on D+1, and only once the live consumer and the raw archiver have both processed every record with received day D (see step 8).

## Live path

1. **Validate per event.** The collector receives a batch of up to 100 events over HTTPS. Each event is checked on its own: `event_id` is present and a UUID, `device_id` is present, and the serialized event is 32 KB or less. Invalid events are left out of the write and listed in the response with their batch index and reason. The valid events continue.
2. **Stamp.** Each accepted event gets `received_at` (server UTC, millisecond precision), `collector_id`, `batch_id`, and its position in the batch. The event's original bytes are kept unchanged next to the stamp.
3. **Make durable, then acknowledge.** The collector appends the accepted events to the replicated log and waits for the replication ack. Only then does it return 202, with the reject list in the body. If the append fails or times out, it returns 5xx and the client retries the same batch with the same `event_id`s. Duplicates are expected and handled downstream. Open item 4 covers a batch where every event is rejected.
4. **Archive raw.** A raw-archive consumer group reads the log and writes objects to object storage, partitioned by received day (`raw/day=YYYY-MM-DD/`). Each record is stored as stamped, including duplicates. It commits its log offset only after the object write succeeds. The log keeps 14 days, so the archiver's lag must stay far below that. Alert when lag reaches 1 day.
5. **Dedup and enrich.** The live consumer group processes each record as follows.
   a. Claim the `event_id` with set-if-absent in the key-value store. The stored value is a reference to this raw record (`collector_id`, `batch_id`, position). TTL is 8 days: the 7-day client buffer plus a margin, counted from first receipt.
   b. If the claim was created now, or already exists with this same reference (a redelivery of this record), this record is the winner. If the claim belongs to another record, drop the record from `events_clean`. Raw still keeps it.
   c. For the winner, enrich with the current enrichment version (geo-IP, user-agent parsing). Set `partition_day` to the received day and record `enrichment_version`.
   d. Write a first-seen ledger row (`event_id`, `received_at`, raw reference) to durable storage. Replay needs it (step R3).

   Storing the reference in the claim means a crash after the claim but before the warehouse write does not turn the event into a dropped duplicate when it is redelivered.
6. **Write to the warehouse.** The warehouse writer flushes micro-batches about every 60 seconds. Each batch is an upsert keyed by `event_id` into partition `partition_day`, so a redelivery after a crash cannot create a second row. Live writes touch only today's partition and any day that is not yet closed.
7. **Freshness.** The target is 5 minutes from collector receipt to queryable in `events_clean`. Measure the p99 of (warehouse visible time minus `received_at`). Alarm at 3 minutes, and separately on consumer lag.
8. **Close the day.** A scheduled job runs at 02:00 UTC on D+1. It marks day D closed only if (a) the live consumer's watermark, the minimum processed `received_at` across partitions, has reached the start of D+1, (b) the raw archiver's watermark has reached the start of D+1, and (c) no writes to D are pending. If a condition is not met, the job retries every 5 minutes and alarms after 60 minutes. The clock alone never closes a day.

## Replay path (rebuild one closed day D)

R1. **Request and check preconditions.** The operator submits the day, the target `enrichment_version`, and a reason. The request is refused unless D is closed, D is inside the retention window, and no replay of D is already running.

R2. **Build in staging.** Create a staging partition for D in a staging table. Dashboards read only `events_clean`, so nothing in staging is visible to them.

R3. **Select winners.** Read the ledger rows whose `received_at` falls on D. Each row names its winning raw record. The ledger is what lets replay find winners without reading copies from before D (see open item 2).

R4. **Re-enrich.** Read those raw records from object storage and run enrichment with the target version. Replay must not read the log, must not touch the key-value store, and must not change any consumer offset. Run it on a separate compute pool with a throttle, and watch live freshness while it runs.

R5. **Write staging.** Upsert the rows into the staging partition for D, keyed by `event_id`. Reruns are then idempotent.

R6. **Validate before the swap.**
   - The staging row count equals the ledger row count for D, with no duplicate `event_id`s and every `partition_day` equal to D.
   - Compare against the current partition D and report added, removed, and changed rows, broken down by field.
   - Require explicit operator approval when the diff is outside what the enrichment change predicts, for example when any rows are removed.

R7. **Swap atomically.** In one warehouse transaction, replace partition D with the staging partition. Re-check that D is still closed and that no live write to D is pending, and abort if either check fails. Readers see the old partition or the new one, never a mix.

R8. **Audit.** Record the day, the old and new `enrichment_version`, the counts, the diff summary, the operator, and the timestamps. Then drop the staging partition.

R9. **Failure.** If any step fails, drop the staging partition. The live partition is untouched, and nothing in the key-value store, the log, the consumer offsets, the raw archive, or the ledger has changed.

## Retention

- **Raw objects**: lifecycle deletes objects 90 days after creation. Objects are written on or after their received day, so every event is kept at least 90 days from `received_at`. Duplicates are kept as well.
- **Ledger**: kept 90 days from `received_at`, with the same lifecycle rule.
- **Log**: 14 days. It is an operational buffer, not the record of accepted events.
- **Key-value store**: 8-day TTL. It is a dedup mechanism, not a retention store.
- **`events_clean`**: retention is not set by this plan (open item 1 covers related decisions).

## Open items

1. **Bot traffic: open, not decided.** Product has not decided whether suspected bot traffic is dropped or kept with a flag, and this plan does not choose. The design supports either outcome. The classification belongs in enrichment (step 5c), not the collector, because enrichment can be replayed and the collector cannot. Raw keeps every event, so either choice still meets the 90-day rule. The exact `events_clean` schema (a flag column or none) and the drop rule wait on this decision.
2. **Replay horizon.** Without the ledger (step 5d), replaying day D needs raw copies from up to 7 days before D, because a winner's earliest copy can be that old. The replayable window would then shrink to about 83 days. Recommendation: keep the ledger, which holds the replay window at 90 days.
3. **Dedup window.** Confirm with the mobile SDK team that the 7-day buffer is a hard limit, including retry backoff and device clock error. If the real limit is longer, the TTL must grow. A copy that arrives after its claim expires becomes a second row. Replay compares live and replay output, so any duplicate it finds is reported as a difference.
4. **All-rejected batch.** Confirm that a 202 with every event listed as rejected is acceptable to clients, or define another status.
5. **Clock skew across collectors.** The winner is decided by claim order in the key-value store, not by timestamps. The partition day is the winner's `received_at`, which may come from a collector whose clock runs a few seconds off. Confirm that this is acceptable at day boundaries.
6. **Warehouse capabilities.** Verify that partition replace is a single atomic transaction on this warehouse, and that concurrent readers are not blocked or shown partial results.
7. **Replay isolation.** Confirm a compute pool separate from live ingestion exists. If it does not, the throttle in R4 becomes a hard requirement.

## Checks before launch

- A duplicate arrives 7 days after the first copy. It lands in a different received day, is dropped from `events_clean`, and is kept in raw.
- Two copies straddle midnight UTC. The first arrival wins, and its day is the partition.
- Crash after the key-value claim and before the warehouse write, then redeliver. The event appears exactly once.
- Replay with unchanged enrichment reproduces the live partition with zero diff.
- Replay under full live load keeps live p99 freshness under 5 minutes.
- A concurrent reader during the swap never sees a partial partition.
- The archiver is stopped for 13 days. The alarm fires before log retention loses data.