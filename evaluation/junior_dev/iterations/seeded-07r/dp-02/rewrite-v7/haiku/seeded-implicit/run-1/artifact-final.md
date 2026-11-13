# Clickstream ingestion plan

This pipeline takes click and screen-view events from our website and our iOS and Android apps, removes duplicates, adds enrichment, and loads them into one warehouse table, `events_clean`. The table has one partition per UTC day. Live events must be queryable within 5 minutes of reaching us. An operator can also rebuild one closed day from the archive, usually after an enrichment bug fix. The collector writes every accepted event to a raw log and an archive first, so any day can be rebuilt later. The live path and the replay share no state, so a replay cannot change live deduplication.

## Terms

- **SDK**: the code inside our website and mobile apps that collects events and sends them.
- **Event**: one click or screen view. It has an `event_id` (a UUID the client makes), a `device_id` and a client timestamp.
- **Batch**: up to 100 events sent together over HTTPS.
- **Collector**: our new HTTPS service that receives batches.
- **`received_at`**: the server time the collector stamps on each accepted event. An event's UTC day is the day of `received_at`, never of the client timestamp. That day sets its partition and which replay covers it.
- **Raw log**: a replicated, append-only log (Kafka-style). It keeps events for 14 days.
- **Archive**: object storage, meaning a store of files. Its lifecycle rule deletes files automatically after a set age.
- **Reject bucket**: a separate object storage area for malformed events.
- **KV store**: a key-value store where each key expires after its own TTL (time to live).
- **Duplicate**: an event whose `event_id` we already accepted. The first copy wins. Later copies are dropped from `events_clean`.
- **Partition**: the slice of a table that holds one UTC day.
- **Staging table**: a temporary table that holds a rebuilt day before it goes live.
- **Atomic replace**: the warehouse swaps one day partition for another in one step. Readers see the old day or the new day, never a mix.
- **Closed day**: a UTC day closes at 02:00 UTC the next day. Only closed days can be replayed.

## Live path

1. **SDK sends batches.** This starts when an app or page has events. Each batch holds up to 100 events. The SDK sends it over HTTPS. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days. If the SDK gets a timeout, a 429 or a 5xx, it resends the same batch with the same `event_id`s. It waits between tries, backing off exponentially from 1 s up to 5 minutes. So a retry can reach us up to 7 days after the first copy. The SDK never retries events the collector rejected.

2. **Collector validates and stores.** This starts when a batch arrives.
   - It checks each event. An event is malformed if it lacks `event_id` or `device_id`, or if it is over 32 KB.
   - It rejects malformed events one at a time. It writes them to the reject bucket and lists them in the response. The rest of the batch is still accepted.
   - It stamps each accepted event with `received_at`.
   - It writes accepted events to the raw log.
   - It returns 202 only after the batch is durably stored. If storage fails, it does not return 202. It returns a timeout or 5xx, so the SDK retries.

3. **Archiver keeps a copy.** This starts when events appear in the raw log. It writes every accepted event, duplicates included, to the archive. It writes hourly files and does not change the events. The lifecycle rule deletes each file after 90 days. If the archiver stops, events wait in the raw log, which keeps them for 14 days.

4. **Live processor loads `events_clean`.** This starts when events appear in the raw log. For each event, in order:
   - It looks up `event_id` in the KV store. If the key exists, the event is a duplicate. It is dropped from `events_clean`. Its archive copy stays.
   - If the key does not exist, it writes the key with a TTL of at least 7 days. The TTL must cover the 7-day retry window, so late retries are still caught.
   - It enriches the event with a geo-IP lookup and user-agent parsing.
   - It loads the event into the `events_clean` partition for the UTC day of `received_at`.
   If the KV store or the warehouse is unavailable, the processor stops at the event it has not finished. The event stays in the raw log and lag rises.

5. **Monitoring.** Alert on consumer lag, because the 5-minute target applies to live events.

## Replay path

Replay rebuilds one closed day. It runs as its own job, separate from the live path, so it does not slow live ingestion.

1. **Operator starts a replay.** The operator names one UTC day. The job refuses the request unless that day is closed. A day is closed from 02:00 UTC on the following day.
2. **Job reads the archive.** It reads the archived hourly files whose `received_at` falls in that day. It applies first-copy-wins using the whole archive, including earlier days. An event is kept only if no copy with an earlier `received_at` exists. It never writes to the KV store.
3. **Job enriches.** It applies the current enrichment code to each kept event.
4. **Job writes to staging.** It writes the results to a staging table. It does not touch `events_clean` yet.
5. **Job swaps the day in.** It atomically replaces that day's partition in `events_clean` with the staging table contents. Dashboards never see a half-rebuilt day.

## What happens when things fail

| Step | What fails | What happens |
|---|---|---|
| SDK to collector | Timeout, 429 or 5xx | SDK resends the same batch with the same `event_id`s, backing off from 1 s up to 5 minutes. |
| Collector | Event missing `event_id` or `device_id`, or over 32 KB | That event is rejected and listed in the response. The rest of the batch is accepted. The SDK does not retry it. |
| Collector | Durable storage fails | No 202 is returned. The SDK retries the batch. |
| Archiver | Stops | Events wait in the raw log for up to 14 days. |
| Live processor | KV store or warehouse is down | Processing stops at the unfinished event. Lag rises and an alert fires. |
| Replay | Day is not closed | Request is refused. |
| Replay | Fails before step 5 | `events_clean` is unchanged. The staging table can be discarded and the replay run again. |

## Open questions

- **Bot traffic is not decided.** Product has not decided whether suspected bot events are dropped or kept with a flag. This plan does not choose. The steps above do not filter bots.
- **Late archiving.** If the archiver is down for more than 14 days, events not yet archived are lost. The brief does not say how to prevent this.
- **Write order in step 4.** The plan does not say what happens if the warehouse load fails after the KV key is written. The event would then be lost, because its retry would be dropped as a duplicate.
- **Exact KV TTL.** The TTL is at least 7 days. The exact value is not set.
- **Reject bucket retention.** The 90-day rule covers accepted events only. How long rejected events are kept is not stated.