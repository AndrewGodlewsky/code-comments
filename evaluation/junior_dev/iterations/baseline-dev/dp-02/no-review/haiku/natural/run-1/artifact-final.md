# Clickstream ingestion: plan

## 1. Goal and invariants

Accept click and screen-view events from the website and the iOS and Android apps, deduplicate them, enrich them, and land them in `events_clean`, a warehouse table with one partition per UTC day. Live events are queryable within 5 minutes of reaching the collector. Replay rebuilds one closed UTC day without touching live ingestion or live dedup state.

Invariants the design must keep:

- **I1 Day assignment.** An event belongs to the UTC day of its collector-stamped `received_at`. Client timestamps are stored but never used for partitioning or replay.
- **I2 Durable before 202.** The collector returns 202 only after every accepted event in the batch is acknowledged by the replicated intake log.
- **I3 Archive.** Every accepted event, duplicates included, is kept byte-for-byte as received for 90 days.
- **I4 Dedup.** Identity is `event_id` alone. The first copy claimed by the pipeline wins. Later copies are excluded from `events_clean` but remain in the archive.
- **I5 Replay isolation.** Replay reads only the archive and the per-day winners manifest. It never reads or writes the dedup claim store, never consumes the intake log, and never blocks live loads.
- **I6 No half-rebuilt days.** Dashboards read `events_clean` only. A rebuilt day becomes visible through one atomic partition replace.

## 2. Components

| Component | Source | Role |
|---|---|---|
| Collector | New service | HTTPS intake, per-event validation, `received_at` stamping, log append, 202 response |
| Intake log | Existing, replicated, 14-day retention | Durable buffer between collector and consumers. It is not the archive. |
| Archive sink | New consumer | Writes accepted events exactly as received to object storage by `received_at` day |
| Dedup claim store | Existing key-value store, per-key TTL | `event_id` claim with 8-day TTL, set-if-absent |
| Live clean consumer | New consumer | Claims, enriches, and loads winners for live days |
| Winners manifest | Object storage, one set per day | Durable list of which archived events won dedup for each day. Replay's source of truth for dedup. |
| `events_clean` | Existing warehouse | Final table, partitioned by UTC day |
| Replay runner | New batch job, separate worker pool | Rebuilds one closed day into staging, validates, and swaps it in |

## 3. Live path

1. **Client batch.** The client sends up to 100 events over HTTPS. Each event keeps its original `event_id`, `device_id`, and client timestamp. Retries reuse the same `event_id` values.
2. **Request checks.** The collector authenticates the request and enforces a body-size limit. It records a request start time in UTC. The brief does not define authentication, so this step is open (see section 8).
3. **Per-event validation.** For each event, the collector keeps the original JSON bytes exactly as received, without re-serialising them. It then checks three things: `event_id` is present, `device_id` is present, and the event is at most 32 KB. Each failure is rejected individually and listed in the response with its batch index, `event_id` if present, and reason. Rejected events are not stored and are not part of the 90-day obligation.
4. **Stamp.** Each accepted event gets `received_at` (UTC server time, taken at request start) and a server-generated `batch_id`. The batch's other accepted events share the same `batch_id`, and each keeps its index.
5. **Append.** The collector appends one log record per accepted event, keyed by `event_id`. The record holds the original event bytes plus the envelope fields from step 4 and the client IP needed for geo-IP enrichment. Appends use `acks=all` and a hard deadline of 60 seconds.
6. **Respond.** Only after every accepted event's append is acknowledged does the collector return 202 with the rejected list. If any append fails or times out, the whole batch gets a 5xx. Clients then retry the same batch, and dedup absorbs any copies already appended.
7. **Archive sink.** The sink reads the log in its own consumer group and writes accepted events to object storage in files partitioned by `received_at` UTC day. It advances its offset only after the object is durable. It also publishes a per-day accepted count so the seal step can reconcile.
8. **Dedup claim.** The live clean consumer, in its own consumer group, processes each record as follows:
   a. It runs set-if-absent on the claim store with key `event_id`, value `{log partition, offset, received_at day}`, and TTL 8 days.
   b. If the claim is created, the event is the winner.
   c. If a claim already exists and it equals this record's `{partition, offset}`, the record is a redelivery of the same winner, so it is treated as the winner again.
   d. Any other existing claim makes the record a duplicate. Duplicates are skipped.
9. **Enrich winners.** Winners get geo-IP and user-agent enrichment using the current enrichment version, which is written to each row as `enrichment_version`. The row's partition key is its `received_at` day.
10. **Flush every about 60 seconds.** For each day in the micro-batch:
    a. Append `(event_id, log partition, offset, archive object ref)` for each winner to that day's winners manifest. Duplicate entries are tolerated and deduplicated by `event_id` at replay time.
    b. Load the winners into `events_clean`'s partition for that day. The load is keyed by the micro-batch id, so a retried load cannot double-count.
    c. Commit consumer offsets only after (a) and (b) succeed.
11. **Freshness.** The target is p99 under 5 minutes from `received_at` to warehouse visibility. Track it per micro-batch. Alert at 3 minutes so there is time to act before the budget is missed.
12. **Duplicates.** A duplicate is never loaded into `events_clean`. It stays in the archive from step 7, and its count appears in the reconciliation for that day.
13. **Claim store sizing.** Claims are roughly accepted events per day times 8 days. Check the store's capacity against that figure before launch.

## 4. Day close and seal

A UTC day D is closed at 02:00 UTC on D+1. Closed days are the only days eligible for replay. Sealing happens after close.

1. At 02:05 UTC on D+1, the seal job records the end offset of every intake-log partition. The 60-second append deadline has passed for every request stamped with a D `received_at`, so no new D-stamped records can appear after this point. The 2-hour gap between day end and close is a safety margin.
2. The seal job waits until the archive sink and the live clean consumer have committed past the recorded offsets, and until every live micro-batch for D has finished loading.
3. The seal job writes the final archive manifest for D, which lists objects, counts, and checksums. It also writes the final winners manifest for D.
4. Reconciliation must hold, or the day stays unsealed and an alert fires:
   - archive count for D equals the collector's accepted count for D;
   - winners count for D (unique `event_id` in the winners manifest) equals the row count of `events_clean` partition D;
   - accepted count equals winners plus duplicates.
5. The seal job marks D sealed. Any D-stamped record found after sealing goes to a quarantine location and raises an alert. It is never silently added to a sealed day. Clock skew between collectors is assumed to stay well under the 1-minute margin, and this must be checked.

## 5. Replay path

Replay rebuilds a day's enrichment columns. It does not change which events are in the day.

1. **Request.** An operator asks to replay day D with a target enrichment version V.
2. **Pre-checks.** The controller refuses the request unless all of these hold:
   - now is at or after 02:00 UTC on D+1;
   - D is sealed;
   - D is within 90 days of `received_at`, so its archive still exists;
   - no other replay of D is running.
3. **Inputs.** The runner reads the final winners manifest for D, deduplicates it by `event_id`, and fails if any `event_id` maps to two different archive refs. It then reads only those winning events from the archive for D.
4. **Isolation.** The runner never reads the claim store, never reads or commits intake-log consumer offsets, and never writes claims. It runs on a separate worker pool and a separate warehouse resource group with a concurrency cap. Live loads are unaffected.
5. **Build.** The runner enriches each winner with version V and writes the rows to a staging table, `events_clean_rebuild_D`. Dashboards cannot see staging.
6. **Validate.** Before any swap, the runner checks:
   - the row count equals the deduplicated winners count;
   - `event_id` is unique in staging;
   - the `event_id` set equals the manifest's set exactly;
   - non-enrichment columns match the live partition for D;
   - the required fields are not null;
   - `enrichment_version` is V on every row.
   It also produces a diff report giving the number of changed rows per enrichment column.
7. **Approval.** The operator reviews the diff report and approves the swap. Approval is a separate step from the build.
8. **Swap.** The runner atomically replaces partition D in `events_clean` with the contents of staging. Dashboards see either the old version or the new one, never a mix.
9. **Record.** The runner writes an audit row with the replay id, day, enrichment version, operator, counts, and timestamps. It drops staging. If the warehouse supports time travel, the previous partition is kept for a rollback window.
10. **Failure.** If any step fails, staging is discarded. Partition D is never modified until the atomic swap.
11. **Limit.** Replay can only reach days whose archive still exists. Since the archive is kept 90 days, that is the replay window.
12. **Scope.** A replay corrects enrichment only. It cannot correct a dedup decision, because winners are fixed by the manifest. A dedup bug needs a separate, explicit procedure. That procedure is out of scope here.

Why a manifest and not the claim store: claims expire after 8 days and are overwritten by nothing, but replay of days up to 90 days old must still know who won. The manifest is written once per day at live time, so it survives the claim TTL, and reading it keeps replay away from live state.

## 6. Retention

- **Archive objects:** delete 90 days after write, using the object-storage lifecycle rule. Objects are written after `received_at`, so every event is kept at least 90 days from receipt. Compaction must keep content unchanged.
- **Winners manifests and archive manifests:** keep for at least as long as the archive they describe.
- **Intake log:** 14 days. This is a buffer only. Consumer lag must alarm well before that limit.
- **Claim store:** 8-day TTL per key. The margin over the 7-day retry window covers scheduling delay and clock skew.
- **`events_clean`:** the brief does not set a retention period. Left open (section 8).

## 7. Checks before launch

- Duplicate across midnight: first copy with `received_at` on D, retry with `received_at` on D+1. The retry is dropped, and the row stays in day D.
- Retry at about 7 days after the first copy, with TTL 8 days. The duplicate is still caught.
- Partial batch with one missing `device_id` and one oversized event. The valid events get 202, and the response lists both rejections.
- Crash between claim and load. On redelivery, the record is treated as the same winner and loaded once.
- Two collectors receive the same `event_id` concurrently. Exactly one claim succeeds.
- Replay of D during live ingestion of D+1. Live latency and throughput are unchanged.
- Replay of an open day is refused.
- Dashboard queries during swap show no partial day.
- Replay output equals live output except for enrichment columns.
- Reconciliation holds every day: accepted equals archive equals winners plus duplicates, and winners equal `events_clean` rows.

## 8. Open decisions and assumptions

**Open: suspected bot traffic.** Product has not decided whether it should be dropped or kept with a flag. This plan does not choose. The archive keeps every accepted event either way. So the decision can be applied at enrichment time and during replay without re-collecting data. The choice still needs an owner, detection criteria, and a decision on whether bot-flagged events take part in dedup claims.

**Other items the brief does not settle:**
- Client authentication and rate limits for the collector.
- Whether a non-UUID `event_id` is rejected. The brief lists only three rejection reasons, so a non-UUID value would currently be deduplicated as a raw string.
- The response for a batch that is not valid JSON or has more than 100 events.
- Whether rejected events' metadata, without payloads, is logged for monitoring.
- Retention of the client IP kept in the archive for geo-IP enrichment, and the privacy implications.
- Retention period for `events_clean`.

**Assumptions to verify:**
- The warehouse accepts idempotent loads into an open day's partition while it is still live. If it does not, use a live tail table with the same schema, and expose `events_clean` together with the tail through a view. The swap step at close would then be a replace of partition D from the tail.
- The log's maximum message size is at least 3.2 MB (100 events at 32 KB each), or each event is sent as its own message.
- Collector clocks are kept in sync closely enough that the seal margin holds.
- Claim store capacity is sufficient for 8 days of accepted events.