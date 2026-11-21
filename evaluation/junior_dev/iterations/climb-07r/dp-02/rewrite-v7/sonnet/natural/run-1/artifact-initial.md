# Clickstream ingestion plan

## Summary

Events go collector → replicated log → two independent consumers. One consumer archives raw events to object storage. The other deduplicates, enriches and appends to `events_clean`. Replay rebuilds a closed day from the raw archive only. It builds into a staging table and swaps the partition atomically. It never touches the live log consumers or the live dedup state.

## Decisions and assumptions to confirm

- **Canonical order and `received_at`.** "First copy wins" needs one order that live and replay agree on. The log is keyed by `event_id`, so all copies of an event land in one log partition. Order is the offset within that partition. `received_at` is the log's append timestamp (Kafka-style `LogAppendTime`), so it never goes backwards within a partition. Assumption to verify: the log supports broker-assigned append time. If it doesn't, the collector stamps `received_at` and I add a small reconciliation rule for copies that straddle midnight.
- **Dedup window of 8 days.** Retries can arrive up to 7 days after the first copy, so the KV TTL is 8 days (7 plus 1 day margin). The TTL is set at first sight and never refreshed.
- **Raw archive window of 90 days.** The log keeps only 14 days, so the archive is the system of record for the 90-day retention. Replay reads the archive, not the log.
- **Warehouse capability.** Live appends go into the open-day partitions of `events_clean`. Replay swaps one closed-day partition atomically. Assumption to verify: the warehouse allows appends into other partitions while a different partition is replaced.

## Part A: Live path

1. **Collector validation.** For each batch of up to 100 events, check each event independently. Reject an event if `event_id` or `device_id` is missing, or if it is over 32 KB. Accepted events continue. Rejected events are listed in the response with a reason. Clients never retry them.

2. **Durable write.** Append each accepted event to the log, keyed by `event_id`. The log record holds the original event bytes untouched plus an envelope: `received_at`, collector id and schema version. Use acks=all and require at least 2 in-sync replicas. Return 202 only after every accepted event in the batch is acknowledged. If any append fails, return 5xx. The client resends the whole batch and the duplicates are dropped later.

3. **Raw archiver (consumer group 1).** Read the log and write immutable files to object storage. Layout: `raw/dt=<UTC day of received_at>/hour=HH/<log-partition>-<start-offset>-<end-offset>`.
   - Files hold every event, duplicates included, with the original bytes plus envelope and offset.
   - File names are deterministic, so a retried write overwrites the same object.
   - A lifecycle rule deletes objects after 90 days.
   - Alert if archiver lag passes 1 hour. Page well before 14 days, when events would fall out of the log.

4. **Dedup and enrich (consumer group 2).** Run one consumer per log partition, so ordering is preserved. For each event, run an atomic set-if-absent on the KV key `event_id`. The value is `(log partition, offset)` and the TTL is 8 days.
   - If the key was absent, or its stored value equals this event's own offset, this event is the winner. The second case handles reprocessing after a crash.
   - Otherwise it is a duplicate. Count it and drop it from `events_clean`. The raw copy stays in the archive.

5. **Enrichment.** Winners get geo-IP lookup and user-agent parsing. Each row records the enrichment versions used (`geoip_version`, `ua_parser_version`, `pipeline_version`). Rows keep `event_id`, `device_id`, the client timestamp, `received_at`, and the partition day, which is the UTC day of `received_at`.

6. **Bot handling (open).** Put suspected-bot classification in one isolated stage after dedup and enrichment, so either product decision is a small change. It is not decided, see Open questions.

7. **Load within the 5-minute budget.** Micro-batch every 60 seconds or so. Each batch is one transaction that appends rows to the `received_at`-day partition of `events_clean`. The same transaction records the batch's `(log partition, start offset, end offset)` in a control table. On retry, an already-recorded batch is skipped, so loads are idempotent.
   - Together with the offset-valued KV entry from step 4, a crash anywhere in the pipeline cannot lose or double-count an event.
   - Target p99 of 3 minutes from log append to queryable. Alert at 4 minutes.

8. **Day close.** At 02:00 UTC the next day, a job checks that the live consumer and the archiver have both passed the day's last offset in every partition, and that all loads are committed. It then marks the day `closed` in the control table. If the check fails, the day stays open and the job alerts. Only `closed` days can be replayed.

## Part B: Replay of one UTC day D

9. **Request and gate.** An operator submits day D, the enrichment code and data versions to use, and a reason. The job refuses unless these hold:
   - D is `closed`.
   - D is within the archive's reach. The archive must cover D and the 8 days before it, so D must be at most about 82 days old.
   - No other replay holds the per-day lock for D.

10. **Isolated compute.** Run the replay on its own compute pool, with throttled object-storage reads. It reads only the archive and the pinned enrichment data. It never reads or writes the live log consumers, the KV store, or live tables, so live ingestion is unaffected.

11. **Rebuild dedup from raw.** Read all raw copies with `received_at` in D. Also read the archive for D-8 through D-1.
    - Order the copies of each `event_id` by `(log partition, offset)`.
    - Apply the live rule: the first copy wins. A later copy is also dropped if it is within 8 days of the current winner.
    - Keep D's winners only. This drops events whose first copy arrived on an earlier day, as live did.
    - A copy from after D can never displace a winner in D, because the order is monotonic.

12. **Re-enrich.** Run the winners through the fixed enrichment and the bot stage, using the same code path as live with the pinned versions. Write the result to a staging table, not to `events_clean`.

13. **Validate before swap.** The swap is blocked unless all of these hold:
    - The set of `event_id`s in staging equals the set in the live partition for D. Any difference means a dedup mismatch to investigate, not to swap.
    - Row counts match.
    - Non-enrichment columns are identical.
    - Changes in enriched columns are within the expected size for the bug fixed.
    - Null rates are sane.

    Write the diff report to the replay record.

14. **Back up, then swap.** Copy the current partition D to object storage for rollback and keep it for 14 days. Then atomically replace partition D in `events_clean` with the staging data. Dashboards see either the old partition or the new one, never a half-built day. Release the lock, record the outcome, and keep the old copy for rollback.

15. **Rollback and retries.** If a bad replay is discovered, swap the backup back in the same way. A failed replay leaves `events_clean` untouched, so a rerun is safe because the job is idempotent per day.

## Part C: Operations

16. **Monitoring.**
    - Collector: 202 latency, rejection rate by reason, and append failures.
    - Log: consumer lag for both groups.
    - Dedup: duplicate rate and KV errors.
    - Freshness: end-to-end p99.
    - Archive: lag, and days with missing files.
    - Replay: how many days older than 80 days have been requested, so people know the window is closing.

17. **Testing before launch.**
    - Retry storms with the same batch repeated.
    - A partial batch append failure.
    - A consumer crash between KV write and load.
    - A duplicate arriving at day 7 and again after day 8.
    - Copies straddling midnight.
    - A replay of a day, compared against live.
    - A live load running while a different day is swapped.

## Open questions

- **Suspected bot traffic: drop, or keep with a flag?** Product has not decided and this plan does not pick one.
  - Option 1: drop bot events from `events_clean`.
  - Option 2: keep them with a column such as `is_suspected_bot`.
  - Either way, the raw archive keeps every event, and the classifier sits in the single stage in step 6, so both live and replay change in one place.
  - Sub-question for product: if bot events are dropped, they should still be recorded in dedup state, so a retry of a dropped bot event is not later treated as new. I have assumed dedup runs before the bot stage, which supports either choice.
- **Log append time** (see Decisions): confirm the log supports broker-assigned timestamps.
- **Warehouse concurrency** (see Decisions): confirm appends can run while another partition is replaced.
- **Older replay requests:** days older than about 82 days cannot be replayed. Confirm that is acceptable, or extend the archive retention beyond 90 days.
