# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Summary

Today every read and write of `users` goes through `UserRepository`. Writes go to the MySQL primary, and reads go to the MySQL replica. Postgres (`pg-core`) is empty.

The main flow has five stages:
1. Make every write also reach Postgres, with MySQL still the source of truth.
2. Copy the historical rows.
3. Prove the two tables match.
4. Move reads to Postgres.
5. Move the source of truth to Postgres, keep MySQL mirrored for 14 days so we can roll back, then stop writing MySQL and drop it.

Reads never fail. Writes pause for at most 90 seconds each time the source of truth changes. During a pause, writes get a retryable 503, which our clients already retry.

## Terms

- **version:** the integer column already on `users`. It starts at 1, and `UserRepository.update` adds 1 on each update. Postgres gets the same column. No column is added.
- **Flags:** `app.flags`. Each app instance caches them and refreshes every 30 s, so instances can disagree for up to 30 s. Each instance exports the values it uses as the metric `app_flag_value{flag=...}`.
- **Outbox:** a table of user ids whose copy to the other database may be missing. It is written in the same transaction as the user write. MySQL has `users_sync_outbox`. Postgres has `users_mirror_outbox`, used after the switch.
- **Drainer:** a permanent worker that reads outbox rows and copies the current user row to the other database. It keeps running even if dual writes are turned off.
- **Tombstone:** the Postgres table `users_tombstone(id)`. It holds ids only, with no personal data. An erased user's id is recorded there so a stale copy can never bring the user back. Ids are never reused.
- **Fence:** a one-row open/closed switch per database (MySQL `users_write_fence`; Postgres `migration_state.pg_write_open`). Every user write takes a shared lock on the fence of the database it writes to, and returns 503 if it is closed. Closing the fence takes an exclusive lock, so it waits for in-flight writes and then stops new ones on every instance at once.
- **Orchestrator:** the deploy platform, which knows how many app instances are running.

## Rules that hold throughout

- **Repair:** the outbox, not the Redis job queue. `jobs.enqueue` fails when Redis is down, and failed jobs end in `jobs:dead`, which nothing processes. The outbox row commits with the write, so a committed write cannot lose its repair record. The outbox holds only the user id, and the drainer always copies the current row from the source of truth. So repair is idempotent, and order does not matter.
- **Version rule:** every copy into a database (dual write, drainer, backfill, compare repair) is `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`, and also requires that the id is not in the tombstone. The check and the write run under `pg_advisory_xact_lock(id)`, so a stale row cannot slip in between them.
- **Only user writes are fenced.** Sync copies skip the fence. The version rule and the tombstone make them safe.
- **Flags only trigger the switch.** Correctness comes from the fences. An instance with a stale flag gets 503. It never writes to the wrong database.
- **New ids** come from the Postgres sequence `users_id_seq`. At the switch it is set to `GREATEST(MySQL AUTO_INCREMENT, max Postgres id) + 100000`. The margin means no id is reused, and gaps are already normal. On rollback, MySQL's counter is set the same way.
- **Email uniqueness:** Postgres uses `citext` (or a unique index on `lower(email)`), because MySQL's collation is case-insensitive.
- **Persistent drain failure:** the drainer retries forever, with backoff capped at 30 s. A row that keeps failing is retried every 5 minutes with `attempts` incremented, and raises an alert. The usual cause is an email conflict. User B now has an email that Postgres still shows on user A, because A's change is not copied yet. Copying A's row resolves it.
- **Outbox age alerts:** warn at 2 minutes, page at 10 minutes.

## Rollout steps

### Phase A: Preparation

- [ ] **1. Create the schemas (additive only).**
  - **Starts when:** manual DDL through the normal migration tooling.
  - **Does:**
    - Postgres: `users` (same columns; `id BIGINT PRIMARY KEY`, no default yet), `users_tombstone`, `users_mirror_outbox`, and `migration_state`.
    - `migration_state` is one row: `backfill_last_id`, `backfill_done`, `compare_cursor`, `compare_last_clean_pass_at`, and `pg_write_open` (false). This row is also the Postgres fence.
    - MySQL: `users_sync_outbox(seq, user_id, attempts, created_at)` and `users_write_fence(open)`, one row, open.
    - The existing `users` table is not altered.
  - **State:** the objects above.
  - **If it fails:** nothing uses them yet. The DDL uses `IF NOT EXISTS`, so fix and re-run.
  - **Before step 9, confirm** that Postgres has a synchronous standby and tested backups. After the switch, Postgres is the only place new writes are guaranteed to exist until they are mirrored.

- [ ] **2. Deploy the migration-aware code, with all flags off.**
  - **Starts when:** a normal deploy. The flags are:
    - `users_dual_write` (percentage, default 0)
    - `users_write_mode` (`mysql_primary` | `pg_primary` | `pg_only`, default `mysql_primary`)
    - `users_read_pg` (percentage, default 0)
    - `users_backfill` (boolean, default false)
  - **Does:** `UserRepository` gains:
    - the fence check in every write transaction;
    - the outbox insert in the same transaction, when dual write applies;
    - a Postgres apply after commit (250 ms timeout, errors swallowed, so it can never fail the request);
    - a circuit breaker that skips Postgres for 10 s after repeated failures;
    - read fallback to the MySQL replica on a Postgres error or miss.
  - The drainer, backfill and compare workers are deployed as separate processes. Backfill and compare stay idle until later steps.
  - **How the drainer works:**
    1. It polls the outbox in batches with `FOR UPDATE SKIP LOCKED`.
    2. It groups rows by `user_id` and notes the highest `seq` for each.
    3. It reads the current row from the MySQL primary.
    4. If the row exists, it applies the version rule. If not, it deletes the Postgres row and writes the tombstone, in one transaction.
    5. Then it deletes outbox rows up to that `seq`.
  - **State:** flags in `app.flags`; outbox and fence in MySQL. A new instance shows it runs the new code by exporting `app_flag_value{flag="users_write_mode"}`. Old instances do not export it.
  - **If it fails:** roll back the deploy. With flags off, behaviour is the same as today, apart from a shared lock on a one-row table.

### Phase B: Dual writes

- [ ] **3. Ramp dual writes to 100%.**
  - **Starts when:** every instance exports `app_flag_value` (step 2 done everywhere).
  - **Does:** set `users_dual_write` to 1%, 10%, then 100%, holding each stage for at least 15 minutes with clean checks. Buckets are by `user_id`, so a user stays in the same bucket as the percentage grows.
  - **One write for a user in the bucket:**
    1. Open the MySQL transaction.
    2. Take the shared lock on the fence. Abort with 503 if it is closed.
    3. Do the write. For an update, read the full new row in the same transaction.
    4. Insert the outbox row.
    5. Commit.
    6. Apply to Postgres with the version rule and tombstone check.
    7. If that succeeded, delete the outbox row.
  - If step 6 fails or is skipped, the row stays and the drainer copies the then-current MySQL row.
  - A create copies the row with its MySQL-assigned id. A delete writes the outbox row, and then the Postgres delete and tombstone follow.
  - The drainer may pick up a row while the inline apply runs. That is harmless. The per-id lock serialises them, and the version rule makes the second copy a no-op.
  - Users outside the bucket write to MySQL only, and Postgres may be incomplete for them. Backfill (step 5) copies them. A user erased before then is gone from MySQL, so backfill never copies them.
  - **State:** the outbox in MySQL.
  - **If it fails:** a Postgres error never reaches the user. The outbox row stays and the drainer fixes it. If the inline attempt is slow, the breaker skips it and the drainer does all the copying (about 1 s delay). A crash after commit is covered by the outbox. For a bug in the new path, set `users_dual_write` to 0. Remaining outbox rows are still drained.

- [ ] **4. Gate: every instance is dual-writing.**
  - **Starts when:** `users_dual_write` is 100.
  - **Does:** a script checks, for 2 consecutive minutes, that:
    - the number of instances reporting `users_dual_write=100` equals the orchestrator's running instance count (this also proves no old-code instance is left);
    - no deploy is in progress;
    - the oldest outbox row is younger than 1 minute.
  - It changes nothing and records the result.
  - **If it fails:** wait, or restart the instance that is behind. Do not start step 5.

### Phase C: Backfill

- [ ] **5. Backfill about 38M rows.**
  - **Starts when:** the step 4 gate has passed and an operator sets `users_backfill=true`.
  - **Does:** one worker holds a Postgres advisory lock for its whole run, so a second copy cannot start. It loops:
    1. If `mysql_replica_lag_seconds` is above 5, sleep 10 s and re-check. Reporting jobs share the replica.
    2. Read `SELECT * FROM users WHERE id > :last ORDER BY id LIMIT 2000` from the replica.
    3. In one Postgres transaction, lock the batch's ids in ascending order, apply each row with the version rule and tombstone check, and set `backfill_last_id` to the batch's highest id.
  - A row that fails (an email conflict, for example) is skipped and its id goes into the MySQL outbox. The drainer repairs it (see the persistent-failure rule above). Backfill never waits for it.
  - Stale replica rows are harmless. The version rule ignores them, and the tombstone blocks erased users.
  - A batch of fewer than 2,000 rows means the end is reached, and the worker sets `backfill_done`.
  - **State:** `migration_state.backfill_last_id`, committed together with each batch, so "last completed batch" is exact.
  - **If it fails:**
    - **Crash:** the restarted worker continues after `backfill_last_id`.
    - **Postgres error:** the transaction rolls back, the cursor does not move, and the batch is retried with backoff.
    - **Lag above 5 s:** it pauses, with no error.
    - **Stop:** set `users_backfill=false`. The worker stops after its current batch.

### Phase D: Verify

- [ ] **6. Compare the tables until one full pass finds zero mismatches.**
  - **Starts when:** `backfill_done` is set and the oldest outbox row is under 1 minute old.
  - **Does:** the compare worker walks ids in chunks of 10,000. For each chunk it compares a checksum of `(id, email, name, plan, version)` from the replica against Postgres. The replica lag guard from step 5 applies. It also finds Postgres rows that are gone from MySQL. When a chunk differs:
    1. Compare it row by row and list the differing ids.
    2. Wait 60 s, then re-read those rows from the MySQL primary and compare again.
    3. If they now match, it was a write in flight or replica lag. Do not count it.
    4. If they still differ, count a mismatch and insert the id into the MySQL outbox. The drainer repairs it, or deletes it and writes the tombstone if the row is gone from MySQL.
  - **State:** `compare_cursor` and the mismatch count. `compare_last_clean_pass_at` is set only when a whole pass ends with 0 counted mismatches.
  - **If it fails:**
    - **Mismatches found:** they are repaired, and a new full pass starts. A pass that found any does not count.
    - **Crash:** it resumes from `compare_cursor`.
    - **Mismatches that keep coming back:** stop and investigate. It is a bug in the dual-write path.
  - The worker keeps running about one pass per day until step 11. It pauses only during switches (steps 9 and 10).

### Phase E: Reads move

- [ ] **7. Ramp reads to Postgres.**
  - **Starts when:** `compare_last_clean_pass_at` is set.
  - **Does:** set `users_read_pg` to 1%, 10%, 50%, then 100%. Hold each stage for at least 30 minutes, with the metric showing all instances on the new value. Bucketing is by `user_id`. A Postgres error, timeout or miss falls back to the MySQL replica for that request. Watch the read error rate, p99 latency, fallback rate and outbox age.
  - **State:** the flag only.
  - **If it fails:** set `users_read_pg` to 0, and instances are back on MySQL within 30 s. A Postgres outage is covered by the fallback and raises an alert. Any drop below 100 restarts the clock in step 8.

- [ ] **8. Soak at 100% for at least 3 days.**
  - **Starts when:** all instances report `users_read_pg=100`. Record that time as T0.
  - **Does:** nothing. The compare worker keeps running.
  - **Continue to step 9 only if** 3 days have passed since T0, reads stayed at 100% throughout, the latest compare pass is clean and under 24 hours old, and the outbox age stayed under 1 minute.
  - **If it fails:** extend the soak, or follow the step 7 failure path.

### Phase F: The source of truth moves

- [ ] **9. Switch writes to Postgres (pause about 45 s; hard limit 90 s).**
  - **Starts when:** the step 8 conditions hold, an operator is present, and the standby and backups are confirmed (step 1). One script, `switch_to_pg`, runs the sequence and aborts if a 30 s deadline is missed. Here t0 is the moment the fence closes.
  - **Does:**
    1. **t0: close the MySQL fence** (`UPDATE users_write_fence SET open=0`, lock wait timeout 10 s). In-flight writes finish, then every MySQL write on every instance returns 503. Reads are untouched. Pause the compare worker, so only the drainer adds outbox rows.
    2. **Drain the outbox to zero.** The script polls the row count. With the fence closed and compare paused, no new rows appear. It normally takes a second or two. Every committed MySQL write is now in Postgres.
    3. **Spot-check** 10,000 random ids against Postgres.
    4. **Set the sequence:** `setval('users_id_seq', GREATEST(MySQL AUTO_INCREMENT, max pg id) + 100000)`.
    5. **Open the Postgres fence** (`pg_write_open=true`).
    6. **Set `users_write_mode=pg_primary`.** This comes after step 5, so any instance that picks it up finds the Postgres fence open. Instances pick it up within 30 s. Meanwhile an instance still on `mysql_primary` finds the MySQL fence closed and returns 503. An instance on `pg_primary` writes to Postgres.
    7. Wait until all instances report `pg_primary`. Restart any that do not. Resume the compare worker.
  - **A write in `pg_primary` mode** takes the shared lock on the Postgres fence, which returns 503 while it is closed. Then:
    - **Create:** the id is `nextval('users_id_seq')`.
    - **Update:** `UPDATE ... SET version = version + 1 WHERE id = ? AND version = ?`. If no row matches, raise `StaleWrite`.
    - **Delete:** delete in Postgres and write the tombstone.
    - All three also write a `users_mirror_outbox` row in the same Postgres transaction. The change is then applied to MySQL inline (250 ms timeout, errors ignored) with the version rule. A created row keeps its explicit Postgres id and version. The mirror drainer repairs misses forever, as in step 2.
  - **Clients:** during the pause, writes get a retryable 503 and the client retries. Reads keep working through Postgres or the fallback.
  - **Pause budget:** about 10 s for steps 1 to 5, plus at most 30 s of flag propagation. That is roughly 45 s per instance.
  - **State:** the sequence, both fences, `users_write_mode`.
  - **If it fails:**
    - **Before sub-step 5, or a deadline missed:** the script reopens the MySQL fence. Postgres was never the source of truth, so nothing is lost.
    - **After sub-step 5:** use the rollback in step 10, a second pause under the same 90 s limit.
    - **Script crash:** the fences are the state, and at most one is open, so there is no split brain. An operator reruns the script from the recorded step.
  - **From now on, if Postgres is down, writes get 503.** That is correct while Postgres is the source of truth. Reads continue through the fallback.

### Phase G: Rollback window (14 days)

- [ ] **10. Hold the rollback window; roll back if needed.**
  - **Starts when:** step 9 completes. Record that time as T1.
  - **Does:** all writes go to Postgres first and are mirrored to MySQL, so MySQL stays complete. The mirror drainer and the compare worker (both directions) run continuously.
  - **Rollback, `switch_to_mysql` (the same script with roles reversed):**
    1. Close the Postgres fence (`pg_write_open=false`) and pause the compare worker.
    2. Drain `users_mirror_outbox` to zero.
    3. Run `ALTER TABLE users AUTO_INCREMENT = (sequence last value + 100000)` on MySQL.
    4. Open the MySQL fence.
    5. Set `users_write_mode=mysql_primary`.
  - Dual writes then run MySQL to Postgres again. The pause is about 45 s. No write is lost, because the mirror outbox is drained before MySQL reopens.
  - **State:** the outbox, both fences and the flags, as in step 9.
  - **If it fails:**
    - **Mirror backlog:** it grows but is safe, with alerts at the usual thresholds. Rollback waits for it to drain. That is the cost of lossless rollback.
    - **Rollback fails before sub-step 4:** reopen the Postgres fence.
    - **Rollback during a Postgres outage:** it cannot drain and cannot finish. The standby from step 1 is the protection.

### Phase H: Final cut-over

- [ ] **11. Switch to Postgres-only writes (the point of no return).**
  - **Starts when:** at least 14 days after T1, and:
    - the mirror outbox is empty;
    - a clean compare pass is under 24 hours old;
    - there was no rollback in the window (a rollback sets a new T1 at the next step 9);
    - the team has explicitly approved.
  - **Does:** set `users_write_mode=pg_only`. Instances stop writing the mirror outbox and stop applying to MySQL. Read fallback to the MySQL replica is switched off, because it would be stale. When all instances report `pg_only`, wait for the mirror outbox to reach zero, then stop the mirror drainer and the compare worker. There is no pause, because MySQL simply stops being updated.
  - **State:** the flag, plus Postgres.
  - **If it fails:** until the flag has reached every instance, setting it back to `pg_primary` restores the mirror, and the drain catches up. Once the mirror drainer is stopped, rolling back to MySQL needs a rebuild. This step is irreversible.

- [ ] **12. Decommission MySQL.**
  - **Starts when:** step 11 is done and a clean week of metrics has passed.
  - **Does, in order:**
    1. Deploy a cleanup release that removes the MySQL branches, fences, outbox code and migration flags from `UserRepository`. The `no-raw-users-sql` lint rule stays.
    2. Drop `core.users`, `users_sync_outbox` and `users_write_fence` from MySQL.
    3. Remove `users_mirror_outbox` and the migration rows from Postgres. Keep `users_tombstone`.
    4. Keep no copy of `core.users` beyond normal backup retention, so erased users do not persist in a long-lived dump.
  - **State:** none left. Postgres is the only copy.
  - **If it fails:** a deploy fault is rolled back with the normal tooling. Dropping the table is irreversible, so it comes last.

## Open questions

- Which system supplies the orchestrator's running instance count in step 4 is not specified. Confirm it before step 4 is automated.
