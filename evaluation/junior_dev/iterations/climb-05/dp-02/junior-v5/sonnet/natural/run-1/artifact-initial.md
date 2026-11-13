# Clickstream ingestion plan

## Decisions that shape the plan

- **Partition key.** The collector keys the log by `event_id`, so every copy of an event lands in the same log partition. "First copy wins" means the lowest `(partition, offset)` for that `event_id`. Live and replay both use this one rule.
- **Raw archive.** Object storage holds every accepted event, duplicates included, with its envelope. The 14-day log can't cover 90-day retention or late replays, so the archive is the source for replay and the log is not.
- **Replay isolation.** Replay reads only the raw archive. It never touches the live KV store, the log consumers or the live warehouse writes. It publishes by one atomic partition replace.

## Assumptions to confirm

- A warehouse append can be made idempotent, either by loading a deterministic file manifest or by a merge on `event_id`. Step 7 depends on this.
- Enrichment inputs (client IP, user agent) are available at the collector. They must be stored raw, or replay cannot re-run geo-IP and user-agent parsing.

## Open decision (product): suspected bot traffic

Drop it, or keep it with a flag? Not decided here.

The plan works either way. The raw archive keeps everything regardless. Only step 8 and the final replay step change:
- **Flag:** add a nullable `is_suspected_bot` column to `events_clean`.
- **Drop:** filter after deduplication.

Whichever is chosen, the event's `event_id` is still recorded as seen in the KV store, so first-copy-wins stays stable. Do not build the bot classifier until this is decided.

## Live path

1. **Collector validation.**
   - For each event in a batch, check that `event_id` and `device_id` are present and that the event is 32 KB or less.
   - Rejected events are listed in the response, by `event_id` or by batch index if the ID is missing. The rest of the batch is still accepted.
   - Rejected events are not stored. Count them in a metric.
   - Add no other rejection rules, such as UUID format, without a decision.

2. **Stamp the envelope.** For each accepted event the collector adds:
   - `received_at` (server UTC time);
   - client IP;
   - user-agent header;
   - collector ID.

   The original event body is kept byte-for-byte. The UTC day of `received_at` is the event's day from here on. The client timestamp is never used for partitioning.

3. **Durable write, then 202.**
   - Append each event to the log, keyed by `event_id`, and wait for acknowledgement from all in-sync replicas.
   - Return 202 only after every accepted event in the batch is acknowledged.
   - On a partial failure, return 5xx. The client resends the whole batch. Copies that were already appended become duplicates, which is acceptable, because duplicates are kept in raw and dropped downstream.
   - Under overload, return 429.
   - Do not deduplicate in the collector. Retries must be stored, because the requirement is to keep duplicates.

4. **Raw archive sink.**
   - A separate consumer group writes every log record to object storage, unchanged.
   - Path: `raw/received_date=YYYY-MM-DD/…`, where the date comes from `received_at`.
   - Each record keeps its log `(partition, offset)`.
   - Set a lifecycle rule to expire objects after 91 days, which gives a one-day margin over the 90-day minimum.
   - Alert if sink lag exceeds a few hours. It must stay far below the log's 14-day retention.
   - Each day's prefix is sealed by writing a marker once every partition's archive position has passed the end of that day.

5. **Live deduplication consumer.**
   - A consumer group reads the log in micro-batches of about 1 minute.
   - For each record, do an atomic set-if-absent in the KV store:
     - key: `event_id`;
     - value: `(partition, offset, received_at day)`;
     - TTL: 8 days (the 7-day retry window plus a 1-day margin).
   - If the key was absent, or exists with this record's own `(partition, offset)`, the record is the winner and moves on.
   - Otherwise the record is a duplicate and is dropped from the clean path (it stays in raw).
   - The "own offset" check makes reprocessing after a crash safe. Without it, an event marked seen but not yet written would be lost.

6. **Enrichment.** For winners only, run geo-IP lookup and user-agent parsing. Stamp each row with an `enrichment_version`, so replays after a fix can be told apart.

7. **Warehouse append.**
   - Load each micro-batch into the `events_clean` partition for its `received_at` UTC day, with an idempotent load keyed by the batch's `(partition, offset range)`.
   - Commit consumer offsets only after the load succeeds.
   - Latency budget: collector plus log under 10 s, micro-batch about 60 s, enrichment and load under 2 min. That leaves slack inside the 5-minute target.
   - Alert on consumer lag above 3 minutes.

8. **Bot handling hook (open).** Placeholder between steps 5 and 7, empty until product decides. See the open decision above.

9. **Closed-day fence.**
   - Once a day is closed (02:00 UTC the next day), the live writer stops appending to its partition.
   - A live writer that lags past close raises an alert, because the 5-minute target is already broken. Replay is the recovery.

## Replay

10. **Trigger and eligibility.** An operator requests replay for one UTC day D. The request is accepted only if all of these hold:
    - now is at or after D+1 at 02:00 UTC;
    - the raw prefix for D is sealed (step 4);
    - D and its 8-day lookback are still inside the 91-day raw retention. In practice replays work for days up to about 80 days old;
    - no other replay for D is running. Take a per-day lock and record the run in a replay ledger, with the operator, code version and enrichment version.

11. **Build the set of already-seen IDs.**
    - A batch job scans raw for D-8 through D-1 and extracts the `event_id` of every event in that window.
    - This replaces the live KV state, and the job never reads or writes the live KV.

12. **Deduplicate day D.**
    - Read raw for D.
    - For each `event_id`, keep the record with the lowest `(partition, offset)`.
    - Drop it if its `event_id` is in the step-11 set, since an earlier day won.
    - Copies that arrive after D are not a concern. Live drops them in D+1 and later, and a replay of those days drops them the same way via lookback.

13. **Re-enrich.** Apply the fixed geo-IP and user-agent code to the surviving events, using the stored IP and user-agent from the envelope. Stamp the new `enrichment_version`.

14. **Write to staging.**
    - Write the result to a staging table or partition, not to `events_clean`.
    - The job runs on separate compute and reads only from object storage, so it cannot slow live ingestion or touch live deduplication state.
    - Apply the step 9 bot rule here too, once decided.

15. **Validate before publish.** Compare staging to the live partition for D:
    - the `event_id` sets must match (replay changes enrichment, not membership);
    - row counts must be equal;
    - only enrichment columns may differ;
    - no duplicate `event_id`.

    If a check fails, stop and leave the live partition untouched.

16. **Publish atomically.**
    - Use the warehouse's atomic replace of the single day partition: swap D in `events_clean` for the staging data.
    - Dashboards see either the old complete day or the new complete day, never a half-built one.
    - Mark the ledger entry done and release the lock.

17. **Failure and rerun.** A failed or cancelled replay leaves `events_clean` unchanged. Rerunning is safe, because the job is a pure function of the raw archive and nothing live is mutated.

## Checks before launch

- Test a retry that crosses midnight UTC. Copy A arrives on day D, copy B on D+1. B is dropped live, and a replay of D+1 also drops it.
- Test a 7-day-late retry against KV TTL expiry.
- Run a replay while live traffic is at peak. Check consumer lag.
- Kill the live consumer between KV set and warehouse load. Confirm that no event is lost.
- Check KV memory for 8 days of `event_id`s at peak volume.
