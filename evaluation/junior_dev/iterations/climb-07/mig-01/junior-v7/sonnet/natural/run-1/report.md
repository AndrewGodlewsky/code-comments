## Review of mig-01 (junior-v7, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Write path and Decisions: outbox row is inserted only while users_dual_write is true, fixing the contradiction with step 2.
- Added a Terms section defining version, erasure job, source of truth, outbox and flag cache.
- Flags: explained that enabled_for hashes the user id into a stable bucket and what bucketed users are.
- State locations: said why there is an outbox in each database and that the relay reads only the current source of truth's outbox.
- Relay worker: said the outbox row holds no data and the relay re-reads the current row, so the latest version wins.
- Write path: added one line on how an erasure reaches the tables under sot=postgres.
- Step 6: spelled out how get() chooses a store and what happens for tombstones, errors and misses before and after the switch.
- Step 8: explained why instances stop writing to MySQL (30 s refresh or 40 s fail-closed) and what happens to in-flight writes.
- Added an Open questions section noting that what serves the flags is not known.
- Added a two-sentence summary of how users works today and how the migration flows, plus a version rule term defined once and reused instead of repeated.
- Expanded Terms: version, version rule, source of truth, dual write, erasure job, tombstone (Postgres and MySQL forms merged into one definition), outbox, relay worker, flag cache, bucketed user.
- Split the old Decisions section into Flags, and How it runs (why an outbox, where state lives, schema notes, write path, relay, reads, write-safety rules); rollout is now a separate Rollout checklist section.
- Moved the read behaviour (tombstone, Postgres error, miss fallback) out of step 6 into one Reads paragraph; step 6 now refers to it.
- Moved the WritesPaused, 40 s fail-closed and 5 s deadline rules out of step 2 into one place under How it runs; step 8 keeps only a short pointer to the 40 s rule.
- Merged the repeated tombstone explanations (Decisions, step 5, step 9) and the repeated erasure paths into Terms, the write path and step 9.
- Added the outbox rows hold no row data and relay re-read detail, the reason for an outbox in each database, and that dual-write-off writes get no outbox row (fixing the earlier contradiction).
- Listed users_backfill_pause_ms among the flags and placed it in the backfill loop; turned the backfill description into an ordered loop.
- Kept all numbers and limits: 2,000 batch, 5 s lag, 10,000 chunks, 300 ms, 10 s breaker, 5 s relay age, 5 min backoff, 2 min alert, 30/40/45/75/90 s, 3 and 14 days, 100000 sequence offset, 7 day hold.
- Kept the Open questions section with the unknown flag service; the other open items were answered in the file so none were added.

### Holes
- Q6: How does each instance learn flag values, and what is the 'flag cache' and the 30 s refresh? What serves the flags? (author: The existing flags file says only that each instance caches all flags and refreshes them every 30 s, and that instances export app_flag_value. It does not say what serves the flags, and I do not know. The plan depends only on the 30 s refresh and the metric. Terms now define the flag cache; the unknown is listed under Open questions.)
