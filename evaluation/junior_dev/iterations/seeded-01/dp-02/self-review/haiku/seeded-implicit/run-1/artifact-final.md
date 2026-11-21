# Clickstream ingestion plan

This plan describes how click and screen-view events from our website and our iOS and Android apps reach one warehouse table, `events_clean`. The table is split into partitions, one per UTC day. UTC is the standard world time, so each day has the same start and end everywhere. Live events must be queryable within 5 minutes of reaching our servers.

## How the pieces fit

Live events flow in one direction:

apps and website → collector → raw log → live processor → `events_clean`

Two other pieces sit beside this flow:

- The **archiver** copies the raw log into the archive, for long-term storage.
- **Replay** rebuilds one day from the archive. It never reads the raw log.

## Terms

- **Event**: one click or screen view. Each event has a client-generated `event_id` (a UUID, a random unique identifier), a `device_id`, and a client timestamp set by the device.
- **Batch**: up to 100 events sent together in one HTTPS request.
- **received_at**: the time our collector received the event, stamped by our server. An event belongs to the UTC day of its `received_at`. That day decides its partition and which replay covers it. The client timestamp is stored but never used for this.
- **Duplicate**: a later copy of an event with the same `event_id`. The first copy we receive wins. Later copies are dropped from `events_clean` but are still kept in the archive.
- **Raw log**: a replicated, append-only log of accepted events. Append-only means new entries are added at the end and old entries are never changed. Replicated means copies are kept on several machines, so one machine failing does not lose data. Entries are kept for 14 days.
- **Archive**: accepted events, exactly as received, stored in object storage (a file store for large files) for 90 days.
- **KV store**: a key-value store, a database that maps a key to a value. Each key can expire after a set time, called its TTL (time to live). We use it to remember which `event_id`s have already been seen.
- **Atomic**: a step either fully happens or does not happen at all. No one can see a partial result.
- **Partition**: one day's slice of `events_clean`. The warehouse can replace one partition in a single atomic step.
- **Closed day**: a UTC day whose events are all in the archive and whose live processing has finished. A day closes at 02:00 UTC the following day.
- **Staging table**: a temporary table with the same shape as `events_clean`. It holds a rebuilt day until that day replaces the live partition.

## Live path

1. **SDKs (web, iOS, Android).** Each SDK groups events into batches of up to 100 and sends each batch to the collector. If a send times out, or the collector answers 429 (too many requests) or 5xx (server error), the SDK resends the same batch with the same `event_id`s. It waits longer before each attempt, starting at 1 second and growing up to 5 minutes. The mobile SDK keeps events it has not had confirmed in an on-device buffer for up to 7 days. So a retry can reach us up to 7 days after the first copy.

2. **Collector.** For each batch, the collector:
   - Checks each event. An event is malformed if it lacks `event_id` or `device_id`, or if it is over 32 KB. Malformed events are rejected one at a time and listed in the response. The rest of the batch is still accepted. Clients never retry rejected events.
   - Stamps each accepted event with `received_at`.
   - Writes the accepted events to the raw log. It returns 202 (accepted) only after that write is durably stored, meaning it will survive a machine failure. Rejected events go to a reject bucket, a separate store kept for inspection.

3. **Archiver.** Reads accepted events from the raw log and writes them unchanged to object storage, in hourly files. Object storage deletes each file 90 days after it was written. Duplicates are archived too, because the archive must hold every accepted event.

4. **Live processor.** Reads the raw log in order and handles each event as follows:
   - **Duplicate check.** Writes the `event_id` to the KV store only if that key does not already exist. The check and the write are one atomic step, so two copies arriving at the same moment cannot both pass. If the key already exists, the event is a duplicate and is dropped. Each key gets a TTL of at least 7 days, because a retry can arrive 7 days after the first copy.
   - **Enrich.** Adds a geo-IP lookup (an estimate of location from the IP address) and user-agent parsing (browser or app details read from the request header).
   - **Write.** Writes the event to `events_clean`, in the partition for its `received_at` day.

   This step must keep up, so that events are queryable within 5 minutes of arrival. Consumer lag is how far the processor is behind the end of the raw log.

5. **Replay.** Rebuilds one UTC day from the archive. This is usually needed after an enrichment bug is fixed. Only closed days can be replayed.
   1. The operator chooses a closed day, D.
   2. The replay reads archived events with a `received_at` on day D. It also reads archived events from the 7 days before D (days D-7 through D-1). Those earlier events are needed to find first copies, because a retry can arrive up to 7 days after the copy it repeats.
   3. Across that set, the replay keeps only the first copy of each `event_id`, meaning the copy with the earliest `received_at`. If a copy arrived on day D but its first copy arrived on an earlier day, that copy is dropped from day D. This is the same first-copy-wins rule the live path uses, so the rebuilt day matches what live would have produced.
   4. The replay enriches the kept events using the current, fixed code.
   5. The replay writes the result to a staging table, not to `events_clean`.
   6. The warehouse atomically replaces partition D in `events_clean` with the staging table. Dashboards see either the old day or the new day. They never see a partly rebuilt day.

   Replay reads only the archive. It never reads the raw log and never writes to the KV store. So it cannot change live deduplication state, and it does not compete with live ingestion for the raw log.

6. **Monitoring.** Track consumer lag, and alert when it threatens the 5-minute target. Also monitor collector errors and rejects, and the status of replay jobs.

## Open decision

- **Bot traffic: not yet decided.** Product has not decided whether suspected bot traffic should be dropped or kept with a flag. This plan does not choose. Either option changes the live processor (step 4) and the replay (step 5), so both steps must be updated when the decision is made.