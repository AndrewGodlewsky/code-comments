# Clickstream ingestion: plan

## Decisions this plan rests on

- **Partition day:** the UTC day of `received_at`, taken from the winning copy of an event. The client timestamp is stored but never used for partitioning or replay.
- **Winner among duplicates:** the first copy in log order. All copies of an `event_id` go to the same log partition (keyed by `event_id`), so "first" is one lowest offset. The raw archive keeps `partition` and `offset` for every copy, so replay can pick the same winner as live. The log partition count must never change; if it ever must, record a monotonic ingest sequence in the envelope first.
- **Source of truth:** the raw archive in object storage, not the log. The log keeps 14 days and raw must be kept 90 days, so the log is only a buffer.
- **Dedup scope:** an event is kept only if no earlier copy exists anywhere in the dedup horizon. A retry arriving days later, in a different UTC day than the first copy, is dropped. It is never inserted into its own day's partition.

## A. Collector (shared by the live path and the archive)

1. **Accept a batch over HTTPS.** If the body is unparseable or the batch is over 100 events, return 400 for the whole batch. Clients treat this as non-retryable.
2. **Stamp and validate each event.** Set `received_at` from the collector's NTP-synced clock. Reject individually any event that is missing `event_id` or `device_id`, or is over 32 KB. Rejected events are never stored, because they are not "accepted". The collector emits only a metric and a log line for them.
3. **Write accepted events to the log.**
   - Wrap each event in an envelope containing the original event bytes untouched, `received_at`, the client IP and User-Agent header (needed later for geo-IP and UA replay), and the collector id.
   - Key each record by `event_id` and publish with `acks=all` on a replicated topic.
   - Duplicates are published like any other event. The collector does not dedup.
4. **Respond.**
   - Return 202 only after the log confirms every accepted event is durably written. The body lists the rejected `event_id`s, or the index of any event with no usable id, with a reason.
   - If the log write fails or times out, return 5xx for the whole batch. The client resends the same `event_id`s and step 8 absorbs the duplicates.
   - If all events in the batch are rejected, still return 202 with the full rejected list. Nothing needed storing.

## B. Raw archive (the 90-day retention requirement)

5. **Archive from the log.** A dedicated consumer group copies every log record, duplicates included, to object storage. Objects are written under `raw/received_date=YYYY-MM-DD/hour=HH/`. Each object is named by `partition` and offset range, so a retried write overwrites the same object and never creates a second copy.
6. **Apply lifecycle expiry.** Delete raw objects 90 days after `received_date`. Alert if archive lag exceeds 2 days. The 14-day log retention is the safety margin, and the archive must never fall behind it.

## C. Live path (target: queryable within 5 minutes)

7. **Run the stream processor.** It is a separate consumer group, partitioned like the log, so each `event_id` is processed by one worker in offset order. It runs in micro-batches of about 1 minute.
8. **Dedup against the key-value store.**
   - For each event, do an atomic set-if-absent on key `event_id`. The value is `partition:offset` of this copy, and the TTL is 8 days. That is the 7-day maximum retry window plus a day of margin.
   - If the key was absent, or it exists with this same `partition:offset`, treat the copy as the winner and continue. The second case means the batch is being reprocessed after a crash, so the event is re-emitted idempotently rather than lost.
   - If the key exists with a different value, drop the copy. It stays in the raw archive.
9. **Enrich** with geo-IP lookup and UA parsing from the envelope's IP and User-Agent. Write the enrichment version (code plus lookup database versions) into a column.
10. **Bot handling hook (open, see section E).** This is one isolated stage between enrichment and load. Until Product decides, the plan does not specify what it does.
11. **Load into the warehouse idempotently.**
    - Insert each micro-batch into the `events_clean` partition for the UTC day of the winner's `received_at`.
    - Each load is tagged with a deterministic id made of partition plus start and end offset. A load whose id is already recorded is skipped, so a crash and retry cannot double-insert.
    - Commit consumer offsets only after the load is confirmed.
12. **Close the day.** Day D closes at 02:00 UTC on D+1, and the live path never writes to D after that. Closing is also gated on the live processor's committed watermark having passed the end of D. If the processor is more than 2 hours behind, the day stays open and an alert fires, so replay can never race with live writes.
13. **Monitor.** Track freshness (the time from `received_at` to queryable, with an alert at 4 minutes), consumer lag, the rejected-event rate, and the drop rate in step 8. A sudden fall in the drop rate suggests the key-value store has lost state.

## D. Replay of one closed UTC day

14. **Operator starts `replay(D)`.** The job refuses unless all of these hold:
    - D is closed (step 12).
    - Raw for D-8 through D+1 still exists, so D must be at most about 82 days old.
    - No replay for D is already running (one lock per day).
15. **Read only from the raw archive.** The job runs on its own compute and only reads raw objects, from D-8 through D+1 (the data available at the moment the job starts). It does not read the log, touch the key-value store, or alter any live consumer, so live ingestion and live dedup state are unaffected. It also throttles its object-storage reads.
16. **Re-derive the winners.** For each `event_id`, take the copy with the lowest `(partition, offset)` across the whole window, which applies the same rule as step 8. Keep the event for D only if that winning copy's `received_at` falls in D. This correctly handles two cases:
    - A copy in D whose first copy arrived in D-3 is dropped.
    - An event first received in D is kept even though its retries land in D+2.
17. **Re-enrich** the kept events from the raw envelopes using the current code and lookup data, and record the new enrichment version. Apply the same bot stage as the live path (section E).
18. **Build into staging.** Write the result to a staging table or partition, never to the live partition.
19. **Validate before publishing.** All of these must pass:
    - Every row has `received_at` in D.
    - `COUNT(*)` equals `COUNT(DISTINCT event_id)`.
    - The row count is within an operator-set tolerance of the live partition. Expect a difference only where the fixed enrichment changes the data, and never a large unexplained one.
    - No `event_id` in the staging data also appears in earlier days' partitions.
20. **Swap atomically.** Use the warehouse's atomic single-partition replace to swap staging into partition D. Dashboards see the old complete day or the new complete day, never a partial one. Record the replay id, enrichment version and row counts in an audit log. A failed or aborted job leaves partition D untouched, and rerunning is safe.

## E. Open decision: suspected bot traffic

**Status: undecided by Product. This plan does not choose.**

- **Option 1, drop:** the bot stage filters suspected-bot events out of `events_clean`.
- **Option 2, keep with a flag:** the stage adds an `is_suspected_bot` column and keeps the rows.

Facts that hold under either option:
- Raw retention (step 5) keeps all accepted events, bots included, so the decision can be reversed or backfilled by replay.
- Dedup (step 8) happens before the bot stage, so a bot event still counts as "seen". This makes live and replay agree.
- The bot classifier and its version must be part of the recorded enrichment version, so live and replay stay consistent.
- Only steps 10 and 17 and, for option 2, one table column change once Product decides.

## Assumptions and risks to confirm

- **Warehouse inserts.** The brief says the warehouse can atomically replace a partition. It does not say it can insert micro-batches, which step 11 and the 5-minute target need. If it cannot, the live path would have to rebuild today's partition from staging on every cycle. Please confirm.
- **Key-value store loss.** If the store loses state, duplicates will leak into live partitions until the affected days are replayed. Replay corrects them from raw.
- **Clock skew.** The 1-day lookahead in step 15 absorbs small differences between collector clocks and log order near UTC midnight. The partition day is always taken from the winning copy's `received_at`, in both live and replay.
- **Raw contains client IP and User-Agent for 90 days.** This is required for replaying enrichment fixes. It may need a privacy review.
