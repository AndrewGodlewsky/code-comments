# Clickstream ingestion: plan

## Summary of the design

- The collector writes every accepted event to the replicated log before it returns 202. It stores each event unchanged.
- Two independent consumers read that log.
  - The **archiver** copies events unchanged to object storage. This is the 90-day record and the only input to replay.
  - The **live processor** deduplicates through the key-value store, enriches, and appends to `events_clean`.
- **Replay** is a batch job over the archive. It has its own dedup logic, so it never touches the live key-value store or the live consumers. It builds a staging table and swaps it into the day partition atomically.
- Two settings must agree between live and replay: the dedup window (8 days) and the definition of "first copy" (see step 4).

## Definitions used throughout

- **Day**: the UTC day of the collector's `received_at` on the copy that wins deduplication. The client timestamp is never used for the day.
- **First copy**: the copy with the lowest offset in its log partition. The log is keyed by `event_id`, so all copies of one event are in one partition and have a total order.
- **Dedup window**: 8 days. Clients retry for at most 7 days after the first copy, so this leaves 1 day of margin.
- **Day D is closed** at 02:00 UTC on D+1. A day is replayable only after it is closed and the gate in step 17 passes.

## Part A: Live path

### Collector

1. **Validate each event on its own.**
   - Reject an event if `event_id` or `device_id` is missing, or if the event is over 32 KB.
   - Also reject an event that is not parseable as an object, because it cannot be keyed.
   - Rejected events are listed in the response by their position in the batch, with a reason. They are not stored, and clients never retry them.
   - The valid events in the same batch continue.
   - Two cases the brief does not cover are assumed here: a request body that is not a parseable array gets 400, and a batch of more than 100 events gets 413. Both are assumptions to confirm.

2. **Stamp and wrap each valid event.**
   - Set `received_at` from the collector's server clock.
   - Wrap the event in an envelope: `received_at`, `collector_id`, `batch_id`.
   - Keep the original event bytes untouched inside the envelope. Do not parse and re-serialise them. This is what "exactly as received" means.

3. **Write to the log, then acknowledge.**
   - Write all valid events to one topic, `events_raw`. Use full replication acknowledgement (`acks=all` with a minimum in-sync replica count), and key by `event_id`.
   - Return 202 only after the write is acknowledged. The response lists any rejected events.
   - If the write fails or times out, return 5xx. The client resends the same batch with the same `event_id`s. Any partial write from the failed attempt becomes ordinary duplicates, which step 4 removes.
   - The collector does not deduplicate. Duplicates are accepted and kept, as the requirements say.
   - Under load, return 429 when the log write path is saturated. This protects the collector and signals clients to back off.

4. **Lock the partition count of `events_raw`.**
   - Keying by `event_id` makes "first copy" mean "lowest offset in the key's partition". That definition is the same for live and replay.
   - Changing the partition count would break the ordering. Treat that as a runbook event that needs a dedup-state cutover. Do not do it casually.
   - Set retention to 14 days. Nothing downstream depends on the log for more than a short outage. The archive holds the long-term copy.

### Archiver

5. **Run the archiver as a separate consumer group.**
   - It writes the envelope and the original bytes to object storage.
   - Path: `raw/received_day=YYYY-MM-DD/partition=P/<start_offset>-<end_offset>.<ext>`.
   - Choose the day from each record's `received_at`. Split a file at the UTC midnight boundary.
   - Record `partition` and `offset` inside every record.
   - Make file names deterministic from the offset range. A retry or restart then overwrites the same object and does not create a second copy.
   - Commit log offsets only after the object is written.

6. **Apply a lifecycle rule that expires raw objects 90 days after creation.**
   - Include duplicates. Do not deduplicate or modify anything here.
   - Alert when archiver lag exceeds 1 hour. Page when it exceeds 24 hours, well inside the 14-day log retention. If the archiver falls more than 14 days behind, data is lost.
   - Write the archiver's per-partition watermark (the highest `received_at` fully written) somewhere the replay gate can read it.

### Live processor

7. **Run the live processor as its own consumer group, with one worker set per partition range.**
   - For each record, do `set-if-absent(event_id → {partition, offset})` in the key-value store, with a TTL of 8 days.
   - Do not refresh the TTL when a duplicate arrives.
   - If the key is absent, this record is the first copy: continue.
   - If the key is present with a different `{partition, offset}`, drop the record and count it in a metric.
   - If the key is present with the same `{partition, offset}`, treat it as the winner again. This happens when the worker crashed after claiming the key and before writing to the warehouse, and it prevents losing that event.

8. **Fail closed if the key-value store is unavailable.**
   - Stop consuming and let lag build. The log can hold 14 days.
   - Never write events through without a dedup check.
   - If the key-value state is lost, rebuild it from the archive for the last 8 days before resuming. Alternatively, resume and then replay the affected days. Prefer the rebuild.

9. **Enrich the winning events.**
   - Look up geo-IP and parse the user-agent.
   - Record the versions of the geo-IP database and the user-agent parser on each row, or in the batch metadata. Replay needs this to be reproducible.
   - Keep the enrichment code in one library that both the live processor and the replay job call, so a bug fix applies to both.

10. **Bot handling is an open product decision. Do not choose it.**
    - Keep a single, clearly marked stage after dedup and enrichment where the choice will go (see "Open decisions").
    - Until the decision is made, the processor makes no bot decision. No event is dropped or flagged for being a bot.
    - Dedup always runs first, so an event consumes its `event_id` regardless of the eventual bot decision.

11. **Write to the warehouse in micro-batches.**
    - Flush at least every 60 seconds.
    - Append each batch to the `received_at` day partition of `events_clean`, not to the partition for processing time.
    - Give each load a deterministic identity (topic, partition, start offset, end offset), so a retried load does not double-write. This assumes the warehouse can make loads idempotent by job id. If it cannot, delete rows by that batch id before inserting.
    - Commit log offsets only after the load succeeds.

12. **Meet the 5-minute freshness target.**
    - The budget is: log write, consume, key-value check and enrichment, flush at most 60 seconds, then load.
    - Alert when end-to-end lag from `received_at` to queryable passes 3 minutes. Page at 5 minutes.
    - Late retries are not a freshness problem. The 5 minutes is counted from the moment an event reaches us.

13. **Stop live writes into closed days.**
    - Live writes to day D normally end shortly after 00:00 UTC on D+1, when the processor drains.
    - If a backlog causes the processor to write into a day that has already been replayed, it would add duplicates to the replayed partition.
    - So the live sink refuses to write to a day that has been marked replayed or closed past its gate, and raises an alert. Replaying that day again corrects it.

## Part B: Replay

14. **Define the operator interface.**
    - One command: `replay --day YYYY-MM-DD`. It returns a run id.
    - It is safe to rerun, because the same inputs and the same pinned enrichment versions give the same output.

15. **Check that the day can be replayed (the gate).** Refuse to start unless all of the following hold:
    - The current time is at or after 02:00 UTC on D+1.
    - The live processor's committed watermark has passed the end of day D for every partition, and its last flush for D has completed.
    - The archiver's watermark has passed the end of day D for every partition.
    - The raw archive still holds D and the 8 days before it, within the 90-day expiry. Because of this, a day can be replayed only until about 82 days after it ends.
    - No other replay of the same day is running. Take a lock per day.

16. **Read only from the archive.**
    - Read the raw files for `received_day` from D−8 through D.
    - Do not read the log. It keeps only 14 days, and replay must not add load to live consumers.
    - Do not read or write the live key-value store, and do not use live consumer groups.
    - Run the job on separate compute from live ingestion, so a replay cannot slow live ingestion.

17. **Rebuild dedup from the archive.**
    - For each `event_id`, find its first copy: the copy with the lowest `offset` in its partition across the whole D−8 to D window.
    - Keep a record for day D only if that first copy has `received_at` in day D.
    - This drops copies of events first seen on earlier days. The live path drops them through the key-value store.
    - It keeps D's first copies even if later copies arrive on D+1 to D+7. Those later copies are not in the window and do not matter, because the first copy wins.
    - Skew caveat: collector clocks can disagree slightly. A first copy by offset might carry a `received_at` a few milliseconds past midnight. Live and replay both follow the rule above exactly, so they agree. Keep collector clocks synchronised to keep this rare.
    - Invariant check: if any duplicate appears more than 7 days after its first copy, log it. That would break the client contract and the 8-day window.

18. **Re-enrich with the fixed code.**
    - Use the shared enrichment library from step 9, at a pinned and recorded version, including the geo-IP database version.
    - Apply the bot-handling stage if a decision exists by then (step 10). Otherwise do the same as live.

19. **Write to a staging table.**
    - Write to `events_clean_stage` under the run id. It never shares a table partition with live reads.
    - Dashboards read `events_clean` only, so they cannot see the staging data.

20. **Validate before the swap.** Refuse to swap if any check fails.
    - The staging row count equals the number of distinct first-copy `event_id`s computed straight from the archive.
    - `event_id` is unique in the staging table.
    - Every row has `received_at` inside day D.
    - The row count is within an expected range of the current live partition, and the difference is reported to the operator. A large difference is expected if the replay fixes a loss, and unexpected otherwise.

21. **Swap atomically.**
    - Use the warehouse's atomic single-partition replace to move the staging data into day D of `events_clean`.
    - Dashboards see either the old day or the new day, never a half-built one.
    - Mark day D as replayed so step 13 applies.
    - Record the run id, enrichment versions and row counts. Delete the staging table.

22. **If the replay fails at any step before the swap, nothing in `events_clean` has changed.** Fix the cause and rerun. If a bad replay is swapped in, replay again with the corrected code. The raw archive is unchanged, so a replay can always be redone within the 90 days.

## Part C: Operations and testing

23. **Monitor.**
    - Collector: rate of 202, 429 and 5xx; rejected-event rate by reason.
    - Log: consumer lag for the archiver and the live processor.
    - Live: key-value store errors, duplicate-drop rate, and end-to-end lag.
    - Archive: lag and object counts against log offsets.

24. **Reconcile daily, after each day closes.**
    - Compare the live partition for day D with a replay-style count taken straight from the archive.
    - A mismatch means a bug in the live path, the archive or the key-value state. It is also the trigger to replay D.

25. **Test before launch.**
    - Duplicate and replay correctness: send duplicate batches, partial batches and retries, including a retry that arrives on a later UTC day. Confirm live and replay produce identical rows.
    - Failure handling: crash the live processor between the key-value claim and the warehouse load, and confirm nothing is lost or doubled. Also run an archiver restart.
    - Replay isolation: run a replay under load, and confirm there is no change to live latency or key-value contents.
    - Retention: confirm the 90-day lifecycle rule on a test prefix.

## Open decisions

- **Suspected bot traffic: drop or keep with a flag.** This is Product's decision. It is not chosen in this plan.
  - The decision touches only the single stage in step 10, and the same stage in step 18.
  - Whichever option is chosen, raw events are still archived for 90 days, as the requirements say.
  - Once decided, it can be applied to closed days by replay, within the 90-day window.
  - If the answer is "keep with a flag", that adds a column to `events_clean`. That is a schema change to plan for.
  - Dedup is unaffected by either choice.
- **Edge-case assumptions to confirm.** These are the 400 and 413 responses in step 1, and the warehouse's support for idempotent loads in step 11.
