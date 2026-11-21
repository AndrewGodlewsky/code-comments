# Clickstream ingestion: plan

## Scope and assumptions

- Sources: website, iOS and Android apps. Event types: click and screen-view.
- Existing infrastructure: a replicated append-only log (14-day retention), object storage with lifecycle rules, a key-value (KV) store with per-key TTL, and a warehouse that can atomically replace one day partition of a table.
- Assumptions to confirm: collector clocks are NTP-synced to within a few seconds. The collector request deadline is 30 seconds or less. The archive and decision writers keep up with the log within hours, not days.

## Terms

- **received_at**: the collector's server timestamp, stamped when an event is accepted. It decides the UTC day, the partition, and the replay that covers an event.
- **copy**: one accepted occurrence of an `event_id` in the log. A client retry creates another copy.
- **winner**: the first copy of an `event_id` in log order. Only winners reach `events_clean`.
- **decision record**: one per copy, saying whether it is a winner or a duplicate, and which copy won.

---

## Part A: Live path

1. **Receive the batch.** The collector parses the batch envelope. It validates each event on its own: `event_id` and `device_id` must be present, and the serialized event must be 32 KB or less. Invalid events are rejected individually. Each rejection is listed in the response with its batch index, `event_id` if present, and a reason. Valid events in the same batch are kept.

2. **Stamp each accepted event.** Set `received_at` from the collector clock. Keep these as ingest metadata beside the event: `batch_id`, the collector node, the client source IP, and the User-Agent header. Geo-IP and UA parsing need the IP and UA, and the event body does not carry them.

3. **Append to the log.** Write each accepted event's raw body bytes, exactly as received, plus the metadata from step 2. Partition the log by a hash of `event_id`, so every copy of one `event_id` lands in one partition, in order.

4. **Acknowledge.** Return 202 only after the log confirms the replicated write. The body lists the rejected events. Batch-level failures (malformed JSON, more than 100 events) return 400. Clients never retry rejected events. The 400 handling is an open question (see Open decisions).

5. **Do not deduplicate at the collector.** Retries become extra copies. Every copy is kept.

6. **Archive writer (consumer group A).** Read the log and write every copy to object storage, exactly as received, with its metadata. Partition objects by the UTC day of `received_at`. Each day also gets a manifest with the copy count and the log offset ranges per partition. Set the lifecycle rule to delete objects 90 days after they are written. Writes start from the last committed offset, so restarts neither skip nor double-count copies.

7. **Dedup and decision stage (consumer group B, separate from A).** For each copy, in log order per partition:
   1. Atomically set the KV key `event_id` only if it is absent, with TTL 8 days. The value is the copy's (partition, offset, received_at). The 7-day retry window plus one day of margin makes 8 days the TTL.
   2. If the set succeeded, the copy is the winner. If the key already exists with this same (partition, offset), treat the copy as the winner. This keeps the stage safe to restart. Otherwise the copy is a duplicate.
   3. Write the decision record for the copy to object storage, partitioned by the copy's received_at day. Do this before enriching the winner.
   4. For winners only, enrich: geo-IP lookup, UA parsing, and an `enrichment_version` field. Then send the row to the live writer.

8. **Live warehouse writer.** Write winners to the `events_clean` partition for their received_at day in micro-batches of about one minute. Make each write idempotent: MERGE by `event_id` within the partition, or keyed batch IDs, so a restart never duplicates rows. Target: a row is queryable within 5 minutes of its received_at. Measure p95 and p99 lag, and alert at 4 minutes.

9. **Duplicates stay in the archive.** A late copy with received_at on day D+k is archived under D+k and recorded as a duplicate. It never touches partition D. A late retry of a day-D event is dropped by the KV check, so it cannot create a second row.

10. **Day close.** Day D closes at 02:00 UTC on D+1. Any winner with received_at on D should be in `events_clean` before close. A winner that appears after its partition is closed is an incident. Alert, quarantine the row, and let the next replay of D include it, because the replay reads the archive and decisions, not the live table.

---

## Part B: Replay of a closed day

Preconditions
- Day D is closed: current time is at or after 02:00 UTC on D+1.
- Day D is still within the archive window, meaning the 90-day objects still exist. Replays cannot run after that.
- No other replay of day D is running. Take a per-day lock.

Steps
1. **Check completeness.** Confirm that the archive writer and the decision writer have both processed the log past 02:00 UTC on D+1. Confirm that the day-D manifest is sealed. If the archived copy count does not match the manifest, or any copy has no decision record, fail the replay and do not continue.
2. **Read copies from the archive.** Read day D's copies and their metadata from object storage only. Do not read the log, which keeps only 14 days, and do not read the KV store.
3. **Join decisions.** Join the decision records to the copies on (partition, offset). Every copy must have exactly one decision.
4. **Select winners.** Keep copies flagged as winners. Their count is a sanity baseline against the live partition's row count, not the authority.
5. **Re-enrich.** Parse each winner's raw bytes and run the corrected enrichment (geo-IP, UA). Set `enrichment_version` to the new version. For the same inputs and version, output is deterministic.
6. **Write to staging.** Write the rebuilt rows to a staging table or partition named for this day and replay run. Staging is invisible to dashboards. Check that every row has received_at on day D and that `event_id` is unique.
7. **Validate.** Check that the row count equals the winner count from step 4. Check that required fields are not null and `event_id` is unique. Compare against the current partition and report rows added, rows removed, and changed enrichment columns. Require human approval above a set threshold.
8. **Atomic swap.** Replace partition D in `events_clean` with the staging contents in one warehouse operation. Dashboards read the old partition until the swap commits, then read the new partition in full. They never see a partial rebuild.
9. **Clean up and record.** Drop staging. Record the run: day, run ID, enrichment version, counts, operator, and timestamps.

Failure and re-run behavior
- Any failure before step 8 leaves `events_clean` unchanged.
- Re-running the same day with the same enrichment version produces the same output.

Isolation from live ingestion
- Replay runs as its own job with its own compute quota, separate from the live warehouse pool. Archive reads are rate-limited.
- Replay never reads or writes the KV dedup store, never uses the live consumer-group offsets, and never writes archive objects or decision records.
- Replay writes only to its staging table and to the atomic swap of partition D. The live path does not depend on replay.

---

## Invariants for review

- I1. `received_at` (UTC) decides the partition and which replay covers an event.
- I2. A 202 is returned only after the log acknowledges a replicated write.
- I3. Each `event_id` has at most one winner row in `events_clean`.
- I4. Every accepted copy, duplicates included, is kept in the archive for 90 days. The lifecycle rule is never shorter than 90 days.
- I5. Winners are decided once, at live time, by the KV stage. Replay uses the recorded decisions and never re-decides.
- I6. Partition D changes only through live writes before close, or through the atomic replay swap.

## Failure modes and mitigations

- **Client retry after a lost response.** A duplicate copy is archived and dropped by the KV check.
- **Dedup stage crashes after the KV set but before the decision write.** On restart, the KV value matches this copy's (partition, offset), so it is treated as the winner, and its decision record is then written.
- **Archive writer falls behind.** Alert on archive lag, aiming for under a few hours. The log's 14-day retention is the hard limit. Copies that expire from the log before they are archived are lost.
- **KV TTL expires before a late retry.** A late retry could then become a second winner. The 8-day TTL covers the 7-day guarantee. Add a canary: alert on any KV miss for a copy whose client timestamp is more than 7 days old.
- **Collector clock drift.** A wrong `received_at` puts rows in the wrong partition and in the wrong replay. Alert on clock skew between nodes.
- **Late copy from a later day.** It is counted under its own day, so it does not change day D.
- **Missing decision at replay time.** The completeness check in step 1 fails the replay.
- **Enrichment bug in live.** Fixed by replaying the affected days after the fix.
- **Dedup logic bug.** Recorded decisions carry the bug. Fixing it needs a separate re-decision procedure, which is not designed here. See Open decisions.

## Open decisions

1. **Suspected bot traffic: drop or keep with a flag.** Not decided. Product must choose. The plan works either way. The choice applies to winners in the enrichment stage (filter or flag column), and the archive keeps all copies regardless. Because it sits in enrichment, a replay re-applies the choice. Where the filter sits relative to dedup is set when the decision is made.
2. **Storing client IP and User-Agent in the archive.** The plan assumes these are stored, because replay cannot re-derive them from the event body. Needs a privacy review.
3. **Batch-level errors.** Clients retry only on timeout, 429 and 5xx, so a 400 for a malformed envelope or an oversized batch would drop events. The brief does not say how this should be handled.
4. **Retention of `events_clean` itself.** Not specified. Archive retention (90 days) bounds how far back replay can reach.
5. **KV TTL value.** Proposed 8 days. Confirm against the 7-day retry guarantee and the storage cost of the key space.
6. **Re-deciding dedup.** A dedup-logic fix needs a re-decision procedure, which would have to rebuild winners from the archive by event_id across the 7-day window. Not designed here.

## Verification plan

- Load test with duplicates delayed 0 to 7 days, and check that exactly one winner row exists per `event_id`.
- Fault-inject the dedup stage between the KV set and the decision write, then check that there is no lost or double winner.
- Measure end-to-end latency from received_at to queryable, and confirm p99 is under 5 minutes.
- Dry-run a replay of a closed day, then compare its counts with the live partition.
- Confirm the object-storage lifecycle rule is 90 days in the bucket configuration.
- Confirm that a swap is not visible mid-way: query the partition during a staged swap in a test environment.