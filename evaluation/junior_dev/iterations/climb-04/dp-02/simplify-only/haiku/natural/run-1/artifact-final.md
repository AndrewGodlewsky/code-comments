# Clickstream ingestion: plan

This pipeline takes click and screen-view events from the website and the iOS and Android apps, removes duplicates, enriches them and writes them to `events_clean`, a warehouse table with one partition per UTC day. Live events are queryable within 5 minutes. Replay rebuilds one closed day from the raw archive without touching live ingestion or live dedup state.

The main flow: clients send batches to a collector. The collector stores each accepted event in a replicated log, then returns 202. From the log, events go to a raw archive and to dedup, enrichment and a staging table that dashboards read while the day is open. At 02:00 UTC the next day, a finalize job rebuilds the day from the raw archive, checks it against staging, and swaps it into `events_clean`.

The plan uses existing infrastructure: a replicated log (14-day retention), object storage with lifecycle rules, a key-value store with per-key TTL, and a warehouse that can atomically replace one day partition.

## Terms

- **Event:** one click or screen view, with a client-made `event_id` (UUID), a `device_id` and a client timestamp.
- **Batch:** up to 100 events sent together in one HTTPS request.
- **Collector:** the new service that receives batches, checks them and writes accepted events to the log.
- **Log:** the replicated append-only log where accepted events are first stored.
- **Raw archive:** object storage holding every accepted event exactly as received, duplicates included, for 90 days.
- **Partition day (D):** the UTC date of `received_at`, the server time the collector stamps. It sets the event's partition and which replay covers it. The client timestamp never sets it.
- **Dedup window (W):** 8 days. Retries arrive up to 7 days after the first copy.
- **Key-value store:** remembers the winning copy of each `event_id` for W.
- **`events_clean_open`:** staging table for the open day or days, written every minute.
- **`events_clean`:** the warehouse table, one partition per closed day.
- **`closed_through`:** a one-row table holding the last day moved into `events_clean`.
- **Shadow partition:** a temporary build of one day. Nothing reads it until it is swapped in.
- **`late_discarded`:** a flag on an archived record whose log commit finished after its deadline.

## The dedup rule

Among the accepted copies of an `event_id`, the winner is the copy with the smallest `(received_at, partition, offset)` within W. A copy dated D is dropped if a winner exists whose `received_at` is within W before its own. Only copies dated D are output. Records flagged `late_discarded` are never counted. Live dedup and replay use this same rule. The one exception is a key-value store failure during live processing, which the verify step will show.

## Live path

1. **Client sends a batch.**
   - Starts: the SDK has events to send, or a retry timer fires.
   - Does: sends up to 100 events over HTTPS. On timeout, 429 or 5xx, it resends the same batch with the same `event_id`s, backing off from 1 s to 5 min. It never resends events the collector listed as rejected.
   - Keeps: unacknowledged events stay in an on-device buffer for up to 7 days.
   - If it fails: it keeps retrying until acknowledged. Retries stop when the 7-day buffer runs out.

2. **Collector checks each event.**
   - Starts: a batch arrives.
   - Does: checks that each event has `event_id` and `device_id` and is at most 32 KB. Rejects bad events one at a time, with index and reason. The rest of the batch continues. Rejected events are not stored.
   - Keeps: nothing.
   - If it fails: the bad event is listed in the response. The batch is still accepted.

3. **Collector stamps receipt.**
   - Starts: valid events remain.
   - Does: stamps `received_at` (server UTC) once per request, with `batch_id`, `collector_id` and a write deadline (for example, `received_at` plus 60 s). The partition day is the UTC date of `received_at`.
   - Keeps: the stamp travels with each event into the log.
   - If it fails: nothing is stored and the batch is not acknowledged, so the client retries.

4. **Collector writes to the log before replying.**
   - Starts: stamped events.
   - Does: appends each accepted event to the log, keyed by `event_id`. It stores the original JSON bytes unchanged, plus the envelope (`received_at`, `batch_id`, `collector_id`). It waits for full replication, then returns 202 with the rejected list. Because the key is `event_id`, every copy of an event lands in the same log partition, so offset order is arrival order.
   - Keeps: the log, for 14 days.
   - If it fails: an append error or a missed deadline returns 503, and the client retries. Retried copies are stored as separate records with their own `received_at`. Dedup handles them.

5. **Archive copies every record.**
   - Starts: a new record in the log.
   - Does: a consumer copies each accepted record to `raw/dt=<received_at UTC date>/`, with original bytes and envelope, duplicates included. It commits its log offset only after the object write is acknowledged. A prefix job deletes objects where `dt < today - 90`. An object lifecycle rule at 91 days is a backstop. Lifecycle follows the `received_at` day, not the object creation time.
   - Keeps: the archive, for 90 days.
   - If it fails: without the commit, the record is copied again. Archive lag alarms: alert at more than 1 day behind, page at 12 days behind.

6. **Late guard.**
   - Starts: a record's log commit completes.
   - Does: if the commit completes after `received_at` plus the deadline, the record is flagged `late_discarded` in the archive and excluded from dedup and `events_clean`. Because 202 is returned only before the deadline, the accepted set for day D is fixed shortly after 00:00 UTC on D+1.
   - Keeps: the flagged archive copy.
   - If it fails: not applicable. A late record is never counted.

7. **Dedup.**
   - Starts: a record that is not late, read in offset order by one consumer per log partition.
   - Does: runs a conditional insert into the key-value store, with key `event_id` and value `{received_at, partition, offset}`. It inserts only if the key is absent. TTL is W = 8 days, or an absolute expiry of `received_at` + W if the store supports it. The insert winner moves on. A losing copy is dropped from `events_clean`.
   - Keeps: the key-value store, for W.
   - If it fails: if the store is down, consumers pause at their last committed offset. Nothing is lost or double-counted. Reprocessing after a crash is safe, because the stored winner has the same `(partition, offset)`.

8. **Enrichment.**
   - Starts: a winner.
   - Does: runs geo-IP lookup and user-agent parsing. Each row records `enricher_version`, so every row shows which code built it. Enrichment never changes the raw archive.
   - Keeps: the enriched row.
   - If it fails: not specified yet. See open questions.

9. **Bot-traffic step (open).**
   - Starts: an enriched row.
   - Does: product will choose one behaviour. Either drop the row, or write `is_suspected_bot` and keep it. This step is the only place the choice takes effect. Both options keep every accepted event in the archive, so the 90-day rule is unaffected. Until product decides, this step is a no-op: it writes no flag and drops nothing.
   - Keeps: the row, unchanged.
   - If it fails: not specified yet. See open questions.

10. **Freshness sink.**
    - Starts: every 60 seconds.
    - Does: writes the micro-batch of winners to `events_clean_open`. Each micro-batch is tagged with its log partition and offset range. The sink skips any batch it has already written, so retries do not double-count. Budget: collector receipt to queryable in under 5 minutes at p99. Alert at 3 minutes.
    - Keeps: `events_clean_open`, for the open days.
    - If it fails: the sink retries. The skip rule prevents duplicates. The 3-minute alert fires first.

11. **Query view.**
    - Starts: a dashboard query.
    - Does: `events_clean` is a view. For days where `day <= closed_through`, it reads the warehouse partition. For days where `day > closed_through`, it reads `events_clean_open`. Because the view reads the watermark, dashboards move from staging to the warehouse in one step.
    - Keeps: `closed_through`.
    - If it fails: nothing is written here, so there is nothing to fail.

## Day close (automatic)

12. **Close gate.**
    - Starts: the clock passes 02:00 UTC on D+1.
    - Does: the finalize job starts only when all three hold. The clock is past 02:00 UTC on D+1. Every log partition has been consumed past 00:00 UTC on D+1 plus the write deadline. The raw archive for D has no records pending in the consumer.
    - Keeps: nothing.
    - If it fails: the job does not start. It waits.

13. **Finalize.**
    - Starts: the gate passes.
    - Does: rebuilds D from the raw archive, not from staging. It applies the dedup rule, enrichment and the bot-traffic step, and writes the result to a shadow partition. It then compares the shadow with `events_clean_open` for D. The counts and the sets of `event_id`s must match.
    - Keeps: the shadow partition.
    - If it fails: any difference blocks the swap and raises an alert for a person to review.

14. **Swap.**
    - Starts: the comparison passes.
    - Does: replaces the `events_clean` partition for D with the shadow partition, in one atomic operation. Then sets `closed_through = D` and deletes D's rows from `events_clean_open`.
    - Keeps: the warehouse partition for D.
    - If it fails: the atomic replace leaves the previous state in place. Failures in the later two writes are not specified. See open questions.

## Replay (operator-triggered, closed days only)

15. **Eligibility.**
    - Starts: an operator asks to replay day D and names an enricher version.
    - Does: allows the replay only if D is closed (now is at or after 02:00 UTC on D+1), D is within the 90-day archive, and no other replay or finalize holds the lock for D.
    - Keeps: the lock for D.
    - If it fails: the request is refused.

16. **Read-only inputs.**
    - Starts: an approved replay begins.
    - Does: reads raw objects for days D-8 through D. It has no write access to the log, the key-value store, `events_clean_open` or `closed_through`. IAM enforces this, so the rule holds even if the job has a bug.
    - Keeps: nothing.
    - If it fails: nothing live is touched.

17. **Dedup.**
    - Starts: the records are read.
    - Does: applies the dedup rule. Only copies dated D are output. `late_discarded` records are excluded.
    - Keeps: nothing live.
    - If it fails: nothing live is touched.

18. **Rebuild in shadow.**
    - Starts: the dedup output is ready.
    - Does: enriches with the requested `enricher_version` and applies the bot-traffic step. Writes to a shadow partition or rebuild table. Nothing reads the shadow until the swap. The replay runs in its own compute pool with quotas, so it cannot starve live consumers.
    - Keeps: the shadow.
    - If it fails: the shadow is never read, and live consumers are unaffected.

19. **Verify.**
    - Starts: the shadow is complete.
    - Does: compares the replay's `event_id` set for D with the live set in the warehouse. Differences should be zero, unless a live key-value outage is recorded in the incident log. Enrichment column changes are expected, and a sample goes to an operator. Record counts per enricher version.
    - Keeps: the counts.
    - If it fails: an unexplained difference goes to the operator to investigate before any swap.

20. **Swap.**
    - Starts: the operator approves the build.
    - Does: replaces the `events_clean` partition for D with the shadow, in one atomic operation. The previous partition is kept until the operator confirms the new build, so rollback is possible.
    - Keeps: the previous partition, until confirmed.
    - If it fails: the atomic replace leaves the old partition in place. Rollback uses time travel if the warehouse has it. Otherwise the old partition is kept for a fixed period. See open questions.

21. **Audit.**
    - Starts: the swap is done.
    - Does: writes one row to `replay_runs`: day, enricher version, operator, counts, dedup diff, swap time and rollback handle. Live ingestion, live dedup state and the staging table are never touched.
    - Keeps: the `replay_runs` row.
    - If it fails: not specified. See open questions.

## What goes wrong

| Failure | What happens | Recovery |
|---|---|---|
| Key-value store down | Dedup pauses at its last committed offset. Nothing is lost or double-counted. Freshness alarm fires at 5 min. | On recovery, consumers resume in offset order, so winners match the dedup rule. The log's 14-day retention gives time to recover. |
| Log down or append fails | Collectors return 503. | Clients retry the same batch with the same `event_id`s. Duplicate appends are handled by dedup. |
| Client retry arrives more than W after the first copy | Counted as a new event, in live and replay alike. | Monitor the 7-day buffer assumption with the mobile team. W is configurable. A change to W is versioned and applied to live and replay together. |
| Archive lag | Alert at more than 1 day behind. | Page at 12 days behind. Replay and the 90-day rule both depend on the archive. |
| Finalize comparison differs | Swap is blocked. | A person reviews the alert. |
| Freshness sink fails or lags | Alert at 3 min. The 5-min budget is at risk. | The sink retries. The skip rule prevents double-counting. |

## Open questions

- **Bot traffic:** drop flagged rows, or keep them with `is_suspected_bot`. Product decides. Until then, the bot-traffic step is a no-op.
- **Enrichment failure:** the plan does not say what happens when a geo-IP lookup or user-agent parse fails. This applies to enrichment and to the bot-traffic step.
- **Staging appends:** the plan does not confirm that the warehouse accepts micro-batch appends into the open-day staging table. Warehouse owners to confirm. The plan does not rely on appends to a closed partition.
- **SDK buffer:** the 7-day on-device buffer must be confirmed as a hard maximum with the mobile SDK owners. It sets W = 8 days.
- **Failures after the partition swap:** the plan does not say what happens if the watermark update, the staging delete (in the day swap) or the audit row (in the replay) fails after the swap.
- **Rollback period:** if the warehouse has no time travel, the length of the fixed period for keeping old partitions is not set.
- **Quarantine:** whether rejected events need a quarantine store for debugging. Not required by the brief, and out of scope for now.