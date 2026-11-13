# Clickstream ingestion plan for `events_clean`

## What this is

There is no existing pipeline, so this one is new. Web, iOS and Android clients send click and screen-view events to a collector. The collector writes each accepted event to a replicated log. A dedup consumer keeps only the first copy of each event, enriches it and writes it to the warehouse table `events_clean`, which has one partition per UTC day. A raw archive sink copies every accepted event to object storage beside it.

Main flow: client, collector, log, dedup, enrichment, clean write. When a UTC day is complete, it is rebuilt automatically (the seal). Later, an operator can rebuild a sealed day again (replay), for example after an enrichment fix. Live events must be queryable within 5 minutes.

## Terms

- **Event**: one click or screen view. It has a client-made `event_id` (UUID), a `device_id` and a client timestamp.
- **received_at**: the server's UTC time when the collector accepts an event. An event's day, partition and replay all use this time, never the client time.
- **Day D**: the UTC day of `received_at`. It closes at 02:00 UTC on D+1.
- **Day states**: *open* until it closes. *Closing* from 02:00 UTC on D+1 until its seal finishes (it still takes writes). *Sealed* after the seal.
- **Log**: the replicated append-only log, with 14-day retention. It is a transport buffer, not an archive. Each event goes to a partition chosen by a hash of its `event_id`. Each partition is read in order by one consumer.
- **Log position**: a partition number plus an offset in that partition.
- **Winner**: the first copy of an `event_id` in log order. Later copies are **duplicates**.
- **Key-value store**: one key per `event_id`, whose value is the winner's log position, with a 9-day TTL. It also holds one **day record** per day, with no TTL. The day record holds the cutoff and the sealed state.
- **Cutoff** (for day D): for each log partition, the last log position of a write stamped on day D.
- **Dedup offset**: the dedup consumer's place in each log partition. It is saved in the log.
- **Raw archive**: object storage holding every accepted event as received, with its `received_at`, batch id and log position. Kept 90 days.
- **Manifest**: object storage with one row per accepted event: `event_id`, `received_day`, log position and `decision` (`winner` or `duplicate`). Kept 90 days.
- **Seal**: the automatic rebuild of day D once it is complete. It uses the live enrichment versions.
- **Replay**: a rebuild of a sealed day with chosen enrichment versions. An operator starts it.
- **Staging table**: a warehouse table with the same columns as `events_clean`. Dashboards never read it. It is dropped after each swap.
- **Replay ledger**: a warehouse table with one row per replay request.

## Live path

1. **Client sends and retries.**
   - Starts: a client has a batch of up to 100 events.
   - Does: sends the batch over HTTPS. On a timeout, 429 or 5xx, it resends the same batch with the same `event_id`s. Backoff starts at 1 s and caps at 5 minutes.
   - Keeps its data: the mobile SDK's on-device buffer, for up to 7 days.
   - If it goes wrong: a retry can arrive up to 7 days after the first copy. Dedup handles it.

2. **Collector validates and writes.**
   - Starts: a batch arrives.
   - Does:
     1. Stamps each event with `received_at`, the server's UTC time.
     2. Checks each event on its own. An event is rejected if `event_id` or `device_id` is missing, or if it is over 32 KB. The rest of the batch is kept.
     3. Appends the accepted events to the log in one durable write. Each event goes to the partition for its `event_id` hash.
     4. Returns 202 only after the log confirms the write. The body lists rejected events by index and `event_id`.
   - Keeps its data: the log.
   - If it goes wrong:
     - The log write fails or is not confirmed: return 429 or 5xx. The client resends the whole batch.
     - The log write succeeds but the response is lost: the resend makes a second copy with a new `received_at`. Dedup keeps the first copy in log order.
     - A rejected event is not stored. The 202 body is the only record of it, and clients do not retry it.

3. **Raw archive sink.**
   - Starts: new accepted events in the log. The sink reads at its own pace, with its own saved offset.
   - Does: copies each event as received, with its `received_at`, batch id and log position, to `raw/received_day=YYYY-MM-DD/`. Files are gzip-compressed and never rewritten.
   - Keeps its data: the raw archive. Each object is deleted 90 days after creation.
   - If it goes wrong: it resumes from its saved offset. Dedup and the clean write do not wait for it. The seal does. The lag alert must fire long before 14 days, when the log drops events the sink has not archived.

4. **Deduplication.**
   - Starts: the next event in a log partition. Both copies of an event are in the same partition, so the first copy is read first.
   - Does, for each event:
     1. Sets its key only if the key does not exist. The value is this event's log position. The TTL is 9 days.
     2. If the set succeeded, or the stored value equals this position, the event is a **winner**. Otherwise it is a **duplicate**.
     3. Writes its manifest row. Writing the same row again gives the same row.
     4. A duplicate stops here. It stays in the archive and manifest and is not written to `events_clean`.
     5. A winner on a day that has a cutoff, at a position past that cutoff, is **late**. It is counted and alerted, and stops here. It stays in the archive and manifest and is not written to `events_clean`. Every other winner goes on to enrichment.
   - Keeps its data: the key-value store (9 days), the manifest (90 days) and the dedup offset.
   - If it goes wrong:
     - Crash before step 1: the key is missing on restart, so the event is handled as new.
     - Crash after step 1: on restart the same position is read again. The stored value matches, so the event is still a winner.
     - Restart from the saved dedup offset. Never rewind more than 9 days, because older keys expire and an old duplicate could then win. Within 9 days a rewind cannot make a duplicate win, because a duplicate always has a later position than its winner in the same partition.
     - Key-value store down or slow: deduplication stops and does not advance its offset. Events wait in the log. The freshness alert fires.

5. **Enrichment.**
   - Starts: a winner from dedup.
   - Does: looks up the geo-IP and parses the user agent. Stamps each row with `enrichment_version`, `geoip_db_version` and `ua_parser_version`. The live path uses only stored file versions, so a replay can reproduce the output. The bot-traffic decision will go here (see Open).
   - Keeps its data: nothing. It passes the row on.
   - If it goes wrong: the winner is retried. Its key still says winner, so the retry is safe. If it keeps failing, its partition stops at that event and an alert fires. Later events in that partition wait in the log. Other partitions continue.

6. **Clean write and offset.**
   - Starts: enriched winners, collected into micro-batches at most one minute apart.
   - Does:
     1. Appends the batch to `events_clean`, in the partition for each row's `received_day`.
     2. After the warehouse confirms the batch, saves the dedup offset to the last log position read in that batch. Duplicates and late events in the batch count as read, because their manifest rows were already written in step 4.
     3. A batch with no winners saves its offset once its manifest rows are written.
   - Keeps its data: `events_clean` and the dedup offset.
   - If it goes wrong: a failed write is retried. If the process dies after the warehouse accepts a batch but before the offset is saved, the batch is read again and written twice. The seal removes these copies. Until then, dashboards can see them.
   - Freshness: the time from `received_at` until the row can be queried. Alert at 4 minutes, against the 5-minute target.

7. **Cutoff and seal.**
   - Starts: 02:00 UTC on D+1. Day D becomes closing.
   - Does:
     1. Each collector instance reports its count of pending day-D writes and, for each partition, its last day-D log position. A write is pending from its stamp until the log confirms or refuses it. The cutoff is written to the day record only when every instance reports zero pending writes. No new day-D stamp can start after midnight, so the report is final.
     2. Every 10 minutes a scheduler checks completeness. Day D is complete when the cutoff is set and, in every partition, both the dedup offset and the archive sink offset have reached the cutoff.
     3. When day D is complete, the seal builds and verifies the rebuild (steps 9 and 10 below) with the live enrichment versions. It uses only manifest winners at or before the cutoff. If the checks pass, it replaces partition D in one atomic swap (step 11), then marks day D sealed.
   - Keeps its data: partition D and the day record.
   - Why this is safe: every day-D winner at or before the cutoff is already in `events_clean`, because the dedup offset moves only after the write (step 6). Every later day-D winner is late and is held out. So the seal rebuilds rows that are already there, and no day-D row changes during the swap.
   - If it goes wrong:
     - A collector instance has pending writes: the cutoff is not set. Day D stays closing.
     - Day D is not complete: the seal does not start. Day D stays closing and the scheduler checks again every 10 minutes. The operator is alerted at 06:00 UTC if it is still not complete.
     - A seal check fails: partition D does not change. The operator is alerted.
   - Late events: a late winner is counted and alerted, and is not in `events_clean`. An operator decides whether to replay day D. A replay includes it.

## Replay path

Replay rebuilds one sealed day from the raw archive and the manifest. It never reads the live log, never changes dedup state and never touches another day. Unlike the seal, it uses all of the day's winners, so it includes late events. It runs on separate compute with its own rate limits, so live freshness is not affected. It reads only object storage and the warehouse, and it writes only the staging table and partition D.

8. **Start and check.**
   - Starts: an operator runs replay for day D with a reason and the target enrichment versions.
   - Does: refuses the request unless day D is sealed. Refuses any version whose geo-IP or user-agent files are not stored. Otherwise writes a ledger row with who asked, the day, the reason and the target versions.
   - Keeps its data: the replay ledger.
   - If it goes wrong: a refused request is recorded with its reason. Nothing else changes.

9. **Build into staging.**
   - Starts: step 8 accepts the request.
   - Does:
     1. Reads all manifest files for day D and keeps only the rows marked `winner`. Dedup decisions are not made again.
     2. For each winner, finds its raw copy by log position (partition and offset). A retry copy has a different position, so it is never used.
     3. Re-runs enrichment with the target versions and writes the rows to the staging table.
   - Keeps its data: the staging table.
   - If it goes wrong: the staging rows are discarded. `events_clean` does not change, and the operator can run replay again.

10. **Verify.**
    - Starts: staging is complete.
    - Does: checks that the staging row count equals the number of winners in day D's manifest, that `event_id` is unique in staging, and that every row has the target versions. Records counts and checksums in the ledger.
    - Keeps its data: the replay ledger.
    - If it goes wrong: any failed check stops the replay. `events_clean` does not change, and the ledger records the failure.

11. **Atomic swap.**
    - Starts: all checks pass.
    - Does: replaces partition D of `events_clean` with the staging rows in one operation, then drops the staging rows.
    - Keeps its data: partition D of `events_clean`.
    - If it goes wrong: the swap is all or nothing. Readers see the old day or the new day, never part of a rebuild. If the swap fails, the old day stays and replay can run again.

Every replay writes its day, requester, versions before and after, counts, checksums, and start and end times to the ledger. With the same day and versions, and no new winners added to day D, a replay gives the same result.

## Alerts and recovery

- Alerts go to the on-call operator. The brief does not name who that is.
- Dedup, enrichment partitions, the archive sink and the seal check recover on their own once the cause is fixed. Their retries and saved offsets resume the work.
- Replay, and any replay of a late event, needs an operator to start it.

## Retention

- Raw archive and manifests: 90 days from object creation, by lifecycle rule. Replay can reach any day still in the archive.
- Dedup keys: 9-day TTL. They are not history. Day records have no TTL.
- Log: 14 days. It is a transport buffer, used for recovery only.
- Replay ledger, stored geo-IP and user-agent files, and `events_clean`: retention is not set in the brief. See Open.

## Open

**Decisions not yet made**

- **Bot traffic.** Product has not decided. Either drop suspected bot events, or keep them with a flag column. The plan does not choose. Keeping adds a flag column to `events_clean`. Dropping needs a recorded decision that replay repeats. The manifest is written before enrichment, so the plan does not yet say where a drop would be recorded. Product decides before enrichment is built.
- **Close-time guarantee.** Step 7 waits for every day-D write to be confirmed or refused. The plan assumes this finishes within 2 hours of close. Confirm the collector's maximum write latency.
- **Late-event policy.** Either replay the day, or accept the event and report it. The plan counts and alerts, and an operator decides on replay.
- **On-call owner.** The brief does not name who receives alerts.
- **06:00 UTC alert time.** This is the plan's choice, not a brief requirement.

**Facts to confirm**

- **"First copy".** The winner is first in log order within a partition. Confirm that ordering guarantee with the log vendor. Also confirm the partition count will not change during the 9-day window, since a change would move an `event_id` to another partition.
- **Dedup TTL.** The 9-day TTL assumes the 7-day retry window starts when the first copy is received. If the mobile SDK measures it from event creation, the window may be longer. Confirm with the mobile team.
- **Warehouse.** Confirm that the warehouse can atomically replace one day's partition while the open day keeps receiving appends, and that seal and replay use that same operation.
- **Duplicate rows after a clean-write crash.** Can the warehouse merge by `event_id`? If it can, the clean write can avoid writing duplicates in the first place.
- **Offsets in the log.** Confirm the log lets a consumer save its offset only after an external write (the warehouse) is confirmed.
- **Assumptions to verify.** The key-value store supports atomic set-if-absent with a TTL at this scale. The warehouse can load micro-batches fast enough for the 5-minute target. Lifecycle rules act on creation time precisely enough for a 90-day guarantee. The collector's durable write is a replicated log acknowledgement, not an in-memory buffer. Collector clocks agree closely enough that a day boundary is the same on every instance.

**Not in the brief**

- Rejected events are not kept. Decide whether operations wants them for debugging.
