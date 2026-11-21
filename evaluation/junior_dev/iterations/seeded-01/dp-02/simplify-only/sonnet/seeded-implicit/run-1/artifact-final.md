# Clickstream ingestion plan

This is a new pipeline. It takes click and screen-view events from the website and the iOS and Android apps. It removes duplicates, adds geo-IP and user-agent data, and loads them into the warehouse table `events_clean`, one partition per UTC day. Live events are queryable within 5 minutes. The main flow is: collector, then raw log, then two readers (an archiver that keeps every event for 90 days, and a live processor that loads the warehouse). A separate replay job rebuilds a closed day from the archive.

## Terms

- **event_id**: a UUID made by the client. Two events with the same `event_id` are the same event.
- **received_at**: server time, stamped by the collector. An event belongs to the UTC day of `received_at`, never of the client timestamp.
- **Raw log**: the replicated append-only log, 14-day retention. It is partitioned by `event_id`, so all copies of one event sit in one partition, in the order we received them.
- **Archive**: object storage holding every accepted event exactly as received, duplicates included, for 90 days.
- **First copy**: the copy with the earliest `received_at`. Ties are broken by raw log position. It is the only copy kept in `events_clean`.
- **Closed day**: a UTC day becomes closed at 02:00 UTC the next day. Only closed days can be replayed.
- **Claim**: a KV entry `event_id` to raw log position, kept 8 days. Clients can resend an event up to 7 days after the first copy, so 8 days gives a margin.

## How the system runs

### 1. SDKs send batches
- **Starts when**: a web, iOS or Android client has events to send. Mobile SDKs keep unacknowledged events on the device for up to 7 days.
- **Does**: sends a batch of up to 100 events over HTTPS to the collector. Each event has `event_id`, `device_id` and a client timestamp. On a timeout, 429 or 5xx, it resends the same batch with the same `event_id`s, backing off from 1 s up to 5 minutes. It never retries events the collector rejected.
- **Keeps data in**: the device buffer.
- **If it goes wrong**: it keeps retrying. Resent copies are removed later as duplicates.

### 2. Collector accepts the batch
- **Starts when**: a batch arrives.
- **Does**: rejects each malformed event on its own (missing `event_id` or `device_id`, or over 32 KB) and lists the rejects in the response. Stamps `received_at` on the rest and writes them to the raw log. Returns 202 only after the log confirms the write is replicated.
- **Keeps data in**: the raw log. Rejected events are not stored. They are only listed in the response and counted in a metric.
- **If it goes wrong**: if the log write fails, it returns 503 for the whole batch and the client resends it. The collector never returns 202 for data that is not stored.

### 3. Archiver keeps every event
- **Starts when**: new records appear in the raw log.
- **Does**: writes each record, unchanged, to an object storage file under its `received_at` UTC day and hour. File names include the log partition and first offset. It records its log position only after the file is written. Duplicates are kept. A lifecycle rule deletes files after 90 days.
- **Keeps data in**: object storage, plus its own log position.
- **If it goes wrong**: it restarts from its last position and rewrites the same files, so no event is lost or doubled. It must catch up within the log's 14 days, so lag has an alert (step 6).

### 4. Live processor loads the warehouse
- **Starts when**: new records appear in the raw log. It works in micro-batches of about one minute.
- **Does**: for each event, tries to create a claim in the KV store. If no claim exists, the event is the first copy. If a claim exists with a different log position, the event is a duplicate and is dropped. If the claim has this same position, the batch is being reprocessed, so the event counts as the first copy. First copies are enriched (geo-IP, user agent) and appended to the `events_clean` partition for the UTC day of `received_at`. It records its log position after the load.
- **Keeps data in**: the KV store (claims) and the warehouse.
- **If it goes wrong**: after a crash it restarts from its last position. A batch may then be loaded twice. The replay in step 5 repairs this once the day is closed.

### 5. Replay rebuilds one closed day
- **Starts when**: an operator asks to rebuild day D, usually after fixing an enrichment bug. The job refuses if D is not closed.
- **Does**: reads only the archive, never the raw log or the KV store. It reads the files for D and for the 8 days before D. For each `event_id`, it finds the first copy. It keeps the events whose first copy falls in D, because a copy of an older event may arrive in D. It enriches them with the current code. It writes them to a staging table, then atomically replaces the D partition of `events_clean`.
- **Keeps data in**: the staging table, then the warehouse.
- **If it goes wrong**: if it fails before the swap, nothing changes and it can be run again. Dashboards see the old partition or the new one, never a half-built day. Live ingestion is not affected, because replay touches neither the log nor the KV store. Day D can be replayed only while its look-back files are still in the archive, about 82 days.

### 6. Monitoring
- **Starts when**: always on.
- **Does**: alerts on archiver lag (well under 14 days; the target is under 1 hour), live processor lag (over 5 minutes breaks the freshness goal) and the collector's 5xx rate.
- **If it goes wrong**: an operator is paged.

## What happens when things fail

| Failure | Result |
|---|---|
| Collector cannot write to the log | 503 for the batch, client resends |
| Malformed event | rejected alone, rest of the batch accepted |
| Archiver crashes | restarts from its position, rewrites the same files |
| Processor crashes | restarts from its position, a batch may load twice, replay repairs it |
| Replay fails before the swap | warehouse unchanged, run again |
| Enrichment bug found | replay each affected closed day |

## How to build it

1. Raw log and collector, then archiver. Raw data is safe from this point.
2. Live processor, with claims and enrichment.
3. Replay job. Test it on a day with no bug. The result should match the live output, apart from crash duplicates.
4. Monitoring and alerts.

## Open questions

- **Bot traffic**: should suspected bots be dropped or kept with a flag? Product has not decided. Enrichment in step 4 is where the flag would be set, and the plan does not choose.
- **Live duplicates after a crash**: is it acceptable for `events_clean` to hold some duplicate rows for a short time before replay? Not decided.
- **Appending**: it is not confirmed that the warehouse can append to a day partition while that day is open. The brief only states that it can replace one atomically.
- **Live lag at close**: the 02:00 close assumes the live processor is no more than about 2 hours behind. Nothing enforces this beyond the lag alert.
