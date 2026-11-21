# Clickstream ingestion plan: `events_clean`

## What this is

This plan moves click and screen-view events from our website and our iOS and Android apps into one warehouse table, `events_clean`. Each event appears once, is enriched (geo-IP lookup and user-agent parsing), and sits in the partition for its UTC day. Live events are queryable within 5 minutes of reaching us. Any closed day can be rebuilt later, for example after an enrichment bug is fixed.

The live path works like this. A client sends a batch to a collector. The collector checks each event, stamps it, and writes it to a log. It acknowledges the batch only after the log confirms the write. Two consumers then read the log. The raw archiver keeps every copy. The live consumer picks one winning copy per event, enriches it, and writes it to the warehouse. A daily close job later marks each day as closed, using log positions, so that nothing more can arrive for that day.

The replay path rebuilds one closed day from the stored winners and swaps the result in. It never touches live ingestion.

It is shaped this way because clients retry. The same event can arrive more than once, and a retry can arrive up to 7 days late. So every copy is kept, one rule picks the winner, and the winners of any day can be found again later for a rebuild.

## Terms

- **Event**: one click or screen view. The app gives it an `event_id` (a UUID), a `device_id` and a client timestamp.
- **Batch**: up to 100 events sent together in one HTTPS request. The collector gives each batch a `batch_id`.
- **Collector**: the new service that receives batches, checks them, stamps them and writes them to the log.
- **Stamp**: fields the collector adds to each event: `received_at`, `collector_id`, `batch_id` and the event's position in the batch.
- **`received_at`**: the collector's UTC time, to the millisecond, when it stamped the batch.
- **Received day**: the UTC date of `received_at`. Day D runs from 00:00:00 to 23:59:59.999 UTC on that date. The app's own clock never decides the day.
- **Log**: a replicated, append-only queue split into partitions. Each record has a position number called an **offset**. The log keeps records for 14 days.
- **Log position**: a record's partition and offset together. Raw copies are found by log position.
- **Consumer**: a worker that reads the log. It keeps a committed offset per partition, meaning "everything up to here is finished."
- **Raw archiver**: the consumer that copies every log record, unchanged, to object storage.
- **Live consumer**: the consumer that picks winners, enriches them and writes them to the warehouse.
- **Key-value store**: a fast store whose keys can expire after a set time (TTL). Dedup uses it.
- **Claim**: a key-value entry for one `event_id`. Its value is the stamp reference of the copy that created it: `collector_id`, `batch_id` and position. A claim is created in one atomic step, only if no entry exists yet. It expires after 8 days.
- **Raw copy**: a stamped event kept exactly as received. Every accepted copy has one, duplicates included.
- **Winner (winning copy)**: the copy whose claim is created first. Claim order follows processing order, which roughly follows arrival order. Timestamps do not decide it.
- **Dropped copy**: any later copy of an event that already has a winner. It stays in raw and is not written to `events_clean`.
- **Partition day**: the received day of the winner. It decides which partition the row goes in. It is always the date of the winner's `received_at`.
- **Enrichment version**: a label for one build of the enrichment code and its reference data (geo-IP, user-agent rules). It is set when a consumer is deployed. Every row records the version that wrote it.
- **Ledger**: a set of objects in object storage. Each row is one winner. It holds the winner's `event_id`, its `received_at` and its log position. Replay uses the ledger to find winners.
- **Day status**: a small `day_status` table in the warehouse, with one row per UTC day. The row says `open` or `closed`. A day with no row is open. Only the close job writes it.
- **Closed day**: a day whose status row says `closed`.
- **Late record**: a record for a day that is already closed. It should not happen. If it does, the rules below handle it.
- **Snapshot offsets**: the end offset of every log partition, read once by the close job. They mark the last positions that can hold records for the day.
- **Staging partition**: a temporary copy of one day's partition, used during replay. Dashboards never read it.

## Live path

1. **Check each event.** It starts when a client sends a batch over HTTPS. The collector checks each event on its own. The `event_id` must be present and be a UUID. The `device_id` must be present. The serialized event must be 32 KB or less. Invalid events are left out and listed in the response with their batch index and reason. The valid events continue. Clients never retry rejected events.

2. **Stamp.** The collector reads its UTC clock once per batch. It gives each valid event that `received_at`, plus its `collector_id`, `batch_id` and position in the batch. The event's original bytes are kept unchanged next to the stamp. Because all events in a batch share one `received_at`, a whole batch belongs to one received day.

3. **Store, then acknowledge.** The collector writes the valid events to the log and waits for the log to confirm replication. Only then does it return 202, with the reject list in the body. If the write fails, or is not confirmed within 30 seconds, it returns 5xx.
   - The client resends the same batch with the same `event_id`s after a timeout, 429 or 5xx. It backs off exponentially, from 1 second up to 5 minutes. The resend gets new stamps, so it becomes a new log record.
   - If the first write succeeded but its 202 was lost, the log now holds two copies. A lost 202 and a timeout look the same to the client. So this retry is the main source of duplicates. Steps 5 and 6 handle them.

4. **Archive raw.** The raw archiver reads the log and writes each record to object storage, duplicates included, unchanged. Each record gets its own object, named from its received day and its log position: `raw/day=YYYY-MM-DD/partition=P/offset=O.json`. So a log position is enough to find a raw copy. The archiver commits its offset only after the object write succeeds. The log keeps only 14 days, so the archiver must stay far behind that limit. An alarm fires when its lag reaches 1 day.

5. **Dedup and enrich.** The live consumer handles each log record in order, with the steps below. If the key-value store is down or slow, the consumer does not skip the record. It stops that log partition, does not commit the offset, and retries with backoff. Lag grows and alarms fire. Nothing is lost, because the log keeps records for 14 days. Skipping would either lose an event or let a duplicate through unchecked.
   - a. **Claim.** Try to create the claim for the `event_id`. Its value is the record's stamp reference, and its TTL is 8 days. The create is atomic. When two consumers race for the same `event_id`, exactly one create succeeds, whatever log partition each copy is on. The 8 days are the 7-day device buffer plus a margin, counted from first receipt. Storing the reference means a crash after the claim but before the warehouse write does not turn the event into a dropped duplicate on redelivery.
   - b. **Decide the winner.** If the create succeeded, or the claim already holds this same stamp reference (the same record, redelivered), this copy wins. If the claim holds a different reference, this copy is dropped. It stays in raw and is not written to `events_clean`. A dropped copy can have an earlier received day than the winner. For example, copy X is stamped on day D at 23:59:59.9 but is processed after copy Y, which is stamped on D+1 at 00:00:00.1. Y claims first and wins, so the partition is D+1. X stays in raw under day D.
   - c. **Enrich the winner.** Use the enrichment version the consumer was deployed with. Set `partition_day` to the winner's received day. Record `enrichment_version`.
   - d. **Write the ledger.** For the winners in this offset range, write one ledger object under `ledger/day=YYYY-MM-DD/partition=P/offsets=<first>-<last>.json`. Here the day is the winner's received day. Each row holds the winner's `event_id`, `received_at` and log position. Write it before the warehouse batch for that offset range commits. A redelivery rewrites the same object with the same rows, so repeating the write is safe. A redelivery can also group the same winners into a different object, with a different offset range. So one winner can have rows in two objects. Readers count each `event_id` once.
   - Late winners are written to the ledger here, too. Step 6 decides whether they reach the warehouse.

6. **Write to the warehouse.** Micro-batches are flushed about every 60 seconds. Each micro-batch is one warehouse transaction. Inside that transaction, the writer reads the `day_status` row for every partition day in the batch. It then upserts only the rows whose day is not closed. Each upsert is keyed by `event_id` within its `partition_day`, so a redelivery after a crash cannot create a second row. Reading the status inside the same transaction means the writer never acts on an old mark.
   - Normally, writes touch only today's partition and recent open days.
   - A winner for a closed day is skipped in this transaction. This is a late record. Its ledger row from step 5d stays, so the next replay of that day includes it. The consumer still commits its offset, and an alarm fires.
   - After the transaction commits, the consumer commits the offsets of its records. A record counts as processed only at that point.
   - If the transaction fails, nothing is committed. The offsets stay where they were, and the batch is retried.

7. **Freshness.** The target is 5 minutes from collector receipt to queryable in `events_clean`. Measure the 99th percentile of (warehouse visible time minus `received_at`). Alarm at 3 minutes. Alarm separately on consumer lag.

8. **Close each day.** A scheduled job closes day D. It starts at 02:00 UTC on D+1. The two hours after midnight give in-flight batches time to finish. The job closes a day by log offsets, not by `received_at`. Timestamps cannot prove that all of D has been processed, because records do not arrive in `received_at` order and each collector uses its own clock. Offsets can. Each day closes on its own, in any order, because each check looks only at that day. The job runs three parts, in this order. If a part does not pass, the job retries every 5 minutes and alarms after 60 minutes. The clock alone never closes a day.
   - a. **Fence: no new D stamps.** Each collector stamps with its own UTC clock. Once that clock passes 00:00 UTC on D+1, the collector stamps only D+1. Collector clocks follow NTP. A clock more than a minute off raises an alarm. By 02:00, every collector has moved to D+1. The job then calls a status endpoint on every collector. Each collector answers with the number of batches it has stamped for D that are not yet acknowledged or definitively failed. Each batch has one day, so each batch is counted once. That count can only fall now, so a zero stays zero. The fence passes only when every collector answers zero. A collector that is down or does not answer blocks the fence, because silence is not zero. A restart clears the collector's count, so a poll that spans a restart counts as no answer, and the job polls again. A batch sent before a crash can still reach the log after the fence. That record is a late record.
   - b. **Snapshot: where D can be.** After the fence passes, the job reads the end offset of every log partition, once. These are the last positions that can hold records for D. If the job restarts, it runs the fence and the snapshot again. A later snapshot covers more offsets, so it is still safe.
   - c. **Wait: everything has been read.** The job closes D only when, for every log partition, the live consumer and the raw archiver have committed offsets at or past the snapshot. An idle partition's end offset equals its committed offset, so it never blocks the close. A stuck partition does block it. For example, if the key-value store is down, the live consumer for that partition commits nothing, so the close waits. The job's status shows which partition is short, which consumer it is waiting on, and the offset it must reach.
   - When all three parts pass, the job writes D's status row as `closed`, with the snapshot offsets. From then on, step 6 skips records for D. The stored snapshot offsets are an audit record. The live path never reads them. An operator uses them to check whether a late record arrived after the close.

### What happens when live things fail

| What fails | What happens | What someone sees |
|---|---|---|
| Key-value store down or slow | The live consumer stops that log partition without committing. It retries with backoff. No record is skipped. | Lag and freshness alarms. The close waits. |
| Log write fails or is not confirmed within 30 seconds | The collector returns 5xx. The client resends the same batch with the same `event_id`s. | Nothing, unless the retries keep failing. |
| A 202 is lost | The client resends. The log holds both copies, and the second is a dropped copy. | Nothing. This is expected. |
| Live consumer crashes after the claim, before the warehouse write | On redelivery, the claim holds the same stamp reference, so this copy wins again. The event appears once. | Nothing. |
| Live consumer crashes after the ledger write, before the warehouse commit | On redelivery, the ledger object is rewritten with the same rows. The warehouse upsert is keyed by `event_id`. | Nothing. |
| Warehouse commit succeeds, but the offset commit is lost | On redelivery, the upsert rewrites the same row. No second row is created. | Nothing. |
| Archiver falls behind | The log still holds 14 days of records. | Lag alarm at 1 day. |
| Late winner for a closed day | The writer skips it and the consumer commits its offset. The ledger keeps its row and the raw copy stays. The next replay of that day includes it. | Alarm. |
| A collector is down during the close | The fence does not pass until the collector answers zero. | The close waits. Alarm after 60 minutes. |
| A collector's clock is more than a minute off | Nothing stops. A batch may be stamped on the wrong day. | Clock alarm. |

## Replay path (rebuild one closed day D)

Replay is manual. An operator starts it, usually after an enrichment fix. Nothing starts it automatically. Replay builds a new copy of day D from stored data. It swaps the copy in only after the copy passes its checks. Replay never reads the log or the key-value store, and it never changes any consumer offset. So it cannot slow live ingestion or change dedup.

1. **Request and check.** The operator submits the day, the target enrichment version and a reason. The request is refused unless D is closed, D is within the 90-day retention window, no other replay of D is running, and the target version exists in the replay compute pool. How operators submit requests is still open.
2. **Build staging.** Create an empty staging partition for D. Dashboards read only `events_clean`, so they never see staging.
3. **Select winners.** List every ledger object under `ledger/day=D/` and read its rows. Keep one row per `event_id`, because a redelivery can record the same winner twice. Each row gives the winner's log position, which leads to its raw object. Replay reads only these winners. Copies that did not win are never read or re-enriched. They stay in raw for audit. Replay never changes which copy wins. Because a ledger row's `received_at` is the winner's `received_at`, its day is the winner's partition day. So this step selects exactly the rows that live writes put in partition D. A late winner written after this step is not part of this replay. It waits for the next one.
   - The ledger is needed for this step. Without it, replay would have to read raw copies from up to 7 days before D to find winners. That would shorten the replayable window to about 83 days.
4. **Re-enrich.** For each winner, read its raw object at `raw/day=D/partition=P/offset=O.json`. Run enrichment with the target version. Run this on a separate compute pool with a throttle. Watch live freshness while it runs.
5. **Write staging.** Upsert the rows into the staging partition, keyed by `event_id`. Running it again gives the same result.
6. **Check before the swap.** There are two kinds of check.
   - **Hard checks** must all pass. The staging row count must equal the number of distinct winners from step 3. No `event_id` may appear twice. Every `partition_day` must equal D. If any check fails, the replay ends as ABORTED. The operator sees the check's name, the expected value and the actual value.
   - **Diff.** Compare staging with the current partition D. Report added, removed and changed rows, broken down by field.
   - **Approval.** If the diff is larger than the enrichment change predicts (for example, any removed rows), the replay pauses with staging kept. A pause is not a failure. The operator either approves, and the replay goes on to the swap, or rejects, and the replay ends as ABORTED. How that decision reaches the system depends on the request interface, which is still open.
7. **Swap.** In one warehouse transaction, re-read D's status row. It must still say `closed`. Then replace partition D with the staging partition. Live writes to D also read the status row in their own transactions, so the warehouse orders each live write either before the swap or after it. A live write that comes after the swap finds D closed and is skipped. If the status check fails, the replay ends as ABORTED and says why. A closed day is final. No step reopens it.
8. **Audit.** Record the day, the old and new enrichment versions, the row counts, the diff summary, the operator and the timestamps. Then drop the staging partition.
9. **Failure.** If any step fails, drop the staging partition. The operator fixes the cause and submits a new request from step 1. The live partition is untouched. Nothing in the key-value store, the log, the consumer offsets, the raw archive or the ledger has changed.

## Retention

- **Raw objects**: deleted 90 days after they are written. They are written on or after their received day, so every event is kept at least 90 days from `received_at`. Duplicates are kept too.
- **Ledger**: kept 90 days from `received_at`, with the same lifecycle rule as raw.
- **Log**: 14 days. It is an operational buffer, not the record of accepted events.
- **Key-value store**: 8-day TTL. It is for dedup only, not for retention.
- **`events_clean`**: retention is not set by this plan. See the open questions.

## Building and launching

This section covers how to verify the build and launch it. It is not part of how the system runs.

Checks before launch:

- A duplicate arrives 7 days after the first copy. It lands on a different received day. It is dropped from `events_clean` and kept in raw.
- Two copies straddle midnight UTC. The first copy to claim the `event_id` wins, and its day is the partition.
- The live consumer crashes after the claim and before the warehouse write, then the record is redelivered. The event appears exactly once.
- A replay with unchanged enrichment reproduces the live partition with zero diff.
- A replay under full live load keeps live p99 freshness under 5 minutes.
- A concurrent reader during the swap never sees a partial partition.
- The archiver is stopped for 13 days. The alarm fires before log retention loses data.
- A collector that is down blocks the close until it answers zero in-flight batches for D.

## Open questions

- **Bot traffic: not decided.** Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose. The design supports either. The classification belongs in enrichment, not the collector, so it can be replayed. Raw keeps every event either way, so both options meet the 90-day rule. The `events_clean` schema (a flag column or none) and any drop rule wait on this decision.
- **Replay horizon.** The ledger keeps the replay window at 90 days. Without it, the window would shrink to about 83 days. Keeping the ledger is recommended.
- **Dedup window.** Confirm with the mobile SDK team that the 7-day buffer is a hard limit, including retry backoff and device clock error. If the real limit is longer, the claim TTL must grow. A copy that arrives after its claim expires becomes a second row. Replay compares live and replay output, so such a duplicate shows up as a difference.
- **All-rejected batch.** Confirm that a 202 listing every event as rejected is acceptable to clients, or define another status.
- **Clock skew and processing order.** Winners are decided by claim order, not by timestamps. A dropped copy can therefore have an earlier day than the winner. The partition day comes from the winner's `received_at`, which may come from a collector whose clock runs a few seconds off. Confirm this is acceptable at day boundaries.
- **Warehouse capabilities.** Verify three things. A partition replace is one atomic transaction. A transaction that reads `day_status` and writes a partition is serialized against a replace of that partition. Concurrent readers are never blocked or shown partial results.
- **Replay compute.** Confirm that a compute pool separate from live ingestion exists. If it does not, the throttle in replay step 4 becomes a hard requirement.
- **Replay request interface.** Decide how an operator submits a replay (UI, command line or ticket), who the operator authenticates as, and how an approval or rejection of a paused replay reaches the system. Decide this before launch.
- **Close after 02:00.** The job starts at 02:00, but the wait can finish later if a consumer lags. Confirm that a close after 02:00 is acceptable. If it is not, the close must be cut at 02:00, and records arriving after the cut are handled as late records.
- **Raw object count.** One raw object per log record means many small objects each day. Confirm the storage and request cost at expected volume. If it is too high, group raw records into larger blocks of offsets and change the key in step 4 and replay step 4 to match.