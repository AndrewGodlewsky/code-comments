# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Design decisions

All changes go in `UserRepository`. The pieces below are used by later steps.

- **Source and follower.** One store is the source of truth and the other is the follower. Every write commits to the source, then is copied to the follower. At first MySQL is the source. After the switch Postgres is the source and the copy runs in reverse. This reverse copy is what makes rollback lossless.
- **Repair uses a durable outbox, not Redis jobs.**
  - `jobs.enqueue` raises when Redis is down. Failed jobs go to `jobs:dead` after about 15 minutes, and nothing processes that list. That cannot guarantee that a missed row is eventually fixed.
  - Instead, each write transaction inserts a row `(seq, user_id, kind)` into `users_sync_outbox` in the same database and transaction as the user row. The write and its repair record commit or fail together.
  - After commit, the repository tries to copy the row inline, with a 200 ms timeout and a circuit breaker. On success it deletes the outbox row. On any failure it logs, increments a metric and returns success to the caller.
  - A `sync-relay` worker keeps draining the outbox, retrying forever. It claims rows with `FOR UPDATE SKIP LOCKED`, re-reads the current row from the source primary (never a replica), copies it, then deletes the outbox row. If the row is gone from the source, it copies a delete instead.
- **Version rule and erasure, enforced in one place.**
  - The copy function is the only way data enters the follower. For Postgres it runs in a transaction that starts with `pg_advisory_xact_lock(id)`. If `user_tombstones` has the id, it does nothing. Otherwise it runs `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
  - The MySQL equivalent is `INSERT ... ON DUPLICATE KEY UPDATE`, with each column set conditionally on `version < VALUES(version)`.
  - A delete copy, under the same lock, inserts the tombstone and deletes the row. Backfill, dual writes, repair and the reconciler all use this function. A stale replica read can therefore never resurrect an erased user.
  - Ids are never reused. Tombstones hold only the id and are kept indefinitely (about 2,000 rows per day).
- **Write fence, so a stale flag cache cannot lose a write.**
  - Flags can disagree between instances for up to 30 seconds, so flags only say where to write. Each database holds a one-row `users_fence` table. Every write transaction starts by reading its own database's fence with `FOR SHARE`. If the fence is not open for writes, the request gets a retryable 503.
  - The switch script takes an exclusive lock on the fence row. That waits for in-flight writes and blocks new ones, so the pause is exact and does not depend on 30-second flag timing.
- **Flags (`app.flags`).**
  - `users.dual_write` (bool, default false).
  - `users.source` (`mysql` | `pg`, default `mysql`).
  - `users.read_pg_pct` (percentage, default 0), bucketed with `flags.enabled_for("users.read_pg_pct", user_id)`.
- **Read fallback.** Reads sent to Postgres fall back to the other store on a Postgres error or a miss, and a metric counts each fallback. Reads therefore never fail because of the migration.
- **Postgres column types.** `updated_at` is `timestamp(3)` without time zone, to match MySQL `DATETIME(3)` exactly. The email index is non-unique at first (see step 8).
- **"Every app instance" means web instances and worker processes.** The erasure job runs in workers and calls `UserRepository.delete`, so workers must run the new code and flags too.

### State locations

| State | Lives in |
|---|---|
| Forward repair queue | `users_sync_outbox` in MySQL (written in the same transaction as the user row) |
| Reverse repair queue (after the switch) | `users_sync_outbox` in Postgres |
| Write routing and fence | `users_fence` in each database; the `users.source` flag is only a hint |
| Backfill progress | `migration_state(name, last_id, done)` in Postgres, updated in the same transaction as each batch |
| Erasure guard | `user_tombstones(id)` in Postgres |
| Id generator | MySQL `AUTO_INCREMENT` until the switch, then a Postgres sequence |

## Checklist

- [ ] **1. Create the schemas.**
  - **Starts:** a reviewed migration, run by hand against both databases.
  - **Changes:**
    - Postgres: `users` (`id BIGINT PRIMARY KEY` with no default yet, `email`, `name`, `plan`, `version INT`, `updated_at timestamp(3)`, plus a non-unique email index), `user_tombstones`, `migration_state`, `users_fence` (closed), `users_sync_outbox`, and the sequence `users_id_seq`.
    - MySQL: `users_sync_outbox` and `users_fence` (mode `mysql`).
  - **State:** the tables are empty.
  - **If it fails:** nothing reads these tables yet. Fix the migration, drop what was created and rerun.

- [ ] **2. Deploy the new code with every flag at its default.**
  - **Starts:** a normal deploy.
  - **Changes:** `UserRepository` gains the fence check, outbox writes, the copy function, read fallback and the flag handling. It also ships the `sync-relay`, `backfill` and `reconciler` workers (the reconciler is used in step 8). With `dual_write=false`, `source=mysql` and `read_pg_pct=0`, behavior is unchanged apart from the extra fence read per write.
  - **Gate:** the deploy has finished, no old-build web or worker process is running, and the number of `app_flag_value{flag="users.dual_write"}` series equals the orchestrator's instance count (web plus worker).
  - **If it fails:** roll back the deploy. The schemas from step 1 are harmless.

- [ ] **3. Rehearse the copy path in staging.**
  - **Starts:** step 2 is done.
  - **Changes:** nothing in production. Tests cover version ordering, tombstone-before-insert and insert-before-tombstone, Postgres down mid-write (the request must succeed and the relay must repair the row), and the pause and rollback scripts with a timing check.
  - **If it fails:** fix the code and redeploy. Do not continue.

- [ ] **4. Turn on dual writes.**
  - **Starts:** step 3 passes. A human sets `users.dual_write=true`.
  - **Changes:** from now on every write adds an outbox row in its MySQL transaction, commits to MySQL, then tries Postgres inline. Nothing is backfilled yet.
  - **State:** the MySQL outbox. Alert if oldest-row age exceeds 60 s.
  - **If it fails:**
    - If Postgres is unavailable, requests are unaffected and the outbox grows. The relay catches up when Postgres returns.
    - If dual writes cause user-visible latency, the circuit breaker already skips the inline copy.
    - Do not set the flag back to false once step 6 has started. Missed writes after that point would be unrecorded.

- [ ] **5. Wait until every instance is dual-writing.**
  - **Starts:** step 4.
  - **Condition, all of:**
    - Every web and worker instance reports `app_flag_value{flag="users.dual_write"}=1`, and the series count equals the instance count, for at least 2 consecutive scrapes.
    - At least 60 seconds have passed since the last instance changed. This covers the 30-second refresh and in-flight requests.
    - Outbox age is under 60 s.
    - A test erasure shows the tombstone and the Postgres delete.
  - **Why:** rows written before this point by an instance that was not dual-writing are not in the outbox. Backfill picks them up because it starts only after this gate.
  - **If it fails:** a series is missing or stuck at 0, so investigate that instance. Do not start the backfill.

- [ ] **6. Run the backfill.**
  - **Starts:** step 5's condition is met. A human runs the `backfill` command, which refuses to start if the condition is not met.
  - **Changes:**
    - It reads `WHERE id > last_id ORDER BY id LIMIT 2000` from `mysql-core-replica`.
    - Before each batch it checks `mysql_replica_lag_seconds`. If the value is above 5, it sleeps and rechecks until it is 5 or below.
    - It then copies the batch with the copy function, which applies the version rule and tombstone check. It sets `migration_state.last_id` to the batch's last id in the same Postgres transaction.
    - It stops when a read returns no rows, and sets `done`. At roughly one batch per second this takes about 5 hours.
  - **State:** `migration_state` in Postgres. After a crash or restart it continues from `last_id`, so a batch is either fully applied with its progress recorded or not applied at all.
  - **If it fails:**
    - Replica or Postgres errors are retried with backoff.
    - A crash resumes from `last_id`.
    - Running two copies is safe, because the copy function is idempotent and `last_id` only moves forward.
    - Stale replica rows are rejected by the version rule or the tombstone.

- [ ] **7. Let the relay and reconciler run continuously.**
  - **Starts:** step 6 is done.
  - **Changes:** the reconciler scans both tables in id order in chunks, with MySQL read from the replica. A difference counts as a mismatch only if it persists after re-reading both primaries and has no pending outbox row. Each confirmed mismatch gets an outbox row, which the relay then fixes automatically. The relay also fixes failures left by dual writes, so this repair needs no manual step.
  - **State:** a `mismatch_count` metric per pass.
  - **If it fails:** the reconciler is idempotent and restartable. A crashed pass is simply rerun.

- [ ] **8. Run the full comparison and make email unique.**
  - **Starts:** step 6 is `done`.
  - **Changes:**
    - One full pass compares all columns of every row in both tables, including rows only on one side. Repeat until a complete pass that started after `done` ends with zero confirmed mismatches.
    - Then run `CREATE UNIQUE INDEX CONCURRENTLY` on `users(email)` in Postgres. The index was left non-unique so that out-of-order copies, such as a user changing an email that another user then takes, could not block a copy mid-migration.
  - **Gate for step 9:** a zero-mismatch pass, plus the unique index built.
  - **If it fails:**
    - A mismatch is repaired by the relay, then the pass is rerun.
    - A mismatch that persists across passes is a bug, so stop and investigate.
    - If the index build fails because of duplicate emails, the duplicates are mismatches. Repair them and retry.
    - After the index exists, a copy blocked by an email conflict stays in the outbox and is retried until the earlier change lands.

- [ ] **9. Ramp reads to Postgres.**
  - **Starts:** step 8's gate is met. A human sets `users.read_pg_pct` to 1, 10, 50, then 100. Each stage holds at least 1 hour with fallback rate and error rate flat, and the next stage starts only if the reconciler still shows zero.
  - **Changes:** reads for the selected users come from Postgres. Nothing changes on writes.
  - **State:** the flag, with `app_flag_value` showing each instance's value.
  - **If it fails:**
    - Lower the percentage. Reads fall back to MySQL immediately.
    - Any confirmed mismatch holds the ramp until repaired.
    - Reads right after a write can lag the source by the time to copy to Postgres, usually milliseconds. If an inline copy failed, the lag lasts until the relay runs, normally seconds. An `update` that reads a stale version fails the version check on MySQL and raises `StaleWrite`, which is safe and retried by the caller.

- [ ] **10. Soak for at least 3 days at 100% reads.**
  - **Starts:** every instance reports `users.read_pg_pct=100`. The 3-day clock starts when the last instance does, and restarts if the percentage is ever lowered.
  - **Changes:** nothing. The reconciler keeps running and the outbox is monitored.
  - **Gate for step 11:** at least 3 days elapsed, a zero-mismatch pass in the last 24 hours, and the outbox empty or under 60 s.
  - **If it fails:** a regression sends you back to step 9 at a lower percentage and restarts the clock.

- [ ] **11. Switch the source of truth to Postgres (writes paused, at most 90 s).**
  - **Starts:** the step 10 gate is met and a human launches `switch-to-pg`. This is the first pause.
  - **The script does this, in order:**
    1. Set the MySQL fence to `closed`. The update waits for in-flight writes to finish. From now on every write gets a retryable 503. Reads continue. The clock starts.
    2. Wait for the MySQL outbox to reach zero rows (the relay is told to run immediately). At that point Postgres contains every committed MySQL write.
    3. Set `users_id_seq` with `setval` to `max(MAX(id) in MySQL, AUTO_INCREMENT − 1) + 1000`. The gap leaves room for ids already issued but unused. Then give `id` the default `nextval('users_id_seq')`.
    4. Open the Postgres fence, then set the flag `users.source=pg`. Writes now commit to Postgres first and are copied to MySQL through the Postgres outbox, with `users.dual_write` still true.
  - **Timing:**
    - Steps 1–3 take a few seconds.
    - Instances still holding `source=mysql` get 503 from the closed MySQL fence until they refresh the flag, at most 30 s later. Each instance's pause is therefore under about 45 s.
    - The script aborts at 60 s if step 2 has not finished. The 90 s budget is never reached.
  - **State:** both fences, the flag, and the Postgres outbox.
  - **If it fails:**
    - Before step 4 nothing has moved. The abort reopens the MySQL fence and leaves `source=mysql`.
    - After step 4, do not abort. Either finish, or run the rollback in step 12.
    - A failed outbox drain is retried until the deadline, then aborts as above.
    - A stale flag cannot cause a lost write, because the closed MySQL fence rejects it.

- [ ] **12. Rollback procedure (available from step 11 until step 14).**
  - **Starts:** a human decides, or an alert fires on error rate, mismatches or outbox lag.
  - **The script does this, in order:**
    1. Set the Postgres fence to closed. This is the second pause, again at most 90 s.
    2. Drain the Postgres outbox to zero, so MySQL has every write made while Postgres was the source.
    3. Raise MySQL `AUTO_INCREMENT` if it is below max id + 1 across both stores.
    4. Set the MySQL fence to `mysql`, set `users.source=mysql`, and set `users.read_pg_pct=0`.
  - Forward dual writes resume automatically.
  - **State:** the fences, flags and both outboxes.
  - **If it fails:** the script aborts at 60 s and reopens the Postgres fence, so nothing is lost. Instances with a stale flag get 503 until they refresh. The version rule makes every copy safe to repeat.

- [ ] **13. Soak for at least 14 days with Postgres as the source.**
  - **Starts:** step 11 completes. The clock starts when the flag change reaches the last instance.
  - **Changes:** nothing. Reverse copies keep MySQL current. The reconciler keeps running in both directions, with the source always overriding the follower under the version rule.
  - **State:** the Postgres outbox, with oldest-row age under 60 s alerted.
  - **If it fails:** run step 12. Rolling back restarts this soak from the next switch.

- [ ] **14. Switch to Postgres-only writes.**
  - **Starts:** at least 14 days after step 11 and no rollback in that period. The Postgres outbox is empty, and a full comparison in the last 24 hours showed zero mismatches. A human sets `users.dual_write=false`.
  - **Changes:** writes stop being copied to MySQL. This needs no pause, because the source does not change. Instances that have not refreshed yet still write outbox rows, and the relay applies them, so nothing is lost during the 30-second window.
  - **Gate:** every instance reports `dual_write=0`, and the Postgres outbox is empty.
  - **If it fails:**
    - Set the flag back to true and run a full reconciliation pass to bring MySQL back to date. That restores the ability to roll back.
    - Once MySQL has fallen behind, plain rollback is no longer available. Use this path only soon after the change.

- [ ] **15. Retire MySQL `users`.**
  - **Starts:** step 14's gate is met, and no `users` queries have reached MySQL for at least 7 days.
  - **Changes:**
    1. Rename `users` to `users_retired`. Any missed reader fails loudly.
    2. After another 7 days with no errors, take a last dump only if policy allows, because erased users would still be in it. Then drop `users_retired`, `users_sync_outbox` and `users_fence`.
    3. Remove the dual-write, fence, outbox and backfill code and the three flags in a cleanup deploy. Keep `user_tombstones`.
  - **If it fails:** before the drop, rename the table back. After the drop there is no way back, so make sure steps 13 and 14 were clean first.

## Failure summary

| Failure | Effect on users | Repair |
|---|---|---|
| Postgres write fails or times out | None | Outbox row remains and the relay retries forever |
| Redis down | None, since repair does not use Redis | None needed |
| Backfill crash or restart | None | Resumes from `last_id` in Postgres |
| Replica lag above 5 s | None | Backfill pauses |
| Stale replica row during backfill | None | Rejected by the version rule or tombstone |
| Erased user's row copied late | None | Rejected by the tombstone; the Postgres delete applies |
| Instance with stale flag at a switch | Retryable 503 for at most about 30 s | Fence blocks the write; instance refreshes its flag |
| Switch or rollback exceeds 60 s | Retryable 503 | Script aborts and reopens the previous fence |
