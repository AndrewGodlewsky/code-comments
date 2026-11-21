# Clickstream ingestion plan

**Goal:** land click and screen-view events from the website and the iOS and Android apps in the warehouse table `events_clean`, deduplicated and enriched, with one partition per UTC day. Live events must be queryable within 5 minutes of reaching us.

**How it fits together:** clients send events to a new collector. The collector writes them to a durable log. Two readers consume that log. The archiver keeps a permanent-ish copy in object storage. The live processor removes duplicates, enriches and loads the warehouse. Replay rebuilds one past day from the archive, never from the live path.

**Terms used below**
- **Raw log**: the existing replicated append-only log (Kafka-style, 14-day retention).
- **Archive**: copies of raw events in object storage, kept 90 days by a lifecycle rule (the storage deletes files automatically after a set age).
- **KV store**: the existing key-value store, where each key can have a time-to-live (TTL) after which it is deleted.
- **Event day**: the UTC day of `received_at`, the server time the collector stamps on each event. It never comes from the client timestamp. The event day decides the partition and which replay covers the event.
- **First copy**: among all copies of an event (same `event_id`), the one we received earliest. Clients resend batches, so the same event can reach us more than once.
- **Enrich**: add geo-IP and user-agent fields to an event.
- **Staging table**: a temporary table in the same warehouse where a replayed day is built before it goes live.

## Live path

1. **Clients (web, iOS, Android) send batches.**
   - Each batch has up to 100 events and goes over HTTPS to the new collector service.
   - Each event carries a client-generated `event_id` (UUID), a `device_id` and a client timestamp.
   - On a timeout, 429 or 5xx, the client resends the same batch with the same `event_id`s. It backs off exponentially, from 1 s up to 5 minutes between tries.
   - The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days. A retry can therefore arrive up to 7 days after the first copy.
   - Clients never retry events the collector rejected.

2. **The collector validates, stamps and stores.**
   - It checks each event on its own. An event is rejected if `event_id` or `device_id` is missing, or if it is over 32 KB.
   - Rejected events are listed in the response. The rest of the batch is still accepted.
   - It adds `received_at` to every accepted event and writes the events to the raw log.
   - It returns **202 only after the raw log confirms a durable, replicated write**. If the write fails, it returns 5xx so the client retries.
   - It does not remove duplicates. Every accepted event is written, including repeats.

3. **The archiver copies the raw log to object storage.**
   - It writes accepted events exactly as received, duplicates included, in hourly files grouped by event day.
   - A lifecycle rule deletes files after 90 days, which meets the 90-day retention requirement.
   - The raw log keeps data for only 14 days, so the archive is the long-term record and replay reads from it. Alert if the archiver falls behind by more than a few hours, so the raw log never expires data that has not been archived.

4. **The live processor deduplicates, enriches and loads.** It reads the raw log in small batches and, for each event:
   1. **Dedup.** It does an atomic "set if absent" on the key `event_id` in the KV store. If the key was new, this is the first copy and the event continues. If the key already existed, the event is dropped. The first copy received wins.
      - **KV TTL:** 8 days. This covers the 7-day retry window plus a day of margin.
      - **Crash safety:** the KV value records the raw log position of the first copy. If the processor restarts and re-reads that same position, it sees its own record and treats the event as the first copy, not a duplicate. Without this, an event marked as seen but never loaded would be lost.
   2. **Enrich.** It adds the geo-IP and user-agent fields.
   3. **Load.** It loads the results into the partition of `events_clean` for the event day, in batches small enough to meet the 5-minute target.
   - *Assumption to confirm:* the warehouse can append rows to a partition. The only operation the brief guarantees is atomic replacement of a whole day partition.

## Replay (rebuild one UTC day)

An operator runs replay for a day D, usually after fixing an enrichment bug (geo-IP, user-agent).

5. **Check eligibility.**
   - Only closed days can be replayed. Day D closes at 02:00 UTC on D+1. The two hours allow the live processor to finish events received just before midnight.
   - The archiver must have written all of day D.
   - The archive must still hold day D and the 7 days before it (step 7 needs them). Since the archive keeps 90 days, D can be at most about 83 days old.

6. **Read the archive, not the raw log.** Replay reads the archived files for day D. It does not touch the raw log or the live consumers, so it cannot slow live ingestion.

7. **Deduplicate inside the replay job, not in the KV store.**
   - Replay never reads or writes the live KV store, so live dedup state is unchanged.
   - It sorts events by `received_at`, using raw log position to break ties. For each `event_id`, only the earliest copy can survive.
   - It also scans the archive for the 7 days before D. If an `event_id` appeared there, its first copy belongs to an earlier day, so the copy in day D is dropped. This reproduces what live dedup did.

8. **Enrich with the fixed code, then write to the staging table.** Live data and dashboards are unaffected while staging is built.

9. **Swap atomically.**
   - First check staging (row count, no duplicate `event_id`s). If a check fails, stop and alert. `events_clean` is untouched.
   - Then replace day D's partition in `events_clean` with the staging data in a single atomic operation. Dashboards see either the old day or the complete new day, never a half-rebuilt one.
   - The live processor writes only to the current event day. A closed day receives no live writes, so the swap cannot race with them.

## Monitoring

10. Alert on these:
    - raw log consumer lag for the archiver and for the live processor;
    - end-to-end freshness against the 5-minute target;
    - collector reject rate and 5xx rate;
    - the gap between the archiver's position and the 14-day raw log retention limit;
    - replay failures, and staging checks that fail before the swap.

## Open decision

- **Bot traffic: drop or keep with a flag?** Product has not decided, and this plan does not choose. Either option is one extra step: in the live processor right after dedup (step 4), and in replay right after dedup (step 7). The raw log and archive are unaffected because they keep every accepted event. Once the decision is made, replay can apply it to past days.
