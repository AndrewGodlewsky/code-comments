# Clickstream ingestion plan

## What this is

This pipeline takes click and screen-view events from the website and the iOS and Android apps. It removes duplicates, adds geo-IP and user-agent details, and loads the result into the warehouse table `events_clean`, which has one partition per UTC day. A live event must be queryable within 5 minutes of reaching us.

The raw log, object storage, the KV store and the warehouse already exist. The collector is new.

The main flow: the apps and the site send batches to the collector. The collector stores each accepted event in the raw log before it confirms the batch. Two readers work from that log, each at its own pace. The Archiver keeps a full copy of every accepted event in object storage. The Live processor removes duplicates, enriches events and loads the warehouse. A replay rebuilds one closed day from the archive, so a fix to enrichment reaches old data without touching live state.

Why it is shaped this way: the collector confirms as soon as the log holds the events, so clients can stop retrying. The archive holds everything, so any closed day can be rebuilt. The replay never writes to live state, so it cannot change live deduplication.

## Terms

- **Event**: one click or screen view. It has an `event_id` (a UUID the client makes), a `device_id`, and a client timestamp (when the client says it happened).
- **Batch**: up to 100 events sent together in one HTTPS request.
- **Request metadata**: the client IP address and the User-Agent header of the HTTPS request that carried an event. The collector stores it beside the event, for geo-IP and user-agent enrichment.
- **SDK**: the code in the website and mobile apps that batches events and sends them. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days.
- **Collector**: the new service that receives batches from the SDKs.
- **received_at**: the server time the collector stamps on each accepted event when it arrives.
- **UTC day**: a calendar day in UTC time. An event belongs to the UTC day of its `received_at`, never of its client timestamp. That day sets its partition and which replay covers it.
- **Raw log**: the existing replicated, append-only log (Kafka-style). It keeps events for 14 days.
- **Durably stored**: the raw log has acknowledged the append. How many copies must confirm is set by the log itself.
- **Log position**: how far a reader has read in the raw log. Each reader keeps its own. It moves forward only after that reader's work is safely stored.
- **Archiver**: the reader that copies every accepted event from the raw log into the archive.
- **Archive**: object storage holding hourly files of accepted events. Each file holds the events whose `received_at` falls in one UTC hour. A lifecycle rule deletes files after 90 days.
- **Live processor**: the reader that removes duplicates, enriches events and loads `events_clean`.
- **Reject bucket**: storage for malformed events.
- **KV store**: a key-value store. Each key can have a TTL (time to live), after which the store deletes it.
- **Set-if-absent write**: a write that succeeds only when the key does not exist yet. For a given key, only one writer can succeed.
- **Duplicate**: a later copy of an event whose `event_id` was already seen. Only the first copy counts.
- **events_clean**: the warehouse table. Each UTC day is one partition.
- **Atomic swap**: the warehouse replaces one day partition in a single step. Readers see the old day or the new day, never a mix.
- **Staging table**: a temporary table that holds a rebuilt day before it replaces the live day.
- **Replay state**: the set of `event_id`s that one replay run has seen. The replay job holds it. It is not the live KV store.
- **Consumer lag**: how far behind a reader is from the newest event in the raw log.

## Live path

1. **The SDK sends a batch.** This starts when the app or site has events to send. Each event carries `event_id`, `device_id` and its client timestamp. The SDK sends up to 100 events per batch over HTTPS to the collector. If the request times out or gets a 429 or 5xx response, the SDK resends the same batch with the same `event_ids`. It backs off exponentially, from 1 s up to 5 minutes. Unacknowledged events stay in the on-device buffer for up to 7 days, so a retry can reach us up to 7 days after the first copy.
   - Data kept: the events stay in the on-device buffer until acknowledged.
   - If it goes wrong: the SDK keeps retrying with backoff. Retries are safe because the duplicates are dropped later.

2. **The collector validates and stores the batch.** This starts when a batch arrives. It checks each event on its own. An event is malformed if it is missing `event_id`, missing `device_id`, or over 32 KB. Malformed events are rejected and written to the reject bucket. The rest of the batch is still accepted. For each accepted event, the collector stamps `received_at`, attaches the request metadata, and appends the event to the raw log. It returns 202 only after the raw log has acknowledged every accepted event. The 202 response lists the rejected events. Clients never retry rejected events.
   - Data kept: accepted events in the raw log. Rejected events in the reject bucket.
   - If it goes wrong: if the collector cannot store the accepted events, it does not return 202, so the SDK resends the whole batch (step 1). Copies written before the failure are dropped later as duplicates.

3. **The Archiver keeps a copy.** This starts when new events appear in the raw log. It reads them in log order. It writes each event, exactly as received and with its request metadata, to the archive file for the UTC hour of its `received_at`. It keeps every accepted event, duplicates included, for 90 days. An hour's file counts as complete once the Archiver has read the log past the end of that hour. The Archiver moves its log position forward only after the file is written.
   - Data kept: the archive, for 90 days.
   - If it goes wrong: if it crashes before it moves its log position, it writes some events again, so the archive can hold a copy twice. Replay removes these extra copies.

4. **The Live processor removes duplicates, enriches and loads.** This starts when new events appear in the raw log. It reads small groups of events, in log order. For each accepted event:
   1. It makes a set-if-absent write of the event's `event_id` to the KV store, with a TTL longer than 7 days, so a retry on day 7 is still caught. If the write fails because the key already exists, the event is a duplicate and is dropped. The archive still keeps it.
   2. If the write succeeds, the event is the first copy. The processor adds geo-IP and user-agent details, using the request metadata.
   3. It loads the group's first-copy events into the `events_clean` partition for the UTC day of each event's `received_at`. It loads the whole group in one write, not row by row.

   After the group is loaded, the processor moves its log position past the group. Several Live processor instances can run at once. The set-if-absent write makes sure only one of them wins each `event_id`.
   - Data kept: the KV key for each event, until its TTL expires. The loaded rows stay in `events_clean`.
   - If the warehouse load of a group fails: the processor retries the same group. It does not check the KV store again for those events, because they are already marked. Its log position does not move until the load succeeds.
   - If it crashes after the KV write but before the load: the event stays marked, so the restarted processor drops it and it is never loaded. This is an open question.
   - If it crashes after the load but before it moves its log position: the group is read again. Its events are already marked, so they are dropped. Nothing is loaded twice.
   - If the KV store is down or slow: the processor waits and retries. It does not load events without the check, which could load duplicates. It does not skip them, which could lose first copies.

5. **Monitoring.** Alerts fire on consumer lag. The goal is that live events are queryable within 5 minutes of reaching us. What an alert triggers, and which consumers it covers, is open.

## Replay path

A replay rebuilds one UTC day from the archive. Only closed days can be replayed. A day closes at 02:00 UTC the following day.

1. **An operator starts a replay** for one closed UTC day. This is usually done after an enrichment fix, such as a geo-IP or user-agent change. The operator starts it by hand. An operator must always be able to start it. If the day is not closed, the replay is not allowed.

2. **The replay reads, dedups and enriches the day.** It reads the 24 hourly archive files for that UTC day, by `received_at`. It keeps the first copy of each `event_id` in its replay state and drops later copies. It enriches each first copy with the same fixed geo-IP and user-agent logic as the live path, so the rebuilt day matches the fix. It writes the result to its own staging table. It never writes to the live KV store, so it cannot change live dedup state. It must not slow live ingestion.
   - The replay state is built from scratch for each run. It holds only the `event_id`s read from that run's files. It is discarded when the run ends.
   - The replay is complete when all 24 files have been read and all their first-copy rows are in the staging table.
   - If it goes wrong: nothing live has changed yet. See step 4.

3. **The atomic swap.** When the staging table is complete, the warehouse replaces that day's partition in `events_clean` in one atomic step. Dashboards see the old day or the new day, never a half-rebuilt day. New events get a later `received_at` day, so they normally do not add to the closed day. Late live events are an open question.

4. **If the replay fails before the swap,** the live partition is unchanged. Dashboards keep reading it. The atomic swap is the only step that changes the live day.

## What happens when things fail

| Failure | What happens | What covers it |
|---|---|---|
| SDK gets a timeout, 429 or 5xx | The SDK resends the same batch, backing off from 1 s up to 5 min | Same `event_id`s, so the Live processor drops duplicates |
| Device is offline | Unacknowledged events stay on the device for up to 7 days | A retry can arrive up to 7 days after the first copy. The KV TTL is longer than 7 days |
| Malformed event | Rejected, listed in the response, and put in the reject bucket. The SDK never retries it | Handling of the reject bucket is open |
| Collector cannot store accepted events | No 202. The SDK resends the whole batch | The Live processor drops copies already written |
| Duplicate arrives while its KV key exists | Dropped by the Live processor | The archive keeps it. First copy wins |
| Duplicate arrives after its KV key expired | It would be loaded a second time | The TTL is set longer than 7 days |
| Two Live processor instances see the same `event_id` | Only one set-if-absent write succeeds. The other drops the event as a duplicate | The set-if-absent write |
| Live processor crashes after its KV write but before the warehouse load | The event is marked seen. The restarted processor drops it, so it is never loaded | Open. How to recover it is not specified |
| Warehouse load of a group fails | The processor retries the same group. Its log position does not move | The retry. If the processor restarts during a long failure, the row above applies |
| Live processor crashes after the load but before it moves its log position | The group is read again. Its events are already marked, so they are dropped | The set-if-absent write. No second load |
| KV store is down or slow | The processor waits and retries. It neither loads nor skips events without the check | Live events miss the 5-minute goal while it lasts. The lag alert |
| Archiver crashes before it moves its log position | It writes some events again, so the archive can hold a copy twice | The archive keeps every copy. Replay drops the extra copies |
| Archiver is behind at the 02:00 UTC close | A replay of that day could miss events not yet archived | Open. Only closed days can be replayed, but the rule does not check the archive |
| Archiver or Live processor falls behind or is down | Events wait in the raw log, which keeps them for 14 days | Once a reader is more than 14 days behind, see Open questions |
| Live processor lags | Live events miss the 5-minute goal | The lag alert. Its response is open |
| Replay fails before the swap | The live day in `events_clean` is unchanged | The atomic swap is the only step that changes it |
| Replay requested for a day that is not closed | Not allowed | Only closed days can be replayed |
| Two replays of the same day run at once | Each writes its own staging table. The last swap decides what dashboards see | Both read the same archive. Blocking a second run is open |

## Open questions

- Bot traffic: drop it, or keep it with a flag. Product has not decided. This plan does not choose.
- What the consumer lag alert triggers, and which consumers it covers.
- Reject bucket: who reads it, whether rejected events are reprocessed, and how long they are kept. The 90-day rule covers accepted events only.
- A crash between the KV write and the warehouse load can leave an event marked as seen but never loaded. How this is recovered is not specified.
- A replay must find the first copy of each event, which can have arrived up to 7 days before the day being rebuilt. The replay state sees only that day's archive files. How the replay finds an earlier first copy is not specified.
- If the Live processor lags past 02:00 UTC, late live events can arrive for a closed day. How they are handled is not specified.
- If the Archiver is behind at 02:00 UTC, or the raw log does not keep events in `received_at` order, an hour's file may be incomplete when a replay reads it. How an hour's file is written while events still arrive, and when it is sealed, is not specified either.
- If a reader is down for more than 14 days, the log loses those events. Whether the archive still has them depends on the Archiver, which is not specified.
- The value stored under each KV key is not specified. Only the key and its TTL are.
- The KV store must support a set-if-absent write with a TTL. The brief does not say whether the store does.
- Whether the client IP address may be stored, and for how long, is not specified. The plan stores it for enrichment.
- Whether a second replay of a day should wait for a running one, or be blocked, is not specified.
- Why the day closes at 02:00 UTC, rather than at midnight, is not given. The rule stands as stated.