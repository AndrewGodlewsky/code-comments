# Clickstream ingestion plan

## What this is

Clients send batches of click and screen-view events to a new collector. The collector checks each event, stamps it with `received_at`, and appends it to a replicated log. It answers 202 only after every replica has the write.

Two readers then work from the log, independently. An archiver keeps every accepted event, duplicates included, in object storage for 90 days. A live job drops duplicate events, enriches the rest, and adds them to the warehouse table `events_clean` within 5 minutes.

A replay rebuilds one closed UTC day from the archive alone. It builds the day in a hidden table, checks it, and swaps it in atomically. It never touches the log or the live dedup store.

This is a new system. The brief names the existing pieces we use: a replicated append-only log (14-day retention), object storage with lifecycle rules, a key-value store with per-key TTL, and a warehouse that can atomically replace one day partition.

## Terms

- **Event:** one click or screen view. It has a client-made `event_id` (UUID), a `device_id` and a client timestamp.
- **`received_at`:** the collector's server time, in UTC. It is the only thing that decides an event's day.
- **`dt`:** the UTC date of `received_at`. It is the partition of `events_clean`.
- **Duplicate:** a later copy of an event with the same `event_id`. The first copy received wins.
- **Envelope:** the data the system adds to an event: `received_at`, `collector_id`, `batch_id`, and (at archive time) `log_partition` and `log_offset`. The event bytes are never changed.
- **Closed day:** day `D` closes at 02:00 UTC on `D+1`. Only closed days can be replayed.
- **Seal:** a marker `sealed/dt=D` in object storage. It says the archive holds all of day `D`, and it lists the log end offsets and files. Replay only runs on sealed days.
- **Stage:** a hidden warehouse table where a replay builds its day.

## How it fits together

```
clients -> collector -> raw log --+--> archiver -> object storage (raw, 90 d) --> replay job -> stage -> atomic swap
                                  |                                                                        |
                                  +--> live job (KV dedup, enrich) -> events_clean (dt = UTC day of received_at) <-+
```

The diagram shows the two paths. The live path is the top row from the log down to `events_clean`. The replay path is the archive, replay job, stage and swap.

## Running the system: live path

1. **Collector validates each event.**
   - Starts: a client sends a batch of up to 100 events over HTTPS.
   - Does: rejects an event if `event_id` or `device_id` is missing, or it is over 32 KB. Rejected events are not stored. The rest are accepted. The response is 202 with `{accepted: n, rejected: [{index, event_id if present, reason}]}`. A batch with more than 100 events, or one that cannot be parsed, gets a 4xx with `{error: reason}`. Clients do not retry a 4xx.
   - Data: nothing is kept. Rejections are counted by reason as a metric.
   - If it goes wrong: the collector keeps no state, so a request that fails can simply be sent again.

2. **Collector stamps, appends, acknowledges.**
   - Starts: step 1 has accepted at least one event.
   - Does: stamps `received_at` once per request. Appends each accepted event, with its envelope, to the log, keyed by `event_id`, with all-replica acknowledgement. Returns 202 only when every append is acknowledged. Resent batches are appended again, because duplicates must be kept. Dedup happens later.
   - Data: the log. Keying by `event_id` puts all copies of one event on one log partition, in a fixed order.
   - If it goes wrong: if the log is down or slow, the collector returns 503 (or 429 when shedding load), never 202. If only some appends succeed, the whole request fails and the client resends the whole batch. That is safe because dedup is by `event_id`.

3. **Archiver keeps the raw copy.**
   - Starts: it reads the log continuously, in its own consumer group, so a live job problem cannot stop archiving.
   - Does: reads a run of consecutive offsets from one partition and splits it by `received_at` day. It writes one object per day present, at `raw/dt=<day>/partition=<p>/<first_offset>-<last_offset>`, holding the original bytes and envelope. After all objects of the run are written, it saves one checkpoint "archived through offset N" for that partition.
   - Data: object storage, kept 90 days. The checkpoint says every record up to N is in some object.
   - If it goes wrong: after a crash it restarts from the last checkpoint and reads the run again. Files may then overlap, which is harmless because replay drops repeats by `(log_partition, log_offset)`. If it is about to write for a day that is already sealed (step 9), it writes the object anyway and also creates the marker `stale/dt=D`. Alert if it falls more than 1 hour behind, because the log keeps only 14 days.

4. **Live job drops duplicates.**
   - Starts: each log record, one at a time, in offset order. One consumer handles each partition, and the log's consumer-group fencing keeps it that way after a restart or rebalance.
   - Does: runs an atomic claim in the key-value store: set `event:<event_id>` to `(partition, offset)` if it does not exist, with an 8-day TTL (the 7-day retry window plus 1 day). If the claim succeeds, or the stored value equals this record, the record is the winner and goes on. Otherwise it is dropped and counted.
   - Data: the key-value store, sized for 8 days of unique `event_id`s.
   - If it goes wrong: if the store is unavailable, the job stops reading and lag builds. It never lets duplicates through and never drops events. The "stored value equals this record" rule covers a crash between the claim and the warehouse write: the redelivered record is recognized as the winner.

5. **Live job enriches.**
   - Starts: a winning record from step 4.
   - Does: runs geo-IP lookup and user-agent parsing. This is a pure function of the event and versioned reference data. It writes the code and geo-IP database versions into the row as `enrich_version`.
   - Data: none beyond the row.
   - If it goes wrong: the failure is treated like a failed warehouse write in step 7: the job stops and retries without committing offsets.

6. **Bot-traffic hook (decision open).**
   - Starts: an enriched record, before the warehouse write.
   - Does: for now it passes every event through unchanged. Only the hook is built. Product has not decided whether suspected bots are dropped (not written to `events_clean`) or kept with a new `is_suspected_bot` column. It also has not decided the detection rule or its owner. The hook never changes which copy wins. The archive keeps everything either way, so a replay can apply the decision later.
   - Data: none yet.
   - If it goes wrong: not applicable until the behavior exists.

7. **Live job writes to the warehouse.**
   - Starts: every 30 to 60 seconds, with a micro-batch of records.
   - Does: first checks whether `sealed/dt=D` exists for each record's day (the answer is cached for up to 1 minute). A record for a sealed day goes to `quarantine/dt=D/` and raises an alert. All other records are inserted into `events_clean` with insert-if-absent on `(dt, event_id)`. Only after the write succeeds does it commit the log offsets, covering every record in the batch including dropped duplicates.
   - Data: `events_clean`, and the quarantine objects.
   - If it goes wrong: it retries the same micro-batch with backoff and does not commit offsets. Retrying is safe because the insert adds nothing the second time. Reading pauses, lag builds, and the freshness alert fires. Nothing moves quarantined records automatically. They are already in the archive, so an operator decides whether to replay that day.

8. **Monitor the 5-minute target.**
   - Starts: continuously.
   - Does: freshness is `now - max(received_at)` visible in `events_clean`. Alert at 3 minutes. Also alert on consumer lag, archive lag, key-value errors, rejection rate, duplicate rate and quarantine count. Rough budget: collector to log under 1 s, micro-batch up to 60 s, warehouse load and visibility under 2 minutes.
   - Data: metrics only.
   - If it goes wrong: a missed alert means a missed target, so test the alerts before launch.

## Running the system: replay path

9. **Seal each day.**
   - Starts: a scheduled seal job at 02:00 UTC on `D+1`. It retries every 5 minutes.
   - Does: takes the log end offsets for all partitions. When the archiver's checkpoints reach them, it writes `sealed/dt=D`, holding the end offsets and the file list.
   - Data: the marker in object storage.
   - If it goes wrong: while the archiver is behind, the seal job waits and replay of `D` is refused. Alert if `D` is not sealed by 04:00 UTC. If a stale marker appears (step 3), an operator runs `seal --day D --force`. That takes fresh end offsets, waits for the archiver, overwrites the seal and deletes `stale/dt=D`.

10. **Replay starts and passes preflight.**
    - Starts: an operator runs `replay --day D`.
    - Does: refuses unless all of these hold. `D` is sealed and has no `stale/dt=D`. No replay is running for `D`, which it checks by creating `replay-lock/dt=D` with the run id. Raw data exists for `D` and for the 8 days before it, so replay works only for days up to about 82 days old. The enrichment code and reference-data versions are pinned and recorded.
    - Data: the lock object.
    - If it goes wrong: the job deletes the lock when the run ends, whether it succeeded or failed. If the job crashes, the lock stays. The operator checks the run is dead and runs `replay --day D --release`.

11. **Replay reads and dedupes the archive.**
    - Starts: preflight passed.
    - Does: reads only object storage, on compute separate from live ingestion. Drops overlapping records by `(log_partition, log_offset)`. Keeps a copy of an event in `D` only if no copy of the same `event_id` has a lower offset, either in `D` or in the 8 days before it. All copies of one event are on one log partition, so "earlier" is just the lower offset. The live job uses the same rule, so both pick the same copy.
    - Data: reads the archive. Replay has no credentials for the key-value store or the log.
    - If it goes wrong: nothing is published yet, so the run can just be started again.

12. **Replay enriches into the stage.**
    - Starts: step 11 has a list of first copies.
    - Does: applies the fixed enrichment code, and the bot decision once Product has made it. Writes to a stage table such as `events_clean_stage_<D>_<run_id>` that dashboards cannot see.
    - Data: the stage table.
    - If it goes wrong: nothing is visible to dashboards. The next run of `D` drops any old stage first.

13. **Replay validates the stage.**
    - Starts: the stage is complete.
    - Does: blocks the run unless all of these hold. No duplicate `event_id`s. Every row has `dt = D`. The row count equals the number of distinct first-copy `event_id`s computed from the archive. The stage's `event_id`s match the live partition's. A mismatch needs a named operator override, and the known cause is a clock skew across midnight that flipped which copy won live. A diff report shows which enrichment columns changed and how many rows.
    - Data: the replay log records the results and any override.
    - If it goes wrong: nothing is published. `events_clean` for `D` stays as live left it, the lock is released, and the stage is kept for inspection. The operator fixes the cause and re-runs, or re-runs with an override that names the failed check and gives a reason.

14. **Replay publishes.**
    - Starts: validation passed.
    - Does: replaces the `dt = D` partition of `events_clean` from the stage in one atomic operation. Dashboards see the old day or the new day, never a half-built one. Records the run in the replay log: run id, day, code and reference-data versions, input manifest, validation results, any override and operator. Drops the stage.
    - Data: `events_clean` and the replay log.
    - If it goes wrong: the replace is atomic, so a failure leaves the old day in place. Re-running is safe, because the output depends only on the archive and the pinned versions.

## What happens when things fail

| Failure | Result |
|---|---|
| Log unavailable or slow | Collector returns 503 or 429. Clients back off from 1 s to 5 minutes and resend. |
| Some appends fail in a batch | Whole request fails. Client resends. Dedup by `event_id` makes this safe. |
| Archiver crashes before checkpoint | Re-reads the run. Overlapping files are dropped by replay. |
| Key-value store down | Live job stops reading. Lag builds. No duplicates pass and no events are lost. |
| Live job crashes after claim | Redelivered record matches the stored claim, so it is not lost. |
| Warehouse write fails | Same micro-batch retried, offsets not committed. Insert is idempotent. |
| Record arrives for a sealed day | Goes to quarantine and raises an alert. An operator decides on a replay. |
| Archive behind at seal time | Seal waits and replay of that day is refused. Alert at 04:00 UTC. |
| Replay crashes | Lock stays. Operator confirms it is dead and releases it. |
| Replay validation fails | Nothing published. Stage kept. Operator fixes or overrides with a reason. |

## Guarantees to test

- **Live latency:** replay uses separate compute and reads only the archive, so it takes no log or key-value capacity.
- **Dedup state:** replay has no key-value credentials.
- **Day consistency:** the swap is atomic, and the live job cannot write to a sealed day.

## Retention

- Log: 14 days, as it exists.
- Key-value claims: 8-day TTL.
- Raw archive: a lifecycle rule deletes objects 91 days after creation, so every event is kept at least 90 days from receipt.
- `events_clean`: the brief gives no retention rule.

## Building and launching

Build in this order:

1. Collector and log.
2. Archiver and seal job.
3. Live job with key-value dedup and warehouse sink.
4. Replay job and its validation.
5. The bot hook's behavior, once Product decides.

Tests to write before launch:

- A duplicate within one batch, within one day, and across days (a retry 6 to 7 days later).
- A crash between the key-value claim and the warehouse write.
- A micro-batch retry that adds no duplicate rows.
- An archiver crash between writing files and saving the checkpoint.
- A malformed event inside a batch: the rest is accepted and the rejection is listed.
- Replay output equals live output when the enrichment code is unchanged. This is the main correctness check.
- A replay during peak live load, with live latency staying within target.
- A dashboard query during a swap returns only old or only new data.

## Open questions

| Item | Owner | Effect on plan |
|---|---|---|
| Drop or flag suspected bot traffic, and the detection rule. Not ours to decide. | Product | Step 6 only. Adds a column if "keep with flag". Replay can apply it later. |
| The warehouse can append or MERGE into `events_clean` for the open day, not only replace a partition. If it cannot, use a ledger of committed batches keyed by log partition and offset range. | Data platform | Step 7 sink design. |
| The key-value store has an atomic set-if-absent with TTL, and an atomic read of the stored value. | Platform | Step 4. |
| The log topic has a fixed partition count. Changing it needs a new topic and an explicit dedup cutover. | Platform | Steps 4 and 11 pick the same winner only if this holds. |
| The log's consumer-group fencing gives one consumer per partition, even across rebalances. | Platform | Steps 4 and 11 agree on the winner only if it holds. |
| Object storage can create an object only if it does not exist. | Platform | Seal, stale and lock markers in steps 3, 9 and 10. |
| Whole-batch 4xx rejection for oversized or unparseable batches. The brief only specifies per-event rejection. | Collector owner | Step 1 response contract. |
