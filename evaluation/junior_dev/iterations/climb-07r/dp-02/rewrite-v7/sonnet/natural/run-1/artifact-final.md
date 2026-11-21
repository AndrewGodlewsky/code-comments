# Clickstream ingestion plan

## Summary

Website and iOS/Android clients send batches of click and screen-view events to a new collector. The collector writes each event to a replicated log, and two independent readers consume that log. One reader copies every raw event to object storage. The other drops duplicates, enriches the rest and appends them to the warehouse table `events_clean`, which has one partition per UTC day, so live events are queryable within 5 minutes. A day can later be rebuilt from the raw copies alone, into a staging table, and swapped in atomically. This isolates replay from live ingestion and from live dedup state.

## Terms

- **Collector**: the new HTTPS service that receives client batches (up to 100 events each).
- **Event**: has a client-generated `event_id` (UUID), a `device_id` and a client timestamp.
- **Log**: the existing replicated, append-only, Kafka-style log with 14-day retention. It is split into partitions. An offset is an event's position within its partition.
- **Consumer group**: a set of readers that each track their own position in the log. Groups do not affect each other.
- **`received_at`**: server time when we first took the event in. An event belongs to the UTC day of `received_at`, never of the client timestamp. That day decides its partition in `events_clean` and which replay covers it.
- **KV store**: the existing key-value store with per-key TTL. It holds live dedup state.
- **Archive**: raw events in object storage (with lifecycle rules). It is the system of record for the 90-day retention.
- **Control table**: a small warehouse table that records loaded batches, day status (`open` or `closed`), replay locks and replay outcomes.
- **Closed day**: a UTC day D that the day-close job has marked `closed`. This happens at 02:00 UTC on D+1. Only closed days can be replayed.
- **Staging table**: a scratch table where a replay builds day D before the swap.
- **Atomic partition replace**: a warehouse feature that swaps one day partition in a single step. Readers see the old partition or the new one, never a mix.

## Rules that hold everywhere

- Duplicates are identified by `event_id` alone. The first copy we receive wins and later copies are dropped from `events_clean`.
- Every accepted event, duplicates included, is kept exactly as received for 90 days.
- Retries can arrive up to 7 days after the first copy (see step 1).
- A replay must not slow live ingestion or change live dedup state. Dashboards must never see a half-rebuilt day.

## Steps: live path

1. **Client send and retry.** A client sends a batch over HTTPS. On a timeout, 429 or 5xx, it resends the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can reach us up to 7 days after the first copy. Clients never retry events the collector rejected.

2. **Validate.** The collector checks each event on its own. It rejects an event with a missing `event_id` or `device_id`, or one over 32 KB. Rejected events are listed with a reason in the response. The rest of the batch continues.

3. **Durable write.** The collector appends each accepted event to the log, keyed by `event_id`, so all copies of an event land in one log partition. A log record holds the original event bytes untouched plus an envelope: `received_at`, collector id and schema version. It writes with acks=all and at least 2 in-sync replicas. It returns 202 only after every accepted event in the batch is acknowledged. If any append fails, it returns 5xx. The client resends the whole batch, and the duplicates are dropped later.
   - **Order and `received_at`.** "First copy wins" needs one order that live and replay agree on. That order is the offset within the log partition. `received_at` is the log's own append time (Kafka-style `LogAppendTime`), so it never goes backwards within a partition. If the log cannot assign append time, the collector stamps `received_at` instead, and a reconciliation rule is needed for copies that straddle midnight (open question).

4. **Archive (consumer group 1).** The archiver writes immutable files to `raw/dt=<UTC day of received_at>/hour=HH/<log-partition>-<start-offset>-<end-offset>`. Files hold every event, duplicates included, as original bytes plus envelope and offset. File names are deterministic, so a retried write overwrites the same object. A lifecycle rule deletes objects after 90 days. The log keeps only 14 days, so the archive, not the log, is what replay reads. If the archiver lags more than 1 hour, an alert fires, well before events fall out of the log at 14 days.

5. **Dedup (consumer group 2).** One consumer runs per log partition, so order is preserved. For each event it does an atomic set-if-absent on KV key `event_id`, with value `(log partition, offset)`. The TTL is 8 days (7 days of retries plus 1 day margin), set at first sight and never refreshed.
   - If the key was absent, or its stored value equals this event's own offset, this event is the winner. The second case covers reprocessing after a crash.
   - Otherwise it is a duplicate. Count it and drop it from `events_clean`. The raw copy stays in the archive.
   - If the KV store errors, the consumer stops and retries. It never skips the check.

6. **Enrich.** Winners get geo-IP lookup and user-agent parsing. Each row keeps `event_id`, `device_id`, the client timestamp, `received_at`, the partition day (UTC day of `received_at`), and the versions used: `geoip_version`, `ua_parser_version`, `pipeline_version`.

7. **Bot stage (open).** Suspected-bot classification sits in one isolated stage after dedup and enrichment, so either product decision is a small change. See Open questions.

8. **Load.** Every 60 seconds or so, a micro-batch is written in one transaction. The transaction appends rows to the `received_at`-day partition of `events_clean` and records the batch's `(log partition, start offset, end offset)` in the control table. On a retry, an already-recorded batch is skipped, so loads are idempotent. Together with the offset-valued KV entry in step 5, a crash anywhere cannot lose or double-count an event. The target is p99 of 3 minutes from log append to queryable, with an alert at 4 minutes.

9. **Day close.** At 02:00 UTC on D+1, a job checks that the dedup consumer and the archiver have both passed day D's last offset in every partition, and that all loads are committed. If so, it marks D `closed` in the control table. If not, D stays open and the job alerts.

## Steps: replay of one UTC day D

10. **Request and gate.** An operator submits day D, the enrichment code and data versions to use, and a reason. The job refuses unless D is `closed`, no other replay holds the per-day lock for D, and the archive covers D and the 8 days before it. Since the archive keeps 90 days, D must be at most about 82 days old. A refused request changes nothing.

11. **Isolated compute.** The replay runs on its own compute pool with throttled object-storage reads. It reads only the archive and the pinned enrichment data. It never touches the live log consumers, the KV store or live tables.

12. **Rebuild dedup from raw.** Read the archive for D-8 through D. Order the copies of each `event_id` by `(log partition, offset)`. Apply the live rule: the first copy wins, and a later copy is also dropped if it is within 8 days of the current winner. Keep only D's winners. This drops events whose first copy arrived on an earlier day, as live did. A copy from after D can never displace a winner in D, because order is monotonic.

13. **Re-enrich.** Run the winners through the fixed enrichment and the bot stage, using the same code path as live with the pinned versions. Write the result to the staging table, not to `events_clean`.

14. **Validate.** The swap is blocked unless all of these hold:
    - The set of `event_id`s in staging equals the set in the live partition for D. Any difference is a dedup mismatch to investigate, not to swap.
    - Row counts match.
    - Non-enrichment columns are identical.
    - Changes in enriched columns are within the expected size for the bug fixed.
    - Null rates are sane.

    The diff report goes to the replay record.

15. **Back up, then swap.** Copy the current partition D to object storage and keep it for 14 days. Then atomically replace partition D in `events_clean` with the staging data. Release the lock and record the outcome.

16. **Rollback.** If a bad replay is found later, swap the backup back in the same way.

## What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Step 2 | Malformed event | Rejected and listed. Rest of batch accepted. Not retried. |
| Step 3 | Any append fails | 5xx. Client resends whole batch. Duplicates dropped in step 5. |
| Step 4 | Archiver write retried or crashes | Same file name overwrites the same object. Lag alert at 1 hour. |
| Step 5 | Consumer crash after KV write | On reprocess, stored offset equals own offset, so the event is still the winner. |
| Step 8 | Crash or retry around load | Recorded batch is skipped. Unrecorded batch is reloaded. |
| Step 9 | Consumers behind or loads uncommitted | Day stays open, alert fires, replay is refused. |
| Steps 10-14 | Gate or validation fails, or replay crashes | `events_clean` is untouched. Rerun is safe because the job is idempotent per day. |
| Step 15 | Bad replay found afterwards | Step 16 rollback. |

## Monitoring

- Collector: 202 latency, rejection rate by reason, append failures.
- Log: consumer lag for both groups.
- Dedup: duplicate rate and KV errors.
- Freshness: end-to-end p99.
- Archive: lag, and days with missing files.
- Replay: how many requests came for days older than 80 days, so people know the window is closing.

## Testing before launch

- Retry storms with the same batch repeated.
- A partial batch append failure.
- A consumer crash between KV write and load.
- A duplicate arriving at day 7 and again after day 8.
- Copies straddling midnight.
- A replay of a day, compared against live.
- A live load running while a different day is swapped.

## Open questions

- **Suspected bot traffic: drop, or keep with a flag?** Product has not decided and this plan does not pick one. Option 1 drops bot events from `events_clean`. Option 2 keeps them with a column such as `is_suspected_bot`. Either way the archive keeps every event, and only the single stage in step 7 changes, for live and replay alike. If bots are dropped, they should still be recorded in dedup state so a retry is not treated as new. Dedup runs before the bot stage, which supports either choice.
- **Log append time:** confirm the log supports broker-assigned timestamps (step 3). If not, the collector stamps `received_at` and a midnight reconciliation rule is needed.
- **Warehouse concurrency:** confirm the warehouse allows appends to open-day partitions while a different partition is atomically replaced (steps 8 and 15).
- **Older replay requests:** days older than about 82 days cannot be replayed. Confirm that is acceptable, or extend archive retention beyond 90 days.