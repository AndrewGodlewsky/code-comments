# Clickstream ingestion: plan for `events_clean`

## What this is

This pipeline takes click and screen-view events from our website and our iOS and Android apps. It removes duplicate events, adds extra fields, and writes the result to the warehouse table `events_clean`. That table has one partition per UTC day. An event's day comes from when we received it, not from the clock on the device.

The live path works like this. Clients send batches of events to a new collector service. The collector checks each event, stores the batch in a replicated log, and only then replies 202. Two consumers read the log. One copies every event to object storage. The other removes duplicates, adds enrichment, and loads the rows into today's partition about every minute.

Replay rebuilds one closed day from the raw copies in object storage. Operators use it after they fix an enrichment bug. Replay never touches the log or the live dedup store. It builds the new day in a staging table, checks it, and swaps it in with one warehouse transaction.

The shape comes from two facts. Raw copies are kept for 90 days, so any recent closed day can be rebuilt. Live dedup can be wrong for the open day if its store is lost, so replay recomputes dedup from raw data and corrects closed days.

## Terms

- **Event:** one click or screen view. It has a client-made `event_id` (a UUID), a `device_id`, a client timestamp and a payload.
- **Batch:** up to 100 events sent together in one HTTPS request.
- **Collector:** the new service that receives batches, checks them and stores them.
- **Envelope:** the fields the collector adds beside the payload: `received_at` and the collector node ID.
- **`received_at`:** the server's UTC time when the collector received an event. It sets the event's day.
- **UTC day:** a calendar day in UTC, from 00:00 to 24:00.
- **Partition:** one day's slice of `events_clean`.
- **Log:** the replicated, append-only record of accepted events. It keeps records for 14 days.
- **Consumer group:** a set of readers that share the log's work and track their own position.
- **Offset:** a record's position in the log. A consumer records how far it has read.
- **Raw archive:** object storage holding every accepted event, duplicates included, in files grouped by receipt day. Each file is deleted 90 days after it is created.
- **Dedup store:** a key-value store with one key per `event_id`. Each key expires 8 days after it is set.
- **First copy:** the copy of an event that wins. Live: the first copy the dedup store accepts. Replay: the copy with the earliest `received_at`.
- **Micro-batch:** the rows the live consumer loads together, about every 60 seconds.
- **Enrichment:** adding geo-IP location and parsed user-agent fields to a row.
- **Enrichment version:** a label on each row that says which enrichment rules produced it.
- **Staging table:** a temporary table that a replay fills before the swap.
- **Quarantine table:** a holding table for rows that arrive for a closed day, so they never reach `events_clean`.
- **Watermark:** proof that a consumer has read every log record up to a given point.
- **Closed day:** a UTC day D after 02:00 UTC on D+1 has passed. Live writes never target a closed day.

## How the live path works

1. **The client sends a batch.** The SDK sends up to 100 events over HTTPS. If the request times out, or gets a 429 or 5xx, the SDK sends the same batch again with the same `event_ids`. It waits 1 second before the first retry, doubles the wait each time, and stops growing it at 5 minutes. The mobile SDK keeps unacknowledged events on the device for up to 7 days, so a retry can arrive up to 7 days after the first copy. Rejected events are never resent.

2. **The collector checks each event alone.** An event must have a UUID `event_id` and a `device_id`. It must be 32 KB or smaller. A bad event is rejected, and the rejection records its position in the batch and a reason. The other events in the batch continue.

3. **The collector stamps the receipt time.** It records the server's UTC time as `received_at`, and the node ID, in an envelope beside the payload. The payload is stored exactly as received. The client timestamp is kept as a plain field. Neither one decides the partition or whether an event is replayed.

4. **The collector stores the batch before it replies.** It appends the accepted events to the log and waits until every in-sync replica confirms. That confirmation is the durability point. Only then does it reply 202, with the list of rejected events. If the append fails for any part of the batch, it replies 503 for the whole batch, and the client retries with the same IDs. A partial append can leave duplicates, and step 6 removes them.

5. **Every copy is archived.** The archive consumer reads the log and writes every accepted event, duplicates included, to object storage under `raw/received_day=YYYY-MM-DD/`. Each flush is a new file that is never changed. Object storage deletes each file 90 days after it was created. The consumer records its offset. An alert fires if its lag goes over one hour, because the log keeps records for only 14 days.

6. **Duplicates are removed and rows are enriched.** The live consumer reads the log. Records are split by a hash of `event_id`, so every copy of an event reaches the same consumer. For each event:
   a. It tries to set the key `event_id` in the dedup store, but only if the key is absent. The value holds the `received_at`, the partition day and the ID of the micro-batch that claims the event. The key expires after 8 days. Later copies do not reset the expiry.
   b. If the set succeeds, this is the first copy. The consumer adds geo-IP and user-agent fields and stamps the enrichment version.
   c. If the key exists with a different batch ID, the event is a duplicate. It is dropped from the clean path. The raw archive still keeps it.
   d. If the key exists with the same batch ID, the consumer is re-running a batch it had not committed before a restart. The event is kept.
   e. If the dedup store is unavailable, the consumer pauses. It must not write rows it has not checked, because that could create duplicates. Lag grows, and the 14-day log retention covers the pause.

7. **Bot traffic (open).** Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose either. The decision goes after enrichment and before the load in step 8.

8. **Micro-batches are loaded.** About every 60 seconds, the live consumer inserts its rows into `events_clean`. Each row goes to the partition of its own `received_at` day. Live writes only target the current open day. Each micro-batch commits as one transaction. Its idempotency key is built from the consumer group and the offset range, so a retried load cannot insert the same rows twice.

9. **The latency budget is kept.** The 5-minute target is measured from our receipt, not from the client's send time. The budget is: collector and log commit under 1 second, consumer and enrichment under 1 minute, warehouse load under 2 minutes at p99. An alert fires if the oldest uncommitted record is more than 3 minutes old.

10. **Monitoring.** Track these: rows accepted per collector; rows rejected, by reason; duplicates dropped; dedup store errors; lag for both consumer groups; rows loaded per micro-batch. Once an hour, compare accepted counts with raw archive counts.

## How replay rebuilds one closed day

Replay rebuilds partition D of `events_clean`, for a closed day D. Day D closes at 02:00 UTC on D+1.

Replay uses a stateless dedup rule. For each `event_id`, the copy with the earliest `received_at` wins. Ties go to the lower collector node ID, then the lower batch sequence. An event belongs to the day its winning copy was received. Live dedup follows log order, so for copies received within about a second of each other across midnight, live and replay can disagree. Replay is authoritative for closed days.

11. **Admission.** The operator gives a day D, a reason and a target enrichment version. The runner refuses the request unless the current time is at or after 02:00 UTC on D+1. It also refuses from D+80 onward. Raw data for day D-7 expires about D+83, so the margin keeps a replay from starting too close to that. Only one replay per day can run, and a lock enforces this. The live path never takes this lock.

12. **Watermark check.** The runner confirms that the live consumer and the archive consumer have each processed every log record appended before 02:00 UTC on D+1. It checks consumer offsets, not only the clock. If either consumer is behind, the runner waits and checks again.

13. **Candidates are read from raw.** The runner reads every raw copy in partitions D-7 through D, duplicates included. Retries arrive within 7 days of the first copy, so every event with a copy on D has its first copy no earlier than D-7. For each `event_id`, the runner keeps the earliest copy. It keeps only the winners whose winning copy was received on D. It does not read or write the dedup store or the log.

14. **Winners are enriched.** The runner applies the target enrichment version to each winner. It applies the bot decision that is in force for this replay, the same one the live path uses at that time.

15. **Rows are staged.** The runner writes the rebuilt rows to a staging table tagged with the replay run ID. `events_clean` is not changed.

16. **Staging is validated.** The runner checks that:
   - the staged row count equals the winner count from step 13;
   - no `event_id` appears twice;
   - every row's partition day is D;
   - every row carries only the target enrichment version;
   - the differences from live partition D are limited to enrichment columns and to the boundary rows described above.

   If any check fails, the runner drops the staging table. The live partition stays as it is.

17. **The partition is swapped.** In one warehouse transaction, the runner replaces partition D of `events_clean` with the staged rows. Readers see either the old partition or the new one, never a mix. Live writers never write to a closed day. If a row for a closed day arrives anyway, it goes to the quarantine table and raises an alert.

18. **The run is recorded and released.** The runner logs the run ID, the day, the enrichment version, the raw copy counts, the winner counts, the row counts, the operator and the duration. It drops the staging table and releases the lock.

19. **Replay is isolated.** Replay reads only the raw archive. It never touches the log, the dedup store or the live consumers. It runs on its own warehouse compute with a resource quota, so it cannot slow the live loads.

## What happens when things fail

| Failure | What happens | What keeps the data |
|---|---|---|
| Log append fails for part of a batch | The collector replies 503 for the whole batch. The client retries with the same IDs. | The client keeps the events. Partial copies are removed by dedup. |
| An event is malformed (no UUID, no `device_id`, over 32 KB) | It is rejected alone and listed in the response. The rest of the batch is accepted. | The client does not resend it. It is not stored in `events_clean`. Keeping rejected events is an open question. |
| Client times out, or gets 429 or 5xx | The client resends the same batch with the same IDs, backing off from 1 second to 5 minutes. | The mobile SDK buffers unacknowledged events for up to 7 days. |
| A duplicate copy arrives | It is dropped from the clean path. | The raw archive keeps it for 90 days. |
| The dedup store is unavailable | The live consumer pauses. It writes nothing unchecked. | The log keeps records for 14 days. |
| A live consumer restarts mid-batch | Events claimed by the same batch ID are kept. | Offsets, and the idempotent micro-batch load. |
| A micro-batch load fails or is retried | The retry uses the same idempotency key, so rows are not inserted twice. | The log, from the last committed offset. |
| The archive consumer falls more than 1 hour behind | An alert fires. | The log, for 14 days. |
| A replay finds a consumer behind | The runner waits and checks again. | The raw archive. |
| A replay check fails | The staging table is dropped. | The live partition is unchanged. |
| A row for a closed day arrives live | It goes to the quarantine table, and an alert fires. | The quarantine table. |
| The dedup store loses keys | Live dedup is broken for the open day. Closed days are repaired by replay. | A recovery procedure is still to be written. |

## Build and rollout

Assumptions to confirm before building:

- The warehouse accepts micro-batch inserts into the current day's partition, and it can atomically replace one day's partition, both in the same table. If inserts are not supported, live writes go to a staging table, and the warehouse exposes that table to `events_clean` as one view.
- The log exposes per-partition offsets and consumer lag, and it supports acknowledgement from all in-sync replicas.
- Object storage deletes an object 90 days after it is created. Raw objects are created at receipt, so an object's age equals its receipt age.
- Collector nodes use NTP, so clock skew is seconds, not minutes.
- Records stamped on day D reach the log well before 02:00 UTC on D+1.
- The brief gives no status for a wholly malformed batch or for invalid JSON. This plan uses 400 for an unparseable body or a batch over 100 events. It uses 202 with a per-event rejection list for any batch that can be parsed.

Checks during rollout:

- The mobile team confirms that the 7-day buffer is measured from the first send, not from the client event time. If it is measured from event time, retries could arrive more than 7 days after our first receipt, and the 8-day dedup key would not cover them.
- Measure how often live and replay pick different winners. The comparison in step 16 counts these rows.
- Confirm that the warehouse can do both micro-batch inserts and partition replacement on one table, and that a replacement is one transaction that readers see all at once.
- Monitor NTP health. A few seconds of clock skew can move an event across midnight.
- Write the recovery procedure for dedup store loss before launch.
- Replay of day D is impossible after about D+83. The admission check at step 11 tracks this.

## Open questions

- **Bot traffic:** drop, or keep with a flag. Owner: product. The decision goes between enrichment and the load (step 7). The plan assumes neither option.
- **Status for an all-rejected batch:** the plan returns 202 with the rejection list. Confirm with the client team.
- **Archiving rejected events:** the brief does not require it. Decide whether to keep them for debugging, and if so, for how long.