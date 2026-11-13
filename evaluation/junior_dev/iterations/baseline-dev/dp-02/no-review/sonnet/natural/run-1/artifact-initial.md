# Clickstream ingestion: implementation plan

## Design rules

These follow from the brief and shape every step below.

- **Partition by `received_at`.** An event's UTC day is the day of the collector's `received_at` stamp. Client timestamps never decide partition or replay coverage.
- **Canonical copy order.** The first copy wins, and "first" means the earliest `(received_at, collector_id, collector_seq)`. Live processing and replay both use this order, so replay reproduces live deduplication.
- **Dedup window.** A retry can arrive up to 7 days after the first copy, and a later copy can land in a different UTC day than the first. A copy is a duplicate if any earlier copy exists, in any day, within the window. The dedup state must outlive 7 days.
- **Raw is the source of truth.** Everything downstream, including a replay, can be rebuilt from the raw archive.

## Assumptions to confirm before building

- **A1.** The warehouse can append rows to a day partition, with an idempotent load keyed by a load ID. It can also atomically replace a whole partition. If appends are not supported, step 11 needs a different loading mechanism.
- **A2.** The key-value store supports atomic put-if-absent with per-key TTL.
- **A3.** Collector clocks are synchronized (NTP) to within about 1 s. Only copies received near a UTC midnight boundary are sensitive to skew.
- **A4.** Client IP and request headers are available to the collector. Geo-IP and user-agent enrichment need them, and they are not part of the event JSON.

## Part 1: Live path

### Ingest and durability

1. **Collector service.** Stateless and horizontally scaled behind a load balancer. It accepts an HTTPS POST of up to 100 events. For each event it checks that `event_id` and `device_id` are present and that the event is at most 32 KB. Invalid events are rejected individually and referenced in the response by their position in the batch, because a missing `event_id` cannot be used as a key. Clients never retry rejected events.

2. **Stamp and wrap.** For each valid event the collector sets `received_at` from its own clock. It records the event bytes untouched, plus an envelope containing `received_at`, `collector_id`, a per-collector monotonic `collector_seq`, client IP, and the User-Agent header. Clients can send the same event twice, and every accepted copy is wrapped and kept, duplicates included.

3. **Durable write before 202.** The collector writes the accepted events to the `raw-events` log topic with full replication and waits for the acknowledgment from all in-sync replicas. Only then does it return 202. The 202 response lists the rejected events. If the log write fails or times out, the collector returns 5xx, or 429 under overload. The client then retries the whole batch with the same `event_id`s. A rejected event is rejected the same way on every retry, so retries stay consistent.

4. **No dedup in the collector.** Duplicates are written to the log like any other event. This keeps the 202 path fast and keeps "keep every accepted copy" trivially true.

### Raw archive (90-day retention)

5. **Archiver.** A separate consumer group reads `raw-events` and writes immutable files to object storage, laid out as `raw/received_date=YYYY-MM-DD/…`. The date is the UTC day of `received_at`. Each file records its source log partition and offset range, so rewriting after a crash overwrites the same object name and creates no duplicates.

6. **Lifecycle rule.** Delete raw objects 90 days after creation. Raw is exactly as received, so duplicates are included. Alert if archiver lag exceeds 6 hours. The log keeps data for only 14 days, so an archiver outage longer than that would lose data.

### Dedup and enrichment

7. **Stream processor.** This is a second consumer group on `raw-events`, independent of the archiver. It runs micro-batches of about 30–60 s. For each event it does the following:
   1. Claim the `event_id` in the key-value store with put-if-absent, storing the value `(log partition, offset)` of the claiming copy. TTL is 8 days: the 7-day device buffer plus a 1-day margin.
   2. If the claim succeeds, or the stored value equals this copy's own `(partition, offset)`, the copy is the winner. The second condition makes crash recovery idempotent. A reprocessed batch recognizes its own earlier claim and does not mistake itself for a duplicate.
   3. Otherwise the copy is a duplicate. It is dropped from `events_clean` and counted in a metric. The raw copy stays in the archive.

8. **Enrichment.** Winners are enriched with geo-IP and parsed User-Agent, using the IP and headers from the envelope. Each row records the versions of the geo-IP database and UA parser it used, in an `enrichment_version` column. Replay uses this to show which rows a fix changed.

9. **Bot handling stage (open, see "Open decisions").** Reserve a named stage after dedup and before the load. This plan does not specify its behavior. Dedup runs before this stage, so a bot decision never changes which copy is the winner or the key-value state.

### Load

10. **Derive the partition.** Each winner's target partition is the UTC date of its `received_at`. An event received at 23:59:50 and processed at 00:00:20 still goes to the earlier day's partition.

11. **Idempotent warehouse load.** After each micro-batch, load the output into the day partition or partitions it belongs to, with a deterministic load ID derived from the source offset ranges. If the warehouse supports a load ID, a retried load becomes a no-op. This is assumption A1. Commit the log offsets only after the load succeeds. A crash between the claim in step 7 and the load is safe: the batch is reprocessed, step 7.2 recognizes its own claims, and the load is repeated idempotently.

12. **Freshness budget.** The allowed delay is 5 minutes from receipt to queryable. The budget is about 5 s for the collector, up to 60 s for the micro-batch window, up to 60 s for processing, and up to 60 s for the load, which leaves headroom. Measure `now() − received_at` of the newest row in `events_clean` and alert at 3 minutes.

### Day closure

13. **Closing a day.** Day D is closed at 02:00 UTC on D+1. It counts as closed for replay only if the processor's committed watermark has passed the end of D. That means every log offset with `received_at` before D+1 00:00 has been loaded. Publish the closed-day status as a small table or flag that the replay tooling reads. If the watermark is behind, the day stays open and a replay of it is refused.

## Part 2: Replay of one UTC day

An operator runs a replay of day D, typically after fixing a geo-IP or User-Agent bug.

14. **Preconditions.** The replay tool refuses to start unless all of these hold:
    1. D is closed (step 13).
    2. D is within the replayable range: today minus about 82 days. Replay needs raw data from D−8 days through D, and raw expires at 90 days, so older days lack the full lookback.
    3. No other replay of D is running (a lock per day).

15. **Isolation from live.** The replay runs as a batch job on its own compute pool. It reads only from the object-storage archive. It never reads the log, never touches the collector or the live processor, and never reads or writes the key-value store. Cap its read throughput so it cannot starve the live archiver's object-store writes.

16. **Build the seen-before set.** Read raw files for `received_date` D−8 through D−1 and collect every `event_id`. An event whose first copy came before D is a duplicate within D. The lookback is 8 days, one more than the 7-day retry window, for margin. Include all accepted copies, including duplicates. Building the set from the archive rather than from the key-value store keeps the replay independent of live state.

17. **Deduplicate day D.** Read raw files for `received_date` = D. Drop any event whose `event_id` is in the seen-before set. Among the remaining copies of an `event_id`, keep the earliest by `(received_at, collector_id, collector_seq)` and drop the others. This is the same order and rule as live (step 7), so replay produces the same set of events as live, with only the enrichment differing.

18. **Re-enrich.** Run the fixed enrichment from step 8 over the winners, stamping the new `enrichment_version`. Apply the bot stage (step 9) exactly as live does.

19. **Write to a staging location.** Write the result to a staging table or object prefix, not to `events_clean`.

20. **Validate before swap.**
    1. Compare the set of `event_id`s with the live partition D. They should match. Investigate or have an operator approve any difference, such as events near midnight whose first-copy order was decided differently because of clock skew.
    2. Compare row counts and check that no required column is null.
    3. Count rows whose enrichment values changed, to confirm the fix had the intended effect.

21. **Atomic partition replace.** Replace partition D of `events_clean` with the staged data in one atomic warehouse operation. Dashboards see either the old complete day or the new complete day, never a half-rebuilt one. Live ingestion does not append to D at this point, because D is closed and fully loaded (step 13).

22. **Post-swap.** Release the lock, record the replay in an audit log (operator, day, old and new `enrichment_version`, row counts), and keep the staging data until the next replay or a fixed number of days, to allow a manual rollback by replacing the partition again.

## Failure handling summary

| Failure | Effect | Recovery |
|---|---|---|
| Collector crash after log write, before 202 | Client times out and retries; duplicate copies stored | Deduplicated in step 7 |
| Processor crash after claim, before load | Batch is reprocessed | Own-claim check (7.2) and idempotent load (11) |
| Key-value store loses data | Some duplicates reach `events_clean` | Replay of affected closed days (14–21) repairs them |
| Archiver stalls | Log retention (14 days) is the deadline | Alert at 6 h lag (6) |
| Replay fails mid-run | Nothing changes in `events_clean` | Rerun; staging only (19) |

## Open decisions

- **Bot traffic: drop or keep with a flag.** Product has not decided, and this plan does not choose.
  - Step 9 reserves a single stage for the decision. Until it is made, no classifier is built and no bot column is added to `events_clean`.
  - Either outcome can be applied later. Raw is retained for 90 days and replay re-runs the stage over closed days.
  - The deadline for deciding is the replay window in step 14.2: days that age out of it cannot be reprocessed.
  - Dedup always runs before the stage, so the decision does not affect dedup.
  - Owner: Product. Needed to build the classifier and, if "flag" is chosen, the schema change.
