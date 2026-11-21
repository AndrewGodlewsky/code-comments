# Clickstream ingestion: plan

## Overview

Clients → **Collector** → **Raw log** → two independent consumers:

- **Archiver**: keeps an unchanged copy of every accepted event in object storage for 90 days. Replay takes its events from this copy.
- **Live processor**: deduplicates and enriches events, then loads them into `events_clean`.

**Replay** is a separate batch job. Its event input is only the archive files for one day; it also looks up `event_id`s in `events_clean`, and it swaps the rebuilt day in at the end.

**Day rule (used by every step):** an event's day is the UTC date of `received_at`, which the Collector stamps. The client timestamp is kept as a field but never decides the day.

**Duplicate rule (used by every step):** the same `event_id` means the same event. The first copy received is kept. Later copies are dropped, even if they arrive up to 7 days later.

## Live path

### 1. Client sends a batch
- **Starts when:** the SDK flushes its queue (at most 100 events per batch).
- **Moves:** events with `event_id`, `device_id` and the client timestamp, sent over HTTPS to the Collector.
- **State:** events stay on the client until they are acknowledged. Mobile keeps them in an on-device buffer for up to 7 days.
- **On failure:** on a timeout, 429 or 5xx, the client resends the *same* batch with the *same* `event_id`s, backing off 1 s, 2 s, 4 s … up to 5 min. Mobile events still unacknowledged after 7 days are discarded. Events the Collector lists as rejected are discarded and never retried.

### 2. Collector validates, stamps and appends
- **Starts when:** an HTTPS POST arrives.
- **Moves:** each valid event gets `received_at` and is appended to the Raw log, keyed by `device_id`. Malformed events (no `event_id` or `device_id`, or over 32 KB) go, with a reason, to a reject bucket in object storage (kept 14 days).
- **State:** none in the Collector. The Raw log (replicated, 14-day retention) is the durable record.
- **Responds:** 202 only after the Raw log confirms the replicated append. The response body lists the rejected `event_id`s.
- **On failure:** if the append fails or times out, the Collector returns 503 and the client retries the whole batch (step 1). If the append actually succeeded but the 202 was lost, the retry creates duplicates in the Raw log, and step 4 removes them.

### 3. Archiver keeps the raw copy
- **Starts when:** it runs continuously as its own consumer group on the Raw log.
- **Moves:** every accepted event, duplicates included, unchanged and stored with its Raw-log partition and offset. Events go into hourly files at `archive/date=<day>/hour=<HH>/`. An object-storage lifecycle rule deletes files after 90 days.
- **State:** its Raw-log position, committed only after a file is fully written. File names contain the log partition and offset range, so a rewrite after a crash replaces the file instead of adding a second copy.
- **Day closing:** at 02:00 UTC, once its position is past the previous day's last event, it writes `archive/date=<day>/_COMPLETE`.
- **On failure:** if object storage is unavailable, it stops and retries while events wait in the Raw log (up to 14 days). An alert fires at 15 min of lag. The live path is unaffected. The `_COMPLETE` marker, and so replay of that day, waits until the Archiver catches up.

### 4. Live processor deduplicates
- **Starts when:** every minute, it reads the next micro-batch from the Raw log (its own consumer group).
- **Moves:** for each event, a set-if-absent on the **Dedup store** (the key-value store's `dedup` namespace). The key is `event_id` and the value is this copy's Raw-log position (partition + offset). The TTL is 8 days (the 7-day retry window plus 1 day of margin), and the TTL is what removes old entries.
  - Key absent: this is the first copy, so keep it.
  - Key holds *this* position: this same copy was handled before a crash, so keep it (step 6 makes rewriting it harmless).
  - Key holds a *different* position: this is a duplicate, so drop it.
- **On failure:** if the Dedup store is unreachable, the processor pauses and retries the micro-batch with backoff. It never lets events through unchecked. Events wait in the Raw log (14-day retention), and the Collector keeps accepting and acknowledging. An alert fires at 5 min of lag.

### 5. Live processor enriches
- **Moves:** adds geo-IP fields, parsed user-agent fields and `enrichment_version`.
- **On failure:** an event that can't be enriched (for example, an unparseable user-agent) is loaded with those fields empty and an `enrichment_error` field. It is never dropped.
- **Bot traffic (OPEN QUESTION):** Product has not decided whether suspected bots are dropped or kept with a flag. Either rule would go in this step, and replay reuses this step. Whichever is chosen, bot events stay in the archive.

### 6. Live processor loads, then commits
- **Moves:** merges the micro-batch into `events_clean`, in the partition for each event's day, matching on `event_id` (insert if new, overwrite if present).
- **Then:** commits its Raw-log position. Rows are queryable about 1–2 min after receipt (the target is 5 min).
- **On failure:**
  - If the load fails, the position is not committed and the same micro-batch is retried.
  - If the processor crashes after the load but before the commit, it rereads the micro-batch. Step 4 finds the same positions and keeps the events, and the merge on `event_id` overwrites the rows instead of adding new ones. Nothing is lost or doubled.

## Replay of one day D

### 7. Operator starts the replay
- **Starts when:** an operator runs `replay --day D`, usually after an enrichment fix has been deployed.
- **Checks (otherwise the replay is refused):**
  - D is closed (now is at least 02:00 UTC on D+1) and `archive/date=D/_COMPLETE` exists.
  - The live processor has committed past D's last event, so no late live write lands in D after the swap.
  - D is within the 90-day archive.
  - No other replay of D is running. The job takes the lock key `replay:D` with a set-if-absent in the key-value store's `replay-locks` namespace. This namespace is separate from the Dedup store's `dedup` namespace, which replay never reads or writes.

### 8. Replay job rebuilds D in staging
- **Runs on:** separate batch compute, so live ingestion is not slowed.
- **Reads:** its event input is only the files under `archive/date=D/`. Besides those, it only makes read-only `event_id` lookups in `events_clean` partitions D-7 … D-1. It never reads the Raw log and never touches the Dedup store, so live dedup state is not changed.
- **Dedup (same rule as the live path):**
  1. Within D, for each `event_id`, keep the copy with the earliest `received_at` (on a tie, the lowest Raw-log position).
  2. Drop any `event_id` already in `events_clean` for days D-7 … D-1, because its first copy arrived on an earlier day.
- **Writes:** enriches with the current code (the step 5 logic) and writes to the table `events_clean_staging_D`.
- **On failure:** drop the staging table, release `replay:D` and rerun from the start. `events_clean` has not been touched and still serves the old D.

### 9. Validate and swap
- **Check:** the staging row count must be within 1% of the current partition D. Otherwise the job stops and asks the operator.
- **Swap:** atomically replace partition D of `events_clean` with the staging table. Dashboards read the old day until the swap and the new day after it, never a mix.
- **On failure:** if the swap fails, the old partition stays in place and the swap is retried.
- **Then:** drop staging and release `replay:D`.

## Where state lives

| State | Where | Removed by |
|---|---|---|
| Unacknowledged events | Client (mobile buffer, up to 7 days) | 202, rejection, or the 7-day limit |
| All accepted events | Raw log | 14-day retention |
| Raw copy including duplicates | Archive (object storage) | 90-day lifecycle |
| Malformed events | Reject bucket | 14-day lifecycle |
| First-copy positions | Dedup store (KV, `dedup` namespace) | 8-day TTL |
| Clean events | `events_clean`, one partition per UTC day | (kept) |
| Replay lock `replay:D` | KV, `replay-locks` namespace (separate from `dedup`) | Released at the end of the replay |
| Replay output | `events_clean_staging_D` | Dropped at the end of the replay |

## Open questions
- **Bot traffic:** dropped, or kept with a flag? Product has not decided. Affects step 5, which step 8 reuses.
