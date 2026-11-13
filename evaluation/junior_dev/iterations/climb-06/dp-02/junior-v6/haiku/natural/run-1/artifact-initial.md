# Clickstream ingestion: plan

## Definitions

- **Receipt**: the collector accepts one copy of an event. `received_at` is stamped at receipt, once per copy.
- **Winner**: the first accepted copy of an `event_id`, in log append order. The event's `received_at` and UTC day are the winner's.
- **Day D**: the UTC day of `received_at`. Live writes to D stop at 02:00 UTC on D+1 (the close). After close, D is closed.
- **Archive**: object storage holding every accepted copy, duplicates included, exactly as received, with a metadata sidecar.
- **events_clean**: warehouse table, one partition per UTC day, winners only, enriched.

## Live path

1. The client SDK sends a batch of up to 100 events over HTTPS. Cap the request body at about 4 MB (100 events at 32 KB each, plus envelope).
2. The collector validates each event on its own. An event missing `event_id` or `device_id`, or larger than 32 KB, is rejected and listed in the response with its index and reason. Rejected events are not stored. The other events continue.
3. A batch with no valid events still returns 202, listing only rejections, because there is nothing to store.
4. The collector stamps `received_at` from its NTP-synchronised clock, once per accepted copy. It does not check for duplicates. A resent batch gets the same 202 success as the first send, so clients stop retrying.
5. The collector appends each accepted event to the replicated log. The payload is the original bytes as received, with `received_at`, batch id and collector id attached. The log is partitioned by a hash of `event_id`, so all copies of one event share a partition and are ordered by append.
6. The collector returns 202 only after the log acknowledges the write with replication (a quorum of replicas). If the append fails or times out, the collector returns 503 for the whole batch. A partial append is safe because the client's retry resends the same `event_id`s and step 9 absorbs the duplicates.
7. The log keeps 14 days. Until step 10 has archived a copy, the log holds the only durable record of it. Alarm on archive-sink lag well before 14 days (the threshold is a proposal to confirm).
8. Dedup stage. One consumer per log partition keeps per-event order. For each accepted copy:
   1. Run an atomic set-if-absent in the key-value store, with key `event_id`, value `{winner received_at, ingest sequence}`, and TTL 8 days. The 8 days is the 7-day client retry window plus a 1-day margin.
   2. If the set succeeds, the decision is `winner`. If the key already exists, the decision is `duplicate`, referencing the stored winner.
   3. Attach the decision to the copy and pass it on. Only this stage writes to the key-value store.
9. Duplicates are dropped here and nowhere else. Copies are never rejected for being duplicates.
10. Archive sink. Consume every decided copy, winners and duplicates, and write it to object storage at `raw/received_date=YYYY-MM-DD/hour=HH/`. Each record holds the original event bytes unchanged, plus a sidecar with `received_at`, ingest sequence, collector id, batch id, decision and winner reference. Write each file completely and commit it atomically (temp name then rename, or a multipart commit), so readers never see a partial file.
11. Lifecycle rule: expire archive objects 90 days after their received day, using a margin so that every accepted event is kept for at least 90 days.
12. Enrichment, winners only. Apply the geo-IP lookup and user-agent parsing, pinned to versions recorded in an enrichment manifest. If enrichment fails for an event, still write it, with enrichment fields null and `enrichment_status` set. Do not drop it. A replay can fill it in later.
13. Loader. Every minute or so, append enriched winners into the events_clean partition for the winner's received day. This is an append, not a replace.
14. Writes that reach the loader after day D is closed go to a table `events_late`, keyed by received day. They never enter the closed partition.
15. Close job at 02:00 UTC on D+1. Check that the archive for D is complete, and that the count of winners for D in the archive equals the rows for D in `events_clean` plus `events_late`. Write a closed-day manifest. If `events_late` has rows for D, schedule a replay of D (steps 16 to 24).
16. Latency target. A receipt is queryable within 5 minutes at the 99th percentile, measured from collector receipt. Alert at 3 minutes p99 to leave margin. Measure it with canary events that carry known `event_id`s, injected every minute.

## Replay path (one closed day D)

17. Operator requests a replay of D with a reason and the enrichment versions to use. The job refuses if D is not closed, if another replay of D is running (per-day lock), or if the archive for D would expire before the replay can finish (archive for D expires at D+90).
18. Inputs are read-only: the archive files for received day D (including duplicates and their recorded decisions) and `events_late` rows for D. The replay never reads the log, which is shared with live traffic and kept for only 14 days. It never writes to the key-value store.
19. Run on a compute pool separate from the live consumers, with resource caps, so live lag does not change.
20. Select winners: records with decision `winner` and received day D. Sort by ingest sequence. Fail the replay if any `event_id` appears more than once, rather than picking one silently.
21. Enrich the winners with the requested versions. Write them to a staging table, `events_clean_rebuild_D`, which dashboards cannot see. Record `enrichment_version` on every row.
22. Validate staging:
    1. The row count equals the winner count from step 20.
    2. No `event_id` appears twice.
    3. The schema matches events_clean.
    4. For a replay with unchanged versions, the row hash equals the live partition, which is the regression check.
    5. For changed versions, a sample of rows differs only in the enrichment fields.
23. Atomically replace partition D of events_clean with the staging rows, using the warehouse's single-partition replace. Dashboards see the old day or the new day, never a mix. If validation or the swap fails, the live partition is untouched. Report the failure.
24. Drop staging. Write a replay manifest entry: day, versions, row counts, times, operator and reason. The replay changes no key-value state, no log state and no live consumer state.

## Open decisions

1. **Suspected bot traffic: drop or keep with a flag. Not decided; do not choose.** The archive keeps all accepted events for 90 days under either option, because the requirement covers accepted events. The choice only affects events_clean and whether a bot-flag column exists. The plan reserves an enrichment step for it, with no default behaviour.
2. **Rejected events.** The brief does not say whether their payloads should be kept. Proposed default, to confirm: keep only counts and reasons, not payloads.
3. **Changes to dedup logic.** Dedup decisions are recorded at live time and reused by replay, so a fix to dedup logic cannot be replayed from the archive alone. Supporting it needs a recompute with a 7-day archive lookback, which must finish before the archive expires. Not decided.
4. **Client retry guarantee.** The 8-day TTL depends on the SDK really holding events for at most 7 days. If a client can resend later, a late duplicate after TTL expiry becomes a new winner. Either the SDK must guarantee the limit or the TTL must change.
5. **Sizing.** The brief gives no volumes. Key-value capacity is peak receipts per second × 8 days × per-key size. Archive and warehouse costs need the same inputs.

## Verification

- Duplicate: resend a batch. It returns 202 both times. events_clean has one row, and the archive has two records, one `winner` and one `duplicate`.
- Retry at 7 days: a copy resent 7 days after the winner is archived as a duplicate and not loaded.
- Day assignment: a client timestamp on D-1 with receipt on D lands in partition D.
- Crash: kill the collector after the log ack and before the response. The client's retry yields one winner.
- Replay equivalence: replay an unchanged closed day. The row hash matches the live partition.
- Atomic swap: queries during a swap see either the full old day or the full new day.
- Isolation: during a replay under load, key-value state is unchanged (compare a digest before and after) and live lag does not rise.
- Latency: canary events meet the 5-minute p99 target.