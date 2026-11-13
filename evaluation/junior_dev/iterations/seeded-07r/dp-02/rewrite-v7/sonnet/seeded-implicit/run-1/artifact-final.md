# Clickstream ingestion plan

Website, iOS and Android clients send click and screen-view events to a new collector. The collector stamps each event and writes it to a log. From the log, one consumer archives every event untouched and another deduplicates, enriches and loads the warehouse table `events_clean` (one partition per UTC day) within 5 minutes. A separate replay job rebuilds a closed day from the archive, because the archive keeps exactly what we received and the log only keeps 14 days.

## Terms

- **Event**: one click or screen view. It carries a client-generated `event_id` (UUID), a `device_id` and a client timestamp.
- **Batch**: up to 100 events sent in one HTTPS request.
- **`received_at`**: server time stamped by the collector. An event belongs to the UTC day of `received_at`, never of the client timestamp. That day decides its partition and which replay covers it.
- **Raw log**: the replicated append-only log (Kafka-style, 14-day retention).
- **Archive**: raw events in object storage, in hourly files, with a lifecycle rule that deletes them after 90 days.
- **KV store**: the key-value store with per-key TTL. It remembers which `event_id`s the live path has already seen.
- **Closed day**: a UTC day that ended at least 2 hours ago, so its last events have been archived and loaded. A day closes at 02:00 UTC the following day.
- **Staging table**: a scratch copy of one day's partition, built during replay.

## Rules that apply to several steps

- Duplicates are identified by `event_id` alone. The first copy we receive wins and later copies are dropped from `events_clean`.
- Every accepted event, duplicates included, is kept exactly as received for 90 days (in the archive).
- A malformed event has no `event_id`, has no `device_id`, or is over 32 KB. Clients never retry rejected events.

## Live path

1. **SDK sends.** Web, iOS and Android SDKs send batches to the collector. On a timeout, 429 or 5xx they resend the same batch with the same `event_id`s, backing off exponentially from 1 s up to 5 minutes. The mobile SDK keeps unacknowledged events in an on-device buffer for up to 7 days, so a retry can arrive up to 7 days after the first copy. This is why duplicates exist.
2. **Collector accepts.** For each batch it checks every event, rejects malformed ones one at a time, stamps `received_at` on the rest, and writes them to the raw log. It returns 202 only after the log confirms the write is replicated. The response lists the rejected events, and the rest of the batch is still accepted. Rejected events are also written to a reject bucket for inspection. If the log write fails or the collector is overloaded, it returns 5xx or 429 and the client retries the whole batch. Duplicates from such retries are removed in step 4.
3. **Archiver stores.** It reads the raw log and writes every event, duplicates included, to the archive. Each hourly file covers one UTC hour of `received_at`, so no file spans two days. It records its position in the log only after a file is written. If it crashes, it resumes from that position and may rewrite a file. Rewriting is harmless because replay removes duplicates (step 6).
4. **Live processor loads.** It reads the raw log in micro-batches about once a minute. For each event it tries to claim `event_id` in the KV store (set only if absent). If the claim succeeds, it enriches the event (geo-IP lookup, user-agent parsing) and loads it into the `events_clean` partition for its `received_at` day. If the key already exists, it drops the event. Each key expires after 8 days: the 7-day retry window plus one day of margin. It records its position in the log after the load. If it crashes between claiming and loading, that event is missing from the live table until its day is replayed.
5. **Monitoring.** Alerts fire on consumer lag. The live processor alerts if it falls more than 2 minutes behind, since the limit is 5 minutes. The archiver alerts at 1 hour behind, well before the log's 14-day retention would delete unread events.

## Replay

An operator runs it for one UTC day, usually after fixing an enrichment bug. Only one replay runs at a time.

6. **Replay job.**
   1. Refuse if the day is not closed.
   2. Read the archive files for that day and the 7 days before it. It reads the archive and never the log, so live ingestion is not slowed. It runs on its own compute and never touches the KV store, so live deduplication state does not change.
   3. Deduplicate by `event_id`, keeping the earliest `received_at` (ties broken by log order). Keep an event only if its first copy falls on the replayed day. The 7 earlier days are needed because a copy that first arrived on an earlier day was already dropped by the live path.
   4. Enrich with the fixed code and write the result to a staging table.
   5. Use the warehouse's atomic replace to swap the staging table into that day's partition of `events_clean`. Dashboards see the old day or the new day, never a half-built one.
   If any step fails, nothing is swapped and the old partition stays. The operator fixes the cause and reruns. Replay only works for days whose archive files still exist (90 days).

## What happens when things fail

| Failure | Result |
|---|---|
| Collector cannot write to the log | 5xx, client retries the same batch |
| Malformed event | Rejected and listed in the response, never retried, kept in the reject bucket |
| Archiver or live processor crashes | Resumes from its recorded log position |
| Duplicate arrives within 8 days | Dropped by the KV claim |
| Live processor loses an event between claim and load | Fixed by replaying that day |
| Replay fails before the swap | Old partition unchanged, rerun |

## Build order

1. Collector, raw log and archiver, so nothing is lost.
2. Live processor and `events_clean`.
3. Replay job.
4. Lag alerts.

## Open questions

- **Bot traffic:** product has not decided whether suspected bots are dropped or kept with a flag. This plan does not choose. Detection would run in the enrichment step of both the live path and replay, so either choice can be added there without changing the rest.
- Whether the warehouse can append to today's still-open partition. The live path assumes it can. Atomic replace is only needed for closed days.
- Why the day closes at 02:00 and not earlier. The 2-hour margin is assumed to cover archiver and processor lag. Confirm it.
- A duplicate arriving after its KV key expires (more than 8 days) would be loaded as new. The SDK's 7-day limit should prevent this.
