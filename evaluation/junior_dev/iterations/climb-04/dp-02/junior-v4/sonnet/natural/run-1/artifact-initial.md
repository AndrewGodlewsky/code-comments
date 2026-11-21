# Clickstream ingestion plan

## Summary

Clients send batches to a collector. The collector validates each event, stamps it with `received_at`, and appends it to the replicated log. It returns 202 only after the log write is acknowledged by all replicas.

Two independent consumers read the log:

- An **archiver** copies every accepted event, duplicates included and byte-for-byte, to object storage for 90 days.
- A **live stream job** dedupes on `event_id` with a key-value claim, enriches, and appends to `events_clean`.

**Replay** is a batch job over the object-storage archive. It never touches the log or the key-value store. It builds the day in a hidden staging table, validates it, and swaps it in with the warehouse's atomic partition replace.

```
clients -> collector -> raw log --+--> archiver -> object storage (raw, 90 d) --> replay job -> stage -> atomic swap
                                  |                                                                       |
                                  +--> live job (KV dedup, enrich) -> events_clean (dt = UTC day of received_at) <-+
```

## Assumptions to confirm before building

These are not stated in the brief. The plan depends on them.

- **A1.** The warehouse can append rows or MERGE into `events_clean` for the open day, not only replace a partition. The plan uses an idempotent insert-if-absent on `(dt, event_id)`. If MERGE is unavailable, use a committed-batch ledger keyed by log partition and offset range.
- **A2.** The key-value store has an atomic "set if not exists, with TTL" and an atomic read of the stored value.
- **A3.** The log topic has a fixed partition count. Events are keyed by `event_id`, so all copies of one event land on one partition and have a total order. Changing the partition count needs a new topic and an explicit dedup cutover.
- **A4.** A batch with more than 100 events, or a body that is not parseable, is rejected whole with a 4xx. This is not a retryable status, so clients do not resend it. The brief only specifies per-event rejection.

## Open decision (not ours to make)

**Bot traffic: drop or keep with a flag is undecided by Product.** Step 8 is the single place this will be implemented. Nothing else in the plan depends on the answer. See "Open items" at the end.

---

## Live path

1. **Fix the data contract.**
   - Every record in the log and the archive has two parts: the original event bytes, untouched, and an envelope.
   - The envelope holds `received_at` (UTC, from the collector), `collector_id`, `batch_id`, `log_partition` and `log_offset` (the latter two added at archive time).
   - The event body is treated as opaque bytes after validation and is never re-serialized. This is what lets the archive satisfy "kept exactly as received".
   - The partition day is `dt = UTC date of received_at`. The client timestamp is a plain column and never decides a partition or a replay.

2. **Collector: validate each event on its own.**
   - Reject an event if `event_id` is missing, `device_id` is missing, or the event is over 32 KB.
   - Rejected events are not stored. They are listed in the response as `{index, event_id (if present), reason}`.
   - The rest of the batch continues. Clients never retry rejected events, so they must be listed precisely.
   - Count rejections by reason as a metric.

3. **Collector: stamp, append, then acknowledge.**
   - Stamp `received_at` once per request, on arrival.
   - Append each accepted event to the log, keyed by `event_id`, with all-replica acknowledgement.
   - Return 202 only after every append in the batch is acknowledged.
   - Every accepted copy is appended, including resent batches. Dedup happens downstream, never at the collector, because duplicates must be retained.

4. **Collector: failure behavior.**
   - If the log is unavailable or slow, return 503, or 429 under load shedding, never 202. Clients already back off from 1 s to 5 min on these codes.
   - A partial append failure fails the whole request. The client resends the whole batch, which is safe because dedup is by `event_id`.
   - The collector keeps no state, so it scales horizontally.

5. **Archiver: the 90-day raw copy.**
   - Run a dedicated consumer group, separate from the live job, so a live-job incident cannot stop archiving.
   - Write to object storage as `raw/dt=<received_at day>/partition=<p>/<first_offset>-<last_offset>`. Cut files at day boundaries, and keep the original bytes and envelope.
   - Commit a per-partition "archived through offset" checkpoint after each file.
   - Alert if archive lag exceeds 1 hour. The log keeps only 14 days, so the archive becomes the system of record and must never fall far behind.
   - Overlapping files from retries are harmless. Replay dedupes records on `(log_partition, log_offset)`.

6. **Live job: deduplicate by `event_id` alone, first copy wins.**
   - For each record, run an atomic claim in the key-value store: `SET event:<event_id> = (partition, offset) IF NOT EXISTS`, with a **TTL of 8 days**. The retry window is 7 days, plus 1 day of margin.
   - If the claim succeeds, or the stored `(partition, offset)` equals this record's, the record is the winner and continues.
   - If the stored value is a different record, drop it as a duplicate. Count it.
   - The "equals this record" case makes crash recovery safe. If the job dies after claiming but before writing to the warehouse, the redelivered record is recognized as the winner and not lost.
   - If the key-value store is unavailable, stop consuming and let lag build. The log holds 14 days. Never fail open, which would let duplicates through, and never fail closed by dropping events.
   - Size the key-value store for 8 days of unique `event_id`s once the event rate is known.

7. **Live job: enrich.**
   - Run geo-IP lookup and user-agent parsing as a pure function of the event plus versioned reference data.
   - Write the enrichment code version and geo-IP database version into each row as `enrich_version`. This is how a replay is later told apart from live output.

8. **[OPEN] Bot-traffic decision point.**
   - This step runs after dedup, so the decision never changes which copy wins and never changes archive contents.
   - Build only the hook until Product decides. Do not implement either behavior.
   - Option A, drop: suspected-bot events are not written to `events_clean`. They stay in the raw archive.
   - Option B, keep with a flag: add an `is_suspected_bot` column to `events_clean`. This is a schema change that should be sequenced with the dashboards.
   - Either way, the archive keeps everything, so the decision can be applied retroactively through replay.
   - This step also needs the detection rule and its owner, which are undecided too.

9. **Live job: write to the warehouse idempotently.**
   - Write micro-batches of about 30-60 seconds into `events_clean`, with `dt` from the winning copy's `received_at`.
   - Use insert-if-absent on `(dt, event_id)` (A1), so a replayed micro-batch after a crash adds nothing.
   - Commit log offsets only after the warehouse write succeeds.
   - The live job must refuse to write to a sealed day (step 11). It diverts such a record to a quarantine location and raises an alert. This protects a replay from a late straggler.

10. **Meet and monitor the 5-minute target.**
    - Freshness is `now - max(received_at)` visible in `events_clean`. Alert at 3 minutes, which leaves headroom before the 5-minute limit.
    - Also alert on consumer lag, archive lag, key-value error rate, rejection rate, duplicate rate, and quarantine count.
    - Rough latency budget: collector to log under 1 s, micro-batch up to 60 s, warehouse load and visibility under 2 min.

## Replay path

11. **Seal each day before it can be replayed.**
    - A day `D` closes at 02:00 UTC on `D+1`.
    - After that time, take the log end offsets for all partitions.
    - When the archiver's checkpoints reach those offsets, write `sealed/dt=D` containing the end offsets and the file list.
    - If the archiver later sees a record for an already sealed day, mark the seal stale and alert. The operator can then re-seal and replay.

12. **Replay request and preflight.** The operator runs `replay --day D`. The job refuses unless all of these hold:
    - `D` is sealed and not stale, which also means it is closed.
    - No replay is running for `D`. Take a lock keyed by day.
    - Raw archive data exists for `D` and for the 8-day lookback `D-8 ... D-1`. Because of the 90-day archive retention, replay is only possible for days no more than about 82 days old.
    - The enrichment code and reference-data versions are pinned and recorded for the run.

13. **Replay: read and dedupe from the archive.**
    - Read only object storage, on separate compute from live ingestion.
    - Drop overlapping records by `(log_partition, log_offset)`.
    - Keep a copy of an event in `D` only if no copy of the same `event_id` has an earlier log order in the lookback window `D-8 ... D-1` or earlier in `D`. This is the same "first copy wins" rule as the live key-value claim.
    - Never read or write the live key-value store. Dedup state is rebuilt from the archive alone, so live state cannot change.

14. **Replay: enrich into a hidden stage.**
    - Apply the fixed enrichment code and apply the step 8 decision once Product has made it.
    - Write to a staging table, for example `events_clean_stage_<D>_<run_id>`, that dashboards cannot see.

15. **Replay: validate before publishing.** The run is blocked unless all of these hold:
    - Zero duplicate `event_id`s in the stage.
    - Every row has `dt = D`.
    - The row count equals the number of distinct first-copy `event_id`s computed from the archive.
    - The set of `event_id`s matches the live partition's set. A mismatch needs a named operator override. The known edge case is a clock skew across midnight that flipped which copy won live.
    - A diff report shows which enrichment columns changed and how many rows. This confirms the fix did what was intended.

16. **Replay: publish with the atomic partition replace.**
    - Replace `events_clean` partition `dt = D` from the stage in one atomic operation.
    - Dashboards see the old day or the new day, never a half-built one.
    - Record the run in a replay log: run id, day, code and reference-data versions, input manifest, validation results, and operator.
    - Drop the stage afterwards. A failed run just drops the stage, because nothing was published.
    - Re-running a replay is safe, since the output depends only on the archive and the pinned versions.

17. **Isolation guarantees, stated as testable properties.**
    - **Live latency:** replay uses separate compute and reads only the archive, so it takes no log or key-value capacity.
    - **Dedup state:** replay has no key-value credentials.
    - **Day consistency:** the swap is atomic, and the live job cannot write to a sealed day.

## Operations and delivery

18. **Retention.**
    - Log: 14 days, as it exists.
    - Key-value claims: 8-day TTL.
    - Raw archive: a lifecycle rule deleting objects 91 days after creation. Extra margin guarantees that each event is kept for at least 90 days from receipt.
    - `events_clean`: no retention rule is given in the brief.

19. **Tests to write before launch.**
    - A duplicate within the same batch, within the same day, and across days (a retry 6-7 days later).
    - A crash between the key-value claim and the warehouse write.
    - A micro-batch retry that adds no duplicate rows.
    - A malformed event inside a batch: the rest is accepted and the rejection is listed.
    - Replay output equals live output when the enrichment code is unchanged. This is the main correctness check.
    - A replay running during peak live load, with live latency staying within target.
    - A dashboard query during a swap returns only old or only new data.

20. **Build order.**
    1. Collector and log.
    2. Archiver and seal.
    3. Live job with key-value dedup and warehouse sink.
    4. Replay job and its validation.
    5. The bot hook, once Product decides.

## Open items

| Item | Owner | Effect on plan |
|---|---|---|
| Drop or flag suspected bot traffic, and the detection rule | Product | Step 8 only. Adds a column if "keep with flag". Replay can apply it retroactively. |
| A1: warehouse supports append or MERGE | Data platform | Step 9 sink design. |
| A2: key-value store has atomic set-if-absent with TTL | Platform | Step 6. |
| A3: fixed log partition count | Platform | Replay's first-copy rule in step 13. |
| A4: whole-batch rejection for oversized or unparseable batches | Collector owner | Step 2 response contract. |
