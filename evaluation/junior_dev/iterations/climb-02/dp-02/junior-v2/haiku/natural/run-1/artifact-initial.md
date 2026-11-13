# Clickstream ingestion plan: `events_clean`

## Summary

Click and screen-view events from the website and the iOS and Android apps pass through a collector, a replicated log, a raw archive, a deduplication stage, enrichment, and a warehouse load into `events_clean`, which is partitioned by UTC day of `received_at`. Two rules shape the whole design:

- The **raw archive** is the system of record for 90 days. Kafka keeps only 14 days, so replay reads from the archive, not from Kafka.
- Deduplication decisions are **recorded once** in a decision ledger. Replay reuses those decisions and never touches the live dedup state.

## Assumptions and terms

- **Winner.** The first copy of an `event_id` to be decided by the dedup stage. The dedup stage decides in log order for that `event_id`'s partition. Each accepted copy gets an `envelope_id` (UUID) at the collector.
- **Raw envelope.** The event's exact received bytes, plus collector metadata (`envelope_id`, `received_at`, `batch_id`, `collector_id`). The event bytes are never re-serialized.
- **Day close.** Day D closes at 02:00 UTC on D+1. A close watchdog marks D as closed only after the live pipeline has passed the close time.
- **Retry window.** A retry can arrive up to 7 days after the first copy. This plan assumes the 7 days is measured from event creation or first send, which means every copy arrives within 7 days of our first receipt of that event. Confirm this with the mobile SDK owners (open item 2).

## Live path

1. **Client batching.** Each SDK sends batches of up to 100 events over HTTPS. Every event carries a UUID `event_id`, a `device_id`, and a client timestamp. Retries reuse the same `event_id`s and back off exponentially from 1 s to 5 min. Unacknowledged events stay in an on-device buffer for up to 7 days.

2. **Collector receives the batch.** The collector stamps `received_at` from server UTC time when the request arrives. Stamping and durable write must finish within a bounded write deadline `T_w` (proposed 30 s, to confirm; see open item 3).

3. **Per-event validation.** The collector checks each event independently:
   - `event_id` present
   - `device_id` present
   - raw event size 32 KB or less

   Failing events are rejected one at a time. Each rejection is listed in the response with its batch index and a reason. Clients never retry rejected events.

4. **Durable write before acknowledgement.** Each accepted event is published as a raw envelope to the replicated log, keyed by `event_id` so that every copy of an event lands in the same partition. The publish uses acks from all in-sync replicas. The collector returns **202 only after this write is acknowledged**, and the 202 body lists the rejected events.

5. **Failure during the write.** If the publish fails or misses `T_w`, the collector returns 5xx for the whole batch, including events that were valid. Clients resend the batch with the same `event_id`s, and dedup absorbs any copies that did land.

6. **Raw archive copy.** A separate consumer group reads the log and writes envelopes byte-for-byte to object storage. Files are partitioned by `received_at` UTC day and hour, and are flushed about every 60 seconds. The consumer commits its offset only after a file is complete. This is the 90-day system of record and the input to replay.

7. **Dedup against the global key-value store.** A second consumer group runs one atomic set-if-not-exists per `event_id`, with a TTL of 8 days (the 7-day retry window plus one day of margin). The stored value is `{winner_envelope_id, winner_received_day}`.
   - **Set succeeds:** this copy is the winner. It goes on to enrichment.
   - **Key exists with a different `envelope_id`:** this copy is a duplicate. It is not written to `events_clean`.
   - **Key exists with this `envelope_id`:** this is a redelivery of the winner. It is processed again idempotently.
   - **Store unavailable:** stall and alert. Never guess, and never fail open.

   The TTL is set only on the first insert. Duplicates do not refresh it.

8. **Decision ledger.** For every envelope the dedup stage writes one row: `envelope_id`, `event_id`, `received_at`, `received_day`, `decision` (winner or duplicate), and `winner_envelope_id`. The ledger is append-only, stored in object storage and partitioned by `received_day`, and retained 90 days. Rows are keyed by `envelope_id`, so rewrites from redelivery are harmless.

9. **Enrichment.** Winners get a geo-IP lookup and user-agent parsing. Each row records `enrichment_version`, the geo database version, and the user-agent parser version. A **bot-traffic step is present but unresolved** (see Open decisions). The step is a placeholder and must not be implemented as drop or flag until product decides.

10. **Warehouse load.** A micro-batch loader runs every 1 to 2 minutes and appends winners to the `received_day` partition of `events_clean`. Each load is idempotent: it uses MERGE on `event_id` within the partition, so a replayed batch does not insert twice.

11. **Freshness.** The freshness budget runs from collector receipt to queryable row. The budget is: batch wait under 1 min, dedup and enrichment under 1 min, load under 2 min, leaving headroom for 5 min. Track p95 and p99 freshness. Alert at 3 min and page at 5 min.

12. **Live-path reconciliation.** Hourly, compare the accepted envelope count in the log, the ledger row count, and the winner count in `events_clean`, all per `received_day`. Nightly, scan `events_clean` for duplicate `event_id`s across partitions. The expected count is zero. A non-zero count means the KV TTL expired too early or the dedup logic is wrong, and the day needs a replay.

## Day close (02:00 UTC on D+1)

13. **Collector bound.** Before a request is acknowledged, the collector confirms its durable write completes within `T_w` of the stamp. Any envelope stamped with D is durable within `T_w`.

14. **Close watchdog.** At 02:00 plus `T_w` plus a lag margin, the watchdog checks that the copy consumer, the decision ledger, and the warehouse loader have all processed past the 02:00 stamp boundary. It then writes a close record for D (counts, watermarks, and the manifest of raw and ledger objects). Only then is D marked **closed** and eligible for replay.

15. **Stragglers.** An envelope stamped D that is found after the close record is still archived in raw and ledgered. Its effect on the warehouse is corrected by the next replay of D (step 23). The completeness check (step 19) detects it.

## Replay (rebuild one closed UTC day)

16. **Request.** An operator requests a replay of day D with a reason and a target enrichment version. The replay is a separate job with its own compute and quotas.

17. **Preconditions.** Refuse the replay unless all of these hold:
    - D is marked closed.
    - The raw copy watermark and the ledger watermark are past the close boundary for D.
    - The current time is before the replay deadline, which is D+90 days minus a safety margin.

    The replay deadline is set by raw object lifecycle (step 27). Raw objects are removed 90 days after they are created, which is always at or after `received_at`, so raw data for D exists until at least D+90 days.

18. **Freeze the inputs.** List the raw objects for D and the ledger objects for D, and record them as an immutable manifest with a hash. Later files do not change this run.

19. **Completeness and integrity checks.** Before any write, verify:
    - Every ledger row with `decision = winner` and `received_day = D` has a matching raw envelope with the same `envelope_id`.
    - No `event_id` has two winners.
    - Each raw envelope is the exact stored byte sequence, verified against stored checksums.

    Any failure aborts the replay. Nothing becomes visible.

20. **Build the replay input.** Join raw envelopes for D to ledger rows where `decision = winner` and `received_day = D`. This set is the one the live path produced. Replay does not re-run dedup, does not read the KV store, and does not read Kafka.

21. **Enrich into staging.** Re-parse each event and re-run enrichment with the pinned target versions of the geo database and user-agent parser. Write the output to a separate staging table keyed by a run ID, not to `events_clean`. Staging writes are rate-limited so they do not compete with the live loader.

22. **Validate staging.**
    - Row count equals the winner count from step 19.
    - Schema matches `events_clean`.
    - `enrichment_version` is set to the target value on every row.
    - Null rates and distributions are within agreed bounds of the previous version, and differences are reviewed by the operator.
    - A random sample of rows is spot-checked.

23. **Atomic swap.** Replace partition D of `events_clean` with the validated staging partition in a single warehouse operation. Dashboards read either the old day or the new day, never a partial rebuild. The previous partition is retained (through warehouse snapshots or a copy) so the swap can be rolled back.

24. **Audit and cleanup.** Record the run ID, D, target enrichment version, manifest hash, input and output counts, operator, and timestamps. Drop the staging partition after the swap is verified.

## Storage and retention

| Store | Contents | Retention | Notes |
|---|---|---|---|
| Replicated log | Raw envelopes | 14 days | Copy to archive within minutes. Alert when copy lag exceeds 1 day. |
| Object storage (raw archive) | Raw envelopes, partitioned by day and hour | 90 days from object creation | Lifecycle rule. Creation is never before `received_at`, so the requirement holds. Source for replay. |
| Key-value store (dedup) | `event_id` to winner envelope | 8 days, per-key TTL | Set only on first insert. Stores no event content. |
| Object storage (ledger) | One row per envelope with its decision | 90 days | Input to replay alongside raw. |
| Warehouse `events_clean` | Winners only, enriched | Per product policy | Partitioned by UTC day of `received_at`. Replay swaps partitions atomically. |
| Warehouse staging | Replay output | Until swap is verified | Never read by dashboards. |

Rejected events are not accepted, so they are not required to be kept. Counts of rejections are logged for operations.

## Failure handling

- **Collector or log unavailable.** Collector returns 5xx. Clients retry with backoff. The mobile buffer covers up to 7 days. Capacity planning must keep the collector ahead of the 7-day retry tail.
- **Key-value store unavailable.** The dedup consumer stalls and does not advance. Alert. Nothing is decided incorrectly, and lag builds up in the log, which has 14 days of retention.
- **Warehouse unavailable.** The loader stalls and lag builds. The raw archive copy and the ledger continue independently.
- **Consumer crash.** On restart, redelivered envelopes are handled idempotently (steps 7 and 10).
- **Archive copy falls behind for 14 days.** Log data is lost. Alert long before this point.

## Open decisions

1. **Bot traffic (not decided; do not choose).** Product must decide between dropping suspected bot events and keeping them with a flag in `events_clean`. The raw archive keeps every accepted event either way, so the decision changes only `events_clean` and the live path. Once decided, the rule can be applied on closed days through replay. Until then, the enrichment step in step 9 stays as a placeholder.
2. **Dedup TTL margin.** Confirm with mobile SDK owners that the 7-day buffer is measured from creation or first send. The plan uses 8 days. If the buffer can extend, the TTL must be raised or the dedup must move to a durable store.
3. **Write deadline `T_w`.** Set the value (proposed 30 s) and confirm that the collector can enforce it under load. The value determines the lag margin for the close watchdog.
4. **Definition of "durably stored".** Confirm that a replicated log with acks from all in-sync replicas meets the durability requirement for the 202 response.
5. **Warehouse capabilities.** Confirm that the warehouse supports MERGE within a partition at the micro-batch rate needed for 5-minute freshness, and atomic single-partition replace at the size of a day.
6. **Replay deadline.** Confirm the operational deadline for replay, which must sit comfortably inside the D+90 raw retention window.
7. **Ordering of "first".** The plan defines "first" as the dedup stage's decision order per `event_id` partition. Confirm that this matches the product definition of "first copy we receive".

## Verification

- Load tests with duplicate copies arriving 0, 1, 7 and 8 days after the first copy. Expect the copy to be dropped at 0, 1 and 7 days and accepted as a duplicate or a new winner only beyond the TTL, which is the case the nightly reconciliation must catch.
- Fault injection: kill consumers between the KV write and the loader commit, and confirm no duplicate rows in `events_clean`.
- A replay of a closed day with no enrichment change must produce a partition identical to the live output for that day.
- A replay with a changed enrichment version must change only the enrichment columns and the `enrichment_version` value.
- A replay under full live load must not change the live freshness p99 beyond the alert threshold.
- Freshness and ledger reconciliation dashboards must show zero unexplained differences for a full week before the pipeline is considered live.