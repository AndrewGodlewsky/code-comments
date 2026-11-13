# Clickstream ingestion: plan

## Summary of the design

- The collector writes every accepted event to the replicated log before it returns 202. It stores each event unchanged.
- Two independent consumers read that log.
  - The **archiver** copies events unchanged to object storage. This is the 90-day record and the only input to replay.
  - The **live processor** deduplicates through the key-value store, enriches, and appends to `events_clean`.
- **Replay** is a batch job over the archive. It has its own dedup logic, so it never touches the live key-value store or the live consumers. It builds a staging table and swaps it into the day partition atomically.
- Two settings must agree between live and replay: the dedup window (8 days) and the definition of "first copy" (see Definitions).

## Definitions used throughout

- **Existing infrastructure.** The brief names only kinds of system, not products, and this plan keeps it that way.
  - Log: replicated, append-only, Kafka-style, 14-day retention. Records have a partition and an offset.
  - Object storage: with lifecycle rules.
  - Key-value store: supports set-if-absent and a per-key TTL.
  - Warehouse: can atomically replace one day partition of a table. `events_clean` has one partition per UTC day of `received_at`. This plan also assumes it can delete rows by condition (step 11).
  - Progress table: a small new table for watermarks and day status (steps 6, 11, 13, 15). Any store that can hold a few rows works. Place it with the platform team.
- **Day**: the UTC day of the collector's `received_at` on the copy that wins deduplication. The client timestamp is never used.
- **First copy**: the copy with the lowest offset in its log partition. The log is keyed by `event_id`, so all copies of one event are in one partition and have a total order.
- **Dedup window**: 8 days. Clients retry for at most 7 days after the first copy, so this leaves 1 day of margin. A copy arriving after the key has expired would be kept as new. The client contract rules that out, and step 17 logs it if it happens.
- **Day D is closed** at 02:00 UTC on D+1. A day is replayable only after it is closed and the gate in step 15 passes.
- **Watermark** (one per partition, for the archiver and for the live processor): the highest `received_at` fully written. When a worker is caught up with the end of its partition, it writes the current time minus 1 hour instead, so a quiet partition still advances. A watermark has **passed day D** when it is at least 5 minutes after the end of D. The 5 minutes covers small clock differences between collectors.

## Part A: Live path

### Collector

1. **Validate each event on its own.**
   - Reject an event if `event_id` or `device_id` is missing, if the event is over 32 KB, or if it is not parseable as an object (it cannot be keyed).
   - Rejected events are listed in the response by position in the batch, with a reason. They are not stored, and clients never retry them. The valid events in the batch continue.
   - Assumed, to confirm: a body that is not a parseable array gets 400, and a batch of more than 100 events gets 413.

2. **Stamp and wrap each valid event.**
   - Set `received_at` from the collector's server clock.
   - Wrap the event in an envelope: `received_at`, `collector_id`, `batch_id`.
   - Keep the original event bytes untouched inside the envelope. Do not parse and re-serialise them. This is what "exactly as received" means.

3. **Write to the log, then acknowledge.**
   - Write all valid events to one topic, `events_raw`, keyed by `event_id`, with full replication acknowledgement (`acks=all` with a minimum in-sync replica count).
   - Return 202 only after the write is acknowledged. The response lists any rejected events.
   - If the write fails or times out, return 5xx. Also return 429 when the log write path is saturated. Clients treat 5xx, 429 or a timeout as "not stored", back off (1 s, doubling up to 5 minutes) and resend the same batch with the same `event_id`s. The mobile SDK drops an event after 7 days in its buffer.
   - A partial write from a failed attempt becomes ordinary duplicates, which step 7 removes. The collector does not deduplicate. Duplicates are accepted and kept, as the requirements say.

4. **Lock the partition count of `events_raw`, and set retention to 14 days.**
   - Keying by `event_id` makes "first copy" mean "lowest offset in the key's partition", the same for live and replay. Changing the partition count would break that ordering, so treat it as a runbook event that needs a dedup-state cutover.
   - The archive holds the long-term copy, so nothing downstream needs the log for more than a short outage.

### Archiver

5. **Run the archiver as a separate consumer group.**
   - It writes the envelope and the original bytes to object storage, with `partition` and `offset` inside every record.
   - Path: `raw/received_day=YYYY-MM-DD/partition=P/<start_offset>-<end_offset>.<ext>`. The file format is an implementation choice, but it must keep the original bytes exactly.
   - Buffer records per partition and day, choosing the day from each record's `received_at`. Close a file at a size or age limit, or at the UTC midnight boundary.
   - Commit log offsets only after the object is written. After a restart a new file can overlap an earlier one. Readers (replay) drop records with the same `partition` and `offset`. Nothing is lost.

6. **Expire raw objects 90 days after creation, and watch the archiver.**
   - The lifecycle rule includes duplicates. Do not deduplicate or modify anything here.
   - After each file, the archiver writes its per-partition watermark to the progress table, for the replay gate.
   - Alert when archiver lag exceeds 1 hour. Page at 24 hours, well inside the 14-day log retention. Beyond 14 days behind, data is lost.

### Live processor

7. **Run the live processor as its own consumer group, with one worker set per partition range.**
   - Each record delivered carries its own `partition` and `offset`.
   - For each record, do `set-if-absent(event_id → {partition, offset})` in the key-value store, with a TTL of 8 days. Do not refresh the TTL when a duplicate arrives.
   - Key absent: this record is the first copy, continue.
   - Key present with a different `{partition, offset}`: drop the record and count it in a metric.
   - Key present with the same `{partition, offset}`: treat it as the winner again. This happens when the worker crashed after claiming the key and before writing to the warehouse.

8. **Fail closed if the key-value store is unavailable.**
   - Stop consuming and let lag build. The log can hold 14 days. Never write events through without a dedup check.
   - If the key-value state is lost, rebuild it from the archive for the last 8 days before resuming.

9. **Enrich the winning events.**
   - Look up geo-IP and parse the user-agent.
   - Record the geo-IP database and user-agent parser versions on each row, or in the batch metadata, so replay is reproducible.
   - Keep the enrichment code in one library that both the live processor and replay call, so a bug fix applies to both.

10. **Bot handling is an open product decision. Do not choose it.**
    - Keep a single, clearly marked stage after dedup and enrichment where the choice will go (see "Open decisions").
    - Until it is decided, no event is dropped or flagged for being a bot. Dedup always runs first, so an event consumes its `event_id` whatever the eventual decision.

11. **Write to the warehouse in micro-batches, without double writes.**
    - Flush at least every 60 seconds. Append each batch to the `received_at` day partition of `events_clean`, not the partition for processing time.
    - Every row carries its source `log_partition` and `log_offset`.
    - Order per batch: load, write the **live watermark** to the progress table, then commit log offsets.
    - If the worker crashes after a load but before the commit, it restarts from the last committed offset and may cut batches differently. So before consuming, a restarting worker deletes the rows of its partitions with `log_offset` at or after the committed offset (these are only in recent, open days), then reprocesses. Step 7's same-offset rule makes those records winners again, so each event ends up in the table once.
    - This relies on the warehouse deleting rows by condition. It is an assumption to confirm.

12. **Meet the 5-minute freshness target.**
    - The budget is: log write, consume, key-value check and enrichment, flush of at most 60 seconds, then load. The 5 minutes is counted from the moment an event reaches us, so late retries are not a freshness problem.
    - Alert when end-to-end lag from `received_at` to queryable passes 3 minutes. Page at 5 minutes.

13. **Stop live writes into days being replayed.**
    - After midnight, live writes to day D only events stamped in D that are still in flight. Late retries add no rows, because they are duplicates. So live writes to D stop once the live watermark passes D.
    - The gate (step 15) waits for both watermarks to pass D, and replay reads the archive only after that, so replay already includes everything live loaded for D.
    - From the moment the gate passes, D is `started` in the progress table, and `replayed` after the swap (step 21). Before each load, the live sink checks it. It drops any rows for a `started` or `replayed` day, counts them, and alerts. It does not stall.
    - Dropping is safe because those events are already in the archive, so they are in the replayed partition.

## Part B: Replay

14. **Define the operator interface.**
    - One command: `replay --day YYYY-MM-DD`. It returns a run id.
    - It is safe to rerun: the same inputs and pinned enrichment versions give the same output.

15. **Check that the day can be replayed (the gate).** Refuse to start unless all of the following hold:
    - The current time is at or after 02:00 UTC on D+1.
    - The live watermark and the archiver watermark have both passed D for every partition.
    - The raw archive still holds D and the 8 days before it, within the 90-day expiry. So a day can be replayed only until about 82 days after it ends.
    - No other replay of the same day is running. Take a lock per day.
    - When the gate passes, mark D as `started` in the progress table (step 13).

16. **Read only from the archive.**
    - Read the raw files for `received_day` from D−8 through D.
    - Do not read the log, and do not read or write the live key-value store or use live consumer groups.
    - Run the job on separate compute from live ingestion, so a replay cannot slow it.

17. **Rebuild dedup from the archive.**
    - First drop overlapping records (same `partition` and `offset`, see step 5).
    - For each `event_id`, find its first copy: the lowest `offset` in its partition across the whole D−8 to D window.
    - Keep a record for day D only if that first copy has `received_at` in day D. This drops copies of events first seen on earlier days, as the key-value store does live.
    - D's first copies are kept even if later copies arrive on D+1 to D+7. The first copy wins, so those do not matter.
    - Collector clocks can disagree slightly, so a first copy by offset might carry a `received_at` just past midnight. Live and replay follow the same rule, so they agree. Keep collector clocks synchronised to keep this rare.
    - If any duplicate appears more than 7 days after its first copy, log it. That would break the client contract and the 8-day window.

18. **Re-enrich with the fixed code.**
    - Use the shared enrichment library from step 9, at a pinned and recorded version, including the geo-IP database version.
    - Apply the bot-handling stage if a decision exists by then (step 10). Otherwise do the same as live.

19. **Write to a staging table.**
    - Write to `events_clean_stage` under the run id. Dashboards read `events_clean` only, so they cannot see staging data.

20. **Validate before the swap.** Refuse to swap if any check fails.
    - The staging row count equals the number of distinct first-copy `event_id`s computed straight from the archive.
    - `event_id` is unique in staging, and every row has `received_at` inside day D.
    - The row count is within an expected range of the current live partition, and the difference is reported to the operator. A large difference is expected if the replay fixes a loss, and unexpected otherwise.

21. **Swap atomically.**
    - Use the warehouse's atomic single-partition replace to move staging data into day D of `events_clean`. Dashboards see either the old day or the new day, never a half-built one.
    - Live cannot add rows to D meanwhile, because D has been `started` since the gate (step 13). Mark D as `replayed`.
    - Record the run id, enrichment versions and row counts. Delete the staging table.

22. **If the replay fails before the swap, nothing in `events_clean` has changed.** Fix the cause and rerun. D stays `started`, so live keeps dropping its rows, which the rerun covers from the archive. If a bad replay is swapped in, replay again with corrected code. The raw archive is unchanged, so a replay can be redone within the 90 days.

## Part C: Operations and testing

23. **Monitor and reconcile.**
    - Monitor: collector rates of 202, 429 and 5xx and rejected events by reason; consumer lag for both groups; key-value errors and duplicate-drop rate; archive object counts against log offsets. Lag and freshness alerts are in steps 6 and 12.
    - After each day closes, compare the live partition for D with a count taken straight from the archive. A mismatch means a bug in the live path, the archive or the key-value state, and is the trigger to replay D.

24. **Test before launch.**
    - Duplicates and replay: send duplicate batches, partial batches and retries, including a retry that arrives on a later UTC day. Confirm live and replay produce identical rows.
    - Failures: crash the live processor between the key-value claim and the load, and again between the load and the offset commit. Confirm nothing is lost or doubled. Restart the archiver and confirm replay ignores overlapping files.
    - Isolation: run a replay under load and confirm no change to live latency or key-value contents. Include a partition with no events near midnight, and confirm the gate still passes.
    - Retention: confirm the 90-day lifecycle rule on a test prefix.

## Open decisions

- **Suspected bot traffic: drop or keep with a flag.** This is Product's decision and is not chosen here.
  - It touches only the single stage in step 10, and the same stage in step 18. Dedup is unaffected.
  - Raw events are archived for 90 days either way. Once decided, it can be applied to closed days by replay within that window.
  - "Keep with a flag" adds a column to `events_clean`, a schema change to plan for.
- **Edge-case assumptions to confirm.** The 400 and 413 responses in step 1, and the warehouse's support for deleting rows by condition in step 11.
- **Platform choices not in the brief.** The log, key-value and warehouse products, the progress-table store and the archive file format are not named. None of them changes the design.
