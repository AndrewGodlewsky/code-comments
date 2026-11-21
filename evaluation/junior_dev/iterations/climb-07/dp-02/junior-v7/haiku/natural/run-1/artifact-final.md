# Clickstream ingestion: plan

Clients send click and screen-view events from the website and the iOS and Android apps to a new collector service. The collector writes each accepted event to a replicated log. One reader archives every copy to object storage for 90 days. A second reader decides which copy of each event wins and writes winners to the warehouse table `events_clean` within 5 minutes of receipt. A replay rebuilds one closed UTC day from the archive and the recorded decisions, then swaps that day into `events_clean` in one step. The plan keeps every copy and every decision, so a day can be rebuilt after a fix without changing which copy won.

## Terms

- **Event**: one click or screen view. It has a client-made `event_id` (a UUID, a random unique ID), a `device_id`, and a client timestamp, which is the time the device says the event happened.
- **Batch**: up to 100 events that a client sends in one HTTPS request.
- **received_at**: the collector's server time when it accepts an event. Its UTC day (the calendar day in Coordinated Universal Time) decides the event's warehouse partition, its archive folder, its decision folder, and the replay that covers it.
- **Copy**: one accepted occurrence of an `event_id` in the log. A client retry makes another copy.
- **Winner**: the first copy of an `event_id` in log order. Only winners reach `events_clean`.
- **Duplicate**: any copy of an `event_id` that is not the winner.
- **Log**: a replicated, append-only log (records are only added, never changed) with 14-day retention. It is split into partitions, which are separate lanes.
- **Offset**: a copy's position within its log partition. The pair (partition, offset) names exactly one copy.
- **Consumer group**: a named reader of the log. It saves how far it has read (its committed offset), so after a restart it resumes from there. Group A is the archive writer. Group B is the dedup stage.
- **KV store**: a key-value store. Each key can expire after a set time (its TTL, or time to live).
- **Object storage**: file storage for objects. A lifecycle rule deletes objects automatically after a set age.
- **Decision record**: one object per copy. It says whether the copy is a winner or a duplicate and, for a duplicate, which copy won.
- **Manifest**: the archive writer's summary for one UTC day: the copy count and the offset range in each log partition.
- **Seal point**: the log's end offset in each partition, recorded at 02:00 UTC on the day after day D.
- **Sealed manifest**: a day's manifest, marked final once every copy up to the seal point is in the archive.
- **Warehouse day partition**: all rows of `events_clean` whose `received_at` falls on one UTC day. This is not the same as a log partition.
- **MERGE**: a write that inserts new rows and updates existing ones by key, so writing the same rows twice does not duplicate them.
- **Enrichment**: adding geo-IP and user-agent fields to a winner.
- **Geo-IP lookup**: finding a location from an IP address.
- **UA parsing**: reading the browser and device from the User-Agent (UA) header.
- **Day close**: day D closes at 02:00 UTC on D+1.
- **Quarantine**: a separate table for winner rows that arrive after their day has closed. Dashboards and replays do not read it.
- **Staging**: a separate table where a replay builds one day before the swap. Dashboards do not read it.
- **Atomic swap**: replacing one whole warehouse day partition in a single operation. Readers see the old partition or the new one, never a mix.

## Assumptions to confirm

- Collector clocks are NTP-synced (kept close to true time by a network time service) to within a few seconds.
- The collector request deadline is 30 seconds or less.
- The archive writer and the decision writer keep up with the log within hours, not days.

---

## Part A: Live path

1. **The collector receives a batch.** It starts when a client sends a batch over HTTPS. The collector parses the batch envelope and checks each event on its own. `event_id` and `device_id` must be present, and the serialized event must be 32 KB or less. Each invalid event is rejected one at a time. Each rejection is listed in the response with its batch index, its `event_id` if present, and a reason. The valid events in the same batch are kept. Batch-level failures (malformed JSON, or more than 100 events) return 400. See Open questions. Clients never retry rejected events.

2. **The collector stamps each accepted event.** It sets `received_at` from its own clock. It keeps ingest metadata beside the event: `batch_id`, the collector node, the client source IP, and the User-Agent header. Geo-IP and UA parsing need the IP and UA, and the event body does not carry them.

3. **The collector appends to the log.** It writes each accepted event's raw body bytes, exactly as received, with its metadata. The log partition is a hash of `event_id`, so all copies of one `event_id` land in the same partition, in order. The collector does not deduplicate. A retry becomes another copy, and every copy is kept.
   - If any append fails, the batch gets no 202. The client resends the whole batch with the same `event_id`s, so some events may get extra copies. That is allowed.

4. **The collector acknowledges.** It returns 202 only after the log confirms the replicated write of every accepted event. The body lists the rejected events. Without a 202, the client resends the batch (see step 3).

5. **The archive writer keeps every copy (consumer group A).** It starts from its last committed offset and reads the log forward. It writes each copy to object storage exactly as received, with its metadata, including its log partition and offset. Objects are grouped by the UTC day of `received_at`. The object name includes the partition and offset, so a rewrite after a restart replaces the same object. No copy is counted twice, and a restart neither skips nor double-counts copies. A lifecycle rule deletes each object 90 days after it is written.
   - For each day it keeps a manifest: the copy count and the offset range per log partition. At 02:00 UTC on the day after D, it records the seal point for day D. When it has written every copy up to the seal point, it writes day D's manifest as sealed.
   - It keeps its data in object storage for 90 days.
   - If it falls behind, alert on archive lag, aiming for under a few hours. The log's 14-day retention is the hard limit: copies that expire from the log before they are archived are lost. A replay of that day waits until its manifest is sealed.

6. **The dedup and decision stage decides each copy (consumer group B, separate from A).** It reads the log forward, in order, per partition. Duplicates are identified by `event_id` alone. For each copy:
   - a. **Set the KV key.** It atomically sets the KV key `event_id`, only if the key is absent, with TTL 8 days. The value is the copy's (partition, offset, received_at). The 7-day retry window plus one day of margin makes 8 days the TTL.
   - b. **Decide.** If the set succeeded, the copy is the winner. If the key already exists with this same (partition, offset), the copy is also the winner. That keeps a restart safe. Otherwise the copy is a duplicate, and its decision record names the winner.
   - c. **Write the decision record.** Write one object per copy, named by its (partition, offset) and grouped by its `received_at` day. It holds `event_id`, `received_at`, winner or duplicate, and, for a duplicate, the winner's (partition, offset). Write it before enriching. A rewrite after a restart replaces the same object with the same content. Decision records are kept 90 days, because replay needs them.
   - d. **Enrich and send winners only.** Run the geo-IP lookup and UA parsing, set `enrichment_version`, and send the row to the live writer.
   - e. **Commit the offset after the warehouse write.** The group B offset moves past a copy only after the live writer confirms the warehouse write of that row.
   - It keeps its data in the KV store for 8 days, in decision records for 90 days, and in the warehouse row (step 7).
   - If the KV store is down or slow, wait and retry the same copy. Do not skip it and do not move the offset. Ingestion keeps running, live lag grows, and alerts fire.
   - If an enrichment lookup fails for a winner, do not drop the winner and do not wait. Send the row with empty enrichment columns and an empty `enrichment_version`. A replay of the day fills them in.
   - If it crashes after the KV set but before the decision record, then on restart the KV key still holds this copy's (partition, offset). The copy is a winner again, and its decision record is then written.
   - If it crashes after the decision record but before the warehouse write, the offset has not moved, so the copy is processed again. The KV answer is the same, so the decision is unchanged. The decision record is rewritten with the same content, and MERGE prevents a second row.

7. **The live warehouse writer.** It starts when a winner arrives. It writes winners to the warehouse day partition for their `received_at` day, in micro-batches of about one minute. It uses MERGE by `event_id` within the partition, or keyed batch IDs, so a restart never duplicates rows. A row must be queryable within 5 minutes of its `received_at`. Measure p95 and p99 lag, and alert at 4 minutes.
   - If the warehouse or the writer fails, the group B offset does not move (step 6e), so copies are processed again. Lag alerts fire.

8. **Day close.** Day D closes at 02:00 UTC on D+1. Before close, every winner with `received_at` on D should be in `events_clean`. Check this by comparing the winner count in D's decision records with D's row count.
   - A winner that arrives after close is an incident. Alert, and write its row to the quarantine table, not to partition D. The next replay of D rebuilds from the archive and the decision records, which already hold this copy, so the replay includes the row. After that replay's swap, delete the quarantined rows for D.

---

## Part B: Replay of a closed day

Preconditions. All must hold.

- Day D is closed: the current time is at or after 02:00 UTC on D+1.
- Day D is still inside the 90-day archive window. A replay cannot run after the objects are deleted.
- No other replay of day D is running. A per-day lock enforces this.

Steps

1. **Check completeness.** It starts when an operator asks for a replay of day D. Wait until D's manifest is sealed and the decision writer has processed the log past the seal point. Then check that the archived copy count equals the manifest count, and that every copy has a decision record. If the counts do not match, or any copy has no decision, fail the replay and do not continue. `events_clean` is unchanged.

2. **Read copies.** Read day D's copies and their metadata from object storage only. Do not read the log, which keeps only 14 days, and do not read the KV store.

3. **Join decisions.** Join the decision records to the copies on (partition, offset). Each copy must match exactly one decision.

4. **Select winners.** Keep the copies whose decision is winner. This count is a sanity baseline, compared with the live partition's row count in step 7. It is not the authority.

5. **Re-enrich.** Parse each winner's raw bytes and run the corrected geo-IP and UA enrichment. Set `enrichment_version` to the new version. The same inputs and version always give the same output. The bot-traffic choice (open question 1) applies here.

6. **Write to staging.** Write the rebuilt rows to a staging table named for day D and this run. Check that every row's `received_at` is on day D and that `event_id` is unique.

7. **Validate.** Check that the row count equals the winner count from step 4, that required fields are not null, and that `event_id` is unique. Compare with the current partition D and report rows added, rows removed, and changed enrichment columns. A human must approve the run when the change is above a threshold (open question 8).
   - If validation fails, `events_clean` is unchanged.

8. **Atomic swap.** Replace partition D in `events_clean` with the staging contents in one warehouse operation. Dashboards read the old partition until the swap commits, then read the new partition in full. They never see a half-rebuilt day.

9. **Clean up and record.** Drop staging. Delete the quarantined rows for D. Record the run: day, run ID, enrichment version, counts, operator, and start and end times.

Failure and re-run

- Any failure before the swap leaves `events_clean` unchanged.
- Re-running day D with the same enrichment version gives the same output.

Isolation from live ingestion

- The replay runs as its own job with its own compute quota, separate from the live warehouse pool, so it does not slow live ingestion. Archive reads are rate-limited.
- The replay never reads or writes the KV store, never uses the live consumer-group offsets, and never writes archive objects or decision records.
- It writes only to staging and to the atomic swap of partition D. The live path does not depend on replay.

---

## Rules that always hold

- Each `event_id` has at most one winner row in `events_clean`.
- Winners are decided once, by the live KV stage. Replay uses the recorded decisions and never re-decides.
- Partition D changes only through live writes before close, or through the atomic replay swap. After close, live writes never touch D.
- Archive objects and decision records are kept at least 90 days. The lifecycle rule is never shorter than 90 days.

## What happens when things fail

Failures that belong to one step are listed under that step. These apply across steps.

| Failure | What happens |
|---|---|
| Client loses the response (timeout, 429 or 5xx) | The client resends the same batch with the same `event_id`s, backing off from 1 s up to 5 min. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can arrive up to 7 days after the first copy. The extra copy is archived, and the KV check drops it. |
| Late copy from a later day (received_at on D+k) | It is archived under D+k. It wins only if no earlier copy of its `event_id` exists in log order. Otherwise it is recorded as a duplicate. Either way, partition D is untouched. |
| KV key expires before a late retry arrives | A late retry could become a second winner. The 8-day TTL covers the 7-day window. A canary alerts on any KV miss for a copy whose client timestamp is more than 7 days old. |
| Dedup stage falls more than 8 days behind | KV keys may expire before a copy is decided, so a restart could make a second winner. Alert on dedup lag at the same threshold as archive lag. |
| Collector clock drift | A wrong `received_at` puts rows in the wrong partition and the wrong replay. Alert on clock skew between nodes. |
| Enrichment bug in live | Replay the affected days after the fix. |
| Dedup logic bug | The recorded decisions carry the bug. Fixing it needs a re-decision procedure, which is not designed here (open question 6). |

## How to verify (build and rollout)

- Load test with duplicates delayed 0 to 7 days. Check that exactly one winner row exists per `event_id`.
- Fault-inject the dedup stage between the KV set and the decision write, and between the decision write and the warehouse write. Check that there is no lost or double winner.
- Take the KV store down for a period under load. Check that no copy is skipped.
- Measure end-to-end latency from `received_at` to queryable. Confirm p99 is under 5 minutes.
- Dry-run a replay of a closed day, then compare its counts with the live partition.
- Confirm the object-storage lifecycle rule is 90 days for archive objects and for decision records.
- In a test environment, query partition D during a staged swap. Confirm that no partial rebuild is visible.

## Open questions

1. **Suspected bot traffic: drop or keep with a flag.** Product must decide. The plan works either way. The choice applies to winners in enrichment, as a filter or as a flag column. The archive keeps all copies regardless. Because the choice sits in enrichment, a replay re-applies it. Where the filter sits relative to dedup is set when the decision is made.
2. **Storing client IP and User-Agent in the archive.** The plan assumes they are stored, because replay cannot re-derive them from the event body. This needs a privacy review.
3. **Batch-level errors.** Clients retry only on timeout, 429 and 5xx. A 400 for a malformed envelope or an oversized batch would drop events. The brief does not say how this should be handled.
4. **Retention of `events_clean`.** Not specified. The 90-day archive retention bounds how far back a replay can reach.
5. **KV TTL of 8 days.** Confirm it against the 7-day retry guarantee and the storage cost of the key space.
6. **Re-deciding dedup after a logic fix.** This would rebuild winners from the archive by `event_id` across the 7-day window. Not designed here.
7. **Which `received_at` decides the day when copies of one `event_id` differ.** The plan uses the winner's. A copy stamped just after midnight can win over an earlier-stamped copy if clock skew reverses their log order. Product must confirm this is acceptable.
8. **Replay approval threshold.** The size of change that needs human approval is not set.