# Move `users` from MySQL 8 to Postgres 16: step-by-step plan

## Design decisions

These decisions apply to every step below.

**1. Write path.**
- While a database is the source of truth (SoT), each write runs in one transaction on that database. The transaction does the following:
  - It reads the control row `users_control` with `FOR SHARE`, and returns a retryable 503 if the state is not "this DB is SoT".
  - It performs the write and re-selects the full row.
  - It inserts a row into `users_sync_outbox(id, user_id, attempts, next_attempt_at)`.
- After commit, the repository tries the other database once, with a 250 ms timeout. On success it deletes the outbox row. On any error it logs, bumps a metric and returns success to the user.
- Every copy is a full-row upsert: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. The MySQL equivalent is `INSERT ... ON DUPLICATE KEY UPDATE` with `IF(version < new.version, ...)` on each column.
- A create copies the MySQL-assigned id.

**2. Repair.**
- Repair is the **outbox sweeper**, a standalone worker with a lease, not the Redis `jobs` queue. The `jobs` queue gives up after about 15 minutes and `enqueue` can raise, and either would leave a manual step.
- The outbox row is committed atomically with the write. It therefore survives a crash between commit and the copy, a Postgres outage and a Redis outage.
- The sweeper takes rows whose `next_attempt_at` has passed, oldest first, and for each `user_id` does the following:
  - It re-reads the current row from the SoT, never from the stale payload.
  - If the row exists, it applies it under the version rule.
  - If the row is absent, it deletes the row on the other side and writes a tombstone there.
  - It then deletes the outbox row.
- Retries never give up. Backoff is capped at 60 seconds.
- An alert fires if the oldest outbox row is older than 5 minutes. The alert is for visibility only, and no manual action is needed.
- Copies are idempotent, so duplicate or out-of-order delivery is harmless.

**3. Deletes.**
- A table `users_tombstone(id)` exists on both sides. It holds ids only, with no personal data.
- The erasure transaction on the SoT does three things: it deletes the row, inserts the tombstone and inserts the outbox row.
- On Postgres, a `BEFORE INSERT OR UPDATE` trigger on `users` takes `pg_advisory_xact_lock(NEW.id)`, then skips the write if a tombstone exists.
- The delete path takes the same lock before it inserts the tombstone.
- This means a stale dual write, backfill batch, repair or comparison fix can never resurrect an erased user, whatever the interleaving.
- On MySQL, the copy transaction first runs `SELECT 1 FROM users_tombstone WHERE id=? FOR SHARE`. That takes a gap lock on the absent key and makes a concurrent tombstone insert wait.
- Tombstones are kept permanently.

**4. Switch coordination (planned switch and rollback).**
- The authority is a DB row, not the 30-second flag cache. Flags only say where each instance should aim.
- `users_control.state` lives on each side and takes the values `sot`, `moving` or `not_sot`.
- Every SoT-first write takes a `FOR SHARE` lock on its side's control row. The switcher's `UPDATE` therefore waits for in-flight writes, then blocks all new ones fleet-wide at once. Flag disagreement cannot cause two sources of truth.
- Instances with a stale flag get a retryable 503 until they refresh. They never write to the wrong side.
- Copies (the second hop) do not check the fence.
- The flag `users.write_mode` takes the values `mysql_only`, `mysql_dual`, `pg_dual` or `pg_only`.
- The switch script does the following:
  1. Set the old side's control row to `moving`. The pause starts here.
  2. Wait for the old side's outbox to be empty.
  3. Prepare the new side.
  4. Set the new side's control row to `sot` and the old side's to `not_sot`.
  5. Flip the flag.
- The script aborts and restores the old side's control row to `sot` if step 2 is not done within 40 seconds of the fence. That abort is a DB write, so it takes effect immediately. It is allowed only before step 4.
- The worst-case pause is about 40 seconds for the fence and drain, plus up to 30 seconds for flag refresh on late instances. That is about 70 seconds against a 90-second limit.
- Reads are never fenced.

**5. Backfill progress.**
- Progress lives in Postgres, in `migration_state(job, last_completed_id, dual_write_all_since, updated_at)`.
- The checkpoint is updated in the same Postgres transaction as the batch upsert. A crash therefore leaves either both or neither, and the batch is idempotent under the version rule.

**6. New ids after the switch.**
- Postgres gets the sequence `users_id_seq`. At the switch it is set to `GREATEST(current, MAX(id) on MySQL primary) + 1,000,000`.
- Postgres then assigns ids and the reverse copy to MySQL passes them explicitly, which also bumps MySQL's AUTO_INCREMENT.
- MySQL assigns no ids while Postgres is SoT, so there are no collisions.
- On rollback, the script sets `AUTO_INCREMENT` to `MAX(id)+1` again.
- On any later re-switch, `setval` takes the `GREATEST` of both sides, so it never moves backwards.

**7. State inventory.**

| State | Where it lives |
|---|---|
| Per-write sync debt | `users_sync_outbox`, on the SoT DB |
| Erasures | `users_tombstone`, on both DBs |
| Who is SoT | `users_control`, on both DBs |
| Backfill checkpoint and gate timestamps | `migration_state`, in Postgres |
| Routing hints | The flags `users.write_mode` and `users.read_pg_percent` |

## Checklist

- [ ] **Step 1. Create schema (additive DDL, no behaviour change).**
  - **Starts when:** a reviewed migration is run by hand once.
  - **Changes:**
    - Postgres gets `users` (same columns, `id BIGINT` with no default, unique `email`, `updated_at timestamptz(3)`), `users_tombstone`, `users_control`, `migration_state`, the lock-and-tombstone trigger, and `users_id_seq` (created but unused).
    - MySQL gets `users_sync_outbox`, `users_tombstone` and `users_control` (state `sot`). The existing `users` table is untouched.
  - **State:** the new tables, all empty.
  - **If it fails:** every statement is idempotent (`IF NOT EXISTS`). Fix and rerun. Nothing reads these tables yet.

- [ ] **Step 2. Deploy the new `UserRepository` and the sweeper worker, with `users.write_mode=mysql_only` and `users.read_pg_percent=0`.**
  - **Starts when:** a normal rolling deploy.
  - **Changes:**
    - The repository gains the control-row check, the outbox insert, the tombstone writes, the Postgres and reverse-MySQL copy paths and the Postgres read path with MySQL fallback. All of it is dormant behind the flags.
    - The sweeper, the backfill job and the comparison job are deployed but not started.
    - With `mysql_only`, behaviour equals today's.
  - **Exit condition:** the deploy has completed on every instance. No instance runs old code, which a version label on `app_flag_value` or the build metric can confirm.
  - **If it fails:** roll back the deploy. No data has moved.

- [ ] **Step 3. Turn on dual writes.**
  - **Starts when:**
    - Step 2 is fully rolled out.
    - The sweeper is running and idle.
    - Postgres health checks are green.
    - A human sets `users.write_mode=mysql_dual`.
  - **Changes:**
    - From the next refresh, each instance writes outbox rows and copies to Postgres.
    - A Postgres failure never fails a request. It leaves an outbox row that the sweeper retries.
  - **Barrier:**
    - `app_flag_value{flag="users.write_mode"}` must show `mysql_dual` on every expected instance.
    - A further 60 seconds must pass, so that in-flight requests started under the old flag finish.
    - A script then writes `dual_write_all_since=now()` into `migration_state`.
  - **State:** the flag, the outbox rows and the `migration_state` timestamp.
  - **If it fails:**
    - If an instance never reports the flag, do not set the timestamp.
    - If problems appear, set the flag back to `mysql_only`. Rows already copied stay and are harmless, and leftover outbox rows are drained by the sweeper.
    - If the flag is ever set below `mysql_dual` after the barrier, the script deletes `dual_write_all_since` and resets the backfill checkpoint to 0. Writes may have been missed, and a rerun is safe under the version rule.

- [ ] **Step 4. Run the backfill.**
  - **Starts when:** the backfill job is launched by an operator. At startup it refuses to run unless `dual_write_all_since` is set and the live flag is still `mysql_dual`.
  - **Changes:**
    - Loop: read `last_completed_id`, then wait while `mysql_replica_lag_seconds` is above 5 or missing (check every 5 seconds before each batch).
    - Then read `SELECT * FROM users WHERE id > :last ORDER BY id LIMIT 2000` from the replica.
    - In one Postgres transaction, upsert the batch under the version rule (tombstones respected) and set `last_completed_id` to the batch's last id.
    - Stop when a batch returns zero rows, then write `backfill_complete_at`.
  - **Why it is safe:**
    - Stale replica rows lose to newer dual-written rows through the version rule.
    - Rows erased since the replica read lose to the tombstone trigger.
  - **State:** `migration_state.last_completed_id` in Postgres.
  - **If it fails:**
    - If the job crashes or its Postgres transaction fails, the transaction rolls back and the checkpoint is unchanged. On restart it continues after the last completed batch.
    - If the replica is lagging or down, the job pauses and resumes by itself.
    - If it is killed repeatedly, the lease on the job lets only one copy run.

- [ ] **Step 5. Full comparison, gate for reads.**
  - **Starts when:** `backfill_complete_at` is set and the oldest outbox row is under 1 minute old.
  - **Changes:**
    - It is read-only, apart from queuing repairs.
    - It walks the id space in both directions in keyset pages (10,000 ids) and compares all columns. It finds missing, extra and differing rows, and it normalises `updated_at` precision.
    - Candidates are re-read from the MySQL primary and Postgres 30 seconds later. Only mismatches that persist count.
    - Persistent mismatches get an outbox row, so the repair is automatic, and the pass does not count as clean.
    - A pass with 0 persistent mismatches writes `compare_clean_at` to `migration_state`.
  - **State:** `migration_state` and a log of mismatches.
  - **If it fails:**
    - If mismatches are found, repair runs automatically and the comparison is run again.
    - If the same mismatch recurs, stop and diagnose the dual-write code. Reads do not move.
    - Comparison runs also pause on replica lag above 5 seconds.

- [ ] **Step 6. Ramp reads to Postgres.**
  - **Starts when:**
    - `compare_clean_at` is less than 24 hours old, and
    - an operator raises `users.read_pg_percent` through 1, 10, 50, then 100.
    - Hold each step until every instance reports it via `app_flag_value`, and until the Postgres error rate and p99 are good for at least 1 hour.
  - **Changes:**
    - `flags.enabled_for("users.read_pg_percent", user_id)` routes that share of reads to Postgres.
    - Any Postgres error, timeout (300 ms) or not-found result falls back to the MySQL replica. Reads therefore never fail.
    - The comparison now runs nightly.
  - **State:** the flag.
  - **If it fails:**
    - Setting the flag to 0 immediately restores MySQL-only reads, since the fallback already exists.
    - If any nightly comparison finds a persistent mismatch, drop reads to 0, repair and rerun from the start of this step.
    - When every instance reports 100, a script records `reads_100_since=now()`.
    - Any later drop below 100 clears `reads_100_since`, which restarts the 3-day clock.

- [ ] **Step 7. Soak at 100% reads for at least 3 days.**
  - **Starts when:** `reads_100_since` is set.
  - **Changes:** nothing is moved. Nightly comparisons continue.
  - **Exit condition:**
    - `now - reads_100_since >= 3 days`.
    - The last comparison is clean and less than 24 hours old.
    - The outbox is empty.
    - The sequence `users_id_seq` exists.
    - A rollback drill has passed in staging.
  - **If it fails:** a failed condition keeps the system in `mysql_dual`, and that state is safe to remain in indefinitely.

- [ ] **Step 8. Switch the source of truth to Postgres (pause of at most 90 seconds).**
  - **Starts when:** an operator runs the switch script, which refuses to run unless Step 7's exit condition holds. The script runs the following sequence:
    1. t=0: set MySQL `users_control.state='moving'`. The statement waits for in-flight writes, then every SoT-first write returns a retryable 503.
    2. Wait for the MySQL outbox to be empty, so every committed MySQL write is in Postgres. Spot-check the 1,000 most recently updated rows and `MAX(id)`.
    3. Set `users_id_seq` to `GREATEST(current, MAX(id) from MySQL primary) + 1,000,000`, then set `users.id` default to `nextval(...)`.
    4. Set Postgres `users_control.state='sot'` and MySQL's to `not_sot`.
    5. Set the flag `users.write_mode=pg_dual`.
  - **Changes after the flag:** Postgres-first writes with a copy to MySQL, using the same outbox and sweeper in the reverse direction (outbox now lives in Postgres). Reads stay on Postgres.
  - **Abort:**
    - If step 2 is not done within 40 seconds, the script sets MySQL back to `sot`, with no flag change needed. Writes resume instantly.
    - After step 4 there is no abort. A late or failed flag flip only prolongs 503s on stale instances for up to 30 seconds (about 70 seconds worst case).
  - **State:** both control rows, the flag, the sequence, and `pg_sot_since=now()` in `migration_state`.
  - **If it fails:** mid-script crash before step 4 leaves `moving`. Rerunning the script's abort path restores `sot`. After step 4, rerun the script to finish step 5, since every step is idempotent.

- [ ] **Step 9. Soak with reverse dual writes for at least 14 days (rollback window).**
  - **Starts when:** all instances report `pg_dual` and `pg_sot_since` is set.
  - **Changes:** Postgres is SoT, MySQL is kept current by the sweeper and the inline copy. Nightly comparison continues.
  - **Rollback (any time before Step 10):** run the mirror image of Step 8.
    1. Fence Postgres.
    2. Drain the Postgres outbox.
    3. Set MySQL `AUTO_INCREMENT` to `MAX(id)+1`.
    4. Set MySQL `sot`.
    5. Set Postgres `not_sot`.
    6. Set the flag `mysql_dual`.
    - The same 40-second abort rule and about 70-second worst case apply, and no write is lost. Reads may stay on Postgres.
    - A later switch restarts the 14-day clock.
  - **If it fails:**
    - If the outbox grows or a nightly comparison shows mismatches, repair is automatic. Do not proceed to Step 10 until the outbox is empty and a comparison is clean.
    - `pg_sot_since` is reset on any rollback.

- [ ] **Step 10. Switch to Postgres-only writes (point of no return for rollback).**
  - **Starts when:**
    - `now - pg_sot_since >= 14 days`.
    - The outbox is empty.
    - The last comparison is clean.
    - An operator sets `users.write_mode=pg_only`.
  - **Changes:**
    - Creates and updates are no longer copied to MySQL.
    - Erasure deletes (with tombstones) keep being copied to MySQL until Step 12, so erased users do not remain in the retired table.
    - No pause is needed, because both modes write to Postgres first. Instances may differ for 30 seconds and that is harmless.
    - Stop copying creates and updates, then revoke the app's MySQL write grants on `users`, except for the erasure job.
  - **State:** the flag and `pg_only_since`.
  - **If it fails:**
    - Reverting to `pg_dual` is possible, but MySQL then lacks the writes made since Step 10.
    - Before rolling back, run a Postgres-to-MySQL comparison-and-repair pass until it is clean, then do the Step 9 rollback.

- [ ] **Step 11. Remove MySQL code paths and migration machinery.**
  - **Starts when:** Step 10 has been stable for at least 7 days.
  - **Changes:** the repository drops the MySQL reads and writes, the control-row checks and the reverse copy. The sweeper, backfill and comparison jobs are stopped.
  - **If it fails:** revert the deploy. The flag state is unchanged, so MySQL data is still present.

- [ ] **Step 12. Drop the MySQL table, after all of the above.**
  - **Starts when:** Step 10 is complete (14 days after Postgres became SoT) and Step 11 is deployed. An operator renames `users` to `users_retired`, waits 7 more days and then drops it, along with the outbox and control tables.
  - **Changes:** the MySQL `users` data is gone, including backups per retention policy.
  - **If it fails:** the rename is reversible. After the drop, the data is only recoverable from backup.
