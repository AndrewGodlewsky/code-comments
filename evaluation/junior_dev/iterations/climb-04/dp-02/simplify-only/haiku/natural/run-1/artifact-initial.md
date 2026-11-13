# Clickstream ingestion: plan

Goal: web, iOS and Android click and screen-view events land, deduplicated and enriched, in `events_clean`, which has one partition per UTC day. Live events are queryable within 5 minutes of the collector receiving them. Replay rebuilds one closed UTC day without touching live ingestion or live deduplication state.

## Decisions and open items

- **Open (not decided by us):** whether suspected bot traffic is dropped from `events_clean` or kept with a flag. The plan leaves a slot for either option in step 9. Both options keep every accepted event in the raw archive, so this choice does not affect the 90-day rule. Until product decides, the bot step is a no-op that writes no flag and drops nothing.
- **Assumption to confirm with the warehouse owners:** the warehouse can atomically replace a day partition (given), but cheap micro-batch appends into an open day are not given. The plan therefore serves the open day from a staging table and does not rely on appends to a closed partition.
- **Assumption to confirm with the mobile SDK owners:** the 7-day on-device buffer is a hard maximum. The dedup window (8 days) depends on it.

## Live path

1. **Client contract.** The SDK batches up to 100 events and sends them over HTTPS. Each event carries a client-generated `event_id` (UUID), `device_id` and client timestamp. On timeout, 429 or 5xx, the SDK resends the same batch with the same `event_id`s, backing off from 1 s to 5 min. It keeps unacknowledged events on device for up to 7 days. It never retries events the collector listed as rejected.

2. **Collector validation.** For each event, the collector checks that `event_id` and `device_id` are present and that the event is at most 32 KB. Invalid events are rejected individually with their index and reason. The rest of the batch continues. Rejected events are not stored as accepted (an optional quarantine store is out of scope).

3. **Receipt stamp.** The collector stamps `received_at` (server UTC) once per request, along with `batch_id`, `collector_id` and a write deadline (received_at plus a bounded window, for example 60 s). The event's partition day is the UTC date of `received_at`. The client timestamp is kept as a column and never decides the partition.

4. **Durable write before 202.** The collector appends each accepted event to the replicated log, keyed by `event_id`. The append stores the event's original JSON bytes unchanged, plus the envelope (`received_at`, `batch_id`, `collector_id`). It waits for full replication acknowledgement. Only after that does it return 202 with the rejected list. If the append fails or misses the deadline, it returns 503 so the client retries. Keying by `event_id` puts every copy of an event in the same log partition, so their offset order is the order of arrival.

5. **Raw archive (90 days).** A consumer copies every accepted record from the log to object storage, under `raw/dt=<received_at UTC date>/`. Records keep their original bytes and envelope, duplicates included. The consumer commits its log offset only after the object write is acknowledged. The log retains 14 days, so an archive lag alarm must fire well before that. Lifecycle is by received_at day, not object creation time: a prefix job deletes `dt < today - 90`, and an object lifecycle rule (at 91 days or later) is a backstop.

6. **Late-record guard.** Any record whose broker commit completes after `received_at + deadline` is treated as not accepted. The consumer flags it in the raw archive as `late_discarded` and excludes it from dedup and `events_clean`. Because the 202 is returned only before the deadline, this keeps the set of accepted records for day D fixed shortly after 00:00 UTC on D+1.

7. **Dedup (live state).** One consumer per log partition processes records in offset order. For each event it runs a conditional insert into the key-value store: key `event_id`, value `{received_at, partition, offset}`, insert only if absent. The TTL is the dedup window W = 8 days, which exceeds the 7-day retry bound. If the store supports an absolute expiry, set it to `received_at + W` so the expiry does not depend on insert lag. A copy that loses the insert is dropped from `events_clean`. Reprocessing the same record after a crash is idempotent because the stored winner matches the same `(partition, offset)`.

8. **Enrichment.** Surviving events go through geo-IP lookup and user-agent parsing. Each row records `enricher_version`, so every row shows which code built it. Enrichment never changes the raw archive.

9. **Bot-traffic slot (open).** One stage after enrichment. Its behaviour is set by product: either drop rows, or write `is_suspected_bot` and keep them. This stage is the only place the choice takes effect.

10. **Freshness path.** Every 60 seconds, a sink writes the micro-batch of winners to `events_clean_open`, the staging table for the current open day(s). Each micro-batch is tagged with its log partition and offset range, and the sink ignores a batch it has already written, so retries do not double-count. Freshness budget: collector receipt to queryable in under 5 minutes at p99. Alert at 3 minutes.

11. **Query surface.** `events_clean` is presented as a view. It returns closed days from the warehouse partitions where `day <= closed_through`, and open days from `events_clean_open` where `day > closed_through`. `closed_through` is a one-row watermark table.

## Day close (automatic)

12. **Close gate.** Day D closes at 02:00 UTC on D+1. The job starts only when all three hold: the clock is past the close time, every log partition has been consumed past 00:00 UTC on D+1 plus the write deadline, and the raw archive for D has no records pending in the consumer.

13. **Finalize.** The finalize job rebuilds day D from the raw archive, not from staging. It runs the dedup rule in step 16, enrichment and bot slot. It writes the result to a shadow partition. It then reconciles the result against `events_clean_open` for D: same count and same set of `event_id`s. Any difference blocks the swap and raises an alert for a person to review.

14. **Swap.** Replace the `events_clean` partition for D from the shadow partition in one atomic operation. Then set `closed_through = D` and delete D's rows from `events_clean_open`. Because the view reads the watermark, dashboards move from staging to the warehouse partition in a single step and never see a half-written day.

## Replay (operator-triggered, closed days only)

15. **Eligibility.** Replay of day D is allowed only if D is closed (now is at or after 02:00 UTC on D+1), D is within the 90-day archive, and no other replay or finalize holds the lock for D. The operator names the enricher version to apply.

16. **Read-only inputs.** The replay job reads raw objects for days D-8 through D. It holds no write credentials for the log, the key-value store, `events_clean_open` or `closed_through`. Enforce this with IAM, so the rule holds even if the job has a bug.

17. **Deterministic dedup, same as live.** Among the accepted copies of each `event_id`, the winner is the copy with the smallest `(received_at, partition, offset)` within the window. A copy of an event dated D is dropped if a winner exists with received_at within W before its own received_at. Only copies dated D are output. Records flagged `late_discarded` are excluded. Live and replay therefore apply the same predicate. The only exception is a key-value failure during live processing (see step 22), which the reconciliation in step 19 will show.

18. **Rebuild in shadow.** Enrich with the requested `enricher_version` and apply the bot slot. Write to a shadow partition of `events_clean` (or a rebuild table). Nothing reads the shadow until the swap. Run the replay in its own compute pool with quotas, so it cannot starve live consumers.

19. **Verify.** Compare the replay's `event_id` set for D against the live set in the warehouse. Expected differences in `event_id`s are zero, unless a live key-value outage is recorded in the incident log. Enrichment column changes are expected and are sampled for an operator to review. Record counts per enricher version.

20. **Swap.** Replace `events_clean` partition D from the shadow in one atomic operation. Keep the previous partition until the operator confirms the new build, so rollback is possible. If the warehouse has time travel, use it; otherwise keep the old partition for a fixed period.

21. **Audit.** Write one row per replay to `replay_runs`: day, enricher version, operator, counts, dedup diff, swap time and rollback handle. Live ingestion, live dedup state and the open-day staging table are never touched by replay.

## Failure handling

22. **Key-value store down.** The dedup consumers pause at their last committed offset. The log holds the records, so nothing is lost and nothing is double-counted. Freshness breaks, and the 5-minute alarm fires. The log's 14-day retention gives time to recover. On recovery, consumers resume from the committed offset in order, so the winners match the rule in step 17.

23. **Log down.** Collectors return 503, and clients retry the same batch with the same `event_id`s. Duplicate log appends from client retries are stored as separate records, with their own received_at. The dedup rule handles them.

24. **Archive lag.** If the raw archive falls more than 1 day behind, alert. If it reaches 12 days behind, page someone. Replay and the 90-day rule both depend on the archive.

25. **Duplicates older than the window.** A retry that arrives more than W after the first copy would be counted as a new event, in both live and replay. Monitor the 7-day buffer assumption with the mobile team and keep W configurable. A change to W is a versioned change, applied to live and replay together.

## Requirement checklist

| Requirement | Where it is met |
|---|---|
| 202 only after durable store | Step 4 (replicated append), step 6 (deadline) |
| Malformed events rejected one at a time, batch still accepted | Step 2 |
| Same `event_id` on retry, 7-day buffer | Steps 1, 7 (W = 8 days), 25 |
| Partition by received_at UTC day | Steps 3, 10, 14 |
| Duplicates dropped by `event_id`, first copy wins | Steps 7, 17 |
| All accepted events kept for 90 days | Steps 5, 6, 17 |
| Replay of closed days only | Steps 12, 15 |
| Replay does not slow live or change dedup state | Steps 16, 18, 21 |
| Dashboards never see a half-rebuilt day | Steps 11, 14, 20 |
| Live queryable within 5 minutes | Step 10 |

## Open items for product and owners

- Bot traffic: drop or keep with a flag (step 9). Open.
- Warehouse append behaviour for open-day staging (assumption above).
- Whether rejected events need a quarantine store for debugging (not required by the brief).
- Confirmation that the 7-day SDK buffer is a hard maximum (sets W).