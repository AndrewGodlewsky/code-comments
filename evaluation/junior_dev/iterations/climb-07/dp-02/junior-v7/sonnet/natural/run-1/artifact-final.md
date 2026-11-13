# Clickstream ingestion: plan

## Summary

Websites and iOS/Android apps send click and screen-view events to a new collector. The collector stamps each event, writes it to the existing log, and answers 202 only once the write is durable. Two independent readers then use the log. An archive copies every record to object storage, and a live processor dedups, enriches and loads events into the warehouse table `events_clean` (one partition per UTC day, queryable within 5 minutes). Replay rebuilds one closed day from the archive alone, so it never touches live ingestion. The log keeps only 14 days and raw data must be kept 90, so the archive, not the log, is the source of truth.

## Terms

- **Log:** the existing replicated append-only log (Kafka-style, 14-day retention). It is a buffer between the collector and its two readers. Records are spread over numbered partitions and each has an offset (its position).
- **Key-value store:** the existing store with per-key TTL. The live processor uses it to remember which `event_id`s it has seen.
- **Warehouse:** the existing warehouse. It can atomically replace a single day partition of a table.
- **Object storage:** the existing storage with lifecycle rules (automatic expiry). It holds the raw archive.
- **Envelope:** the record the collector writes to the log: the original event bytes untouched, `received_at`, the client IP, the User-Agent header and the collector id. IP and User-Agent are kept so geo-IP and UA fixes can be replayed.
- **`received_at`:** server time stamped by the collector. An event belongs to the UTC day of `received_at`, never of the client timestamp. That day decides its partition and which replay covers it. The client timestamp is stored but never used for either.
- **Duplicate and winner:** copies of one event share an `event_id` (client-generated UUID). The first copy in log order is the winner and later copies are dropped. All copies go to the same log partition (the record key is `event_id`), so "first" means the lowest offset. The archive keeps `partition` and `offset` for every copy, so replay picks the same winner as live. The log partition count must never change. If it ever must, first record a monotonic ingest sequence in the envelope.
- **Dedup horizon:** how far back a copy can still be recognised. Live, it is the key-value store's 8-day TTL. In a replay of day D, it is the raw window D-8 through D+1. Clients retry for at most 7 days, so the horizon covers every retry the requirements allow.
- **Closed day:** day D closes at 02:00 UTC on D+1. After that the live path never writes to D, and only closed days can be replayed.
- **Watermark:** the `received_at` of the latest record whose offsets the live processor has committed, taken as the minimum across partitions.
- **Enrichment version:** the version of the enrichment code plus the geo-IP and UA lookup data, and the bot classifier. It is stored in a column of every row.
- **Staging:** a table or partition where a replay builds its result before publishing.

## Client rules (fixed by the requirements)

- Clients send batches of up to 100 events over HTTPS. Each event has `event_id`, `device_id` and a client timestamp.
- On a timeout, 429 or 5xx, a client resends the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events on the device for up to 7 days, so a retry can arrive up to 7 days after the first copy.
- Clients never retry rejected events, and treat a 400 as non-retryable.

## How the system runs

### A. Collector

1. **Accept a batch.** If the body cannot be parsed or has more than 100 events, return 400 for the whole batch.
2. **Stamp and validate each event.** Set `received_at` from the collector's NTP-synced clock. Reject individually any event missing `event_id` or `device_id`, or over 32 KB. Rejected events are not stored, because they are not "accepted", and clients never retry them. The collector emits a metric and a log line only. Operators see the rejected-event rate in monitoring (step 13). The rest of the batch is still accepted.
3. **Write accepted events to the log.** Wrap each in an envelope, key it by `event_id`, and publish with `acks=all`. Duplicates are published like any other event, because the collector does not dedup.
4. **Respond.** Return 202 only after the log confirms every accepted event is durably written. The body lists each rejected `event_id` (or the index of an event with no usable id) with a reason. If every event was rejected, still return 202 with the full list, because nothing needed storing. If the log write fails or times out, return 5xx for the whole batch. The client resends the same `event_id`s, and the live dedup step absorbs the duplicates.

### B. Raw archive (the 90-day retention requirement)

5. **Archive from the log.** A dedicated consumer group copies every log record, duplicates included, exactly as received, to object storage under `raw/received_date=YYYY-MM-DD/hour=HH/`. Each object is named by log partition and offset range, so a retried write overwrites the same object and never creates a second copy.
6. **Expire after 90 days.** A lifecycle rule deletes raw objects 90 days after `received_date`. Alert if archive lag exceeds 2 days. The archive must never fall behind the log's 14-day retention, or records are lost.

### C. Live path (queryable within 5 minutes)

7. **Run the stream processor.** It reads the log directly, not the archive, in its own consumer group, partitioned like the log. Each `event_id` is therefore handled by one worker, in offset order. It works in micro-batches of about 1 minute.
8. **Dedup against the key-value store.** For each event, do an atomic set-if-absent on key `event_id`. The value is `partition:offset` of this copy and the TTL is 8 days (the 7-day maximum retry plus a day of margin).
   - Key absent: this copy is the winner. Continue.
   - Key present with this same `partition:offset`: the batch is being reprocessed after a crash. It is the winner, so re-emit it rather than lose it.
   - Key present with a different value: drop the copy. It stays in the archive.
   - Key expired (first copy over 8 days old): the copy counts as new. This is outside the requirements, and replay treats it the same way.
   - A retry arriving in a different UTC day than the first copy is dropped like any other duplicate. It is never inserted into its own day's partition.
9. **Enrich** with geo-IP lookup and UA parsing from the envelope's IP and User-Agent. Write the enrichment version into a column.
10. **Bot stage (open, see Open questions).** One isolated stage between enrichment and load. Until Product decides, the plan does not say what it does.
11. **Load into the warehouse idempotently.** Insert each micro-batch into the `events_clean` partition for the UTC day of the winner's `received_at`.
    - Each load has a deterministic id: partition plus start and end offset. Finished load ids are kept in a small load-log table in the warehouse. A load whose id is already there is skipped, so a crash and retry cannot double-insert.
    - The insert and the load-log row should commit in one warehouse transaction. This is unconfirmed (see Open questions).
    - Commit consumer offsets only after the load is confirmed.
12. **Close the day.** The live path never writes to D after it closes at 02:00 UTC on D+1, and closing also requires the watermark to have passed the end of D. If the processor is more than 2 hours behind, the day stays open and an alert fires, so replay cannot race with live writes. If an event stamped in D reaches the processor after D has closed, the live path skips it. It stays in the archive and the next replay of D picks it up.
13. **Monitor.** Track freshness (`received_at` to queryable, alert at 4 minutes), consumer lag, the rejected-event rate, and the drop rate from the dedup step. A sudden fall in the drop rate suggests the key-value store has lost state.

### D. Replay of one closed UTC day

An operator rebuilds a day, usually after fixing an enrichment bug (geo-IP or UA parsing).

14. **Operator starts `replay(D)`.** The job refuses unless D is closed, raw data for D-8 through D+1 still exists (so D is at most about 82 days old), and no replay for D is already running (one lock per day).
15. **Read only from the archive.** The job runs on its own compute and reads only raw objects from D-8 through D+1, as they exist when the job starts. It does not read the log, touch the key-value store or alter any live consumer, so live ingestion and live dedup state are unaffected. It throttles its object-storage reads.
16. **Re-derive the winners.** For each `event_id`, take the copy with the lowest `(partition, offset)` in the whole window, the same rule as live. Keep the event for D only if that winning copy's `received_at` falls in D.
    - A copy in D whose first copy arrived in D-3 is dropped.
    - An event first received in D is kept even if its retries land in D+2. Those retries are outside the window and not needed, because a later copy can never be the first.
    - A first copy older than D-8 is outside the horizon, so the copy in D is treated as new, as live does.
    - D+1 is read only to cover clock skew near UTC midnight. The partition day always comes from the winning copy's `received_at`, in live and replay alike.
17. **Re-enrich** the kept events from the raw envelopes with the current code and lookup data, and record the new enrichment version. Apply the same bot stage as live.
18. **Build into staging,** never into the live partition.
19. **Validate before publishing.** All of these must pass:
    - Every row has `received_at` in D.
    - `COUNT(*)` equals `COUNT(DISTINCT event_id)`.
    - The row count is within an operator-set tolerance of the live partition. A difference is expected only where the fix changes the data, never a large unexplained one.
    - No `event_id` in staging also appears in an earlier day's partition.
20. **Swap atomically.** Use the warehouse's atomic single-partition replace to put staging into partition D. Dashboards see the old complete day or the new complete day, never a partial one. Record the replay id, enrichment version and row counts in an audit log.

## When things fail

| Where | What happens |
|---|---|
| Unparseable or oversized batch | 400 for the whole batch. The client does not retry. |
| Malformed event | Rejected and listed in the 202 body. Not stored, never retried. The rest of the batch is accepted. |
| Log write fails or times out | 5xx for the whole batch. The client resends and dedup absorbs the duplicates. |
| Archive write retried | Same object name, so it overwrites rather than duplicates. |
| Live processor crashes mid-batch | Reprocessing finds the same `partition:offset` and re-emits the winner. A load id already in the load-log is skipped. Offsets commit only after a confirmed load. |
| Key-value store loses state | Duplicates leak into live partitions until the affected days are replayed from the archive. A fall in the drop rate raises the alarm. |
| Processor falls over 2 hours behind | The day does not close and an alert fires. |
| Event for D arrives after D closed | Skipped live, kept in the archive, picked up by the next replay of D. |
| Replay validation fails | Nothing is published and partition D is untouched. The lock is released, the audit log records the failed check, and staging is kept for inspection. The operator fixes the cause and reruns `replay(D)`, which overwrites staging. |
| Replay aborts at any point | Partition D is untouched and rerunning is safe. |

## Open questions

- **Suspected bot traffic. Undecided by Product; this plan does not choose.** Option 1, drop: the bot stage filters suspected-bot events out of `events_clean`. Option 2, keep with a flag: the stage adds an `is_suspected_bot` column and keeps the rows. Under either option, raw retention keeps bot events so the decision can be reversed or backfilled by replay, and dedup runs before the bot stage so a bot event still counts as seen and live and replay agree. The bot classifier and its version are part of the enrichment version. Only the bot stage in the live and replay paths (steps 10 and 17) and, for option 2, one table column change once Product decides.
- **Can the warehouse insert micro-batches?** The brief says only that it can atomically replace a partition. Step 11 and the 5-minute target need inserts. If it cannot, the live path must rebuild today's partition from staging on every cycle. Please confirm.
- **Can the load-log commit atomically with the insert?** The brief does not say the warehouse supports multi-statement transactions. If not, a crash between the two could double-insert or skip a load. Where the load-log lives is also undecided.
- **Privacy review.** Raw keeps client IP and User-Agent for 90 days, which replaying enrichment fixes requires. It may need a privacy review.
