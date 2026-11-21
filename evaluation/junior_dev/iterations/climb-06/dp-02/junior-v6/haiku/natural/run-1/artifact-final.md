# Clickstream ingestion: plan

## Summary

No clickstream pipeline exists today. The company already has a replicated log, object storage with lifecycle rules, a key-value store with per-key expiry, and a warehouse that can replace one day partition in one atomic step. This plan builds the pipeline on those parts.

Clients (the website, iOS and Android apps) send batches of click and screen-view events to a new collector. The collector writes each accepted event to the log and returns 202 only after the log confirms the write. A dedup stage reads the log and labels each copy of an event as the **winner** (the first copy) or a **duplicate** (a later copy). Every labelled copy goes to an archive, unchanged, which keeps it for 90 days. Only winners are enriched and loaded into the warehouse table `events_clean`, which has one partition per UTC day.

Because the archive keeps every accepted copy, any closed day can be rebuilt. A replay reads one closed day from the archive, builds it in a staging table, checks it, and swaps it in with one atomic step. Live ingestion never waits for a replay, and dashboards never see a half-built day. The archive is the replay source because the log keeps only 14 days and is shared with live traffic.

## Terms

- **Event**: one click or screen view. It has a client-made `event_id` (a UUID), a `device_id` and a client timestamp.
- **Batch**: up to 100 events sent in one HTTPS request.
- **Collector**: the new service that receives batches.
- **Copy**: one accepted receipt of an event. A retry creates a new copy with the same `event_id`.
- **Receipt**: the moment the collector accepts one copy.
- **received_at**: the server time of a receipt. The collector stamps it once per copy, from its NTP-synchronised clock (a clock kept correct by network time sync).
- **Day D**: the UTC day of `received_at`. Partitions and replays use it. The client timestamp is never used.
- **Log**: the replicated append-only log. It keeps data for 14 days. It is split into partitions by a hash of `event_id`, so all copies of one event land in the same partition.
- **Ingest sequence**: a copy's position in the log, written as its partition number and offset. The log assigns it at append. It is only comparable within one partition.
- **Winner**: the first copy of an `event_id` in log order. The event's `received_at` and day are the winner's.
- **Duplicate**: any later copy of an `event_id`.
- **Decided topic**: a second log topic that holds every copy with its decision (winner or duplicate).
- **Enriched topic**: a log topic that holds enriched winners. The loader reads it.
- **Key-value store**: a store where each key can expire after a set time (its TTL). It holds one key per `event_id`. Only the dedup stage writes to it.
- **Archive**: object storage holding every accepted copy, duplicates included, unchanged. Each record has a sidecar (a small metadata file beside it).
- **events_clean**: the warehouse table. One partition per UTC day. Winners only, enriched.
- **events_late**: a warehouse table for winners that arrive after their day has closed. Keyed by received day.
- **Close**: 02:00 UTC on day D+1. After that time, day D is closed and nothing writes to its `events_clean` partition.
- **Enrichment manifest**: the record of the geo-IP and user-agent versions that enrichment uses.
- **Closed-day manifest**: the record the close job writes when day D passes its checks.
- **Replay request**: a request to rebuild one closed day. It names the day, a reason and the enrichment versions.
- **Replay lock**: a per-day lock. Only one replay of a day can run at a time.
- **Lag**: how far a consumer is behind the newest data in its input.
- **Canary**: a test event with a known `event_id`, sent every minute to measure latency.
- **Staging table**: `events_clean_rebuild_D`. A replay builds day D here. Dashboards cannot see it.
- **Replay manifest**: the record a replay writes when it finishes: the day, the versions, the row counts, the times, the operator and the reason.

## Live path

1. **Send.** A client sends a batch of up to 100 events over HTTPS to the collector. The body is capped at about 4 MB (100 events at 32 KB each, plus the envelope). On a timeout, 429 or 5xx, the client resends the same batch with the same `event_id`s, backing off from 1 second up to 5 minutes. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can arrive up to 7 days after the first copy.

2. **Validate.** The collector checks each event on its own. It rejects an event that has no `event_id`, no `device_id`, or is larger than 32 KB. The response lists each rejected event with its index and reason. Rejected events are not stored. The other events in the batch go on to step 4. Clients never retry rejected events.

3. **Empty batch.** If no event in the batch is valid, the collector still returns 202, listing only the rejections. Nothing is stored.

4. **Stamp.** The collector stamps `received_at` once per accepted copy. It does not check for duplicates. A resent batch gets the same 202 as the first send, so the client stops retrying.

5. **Append.** The collector appends each accepted event to the log. The payload is the original bytes, plus `received_at`, the batch id and the collector id. All copies of one event go to the same partition, so they stay in append order.

6. **Acknowledge.** The collector returns 202 only after the log confirms the write with replication (a quorum of replicas). This is what "accepted" means: the event is durably stored. If the append fails or times out, the collector returns 503 for the whole batch. A partial append is safe. The client's retry resends the same `event_id`s, and step 8 absorbs the duplicates.

7. **Retention.** The log keeps copies for 14 days. Until the archive has a copy, the log is the only durable record. Archive-sink lag must alarm well before 14 days. The threshold is a proposal to confirm.

8. **Dedup.** One consumer runs per log partition, so copies of one event are handled in order. For each copy:
   1. Run an atomic set-if-absent in the key-value store. The key is the `event_id`. The value is `{winner received_at, ingest sequence of this copy}`. The TTL is 8 days: the 7-day client retry window plus a 1-day margin.
   2. If the set succeeds, the decision is `winner`. If the key already exists and its stored ingest sequence is this copy's, the copy was read again after a crash or a lost reply, so the decision is `winner` again. Otherwise the decision is `duplicate`, referencing the stored winner.
   3. Write the copy and its decision to the decided topic. This topic is partitioned by `event_id` like the log, so per-event order holds.
   4. Commit the consumer offset only after the decided topic accepts the copy. A crash before that re-reads the copy, and the set-if-absent check gives the same decision.

   If the key-value store errors or times out, the consumer does not skip the copy and does not guess. It retries the same copy with backoff. It does not move on to later copies in that partition, so their order holds. A timeout after a successful set is safe: the retry finds this copy's ingest sequence and returns `winner`. If the store stays unavailable, the lag alarm fires.

9. **Duplicates.** Nothing is dropped from the archive or the decided topic. Duplicates are dropped from the warehouse path only: enrichment and the loader never receive them. Duplicates are never rejected at receipt.

10. **Archive.** The archive sink reads the decided topic, which holds every copy, under its own consumer group. It writes each copy to the folder of its own `received_at` day and hour: `raw/received_date=YYYY-MM-DD/hour=HH/`. A duplicate received on day D+1 goes in the D+1 folder, even when its winner is from day D. Each record holds the original event bytes unchanged, plus a sidecar with `received_at`, the ingest sequence, the collector id, the batch id, the decision and the winner reference. Each file is written completely, then committed atomically (a temp name then a rename, or a multipart commit), so readers never see a partial file. A crash can re-deliver a copy, so the sink commits each copy once, keyed by its ingest sequence. The archive therefore holds each copy once.

11. **Expiry.** A lifecycle rule expires each archive object 90 days after its received day. The rule has a margin, so every accepted event is kept for at least 90 days.

12. **Enrich winners.** Enrichment reads winners from the decided topic. It applies the geo-IP lookup and user-agent parsing, pinned to the versions in the enrichment manifest. If enrichment fails for an event, the event is still written, with the enrichment fields null and `enrichment_status` set. It is never dropped. Nothing replays it automatically: an operator decides when to replay a day. Enriched winners go to the enriched topic.

13. **Load.** The loader runs about every minute. It reads enriched winners and appends each one to the `events_clean` partition for the winner's day. It is an append, not a replace. It commits its offset only after the append succeeds. If the loader is down or slow, the topics keep the rows for up to 14 days, and a lag alarm fires.

14. **Late winners.** Just before it appends a winner, the loader reads the NTP-synchronised clock of its host, the same kind of clock the collector uses. It decides once per winner. If day D is already closed (the clock is at or past 02:00 UTC on D+1), the winner goes to `events_late`, keyed by its received day. It never goes into a closed partition. A winner the loader checks before 02:00 goes to `events_clean`, even if the append lands a moment later. The close check waits for those appends (step 15). Dashboards read `events_clean` only, so a late winner is not visible until day D is replayed.

15. **Close check.** At 02:00 UTC on D+1 the close job starts. It waits until both of these are true:
    - the archive sink has committed every hour folder for D, with no lag on copies received before close; and
    - the loader has no lag on winners received before close.

    Then it counts the winners for D in the archive. It checks that the count equals the rows for D in `events_clean` plus the rows for D in `events_late`. Each winner is in exactly one of those two tables, so none is counted twice.
    - If the check passes, the close job writes the closed-day manifest. If `events_late` has rows for D, it records a replay request for D, filled in as described in step 17. It does not start a replay.
    - If the check fails, it writes no manifest, alerts the operator and retries until the check passes. It does not guess which side is right. The retry deadline is not yet set.

    The count check always runs before any replay of D, because a replay can start only after the closed-day manifest exists.

16. **Latency.** A receipt must be queryable within 5 minutes at the 99th percentile, measured from the collector's receipt. Alert at 3 minutes p99 to leave margin. Canary events with known `event_id`s, injected every minute, measure this.

## Replay path (one closed day D)

17. **Request.** An operator asks to replay day D, giving a reason and the enrichment versions to use. The close job can also record a request for D when `events_late` has rows (step 15). It fills in the reason ("late winners in events_late") and the versions from the current enrichment manifest. The operator confirms or changes them. Nothing starts a replay on its own. When the operator confirms, the job refuses the request and changes nothing if any of these hold. The same checks apply to close-job requests, because they guard the data, not who asked:
    - day D has no closed-day manifest;
    - another replay of D is running (the replay lock is held); or
    - the archive for D would expire before the replay can finish. The archive for D expires at D+90.

18. **Inputs.** The replay reads the archive files for received day D, including duplicates and their recorded decisions. This input is read-only. The replay does not read the log, which is shared with live traffic and kept only 14 days. It does not read `events_late`, because those winners are already in the archive. Reading both would count the same winner twice. The replay never writes to the key-value store.

19. **Compute.** The replay runs on a compute pool separate from the live consumers, with resource caps. Live lag does not change.

20. **Select winners.** The replay keeps records with decision `winner` and received day D. It sorts them by ingest sequence, that is, by partition and then offset. The sort gives the same row order on every run. The sort does not decide which rows are winners. If any `event_id` appears more than once among them, the replay fails. It does not pick one silently.

21. **Enrich.** The replay enriches the winners with the requested versions and writes them to `events_clean_rebuild_D`. Dashboards cannot see this table. Every row records `enrichment_version`.

22. **Validate staging.** Every check must pass:
    1. The row count equals the winner count from step 20.
    2. No `event_id` appears twice.
    3. The schema matches `events_clean`.
    4. For unchanged versions, the row hash equals the live partition's hash. Rows are compared as a set, ignoring row order, because the live partition was built by appends in a different order. This is the regression check.
    5. For changed versions, a sample of rows differs only in the enrichment fields.

23. **Swap.** The replay atomically replaces partition D of `events_clean` with the staging rows, using the warehouse's single-partition replace. Dashboards see either the old day or the new day, never a mix. If validation or the swap fails, the live partition is untouched and the failure is reported.

24. **Clean up.** The replay drops the staging table and writes a replay manifest entry: the day, the versions, the row counts, the times, the operator and the reason. It changes no key-value state, no log state and no live consumer state. It leaves the `events_late` rows for D in place, because they record what arrived late. After a replay, a late winner is in both `events_clean` and `events_late`, so never add the two tables together. The close check is not run again after a replay.

## What happens when things fail

| Where | What goes wrong | What happens | Data kept |
|---|---|---|---|
| Client | Timeout, 429 or 5xx | Resends the same batch and `event_id`s, backing off from 1 s to 5 min | Client buffer, up to 7 days |
| Collector | Event invalid | Rejected and listed. The rest of the batch is accepted | Nothing stored for the rejected event |
| Collector | Log append fails or times out | 503 for the whole batch. Client retries | Whatever the log holds. Dedup absorbs duplicates |
| Dedup | Key-value store errors, times out or is down | Retries the same copy with backoff. Later copies in the partition wait. Lag alarm fires | Log holds the copy |
| Dedup | Crash after the key is set, before the commit | The copy is re-read and gets `winner` again | Key-value value holds the ingest sequence |
| Archive sink | Falls behind | Archive-sink lag alarm, well before 14 days | Log holds the copies |
| Enrichment | Fails for one event | Written with null enrichment fields and `enrichment_status` set. No automatic replay | Archive holds the raw bytes |
| Loader | Down or slow | Topics hold rows for up to 14 days. Lag alarm fires | Loader offset is not committed |
| Loader | Winner arrives after close | Written to `events_late` | Archive holds the winner |
| Close job | Archive or loader incomplete, or counts differ | No manifest. Operator alerted. Retries until the check passes | Archive |
| Close job | Check passes and `events_late` has rows for D | Records a replay request for the operator. Nothing replays until the operator confirms | `events_late` rows |
| Replay | Request refused | Nothing changes | Nothing |
| Replay | Duplicate `event_id` among winners | Replay fails. Nothing is swapped | Live partition |
| Replay | Validation or swap fails | Live partition untouched. Failure reported | Live partition |

## How we verify it

These checks show the system works. They are not part of how it runs.

- **Duplicate.** Resend a batch. It returns 202 both times. `events_clean` has one row. The archive has two records, one `winner` and one `duplicate`.
- **Retry at 7 days.** A copy resent 7 days after the winner is archived as a duplicate and is not loaded.
- **Day assignment.** A client timestamp on D-1 with receipt on D lands in partition D.
- **Crash.** Kill the collector after the log ack and before the response. The client's retry yields one winner.
- **Replay equivalence.** Replay an unchanged closed day. The row hash matches the live partition.
- **Atomic swap.** Queries during a swap see either the full old day or the full new day.
- **Isolation.** During a replay under load, key-value state is unchanged (compare a digest before and after), and live lag does not rise.
- **Latency.** Canary events meet the 5-minute p99 target.

## Open questions

1. **Suspected bot traffic: drop or keep with a flag.** Not decided. This plan does not choose. The archive keeps all accepted events for 90 days under either option. The choice affects only `events_clean` and whether a bot-flag column exists. The plan reserves an enrichment step for it, with no default behaviour.
2. **Rejected events.** The brief does not say whether their payloads are kept. Proposed default, to confirm: keep only counts and reasons, not payloads.
3. **Changes to dedup logic.** Live dedup decisions are recorded and reused by replay, so a fix to dedup logic cannot be replayed from the archive alone. Supporting it needs a recompute with a 7-day archive lookback, which must finish before the archive expires. Not decided.
4. **Client retry guarantee.** The 8-day TTL depends on the SDK holding events for at most 7 days. If a client can resend later, a late duplicate after the TTL expires becomes a new winner. That winner can fall on a different day from the first winner, so one event could have a winner on two days. Either the SDK must guarantee the limit, or the TTL must change.
5. **Sizing.** The brief gives no volumes. Key-value capacity is peak receipts per second times 8 days times per-key size. Archive and warehouse costs need the same inputs.
6. **Loader restart.** After a crash the loader may re-append its last batch. No design yet makes the append idempotent. A duplicate row would make the close check fail, so the operator is alerted.
7. **Close retry deadline.** How long the close job retries before it escalates is not set.
8. **Staging after a failed replay.** What happens to `events_clean_rebuild_D` after a failed validation or swap is not set.
9. **Archive-lag alarm threshold.** The threshold is a proposal, to confirm.