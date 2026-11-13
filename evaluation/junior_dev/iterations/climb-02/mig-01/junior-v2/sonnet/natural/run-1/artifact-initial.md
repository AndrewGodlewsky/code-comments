# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Design decisions

- **Repair uses a MySQL outbox, not the Redis jobs queue.** `enqueue` can raise when Redis is down. Failed jobs go to `jobs:dead` after about 15 minutes and nothing reads that list. So the repair record has to be written in the same MySQL transaction as the user write.
  - **Outbox table.** `users_pg_outbox(seq PK AUTO_INCREMENT, user_id, created_at)`. A write that commits therefore always leaves a durable repair record.
  - **Inline apply.** After commit, the request applies the row to Postgres inline. This apply is wrapped in try/except with a 250 ms timeout and a circuit breaker. On success it deletes its outbox row. On failure it does nothing, so the request still succeeds.
  - **Drain worker.** A separate `users-sync-worker` deployment (2 replicas) polls the outbox every 2 s. It claims rows with `FOR UPDATE SKIP LOCKED`, only takes rows older than 10 s, and coalesces them by `user_id`.
  - **What the worker does.** It re-reads the current row from the MySQL primary and copies it to Postgres. If the row is gone from the primary, it deletes it in Postgres and writes a tombstone. Retries use backoff, and a rule alerts if the oldest outbox row is more than 5 minutes old.
- **One copy function for dual write, backfill and repair.** `pg_copy(rows)` runs `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.version < EXCLUDED.version`. It skips any id that is in `users_tombstones`. It first takes `LOCK TABLE users_tombstones IN SHARE MODE`. A delete's tombstone insert conflicts with that lock, so a copy and a delete can never interleave to resurrect a row.
- **Deletes use tombstones.** The erasure job's delete runs in one Postgres transaction. It inserts `(user_id, deleted_at)` into `users_tombstones` (id only, no personal data), and then deletes the row. The tombstone is written even if the Postgres row was never there. Deletes are unconditional and not subject to the version rule. Tombstones are kept permanently.
- **Switch coordination uses a database fence, not flag timing.** Flags can disagree across instances for 30 s.
  - **Fence rows.** There is one `migration_state` row in MySQL (`active` / `paused` / `standby`) and one in Postgres (`standby` / `paused` / `active`).
  - **Writers check the fence.** Every request-originated write reads its source's state row with `FOR SHARE` inside its own transaction. If the state is not active, it raises `WritesPaused`, which maps to 503 with Retry-After.
  - **Pausing.** A coordinator's `UPDATE` takes an exclusive lock, so it waits for in-flight writers. After it commits, no stale-flag instance can write to that database.
  - **Copy paths skip the fence.** Backfill, drain and repair do not check it.
- **Backfill progress lives in Postgres.** The table is `migration_progress(name PK, last_id, rows_copied, updated_at)`. It is updated in the same Postgres transaction as each batch's upserts, so "last completed batch" is exact. It is not kept in Redis, which is not durable. It is not kept in MySQL either, because it could not be atomic with the batch there.
- **New ids after the switch come from a Postgres sequence.** `users_id_seq` is created at step 1 and unused until the switch. During the switch pause, the coordinator sets it with `setval(GREATEST(current, mysql_auto_increment_counter + 1,000,000))`.
  - **Why above the counter.** The counter is always at or above every id MySQL has issued, including deleted ones. Starting above it means a new id can never collide with a tombstone.
  - **Why the gap.** The extra 1M margin leaves headroom for any ids issued around the pause.
  - **Rollback.** MySQL gets rows with explicit ids, and InnoDB raises its counter to match. Rollback also checks the counter against the highest Postgres id.
- **Email collation.** MySQL's unique `email` is case-insensitive. The Postgres column therefore uses `citext` with a unique index, so Postgres is never looser than MySQL. Check accent-only differences during the first compare pass.

## Steps

- [ ] **1. Create schemas (no behavior change)**
  - **Starts:** a DDL migration run by an engineer.
  - **Changes:**
    - Postgres: `users` (same columns, `id BIGINT PK`, `email citext UNIQUE`, `updated_at timestamp(3)`), `users_tombstones`, `migration_state` (`standby`), `pg_outbox`, `migration_progress`, `migration_compare`, and `users_id_seq`.
    - MySQL: new tables `users_pg_outbox`, `users_tombstones` and `migration_state` (`active`). The `users` table itself is not touched.
  - **State:** the tables themselves.
  - **If it fails:** all DDL is `IF NOT EXISTS`, so re-run it. Nothing reads these tables yet. Drop them to undo.

- [ ] **2. Deploy repository v1 with all flags off**
  - **Starts:** a normal rolling deploy.
  - **Changes:** `UserRepository` gains these things, all inert while flags are off:
    - the fence read;
    - the mode flag `users_write_mode` (`mysql`, `mysql_dual`, `pg_dual`, `pg_only`; default `mysql`);
    - the percentage flag `users_read_pg_pct` (default 0);
    - `pg_copy`, the outbox write and the read fallback.

    Also deploy `users-sync-worker`, the backfill job and the compare job, all idle.
  - **State:** flags (`app.flags`). The fence row in MySQL is `active`.
  - **If it fails:** roll back the deploy. In `mysql` mode with the fence active, behavior is identical to today's, apart from one extra `FOR SHARE` read of the state row per write.
  - **Done when:** 100% of instances run v1 and no old-version instance reports metrics.

- [ ] **3. Turn on dual writes: `users_write_mode=mysql_dual`**
  - **Starts:** a flag change after step 2 is done.
  - **Changes:** every write is now fenced and commits to MySQL together with an outbox row. After commit it is applied to Postgres inline. A Postgres failure is swallowed and the outbox repairs it.
  - **State:** the outbox in MySQL. Repair is automatic via the worker.
  - **Gate:** `app_flag_value{flag="users_write_mode"}` equals `mysql_dual` on every running instance, with no instance missing from the series. Then wait 5 more minutes. That covers the 30 s refresh plus in-flight requests.
  - **If it fails:** set the flag back to `mysql`. Leftover outbox rows are still drained. Anything missed is caught by backfill and compare.

- [ ] **4. Backfill**
  - **Starts:** the backfill job starts itself only when the step 3 gate has held for 5 minutes. It re-checks the gate before every batch and stops if the flag is reverted.
  - **Changes:** one worker takes a Postgres advisory lock. Before each batch it reads `mysql_replica_lag_seconds`. If lag is above 5, or the metric is missing or stale, it sleeps 10 s and re-checks without reading. Otherwise it runs `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` on the replica.
  - **Batch handling:**
    - It drops ids that have a pending outbox row on the primary, or are tombstoned. The worker handles those.
    - It calls `pg_copy` and updates `migration_progress.last_id` to the batch's max id, both in one Postgres transaction. A minimum of 0.5 s between batches limits load, so about 19,000 batches take roughly 5 to 6 hours.
    - On an email unique violation, it retries the batch row by row. Rows that still conflict go into the MySQL outbox for retry.
  - **State:** `migration_progress` in Postgres.
  - **If it fails:** after a crash, a restart continues from `last_id`. Re-copying is safe because the version rule makes it idempotent. A Postgres outage means retries with backoff and no progress change.
  - **Done when:** the read returns zero rows and the outbox is empty.

- [ ] **5. Full comparison, repeated until clean**
  - **Starts:** step 4 is done.
  - **Changes:** the compare job walks 5,000-id windows in both tables and compares `(id, email, name, plan, version)`. It also finds Postgres-only ids and ids that are tombstoned while still present in MySQL. A window with differences is re-read from the MySQL primary and from Postgres after 60 s. Only differences that persist count.
  - **Repair:** each persistent difference becomes an outbox row, so it is fixed automatically.
  - **State:** `migration_compare(run_id, last_id, checked, mismatches)` in Postgres. A crash resumes from the last window.
  - **Gate:** one complete pass with 0 persistent mismatches. Otherwise run another pass.
  - **If it fails:** an equal-version mismatch with different content cannot be repaired under the version rule. It means a bug, so it pages a human and blocks the gate. This is the only manual case.

- [ ] **6. Ramp reads: `users_read_pg_pct` 1 → 10 → 50 → 100**
  - **Starts:** step 5's gate is met. Move to the next stage after the stage's hold time passes and these checks hold: PG read error rate, p99 latency, fallback rate, compare mismatches at 0. Hold 1 hour at 1%, 4 hours at 10% and 1 day at 50%.
  - **Changes:** `flags.enabled_for("users_read_pg_pct", user_id)` sends that bucket of users to Postgres. A Postgres error, or a miss while the percentage is below 100, falls back to the MySQL replica. Reads therefore never fail.
  - **State:** the flag. Run a compare pass every night. Any mismatch pages and blocks step 7.
  - **If it fails:** set the percentage back to the previous value.
  - **Clock:** the 3-day clock starts when `app_flag_value` shows 100 on every instance. Any drop below 100 resets it.

- [ ] **7. Gate for the switch**
  - **Starts:** 100% reads on Postgres for at least 3 days, and a compare pass with 0 mismatches that finished within the last 24 hours.
  - **Also required:** the outbox is under 1 minute old, and the Postgres cluster is healthy. Record the go decision.

- [ ] **8. Switch the source of truth to Postgres (write pause of 45 s or less)**
  - **Starts:** the engineer runs `users_switch.py`, which is idempotent and logs timestamps.
  - **Changes, in order:**
    1. At t=0, set `users_write_mode=pg_dual`. In the same minute, set MySQL state `active→paused`. That `UPDATE` waits for in-flight writers. Writes now get 503: instances still on the old flag read MySQL as paused, and instances on the new flag read Postgres as `standby`.
    2. Drain the MySQL outbox to empty, with the 10 s age gate ignored while the state is `paused`. Confirm it is empty twice, 2 s apart.
    3. `setval` on `users_id_seq` as described above.
    4. Set Postgres state `standby→active` and MySQL state `paused→standby`. Instances that have the new flag now write.
  - **From now on:** writes go to Postgres first. The Postgres transaction contains the fence read, the write and a `pg_outbox` row. After commit, the row is applied to MySQL by the same copy function, mirrored for MySQL with a gap-locking tombstone check. A MySQL failure never fails the request. The workers run in the opposite direction.
  - **Pause length:** the pause lasts until every instance has refreshed its flag. That is at most 30 s, or the drain time if longer.
  - **State:** the fence rows, the flag and the `source_since` timestamp (in Postgres `migration_state`).
  - **If it fails:** abort is allowed only before sub-step 4. If the drain is not empty at t=45 s, set MySQL back to `active` and the flag to `mysql_dual`. Nothing in Postgres has changed. Instances revert within 30 s, so the total pause is 75 s or less. After sub-step 4, go forward or use step 9.
  - **Afterwards:** run a reverse compare pass.

- [ ] **9. Rollback window, at least 14 days of Postgres as source with MySQL kept current**
  - **Starts:** step 8 is finished.
  - **Changes:** nothing. MySQL keeps receiving every write through `pg_outbox`. Watch the outbox age and the compare passes.
  - **Rollback, if needed, again 90 s or less:**
    1. Set `users_write_mode=mysql_dual` and Postgres state `active→paused`.
    2. Drain `pg_outbox` to empty.
    3. If the MySQL `AUTO_INCREMENT` counter is not above the highest Postgres id, run `ALTER TABLE users AUTO_INCREMENT=...`.
    4. Set MySQL state `standby→active` and Postgres state `paused→standby`.
  - **Rollback abort:** the same abort rule applies before sub-step 4. Reads can stay on Postgres.
  - **After a rollback:** the 14-day clock restarts at the next switch.

- [ ] **10. Postgres-only writes: `users_write_mode=pg_only`**
  - **Starts:** at least 14 days after `source_since` (the script refuses earlier), a clean compare pass, and an empty `pg_outbox`.
  - **Changes:** writes stop going to MySQL. There is no pause. Stale-flag instances still do `pg_dual`, which is harmless.
  - **Follow-up:**
    1. After every instance reports `pg_only`, stop the reverse drain.
    2. 24 hours later, revoke the app's write grants on MySQL `users`, to expose stragglers.
  - **If it fails:** setting the flag back to `pg_dual` is allowed, but MySQL then has a gap. Run a reverse compare pass and wait for 0 mismatches before treating rollback as possible again.

- [ ] **11. Drop MySQL `users` and clean up**
  - **Starts:** at least 7 days after step 10, with no MySQL write attempts in the logs.
  - **Changes:** take a final dump (kept per policy), drop the MySQL `users`, outbox and fence tables, remove the migration code, flags and `mysql.replica` read fallback, and drop `pg_outbox`. Keep `users_tombstones`.
  - **If it fails:** nothing depends on the dropped table, so restore from the dump if needed.
