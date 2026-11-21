# Users migration plan: MySQL to Postgres

## Summary

This plan moves the `users` table from MySQL 8 to the Postgres 16 cluster `pg-core` without taking the service down. Today every read and write of `users` goes through `UserRepository`, so the migration lives there. Reads use the MySQL replica. MySQL assigns each new user's id and the `version` number that optimistic locking uses. The table holds about 38 million rows. The largest id is about 41.2 million, and ids have gaps from deletions. The erasure job hard-deletes about 2,000 rows a day. Peak load is about 3,000 reads and 400 writes a second. The Postgres cluster exists and is empty, and the app already holds a connection pool to it.

The plan adds a Postgres copy inside `UserRepository`. MySQL stays the source of truth until a planned switch. Each write commits to MySQL first, then is copied to Postgres. If the copy fails, the change stays in a `pending` table and a sweeper retries it, so no change is lost. A backfill copies the existing rows from the replica. A comparer checks that the two tables match and repairs what differs. Reads move to Postgres in steps. After 3 days at 100%, Postgres becomes the source of truth. MySQL keeps receiving copies for 14 days, so we can roll back. Only after that is the MySQL table dropped. Every copy can be repeated safely. The source of truth changes only during a short planned pause.

## Rules that must hold

- **Dual writes:** MySQL commits first. A Postgres failure never fails the user's request. Whatever Postgres misses is fixed automatically, with no manual step.
- **Version rule:** every copy (dual write, sweeper, backfill, comparer repair) may only insert a missing row, or replace a row whose `version` is lower than the incoming one.
- **Deletes:** a user removed by the erasure job never reappears in Postgres.
- **Backfill:** starts only after every app instance is dual-writing. It reads the MySQL replica in primary-key order, 2,000 rows per batch. It pauses while replica lag is above 5 seconds. After a crash it continues after the last completed batch.
- **Reads:** reads move to Postgres only after a full comparison finds zero mismatches. The source of truth moves to Postgres only after reads have been 100% on Postgres for at least 3 days.
- **Availability:** reads never fail during the migration. Writes pause for at most 90 seconds each time the source of truth changes. Paused writes get a retryable 503.
- **Rollback:** until we switch to Postgres-only writes, we can go back to MySQL without losing any write. That switch happens no sooner than 14 days after Postgres becomes the source of truth. The MySQL table is dropped only after it.

## Terms

- **Source of truth:** the database whose row wins when the two disagree. Writes commit there first.
- **Primary and replica:** the MySQL primary (`mysql-core-primary`) takes writes. The MySQL replica (`mysql-core-replica`) serves reads. It is a copy that can lag behind the primary. Reporting jobs also read the replica.
- **Replica lag:** how many seconds the replica is behind the primary. The metric `mysql_replica_lag_seconds` shows it.
- **Copy:** writing one user's row into the other database.
- **version:** a number on each user row. It starts at 1 and goes up by 1 on every update.
- **StaleWrite:** the error the repository raises when a row's `version` changed since the caller read it.
- **Version rule:** every copy may only insert a missing row, or replace a row whose `version` is lower than the incoming one. Nothing else.
- **Tombstone:** a row in `user_tombstones` that holds the id of an erased user. Every copy checks it and never writes that id.
- **Pending table (`pending`):** one row per user whose latest change is not yet copied to the other database. It holds the user id and a `change_id`. Each database has its own.
- **change_id:** a new random id written into the pending row with every change.
- **Lock per user id:** a Postgres advisory lock on `pg-core`, taken for one user id. It is a named lock the database hands out, not a row lock. Every copy in either direction, and every row of a backfill batch, holds it, so two copies of one user never interleave. Postgres is the only lock host.
- **`users.write_mode`:** a string flag that says where writes go. Its values are listed under Write modes.
- **`users.read_from_pg`:** a percentage flag that says which users read from Postgres. `flags.enabled_for` buckets users by id, so each user always reads from the same database.
- **Flag refresh:** each app instance reloads flags every 30 seconds, so instances can disagree for up to 30 seconds. Each instance exports its value as `app_flag_value{flag="users.write_mode"}`.
- **Id counter:** the next id a database would issue. For MySQL it is `AUTO_INCREMENT`. For Postgres it is the sequence on `users.id`.
- **Erasure job:** the GDPR job that calls `UserRepository.delete` to hard-delete a user.
- **Retryable 503:** a "service unavailable" reply that tells the client to try again. Our clients already retry it.
- **Job system (`app.jobs`):** a Redis-backed queue with at-least-once delivery. A failed job is retried up to 5 times with exponential backoff, about 15 minutes in total. Then it moves to `jobs:dead`, which nothing processes automatically. If Redis is unreachable, `enqueue` raises after a 1 second timeout.
- **Sweeper:** a new timer on the worker processes that copies `pending` rows. It is not a job, and it does not use Redis.
- **Comparer:** a check that compares the two tables. It is not a job.

## How the system runs

### Write modes

- `mysql_only`: today's behavior. No copies and no pending rows.
- `mysql_primary`: dual write. MySQL is the source. Each write commits to MySQL, then is copied to Postgres.
- `paused`: write requests get a retryable 503. Reads continue. Used only during a switch.
- `postgres_primary`: Postgres is the source. Each write commits to Postgres, then is copied to MySQL. This keeps MySQL in sync for rollback.
- `postgres_only`: Postgres only. No copies to MySQL and no pending rows for MySQL. Once any instance runs this mode, rollback to MySQL is no longer possible. While some instances still run `postgres_primary`, their writes still reach MySQL through the sweeper. Writes on `postgres_only` instances reach MySQL through no copy. That is acceptable, because rollback ends as soon as the first instance shows `postgres_only`.

### A write in `mysql_primary` (dual write)

1. **Commit to MySQL.** A write request runs one MySQL transaction. It makes the change with the usual version check and raises `StaleWrite` if the check fails. It writes the user's `pending` row with a new `change_id`. It then commits. A new user gets its id from MySQL `AUTO_INCREMENT`. Each database write has a 5 second timeout. If this transaction fails, the caller gets the usual error. Nothing is copied and nothing is pending.
2. **Copy to Postgres.** The repository copies the user's current row from the MySQL primary to Postgres, holding the lock for that id. The lock wait and the copy share a 1 second timeout. The copy takes whatever row is committed at that moment, not the version this request wrote. So when two writes to one user land close together, the last copy to run writes the latest row. The version rule stops an older copy from replacing a newer one. The lock also keeps inserts, erasures and tombstone checks from interleaving, which the version rule does not cover. On success, the repository deletes the `pending` row, but only if its `change_id` is still the one it copied.
3. **If the copy fails.** If the copy fails or times out, the caller still gets success. A Postgres failure never fails the request. The `pending` row stays, and the sweeper copies it later.

### A write in `postgres_primary`

The same steps run, with the roles reversed.

- Postgres is the source and MySQL is the copy target. The `pending` row is in Postgres.
- New users get their id from the Postgres sequence. See IDs.
- The version check and `version + 1` run in Postgres, starting from the value copied from MySQL. Copies carry `version`, so counting continues across the switch.
- A rollback copies the Postgres version back to MySQL the same way.

### Writes in `postgres_only`

Each write commits to Postgres only. It writes no `pending` row for MySQL. All copy code stays in `UserRepository`, so the `no-raw-users-sql` lint rule still holds.

### Erasure

1. **Delete in the source.** The erasure job calls `UserRepository.delete`. One transaction in the source database removes the user's row, writes the tombstone and writes the `pending` row. It commits.
2. **Copy the erasure.** The copy finds no source row, so the user was erased. It writes the tombstone at the target and deletes the target row. The tombstone blocks every later copy of that id, so an erased user never reappears.
3. **If that copy fails.** The caller still gets success. Postgres keeps the user until the sweeper's copy lands, so reads in that gap can still return the user.

A repeated `delete` is safe. A missing row is not an error, and the tombstone write is idempotent. During a pause, `delete` returns 503. See Switch procedure.

### The copy

Given a user id, the copy does this:

1. Takes the lock for that id.
2. Reads the row from the source primary.
3. If the row exists, it inserts the row at the target when missing, or replaces the target row when the target's `version` is lower. It does nothing if the target has a tombstone for that id.
4. If the row does not exist at the source, the user was erased. It writes a tombstone at the target and deletes the target row.

A copy removes a row only in the erasure case.

If an insert or replace hits a unique `email` conflict, the copy fails. This can happen when another target row still holds that email, for example a user whose recent email change has not yet been copied. The copy never changes or deletes that other row. The sweeper retries it, and it clears when that row's own copy lands. The pending age alert and the copy failure metric show it if it stays stuck.

### Sweeper

- Runs every 30 seconds on the worker processes. It does not use Redis, so a Redis outage does not stop it.
- There is one sweeper job, and several workers may run it at once. Each pass tries the lock for a user id without waiting. If the lock is busy, the pass skips that id. Another copy is already handling it, so the row is retried on a later pass. Copies are safe to repeat under the version rule.
- Takes `pending` rows, oldest first, and runs the copy for each. It drains the pending table of the current source. After a switch it also drains the old source's pending table, until both tables are empty.
- Deletes a `pending` row only when the copy succeeded and its `change_id` is unchanged. A newer change writes a new `change_id`, so the delete matches nothing and the row stays.
- Retries without end. There is no dead-letter state, so a missed copy is fixed with no manual step.
- Keeps running after the switch until both `pending` tables are empty.

### Comparer

- Walks both tables in primary-key order, 2,000 rows per page. It checks replica lag before each page. Above 5 seconds, it waits and checks again every 5 seconds, the same as the backfill.
- Compares each id on presence, `version`, every column, and tombstone status.
- A difference is a mismatch only if it is still there when both sides are re-read from the source primary 5 minutes later. Writes in flight therefore do not count.
- A confirmed mismatch is repaired with the copy rules. If the target's `version` is higher than the source's, the comparer does not overwrite it. It reports a bug.
- A pass is clean when it finds zero confirmed mismatches. The comparer keeps running after a clean pass as a check. Its source is whichever database is the source at the time.

### Backfill

- Starts only after every app instance is dual-writing (rollout step 4). An instance still on `mysql_only` makes changes that nothing copies to Postgres.
- Reads only the MySQL replica, in primary-key order, 2,000 rows per batch. Reporting jobs also use this replica.
- Before each batch it checks replica lag. Above 5 seconds, it waits and checks again every 5 seconds.
- Each batch is one Postgres transaction. For each row, it takes the lock for that id and applies the copy rules, including the tombstone check. The batch also sets `backfill_progress.last_id` to the batch's last id. Both commit together.
- After a crash, it restarts after `last_id`. A batch that did not commit is read again. That is safe, because of the version rule.
- A replica row can be old. The version rule stops it from replacing a newer row written by a dual write. The tombstone check stops it from re-adding an erased user.

### Switch procedure (planned switch and rollback)

Use this whenever the source of truth changes: the planned switch to Postgres (rollout step 8), and a rollback to MySQL. Writes pause for the duration, which must stay within 90 seconds. Reads continue. An operator runs these steps by hand, in order.

1. Set `users.write_mode` to `paused`.
2. Wait until `app_flag_value` shows every instance on `paused`. This takes up to 30 seconds. Until then, instances on the old mode keep writing to the old source, which is safe. An instance returns 503 for writes only after it sees `paused`.
3. Wait 5 seconds after every instance shows `paused`. Any old-mode write that started before its instance refreshed has then committed or timed out, because writes have a 5 second timeout. Check the old source's pending table with `SELECT COUNT(*) FROM pending`. If the count is not zero, the sweeper is still copying, so check again. Once it reads zero, it stays zero, because no instance writes to the old source any more. One zero reading is therefore final. Steps 2 and 3 together get 45 seconds. If they are not done in 45 seconds, the operator sets the old mode back, and paused instances resume on the old mode.
4. Set the new source's id counter so it passes every id issued so far (see IDs). This applies in both directions.
5. Set `users.write_mode` to the new mode. Each instance resumes writes when it sees the new value, up to 30 seconds later. The operator waits until every instance shows the new value. An instance that does not show it within 30 seconds is restarted, which loads the flags again. A paused instance returns 503 until it sees the new value.

The pause for one instance is at most about 75 seconds. That is at most 30 seconds to see `paused`, at most 45 seconds for steps 2 and 3, and at most 30 seconds to see the new value.

**Rollback** is this procedure with `mysql_primary` as the new mode. After step 5 of a rollback, the operator also sets `users.read_from_pg` to 0. Reads then go to the MySQL replica, which is the source again.

**Erasure during a pause.** During a pause, `delete` returns 503. The erasure job treats that as a failure, and the job system retries it. Its 5 retries over about 15 minutes cover a 90 second pause. The job counts the erasure as done only when `delete` returns success.

### IDs

- Before the switch, MySQL assigns ids with `AUTO_INCREMENT`. The Postgres `users.id` column has no default, and the Postgres sequence is not used. Copies carry MySQL ids explicitly. An explicit id does not move a Postgres sequence, which is why switch step 4 is needed.
- After the switch, Postgres assigns ids from its sequence, and MySQL copies each row under the same id.
- Erased ids must never be reused, because the tombstone would block the copy. Every id ever issued, including ids that now exist only as tombstones, must sit below the new counter.
- **Planned switch to Postgres:** set the sequence to the larger of MySQL's `AUTO_INCREMENT` value and the largest Postgres id plus 1.
- **Rollback:** raise MySQL's `AUTO_INCREMENT` to the larger of its own value and the Postgres sequence's next value. A tombstone-only id does not raise MySQL's counter. Explicit-id copies do raise it, but the reset is still needed for tombstone-only ids.
- A counter that starts too low makes inserts fail with a duplicate-key error. It never overwrites rows.
- On rollback, a Postgres row with a higher version than MySQL's is copied back with its version, so the version rule replaces the lower MySQL row. If a MySQL row ever has a higher version than Postgres, the copy does not overwrite it, and the comparer reports it as a bug.

### Reads

- **Before the switch** (`mysql_only`, `mysql_primary`, `paused`): a read goes to Postgres when the user falls inside `users.read_from_pg`. Other reads go to the MySQL replica, as today. MySQL is still the source, so a Postgres error or a missing row falls back to the MySQL replica, which is correct.
- **After the switch** (`postgres_primary`, `postgres_only`): the read flag is at 100% by then, so reads go to Postgres. A Postgres miss does not fall back. MySQL may still hold a user that Postgres has erased before the erasure is copied, and falling back would return that user. A Postgres error does fall back to the MySQL replica, because reads must not fail. That replica can be stale, or still hold an erased user until its copy lands. This is accepted for now (see open questions).
- A read fails only if both reads fail. That is a MySQL outage, which the migration does not cause.
- A user's change can take a moment to reach the other database. A read in that moment can return the older row.

## Rollout checklist

Each step says what starts it, what it changes, where its state lives, and what happens if it fails.

- [ ] **1. Create the tables.**
  - Starts: the schema deploy, before anything else.
  - Changes: in Postgres, creates `users` (the same columns as MySQL, primary key `id`, unique `email`, and no default on `id`), `user_tombstones`, `pending` and `backfill_progress`. In MySQL, creates `user_tombstones` and `pending`.
  - State: both databases. The tables start empty.
  - If it fails: nothing reads or writes them yet. Fix the problem and rerun. The change is additive.

- [ ] **2. Deploy the new `UserRepository`, sweeper and comparer, with `users.write_mode` set to `mysql_only`.**
  - Starts: the deploy.
  - Changes: no user behavior changes. The sweeper timer starts and finds nothing to do. The deploy adds the metrics the ramp needs: `pending` row count, age of the oldest pending row, Postgres copy failures, Postgres read fallbacks and comparer mismatches. Nothing is copied to Postgres yet, so erasures need no tombstone.
  - State: the flag and the metrics.
  - If it fails: roll back the deploy. No data has changed.

- [ ] **3. Turn on dual writes: set `users.write_mode` to `mysql_primary`.**
  - Starts: an operator changes the flag. Each instance applies it within 30 seconds. The operator waits until `app_flag_value` shows every instance on `mysql_primary`.
  - Changes: writes add `pending` rows and copy to Postgres. Erasures also write tombstones.
  - State: `pending` in MySQL, copies in Postgres.
  - If it fails: Postgres errors leave `pending` rows for the sweeper. If `pending` keeps growing, set `mysql_only`. MySQL stays the source, and the sweeper drains what is left.

- [ ] **4. Run the backfill.**
  - Starts: an operator starts it once every instance has shown `mysql_primary` for at least 30 seconds. An instance still on `mysql_only` makes changes that nothing copies to Postgres, so the backfill waits for all instances.
  - Changes: copies every row from the MySQL replica to Postgres, in batches of 2,000.
  - State: `backfill_progress` in Postgres.
  - If it fails: a crash resumes after the last committed batch. Replica lag above 5 seconds pauses it.

- [ ] **5. Run the comparer until a pass is clean.**
  - Starts: an operator starts it when the backfill reaches the last id. Passes repeat until one is clean, meaning zero confirmed mismatches.
  - Changes: repairs confirmed mismatches by copying.
  - State: the comparer's position and mismatch counts in `backfill_progress`, in its own row.
  - If it fails: a target `version` higher than the source's is not overwritten. The comparer reports it as a bug. Investigate it.

- [ ] **6. Ramp reads: `users.read_from_pg` to 1, then 10, then 50, then 100 percent.**
  - Starts: a clean comparer pass. Each step is held for at least 24 hours (a first choice; the brief sets only the 3 days at 100%).
  - Changes: reads for the users in the bucket move to Postgres. The ramp unit is users, not requests, so each user always reads from the same database.
  - Watch: comparer mismatches, Postgres read fallbacks, copy failures and the age of the oldest `pending` row.
  - State: the flag.
  - If it fails: any mismatch, a `pending` row older than 10 minutes, or a rise in fallbacks sets the flag back to the previous step.

- [ ] **7. Keep reads at 100% on Postgres for 3 days.**
  - Starts: the day reads reach 100%.
  - Changes: none. Same watch as the ramp.
  - State: the flag, and the start date (see open questions).
  - If it fails: go back a read step. The 3-day count restarts once reads are back at 100%.

- [ ] **8. Planned switch: set `users.write_mode` to `postgres_primary`.**
  - Starts: 3 days at 100% reads have passed, and the last comparer pass was clean. The operator runs the switch procedure with `postgres_primary` as the new mode.
  - Changes: sets the Postgres sequence (switch step 4). Writes now commit to Postgres first and are copied to MySQL. Writes get 503 for at most about 75 seconds. Reads stay on Postgres. The MySQL `pending` table is empty at this point and stays empty.
  - State: the flag, the sequence and `pending`.
  - If it fails: if steps 2 or 3 do not finish within 45 seconds, the operator sets the old mode back. If the flag change does not reach an instance, that instance keeps returning 503. Restart it, which loads the flags again.

- [ ] **9. Keep MySQL in sync for 14 days.**
  - Starts: step 8 is done.
  - Changes: nothing else. Every write is copied to MySQL, and the comparer keeps checking.
  - State: the flag and `pending` in Postgres.
  - Rollback until step 10 loses no write, because MySQL is kept complete. To roll back, run the switch procedure with `mysql_primary`. If you switch to Postgres again, the 14 days start again.
  - If it fails: copy errors leave `pending` rows in Postgres. The sweeper retries them. Alert on the age of the oldest row.

- [ ] **10. Switch to `postgres_only`.**
  - Starts: at least 14 days after step 8, the last time Postgres became the source, and the Postgres `pending` table is empty.
  - Changes: writes stop copying to MySQL. No pause is needed, because Postgres stays the source. Instances can switch in any order. Instances still on `postgres_primary` are safe, since every write still commits to Postgres. While instances run both modes, writes on `postgres_only` instances reach MySQL through no copy. That is acceptable, because rollback to MySQL ends as soon as the first instance shows `postgres_only`.
  - State: the flag.
  - If it fails: set `postgres_primary` again. This is safe, because Postgres is still the source. After this step, rollback is no longer possible.

- [ ] **11. Back up the MySQL `users` table, then drop it.**
  - Starts: step 10 is done, and every instance shows `postgres_only`.
  - Changes: takes a backup, then drops the MySQL `users` table. It then drops the MySQL `pending` and `user_tombstones` tables, which only served the copies.
  - State: the backup.
  - If it fails: a failed backup stops the drop. If the drop was wrong, restore from the backup.

## What happens when things fail

| What fails | What the caller sees | What happens next |
|---|---|---|
| Postgres write fails or times out during a dual write | Success | The `pending` row stays. The sweeper copies it. |
| Postgres copy hits a unique `email` conflict | Success | The `pending` row stays. The sweeper retries until the conflicting row gets its own copy. The pending age alert fires if it stays stuck. |
| Copy cannot get the id lock within 1 second | Success | The `pending` row stays. The sweeper retries it and skips the id while the lock is busy. |
| Erasure's Postgres copy fails | Success | Postgres keeps the user until the sweeper's copy writes the tombstone and deletes the row. Reads in that gap can still return the user. |
| Source write fails (MySQL in `mysql_primary`, Postgres in `postgres_primary`) | Error, as today | Nothing is copied, and nothing is pending. |
| Sweeper stops | Nothing | `pending` grows. Alert at 10 minutes. The ramp and the switch wait. |
| Comparer finds a mismatch | Nothing | Repaired by copying. The ramp waits for a clean pass. |
| Repair finds a target `version` higher than the source's | Nothing | Not overwritten. Reported as a bug. |
| Postgres read fails | Success | Falls back to the MySQL replica. After the switch, that replica may be stale or still hold an erased user until its copy lands. |
| Postgres read finds no row, before the switch | Success | Falls back to the MySQL replica, which is still the source. |
| Postgres read finds no row, after the switch | Not found | No fallback, because MySQL may still hold an erased user. |
| Both reads fail | Error, as today | A MySQL outage, not caused by the migration. |
| Backfill crashes | Nothing | Restarts after `last_id`. |
| Replica lag is above 5 seconds | Nothing | The backfill and the comparer wait. |
| User is erased during the backfill | Nothing | The tombstone blocks the copy. |
| Writes paused during a switch | 503, retryable | Clients retry. Reads continue. |
| Switch aborts at steps 2 or 3 | Nothing new | The operator sets the old mode back. No write is lost. |
| An instance has not refreshed the flag | 503 until it sees the new mode | No mixing of modes, so no divergence. The operator sees it on `app_flag_value` and restarts that instance. Setting the flag again does not help an instance that cannot read it. |
| Erasure job's `delete` gets a 503 | Job retry | Its 5 retries over about 15 minutes cover a 90 second pause. If it is dead-lettered, see open questions. |
| Id counter starts too low | Inserts fail with duplicate key | No row is overwritten. |

## Open questions

- How long will the backfill take? 38 million rows at 2,000 per batch is about 19,000 batches, plus any lag pauses. Measure on the first batches.
- The flag system gives no hard fence. The switch relies on every instance showing the new value within 30 seconds, and on the 5 second write timeout. Nothing alerts when an instance stays on the old mode or on `paused`. Only the operator watching `app_flag_value` during the switch sees it. Is that enough?
- Who records the dates for the 3-day and 14-day rules? The app does not check them.
- A dead-lettered erasure job sits in `jobs:dead`, which nothing reads. Who checks it?
- A Postgres read can return an older row for a few seconds while a copy is pending. Is that acceptable?
- After the switch, a Postgres error falls back to a replica that may still hold an erased user until its copy lands. Is that acceptable, or should such reads fail instead?
- Where is the MySQL backup kept, and for how long?
- Each `pending` row adds one more write per user write. Is the extra load on the primary acceptable?
- These numbers are first choices to tune: the 1 second copy timeout, the 5 second write timeout, the 5 minute re-check, the 10 minute pending alert, the 24 hour minimum per ramp step, and the 45 second limit for steps 2 and 3 of a switch.