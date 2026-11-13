# Move `users` from MySQL 8 to Postgres 16: step-by-step plan

## Summary

Today every read and write of `users` goes through one class, `UserRepository`. Reads go to the MySQL read replica. Writes go to the MySQL primary. `create` inserts `version` 1 and MySQL assigns the id. `update` adds 1 to `version` and raises `StaleWrite` if the caller's expected version no longer matches. The GDPR erasure job hard-deletes rows (about 2,000 a day).

We move the table to the empty Postgres 16 cluster `pg-core` with no downtime. All logic lives in `UserRepository`. The order is:

1. Deploy code that can write to both databases, switched off.
2. Turn on dual writes.
3. Copy the old rows (backfill).
4. Compare the two tables.
5. Move reads to Postgres.
6. Move the source of truth with a short write pause.
7. Wait out a rollback window.
8. Retire MySQL.

The plan is cautious on purpose. MySQL stays the source of truth until Postgres has proven itself, and every move can be undone until the Postgres-only step.

## Terms

- **SoT (source of truth):** the database whose copy of a user wins. A write commits there first.
- **Copy:** applying a row written on the SoT to the other database.
- **Version rule:** a copy may only insert a missing row, or replace a row whose `version` is lower than the incoming one. The app sets `version` (1 on create, +1 on each update). The databases only store it. A copy carries it unchanged.
- **Outbox:** the table `users_sync_outbox(id, user_id, attempts, next_attempt_at)`, present on both databases. Only the SoT's outbox gets rows. A row means "this user still needs copying to the other database". It is written in the same transaction as the write, so it is never lost.
- **Sweeper:** a standalone worker that processes outbox rows on both databases. It is the automatic repair. It does not use the Redis `jobs` queue, which gives up after about 15 minutes and whose `enqueue` can raise. Either would leave a manual step.
- **Tombstone:** a row in `users_tombstone(id)` (ids only, no personal data) on both databases. It means "this user was erased and must never come back". Kept permanently.
- **Control row:** `users_control.state` on each database: `sot`, `moving` or `not_sot`. It decides where writes may go.
- **Flags:** `users.write_mode` (`mysql_only`, `mysql_dual`, `pg_dual`, `pg_only`) and `users.read_pg_percent` (0-100). Each instance caches flags and refreshes them every 30 seconds, so instances can disagree for up to 30 seconds. Flags only say where an instance aims first. The metric `app_flag_value{flag=...}` shows what each instance is using.
- **`migration_state`:** a Postgres table holding `last_completed_id` (the backfill checkpoint) and the gate timestamps `dual_write_all_since`, `backfill_complete_at`, `compare_clean_at`, `reads_100_since`, `pg_sot_since` and `pg_only_since`.
- **Backfill:** a job that copies all old rows from the MySQL replica into Postgres, in id order.
- **Comparison:** a read-only job that compares the two tables and queues repairs for differences.

## How the system runs

**1. Write path.**
- The flag picks which database the instance writes first. In one transaction on that database it:
  - reads that database's control row with `FOR SHARE` and returns a retryable 503 unless the state is `sot`;
  - performs the write and re-selects the full row;
  - inserts an outbox row.
- An `update` with a stale expected version changes no row. It raises `StaleWrite` as today, with no outbox row and no copy. This holds on either SoT.
- After commit, it tries the copy once, with a 250 ms timeout. On success it deletes the outbox row. On any error it logs, bumps a metric and still returns success. A Postgres failure never fails a request.
- Every copy is a full-row upsert under the version rule. Postgres: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. MySQL: `INSERT ... ON DUPLICATE KEY UPDATE` with `IF(version < new.version, ...)` on each column.
- A create copies the id the SoT assigned. MySQL `users` already has the same columns, so copying a Postgres-assigned id is a plain insert.
- Copies do not check the control row. A copy that timed out but succeeded, or a process that died after copying, leaves the outbox row. The sweeper repeats the copy, which does nothing, then deletes the row.

**2. Repair (the sweeper).**
- One deployment polls the outbox on both databases. A row means "copy this user from the database holding this outbox to the other one". It does not need to know which side is the SoT.
- Several sweepers may run. Each claims a batch with `SELECT ... FOR UPDATE SKIP LOCKED` on rows whose `next_attempt_at` has passed, oldest first. If one dies, its claim is released. Copies are idempotent, so repeats and reordering are harmless.
- For each `user_id` it re-reads the current row from the database holding the outbox row.
  - If the row exists, it applies it to the other database under the version rule.
  - If the row is absent, it writes the tombstone on the other side and then deletes the row there, in one transaction.
  - Then it deletes the outbox row.
- Retries never give up. Backoff is capped at 60 seconds. An alert fires if the oldest outbox row is over 5 minutes old. It is for visibility only.

**3. Deletes.**
- Only the erasure job deletes. Its transaction on the SoT deletes the row, inserts the tombstone and inserts an outbox row. The copy (inline or by the sweeper) writes the tombstone, then deletes the row, on the other side.
- This is a normal SoT write, so it reads the control row and gets the same 503 during a switch pause. The job fails and the job queue retries it with backoff (about 15 minutes in total, far longer than the 90-second pause).
- Postgres: a `BEFORE INSERT OR UPDATE` trigger on `users` takes `pg_advisory_xact_lock(NEW.id)` and skips the write if a tombstone exists. The delete path takes the same lock before inserting the tombstone.
- MySQL: a copy first runs `SELECT 1 FROM users_tombstone WHERE id=? FOR SHARE`. This gap-locks the absent key, so a concurrent tombstone insert waits.
- So no stale dual write, backfill batch, repair or comparison fix can bring back an erased user.

**4. Switching the source of truth (planned switch and rollback).**
- Every SoT-first write holds `FOR SHARE` on its side's control row. The switcher's `UPDATE` waits for in-flight writes, then blocks all new ones on every instance at once.
- An instance with a stale flag still aims at the old side, sees `moving` or `not_sot`, and returns a retryable 503 until its flag refreshes. It never writes to the wrong side. Clients already retry 503s. Reads are never fenced.
- The switch script:
  1. Set the old side's control row to `moving`. The pause starts.
  2. Wait for the old side's outbox to be empty.
  3. Prepare the new side.
  4. Set the new side to `sot` and the old side to `not_sot`.
  5. Flip the flag.
- Abort: if step 2 is not done within 40 seconds, the script sets the old side back to `sot`. Writes resume at once and the 503s end by themselves, because clients retry. Leftover outbox rows stay for the sweeper. Abort is allowed only before step 4.
- Worst case: 40 seconds for fence and drain, plus up to 30 seconds for late flag refresh, about 70 seconds against the 90-second limit.

**5. Backfill progress.** `last_completed_id` is updated in the same Postgres transaction as the batch upsert. A crash leaves both or neither. A repeated batch is harmless under the version rule.

**6. New ids after the switch.**
- Postgres has the sequence `users_id_seq`. At the switch it is set to `GREATEST(current, MAX(id) on MySQL primary) + 1,000,000`.
- Postgres then assigns ids, and the reverse copy passes them to MySQL explicitly, so there are no collisions. `update` bumps `version` the same way as today.
- On rollback the script sets MySQL `AUTO_INCREMENT` to `MAX(id)+1`. On any later switch the sequence takes the larger of both sides, so it never goes backwards.

**7. Where state lives.**

| State | Where |
|---|---|
| Per-write sync debt | `users_sync_outbox`, on the SoT (the table exists on both) |
| Erasures | `users_tombstone`, on both |
| Who is SoT | `users_control`, on both |
| Backfill checkpoint, gate timestamps | `migration_state`, in Postgres |
| Routing hints | the two flags |

## When things fail

| Where | What happens |
|---|---|
| Postgres copy fails or times out | The user still gets success. The outbox row stays and the sweeper retries forever. |
| Process dies after commit | The outbox row stays and the sweeper repairs. |
| `update` with a stale expected version | `StaleWrite` goes to the caller as today. No outbox row, no copy. |
| Redis down | No effect. The sweeper does not use Redis. |
| Flag disagreement between instances | The control row decides. Stale instances get a retryable 503, never a wrong-side write. |
| Switch drain too slow | At 40 seconds the script restores `sot`. Writes resume at once. |
| Erasure job hits the switch pause | It gets the 503, fails, and the job queue retries it after the pause. |
| Backfill crash | It continues from the last completed batch. |
| Replica lag above 5 seconds | Backfill and comparison pause and resume by themselves. |

## Rollout checklist

- [ ] **Step 1. Create schema (additive DDL, no behaviour change).**
  - **Starts when:** a reviewed migration is run by hand once.
  - **Changes:** Postgres gets `users` (same columns, `id BIGINT` with no default, unique `email`, `updated_at timestamptz(3)`), `users_sync_outbox`, `users_tombstone`, `users_control` (state `not_sot`), `migration_state`, the trigger and `users_id_seq` (unused for now). MySQL gets `users_sync_outbox`, `users_tombstone` and `users_control` (state `sot`). MySQL `users` is untouched. Both outboxes are created now so the switch needs no schema change.
  - **If it fails:** all statements are idempotent (`IF NOT EXISTS`). Fix and rerun. Nothing reads these tables yet.

- [ ] **Step 2. Deploy the new `UserRepository` and the sweeper, with `users.write_mode=mysql_only` and `users.read_pg_percent=0`.**
  - **Starts when:** a normal rolling deploy.
  - **Changes:** the repository gains the control-row check, outbox insert, tombstone writes, both copy paths and a Postgres read path with MySQL fallback. All of it is dormant behind the flags. The backfill and comparison jobs are deployed but not started. Behaviour equals today's.
  - **Exit condition:** every instance runs the new code (confirmed by the build metric).
  - **If it fails:** roll back the deploy. No data has moved.

- [ ] **Step 3. Turn on dual writes.**
  - **Starts when:** Step 2 is fully out, the sweeper is running and idle, Postgres health is green, and a human sets `users.write_mode=mysql_dual`.
  - **Changes:** from the next refresh, each instance writes outbox rows and copies to Postgres.
  - **Barrier:** `app_flag_value{flag="users.write_mode"}` shows `mysql_dual` on every expected instance. Wait 60 more seconds so requests started under the old flag finish. Then a script writes `dual_write_all_since=now()`.
  - **Why the barrier:** if an instance still wrote only to MySQL after the backfill passed a row, that write would never reach Postgres.
  - **If it fails:**
    - If an instance never reports the flag, do not set the timestamp.
    - If problems appear, set the flag back to `mysql_only`. Copied rows are harmless and the sweeper drains leftover outbox rows.
    - If the flag ever drops below `mysql_dual` after the barrier, the script deletes `dual_write_all_since` and resets the checkpoint to 0. Writes may have been missed, and a rerun is safe.

- [ ] **Step 4. Run the backfill.**
  - **Starts when:** an operator launches the job. It refuses to run unless `dual_write_all_since` is set and the live flag is still `mysql_dual`.
  - **Changes:**
    - Loop: read `last_completed_id`, then wait while `mysql_replica_lag_seconds` is above 5 or missing (check every 5 seconds before each batch).
    - Read `SELECT * FROM users WHERE id > :last ORDER BY id LIMIT 2000` from the replica.
    - In one Postgres transaction, upsert the batch under the version rule (tombstones respected) and set `last_completed_id` to the batch's last id.
    - When a batch returns zero rows, write `backfill_complete_at`.
  - **Why it is safe:** stale replica rows lose to newer dual-written rows through the version rule. Rows erased since the read lose to the tombstone trigger. Two accidental copies of the job do the same idempotent work.
  - **If it fails:** a crash or failed transaction leaves the checkpoint unchanged, and a restart continues after the last completed batch. A lagging or down replica makes the job pause and resume by itself.

- [ ] **Step 5. Full comparison (gate for reads).**
  - **Starts when:** `backfill_complete_at` is set and the oldest outbox row is under 1 minute old.
  - **Changes:** read-only, apart from queuing repairs.
    - Two walks in keyset pages of 10,000 ids. One goes over the SoT's ids and checks each exists and matches on the other side. The other goes over the other side's ids and checks each exists on the SoT (this finds extra rows, such as erased users).
    - It compares all columns, normalising `updated_at` precision.
    - Candidates are re-read from the MySQL primary and Postgres 30 seconds later. Only persistent mismatches count.
    - A candidate with a pending outbox row on either side is not a mismatch, because the sweeper is still copying it.
    - Each persistent mismatch with no outbox row gets one, and the pass is not clean. A pass with zero persistent mismatches writes `compare_clean_at`.
  - **If it fails:** repair runs automatically, then compare again. If the same mismatch recurs, stop and diagnose the dual-write code. Reads do not move. Comparison also pauses on replica lag above 5 seconds.

- [ ] **Step 6. Ramp reads to Postgres.**
  - **Starts when:** `compare_clean_at` is under 24 hours old and an operator raises `users.read_pg_percent` through 1, 10, 50, then 100. Hold each level until every instance reports it and Postgres error rate and p99 are good for at least 1 hour.
  - **Changes:** `flags.enabled_for("users.read_pg_percent", user_id)` routes that share of reads to Postgres. Any Postgres error, 300 ms timeout or not-found falls back to the MySQL replica, so reads never fail. Comparison now runs nightly. When every instance reports 100, a script records `reads_100_since=now()`.
  - **Stale reads accepted:** if an inline copy failed, a Postgres read returns the old row (it exists, so no fallback) until the sweeper copies the update, normally within seconds. Replica reads can already lag about a second, and the brief does not require read-your-writes.
  - **If it fails:** set the flag to 0 to restore MySQL-only reads at once. If a nightly comparison finds a persistent mismatch, drop reads to 0, repair and restart this step. Any drop below 100 clears `reads_100_since`, which restarts the 3-day clock.

- [ ] **Step 7. Soak at 100% reads for at least 3 days.**
  - **Starts when:** `reads_100_since` is set.
  - **Changes:** nothing moves. Nightly comparisons continue.
  - **Exit condition:** `now - reads_100_since >= 3 days`, the last comparison is clean and under 24 hours old, the outbox is empty, `users_id_seq` exists, and a rollback drill has passed in staging.
  - **If it fails:** the system stays in `mysql_dual`, which is safe indefinitely.

- [ ] **Step 8. Switch the source of truth to Postgres (write pause of at most 90 seconds).**
  - **Starts when:** an operator runs the switch script, which refuses to run unless Step 7's exit condition holds. It follows the switch sequence above:
    1. Set MySQL `moving`. Writes now get a retryable 503.
    2. Wait for the MySQL outbox to be empty. Spot-check the 1,000 most recently updated rows and `MAX(id)`.
    3. Set `users_id_seq` as described under new ids, then set the `users.id` default to `nextval(...)`.
    4. Set Postgres `sot` and MySQL `not_sot`.
    5. Set `users.write_mode=pg_dual`.
  - **Changes after the flag:** writes go to Postgres first and are recorded in the Postgres outbox. The same sweeper copies them to MySQL. Reads stay on Postgres.
  - **State:** both control rows, the flag, the sequence, and `pg_sot_since=now()`.
  - **If it fails:** before step 4, abort as described above. A script crash leaves `moving`, and rerunning the abort path restores `sot`. After step 4 there is no abort. Rerun the script to finish step 5, since every step is idempotent. Stale instances get 503s for up to 30 more seconds.

- [ ] **Step 9. Soak with reverse dual writes for at least 14 days (rollback window).**
  - **Starts when:** all instances report `pg_dual` and `pg_sot_since` is set.
  - **Changes:** Postgres is SoT. MySQL is kept current by the inline copy and the sweeper. Nightly comparison continues.
  - **Rollback (any time before Step 10):** the mirror image of Step 8. Fence Postgres, drain the Postgres outbox, set MySQL `AUTO_INCREMENT` to `MAX(id)+1`, set MySQL `sot`, set Postgres `not_sot`, set the flag `mysql_dual`. Same 40-second abort rule and about 70-second worst case. No write is lost. Reads may stay on Postgres. Rollback resets `pg_sot_since`, so a later switch restarts the 14-day clock.
  - **If it fails:** if the outbox grows or a comparison shows mismatches, repair is automatic. Do not go to Step 10 until the outbox is empty and a comparison is clean.

- [ ] **Step 10. Switch to Postgres-only writes (point of no return for rollback).**
  - **Starts when:** `now - pg_sot_since >= 14 days`, the outbox is empty, the last comparison is clean, and an operator sets `users.write_mode=pg_only`.
  - **Changes:**
    - A create or update writes to Postgres and still reads the Postgres control row (still `sot`, so harmless until Step 11). It inserts no outbox row and makes no copy, because an outbox row would never be drained.
    - Then the app's MySQL write grants on `users` are revoked, except for the erasure copy.
    - Erasure deletes still insert the tombstone and an outbox row, and are copied to MySQL until Step 12, so erased users do not linger in the retired table. The sweeper handles only these rows now.
    - No pause is needed, because both modes write to Postgres first. Instances may differ for 30 seconds, which is harmless.
  - **State:** the flag and `pg_only_since`.
  - **If it fails:** reverting to `pg_dual` is possible, but MySQL lacks the writes made since Step 10. Run a Postgres-to-MySQL comparison and repair until clean, then do the Step 9 rollback.

- [ ] **Step 11. Remove MySQL code paths and migration machinery.**
  - **Starts when:** Step 10 has been stable for at least 7 days.
  - **Changes:** the repository drops MySQL reads, control-row checks and the copy of creates and updates. The backfill and comparison jobs stop. The sweeper and the erasure copy to MySQL stay until Step 12.
  - **If it fails:** revert the deploy. MySQL data is still present.

- [ ] **Step 12. Retire the MySQL table.**
  - **Starts when:** Step 11 is deployed. That is the real gate, since it is always at least 7 days after Step 10, which already required the 14-day window.
  - **Changes:** an operator removes the erasure copy, renames `users` to `users_retired`, waits 7 more days, then drops it with the outbox and control tables. The data survives only in backups, per retention policy.
  - **If it fails:** the rename is reversible. After the drop, recovery is from backup only.

## Open questions

- Erasures made after the rename in Step 12 do not reach `users_retired`, so for up to 7 days it can hold users erased in that window. Confirm this is acceptable for the erasure deadline, or drop the table sooner.
- The number of sweeper instances and their alert thresholds are not decided. One instance with automatic restart is enough to start.
- It is assumed the erasure job runs on the existing job queue, so a 503 is retried. Confirm this against the job's real code, which is not in the files given.
