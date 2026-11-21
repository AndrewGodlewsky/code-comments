# Users migration plan

## What this is and how it goes

Today every read and write of the `users` table goes through `UserRepository` to MySQL 8. Postgres 16 (`pg-core`) is set up and empty. This plan moves the table to Postgres without downtime. MySQL stays the source of truth while every write is also copied to Postgres. Reads then move to Postgres. The source of truth then moves to Postgres, with one short write pause. MySQL is kept in sync for 14 days so we can roll back, and then it is dropped.

## Terms

- **Source**: the database that holds the truth for writes. MySQL at first.
- **Target**: the other database. It receives copies.
- **`users.write_mode`** (a flag every instance reads):
  - `off`: MySQL only, no copies.
  - `mysql`: MySQL is the source, and copies go to Postgres.
  - `paused`: writes get a retryable 503. Reads still work.
  - `pg`: Postgres is the source, and copies go to MySQL.
  - `pg_only`: Postgres only, no copies.
- **`users.read_from_pg`** (a flag, 0 to 100): the share of users, chosen by id, whose reads go to Postgres.
- **Pending**: a table in the source database with one row per user id still to be copied to the target. It is written in the same transaction as the change.
- **Tombstone**: a table in each database listing erased user ids.
- **Copy**: writes one user row into the target. It takes a lock on that user id, skips a tombstoned id, inserts the row if missing, and replaces it only if the target's `version` is lower than the incoming one. Dual writes, the sweeper, the backfill and the comparer all copy this way.
- **Sweeper**: a worker loop that runs every 10 seconds. It copies each pending id. If the source row is gone, it writes a tombstone to the target and deletes the target row. It deletes a pending row after its copy succeeds. It is a plain worker loop, not `app.jobs`, because `app.jobs` moves a job to `jobs:dead` after 5 failures and nothing retries it.

## Rules that always hold

- A write commits to the source first. A target failure never fails the request.
- Erasure (`UserRepository.delete`) deletes the row, writes a tombstone in the source and writes a pending row, all in one transaction. The tombstone is written even when `write_mode` is `off`.
- If a Postgres read fails or times out, the read goes to the MySQL replica.

## Steps

- [ ] **1. Create the tables.**
  - Starts: a person runs the migration, once.
  - Does: creates `users`, `user_tombstones` and `pending` in Postgres, and `user_tombstones`, `pending` and `backfill_progress` in MySQL.
  - State: schemas only. No data moves.
  - If it fails: nothing has moved. Run it again. The statements use `IF NOT EXISTS`.

- [ ] **2. Deploy the new `UserRepository`, sweeper and comparer.**
  - Starts: a normal deploy, with `users.write_mode = off` and `users.read_from_pg = 0`.
  - Does: writes behave as before, and erasure writes tombstones. The sweeper and comparer start with nothing to do.
  - State: the flags, and the tombstone and pending tables.
  - If it fails: roll back the deploy. Nothing has been copied.

- [ ] **3. Turn on dual writes.**
  - Starts: a person sets `users.write_mode = mysql`.
  - Does: each write commits to MySQL with a pending row. Then one copy to Postgres is tried. If it fails, the sweeper retries it.
  - State: pending rows in MySQL.
  - If it fails: the user's request still succeeds. If Postgres stays down, pending rows grow, so alert on the age of the oldest one. To stop dual writes, set `off`. Existing pending rows are still drained.

- [ ] **4. Run the backfill.**
  - Starts: a person starts the backfill worker, after checking that `app_flag_value{flag="users.write_mode"}` shows `mysql` on every instance.
  - Does: reads the MySQL replica in id order, 2,000 rows per batch. Copies each batch to Postgres in one transaction. Before each batch, if `mysql_replica_lag_seconds` is above 5, it waits 10 seconds and checks again.
  - State: the last completed id in `backfill_progress` in MySQL. It is saved after each batch commits.
  - If it fails: the worker restarts from the saved id. Running a batch twice is harmless because copies are idempotent. If Postgres fails, the batch is retried with backoff, and progress is not saved.

- [ ] **5. Compare until clean.**
  - Starts: the comparer, once the backfill reaches the last id.
  - Does: reads both tables by id in batches and compares id, version and fields. An id that exists in only one table is a difference unless it is pending or tombstoned. A difference counts only if no pending row exists for that id and the rows still differ when re-read from the MySQL primary and from Postgres. Counted differences are added to pending, so the sweeper repairs them.
  - State: none. Each run is a full pass. Its result goes to the job log and a metric.
  - If it fails: run the pass again. The step is done after one full pass with zero counted differences.

- [ ] **6. Move reads to Postgres, and hold at 100% for 3 days.**
  - Starts: a person, once step 5 is clean. Raise `users.read_from_pg` to 1, then 10, 50 and 100. Before each raise, wait for one clean comparer pass. The 3-day hold starts when every instance shows 100 in `app_flag_value`.
  - Does: reads for the chosen share of users come from Postgres. Buckets are stable by id, so a user does not move between databases from one request to the next.
  - State: the flag, and the start date of the hold in the change log.
  - If it fails: lower the flag. Reads go back to MySQL. Nothing is lost. Restart the 3-day hold when you raise it again.

- [ ] **7. Switch the source of truth to Postgres.** Writes are paused for at most 90 seconds.
  - Starts: a person, once reads have been at 100% on Postgres for 3 days and the last comparer pass is clean. Then:
    1. Set `write_mode = paused`. Writes now get a retryable 503.
    2. Wait until every instance shows `paused` in `app_flag_value`. Then wait longer than the longest write request timeout.
    3. Drain the MySQL pending rows into Postgres until none remain.
    4. Set the Postgres `users` id sequence to the larger of MySQL's AUTO_INCREMENT and its max id, plus 1,000. New ids now come from Postgres.
    5. Set `write_mode = pg`. Writes resume once every instance shows `pg`.
  - Does: Postgres becomes the source. Copies flow to MySQL.
  - State: the mode flag, the sequence, and the pending table in MySQL, which is empty after step 3.
  - If it fails: a failed drain is retried, and the pause continues. If the pause is still open at 80 seconds, set `write_mode = mysql` as long as step 5 has not been set. Nothing has been written to Postgres as the source yet, so this is safe.

- [ ] **8. Keep MySQL in sync for 14 days.**
  - Starts: automatic after step 7. It lasts at least 14 days.
  - Does: each write commits to Postgres with a pending row. The sweeper copies it to MySQL under the same copy rule. The comparer keeps running, with Postgres as the source. Erasure writes the tombstone and pending row in Postgres.
  - State: pending rows in Postgres, and tombstones in both databases.
  - If it fails: use the rollback procedure below.

- [ ] **9. Switch writes to Postgres only.**
  - Starts: a person, at least 14 days after step 7, once the Postgres pending table is empty and the last comparer pass is clean.
  - Does: sets `write_mode = pg_only`. Writes go only to Postgres. MySQL receives no more copies. This is not a source change, so no pause is needed.
  - State: the mode flag.
  - If it fails: nothing changes. Once set, a rollback to MySQL can no longer be lossless.

- [ ] **10. Back up and drop the MySQL table.**
  - Starts: a person, after step 9.
  - Does: backs up `users`, `user_tombstones`, `pending` and `backfill_progress` from MySQL. Then drops `users`, and the migration tables in MySQL.
  - State: the backup file. Its location is an open question.
  - If it fails: if the backup fails, do not drop anything.

## Rollback procedure (any time before step 9)

1. Set `users.read_from_pg = 0`, so reads go to MySQL.
2. Run step 7's pause (sub-steps 1 and 2).
3. Drain the Postgres pending rows into MySQL until none remain.
4. Set MySQL's AUTO_INCREMENT above the max Postgres id, so MySQL never reuses an id.
5. Set `write_mode = mysql`.

No write is lost, because MySQL has received every copy. The same abort rule as step 7 applies.

## What happens when things fail

| Failure | What happens | What to do |
|---|---|---|
| Postgres is down during writes | The request succeeds. Pending rows grow. | The sweeper retries. Alert on the oldest pending row. |
| Replica lag is above 5 seconds | The backfill pauses. | It resumes by itself. |
| Backfill worker crashes | Work restarts from the last saved batch. | Restart the worker. |
| An instance shows an old flag | Writes may go to the old source. | Wait until every instance shows the new value. The pause in step 7 does this. |
| A pause passes 80 seconds | Writes stay 503. | Revert as in step 7. |
| A counted difference keeps coming back | The sweeper repairs it. | Investigate the source row. |
| A Postgres read fails | The read goes to the MySQL replica. | None. |

## Open questions

- What is the longest write request timeout? Step 7 waits for it, and the value is not known yet.
- Where are the backups in step 10 kept?
- Does the erasure job retry on a 503 during a pause?
- What age of oldest pending row should trigger an alert?