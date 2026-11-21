# Clickstream ingestion: plan for `events_clean`

## Goal and constraints

Land click and screen-view events from web, iOS and Android in `events_clean`, deduplicated and enriched, partitioned by UTC day of `received_at`. Live events must be queryable within 5 minutes of reaching us. Operators can rebuild one closed UTC day without slowing live ingestion or changing live dedup state, and dashboards never see a half-rebuilt day.

## Assumptions to confirm

- The warehouse supports micro-batch inserts into the current day's partition (live path) and atomic replacement of one day partition (replay). If inserts are not supported, live writes go to a staging table that the warehouse exposes to `events_clean` as one view.
- The log exposes per-partition offsets and consumer lag, and it supports full-replication acknowledgement.
- Object storage lifecycle rules delete an object 90 days after its creation. Raw objects are created at receipt time, so object age equals receipt age.
- Collector nodes use NTP, so clock skew is seconds, not minutes.
- The brief gives no status for a batch that is wholly malformed or not valid JSON. This plan assumes 400 for an unparseable body or a batch over 100 events, and 202 with a per-event rejection list for any parseable batch.

## Part A: Live path

1. **Client send.** The SDK sends batches of up to 100 events over HTTPS. On a timeout, 429 or 5xx, it resends the same batch with the same `event_id`s, backing off from 1 s to a 5-minute cap. Rejected events are never resent. The mobile SDK holds unacknowledged events for up to 7 days.

2. **Validate per event.** The collector checks each event independently. It requires a UUID `event_id` and a `device_id`, and it rejects any event whose serialized size exceeds 32 KB. Each rejection records the batch index and a reason. Valid events continue through the batch.

3. **Stamp `received_at`.** The collector records server UTC time at receipt. It keeps the client payload byte-for-byte as received, and it stores `received_at` and the collector node ID in an envelope beside the payload. The client timestamp is kept as a field only. It never sets the partition or replay membership.

4. **Commit before 202.** The collector appends the accepted events to the replicated log and waits for acknowledgement from all in-sync replicas. That acknowledgement is the durability point. Only after it returns does the collector send 202 with the rejection list. If the append fails for any part of the batch, the collector returns 503 for the whole batch, and the client retries with the same IDs. Duplicates created by a partial append are handled by dedup in step 6.

5. **Raw archive.** A consumer group reads the log and writes every accepted event, duplicates included, into object storage under `raw/received_day=YYYY-MM-DD/`. Each flush is an immutable file. A lifecycle rule deletes objects 90 days after creation. The archive consumer records its watermark. Log retention is 14 days, so alert when this consumer's lag exceeds one hour.

6. **Dedup and enrich (live consumer).** A second consumer group reads the log, partitioned by a hash of `event_id`, so every copy of an event reaches the same consumer. For each event:
   1. Run an atomic set-if-absent on the key-value store with key `event_id` and TTL 8 days. The value holds `received_at`, the partition day, and the ID of the micro-batch claiming it. Later copies must not refresh the TTL.
   2. If the set succeeds, the event is the first copy. Enrich it with geo-IP and user-agent data, and stamp `enrichment_version` on the row.
   3. If the key exists with a different batch ID, drop the event from the clean path. It remains in raw.
   4. If the key exists with the same batch ID, the consumer is re-running its own uncommitted batch after a restart. Keep the event.
   5. If the key-value store is unavailable, pause this consumer. Do not write unchecked rows, because that would create duplicates. Lag grows, and the 14-day log retention covers the outage.

7. **Bot traffic (open).** Product has not decided whether suspected bot traffic is dropped or kept with a flag. This plan does not choose. Step 6.2 is the single decision point, between enrichment and the warehouse write. The raw archive keeps every copy, so a later decision can be applied to any day still inside the 90-day window by replay (Part B).

8. **Micro-batch load.** About every 60 seconds, the live consumer inserts its accumulated rows into `events_clean`, into the partition of each row's `received_at` day. Live writes only target the current open day. Each micro-batch commits as one transaction with an idempotency key made from the consumer group and offset range, so a retried load cannot insert twice.

9. **Latency budget.** The 5-minute target is measured from our receipt, not from the client's send time. The budget is: collector and log commit under 1 s, consumer and enrichment under 1 min, warehouse load under 2 min at p99. Alert when the oldest uncommitted record is more than 3 minutes old.

10. **Monitoring.** Track rows accepted per collector, rows rejected by reason, duplicates dropped, dedup key-store errors, consumer lag for both consumer groups, and rows loaded per micro-batch. Reconcile accepted counts against raw archive counts once per hour.

## Part B: Replay one closed day

Day D closes at 02:00 UTC on D+1. A replay rebuilds partition D of `events_clean`. The plan's first-copy rule is: for each `event_id`, the copy with the earliest `received_at` (ties broken by collector node ID and batch sequence) wins. The partition an event belongs to is the day its winning copy was received.

11. **Admission.** The operator submits a day D, a reason, and a target enrichment version. The replay runner refuses the request unless now is at or after D+1 02:00 UTC. It also refuses once raw day D-7 is close to expiry, which happens about D+83. The plan refuses from D+80 to leave margin. Only one replay per day runs at a time, enforced by a lock. The live path never takes this lock.

12. **Watermark check.** The 02:00 close is what makes this check sound. Any record stamped on D is appended to the log well before 02:00 on D+1. The runner confirms that both the live consumer and the archive consumer have processed every log record appended before 02:00 UTC on D+1. The runner checks consumer offsets and does not rely on the clock alone. If either consumer is behind, the runner waits and retries.

13. **Read candidates from raw.** The runner reads all raw copies in partitions D-7 through D, duplicates included. Every event with a copy in D has its first copy no earlier than D-7, because retries occur within 7 days of the first copy. For each `event_id`, the runner selects the earliest copy. It keeps only the winners whose winning copy was received on D. This is the same rule as live, computed statelessly. The runner does not read or write the key-value store and does not read the log.

14. **Enrich.** The runner applies the target enrichment version to each winner, using the same bot-traffic decision as the live path at that time (see step 7).

15. **Stage.** The runner writes the rebuilt rows to a staging table tagged with the replay run ID. `events_clean` is not touched in this step.

16. **Validate before swap.** The runner checks that:
    - The staged row count equals the number of winners from step 13.
    - No `event_id` appears twice.
    - Every row's partition day is D.
    - The `enrichment_version` column holds only the target version.
    - Differences from the live partition D are limited to enrichment columns and to the boundary-race rows described in the risks.

    If any check fails, the runner discards the staging table. The live partition stays as it is.

17. **Atomic swap.** In one warehouse transaction, the runner replaces partition D of `events_clean` with the staged rows. Dashboards read either the old partition or the new one, never a mix. Once D is closed, live writers never write to it. A row for a closed day that arrives anyway goes to a quarantine table and raises an alert.

18. **Record and release.** The runner logs the run ID, day, enrichment version, raw copy counts, winner counts, row counts, operator and duration. It drops the staging table and releases the lock.

19. **Isolation.** Replay reads only the raw archive. It never touches the log, the key-value store, or live consumers. It runs on its own warehouse compute with a resource quota, so it cannot slow the live loads.

## Requirements cross-check

| Requirement | Where it is met |
|---|---|
| Queryable within 5 minutes | Steps 6, 8, 9 |
| Partition by UTC day of `received_at` | Steps 3, 8 |
| 202 only after durable storage | Step 4 |
| Malformed events rejected individually and listed | Step 2 |
| Retries with same IDs, up to 7 days | Steps 1, 6 (TTL 8 days) |
| First copy wins, dedup by `event_id` alone | Steps 6, 13 |
| Duplicates and accepted events kept 90 days | Step 5 |
| Replay only for closed days | Step 11 |
| Replay does not slow live or change dedup state | Steps 13, 19 |
| No half-rebuilt day visible | Step 17 |

## Open decisions

- **Bot traffic:** drop, or keep with a flag. Owner: product. Decision point: step 7. Undecided, and the plan does not assume either option.
- **Status for an all-rejected batch:** this plan returns 202 with the list. Confirm with the client team.
- **Archiving rejected events:** the brief does not require it. Decide whether to keep them for debugging, which would need its own retention.

## Risks and checks

- **Winner ordering across collectors.** Live dedup follows log order, but the rule is "earliest received_at". Two copies of one event received within a second of each other, especially across midnight, can be decided differently live and in replay. Replay is authoritative for closed days, so it corrects this. The step 16 comparison counts these rows, so the rate can be measured.
- **Dedup window anchor.** The brief says a retry can arrive up to 7 days after the first copy. The TTL assumes "first copy" means the first copy we receive. Confirm with the mobile team that the 7-day buffer is not measured from the client event time, which could run longer if a device was offline before its first send.
- **Replay window.** Replay of D needs raw data for D-7 through D, and raw data expires at 90 days. Replay becomes impossible for any day after about D+83. Track this in the replay admission check.
- **Key-value store loss.** If the store loses keys, live dedup breaks for the affected window. Closed days are repaired by replay, but the open day is not. Alert on store errors and document a recovery procedure.
- **Clock skew.** Partition membership depends on collector clocks. Skew of a few seconds can move events across midnight. The watermark in step 12 covers this, but NTP health should be monitored.
- **Warehouse semantics.** Confirm that inserts into the current day and atomic partition replacement can share one table, and that a partition replacement is a single transaction visible atomically to readers.