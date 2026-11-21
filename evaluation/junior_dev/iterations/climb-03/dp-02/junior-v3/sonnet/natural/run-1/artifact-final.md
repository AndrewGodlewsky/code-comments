# Clickstream ingestion plan

Website and mobile clients send batches of click and screen-view events to a new collector. The collector validates and stamps them and durably appends them to a log. From the log, an archiver copies every event to object storage, and a live loader deduplicates, enriches and loads the first copy of each event into the warehouse table `events_clean` (one partition per UTC day), queryable within 5 minutes. A replay rebuilds one closed day from the archive alone and swaps it in atomically.

## Terms

- **Collector**: the new HTTPS service that receives client batches of up to 100 events.
- **Client**: the website, or the iOS or Android SDK. The SDK keeps unacknowledged events on the device for up to 7 days. On a timeout, 429 or 5xx it resends the same batch with the same `event_id`s, backing off from 1 s up to 5 minutes. So a retry can arrive up to 7 days after the first copy. Clients never retry events the collector rejected.
- **Log**: the existing replicated append-only log (Kafka-style, 14-day retention). Each record has a log position, the pair (partition, offset).
- **Key-value store**: the existing store with per-key TTL. It holds live dedup state only.
- **Archive**: the existing object storage with a lifecycle rule. It holds every accepted event, duplicates included, exactly as received, for 90 days.
- **Warehouse**: holds `events_clean`. It can atomically replace one day partition of a table.
- **Day of an event**: the UTC day of `received_at`, the server time stamped by the collector. The client timestamp is stored as data and never used for partitioning.
- **First copy (dedup winner)**: duplicates are identified by `event_id` alone. All copies of an `event_id` go to the same log partition (hash of `event_id`), and the copy with the lowest offset there is the first received. Live and replay both use this rule. Offsets are only compared within one partition, so archive day folders do not matter. The partition count must stay fixed; if it ever changes, record a "log epoch" in the archive so replay can still order copies.
- **Dedup window**: live dedup keys live 8 days (the 7-day SDK buffer plus 1 day margin).
- **Caught up**: a consumer group is caught up when, in every partition, its committed offset equals the log's end offset.
- **Closed day**: UTC day D is closed from 02:00 UTC on D+1. No new event can belong to D after 00:00 UTC on D+1, and the extra two hours let pipeline lag drain before a replay.

## Live path

1. **Validate.** The collector checks each event in the batch on its own. It rejects an event if `event_id` or `device_id` is missing or if it is over 32 KB. Rejects are listed in the response by their index in the batch (an event with no `event_id` cannot be listed by id). The rest of the batch continues.

2. **Wrap.** For each accepted event, build an envelope with the original bytes untouched, `received_at`, the client IP, the User-Agent header and the collector instance id. IP and User-Agent must be captured now, because they cannot be recovered later and replay needs them.

3. **Store durably.** Append all envelopes to the log, keyed by `event_id`, with an idempotent producer, waiting for acknowledgement from all replicas. Only then return 202, with the rejected events listed. Never return 202 for a batch that is not stored.

4. **Archive.** A dedicated consumer group reads every envelope and writes it to the archive, in objects laid out by day, then log partition and offset range. Each record keeps its partition and offset. It commits log offsets only after the object write succeeds. A lifecycle rule expires objects at 90 days.

5. **Read for loading.** A second consumer group (the live loader) reads the log, one consumer per partition, in offset order, in micro-batches about every 60 seconds.

6. **Dedup.** For each event, run set-if-absent on key `event_id` in the key-value store, with the event's log position as value and a TTL of 8 days.
   - Key absent: the event is the winner.
   - Key present with the same log position: the event is also the winner. This is a restarted loader re-reading an event it had already claimed.
   - Key present with a different position: the event is a duplicate and is dropped from `events_clean`. It stays in the archive. This also covers a retry arriving on a later UTC day than the winner. The winner's row stays in its own day's partition.

7. **Enrich.** Apply geo-IP lookup and User-Agent parsing. Stamp each row with the enrichment code version and geo-IP database version, so replay differences can be explained. Bot handling is not decided here (see Open questions).

8. **Load.** Write the winners to `events_clean`, each into the partition of its own day. Just after midnight the loader still writes some rows into the previous day's partition (received 23:59, loaded 00:03). That is correct. Load each micro-batch idempotently by `event_id` so a restart does not double-insert. Commit log offsets only after the load succeeds.

9. **Freshness.** Budget: collector to log under 1 s, micro-batch wait up to 60 s, enrich and load under 2 min. Alarm if p99 end-to-end lag (`received_at` to queryable) exceeds 3 minutes.

## Replay path

10. **Trigger.** An operator asks to rebuild day D, naming the enrichment code version that contains the fix. The tool starts only if all of these hold, and otherwise refuses:
    - D is closed (now is at or after 02:00 UTC on D+1).
    - Both the loader and the archiver are caught up, measured against log end offsets read after 02:00 UTC on D+1. Every record of D was appended before then, so this means all of D is processed.
    - D and its 8-day lookback are inside the 90-day archive window.
    - No other replay of D is running (one lock per day).

11. **Isolate.** Run on separate compute that reads only the archive, never the live log or key-value store. Cap warehouse and storage read throughput so live ingestion is unaffected. Write to a staging table or partition, never the live one.

12. **Rebuild dedup.** Read the archive for D and the 8 days before it. For each `event_id`, take the copy with the lowest log position. Keep the event for D only if that copy has `received_at` in D. An event first seen on an earlier day, whose retry arrives on D, is dropped, as live did. This is deterministic, so replaying D never changes which events belong to another day.

13. **Re-enrich** the winners with the chosen code version and write them to staging.

14. **Validate.** Compare staging with the live partition and produce a diff report. The `event_id` sets and row counts should match, with differences only in enriched columns. If the id sets differ, stop. The operator reviews the report and may explicitly confirm, after which the swap proceeds with the staged data, since the archive is the source of truth. Such a difference usually means live lost or wrongly dropped events, for example after key-value store loss, which is what the rebuild repairs.

15. **Swap.** Use the warehouse's atomic single-partition replace to put the staged data into day D. Dashboards see the old complete day or the new complete day, never a partial one. Nothing else is needed afterwards: live dedup keys depend only on `event_id`, so later retries are still dropped, and the loader's keys and offsets are untouched. Record the run id, code version and counts.

## When things fail

| Where | What happens |
|---|---|
| Event malformed | Rejected individually and listed in the 202 response. Client does not retry it. |
| Log append fails or times out | Collector returns 503, or 429 under load. Client resends the whole batch. Copies from a half-failed attempt are removed by dedup. |
| Archiver write fails | Offset is not committed, so it retries. Alert if lag exceeds 1 hour. |
| Loader crashes mid-batch | Restarts from its last committed offset. Its own claimed keys are recognised by log position, so events are loaded again without being dropped. The idempotent load avoids double-inserts. |
| Key-value store lost | Pause the loader rather than load without dedup. Wait until the archiver has reached the loader's committed position. From the archive, for the last 8 days and only up to that position, take each `event_id`'s lowest log position and write it as the key's value, with TTL of 8 days minus the age of that copy. Resume from the committed offset. |
| Replay fails or is aborted | The live partition is untouched. Re-running is safe. |
| Replay id sets differ from live | Stop until an operator confirms (step 14). |

## Monitoring

Collector 5xx and 429 rates. Consumer lag for archiver and loader. End-to-end freshness. Dedup rate (a jump may mean a client retry storm, a drop may mean key-value store loss). Daily reconciliation of the archive's winner count against the `events_clean` count for the closed day.

## Tests

- Retry after a crash between the key claim and the load.
- A duplicate that arrives 7 days later.
- Events spanning the UTC midnight boundary, including one loaded after midnight.
- Replay output identical to live when the enrichment code is unchanged.
- Replay running while live traffic continues.
- A half-built replay never visible to a dashboard.

## Open questions

- **Suspected bot traffic: drop, or keep with a flag. Product has not decided and this plan does not choose.** It affects only one stage, after dedup and enrichment: whether bot rows reach `events_clean`, and whether the table needs a flag column. The archive keeps everything either way, so the choice can later be applied to existing days with a replay. Bot classification is not wired in until Product decides, and the interim behavior is not the answer. Product input is needed before that stage ships and before any schema change to `events_clean`.
- Where enrichment code versions are stored, and how the replay tool fetches and runs a pinned version, is not specified.
- The exact enriched columns (geo and user-agent fields) are not listed yet.
- How the warehouse makes a micro-batch load idempotent by `event_id` (upsert, or delete-then-insert in one transaction), and whether that is safe in a partition being queried, is not known. The brief only guarantees atomic replace of a whole day partition.
- Clock skew between collector instances could make offset order differ slightly from `received_at` order near midnight. The plan ignores this and treats offset order as "first received".
