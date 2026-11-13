# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## How the pieces fit

- **Flags.** `app.flags` caches all flags per instance and refreshes every 30 s, so instances can disagree for up to 30 s after a change. Each instance exports the values it uses as `app_flag_value{flag=...}`.
- **Mode flag.** `users_write_mode` is one of `mysql`, `mysql_dual`, `pg_dual`, `pg_only`. It says which database is the source and whether the other one is also written.
- **Version.** `users.version` starts at 1 and `UserRepository.update` adds 1 on every update. Copies carry the version unchanged.

## Design decisions

- **Repair uses a MySQL outbox, not the Redis jobs queue.** `enqueue` can raise when Redis is down, and failed jobs end in `jobs:dead`, which nothing reads. So the repair record is written in the same MySQL transaction as the user write: `users_pg_outbox(seq PK AUTO_INCREMENT, user_id, created_at)`. A committed write always leaves a durable repair record.
- **Write flow in `mysql_dual`** (create, update and delete alike):
    1. One MySQL transaction: read the fence row `FOR SHARE`, do the write (a create gets its id and version 1 from MySQL `AUTO_INCREMENT`), insert the outbox row.
    2. After commit, apply the row to Postgres inline with `pg_copy`, with a 250 ms timeout and a circuit breaker.
    3. On success, delete the outbox row by `seq`. On failure or an open breaker, do nothing: the request still succeeds and the outbox row stays.
- **Drain worker.** A separate `users-sync-worker` deployment (2 replicas) polls the outbox every 2 s. It claims rows older than 10 s with `FOR UPDATE SKIP LOCKED` and coalesces them by `user_id`. For each user it re-reads the current row from the MySQL primary and applies it with `pg_copy`. If the row is gone from the primary, it deletes it in Postgres and writes a tombstone. Failures retry with backoff, and an alert fires if the oldest outbox row is over 5 minutes old. A failed inline apply is therefore repaired within about 12 s, with no notification needed.
- **One copy function, `pg_copy(rows)`, for dual write, backfill and repair.** It runs `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.version < EXCLUDED.version` and skips ids in `users_tombstones`. It first takes `LOCK TABLE users_tombstones IN SHARE MODE`. A delete's tombstone insert conflicts with that lock, so a copy and a delete cannot interleave and resurrect a row.
- **Deletes use tombstones.** Only the erasure job deletes. In `mysql_dual`, one MySQL transaction does the fence read, inserts `(user_id, deleted_at)` into MySQL `users_tombstones`, deletes the row and inserts an outbox row. The Postgres side (inline or by the worker) then runs one transaction: insert into Postgres `users_tombstones` (id only, no personal data), then delete the row. The tombstone is written even if the row was never in Postgres. Deletes ignore the version rule. Tombstones are kept permanently.
- **Switch coordination uses a database fence, not flag timing.**
    - One `migration_state` row in MySQL (`active` / `paused` / `standby`) and one in Postgres (`standby` / `paused` / `active`).
    - Every request-originated write reads a fence row `FOR SHARE` inside its own transaction. `mysql` and `mysql_dual` read the MySQL row. `pg_dual` and `pg_only` read the Postgres row. If the state is not `active`, the write raises `WritesPaused`, which maps to 503 with Retry-After.
    - A coordinator's `UPDATE` of a fence row takes an exclusive lock, so it waits for in-flight writers. Once it commits, no stale-flag instance can write to that database.
    - Backfill, drain and repair do not check the fence.
- **Backfill progress lives in Postgres.** `migration_progress(name PK, last_id, rows_copied, updated_at)` is updated in the same Postgres transaction as each batch's upserts, so "last completed batch" is exact. Redis is not durable, and MySQL could not make it atomic with the batch.
- **New ids after the switch come from a Postgres sequence.** `users_id_seq` is created in step 1. During the switch pause, the coordinator runs `setval(GREATEST(current, mysql_auto_increment_counter + 1,000,000))`. The counter is at or above every id MySQL ever issued, including deleted ones, so a new id cannot collide with a tombstone. The 1M margin covers ids issued around the pause.
- **Email collation.** MySQL's unique `email` is case-insensitive, so Postgres uses `citext` with a unique index. Check accent-only differences in the first compare pass.

## Steps

- [ ] **1. Create schemas (no behavior change)**
  - **Starts:** a DDL migration run by an engineer.
  - **Changes:**
    - Postgres: `users` (same columns, `id BIGINT PK`, `email citext UNIQUE`, `updated_at timestamp(3)`), `users_tombstones`, `migration_state` (`standby`), `pg_outbox`, `migration_progress`, `migration_compare`, `users_id_seq`.
    - MySQL: new tables `users_pg_outbox`, `users_tombstones`, `migration_state` (`active`). `users` is not touched.
  - **State:** the tables.
  - **If it fails:** all DDL is `IF NOT EXISTS`, so re-run it. Nothing reads these tables yet.

- [ ] **2. Deploy repository v1 with all flags off**
  - **Starts:** a normal rolling deploy.
  - **Changes:** `UserRepository` gains the fence read, `users_write_mode` (default `mysql`), the percentage flag `users_read_pg_pct` (default 0), `pg_copy`, the outbox write and the read fallback. Also deploy `users-sync-worker`, the backfill job and the compare job, all idle.
  - **State:** flags in `app.flags`. The MySQL fence row is `active`.
  - **If it fails:** roll back the deploy. In `mysql` mode behavior matches today's, apart from one extra `FOR SHARE` read per write.
  - **Done when:** 100% of instances run v1 and no old-version instance reports metrics.

- [ ] **3. Turn on dual writes: `users_write_mode=mysql_dual`**
  - **Starts:** a flag change after step 2 is done.
  - **Changes:** every write is fenced and commits to MySQL with an outbox row, then is applied to Postgres inline. A Postgres failure is swallowed and the worker repairs it automatically.
  - **State:** the outbox in MySQL.
  - **Gate:** `app_flag_value{flag="users_write_mode"}` is `mysql_dual` on every running instance, with none missing from the series, and then 5 more minutes have passed (30 s refresh plus in-flight requests).
  - **If it fails:** set the flag back to `mysql`. Leftover outbox rows are still drained, and backfill and compare catch anything missed.

- [ ] **4. Backfill**
  - **Starts:** automatically, once the step 3 gate has held for 5 minutes. It re-checks the gate before every batch and stops if the flag is reverted.
  - **Changes:** one worker holds a Postgres advisory lock. Before each batch it reads `mysql_replica_lag_seconds`. If lag is above 5, or the metric is missing or stale, it sleeps 10 s and checks again. Otherwise it runs `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` on the replica. It skips ids with a pending outbox row on the primary (the worker handles those). Then it calls `pg_copy` and sets `migration_progress.last_id` to the batch's max id, in one Postgres transaction. A 0.5 s minimum between batches limits load: about 19,000 batches take roughly 5 to 6 hours.
  - **Why stale replica rows are safe:** `pg_copy` only replaces a lower version and skips tombstoned ids, and the newer write's own outbox row delivers the newer version.
  - **State:** `migration_progress` in Postgres.
  - **If it fails:**
    - After a crash, restart from `last_id`. Re-copying is idempotent under the version rule.
    - A Postgres outage means backoff retries with no progress change.
    - On an email unique violation, retry the batch row by row and send rows that still conflict to the MySQL outbox.
  - **Done when:** the read returns zero rows and the outbox is empty.

- [ ] **5. Full comparison, repeated until clean**
  - **Starts:** step 4 is done.
  - **Changes:** the compare job walks 5,000-id windows in both tables and compares `(id, email, name, plan, version)`. It also finds Postgres-only ids and ids that are tombstoned yet still in MySQL. A window with differences is re-read from the MySQL primary and Postgres after 60 s, and only persistent differences count. Each persistent difference becomes an outbox row, so it is repaired automatically.
  - **State:** `migration_compare(run_id, last_id, checked, mismatches)` in Postgres. A crash resumes from the last window.
  - **Gate:** one complete pass with 0 persistent mismatches. Otherwise run another pass.
  - **If it fails:** an equal-version mismatch with different content cannot be repaired under the version rule. It is a bug, so it pages a human and blocks the gate. This is the only manual case.

- [ ] **6. Ramp reads: `users_read_pg_pct` 1 → 10 → 50 → 100**
  - **Starts:** step 5's gate is met. Move up a stage after its hold time (1 hour at 1%, 4 hours at 10%, 1 day at 50%) if PG read error rate, p99 latency and fallback rate are healthy and compare mismatches are 0.
  - **Changes:** `flags.enabled_for("users_read_pg_pct", user_id)` sends that bucket of users to Postgres. A Postgres error or a miss falls back to the MySQL replica at every percentage and is counted in the fallback rate. Reads therefore never fail, and a row Postgres has not yet received is still found.
  - **State:** the flag. A compare pass runs every night, and any mismatch pages and blocks step 7.
  - **If it fails:** set the percentage back to the previous value.
  - **Clock:** the 3-day clock starts when `app_flag_value` shows 100 on every instance. Any drop below 100 resets it.

- [ ] **7. Gate for the switch**
  - **Starts:** reads have been 100% on Postgres for at least 3 days, and a compare pass with 0 mismatches finished within the last 24 hours.
  - **Also required:** the outbox's oldest row is under 1 minute old and the Postgres cluster is healthy. Record the go decision.

- [ ] **8. Switch the source of truth to Postgres (write pause of 45 s or less)**
  - **Starts:** the engineer runs `users_switch.py`, which is idempotent and logs timestamps.
  - **Changes, in order:**
    1. At t=0, set MySQL state `active→paused` (the `UPDATE` waits for in-flight writers), then set `users_write_mode=pg_dual`. Order does not matter for safety: until Postgres is `active`, old-flag instances see MySQL as paused and new-flag instances see Postgres as `standby`, so all writes get 503.
    2. Drain the MySQL outbox to empty, ignoring the 10 s age gate while paused. Confirm it is empty twice, 2 s apart.
    3. `setval` on `users_id_seq` as described above.
    4. Set Postgres state `standby→active` and MySQL state `paused→standby`.
  - **Pause length:** nobody coordinates the end. Each instance resumes writing when its flag refresh brings `pg_dual`; until then it reads MySQL as `standby` and returns 503. The flag was set at t=0, so every instance has it by t=30 s. The pause is the longer of 30 s and the drain time.
  - **From now on:** writes use the `mysql_dual` pattern with the databases swapped. The Postgres transaction holds the fence read, the write and a `pg_outbox` row. After commit, a mirrored copy function applies the row to MySQL (same version rule, and a MySQL failure never fails the request). It checks tombstones with `SELECT ... FROM users_tombstones WHERE id = ? FOR SHARE`. If the id is absent, InnoDB gap-locks it, so a concurrent tombstone insert waits. This does the job of `LOCK TABLE ... SHARE MODE` in Postgres. `users-sync-worker` now drains `pg_outbox` into MySQL (the reverse drain) in place of `users_pg_outbox`.
  - **State:** the fence rows, the flag, and a `source_since` timestamp in Postgres `migration_state`.
  - **If it fails:** abort is allowed only before sub-step 4. If the drain is not empty at t=45 s, set MySQL back to `active` and the flag to `mysql_dual`. Nothing in Postgres has changed, and instances revert within 30 s, so the total pause is 75 s or less. After sub-step 4, go forward or use step 9.
  - **Afterwards:** run a reverse compare pass.

- [ ] **9. Rollback window: at least 14 days with Postgres as source and MySQL kept current**
  - **Starts:** step 8 is finished.
  - **Changes:** nothing. MySQL receives every write through `pg_outbox`. Watch outbox age and the compare passes.
  - **Rollback, if needed (90 s or less):**
    1. Set `users_write_mode=mysql_dual` and Postgres state `active→paused`.
    2. Drain `pg_outbox` to empty.
    3. If the MySQL `AUTO_INCREMENT` counter is not above the highest Postgres id, run `ALTER TABLE users AUTO_INCREMENT=...`.
    4. Set MySQL state `standby→active` and Postgres state `paused→standby`.
  - **Rollback abort:** same rule as step 8, allowed only before sub-step 4. Reads can stay on Postgres.
  - **After a rollback:** the 14-day clock restarts at the next switch.

- [ ] **10. Postgres-only writes: `users_write_mode=pg_only`**
  - **Starts:** at least 14 days after `source_since` (the script refuses earlier), a clean compare pass, and an empty `pg_outbox`.
  - **Changes:** writes stop going to MySQL, with no pause. Stale-flag instances still do `pg_dual`, which is harmless.
  - **Follow-up:** once every instance reports `pg_only`, stop the reverse drain. After 24 more hours, revoke the app's write grants on MySQL `users` to expose stragglers.
  - **If it fails:** setting the flag back to `pg_dual` is allowed, but MySQL then has a gap. Run a reverse compare pass and wait for 0 mismatches before treating rollback as possible again.

- [ ] **11. Drop MySQL `users` and clean up**
  - **Starts:** at least 7 days after step 10, with no MySQL write attempts in the logs.
  - **Changes:** take a final dump (kept per policy). Drop the MySQL `users`, outbox, tombstone and fence tables and `pg_outbox`. Remove the migration code, the flags and the `mysql.replica` read fallback. Keep Postgres `users_tombstones`.
  - **If it fails:** nothing depends on the dropped table, so restore from the dump if needed.

## Open questions

- The hold times in step 6, the 1M id margin and the 250 ms inline timeout are judgment calls, not measured values.
