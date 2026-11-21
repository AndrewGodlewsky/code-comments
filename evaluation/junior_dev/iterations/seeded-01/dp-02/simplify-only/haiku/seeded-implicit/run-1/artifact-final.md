# Clickstream ingestion plan

## What this is

Events from our website and our iOS and Android apps reach a collector, which stores them before it replies. The live path removes duplicates, adds geo-IP and user-agent data, and loads the events into the `events_clean` table, where live events are queryable within 5 minutes of reaching the collector. A replay rebuilds one closed UTC day from the archive and swaps it into `events_clean` in one step.

## Terms

- **Event**: one click or screen view. It has a client-made `event_id` (UUID), a `device_id` and a client timestamp.
- **Batch**: up to 100 events sent together in one HTTPS request.
- **received_at**: the server time the collector stamps on each accepted event. Its UTC day decides the event's partition and which replay covers it. The client timestamp is never used for this.
- **First copy**: when the same `event_id` arrives more than once, the copy with the earliest `received_at` wins. Later copies are dropped from `events_clean` but kept in the archive.
- **Raw log**: the replicated, append-only log. It keeps 14 days.
- **Archive**: object storage holding hourly files of every accepted event, exactly as received, duplicates included.
- **KV store**: a key-value store. The live path keeps one key per `event_id` with a 7-day TTL.
- **Closed day**: a UTC day whose following day has reached 02:00 UTC. Only closed days can be replayed.
- **Reject bucket**: storage for malformed events.

## Live path

1. **SDK sends a batch.**
   - *Starts when:* a batch is ready to send.
   - *Does:* sends up to 100 events with `event_id`, `device_id` and client timestamp, over HTTPS, to the collector.
   - *Keeps:* unsent events, in an on-device buffer for up to 7 days.
   - *If it fails:* on a timeout, 429 or 5xx, it resends the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. It never resends events the collector rejected.

2. **Collector accepts the batch.**
   - *Starts when:* a batch arrives.
   - *Does:* checks each event. `event_id` and `device_id` must be present, and the event must be 32 KB or less. Rejected events go to the reject bucket and are listed in the response. Each accepted event gets `received_at` and is written to the raw log, keyed by `event_id` so all copies of one event go to the same partition. The collector replies 202 only after that write is durable.
   - *Keeps:* the raw log, for 14 days.
   - *If it fails:* if the log write fails, it replies 429 or 5xx, and the SDK resends the batch.

3. **Archiver copies events to the archive.**
   - *Starts when:* new raw log entries appear.
   - *Does:* writes every accepted event, unchanged, into hourly files. It does no deduplication.
   - *Keeps:* the archive, for 97 days.
   - *If it fails:* it resumes from its last saved log position. The log keeps only 14 days, so lag must be caught long before that.

4. **Live processor loads `events_clean`.**
   - *Starts when:* it reads an event from the raw log. It reads each `event_id`'s copies in log order.
   - *Does:*
     - If the KV store already has the `event_id`, the event is a duplicate. Drop it. The archive still has it.
     - Otherwise, enrich the event with geo-IP and user agent, and load it into the `events_clean` partition for its `received_at` day.
     - Then write the `event_id` key to the KV store with a 7-day TTL.
   - *Keeps:* `events_clean`, and the KV keys.
   - *If it fails:* it restarts from its last committed log position. Because the load happens before the key is written, a crash can load an event twice but cannot lose it. Replay repairs that day once it closes.

## Replay

A replay rebuilds one closed UTC day, usually after an enrichment fix. It reads only the archive, so live ingestion is not slowed. It never writes to the KV store, so live deduplication is unchanged.

1. **Operator requests a replay of day D.**
   - *Starts when:* an operator asks for it.
   - *Does:* refuses the request if day D is not closed yet. Otherwise it goes on to step 2.
   - *Keeps:* nothing.
   - *If it fails:* nothing has changed, so the operator can ask again.

2. **Replay reads the archive and picks the events to keep.**
   - *Starts when:* step 1 accepts the request.
   - *Does:* reads the hourly files for day D and the 7 days before it. For each event received on day D, it keeps the event only if no copy in the archive has an earlier `received_at`. The 7-day lookback is needed because a first copy can be up to 7 days older than a retry.
   - *Keeps:* nothing new. The archive is unchanged.
   - *If it fails:* nothing is written. Run it again.

3. **Replay writes a staging table.**
   - *Starts when:* step 2 has chosen the events.
   - *Does:* enriches them with the current geo-IP and user-agent code, and writes them to a staging table for day D.
   - *Keeps:* the staging table, until step 4 finishes.
   - *If it fails:* drop the staging table. Live data and `events_clean` are untouched.

4. **Replay swaps the partition.**
   - *Starts when:* the staging table is complete.
   - *Does:* replaces partition D of `events_clean` with the staging table in one atomic step. Dashboards see either the old day or the new day, never a partly rebuilt one. Then it drops the staging table.
   - *Keeps:* the new partition in `events_clean`.
   - *If it fails:* the old partition stays in place. Run the replay again.

## What happens when things fail

| Failure | What happens | Who recovers |
|---|---|---|
| SDK is offline | Events wait in the device buffer for up to 7 days, then are resent. | SDK |
| Collector cannot write to the log | Replies 429 or 5xx. The SDK resends the batch. | SDK |
| Malformed event | Rejected, listed in the response, kept in the reject bucket. Clients never resend it. | Nobody, automatically |
| Retry copy of an event | Dropped by the live processor. Kept in the archive. | Nothing needed |
| Archiver or live processor falls behind | Lag alert fires. The process resumes from its saved position. Alert thresholds are not yet set. | Operator |
| Live processor crashes | Restarts from its last committed position. May load an event twice (see open questions). | Automatic restart |
| KV store is unavailable | Live processor pauses and does not load events without the dedup check. The raw log keeps them. | Automatic, when KV returns |
| Enrichment bug found | Replay the affected closed days. | Operator |
| Replay fails midway | `events_clean` is unchanged. Run the replay again. | Operator |
| Replay asked for an open day | Refused. | Operator waits until the day closes |

## Open questions

- **Bot traffic:** not decided. Product must choose between dropping suspected bot events and keeping them with a flag. This plan does not choose.
- **Crash duplicates:** a crash between the load and the KV write can load an event twice. The plan does not yet say how to prevent it.
- **Late copies:** retries are said to arrive within 7 days of the first copy. If one arrives later, live and replay may disagree about it. Not decided.
- **Closed day still behind:** if the live processor is still behind at 02:00 UTC, some events for the closed day may not be loaded yet. Not decided whether replay waits for them.
- **Archive length:** the archive is kept 97 days, not 90, so the 7-day lookback still has data for a 90-day-old day. Confirm this is acceptable.
- **Ties:** two copies with the same `received_at` have no defined winner.
- **Reject bucket retention** and **alert thresholds** are not set.