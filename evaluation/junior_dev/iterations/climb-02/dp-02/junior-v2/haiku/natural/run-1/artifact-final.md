# Clickstream ingestion plan: `events_clean`

## Summary

Click and screen-view events from the website and the iOS and Android apps pass through a collector, a replicated log, a raw archive, a decide-and-enrich stage and a loader into `events_clean`. That table is partitioned by the UTC day of `received_at`. Two rules shape the design:

- The **raw archive** is the system of record for 90 days. The log keeps only 14, so replay reads the archive, never the log.
- Each dedup decision is **recorded once** in a decision ledger. Replay reuses those decisions and never touches the live dedup store.

## Terms

- **Envelope.** An event's exact received bytes plus collector metadata (`envelope_id`, `received_at`, `batch_id`, `collector_id`). Bytes are never re-serialized. Every publish attempt gets a new `envelope_id`.
- **Winner and duplicate.** For each `event_id`, the first envelope that the decide stage (step 6) processes is the winner. Every later envelope with that `event_id` is a duplicate. All copies of an `event_id` go to the same log partition, so decide sees them in one order (open question 7).
- **Received day.** The UTC date of `received_at`. It decides the partition and which replay covers an envelope.

## Live path

1. **Client batching.** Each SDK sends batches of up to 100 events over HTTPS. Each event has a UUID `event_id`, a `device_id` and a client timestamp. Retries reuse the same `event_id`s and back off exponentially from 1 s to 5 min. Unacknowledged events stay in an on-device buffer for up to 7 days, so a retry can arrive up to 7 days after the first copy. The plan assumes those 7 days run from creation or first send (open question 2).

2. **Collector.** A new HTTPS service that keeps no state, so any instance can take any batch. The replicated log is the only durable store. For each batch it:
   a. stamps `received_at` from server UTC time on arrival;
   b. validates each event (step 3);
   c. publishes each accepted event to the log as an envelope, keyed by `event_id`, with acks from all in-sync replicas;
   d. returns **202** only after every publish is acknowledged, listing the rejected events in the body.

   Stamping and publishing must finish within the write deadline `T_w` (proposed 30 s, open question 3). Otherwise the collector returns 5xx.

3. **Per-event validation.** Each event on its own must have `event_id` and `device_id`, and be 32 KB or less. Rejected events are listed in the 202 body with their batch index and a reason. The rest of the batch is accepted. Clients never retry rejected events.

4. **Failed write.** If any publish fails or misses `T_w`, the collector returns 5xx for the whole batch, valid events included. Envelopes already published stay in the log, and the archive keeps them. The client resends the same `event_id`s and the collector makes new envelopes. Step 6 decides by `event_id` alone, so earlier copies win or lose like any other copy.

5. **Raw archive.** Group A reads the log and writes envelopes byte-for-byte to object storage, in files partitioned by `received_at` UTC day and hour, flushed about every 60 s. Group A commits its offset only after a file is complete. The archive keeps every envelope that reached the log, duplicates and failed-batch envelopes included, for 90 days. It is the input to replay.

6. **Decide and enrich.** Group B reads the log in order, one envelope at a time.
   a. **Decide.** Run one atomic set-if-not-exists on the key-value store, keyed by `event_id`, with value `winner_envelope_id` and a TTL of 8 days (the 7-day retry window plus one day of margin). Set the TTL only on first insert, so duplicates never extend it.
      - Set succeeds: this envelope is the winner.
      - Key exists with a different `envelope_id`: this envelope is a duplicate.
      - Key exists with this `envelope_id` (a redelivery): treat it as the winner again.
      - Store unavailable: stall and alert. Never guess, never fail open.
   b. **Ledger.** Write one ledger row for the envelope (see Ledger below).
   c. **Enrich, winners only.** Run a geo-IP lookup and user-agent parsing. Record `enrichment_version`, the geo database version and the user-agent parser version. The bot-traffic check is a placeholder that passes every winner through unchanged until product decides (open question 1). Publish the enriched row to the `enriched` log topic, keyed by `event_id`.

   Group B commits its offset only after the ledger file and the `enriched` publishes for those envelopes are acknowledged. An enrichment error stalls the group and alerts, the same as a store outage. Nothing is dropped.

   **Restarts.** After a crash, uncommitted envelopes are redelivered and go through step a again. Repeated ledger rows and repeated `enriched` rows are harmless: ledger rows are keyed by `envelope_id`, and the loader MERGEs on `event_id`.

   **Ledger.** Append-only object storage, partitioned by `received_day`, with 90-day retention from object creation. Each row holds `envelope_id`, `event_id`, `received_at`, `received_day`, `decision` (winner or duplicate) and `winner_envelope_id` (its own `envelope_id` for a winner).

7. **Warehouse loader.** Group C is a micro-batch loader that runs every 1 to 2 minutes. It reads the `enriched` topic and, for each `received_day` in the batch, MERGEs the winners into that day's partition of `events_clean`, matching on `event_id`. It commits its offset only after the MERGEs commit. A replayed batch does not insert twice. If the warehouse is down, group C stalls and lag builds in the log.

8. **Freshness.** The budget runs from collector receipt to queryable row: batch wait under 1 min, decide and enrich under 1 min, load under 2 min, leaving headroom to 5 min. Track p95 and p99. Alert at 3 min, page at 5 min.

9. **Reconciliation.** Hourly, per `received_day`: the archived envelope count must equal the ledger row count, and the ledger winner count must equal the distinct `event_id` count in `events_clean`. Nightly, scan `events_clean` for `event_id`s in more than one partition; the expected count is zero. A non-zero count means the TTL expired too early or decide is wrong, and the day needs a replay. This check also catches a winner that a swap removed (step 21).

## Day close (02:00 UTC on D+1)

10. **Collector bound.** Any envelope stamped with day D is durable in the log within `T_w` of its stamp. So once 02:00 plus `T_w` has passed on D+1, every envelope stamped before 02:00 is in the log.

11. **Close watchdog.** A scheduled job, separate from groups A, B and C so that a stuck group does not stop it. Starting at 02:00 plus `T_w` on D+1, it runs every 10 minutes until both checks pass. On its first run it records the end offset of each raw log partition and keeps them for later runs. On each run, after a lag margin (open question 3), it checks in this order:
    a. Groups A and B have committed past the recorded offsets in every partition, and the archive files covering them are flushed.
    b. Group C has committed through the current end of the `enriched` topic. This runs after a, so every `enriched` row for those envelopes already exists.

    If both pass, the watchdog writes the close record (step 12) and stops. If either fails, it writes nothing, alerts with the failing check, and runs again at the next interval. D stays open and live processing continues.

12. **Close record.** Counts per `received_day`, watermarks, and the manifest of raw and ledger objects for D. D is **closed**, and eligible for replay, only when this record exists.

13. **Late envelopes.** An envelope stamped D that is archived after the close record means the `T_w` bound was broken. It is still archived, ledgered and loaded into D by the live path, with the live enrichment version. A later replay of D corrects it. The archived count for D then no longer matches the close record, which is how operators see it.

## Replay (rebuild one closed UTC day)

14. **Request.** An operator requests a replay of day D with a reason and a target enrichment version. The replay is a separate job with its own compute and quotas.

15. **Preconditions.** Refuse unless D has a close record (step 12) and the current time is before the replay deadline, D+90 days minus a safety margin (open question 6). Raw objects are removed 90 days after creation, and creation is never before `received_at`, so raw data for D exists until at least D+90.

16. **Freeze the inputs.** List the raw and ledger objects for D and record them as an immutable manifest with a hash. Later files do not change this run.

17. **Checks before any write.** Verify that every winner row for D in the ledger has a raw envelope with the same `envelope_id`, that no `event_id` has two winners, and that each raw envelope matches its stored checksum. Any failure aborts the replay, and nothing becomes visible.

18. **Build the replay input.** Join the raw envelopes in the manifest to the winner rows for D. This is exactly what the live path decided. Replay does not re-run dedup, read the key-value store or read the log. Duplicates are ignored. A duplicate that arrives on a later day is ledgered on its own day, marked duplicate, so it is in neither day's input. Its winner, on the earlier day, owns the event.

19. **Enrich into staging.** Re-parse each event and re-run enrichment with the pinned target geo database and user-agent parser versions. Write to a staging partition keyed by run ID, never to `events_clean`. Rate-limit staging writes so they do not compete with the live loader.

20. **Validate staging.** The row count equals the winner count from step 17. The schema matches `events_clean`. `enrichment_version` equals the target on every row. Null rates and distributions are within agreed bounds of the previous version, and the operator reviews any differences. A random sample is spot-checked.

21. **Swap guard and atomic swap.** Check that partition D of `events_clean` holds the same number of distinct `event_id`s as the manifest has winners. A difference means a winner was loaded after the freeze, so abort and restart from step 16. If the check passes, replace partition D with the validated staging partition in one warehouse operation, so dashboards see either the old day or the new day, never a partial rebuild. Keep the previous partition for rollback. The live loader is not paused, so a late MERGE can land between the check and the swap, depending on warehouse ordering (open question 5). Reconciliation (step 9) catches a missing winner, and a replay fixes it. A MERGE after the swap is an ordinary straggler with the live enrichment version, which the next replay corrects.

22. **Audit and cleanup.** Record the run ID, D, target enrichment version, manifest hash, input and output counts, operator and timestamps. Drop the staging partition once the swap is verified.

## Storage and retention

| Store | Contents | Retention |
|---|---|---|
| Replicated log | Raw envelopes; `enriched` topic | 14 days. Alert when archive copy lag exceeds 1 day. |
| Object storage (raw archive) | Raw envelopes, by day and hour | 90 days from creation (never before `received_at`) |
| Key-value store (dedup) | `event_id` to `winner_envelope_id`; no event content | 8 days, per-key TTL, set on first insert only |
| Object storage (ledger) | One row per envelope with its decision | 90 days from creation |
| Warehouse `events_clean` | Winners only, enriched | Per product policy |
| Warehouse staging | Replay output | Until swap is verified; never read by dashboards |

Rejected events are not accepted, so they are not kept. Rejection counts are logged for operations.

## Failure handling

- **Collector or log unavailable.** The collector returns 5xx and clients back off. The mobile buffer covers 7 days, so capacity planning must keep the collector ahead of the 7-day retry tail.
- **Key-value store, enrichment or warehouse unavailable.** The affected group stalls and alerts. Nothing is decided or loaded wrongly. Lag builds in the log, which keeps 14 days.
- **Archive falls behind 14 days.** Log data is lost. Alert long before this point.
- **Close check keeps failing.** The watchdog keeps retrying (step 11). D stays open and no replay of D can start (open question 8).

## Verification

- Duplicate copies arriving 0, 1, 7 and 8 days after the first copy. Expect duplicates at 0, 1 and 7 days. At 8 days the key may have expired, so the late copy can become a new winner; reconciliation (step 9) must catch it.
- Kill group B between the key-value write and the ledger or `enriched` write, and kill group C between MERGE and commit. Confirm no duplicate rows in `events_clean`.
- A replay of a closed day with no enrichment change produces a partition identical to the live output. A replay with a changed enrichment version changes only the enrichment columns and the `enrichment_version` value.
- A replay under full live load does not move live freshness p99 beyond the alert threshold.
- Freshness and reconciliation dashboards show zero unexplained differences for a full week before go-live.

## Open questions

1. **Bot traffic (not decided; do not choose).** Product must decide whether suspected bot events are dropped or kept with a flag in `events_clean`. The archive keeps every envelope either way, so the rule can later be applied to closed days by replay. Until then, step 6c is a placeholder.
2. **Retry window.** Confirm with the mobile SDK owners that the 7 days run from creation or first send. The plan uses an 8-day TTL. If the buffer can run longer, raise the TTL or move dedup to a durable store.
3. **Write deadline `T_w` and lag margin.** Set `T_w` (proposed 30 s), confirm the collector can enforce it under load, and set the close-check lag margin from it (step 11).
4. **Durable write.** Confirm that a replicated log with acks from all in-sync replicas meets "durably stored" for the 202 response.
5. **Warehouse.** Confirm that MERGE within a partition at 1 to 2 minute batches fits 5-minute freshness, that a single-partition replace works at the size of a day, and whether a MERGE and a partition replace are serialized (step 21).
6. **Replay deadline.** Confirm the operational deadline for replay. It must sit comfortably inside the D+90 raw retention window.
7. **Ordering of "first".** The plan defines "first" as the decide stage's processing order per `event_id` partition. Confirm that this matches the product's "first copy we receive".
8. **Close watchdog limits (not decided).** The brief sets no limit on how long the close check retries, and no alert recipients. Product or operations must decide when a human is paged for a day that will not close, and who receives the alert. Until then the watchdog keeps retrying and D stays open.