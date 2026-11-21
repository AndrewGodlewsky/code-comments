# Clickstream ingestion plan

## Summary

Apps and the website send events in batches to a collector. The collector checks each event, stamps it with server time and writes it to a raw log. Two readers consume that log. The live processor removes duplicates and loads new events into `events_clean` within 5 minutes. The archiver keeps every copy for 90 days. A replay rebuilds one closed UTC day from the archive and swaps it into `events_clean` in one step.

There is no clickstream pipeline today. The raw log, key-value store, archive and warehouse already exist. The collector, live processor, archiver and replay job are new.

## Terms

- **Raw log**: the existing replicated, append-only log. It keeps entries for 14 days and holds every accepted event, duplicates included. Each entry has an offset, which is its position in the log.
- **Archive**: existing object storage with hourly files and a 90-day lifecycle rule. Entries are stored unchanged, with their offsets.
- **Dedup store**: the existing key-value store. The key is `event_id`. Each key expires after 8 days.
- **Reject bucket**: where malformed events are written, one at a time, with a reason.
- **Day**: the UTC date of an event's `received_at`. It decides the event's partition and which replay covers it.
- **Closed day**: a day whose next day has reached 02:00 UTC. The wait covers a request stamped just before midnight that is still being written, and live processor lag.

## Live path

### 1. SDK sends

- **Starts when:** the app or website has events to send.
- **What it does:** sends them over HTTPS in batches of up to 100. Keeps unacknowledged events in an on-device buffer for up to 7 days. On a timeout, 429 or 5xx, resends the same batch with the same `event_id`s, backing off from 1 second up to 5 minutes. Never resends rejected events.
- **Keeps its data:** the on-device buffer.
- **If it fails:** the batch is resent as above. A retry can arrive up to 7 days after the first copy.

### 2. Collector

- **Starts when:** a batch arrives.
- **What it does:**
  - Rejects each malformed event, one at a time. An event is malformed if it lacks `event_id` or `device_id`, or is over 32 KB. Each rejected event goes to the reject bucket with a reason.
  - Stamps `received_at` (server time) on the other events and writes them to the raw log.
  - Does not remove duplicates.
  - Returns 202 only after the raw log confirms the write. The response lists rejected events by batch position and reason.
- **Keeps its data:** accepted events in the raw log; rejected events in the reject bucket.
- **If it fails:** if the raw log write or the reject bucket write fails, it returns 5xx for the batch. The SDK resends it. Events already in the raw log become duplicates, which are kept.

### 3. Archiver

- **Starts when:** new raw log entries appear.
- **What it does:** writes every entry, unchanged and with its offset, to the hourly archive file, duplicates included. Commits its offset after the write.
- **Keeps its data:** the archive, and its own committed offset in its own consumer group.
- **If it fails:** it resumes from its committed offset. The lag alert fires (step 6).

### 4. Live processor

- **Starts when:** new raw log entries appear.
- **What it does:** handles one batch at a time, in log order. For each batch:
  1. Drops an event if its `event_id` is in the dedup store, or if an earlier event in the same batch has that `event_id`. The first copy wins.
  2. Adds geo-IP and user-agent fields. If a lookup errors, keeps the event with empty fields and sets `enrich_status = failed`.
  3. Loads each remaining event into the `events_clean` partition for its `received_at` day.
  4. Writes the `event_id`s of the loaded events to the dedup store, once for the batch, with an 8-day TTL.
  5. Commits its offset.
- **Keeps its data:** its committed offset in the raw log; `event_id` keys in the dedup store; rows in `events_clean`.
- **If it fails:**
  - The dedup check fails or is slow (step 4.1): it stops before loading and does not commit. Events wait in the raw log for up to 14 days. The lag alert fires.
  - The load fails (step 4.3): it writes no keys, does not commit, and retries the batch.
  - The dedup write fails after the load (step 4.4), or it crashes after the load: events may load twice. See open questions.
  - A lookup errors (step 4.2): the event still loads, with `enrich_status = failed`. Replay fixes it (steps 5 and 7).

## Replay path

### 5. Replay job

- **Starts when:** an operator starts it for one closed day, D.
- **Checks first.** It refuses to run if either check fails:
  - D is closed.
  - The live processor has finished D. Its committed offset is at or past the first raw log entry appended after 02:00 UTC on the day after D. The job finds that offset by time in the raw log.
- **What it does, once the checks pass:**
  1. Reads archive entries with `received_at` from 8 days before D through the end of D.
  2. For each `event_id`, keeps the copy with the lowest raw log offset. Keeps it only if its `received_at` is on D. Live processing used the same rule, so this is the copy live loaded.
  3. Applies the current enrichment code.
  4. Writes the result to a staging table.
  5. Atomically replaces partition D of `events_clean` with the staging table.
- **Keeps its data:** the staging table, until the swap. It never reads or writes the dedup store.
- **Why live ingestion is not affected:** the job reads only the archive. Live events are stamped with their arrival day, so none land in D once it has closed. The swap does not conflict with live loads.
- **Why dashboards are not affected:** the swap is atomic. Dashboards see the old day or the new day, never a mix.
- **If it fails:**
  - It refuses to start: D is not closed, or live has not finished D. Try again later.
  - It fails before the swap: `events_clean` is unchanged. Rerun it.

## Monitoring

### 6. Lag alerts

- **Starts when:** continuously.
- **What it does:** lag is the newest raw log offset minus each consumer group's committed offset. Track it as a message count and as the age of the oldest unprocessed event. Watch the live processor and the archiver.
  - Live processor: alert when the oldest unprocessed event is over 3 minutes old. This fires before the 5-minute target is missed.
  - Archiver: alert when it is more than 1 day behind. The raw log keeps only 14 days.
- **Keeps its data:** nothing. It reads offsets and timestamps.
- **If it fails:** not defined in the brief.

### 7. Failed-enrichment check

- **Starts when:** once a day.
- **What it does:** counts events with `enrich_status = failed` for each closed day. Alerts when any day has some. Nothing else finds these days.
- **Keeps its data:** nothing. It reads `events_clean`.
- **Why the window matters:** a replay of D reads archive entries from D-8, and the archive keeps 90 days. So a day can be fixed until about 82 days after it ends.
- **If it fails:** not defined in the brief.

## Open questions

- Bot traffic: drop, or keep with a flag? Product has not decided.
- Who owns the raw log and the reject bucket? Who reviews rejected events?
- Can the warehouse load merge on `event_id`? If not, a crash or failed dedup-store write after the load can duplicate rows.
- The live processor assumes one order of raw log entries. If the log has more than one partition, copies of one `event_id` must land in the same partition, and "lowest offset" needs one order across partitions. Not decided.
- The 2-hour wait before a day closes assumes a collector write takes far less than 2 hours. Nothing enforces this yet.
- Who responds to a lag alert or a failed-enrichment alert, and what is the runbook?