# Clickstream ingestion plan

Today there is no clickstream pipeline. This plan builds one. Websites and iOS and Android apps send batches of click and screen-view events to a new collector. The collector validates them, stamps each with server time and appends them to a replicated log. From the log, one consumer group archives every event unchanged to object storage (kept 90 days). A second group drops duplicates, enriches the rest and loads them into the warehouse table `events_clean`, one partition per UTC day, within 5 minutes. When an enrichment bug is fixed, an operator can replay one closed day. Replay rebuilds that day from the raw archive only and swaps it in atomically. It is shaped this way because clients retry for up to 7 days, so duplicates are normal. The 14-day log is too short to be the source of truth for replay, so the archive is.

## Terms

- **Event:** one click or screen view. It has a client-made `event_id` (UUID), a `device_id` and a client timestamp. Clients send up to 100 per batch over HTTPS.
- **Day:** the UTC day of the collector's `received_at`, never of the client timestamp. It decides the partition and which replay covers the event.
- **The log:** our existing replicated, append-only, Kafka-style log (14-day retention; the product is not named). Records with the same key go to the same partition and are read in order. A write is safe once all in-sync replicas (copies caught up with the leader) acknowledge it.
- **Offset:** a record's position in its log partition. `(partition, offset)` identifies a record, and a lower offset in a partition means it arrived earlier.
- **Duplicate and winner:** copies of one `event_id` are duplicates. The winner is the copy with the lowest `(partition, offset)`. It is the one kept in `events_clean`. The others stay only in raw.
- **KV store:** our existing key-value store with per-key TTL and an atomic set-if-absent (write only if the key is missing). The product is not named.
- **Warehouse:** our existing analytics warehouse. It can atomically replace one day partition of a table. `events_clean` is the clean table.
- **Raw archive:** every accepted event, duplicates included, in object storage with its envelope, under `raw/received_date=YYYY-MM-DD/`.
- **Envelope:** what the collector adds to an event: `received_at`, client IP, user-agent header and collector ID. The original body is kept byte for byte.
- **Sealed day:** a day whose raw prefix has an empty `_SEALED` marker, meaning the archive has everything for it.
- **Staging:** a scratch table or partition where replay builds a day before it is published.

## Assumptions to confirm

- A warehouse append can be made idempotent, by a deterministic file manifest or by a merge on `event_id`. Step 7 depends on this.
- Client IP and user agent are available at the collector. They must be stored raw, or replay cannot re-run geo-IP and user-agent parsing.

## Open decision (product): suspected bot traffic

Drop it, or keep it with a flag? Not decided here, and the plan works either way. The raw archive keeps everything regardless. Only step 8 and replay step 14 change.
- **Flag:** add a nullable `is_suspected_bot` column to `events_clean`.
- **Drop:** filter after deduplication.

Either way, the `event_id` is still recorded in the KV store, so the winner stays stable. Do not build the bot classifier until this is decided.

## How the system runs

### Live path

1. **Collector validation.** Starts when a batch arrives.
   - For each event, check that `event_id` and `device_id` are present and the event is 32 KB or less.
   - Rejected events are listed in the response (by `event_id`, or by batch index if the ID is missing) and counted in a metric. They are not stored. The rest of the batch is still accepted. Clients never retry rejected events.
   - Add no other rejection rules, such as UUID format, without a decision.

2. **Stamp the envelope.** The collector adds `received_at` (server UTC), client IP, user-agent and collector ID to each accepted event. The event's day is fixed from here on.

3. **Durable write, then 202.** The log keeps the data.
   - Append each event to the log, keyed by `event_id`, so every copy of an event lands in the same partition. Wait for all in-sync replicas to acknowledge.
   - Return 202 only after every accepted event in the batch is acknowledged.
   - Partial failure: return 5xx. The client resends the whole batch, and copies already appended become duplicates. That is fine, since duplicates are kept in raw and dropped downstream. Under overload, return 429.
   - The collector does not deduplicate, because retries must be stored.

4. **Raw archive sink.** Raw storage keeps the data.
   - A separate consumer group writes every log record, unchanged, to `raw/received_date=YYYY-MM-DD/…` (date from `received_at`), keeping each record's `(partition, offset)`.
   - A lifecycle rule expires objects after 91 days (90 days plus a one-day margin).
   - The sink writes `_SEALED` for a day once every partition's archive position has passed the end of that day.
   - Failure: if one partition's archive is stuck, no marker is written, replay of that day is refused, and an alert fires when sink lag exceeds a few hours. Lag must stay far below the log's 14 days.

5. **Live deduplication.** A consumer group reads the log in micro-batches of about 1 minute. Each partition is read by one consumer at a time, in offset order. The KV store keeps the data.
   - For each record, do an atomic set-if-absent: key `event_id`, value `(partition, offset)`, TTL 8 days (7-day retry window plus a margin).
   - If the key was absent, or already holds this record's own `(partition, offset)`, the record is the winner and moves on.
   - Otherwise it is a duplicate. It is dropped from the clean path, counted in a metric, and stays in raw.
   - Why the own-offset check: after a crash the same record is read again. Without the check it would look like a duplicate of itself, and an event marked seen but not yet loaded would be lost.
   - Why live and replay pick the same winner: all copies share a partition and are read in offset order, so the first copy the KV sees is the lowest offset.

6. **Enrichment.** For winners only, run geo-IP lookup and user-agent parsing, and stamp each row with an `enrichment_version`.

7. **Warehouse append.** The warehouse keeps the data.
   - Split each micro-batch by the day of `received_at`, since a batch near midnight can hold two days. Load each part into that day's partition of `events_clean`.
   - Loads are idempotent, keyed by `(partition, offset range, day)`. Record the key with the load and skip a part whose key is already recorded.
   - Commit consumer offsets only after all parts are loaded or skipped by the fence in step 9. If a load fails, the batch is read and loaded again. A slow load appears as consumer lag.
   - Latency budget: collector plus log under 10 s, micro-batch about 60 s, enrichment and load under 2 min. Alert on consumer lag above 3 minutes.

8. **Bot handling hook (open).** An empty placeholder between steps 5 and 7 until product decides.

9. **Closed-day fence.** Day D closes at 02:00 UTC on D+1.
   - Before each load, the writer compares the current time with the close time of the part's day. If the day is closed, it does not append that part.
   - A fenced part is counted in a metric and treated as handled, so offsets commit and the consumer does not stall.
   - Such events are safe in raw, and a replay of D adds them. A writer lagging past close raises an alert, because the 5-minute target is already broken. Replay is the recovery.

### Replay

Replay reads only the raw archive. It never touches the KV store, the log consumers or live warehouse writes, so it cannot slow live ingestion or change live deduplication state.

10. **Trigger and eligibility.** An operator asks for a replay of day D through a tool or command (not yet chosen). The request is accepted only if all of these hold:
    - now is at or after D+1 02:00 UTC;
    - D is sealed (step 4);
    - D and its 8-day lookback are still inside the 91-day raw retention, so replays work for days up to about 80 days old;
    - no other replay for D is running.

    On acceptance, take a per-day lock and record the run in a replay ledger (operator, code version, enrichment version). A rejected request returns the list of failed conditions.

11. **Build the seen-ID set.** A batch job scans raw for D-8 through D-1 and writes every `event_id` as files in scratch space in object storage. This stands in for the live KV state.

12. **Deduplicate day D.** Read raw for D. For each `event_id` keep the record with the lowest `(partition, offset)`. Drop it if its `event_id` is in the seen-ID set, because an earlier day won. Copies arriving after D are not a concern: live drops them, and a replay of those days drops them the same way.

13. **Re-enrich.** Run the fixed geo-IP and user-agent code on the survivors, using the stored IP and user-agent. Stamp the new `enrichment_version`.

14. **Write to staging.** Write the result to staging, not to `events_clean`. The job runs on separate compute and reads only object storage. Apply the bot rule here too, once decided.

15. **Validate.** The job runs this itself once staging is written. Day D is closed and sealed, so the live partition no longer changes. Compare staging with the live partition for D:
    - every live `event_id` is in staging (replay changes enrichment, not membership);
    - staging may have extras, which are events live missed by lagging past close. Row count must equal live rows plus extras;
    - only enrichment columns differ;
    - no duplicate `event_id`.

    The extras count and list go into the ledger entry and the tool's output. If a check fails, the job stops, leaves the live partition untouched, marks the ledger entry failed with the failed checks, releases the lock and shows the failure in the tool's output.

16. **Publish atomically.** Use the warehouse's atomic replace to swap day D in `events_clean` for the staging data. Dashboards see either the old complete day or the new complete day. Mark the ledger entry done and release the lock.

### What happens when things fail

| Where | What happens |
|---|---|
| Event malformed | Rejected, listed in the response, not retried |
| Log write partly fails | 5xx; client resends the batch; extra copies are duplicates |
| Overload | 429; client backs off and resends |
| Archive stuck | No `_SEALED`; replay refused; lag alert |
| Consumer crash | Batch re-read; own-offset check and idempotent load make it safe |
| Warehouse load fails or is slow | Offsets not committed; batch retried; lag alert at 3 min |
| Day already closed at load | Part skipped and counted; events stay in raw; replay adds them |
| Replay fails or is cancelled | `events_clean` unchanged; rerun is safe, since the job is a pure function of raw |

## Checks before launch

- A retry crossing midnight UTC: copy A on day D, copy B on D+1. B is dropped live, and a replay of D+1 also drops it.
- A micro-batch with events from two days: both parts load once, and a re-run loads nothing twice.
- A 7-day-late retry against KV TTL expiry.
- A replay at live peak: check consumer lag.
- Kill the live consumer between KV set and warehouse load: no event is lost.
- KV memory for 8 days of `event_id`s at peak volume.

## Open questions

- How the operator requests a replay (tool, command or API), and how a failed replay notifies them beyond the tool's output (for example paging), are not chosen.
- Which batch engine runs replay, and how big the 8-day seen-ID set is at peak, are not known. Size it from real volume.
- The KV product is not stated, so its set-if-absent and TTL behavior must be confirmed. If KV state were lost, live could keep a later copy as the winner. Replay of that day corrects it.
