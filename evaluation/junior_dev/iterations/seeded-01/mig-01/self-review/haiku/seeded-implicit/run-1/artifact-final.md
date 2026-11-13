# Users migration plan

Goal: move the `users` table from MySQL 8 (database `core`) to Postgres 16 (`pg-core`) without taking the service down. Every read and write of `users` goes through one class, `UserRepository`, so the migration logic lives there, plus a few background jobs.

## Terms

- **Instance**: one running copy of the app. Several run at once. Each one reads flags and writes users.
- **Flags**: runtime settings read through `app.flags`. Each instance refreshes them every 30 seconds, so after a change, instances can disagree for up to 30 seconds. The metric `app_flag_value` shows each instance's current value.
- **Write state**: one Redis key, `users:write_state`, holding `write_mode` and `write_pause`. Every write request and every job reads it before acting, so a change takes effect within about a second. The operator changes the key and also sets the flag of the same name, so the metric can confirm the change. If Redis cannot be read, a write gets a retryable 503. The key exists because flags can take up to 30 seconds to reach every instance, which would make the 90-second write pause unsafe.
- **`write_mode`** values:
  - `mysql_only`: today. MySQL only.
  - `dual_mysql_primary`: MySQL is the source of truth, and each write is copied to Postgres.
  - `dual_pg_primary`: Postgres is the source of truth, and each write is copied to MySQL.
  - `pg_only`: Postgres only, no copies.
- **`write_pause`**: on or off. When on, write requests get a retryable 503, which clients already retry. Reads are never paused.
- **`read_from_pg`**: a percentage. Users in that share read from Postgres. The share is chosen by user id, so each user always lands on the same side.
- **Jobs**: background tasks run by workers, separate from the instances. Delivery is at least once, so a job can run twice and must be safe to repeat. A job that keeps failing is moved to a dead-letter list that nobody watches. No step depends on that list. If the backfill is dead-lettered, an operator restarts it by hand.
- **Primary and replica**: the MySQL primary takes writes. The replica is a read-only copy. Reporting jobs also read it, so its lag (`mysql_replica_lag_seconds`) is shared.
- **Source of truth**: the database that decides what a user row is when the two disagree. It starts as MySQL. It moves to Postgres once, at the switch (step 7), and moves back only on a rollback (step 8).
- **Copy**: writing a user row into the other database.
- **Dual write**: a write commits to the source of truth first, then the change is copied to the other database. A failed copy never fails the user's request.
- **Version rule**: every copy (dual write, backfill or repair) may only insert a row that is missing, or replace a row whose `version` is lower than the incoming one. An equal or lower version never overwrites a row. Every user update increases `version` by 1.
- **Pending table**: each database has a `pending` table. The source-of-truth database holds one row per user id that is still owed to the other database: the id and the latest version to copy. The row is written in the same transaction as the change, so it survives a crash. It is deleted only when the copy of that exact version is confirmed. If a newer change has arrived, the row stays.
- **Tombstone**: a record that a user id was erased. Tombstones exist in both databases. Every Postgres insert or update checks the tombstone table in the same transaction and skips the row if the id is tombstoned. This means an erased user never comes back, even if a slow copy arrives late.
- **Repair sweeper**: a job that works through pending rows. For each one, it reads the current row from the source-of-truth primary, copies it under the version rule, and deletes the pending row only if the version is still the one it copied. In steady state it runs every minute. During a switch or rollback it runs continuously until pending is empty.
- **Comparer**: a job that reads both tables by id range and reports differences.

## Steps

- [ ] **1. Create the tables.**
  - Starts: a migration script, run by hand after review. No flag is involved.
  - Changes: Postgres gets `users` (the same columns as MySQL, with `id` as a plain BIGINT primary key; copies supply the id, and the sequence default is added in step 7), `tombstones`, `pending` and `backfill_progress`. MySQL gets `pending` and `tombstones`. The script uses CREATE IF NOT EXISTS, so running it again is safe.
  - State: the new tables. Nothing reads or writes them yet.
  - If it fails: nothing user-visible has changed. Fix the cause and run the script again.

- [ ] **2. Deploy the new UserRepository, the repair sweeper and the comparer.**
  - Starts: a normal deploy of the instances and workers.
  - Changes: no behavior change yet. `write_mode` is `mysql_only` and `read_from_pg` is 0%. The new code writes no pending rows and sends nothing to Postgres. The comparer stays off until step 5.
  - State: none new.
  - If it fails: roll back the deploy. No data has changed.

- [ ] **3. Turn on dual writes.**
  - Starts: the operator sets `write_mode` to `dual_mysql_primary` in the write state key and the flag. Check that `app_flag_value` shows it on every instance before step 4.
  - Changes:
    - A user write runs in one MySQL transaction. It changes the row, bumps `version`, and upserts the user's pending row with the new version. After the commit, the request copies the row to Postgres under the version rule, with a short timeout.
    - If the copy succeeds, the request deletes the pending row, but only if its version still matches the one copied. If the copy fails, the pending row stays and the request still succeeds.
    - An erasure delete runs in one MySQL transaction. It deletes the user, inserts a tombstone, and upserts a pending row marked as a delete. The sweeper then sends the delete to Postgres in one Postgres transaction: delete the user row and insert the tombstone.
    - The sweeper runs every minute and repairs pending rows in batches.
  - State: MySQL `pending` and `tombstones`; Postgres `users` and `tombstones`.
  - If it fails: if Postgres is down, pending rows build up and are repaired when it returns. To stop dual writes, set `write_mode` back to `mysql_only`. Existing pending rows still drain.

- [ ] **4. Backfill from the replica.**
  - Starts: the operator starts the backfill job, only after step 3 shows `dual_mysql_primary` on every instance. The job checks the metric itself and refuses to start otherwise.
  - Changes: the job repeats these steps for about 19,000 batches (38 million rows at 2,000 rows per batch):
    1. Check replica lag. If it is above 5 seconds, wait and check again.
    2. Read up to 2,000 rows from the replica where `id` is greater than the last saved id, in `id` order.
    3. In one Postgres transaction, copy the rows under the version rule, skipping tombstoned ids, and save the batch's last id in `backfill_progress`. Both happen or neither does.
    4. Stop when a read returns no rows.
  - State: Postgres `backfill_progress`, one row holding the last completed id.
  - If it fails: after a crash, the job resumes after the saved id. Because the copy and the saved id commit together, a half-finished batch cannot exist. If Postgres is down, the job retries with backoff. Users are not affected. Replica rows may be slightly behind MySQL; the version rule stops them from overwriting newer rows, and the comparer fixes what is left.

- [ ] **5. Run the comparer until it is clean.**
  - Starts: the backfill reaches the end of the table. The comparer then runs continuously over id ranges, reading the replica under the same lag rule and reading Postgres.
  - Changes:
    - It reports three kinds of mismatch: a row missing from Postgres, a row whose version or fields differ, and a row in Postgres that is not in MySQL.
    - It skips ids that have a pending row in either database, because those are not settled yet.
    - Each mismatch is rechecked after a short delay against the MySQL primary, because rows change during a check. Only mismatches still present on the recheck count as persistent.
    - Persistent mismatches are repaired. Missing and stale rows are copied under the version rule. Extra rows are deleted from Postgres.
  - A clean pass is one complete pass over all id ranges with zero persistent mismatches.
  - State: the result of each pass.
  - If it fails: a pass that does not finish is started again. Data changes only for confirmed mismatches.

- [ ] **6. Move reads to Postgres.**
  - Starts: step 5 is clean. The operator sets `read_from_pg` to 1, then 10, 50 and 100. Before each increase, wait for a clean pass that finishes after the previous change.
  - Changes: reads for users in the share go to Postgres. If a Postgres read fails, the request reads from the MySQL replica instead, so reads never fail.
  - Hold at 100% for at least 3 days. A persistent mismatch, or `read_from_pg` dropping below 100%, restarts the 3-day count.
  - State: none new.
  - If it fails: set `read_from_pg` to 0. Reads go back to MySQL at once.

- [ ] **7. Switch the source of truth to Postgres.**
  - Starts: someone decides, once all of these hold: step 6 has been at 100% for 3 days, the latest comparer pass is clean, and the MySQL `pending` table is empty.
  - Changes, in order. The write pause must last at most 90 seconds in total. The sub-steps are lettered so they are not confused with the main steps.
    - a. Set `write_pause` on in the write state key. Writes get a 503 within about a second. Wait for in-flight writes to finish. Wait longer than the longest request timeout. Do not wait for the metric here, because the key is already in effect.
    - b. Drain. The sweeper runs continuously until the MySQL `pending` table is empty. With writes paused, no new pending rows appear.
    - c. Set the Postgres id sequence to MySQL's `AUTO_INCREMENT` counter plus a margin of 1,000,000. The counter is past every id MySQL has ever issued, so new ids cannot collide with existing ones.
    - d. Set `write_mode` to `dual_pg_primary` in the key.
    - e. Set `write_pause` off in the key. Then check that the metric shows the new values on every instance.
  - Stop rule: if the pause has lasted 75 seconds and step d has not happened, set `write_pause` off and stop. Nothing has moved yet, so this undoes the attempt. After step d, do not stop. Finish step e, then use the rollback in step 8 if needed.
  - After the switch: each write commits to Postgres, which assigns the id from its sequence, and writes a pending row in Postgres. The sweeper copies the row to MySQL under the version rule, using the id Postgres assigned. Deletes and tombstones travel the same way. Reads stay on Postgres.
  - State: the write state key, and the Postgres sequence.

- [ ] **8. Keep MySQL in sync for 14 days, so rollback stays possible.**
  - Starts: automatically after step 7. Step 9 cannot start until 14 days after step 7.
  - Changes: the sweeper and comparer now run from Postgres to MySQL, and the comparer treats Postgres as the reference. Reads stay on Postgres. If a Postgres read fails, the fallback reads the MySQL replica. That row can be a little out of date while its change is still pending, but the read does not fail.
  - Rollback, which is the reverse of step 7. It has the same 90-second limit and the same stop rule:
    - a. Set `read_from_pg` to 0, so reads go to MySQL.
    - b. Set `write_pause` on in the key. Wait for in-flight writes. Then drain: the sweeper runs until the Postgres `pending` table is empty. Every write is now in MySQL.
    - c. Set MySQL's `AUTO_INCREMENT` above the highest id Postgres has issued, so MySQL never reuses one.
    - d. Set `write_mode` to `dual_mysql_primary` in the key.
    - e. Set `write_pause` off in the key.
  - Stop rule for rollback: before step d, set `write_pause` off and stay on Postgres. After step d, finish step e.
  - After a rollback, the plan restarts at step 6, with its 3-day hold, before another switch.
  - State: Postgres `users`, `tombstones` and `pending`, and the MySQL copy.
  - If it fails: the source of truth moves only after `pending` is empty, so no write is lost. If a step fails, set `write_pause` off and stay on the current source.

- [ ] **9. Switch to `pg_only`, back up MySQL, and drop the table.**
  - Starts: at least 14 days after step 7, with the latest comparer pass clean and no rollback in progress.
  - Changes:
    1. Set `write_mode` to `pg_only`. No write pause is needed, because the source of truth does not change.
    2. Wait until every instance shows `pg_only`. Then wait until the Postgres `pending` table is empty. That is the last copy to MySQL, so no new pending rows can appear after this point.
    3. Take a backup of the MySQL `users` table and verify that it can be restored.
    4. Only then drop the MySQL `users` table. Remove the MySQL copy code in a later deploy.
  - State: the backup, kept under the backup policy.
  - If it fails: a failed backup stops the drop, and the MySQL table stays. Once the table is dropped, it can only be restored from the backup.