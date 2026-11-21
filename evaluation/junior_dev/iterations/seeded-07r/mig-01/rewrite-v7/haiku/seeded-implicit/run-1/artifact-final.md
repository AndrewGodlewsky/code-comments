# Users migration plan

This moves the `users` table from MySQL 8 to Postgres 16 without downtime. MySQL stays the source of truth while every write is also copied to Postgres (a "dual write"). Repair, backfill and comparison keep the two copies equal. Reads move to Postgres only after a full comparison finds no differences. The source of truth then switches once. MySQL stays in sync for 14 days so we can roll back, and only then is the MySQL table dropped.

## How the system works today

Every read and write of `users` goes through `UserRepository`, the only code allowed to run SQL on `users`. Reads use the MySQL replica. Writes use optimistic locking: each update checks `version` and adds 1 to it. Each app instance refreshes its flags every 30 seconds. Background jobs in `app.jobs` retry for about 15 minutes, then move to a dead-letter list that nothing reprocesses.

## Terms

- **Source of truth (SoT):** the database that holds the authoritative copy of a user. Writes commit there first, and it wins when the two copies disagree.
- **Write mode:** the flag `users.write_mode`. Its values are listed below.
- **Version:** the `version` column. Every update adds 1.
- **Copy:** writing one row into the other database, using the copy rule below.
- **Pending table:** one row per user id that still needs to be copied to, or deleted from, the other database. It lives in the source of truth, so it survives an outage of the other database.
- **Tombstone:** a record that a user id was erased. It blocks any later copy of that id.
- **Named lock:** a lock on one user id (a Postgres advisory lock, or MySQL `GET_LOCK`). A copy or delete holds it, so two of them for the same id cannot interleave.
- **Sweeper:** the worker that drains the pending table.
- **Comparer:** the worker that scans both tables and counts mismatches.
- **Scheduled worker:** a process that wakes every minute and does one bounded run of the sweeper, backfill or comparer. It is not `app.jobs`, because job retries stop after about 15 minutes and dead jobs are never reprocessed.
- **Replica lag:** the metric `mysql_replica_lag_seconds`.

## Write modes

- `mysql_only`: today's behaviour. No copies.
- `dual`: MySQL is the source of truth. Each write also copies to Postgres.
- `frozen`: every write returns a retryable 503. Reads continue.
- `pg_primary`: Postgres is the source of truth. Each write also copies to MySQL.
- `pg_only`: Postgres only. MySQL is no longer written, and rollback ends.

## How the running system behaves

**Writes in `dual` and `pg_primary`.** The write commits to the source of truth. In the same transaction it adds the user id to that database's pending table. The request then tries to copy the row to the other database. If the copy fails, the request still succeeds, and the pending row waits for the sweeper. A failure in the other database never fails a user's request.

**Copy rule (used by writes, backfill, sweeper and comparer repair).** Under the id's named lock, in one transaction:
- If a tombstone exists for the id, do nothing.
- If no row exists, insert it.
- If a row exists with a lower `version`, replace it.
- Otherwise, do nothing.

**Optimistic lock check.** Updates check `version` against the source of truth.

**Sweeper.** Runs every minute while any pending row exists, in any write mode. It takes up to 500 pending rows, oldest first. For each user it reads the current row from the source of truth and copies it with the copy rule. For an erased user it writes the tombstone and deletes the row in the other database. It removes a pending row only after its copy succeeds. A failing row stays pending and is retried each minute.

**Erasure.** The GDPR erasure job runs on the source of truth, in one transaction. It inserts a tombstone, deletes the user row and adds a pending row. The sweeper then applies the tombstone and the delete to the other database. Copies and deletes hold the same named lock and check tombstones, so an erased user cannot reappear. The comparer also finds and removes any row whose id has a tombstone.

**Reads.** Read Postgres for a user when `users.read_from_pg` is on for that user. The flag is bucketed by user id with `flags.enabled_for`. If the Postgres read fails or finds no row, read the MySQL replica instead. A Postgres error never fails a read. When the flag is off, read the MySQL replica as today.

**Ids after the switch.** Until the switch, MySQL's `AUTO_INCREMENT` assigns ids. Copies into MySQL keep the explicit id, and InnoDB moves its counter past any larger explicit id, so MySQL's counter stays ahead. At the switch, the Postgres sequence is set to the highest id in either database plus 1. After that, writes in `pg_primary` take ids from the Postgres sequence.

## Steps

Do these in order. Each step says what starts it, what it changes, where its state lives, and what happens if it fails.

- [ ] **1. Create the tables.**
  - Starts: a one-time migration, run by hand.
  - Does: creates `users` in Postgres, with the same columns as MySQL. Creates `tombstones`, `pending` and `backfill_progress` in both databases.
  - State: the two databases.
  - If it fails: nothing uses the new tables yet. Run it again.

- [ ] **2. Deploy the new UserRepository, sweeper and comparer.**
  - Starts: a normal deploy.
  - Does: ships code that knows all five write modes. `users.write_mode` stays `mysql_only`, so behaviour does not change.
  - State: the code, and the flag at `mysql_only`.
  - If it fails: roll the deploy back. No data was touched.

- [ ] **3. Turn on dual writes.**
  - Starts: setting `users.write_mode` to `dual`.
  - Does: every write now also copies to Postgres. Wait until `app_flag_value{flag="users.write_mode"}` shows `dual` on every instance. Instances can disagree for up to 30 seconds.
  - State: the flag, and pending rows in MySQL.
  - If it fails: set `users.write_mode` back to `mysql_only`. Pending rows stay, and the sweeper drains them.

- [ ] **4. Backfill Postgres from the MySQL replica.**
  - Starts: the scheduled worker. It refuses to start until every instance reports `dual` in the metric above.
  - Does: reads the MySQL replica in primary-key order, 2,000 rows per batch, and copies each batch to Postgres with the copy rule. Before each batch it reads replica lag. If lag is above 5 seconds, it stops and tries again next minute, because reporting jobs share the replica. Each run stops after about 50 seconds, so runs stay short.
  - State: the last completed id, in `backfill_progress` in MySQL. It is saved only after its batch has been copied.
  - If it fails: after a crash, the run resumes after the last saved id. The batch that was in flight is copied again, which is harmless because of the version rule. If Postgres is unreachable, the run stops and retries next minute.

- [ ] **5. Run the comparer until it is clean.**
  - Starts: the scheduled worker, once backfill has reached the highest id.
  - Does: scans both tables in primary-key order, 2,000 rows per batch, with the same lag pause. It counts a mismatch when a row is missing in Postgres, when its version or fields differ, or when a tombstoned id exists in Postgres. Before counting a mismatch, it rereads the row from the source of truth, so rows changed during the scan do not count. Mismatches are passed to the sweeper.
  - State: its scan position and the result of each pass, in `backfill_progress`.
  - If it fails: a pass with any mismatch is not clean. Keep running passes until one full pass finds zero mismatches.

- [ ] **6. Move reads to Postgres in steps.**
  - Starts: a clean comparer pass. Set `users.read_from_pg` to 1, then 10, then 50, then 100. Check for errors before each step.
  - Does: sets the share of users read from Postgres.
  - State: the flag.
  - If it fails: set the flag to a lower value, or to 0. Reads go back to the MySQL replica.

- [ ] **7. Hold reads at 100% on Postgres for 3 days.**
  - Starts: the flag reaches 100%. Save that date in `backfill_progress`.
  - Does: waits. Nothing else changes.
  - If it fails: a read error during the hold sends the flag back down. The 3-day count starts again when it returns to 100%.

- [ ] **8. Switch the source of truth to Postgres.** This is the planned write pause. Its worst case is 85 seconds (30 + 10 + 15 + 30), within the 90-second limit.
  - Starts: 3 days at 100% reads, then a person sets the flag below.
  - Does, in order:
    1. Set `users.write_mode` to `frozen`. Writes now get a retryable 503. Wait until every instance shows `frozen` in the metric (up to 30 seconds).
    2. Wait 10 seconds. Write requests time out at 10 seconds, so any write that started before the freeze has finished.
    3. Run the sweeper until MySQL's pending table is empty. If it is not empty 15 seconds later, set `dual` again and retry later.
    4. Set the Postgres id sequence to the highest id in either database, plus 1.
    5. Set `users.write_mode` to `pg_primary`. Instances switch within 30 seconds.
  - State: the flag. After this step, the pending table is in Postgres.
  - If it fails: before step 5, set `dual`. Ownership has not changed. After step 5, an instance that still shows `frozen` returns 503 until it reads the new value. No instance writes to the old source of truth, so no write is split between the two databases.

- [ ] **9. Keep MySQL in sync for 14 days.**
  - Starts: step 8 has finished.
  - Does: each write commits to Postgres and copies to MySQL. The comparer keeps running, so rollback stays possible.
  - Rollback, if needed: set `frozen`, wait as in step 8, drain the Postgres pending rows into MySQL, then set `dual`. The same 90-second limit applies.
  - State: the pending table in Postgres.
  - If it fails: a failed copy to MySQL leaves a pending row in Postgres, and the sweeper retries it.
  - Never start step 10 less than 14 days after step 8.

- [ ] **10. Switch to Postgres-only writes.**
  - Starts: at least 14 days after step 8, the comparer is clean, and the pending table is empty.
  - Does: sets `users.write_mode` to `pg_only`. MySQL is no longer written, and rollback ends. This does not change the source of truth, so it needs no write pause.
  - State: the flag.
  - If it fails: set `pg_primary` again. This is possible only until step 11.

- [ ] **11. Back up and drop the MySQL `users` table.**
  - Starts: step 10 has finished.
  - Does: takes a backup of the MySQL table, then drops it.
  - State: the backup.
  - If it fails: if the backup fails, do not drop the table.

## When something fails

| Situation | What happens |
|---|---|
| Postgres is down during a write (`dual` or `pg_primary`) | The request succeeds. The row stays pending, and the sweeper retries each minute. |
| MySQL is down during a write in `pg_primary` | Same, with MySQL as the target. |
| A sweeper copy keeps failing | The row stays pending. It is retried each minute with no limit. |
| Replica lag is above 5 seconds | Backfill and comparer pause and resume the next minute. |
| Backfill crashes | It resumes after the last saved id. |
| Erasure runs during backfill | The tombstone blocks the copy. The comparer removes any leftover row. |
| Instances disagree on the write mode | This lasts up to 30 seconds. The new source of truth starts only after every instance shows `frozen`. |
| Pending rows do not drain in 15 seconds during the switch | Set `dual`, then retry later. |
| A Postgres read errors or finds no row | The read falls back to the MySQL replica. |
| The comparer finds mismatches | The sweeper repairs them. Reads keep working. |

## Open questions

- Which scheduler runs the scheduled worker? The existing docs do not define one.
- The 3-day rule needs a measure of which database each read used. No such metric exists yet.
- A read that falls back to the replica, or a Postgres row that has not caught up yet, can return an older version for a short time. It is not decided whether that is acceptable.
- Do Postgres advisory locks and MySQL `GET_LOCK` work with our connection pools? Unknown.
- The flag check in step 3 assumes `app_flag_value` has one series per instance. This is not confirmed.
- Who gets alerted when the pending table grows? Not decided.
- Email conflicts between the two databases are not handled.