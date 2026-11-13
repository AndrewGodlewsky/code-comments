# Clickstream ingestion plan

Website and mobile clients send batches of click and screen-view events to a new collector, which stamps each event with `received_at` and writes it to a replicated log. Two independent readers take events from that log. One archives them untouched for 90 days. The other drops duplicates, enriches the events and loads them into the warehouse table `events_clean` within 5 minutes. After an enrichment bug fix, a replay job rebuilds one closed UTC day from the archive and swaps it in atomically. The archive is the source of truth because the log keeps data for only 14 days.

## Terms

- **Raw log**: the existing replicated append-only log (Kafka-style, 14-day retention). The collector writes to it. The archiver and the live processor read from it. Each reader tracks its own position (offset), so readers do not affect each other. An event's place in the log is its log partition plus its offset in that partition. The collector picks the log partition by hashing `event_id`, so every copy of an event lands in the same partition.
- **Lag**: how far a reader's position is behind the newest event in the log.
- **Passed time T** (in one log partition): a reader has passed T in a partition when either (a) it has read an event there whose `received_at` is at or after T, or (b) it has read to the end of that partition and the wall clock is at least 10 minutes past T. Rule (b) covers a quiet partition that gets no later event. The 10 minutes is a grace period for the delay between a collector stamping an event and the log holding it. Each reader records, per partition, the latest time it has passed.
- **Archive**: hourly part files in object storage holding every accepted event exactly as received, duplicates included. Beside each event the archiver stores its log partition and offset, as separate fields that are not part of the event. A lifecycle rule deletes files after 90 days.
- **Hour-complete marker**: a small file the archiver writes into an hour's folder once every file for that hour is uploaded. Replay reads an hour only if its marker exists.
- **KV store**: the existing key-value store with per-key TTL. Only the live processor uses it, to remember which `event_id`s it has already loaded.
- **`received_at`**: server time when the collector received the event. The event's UTC day is the day of `received_at`, never of the client timestamp. That day decides its partition and which replay covers it.
- **Closed day**: UTC day D is closed from 02:00 UTC on day D+1. The 2 hours let the live path finish loading D. Only closed days can be replayed.
- **Partition swap**: the warehouse can atomically replace one day partition of a table with another table's contents. Readers see the old or the new partition, never a mix.

## How it runs

1. **Client sends.** The web, iOS and Android SDKs send batches of up to 100 events over HTTPS to the collector. Each event has `event_id` (a client-generated UUID), `device_id` and a client timestamp. Mobile SDKs keep unacknowledged events on the device for up to 7 days.
   - On a timeout, 429 or 5xx, the SDK resends the same batch with the same `event_id`s. It backs off exponentially from 1 s up to 5 minutes. A retry can therefore arrive up to 7 days after the first copy.
   - Clients never retry events the collector rejected.

2. **Collector validates and stores.** It rejects an event that lacks `event_id` or `device_id`, or is over 32 KB. Each bad event is rejected alone and listed in the response. The other events in the batch are still accepted. Rejected events are not stored, only counted in a metric per rejection reason. It adds `received_at` to every accepted event and writes them to the raw log, in the log partition chosen by hashing `event_id`. This keeps all copies of an event in one partition, so one reader instance sees them in order.
   - It returns 202 only after the log confirms the write is durably replicated.
   - If the write fails or times out, it returns 5xx and the SDK retries the whole batch. Duplicates from that retry are handled in step 4.

3. **Archiver stores everything.** It is its own reader of the raw log. It writes every event, duplicates included and unchanged, as part files under the folder for the hour of `received_at`, with the log partition and offset beside each event. Each part file is uploaded whole, so a reader never sees a half-written file.
   - Once the archiver has passed the end of an hour in every log partition, it uploads the last files for that hour and then writes the hour-complete marker. Until then the hour is still filling.
   - If it falls behind, it keeps reading from where it stopped. The log's 14 days leave room to catch up, and the lag alert (step 6) fires long before that.

4. **Live processor dedups, enriches and loads.** It is a second, independent reader of the raw log. It may run as several instances, each owning some log partitions. Because copies of an event share a partition, the instance that owns it sees every copy, so dedup never compares across instances. Each instance works in micro-batches, loading at least once a minute so events are queryable well inside 5 minutes. After each micro-batch it saves its log position and, per partition, the latest time it has passed.
   - **Dedup.** An event is a later copy, and is dropped, if the KV store already has the key `event_id` or the same `event_id` appeared earlier in this micro-batch (the processor keeps a set of IDs seen in the batch). The first copy received wins. Nothing is written to the KV store at this point.
   - **Enrich.** It adds geo-IP and user-agent data.
   - **Load.** It appends the kept rows to the `events_clean` partition for the day of `received_at`. Then it writes each kept `event_id` to the KV store with an 8-day TTL (longer than the 7-day retry window), and then moves its log position forward. Writing the IDs after the load means a failure can cause duplicate rows but never lost events.
   - **If the append fails or times out**, the processor writes no IDs, keeps its log position and retries the micro-batch. If it cannot tell whether the append landed, the retry may load some rows twice, the same as after a crash.
   - **If the KV write fails** after a successful load, the processor retries it a few times. If it still fails, it stops without moving its position, as when the KV store is down. On restart the micro-batch is reprocessed.
   - **If it crashes** after loading and before recording the IDs, it restarts from its last saved position and reprocesses that micro-batch. The KV store does not have those IDs yet, so they are loaded again. Some rows may appear twice in the open day. The replay in step 5 removes them. We accept this rather than risk losing events.
   - **If the KV store is down**, the processor stops without moving its position. Lag grows and the alert fires. It never loads events it cannot check for duplicates.

5. **Replay rebuilds one closed day.** An operator starts it by hand with a UTC day D. It refuses in any of these cases. The refusal message names the failed check and lists each missing hour marker or each log partition whose live passed time is too early. The operator waits and reruns.
   - D is not yet closed, or is older than 83 days (90 days of archive minus the 7-day look-back below).
   - Any hour of D, or of the 7 days before D, lacks its hour-complete marker. The archiver is still behind.
   - The live processor's saved passed time in some log partition is earlier than the end of D. The live processor is still loading D, or a quiet partition is not yet confirmed past D. Without this check, rows the live processor loaded after the swap would land in the rebuilt partition as duplicates.

   Replay reads only the archive and the live processor's saved state. It does not touch the raw log or the KV store and does not change the live processor, so live ingestion and live dedup state are unaffected.
   - **Dedup.** It reads the archive for D and for the 7 days before D. It keeps an event of D only if no other copy of that `event_id` comes earlier in that span. Earlier means a smaller `received_at`. If two copies have the same `received_at`, the smaller offset wins (copies share a log partition). This matches the live rule that the first copy wins, including copies whose first sighting was on an earlier day.
   - **Enrich.** It enriches the kept events with the current code, which carries the bug fix.
   - **Load and swap.** It writes the result to a separate staging table, then uses a partition swap to replace the day D partition of `events_clean`. The live processor has passed the end of D and appends nothing more to it, so the swap does not race with live loading. Dashboards see the old day D or the new one, never a half-built one.
   - **If it fails** before the swap, `events_clean` is untouched. The operator drops the staging table and reruns. A rerun is safe.

6. **Monitoring.** Alerts fire on:
   - Live processor lag over 3 minutes (page).
   - Archiver lag over 1 hour (warn).
   - Collector 5xx rate.
   - A replay failure.

## What happens when things fail

| Failure | Result |
|---|---|
| Collector cannot write to the log | 5xx. The SDK retries the same batch. |
| One malformed event in a batch | Only that event is rejected. The rest is accepted. |
| Archiver or live processor is behind | Each catches up from its own position. The alert fires. The log holds 14 days. |
| Archiver behind when replay starts | Replay refuses because an hour-complete marker is missing. Rerun later. |
| Live processor behind when replay starts | Replay refuses because the live passed time has not reached the end of D. Rerun later. |
| A log partition gets no events after an hour or day ends | The reader counts it as passed once it is at the end of that partition and 10 minutes have gone by. |
| Append to `events_clean` fails or times out | Position kept, batch retried. A few duplicate rows are possible in the open day. |
| KV store down, or KV write keeps failing | The live processor pauses. Nothing is loaded without a duplicate check. |
| Live processor crash | Reprocesses from the saved position. A few duplicate rows are possible in the open day. |
| Replay fails | `events_clean` is unchanged. Rerun. |

## Build order

1. Collector and raw log topic.
2. Archiver (with hour-complete markers) and its 90-day lifecycle rule.
3. Live processor with KV dedup and the `events_clean` load.
4. Replay job and its swap.
5. Alerts.

## Open questions

- **Bot traffic**: product has not decided whether suspected bots are dropped or kept with a flag. This plan does not choose. It would be a step between dedup and enrich in the live processor and in replay.
- Who responds to the alerts, and are the 3-minute and 1-hour thresholds right? Both are unknown.
- Should a replay run automatically for every day after it closes, so crash duplicates always get removed? Today it is operator-started only.
- Should rejected events be kept for debugging? The brief does not require it, so only counts are kept.
- Collector servers may have slightly different clocks, so `received_at` could be out of order within a log partition. The passed-time rule assumes the order is close enough, and the 10-minute grace period is a guess. How much skew is possible is unknown.
- Whether an append to the warehouse can partly succeed is unknown. The plan treats an unclear append as possibly loaded and accepts duplicate rows.
