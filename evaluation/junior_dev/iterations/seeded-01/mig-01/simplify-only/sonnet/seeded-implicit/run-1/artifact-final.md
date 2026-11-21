# Users migration plan

## What this is

We move the `users` table from MySQL 8 to Postgres 16 with no downtime. For a while both databases hold the data. Writes go to the source of truth first, then to the other database. A background job copies old rows over. Reads move to Postgres next, and the source of truth moves last.

Today, all reads and writes of `users` go through `UserRepository`. It reads from the MySQL replica and writes to the MySQL primary. All migration logic goes into this class. No other code touches `users`.

## Terms

- **Source of truth**: the database whose write counts. A write commits there first.
- **Copy**: the write to the other database. A copy may only insert a missing row or replace a row with a lower `version`. Dual writes, backfill and repair all use this one rule.
- **`users.write_mode`**: flag that sets the phase. Values: `mysql_only`, `dual_mysql_primary`, `paused`, `dual_pg_primary`, `pg_only`.
- **`users.read_from_pg`**: percentage flag. Each user id always gets the same answer.
- **Pending row**: a note saying "this user's copy may be missing". It is written in the same transaction as the write, in the source-of-truth database.
- **Tombstone**: a note saying "this user was erased". It is written in the same transaction as the delete, in the source-of-truth database.
- **Sweeper**: a repository job, run every minute on each app instance, that fixes pending rows.
- **Comparer**: a job that compares the two tables row by row and lists mismatches.
- **Flag lag**: instances refresh flags every 30 seconds, so a change reaches all of them only after about 30 seconds. `app_flag_value{flag=...}` shows when it has.

## How it works while both databases are live

1. **Write.** The repository commits to the source of truth, together with a pending row (or a tombstone for a delete). It then makes the copy and removes the pending row. If the copy fails, the user's request still succeeds and the pending row stays.
2. **Repair.** The sweeper takes each pending row, reads the current row from the source of truth, makes the copy, and removes the pending row. If the copy fails again, the row stays and is tried next minute. Repair needs no manual step and does not use the job queue.
3. **Erase.** The erasure job deletes the row, writes a tombstone and deletes the copy. Every copy checks for a tombstone first and does nothing if there is one. The comparer also deletes any copy that has a tombstone.
4. **Read.** `read_from_pg` decides which database answers. If Postgres fails or lacks the row, the repository reads MySQL. Reads never fail because of Postgres.

## Rollout steps

Each step lists what starts it, what it does, where its state lives and what happens if it fails.

- [ ] **1. Create tables.**
  - Starts: a migration run by hand.
  - Does: creates `users` in Postgres. Creates `tombstones` and `pending` in both databases, plus `backfill_progress` (one row: last completed id) in MySQL.
  - State: the tables themselves.
  - If it fails: re-run it. Nothing uses the tables yet.
- [ ] **2. Deploy the code.**
  - Starts: a normal deploy.
  - Does: ships the updated `UserRepository`, sweeper, comparer and backfill job, with `write_mode` still `mysql_only`, so behaviour does not change.
  - State: none.
  - If it fails: roll back the deploy.
- [ ] **3. Turn on dual writes.**
  - Starts: set `write_mode` to `dual_mysql_primary`.
  - Does: every write now also goes to Postgres.
  - State: the flag, plus pending rows and tombstones in MySQL.
  - If it fails: set the flag back to `mysql_only`. Postgres failures only create pending rows.
- [ ] **4. Backfill.**
  - Starts: `app_flag_value` shows `dual_mysql_primary` on every instance.
  - Does: reads the MySQL replica in id order, at most 2,000 rows per batch, and makes the copy of each row. It waits while `mysql_replica_lag_seconds` is above 5.
  - State: `backfill_progress` is updated after each finished batch.
  - If it fails: restart it. It continues after the last finished batch, and re-copying a batch is safe.
- [ ] **5. Compare.**
  - Starts: backfill is finished and the pending table is empty.
  - Does: the comparer checks every row in both tables. Rows with a pending row are skipped. Each mismatch gets a pending row so the sweeper repairs it.
  - State: the mismatch count.
  - If it fails: wait for the sweeper and run it again. Go on only when a full run finds zero mismatches.
- [ ] **6. Move reads.**
  - Starts: the comparer is clean.
  - Does: raise `read_from_pg` to 1%, 10%, 50%, then 100%. Hold 100% for at least 3 days.
  - State: the flag.
  - If it fails: lower `read_from_pg`. If errors or mismatches appear, go back to step 5.
- [ ] **7. Switch the source of truth.**
  - Starts: reads have been at 100% for 3 days.
  - Does, within 90 seconds:
    1. Set `write_mode` to `paused`. Writes now get a retryable 503. Wait until every instance shows `paused`, which takes up to about 30 seconds.
    2. Wait until the pending table is empty.
    3. Set the Postgres id sequence to the next MySQL `AUTO_INCREMENT` value.
    4. Set `write_mode` to `dual_pg_primary`. Writes now commit to Postgres first, then MySQL, and pending rows and tombstones are kept in Postgres.
  - State: the flag, the Postgres sequence.
  - If it fails or passes 90 seconds: set `write_mode` back to `mysql_primary`'s mode, `dual_mysql_primary`. Nothing has been lost, because MySQL was never left.
- [ ] **8. Keep MySQL in sync for 14 days.**
  - Starts: step 7 done.
  - Does: the sweeper keeps MySQL up to date. Rollback is possible. To roll back, do step 7 in reverse: pause writes, empty pending, set the MySQL `AUTO_INCREMENT` to the next Postgres id, set `dual_mysql_primary`. This also may pause writes for at most 90 seconds.
  - State: the flag, pending rows in Postgres.
  - If it fails: a failing MySQL copy only makes pending rows. Writes are not affected.
- [ ] **9. Postgres only.**
  - Starts: at least 14 days after step 7, and no rollback wanted.
  - Does: set `write_mode` to `pg_only`. Then back up the MySQL table and drop it.
  - State: the flag, the backup.
  - If it fails: do not drop the table until the backup is checked. After the drop there is no rollback.

## When things fail

| What fails | What happens |
| --- | --- |
| A copy fails during a write | The request succeeds. The pending row stays and the sweeper repairs it. |
| The sweeper cannot reach the other database | Pending rows build up and are retried every minute. |
| A crash during backfill | Restart. It continues after the last finished batch. |
| Replica lag above 5 seconds | Backfill waits. |
| Postgres read fails | The read goes to MySQL. |
| The switch takes more than 90 seconds | Go back to the old source of truth. |

## Open questions

- Tombstones and pending rows sit in the source-of-truth database. This was chosen so a crash cannot lose them. Between a tombstone check and the insert, there is a short race, and the comparer is what closes it.
- How long to keep tombstones is not decided.
- The backup method for step 9 is not decided.
