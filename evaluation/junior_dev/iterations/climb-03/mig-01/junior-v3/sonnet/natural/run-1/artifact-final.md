# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

In short: we first copy every write to Postgres (dual writes) and backfill old rows. Once a full comparison is clean, reads move to Postgres gradually. After 3 days at 100%, a short write pause switches the source of truth to Postgres, and the copy direction reverses so we can roll back. After 14 more days we stop writing to MySQL. All logic lives in `UserRepository`, steered by flags.

## Terms

- **Source of truth:** the database whose commit decides a write succeeded. The other database is a copy.
- **Sync:** copying one user's current row (or its deletion) from the source of truth to the other database.
- **Outbox:** a table `users_sync_outbox(seq PK auto, user_id, attempts, next_try_at, created_at)` of "this user needs a sync" rows, kept in the source-of-truth database. Each side has one; only the current source of truth's outbox gets new rows.
- **Paused:** the mode in which an instance answers every write request with a retryable 503 and touches no database on the request path. Reads still work. The repair worker is a separate process and keeps running.
- **In-flight write:** a write request that has started and not yet returned, including its inline sync. It lasts at most the request timeout.
- **Tombstone:** a Postgres `users` row with `deleted_at` set and only `id` and `deleted_at` filled. It marks an erased user.

## Rules every step relies on

- **Who starts a step.** A person (the operator) starts each step, by changing a flag or launching a job, once the step's "Starts" condition holds. The backfill and comparison jobs check replica lag themselves before every batch.
- **Write mode flag.** One string flag, `users_write_mode`, takes the values `mysql`, `dual_mysql`, `paused`, `dual_pg` or `pg_only`. `dual_mysql` means MySQL is the source of truth and every write is copied to Postgres. `dual_pg` is the mirror image. One flag means two flags can never contradict each other.
- **Flag propagation.** Each instance caches flags and refreshes every 30 seconds, so instances can disagree for up to 30 seconds. Each instance exports its value as `app_flag_value{flag="users_write_mode"}`, and monitoring scrapes it. That is how we confirm a change reached every instance.
- **Why `paused` exists.** If two instances disagreed on the source of truth, one could write to MySQL while another writes to Postgres, and the two would overwrite each other and assign the same new id to different users. So before the source changes, every instance is paused and idle. The 503 goes to the caller of the write API, which already retries; nothing was written for that request.
- **Read flag.** `users_read_pg_pct` is a percentage flag. The repository calls `flags.enabled_for("users_read_pg_pct", user_id)`, so a given user always gets the same answer.
- **Versions.** `create()` sets `version` to 1 and each `update()` adds 1, in the repository's own SQL, in every mode. A copy never changes `version`.
- **Writing and syncing.**
    - Every write inserts an outbox row in the same transaction as the write, so a crash after commit cannot lose the need to copy.
    - After commit, the request path does an inline sync: read that user's current row from the source of truth, apply it to the other database, with a 250 ms timeout. On success it deletes that user's outbox rows with `seq <=` the one it saw. Any failure is logged and swallowed. The user still gets success, and the outbox row stays for the worker.
    - A per-instance circuit breaker skips inline attempts for 30 seconds after 5 consecutive failures, then tries one. Postgres trouble therefore adds no latency to writes.
    - The repair worker is one standalone process (not `jobs`, because `enqueue` can fail when Redis is down and `jobs:dead` is never processed). It polls both outboxes with `FOR UPDATE SKIP LOCKED` and syncs each user to the opposite database, retrying forever with backoff capped at 60 seconds. The backfill and the comparison also feed the outbox.
    - A sync copies state, not events: it reads the current row by id and applies it, or applies a delete if the row is gone. Syncs are idempotent and order-independent. All columns, including `version` and `updated_at`, are copied verbatim.
    - If a sync fails on a unique-email collision (user A frees an email that user B takes), it retries and succeeds once A's sync lands.
- **Version rule and deletes into Postgres, in one statement.**
    - Upsert: `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.deleted_at IS NULL AND users.version < EXCLUDED.version`. It inserts a missing row or replaces a lower version, and never overwrites a tombstone. It is atomic on the primary key, so a stale copy cannot race a delete.
    - Delete: upsert a tombstone unconditionally. Even if the row was never copied, the tombstone stops a later backfill creating it. Tombstones are kept permanently (about 2,000 per day).
    - The view `users_live` filters `deleted_at IS NULL`. All Postgres reads and comparisons use it.
- **Version rule and deletes into MySQL.** MySQL has a table `users_erased(id PK)`. A copy into MySQL first runs `SELECT 1 FROM users_erased WHERE id=%s FOR SHARE`, skips if found, then does `INSERT ... ON DUPLICATE KEY UPDATE` with the same version rule. A concurrent erasure blocks on that lock, so a stale copy cannot revive an erased user.
- **`delete()` per mode** (only the erasure job calls it).
    - `mysql` and `dual_mysql`: one MySQL transaction hard-deletes the row, inserts the id into `users_erased` and, in `dual_mysql`, adds an outbox row. The sync finds the row gone and writes the Postgres tombstone. If that sync fails, the worker, the backfill and the comparison all repair it.
    - `dual_pg`: one Postgres transaction writes the tombstone and an outbox row. The sync then hard-deletes the MySQL row and inserts into `users_erased`.
    - `pg_only`: the tombstone only.
- **Read path.** If the user is in the read percentage, read from Postgres with a short timeout.
    - On a Postgres error or timeout, fall back to the MySQL replica so reads never fail. In `dual_pg` that data may briefly be stale, which we accept because it only happens while Postgres is failing. In `pg_only` there is no fallback, so the read retries Postgres once.
    - On a Postgres miss, fall back to the replica only in `mysql` and `dual_mysql`. Once Postgres is the source of truth, a miss is final.
- **New ids.** MySQL assigns ids until the switch, and Postgres receives them as explicit values. The Postgres sequence `users_id_seq` is used only in `dual_pg` and `pg_only`, where Postgres assigns ids and copies them to MySQL as explicit ids. At each change of source of truth, inside the pause, the incoming database's counter is set to (largest id in either database) + 1,000,000 (`setval` for Postgres, `ALTER TABLE users AUTO_INCREMENT` for MySQL), so ids stay unique without relying on automatic behaviour.
- **Where state lives.**

    | State | Location |
    |---|---|
    | Modes and percentages | flags |
    | Forward outbox | MySQL primary |
    | Reverse outbox | Postgres |
    | Backfill checkpoint, comparison results | Postgres table `migration_state` |
    | Erasures | `users_erased` in MySQL, tombstone rows in Postgres |

## Steps

- [ ] **1. Create the new schema (additive DDL, nothing uses it yet).**
    - Starts: a manual DDL migration, run once.
    - Postgres: `users` with the same columns as MySQL plus `deleted_at` and a unique index on `email`; `users_live`; `users_id_seq`; `users_sync_outbox`; `migration_state(name PK, last_id, done, updated_at)`.
    - MySQL: `users_sync_outbox` and `users_erased`.
    - State: schema only.
    - If it fails: drop the new objects. No running code references them.

- [ ] **2. Deploy the new code with everything switched off.**
    - Starts: a normal rolling deploy.
    - Ships a new `UserRepository` implementing all modes, the repair worker, the backfill job, the comparison job and the new read path. Defaults are `users_write_mode=mysql` and `users_read_pg_pct=0`, so behaviour is unchanged. Only `delete()` changes at once: it also writes `users_erased`.
    - The deploy is not complete until old-version instances are gone.
    - If it fails: roll the deploy back. All changes are additive.

- [ ] **3. Rehearse a pause.**
    - Starts: set `users_write_mode=paused`, then straight back to `mysql`.
    - Measures how long writes are really unavailable. If it is over 60 seconds, fix the scrape interval or the wait deadlines in the switch step before going on.
    - Writes get a retryable 503 during the drill. Reads are untouched.
    - If it fails: set the flag back to `mysql`. Instances resume within 30 seconds.

- [ ] **4. Turn on dual writes.**
    - Starts: set `users_write_mode=dual_mysql`.
    - Each write commits to MySQL with its outbox row, then syncs to Postgres inline. The worker repairs misses.
    - Healthy when `app_flag_value` shows `dual_mysql` on every instance, the oldest outbox row is under 1 minute old, and the Postgres error rate is low.
    - If it fails: set the flag back to `mysql`. The worker keeps draining the outbox, and any remaining gap is closed by the backfill and comparison.

- [ ] **5. Backfill.**
    - Starts: the operator launches the job once all hold: `app_flag_value` is `dual_mysql` on every running instance (the number of series equals the orchestrator's instance count, and no old-code instance remains); the outbox is healthy; `mysql_replica_lag_seconds` is 5 or less.
    - It reads from the MySQL replica: `WHERE id > last_id ORDER BY id LIMIT 2000`, and copies each batch with the guarded upsert. Before every batch it checks `mysql_replica_lag_seconds`; while above 5 it sleeps and rechecks. It also throttles itself to protect Postgres.
    - Each batch is one Postgres transaction that upserts the rows and sets `migration_state.last_id` to the batch's highest id, so the checkpoint moves only with committed data. A lease row in `migration_state` allows a single runner.
    - Stale replica rows are safe because of the version rule, and rows erased meanwhile are safe because of tombstones. An empty batch with the lag condition met sets `done`.
    - If it fails: a crash rolls back the open batch, and the job restarts from `last_id`; repeating a batch is harmless. Alert if the checkpoint does not move for 15 minutes.

- [ ] **6. Full comparison.**
    - Starts: the backfill is `done`, and the operator launches the job.
    - It scans every id in both tables (MySQL from the replica, under the same lag rule), compares all columns including `version`, and checks for Postgres rows with no MySQL counterpart.
    - A difference is rechecked against the MySQL primary and Postgres once the outbox has nothing pending for that id. Only a persistent difference counts as a mismatch, and it is pushed into the outbox of the current source of truth to be repaired. Results are kept in `migration_state`.
    - Success is one complete pass with zero persistent mismatches. Repeat the pass until that happens.
    - If it fails: it only reports and repairs. Investigate the cause of a repeated mismatch before going on.

- [ ] **7. Move reads to Postgres.**
    - Starts: step 6 has had a zero-mismatch pass. The operator changes the flag.
    - Ramp `users_read_pg_pct` to 1, 10, 50 and 100, watching error and fallback rates at each stage. Run the comparison daily. Hold at 100% for at least 3 days with zero persistent mismatches; any mismatch means fix the cause and restart the 3-day clock.
    - If it fails: set the percentage to 0 or lower. It takes effect within 30 seconds, and reads keep working throughout.

- [ ] **8. Switch preflight.**
    - Starts: reads have been 100% on Postgres for 3 days or more.
    - Check that the latest comparison pass is clean, the oldest outbox row is under 5 seconds old, and Postgres is healthy. Confirm the scrape interval for `app_flag_value` and `users_writes_inflight` is 10 seconds or less.
    - If it fails: do not start. Fix it and recheck.

- [ ] **9. Switch the source of truth to Postgres (writes paused for 90 seconds at most).**
    - Starts: the operator sets `users_write_mode=paused` (call that moment T0).
    1. **T0.** Each instance returns a retryable 503 for writes once it sees the flag and starts no new inline sync. Reads continue on Postgres. In-flight writes finish, bounded by the request timeout.
    2. **By T0+45.** Wait until every instance shows `paused` and its `users_writes_inflight` gauge (added by this migration; it counts in-flight writes) is 0. Then no request path touches a database.
    3. **By T0+55.** Wait until the MySQL outbox is empty (`SELECT COUNT(*)` returns 0; the worker drains it and no new rows arrive). Then set the Postgres sequence: `setval('users_id_seq', MAX(id) from the MySQL primary + 1,000,000)`.
    4. **By T0+55.** Set `users_write_mode=dual_pg`. Each instance resumes within 30 seconds of seeing it, so none is paused for more than about 85 seconds.
    - Afterwards, writes commit to Postgres with an outbox row there, then copy to MySQL. MySQL stays current, so rollback needs no data reconstruction.
    - If it fails before the flip: if the wait in 2 or 3 misses its deadline, set the flag back to `dual_mysql`. Instances resume within 30 seconds, so the pause stays under 90, and nothing has moved. A stuck outbox row (a repeated unique-email failure or a Postgres outage) is a reason to abort: the worker keeps retrying; find the cause and get the oldest row under 5 seconds old before trying again.
    - If it fails after the flip: use rollback.

- [ ] **10. Soak for at least 14 days with reverse dual writes.**
    - Starts: `dual_pg` has reached every instance.
    - Run the comparison daily. The reverse outbox must stay near empty. Rollback stays available throughout.
    - If it fails: use rollback.

- [ ] **11. Rollback (only if needed).**
    - Starts: a person decides, for example because of sustained errors on Postgres.
    1. Set `paused`.
    2. Wait for every instance to be paused and in-flight writes to be 0.
    3. Drain the Postgres outbox to 0.
    4. Set MySQL's counter: `ALTER TABLE users AUTO_INCREMENT = <largest id in Postgres or MySQL> + 1,000,000`.
    5. Set `users_write_mode=dual_mysql`.
    - Reads can stay on Postgres, since it is still kept in sync. The 90-second budget is the same. Any write made in Postgres is already in MySQL or in the outbox, so none is lost.
    - If it fails: set the flag back to `dual_pg`.

- [ ] **12. Stop writing to MySQL.**
    - Starts: at least 14 days have passed since the switch to Postgres, and the last comparison and the Postgres outbox are clean.
    - Set `users_write_mode=pg_only`. This is not a change of source of truth, so no pause is needed. It ends the copies to MySQL and the writing of the reverse outbox. Rollback is no longer possible after this point.
    - If it fails: set the flag back to `dual_pg`. No data is lost, since Postgres has every write, but `pg_only` wrote no outbox rows, so MySQL is stale. Run the comparison until one pass has zero mismatches; it pushes each difference, including tombstones, into the Postgres outbox for the worker to copy. Until that pass is clean, do not roll back to MySQL.

- [ ] **13. Retire MySQL.**
    - Starts: a manual decision after `pg_only` has run cleanly for an agreed period.
    - Rename the MySQL `users` table, take a final snapshot, and drop it only after a further agreed quiet period. Remove the MySQL code paths and flags from `UserRepository`, and drop the outbox and `users_erased` tables. Keep the Postgres tombstones.
    - If it fails: rename the table back, until it is dropped.

## Open questions

- Which service backs the flags store and the metrics scraping is not described in the existing files. The plan relies only on the 30-second refresh and the exported metric.
- The circuit breaker thresholds (5 failures, 30 seconds) are initial values, to be tuned when dual writes are turned on.
