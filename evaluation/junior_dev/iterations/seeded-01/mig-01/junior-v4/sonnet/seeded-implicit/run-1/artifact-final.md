# Users migration plan

We are moving the `users` table from MySQL 8 to Postgres 16 with no downtime. Today every read and write goes through `UserRepository`, which writes to the MySQL primary and reads from the MySQL replica. We add dual writes, copy the old rows over, check that the two tables match, move reads, then move writes. MySQL is the source of truth until step 7.

## Terms

- **Source of truth**: the database that commits a write first. The other database gets a copy afterwards. It is MySQL in `mysql_only` and `dual`, and Postgres in `pg_primary` and `pg_only`. `frozen` has none, because writes are refused.
- **`users.write_mode`**: a string flag in `app.flags`. Its values:
  - `mysql_only`: today's behavior.
  - `dual`: MySQL is the truth, and writes are copied to Postgres.
  - `frozen`: writes get a retryable 503, and reads continue.
  - `pg_primary`: Postgres is the truth, and writes are copied to MySQL.
  - `pg_only`: Postgres only. MySQL goes stale.
- **Flag delay**: instances cache flags for up to 30 seconds, so for that long they can disagree. The metric `app_flag_value` shows when all instances have a change. Every important change of `write_mode` goes through `frozen` first, and nobody moves on until all instances show `frozen`. So no two instances ever write to different databases.
- **`users.read_from_pg`**: a percentage flag. It sends that share of reads, bucketed by user id, to Postgres. If a Postgres read fails, the read falls back to MySQL, so reads never fail. Under `pg_only` there is no fallback.
- **`version`**: a column on each user row. `UserRepository` sets it to 1 on create and adds 1 on every update. Nothing else sets it.
- **Version rule**: every copy into a database inserts a missing row, or replaces a row whose `version` is lower than the incoming one. Otherwise it does nothing. All copies (dual write, backfill, repair) use this one function, so they can run in any order and be repeated safely.
- **`pending`**: a table with one row per user id whose copy to the other database may not have happened. Each row holds `user_id` and a `mark` number. Marking an id again raises its `mark` by 1. There is one `pending` table in MySQL and one in Postgres. A write puts its row in the source-of-truth database's table, in the same transaction as the user write. Every clear of a `pending` row, by a request or by the sweeper, deletes it only if the `mark` is still the one that was written or read. So a newer mark survives.
- **`tombstones`** (Postgres only): ids erased by the GDPR erasure job. The job calls `UserRepository.delete`, the only erasure path. The copy function refuses any id listed here, so an erased user cannot come back.
- **Sweeper**: a loop in every app instance. It runs in every mode except `mysql_only`. Every 10 seconds it takes `pending` rows (id and `mark`) and reads the current row in that table's database. It copies the row to the other database with the version rule. If the row is gone, it deletes the user from the other database and adds a tombstone. Then it clears the `pending` row with the mark check. It reads the `pending` table of the source of truth: MySQL's in `dual`, Postgres's in `pg_primary` and `pg_only`. In `frozen` it drains both. It does not use the Redis job queue. Several sweepers may handle the same id at once, which is harmless because every action can be repeated.
- **Backfill progress** (one row in Postgres): the last user id that was copied.
- **Comparer**: a job that compares both tables.

## How a write works

The same pattern applies in `dual` and `pg_primary`. In `pg_primary` the two databases swap roles.

1. In one transaction on the source of truth, make the change and add a `pending` row.
2. After the commit, the request copies the row to the other database with the version rule, with a short timeout. It then clears the `pending` row with the mark check, and returns.
3. If the copy fails or times out, the user still gets success. The sweeper finishes the copy within about 10 seconds, with no manual step.
4. If the source of truth fails, the request fails and nothing is copied.
5. An erasure works the same way. It deletes the row in the source of truth, with a `pending` row. In Postgres it also adds the tombstone in the same transaction. The request then deletes the row in the other database, and in `dual` adds the tombstone there.

Under `mysql_only` a write goes to MySQL only, with no `pending` row.

## Rollout steps

Each step lists what starts it, what it does, where its state lives, and what happens if it fails.

- [ ] **1. Create tables.**
  - Starts: a deploy of the schema change.
  - Does: in Postgres, create `users` (same columns, plus an id sequence that stays unused until step 7), `tombstones`, `pending` and the backfill progress row. In MySQL, create `pending`.
  - State: the tables themselves.
  - If it fails: fix and rerun. Nothing uses them yet.
- [ ] **2. Deploy the code.**
  - Starts: a normal deploy, with `write_mode` still `mysql_only`.
  - Does: ships the new `UserRepository` paths, the sweeper and the comparer. Behavior is unchanged.
  - State: none.
  - If it fails: roll the deploy back.
- [ ] **3. Turn on dual writes.**
  - Starts: an operator sets `write_mode=dual`.
  - Does: writes follow "How a write works", with MySQL as the source of truth. During the 30-second flag delay, an instance still on `mysql_only` writes to MySQL without a `pending` row. That is why step 4 waits until every instance shows `dual`. The backfill then copies whatever those writes left behind.
  - State: `pending` in MySQL.
  - If it fails: a Postgres failure never fails the request, and the sweeper repairs it. To stop, set `mysql_only`.
- [ ] **4. Backfill.**
  - Starts: an operator launches one backfill process, once `app_flag_value` shows `dual` on every instance.
  - Does: repeat this loop.
    1. Wait while `mysql_replica_lag_seconds` is above 5.
    2. Read up to 2,000 rows from the replica, in id order, with id above the saved progress.
    3. Drop any id that has a row in the MySQL `pending` table (read from the primary), because the sweeper is handling it.
    4. Copy the rest with the version rule in one Postgres transaction, and save the new last id in that same transaction.
    5. Stop when a read returns nothing.
  - Erased users: the replica may still show a user who was just erased. The tombstone blocks that copy once the erasure has reached Postgres. If it has not, its `pending` row makes the backfill skip the id, and the sweeper writes the tombstone.
  - State: the progress row in Postgres.
  - If it fails: restart it. It continues after the last completed batch. Repeating a batch is safe, and so are stale replica rows, because newer versions win.
- [ ] **5. Compare.**
  - Starts: an operator launches the comparer after the backfill ends.
  - Does: it walks the ids of both tables in id order, in fixed-size batches, and compares all columns. Rows being written right now can differ for a moment, so it re-reads each difference from both primaries before counting it. A full pass with zero differences is "clean". It keeps running through steps 6 to 8.
  - State: none.
  - If it finds differences: it adds those ids to the source of truth's `pending` table, so the sweeper repairs them. Then run another full pass until one is clean.
- [ ] **6. Move reads.**
  - Starts: the comparer's first clean pass.
  - Does: set `read_from_pg` to 1, 10, 50, then 100. At each value, wait for all instances and watch for about an hour. Go on if the Postgres read-fallback rate and the `pending` backlog stay near zero. After 100%, hold for 3 days (a fixed requirement) with the comparer still clean. The flag stays at 100 for the rest of the migration.
  - State: the flag.
  - If it fails: set `read_from_pg` back to the previous value, or to 0. MySQL is still the truth, so nothing is lost.
- [ ] **7. Switch the source of truth.**
  - Starts: an operator, after the 3 days. The whole write pause must stay under 90 seconds.
  - Does:
    1. Set `write_mode=frozen` and wait until every instance shows it (up to 30 seconds). Writes now get a retryable 503. Running requests finish, and sweepers drain the MySQL `pending` table.
    2. Wait until the MySQL `pending` table is empty, so Postgres has every MySQL write.
    3. Read MySQL's next AUTO_INCREMENT value from the primary. It is final now, because no write can allocate an id while frozen. Set the Postgres id sequence to the larger of that value and the highest tombstone id plus 1. Without this, new ids would collide with existing ids or reuse erased ones.
    4. Set `write_mode=pg_primary` and wait for all instances. Nothing is left in flight from before, because step 1 refused new writes and step 2 emptied the MySQL table.
  - After that, writes follow "How a write works" with Postgres as the source of truth. Reads come from Postgres and fall back to MySQL if a Postgres read fails.
  - State: from now on the Postgres `pending` table is in use. The MySQL one is empty and unused until a rollback.
  - If it fails: if any step passes 75 seconds, set `write_mode=dual`. MySQL is still the truth. Retry later.
- [ ] **8. Keep MySQL in sync for 14 days.**
  - Starts: step 7 finishing.
  - Does: MySQL keeps receiving every write. To roll back, repeat step 7 in reverse: freeze, wait until the Postgres `pending` table is empty (sweepers keep draining it), set MySQL AUTO_INCREMENT above the Postgres sequence, then set `write_mode=dual`. MySQL is the truth again and uses its own `pending` table. No write is lost.
  - State: Postgres `pending`.
  - If it fails: a failed MySQL copy only leaves a `pending` row for the sweeper.
- [ ] **9. Finish.**
  - Starts: at least 14 days after step 7, with a clean comparer pass and an empty Postgres `pending` table.
  - Does: set `write_mode=pg_only`. Writes stop going to MySQL, reads stop falling back to MySQL, and rollback is no longer possible. Then back up and drop the MySQL table, in that order, because after the drop there is no way back.
  - State: none.
  - If it fails: Postgres is already the only truth, so nothing is lost. Fix the problem and retry the backup or the drop.

## Open questions

- The ramp hold time (about an hour) and the sweeper interval (10 seconds) are my choices, not requirements.
- The length of the Postgres write timeout during dual writes (and the MySQL timeout under `pg_primary`) is not set.
- If an erasure cannot reach Postgres and the backfill has already read the row, the user could appear in Postgres until the sweeper deletes it (about 10 seconds). The plan does not close that window.
