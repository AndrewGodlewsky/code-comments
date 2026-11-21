# Clickstream ingestion plan

Today there is no pipeline for click and screen-view events from the website and the iOS and Android apps. This plan adds one. Clients send batches over HTTPS to a new collector. The collector stamps each event with the server time it was received, `received_at`, and writes it to a durable log. Two readers then consume the log independently. The archiver keeps every accepted event exactly as received for 90 days. The live processor removes duplicates, adds geo-IP and user-agent data, and loads each event into the warehouse table `events_clean`, one partition per UTC day. Live events must be queryable within 5 minutes of `received_at`. Clients retry, so duplicates are normal. Live processing is fast but not perfect, so an operator can run a replay that rebuilds one finished day from the archive, usually after an enrichment bug fix.

## Terms

- **Event**: one click or screen view. It carries `event_id` (a UUID made by the client), `device_id` and a client timestamp.
- **Batch**: up to 100 events sent in one HTTPS request.
- **Acknowledged**: the client received a 202 for the batch and stops resending it. If the 202 is lost and the client times out, it resends and a duplicate is created. That is normal.
- **`received_at`**: the clock time of the collector instance that accepted the event. It decides the event's UTC day, never the client timestamp. Collector clocks are assumed to be NTP-synced, but can differ slightly.
- **UTC day**: the UTC date of `received_at`. It decides the event's `events_clean` partition and which replay covers it.
- **Raw log**: the existing replicated append-only log (Kafka-style, 14-day retention). Reading does not remove events, so several readers can each read all of it.
- **Raw log partition**: one slice of the raw log, read in write order. The collector picks it by hashing `event_id`, so all copies of one `event_id` land in the same partition.
- **Archive**: hourly files in object storage holding every accepted event exactly as received, duplicates included. A lifecycle rule deletes them after 90 days.
- **KV store**: the existing key-value store with per-key expiry. Live dedup uses it.
- **Duplicate**: a later copy of an `event_id` already received. The first copy received wins and later copies are dropped. Duplicates are identified by `event_id` alone.
- **Closed day**: a UTC day that is past 02:00 UTC the next day. The 2 hours let the live processor and archiver finish events received just before midnight, so nothing new is written to that day. Only closed days can be replayed.
- **Staging table**: a temporary table where replay builds a day before swapping it in.

## How it runs

### Live path

1. **SDKs** (web, iOS, Android) batch events and send them to the collector. On a timeout, 429 or 5xx they resend the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events on the device for up to 7 days, so a duplicate can arrive up to 7 days after the first copy. That is why dedup exists.
2. **Collector** (several instances may run) validates each event, adds `received_at`, and writes it to the raw log in the partition chosen by `event_id`.
   - It returns 202 only after the whole batch is durably in the raw log. If the write fails it returns 5xx and the SDK retries.
   - An event is valid if `event_id` and `device_id` are present and it is at most 32 KB.
   - Malformed events are rejected one at a time and listed in the response. The rest of the batch is still accepted. Clients never retry rejected events. Rejected events go to a reject bucket for inspection only; nothing reprocesses them.
3. **Raw log** holds accepted events for 14 days. The archiver and the live processor each read all of it. Because collector clocks differ slightly and writes race, log order can differ slightly from `received_at` order.
4. **Archiver** copies every accepted event, duplicates included, exactly as received, into hourly archive files. It does not deduplicate or reorder. The file is chosen by the UTC date and hour of `received_at`, so one UTC day is exactly the 24 hourly file groups under that date. If it fails or falls behind, it resumes from where it stopped; the log keeps events for 14 days.
5. **Live processor** runs one worker per raw log partition, in parallel. Each worker handles its events one at a time, in log order. For each event:
   1. Dedup: look up `event_id` in the KV store. If present, drop the event.
   2. Enrich with geo-IP and user agent. If enrichment fails, continue with empty enrichment fields; a later replay fills them in.
   3. Load into the `events_clean` partition for the UTC day of `received_at`.
   4. Record the `event_id` in the KV store, with a key expiry of 8 days (the 7-day retry window plus margin).

   The worker finishes step 4 before it reads the next event. All copies of an `event_id` share a partition, so a close second copy is looked up after the first is recorded, and is dropped.

   If the KV store or the load fails, the worker stays where it is in the raw log and retries, so events are delayed, not lost. A crash between load and record can let one duplicate through live; replay removes it.
6. **Monitoring** alerts on how far the archiver and the live processor are behind the raw log (lag). High lag breaks the 5-minute goal and can break the 2-hour margin of a closed day. It is also the only way we would notice a stuck live processor. The 5-minute goal is measured from `received_at` to the event being queryable in `events_clean`.

### Replay path

7. **Replay job.** An operator starts it for one UTC day. Before starting, the operator checks on the monitoring lag view that the archiver and live processor have passed the end of that day. The job itself checks only that the day is closed, and refuses otherwise. It reads only the archive, never the live KV store or the raw log, so it does not slow live ingestion or change live dedup state. It:
   1. Lists the hourly archive files for the day and for the 7 days before it.
   2. Re-runs dedup with its own temporary set of seen `event_id`s, created for this run and thrown away at the end. The 7 earlier days are scanned so a copy is dropped if the same `event_id` was received earlier, as live would have done. "Earlier" means lower `received_at`.
   3. Re-runs enrichment with the fixed code.
   4. Writes the result for the replayed day only to a staging table, then atomically replaces that one day partition of `events_clean`. Dashboards see either the old day or the new day, never a half-built one.

   The new partition has no duplicates that live let through and no events with empty enrichment. Live and replay could pick different winners only for copies received at almost the same instant.

   Retries that arrive on a later day sit in that later day's partition. Live normally drops them, because the first copy's key is in the KV store. A copy live let through after a crash stays until that later day is replayed, and that replay drops it through its 7-day look-back.
8. If replay fails before the swap, the day partition is untouched and still holds the live data. The staging table is discarded and the operator starts the job again. The swap is atomic, so a failure during it leaves either the old or the new day. Rerunning is always safe, because the job rebuilds from the archive.

## When things fail

| Where | What happens |
|---|---|
| Collector cannot write to the raw log | 5xx, so the SDK retries the same batch. Duplicates are removed later. |
| Collector is down | The SDK sees a timeout and retries. |
| KV store down or slow | Live processor stops advancing and retries. Events are delayed. The 14-day log retention covers long outages. |
| Load into `events_clean` fails | Same: no advance, retry. |
| Enrichment fails | Event is loaded with empty enrichment fields. Replay repairs it. |
| Crash between load and KV record | One duplicate may reach `events_clean`. Replay removes it. |
| Archiver fails or lags | It resumes from where it stopped. The operator does not replay a day until it has caught up. |
| Replay fails | Partition unchanged. Operator reruns. |

## Open questions

- Bot filtering: should suspected bot traffic be dropped or kept with a flag? Product has not decided; not chosen here.
- Lag alerts: who is alerted, at what threshold, and what they do is not decided.
- Reject bucket: how long it is kept is not decided.
- An event that can never be loaded makes the live processor retry forever and block the events behind it in the same raw log partition. Whether to skip it and rely on replay is not decided.
- Where the replay job keeps its temporary seen-set is not decided.
- How replay breaks ties between copies with identical `received_at` is not decided.
- Whether the replay job should check lag itself, instead of relying on the operator, is not decided.
