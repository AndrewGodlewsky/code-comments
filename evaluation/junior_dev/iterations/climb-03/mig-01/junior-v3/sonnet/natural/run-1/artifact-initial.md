# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Design decisions

These decisions apply to every step below.

- **Write modes.** One string flag, `users_write_mode`, holds the mode. It can be `mysql`, `dual_mysql`, `paused`, `dual_pg` or `pg_only`. Using one flag means no combination of two flags can be inconsistent.
  - `dual_mysql` means MySQL is the source of truth and every write is copied to Postgres.
  - `dual_pg` means Postgres is the source of truth and every write is copied back to MySQL.
  - Instances can disagree on a flag for up to 30 seconds.
  - Every instance exports its current value as `app_flag_value{flag="users_write_mode"}`, and that is how we confirm a change has arrived everywhere.
- **Read flag.** `users_read_pg_pct` is a percentage flag. The repository calls `flags.enabled_for("users_read_pg_pct", user_id)`, so a given user always gets the same answer.
- **Sync outbox, so repair is automatic.**
  - Every write inserts a row into a table that lives next to `users` in the source-of-truth database: `users_sync_outbox(seq PK auto, user_id, attempts, next_try_at, created_at)`. The row is inserted in the same transaction as the write. A crash after commit therefore cannot lose the need to copy.
  - After commit, the request path tries one inline sync of that user with a 250 ms timeout. Success deletes the outbox rows for that user with `seq <=` the one it saw. Any failure is swallowed and logged, so the request never fails.
  - A circuit breaker skips the inline attempt while Postgres is unhealthy, so Postgres trouble adds no latency to writes.
  - A repair worker (a standalone process, not `jobs`) polls the outbox with `FOR UPDATE SKIP LOCKED`. It retries forever with capped backoff of up to 60 seconds, and there is no dead-letter list. I avoid `jobs` on purpose: `enqueue` can fail when Redis is down, and `jobs:dead` is never processed.
  - The outbox is the only repair mechanism. The backfill and the comparison also feed it.
- **Sync copies state, not events.** To sync a user the worker reads the current row from the source of truth by id and applies it to the target. It does not replay the change. If the row is gone, it applies a delete instead. Syncs are therefore idempotent and can run in any order.
  - The copy carries every column verbatim, including `version` and `updated_at`. It never calls `NOW()`.
  - A unique-email collision (user A frees an email that user B takes) fails the later sync. That sync retries and succeeds once A's sync lands.
- **Version rule and deletes, enforced in one statement.** The Postgres `users` table gets a nullable `deleted_at` column. Rows with `deleted_at` set are tombstones: `email`, `name` and `plan` are NULL, and they hold only `id` and `deleted_at`.
  - Postgres upsert: `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.deleted_at IS NULL AND users.version < EXCLUDED.version`. This inserts a missing row or replaces a lower version, and it can never overwrite a tombstone.
  - It is a single statement atomic on the primary-key index, so there is no race between a stale copy and a delete.
  - Postgres delete: upsert a tombstone unconditionally. A delete for an id that was never copied still leaves a tombstone, so a later backfill cannot create the row.
  - Tombstones are kept permanently. At about 2,000 per day they are small.
  - A view, `users_live`, filters `deleted_at IS NULL`. All Postgres reads and comparisons use it.
- **Reverse direction.** MySQL gets a table `users_erased(id PK)`, written by `delete()` in the same transaction as the hard delete.
  - A copy into MySQL does `SELECT 1 FROM users_erased WHERE id=%s FOR SHARE` and then `INSERT ... ON DUPLICATE KEY UPDATE`, applying the same version rule. A concurrent erasure blocks on the lock, so a stale reverse copy cannot bring an erased user back.
- **Read path.**
  - If the user is in the read percentage, read from Postgres with a short timeout.
  - On a Postgres error or timeout, fall back to the MySQL replica, so reads never fail.
  - On a Postgres miss, also fall back to the replica, but only in `dual_mysql` or `mysql` mode. This covers a row not yet synced. Once Postgres is the source of truth, a miss is final.
- **New ids.** Until the switch, MySQL assigns ids and Postgres receives them as explicit values.
  - A sequence `users_id_seq` exists in Postgres from step 1. It is used only in `dual_pg` and `pg_only` modes, where Postgres assigns ids and copies them to MySQL as explicit ids.
  - MySQL's AUTO_INCREMENT counter moves past any larger explicit id on its own, so a rollback keeps assigning unique ids.
  - At each switch to Postgres, inside the pause, the sequence is set with `setval('users_id_seq', MAX(id) from the MySQL primary + 1,000,000)`.
- **Where state lives.**

  | State | Location |
  |---|---|
  | Modes and percentages | flags |
  | Forward outbox | MySQL primary |
  | Reverse outbox | Postgres |
  | Backfill checkpoint | Postgres table `migration_state` |
  | Erasures | `users_erased` in MySQL, tombstone rows in Postgres |

## Checklist

- [ ] **1. Create the new schema (additive DDL, nothing uses it yet).**
  - Starts: a manual DDL migration, run once.
  - Postgres: `users` with the same columns as MySQL plus `deleted_at` and a unique index on `email`. Also `users_live`, `users_id_seq`, `users_sync_outbox` (for the reverse direction) and `migration_state(name PK, last_id, done, updated_at)`.
  - MySQL: `users_sync_outbox` and `users_erased`.
  - State: schema only.
  - If it fails: drop the new objects. No running code references them.

- [ ] **2. Deploy the new code with everything switched off.**
  - Starts: a normal rolling deploy.
  - Ships a new `UserRepository` implementing all modes, the outbox repair worker, the backfill job, the comparison job and the new `users_read_pg_pct` read path.
  - Defaults: `users_write_mode=mysql` and `users_read_pg_pct=0`, so behaviour is unchanged.
  - Only `delete()` changes immediately: it also writes `users_erased`.
  - The deploy does not complete until old-version instances are gone.
  - If it fails: roll the deploy back. All changes are additive.

- [ ] **3. Rehearse a pause.**
  - Starts: a flag change to `users_write_mode=paused`, then straight back to `mysql`.
  - Measures how long writes really are unavailable. Fix the scrape interval or the abort timings in step 9 if the result is over 60 seconds.
  - Writes get a retryable 503 during the drill. Reads are untouched.
  - If it fails: set the flag back to `mysql`. Instances resume within 30 seconds.

- [ ] **4. Turn on dual writes.**
  - Starts: the flag `users_write_mode=dual_mysql`.
  - From now on each write commits to MySQL together with its outbox row, then syncs to Postgres inline. The worker repairs misses.
  - Healthy when `app_flag_value` shows `dual_mysql` on every instance, the oldest outbox row is under 1 minute old, and the Postgres error rate is low.
  - If it fails: set the flag back to `mysql`. The worker keeps draining the outbox, and any gap left is closed by steps 5 and 6.

- [ ] **5. Backfill.**
  - Starts: a condition. All three must hold:
    - `app_flag_value{flag="users_write_mode"}` is `dual_mysql` on every running instance. The number of series equals the orchestrator's instance count, and no old-code instance remains.
    - The outbox is healthy.
    - `mysql_replica_lag_seconds` is 5 or less.
  - It reads from the MySQL replica in primary-key order: `WHERE id > last_id ORDER BY id LIMIT 2000`. It copies each batch with the guarded upsert.
  - It checks `mysql_replica_lag_seconds` before every batch. While the value is above 5 it sleeps and rechecks. It also throttles itself to protect Postgres.
  - Each batch is one Postgres transaction that upserts the rows and sets `migration_state.last_id` to the batch's highest id. The checkpoint therefore moves only with committed data.
  - A single runner is enforced by a lease row in `migration_state`.
  - A crash or error rolls back the open batch. The job restarts from `last_id`, and repeating a batch is harmless. An empty batch with the lag condition met sets `done`.
  - Stale replica rows are safe because of the version rule. Rows erased in the meantime are safe because of the tombstones.
  - If it fails: nothing to undo. Alert if the checkpoint does not move for 15 minutes.

- [ ] **6. Full comparison.**
  - Starts: the backfill reaches `done`.
  - It scans every id in both tables, MySQL from the replica under the same lag rule, and compares all columns including `version`. It also checks for Postgres rows with no MySQL counterpart.
  - Any difference is rechecked against the MySQL primary and Postgres once the outbox has nothing pending for that id. Only a difference that persists counts as a mismatch. Each one is also pushed into the outbox so it is repaired.
  - Success is one complete pass with zero persistent mismatches. Repeat the pass until that happens.
  - State: results are kept in `migration_state`.
  - If it fails: it only reports and repairs. Investigate the cause of a repeated mismatch before going on.

- [ ] **7. Move reads to Postgres.**
  - Starts: the condition "step 6 has a zero-mismatch pass".
  - Ramp `users_read_pg_pct` to 1, 10, 50 and then 100, watching the error and fallback rates at each stage.
  - Keep running the comparison daily. Hold at 100% for at least 3 days with zero persistent mismatches. Any mismatch fixes the cause and restarts the 3-day clock.
  - If it fails: set the percentage to 0 or a lower value. Takes effect within 30 seconds, and reads keep working throughout.

- [ ] **8. Switch preflight.**
  - Starts: the condition "reads have been 100% on Postgres for 3 days or more".
  - Check that the latest comparison pass is clean, the outbox is under 5 seconds old, and Postgres is healthy.
  - Confirm the flag scrape interval is 10 seconds or less.
  - If it fails: do not start. Fix it and recheck.

- [ ] **9. Switch the source of truth to Postgres (writes paused for 90 seconds at most).**
  - Starts: the flag `users_write_mode=paused` (call that moment T0).
  - Steps, in order:
    1. **T0.** Each instance returns a retryable 503 for writes once it sees the flag. Reads continue on Postgres. In-flight writes finish, bounded by the request timeout.
    2. **By T0+45.** Wait until every instance shows `paused` and its in-flight write gauge is 0. The gauge is `users_writes_inflight`, which this migration adds.
    3. **By T0+55.** Drain the MySQL outbox to 0, then `setval('users_id_seq', MAX(id) + 1,000,000)`.
    4. **By T0+55.** Set `users_write_mode=dual_pg`. Each instance resumes within 30 seconds of seeing it, so no instance is paused for more than about 85 seconds.
  - After the switch, writes commit to Postgres with an outbox row in Postgres, then copy to MySQL. That is the mirror image of step 4. Because MySQL is kept current, rollback needs no data reconstruction.
  - State: the mode flag. The reverse outbox is in Postgres.
  - If it fails: if step 2 or 3 misses its deadline, set the flag back to `dual_mysql`. Instances resume within 30 seconds, so the pause still stays under 90. No data has moved yet, so nothing is lost.
  - After the flip, a failure means use step 11.

- [ ] **10. Soak period of at least 14 days with reverse dual writes.**
  - Starts: the flag `dual_pg` has reached every instance.
  - Run the comparison daily. The reverse outbox must stay near empty.
  - Rollback stays available throughout.
  - If it fails: see step 11.

- [ ] **11. Rollback (only if needed).**
  - Starts: a decision by a person, for example sustained errors on Postgres.
  - Repeat the step 9 pause pattern in the other direction:
    1. Set `paused`.
    2. Wait for every instance and for in-flight writes to finish.
    3. Drain the Postgres outbox to 0.
    4. Check that the MySQL AUTO_INCREMENT counter is above the largest id.
    5. Set `users_write_mode=dual_mysql`.
  - Reads can stay on Postgres, since Postgres is still kept in sync.
  - Same 90-second budget and the same abort rule.
  - Any write that happened in Postgres is already in MySQL or in the outbox, so none is lost.
  - If it fails: abort back to `dual_pg`.

- [ ] **12. Stop writing to MySQL.**
  - Starts: both conditions hold. At least 14 days have passed since step 9, and the last comparison and the Postgres outbox are clean.
  - Set `users_write_mode=pg_only`. This is not a change of source of truth, so no pause is needed. The flag ends the copies to MySQL and the writing of the reverse outbox.
  - Rollback is no longer possible after this point.
  - If it fails: set the flag back to `dual_pg`. The reverse outbox catches MySQL up from Postgres, so nothing is lost until step 13.

- [ ] **13. Retire MySQL.**
  - Starts: a manual decision after `pg_only` has run cleanly for an agreed period.
  - Rename the MySQL `users` table, take a final snapshot, and drop it only after a further agreed quiet period.
  - Remove the MySQL code paths and flags from `UserRepository`, and remove the outbox and `users_erased` tables.
  - Keep the Postgres tombstones.
  - If it fails: the renamed table can be renamed back until the drop.
