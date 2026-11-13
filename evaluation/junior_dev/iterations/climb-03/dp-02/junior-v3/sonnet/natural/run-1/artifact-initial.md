# Clickstream ingestion plan

## Decisions that shape the plan

- **Day assignment.** An event belongs to the UTC day of `received_at`, which is stamped by the collector. The client timestamp is stored as data and never used for partitioning.
- **Dedup winner.** Every copy of an `event_id` goes to the same log partition, chosen by hash of `event_id`. Within one partition, log offset gives a total order. The copy with the lowest offset (the first received) is the winner.
  - Replay must pick the same winner as live, so both use this definition.
  - The partition count must stay fixed. If it ever changes, record a "log epoch" in the archive so replay can still order copies.
- **Dedup window.** Live dedup keys live for 8 days. That is the 7-day SDK buffer plus a 1-day margin.
- **Raw archive.** The 14-day log is not enough for the 90-day requirement or for replay. A separate archive in object storage holds every accepted event, duplicates included, exactly as received.
- **Replay input.** Replay reads only the archive. It never reads the live log or the live key-value store, so it cannot disturb them.

## Live path

1. **Collector validation.** For each batch of up to 100 events, check every event individually.
   - Reject an event if `event_id` or `device_id` is missing, or if it is over 32 KB.
   - Accumulate the rejects by their index in the batch, because an event with no `event_id` cannot be listed by id.
   - Process the remaining events normally.

2. **Envelope.** For each accepted event, build an envelope containing:
   - the original bytes, untouched;
   - `received_at` (server UTC);
   - the client IP, the User-Agent header, and the collector instance id.

   The enrichment inputs (IP and User-Agent) must be captured here. They cannot be recovered later and replay needs them.

3. **Durable write.** Append all accepted envelopes to the replicated log, keyed by `event_id` so copies land in the same partition.
   - Use an idempotent producer and wait for acknowledgement from all replicas.
   - Return 202 only after that acknowledgement. The response lists the rejected events.
   - If the append fails or times out, return 503, or 429 under load. The client then resends the whole batch. Copies written by a half-failed attempt are handled by dedup (step 6).
   - Never return 202 for a batch that is not stored.

4. **Archiver.** A dedicated consumer group reads every envelope and writes it to object storage.
   - Objects are laid out by UTC day of `received_at`, then by log partition and offset range.
   - Each record keeps its partition and offset.
   - The archiver commits log offsets only after the object write succeeds.
   - Duplicates are kept.
   - A lifecycle rule expires objects at 90 days.
   - Alert if archiver lag exceeds 1 hour, well inside the 14-day log retention.

5. **Live loader.** A second consumer group reads the log, one consumer per partition, in offset order. Micro-batches run about every 60 seconds.

6. **Live dedup.**
   - For each event, run set-if-absent on key `event_id` in the key-value store. The value is the event's log position (partition and offset), and the TTL is 8 days.
   - If the key was absent, or it exists with this same position, the event is the winner. The same-position case makes crash-restart reprocessing idempotent.
   - Otherwise it is a duplicate and is dropped from `events_clean`. It stays in the archive.

7. **Enrichment.** Apply geo-IP lookup and User-Agent parsing, and stamp each row with the enrichment code version and geo-IP database version. Replay needs those stamps to explain differences.
   - **Bot handling is open (see "Open decision"). It is not decided here.**

8. **Load.** Write the winners to `events_clean`, partitioned by UTC day of `received_at`.
   - Load each micro-batch idempotently, keyed by `event_id`, so a restart does not double-insert.
   - Commit the log offsets only after the load succeeds.
   - Live writes only ever target the partition for the current day.

9. **Freshness budget.** The 5-minute target breaks down as:
   - collector to log: under 1 second;
   - micro-batch wait: up to 60 seconds;
   - enrichment and load: under 2 minutes.

   Alarm on p99 end-to-end lag (`received_at` to queryable) above 3 minutes.

## Replay path

10. **Trigger.** An operator requests a rebuild of day D with a pinned enrichment code version. The tool then checks all of the following before it starts:
    - Day D is closed: the current time is at or after 02:00 UTC on D+1.
    - The live loader's watermark has passed the end of D, and the archiver is complete through the end of D.
    - Both D and its 8-day lookback are inside the 90-day archive window. Otherwise refuse.
    - No other replay of D is running. Take a lock per day.

11. **Isolation.** Run the replay on separate compute that reads only object storage. It never touches the live log or the live key-value store.
    - Cap its warehouse and storage read throughput so live ingestion is unaffected.
    - Write into a staging table or staging partition, never into the live partition.

12. **Rebuild dedup from the archive.**
    - Read the archive for D and for the 8 days before it.
    - For each `event_id`, take the copy with the lowest log position.
    - Keep the event for D only if that winning copy has `received_at` in D.
    - An event first seen on an earlier day, whose retry arrives on D, is correctly dropped. This matches what live did.
    - Winners are deterministic, so replaying D never changes which events belong to any other day.

13. **Re-enrich** the winners with the fixed code and write them to staging.

14. **Validate before publishing.**
    - The set of `event_id`s should equal the set in the current live partition.
    - Row counts should match.
    - Differences should appear only in enriched columns.
    - Produce a diff report. If the id sets differ, stop and require explicit operator confirmation.

15. **Atomic swap.** Use the warehouse's atomic single-partition replace to swap the staged data into day D.
    - Dashboards see either the old complete day or the new complete day, never a partial one.
    - Record the run id, code version, and counts.
    - A failed or aborted run leaves the old partition untouched.
    - Re-running is safe.

## Operations

16. **Monitoring and alerts.**
    - Collector 5xx and 429 rates.
    - Log consumer lag, for both the archiver and the loader.
    - End-to-end freshness.
    - Dedup rate. A sudden jump may mean a client retry storm. A drop may mean key-value store loss.
    - Daily reconciliation: archive winner count against `events_clean` count for the closed day.

17. **Failure of the key-value store.** The live dedup state is rebuildable. Reload keys from the archive for the last 8 days, then resume. During the outage, pause the loader rather than load without dedup.

18. **Tests.**
    - Retry after crash between the key claim and the load.
    - A duplicate that arrives 7 days later.
    - Events spanning the UTC midnight boundary.
    - Replay output identical to live when the enrichment code is unchanged.
    - Replay running while live traffic continues.
    - A half-built replay never visible to a dashboard.

## Open decision

19. **Suspected bot traffic: drop, or keep with a flag. Product has not decided.**
    - It is not chosen in this plan.
    - It affects only a single stage, after dedup and enrichment (step 7). It changes whether bot rows reach `events_clean` and whether the table needs a flag column.
    - The raw archive keeps everything either way, so whichever option is chosen can be applied to existing days with a replay.
    - Bot classification is not wired in until Product decides. Do not treat the interim behavior as the answer.
    - Product input is needed before that stage ships, and before any schema change to `events_clean`.
