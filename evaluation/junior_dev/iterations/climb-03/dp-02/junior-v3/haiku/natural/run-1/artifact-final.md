# Clickstream ingestion plan: `events_clean`

## What this is and how it works

Website and app events go to a collector. The collector stamps each event with server time, checks it, and writes it to a durable Kafka topic. An archive consumer keeps every accepted event, duplicates included, for 90 days. A live consumer drops duplicates, enriches the first copy of each event, and writes it to `events_clean`, which has one partition per UTC day. To rebuild a closed day, a replay reads only the archive and swaps that day's partition in one step.

## Terms

- **Event day D**: the UTC date of `received_at`, which the collector sets when the request arrives. D picks the partition and decides which replay covers the event. Client timestamps are never used for this.
- **Envelope**: a record the collector writes around each event's original JSON bytes. It holds `received_at`, `batch_id` (new for each request), `position` (the event's index in the batch) and the bytes. The bytes are never edited.
- **Claim**: a key-value (KV) entry keyed by `event_id` that records which copy is being processed. Its time to live is W.
- **Dedup window W = 8 days**: 7 days of mobile SDK buffering plus one day of margin. It starts at the first accepted copy. Later copies do not refresh it.
- **Delivery limit**: the mobile SDK keeps unacknowledged events for up to 7 days and retries with backoff up to 5 minutes. The plan relies on this. It is SDK behaviour, not a verified contract.
- **Day close**: day D closes at 02:00 UTC on D+1.
- **Raw archive**: every accepted event, duplicates included, kept as received for 90 days from write time. It is the source of truth. `events_clean` is derived from it.
- **Operator**: the person who starts a replay.

## Live path

1. **Receive, stamp and check.** The collector accepts a batch of up to 100 events. It sets `received_at` from its NTP-synced server clock, creates a `batch_id`, and wraps each event in an envelope with its `position`. It rejects an event that lacks `event_id` or `device_id`, or whose bytes exceed 32 KB. Each rejected event gets a reason and goes to a reject log. The rest of the batch continues. Open: whether `event_id` must be a valid UUID.

2. **Make the batch durable, then answer.** Append the accepted envelopes to the replicated Kafka topic `events_raw`, keyed by `event_id`, with `acks=all`. All copies of one event share a key, so they share a partition. Return 202 only after the producer acknowledges, and list each rejected event with its reason. If Kafka is unavailable, return 503.

3. **Archive.** A separate consumer group reads `events_raw` and writes envelopes and bytes to object storage under `received_date=YYYY-MM-DD/`, rolling files hourly and by size. It does no deduplication. Objects expire 90 days after they are written. Kafka's 14-day retention is only a backstop.

4. **Claim.** For each event, the live consumer makes an atomic set-if-absent on KV key `event_id`. The value is `{state: pending, first_received_at, kafka_offset, owner, claimed_at}` and the TTL is W. The claim is written before the event is buffered or written. If the claim fails, the copy is a duplicate: it is not written, and it does not refresh the TTL.

5. **Enrich and write.** Collect claimed events into micro-batches of about 60 seconds. Enrich each with pinned code and reference-data versions (geo-IP lookup, user-agent parsing). Write them to partition `received_date = D` of `events_clean`, idempotent on `event_id`, so a retried batch cannot insert twice. Each row records `enrichment_version`, `reference_data_version` and `pipeline_version`. Bot-traffic handling is applied here once product decides it (see open questions).

6. **Commit.** After the warehouse write succeeds, set each claim to `committed`. Then commit Kafka offsets up to the last fully committed micro-batch, never past a pending claim. So a dropped duplicate in the same partition cannot hide a pending first copy. A committed claim stays until its TTL expires, so later copies within W are still dropped.

7. **Take over a stale claim.** A claim still `pending` after about 10 minutes may be taken over. Which consumer finds such claims is open. The taker sets itself as owner with a compare-and-set on the claim's revision number. It then re-reads the partition from the claim's `kafka_offset` and, for each event, does the following:
   - a committed claim is already done;
   - a stale pending claim is taken over and run through the claim, enrich-and-write and commit actions above;
   - an event with no claim is claimed as new and handled the same way.

   Its offset commit stops at the first claim it cannot take over. If the original consumer was only slow, its compare-and-set on commit fails. It then discards its result and commits no offsets. If it already wrote rows, they are identical, and the idempotent write keeps one row per event. Other partitions are not affected.

8. **Late copies.** A copy that arrives after W has no live claim, so it is admitted as new under its own `received_at`. Mobile events buffered for days are first arrivals. They land in the day they arrive, with their old client timestamps. If the first copy's claim has already expired, the late copy gets a second row in its own day, which breaks first-copy-wins. This happens only if the delivery limit is broken, and replay's 8-day lookback cannot detect it (open).

9. **Latency.** Target: p99 of 5 minutes from collector receipt to queryable, for first arrivals only. Budget: collector to Kafka under 1 second, micro-batch 60 to 90 seconds, then warehouse load. Measure `warehouse_commit_time - received_at` for each row. Alert when p99 reaches 4 minutes.

## Replay of one closed day D

Replay rebuilds day D from the archive only. It never writes to `events_raw`, the KV store or live offsets. It reads KV only for the live-write check.

1. **Gate, lock and pin.** Refuse to start unless the time is at least 02:00 UTC on D+1 plus the collector's write timeout T. The wait lets requests stamped just before close finish writing. Refuse unless the archive for D-8 through D still exists. Take a per-day lock so only one replay of D runs at a time. Choose the enrichment code version and the geo-IP and user-agent reference-data versions, and log them.

2. **Read the archive.** Read the objects with `received_date` from D-8 through D, on a separate compute pool with a capped read rate.

3. **Choose winners.** For each `event_id` with a copy in D, the winner is the copy with the smallest `(received_at, batch_id, position)` across D-8 through D. Keep it only if its `received_at` is in D. Live keeps the first copy it processes, and replay keeps the earliest `received_at`. They differ only by sub-second reordering across collector nodes. Replay is authoritative.

4. **Enrich and stage.** Run the pinned enrichment on each winner's original bytes. Write the rows to a staging table or partition for this run. Dashboards never read staging.

5. **Validate and diff.** Check that the row count equals the winner count, `event_id` is unique, every `received_at` is in D, and the schema matches. Diff against the current partition D: rows added, removed and changed, each with a reason. A removal above an operator-set threshold needs sign-off.

6. **Check for live writes.** Read KV. Abort with an alert if any pending claim has `first_received_at` in D. This is read only. Pending claims also cover buffered micro-batches, because each claim is written before its event is buffered.

7. **Swap.** Run the live-write check again immediately before the swap. Then replace partition D of `events_clean` from staging in one warehouse operation. Dashboards see the old partition or the new one, never a mix.

8. **Record and clean up.** Log D, the versions, the counts, the diff, the operator and the time. Drop the staging data.

Replays of different days can run in any order.

## What happens when things fail

| Where | What happens |
|---|---|
| Collector cannot write to Kafka | 503. Client resends the same batch with the same `event_id`s. |
| Validation | Rejected events are listed in the 202 response. Clients never resend them. |
| Client gets no response | Treated as a timeout. Client resends the same batch. |
| KV unavailable or slow (live) | No claim, no write, no offset commit. The event is read again from Kafka. The archive is unaffected. Lag and p99 alerts fire. |
| Warehouse write fails (live) | Claims stay `pending` and offsets are not committed. A takeover runs after about 10 minutes. |
| Consumer crashes after the warehouse write, before claims are `committed` | Claims stay `pending`. The takeover re-runs the write, which is idempotent, then commits. |
| Sink behind | Alert at 1 hour of lag. The close gate catches it for the day. |
| Replay live-write check cannot read KV | Abort and alert. Restart the replay from its gate. |
| Replay fails before the swap | `events_clean` is untouched. Abort and restart the replay from its gate. |
| Live row for D after the swap | Close-gate incident. Day D is not complete until investigated. The next replay corrects it. |

**Close gate.** At 02:00 UTC on D+1, check that the sink has flushed all objects for D. An event with `received_at` in D that arrives after this is a close-gate incident.

**Monitoring.** Collector 202 and 503 rates; reject rate by reason; Kafka consumer lag; sink lag; pending-claim age; end-to-end p99 latency; copies beyond W (should be near zero); per-day archive completeness.

**Retention.** A day can be replayed only while its archive and its eight lookback days are within the 90-day window. Expired days cannot be rebuilt.

## Open questions

- **Suspected bot traffic: drop or keep with a flag.** Not decided. This plan does not choose. The rule is applied the same way in the live micro-batch write and in replay. It is versioned, and a replay uses the version in force when the replay was requested. Dropping removes bot events from `events_clean`. Flagging adds a column. The archive keeps every accepted event either way. Product must decide before the enrichment stage ships.
- **Window size.** W = 8 days relies on the delivery limit. A 90-day window would match the archive, remove the late-copy risk and the dependency on the limit, at higher KV cost. Confirm the choice against the SLA.
- **Enforcement of the 7-day SDK buffer.** Not verified.
- **Winner rule.** Confirm that earliest `received_at` is acceptable as the authoritative winner.
- **Warehouse and KV capabilities.** Confirm keyed idempotent writes; atomic partition replace from a staging table; KV set-if-absent with TTL; compare-and-set on a KV revision; a KV query for pending claims by `first_received_at`; and whether the live-write check and the swap can be made atomic together.
- **Finding stale claims.** How a takeover finds `pending` claims older than 10 minutes is not defined.
- **KV product and owner.** Not known. The brief names only the capability.
- **Reject log retention.** Not specified.
- **Operator and sign-off.** Who the operator is, and who signs off a diff above the threshold, is not known.
- **Collector write timeout T.** Not known. The replay gate waits T after close.
- **Replay timing.** The brief does not say how soon after close replays run.