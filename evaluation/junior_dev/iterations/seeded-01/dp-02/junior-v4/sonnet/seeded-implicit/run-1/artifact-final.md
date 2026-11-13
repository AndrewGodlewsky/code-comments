# Clickstream ingestion plan

Website and app events reach a collector, which stores them durably in the raw log. Two readers then work independently. The live processor deduplicates and enriches events into the warehouse table `events_clean` within 5 minutes. The archiver keeps every event untouched for 90 days. An operator can rebuild a closed day from the archive.

## Terms

- **Event**: one click or screen view, with `event_id` (client UUID), `device_id` and a client timestamp.
- **received_at**: server time the collector stamps on an event. Its UTC day decides the partition of `events_clean` and which replay covers the event. The client timestamp is never used for this.
- **Raw log**: the existing replicated append-only log (14-day retention). Only the collector writes to it. The archiver and the live processor each read it independently. A position in it is a log offset.
- **Archive**: hourly files in object storage, grouped by `received_at` hour, with a 90-day lifecycle rule.
- **Dedup state**: key-value store entries keyed by `event_id`, used only by the live processor. Each entry holds the log offset of the copy that claimed it.
- **Closed day**: a UTC day that is over and past 02:00 UTC the next day. This gives the live processor and archiver time to finish the day.
- **Lag**: how far a reader's committed offset is behind the newest entry in the raw log.

## How it runs: live path

1. **SDK (web, iOS, Android)** sends a batch of up to 100 events over HTTPS.
   - Starts: a client event.
   - Does: on a timeout, 429 or 5xx it resends the whole batch with the same `event_id`s, backing off exponentially from 1 s to 5 minutes. Mobile SDKs keep unacknowledged events on the device for up to 7 days, so a copy can arrive 7 days late. It never retries events the collector rejected.
   - Data: the on-device buffer.
   - If it fails: it keeps retrying as above.
2. **Collector** receives a batch.
   - Does: checks each event, adds `received_at`, and writes the valid ones to the raw log. An event is rejected if it lacks `event_id` or `device_id`, or is over 32 KB. Rejected events are listed in the response and copied to a reject bucket (kept 14 days for debugging, never reprocessed). The rest of the batch is still accepted. It returns 202 only after the raw log confirms the write.
   - Data: the raw log and the reject bucket.
   - If it fails: if the log write fails, it returns 5xx and the SDK retries.
3. **Archiver** reads every event from the raw log, duplicates included.
   - Does: writes each event unchanged to the hourly archive files.
   - Data: the archive, and its own committed offset.
   - If it fails: it resumes from its committed offset. Its lag must stay far below 14 days, or events leave the log before they are archived.
4. **Live processor** reads the raw log in small batches. For each event it:
   - Claims `event_id` in the dedup state with set-if-absent, storing the event's log offset. The first copy to claim it wins.
   - Drops the event if the claim holds a different offset (a later copy). Processes it if the claim holds the same offset (the same event read again after a crash).
   - Enriches it (geo-IP, user agent) and appends it to the `received_at` day's partition of `events_clean`.
   - Commits its log offset only after the batch is loaded.
   - Data: dedup state, `events_clean`, and its own committed offset. Claims expire after 8 days. A retry arrives at most 7 days after the first copy, so a duplicate cannot outlive its claim.
   - If it fails: it does not commit, restarts from its committed offset and reprocesses the batch. An event loaded just before a crash can appear twice in the live day. This is accepted, since a duplicate row is better than a missing one. The next replay of that day removes it.
5. **Monitoring** watches lag.
   - Does: a live processor lag above 3 minutes alerts on-call, because the 5-minute goal is at risk. An archiver lag above 1 hour also alerts on-call.

## How it runs: replay

An operator starts a replay by hand for one UTC day, usually after fixing an enrichment bug. It reads the archive, never the raw log, so live ingestion is unaffected. It never touches the live dedup state.

1. **Check.** The job refuses to run unless the day is closed and the archiver has committed past the end of that day. Otherwise the archive could still be missing the day's last events.
2. **Deduplicate.** The job reads the archive files for that day and for the 7 days before, because an earlier copy may have arrived on an earlier day. Using its own temporary state, it keeps an event only if no copy with a smaller `received_at` exists.
3. **Enrich.** It enriches the kept events with the current code and writes them to a staging table.
4. **Swap.** It compares the staging row count with the number of events kept in step 2. If they match, it atomically replaces that day's partition of `events_clean`, so dashboards see either the old day or the new day. If they differ, the job fails.
5. **If any step fails,** the old partition stays in place. The operator investigates and reruns the job.

Replay and live processing never write the same partition, because a closed day has ended and `received_at` is server time.

Replay changes only the day it is run for. If a later copy is dropped because its first copy sits in an earlier day, that earlier partition is left as it is, even if it was enriched with older code. To refresh it, the operator replays that day too.

## What happens when things fail

| Failure | Result |
| --- | --- |
| Raw log write fails | Collector returns 5xx. The SDK retries. |
| Live processor crashes, or enrichment fails or is slow | It does not commit, resumes from its committed offset and reprocesses. A row may be duplicated until replay. Lag alerts fire if this lasts. |
| Archiver crashes | It resumes from its committed offset. Lag alerts fire if this lasts. |
| Replay fails or row counts differ | The old partition is unchanged. Investigate and rerun. |

## Open questions

- Bot traffic: product has not decided whether suspected bots are dropped or kept with a flag. This plan does not choose. Bot handling would sit in the live processor and the replay enrichment, and is not built yet.
- Who is on-call for the lag alerts, and who owns the raw log platform, is not known.
- The 3-minute and 1-hour alert thresholds and the 14-day reject retention are proposals, not requirements.
- What the geo-IP and user-agent lookups read (for example the client IP, and which database), and how long they may take, is not specified.
