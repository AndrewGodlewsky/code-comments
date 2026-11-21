# Users migration plan: MySQL to Postgres

Today every read and write of `users` goes through `UserRepository`. It reads from the MySQL replica and writes to the MySQL primary. We move the table to Postgres 16 (`pg-core`) without downtime, in four stages. First every write goes to MySQL and then to Postgres. Next the table is copied over and checked. Then reads move. Last, the source of truth moves, after a short write pause. Each stage can be undone until MySQL is dropped. A background sweeper repairs anything Postgres missed, so a Postgres failure never fails a user request.

## Terms

- **Source of truth (primary):** the database whose write decides success. The other database is the secondary. Both are named by `users.write_mode`.
- **Version:** an `INT` column on every `users` row. It starts at 1. A normal update adds 1 (`UPDATE ... WHERE id = %s AND version = %s`), and `StaleWrite` is raised when that check matches no row. A copy to the secondary carries the version unchanged and does not add 1.
- **Version rule:** any copy into the secondary (dual write, backfill or repair) may only insert a missing row, or replace a row whose `version` is lower than the incoming one. In Postgres this is `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. Deletes are not copies; see the dual write.
- **`users.write_mode`:** a string flag with four values.
  - `mysql_only`: the state today.
  - `dual_mysql_primary`: write MySQL, then Postgres.
  - `dual_pg_primary`: write Postgres, then MySQL.
  - `pg_only`: write Postgres only.

  Postgres is the primary in `dual_pg_primary` and `pg_only`. MySQL is the primary otherwise. The repository code today runs on MySQL only, so running the same logic on Postgres is new work.
- **`users.write_paused_until`:** a string flag holding a UTC time, or empty. While the current time is before it, every write request gets a retryable 503. Reads are unaffected. Because it is a deadline, a pause ends by itself even if nobody clears it.
- **`users.read_from_pg`:** a percentage flag. `flags.enabled_for("users.read_from_pg", user_id)` decides per user whether a read goes to Postgres or to the MySQL replica, and the same user always gets the same answer. If a Postgres read fails, it falls back to the replica, so reads never fail.
- **Flag refresh:** each instance caches all flags and refreshes them every 30 seconds, so instances can disagree for up to 30 seconds. Each instance exports the values it uses as `app_flag_value{flag=...}`, so we can see when all of them have a change. Flags change as one set, so an instance sees the changes made together at the same time.
- **Pending table (`user_sync_pending`):** one row per user id whose latest write may not have reached the secondary, plus a random `token` that every write replaces. It lives in the primary database. A row is added in the same transaction as the write, so it cannot be lost. A row is removed only if its token is still the one the remover read, so a newer write's pending row is never removed by mistake.
- **Tombstone table (`user_tombstones`):** ids of users deleted by the erasure job (the GDPR job that hard-deletes about 2,000 users a day). It lives in the secondary database. A copy is skipped if the id has a tombstone, so a deleted user never comes back from a stale copy.
- **Per-user lock:** every write to a user row in the secondary first takes a lock on that id (`pg_advisory_xact_lock(id)` in Postgres, `GET_LOCK('user:<id>')` in MySQL). A copy and a delete of the same user then never overlap, so a copy cannot slip in between a delete and its tombstone.
- **Sweeper:** a loop in a worker process that repairs pending rows. It is a loop and not `jobs.enqueue` because Redis can be down, and jobs that fail 5 times go to `jobs:dead`, which nothing processes.
- **Comparer:** a worker process that checks the two tables against each other.
- **Backfill:** a one-time copy of the existing MySQL rows (about 38 million) into Postgres.
- **`backfill_progress`:** a one-row Postgres table holding `last_id`, the last id of the last completed backfill batch.

## How it runs

**Dual write** (`create`, `update`, `delete` in `UserRepository`):

1. In one transaction on the primary, do the normal write (the existing logic, run on whichever database is primary) and add a pending row for the user id. A create uses the id the insert returns. If the write raises `StaleWrite`, the transaction rolls back and nothing is pending.
2. After commit, read the row back from the primary and apply it to the secondary with a 1 second timeout. A create copies the explicit id. A copy uses the version rule and the per-user lock. A delete has no version check: it takes the lock, then adds a tombstone and removes the row, in one secondary transaction.
3. If the secondary succeeds, remove the pending row (only if its token is unchanged). If it fails or times out, log it and return success to the user. The pending row stays for the sweeper.

**Sweeper:**

- Several sweepers may run at once. Two repairing the same row do no harm, because a copy is safe to repeat and a pending row is removed only if its token is unchanged.
- Every 10 seconds it reads `users.write_mode` to find the primary, and takes up to 500 rows from that primary's pending table, oldest first. It takes only rows older than 30 seconds, so it does not race a dual write still in progress. While a pause is active it takes all rows regardless of age, because no write is in progress.
- For each row it reads the user from the primary. If the user exists, it copies it to the other database with the version rule. If not, the user was erased, so it adds a tombstone and deletes the secondary row.
- It then removes the pending row (only if its token is unchanged). A failure is retried on the next loop, with no retry limit. In `pg_only` there is no secondary, so it does nothing. In `mysql_only` it still drains leftover rows to Postgres.
- It alerts if the oldest pending row is over 5 minutes old.

**Comparer:**

- One pass walks the MySQL replica and Postgres in id order, 2,000 rows at a time, and compares every column. It pauses when replica lag is above 5 seconds.
- It rechecks each mismatch against the primaries after 30 seconds. If it is still there, the comparer adds a pending row for that id and counts it in `users_compare_mismatches`. The sweeper then repairs it. A Postgres row whose id has a tombstone also counts as a mismatch.
- A pass is clean when it ends with zero confirmed mismatches. Progress is not saved, and an interrupted pass restarts.

**Backfill:**

- It starts only when every instance runs the new code and `app_flag_value{flag="users.write_mode"}` shows `dual_mysql_primary` on all of them.
- It reads the replica in primary-key order, 2,000 rows per batch, and waits 10 seconds whenever `mysql_replica_lag_seconds` is above 5 (reporting jobs share the replica).
- Each batch is one Postgres transaction. It takes the per-user locks in id order, copies the rows with the version rule, skips tombstoned ids, and sets `last_id`. After a crash it continues after `last_id`, not from the start.
- Old replica data cannot overwrite newer dual-written rows (version rule) and cannot revive erased users (tombstones).

**Switching the source of truth.** The planned switch and a rollback use the same script. Writes may be paused for at most 90 seconds, counted from setting the pause in step 1 until every instance has the new mode.

1. Set `users.write_paused_until` to now plus 90 seconds. Wait until every instance reports it (at most about 30 seconds). Then wait 10 more seconds for in-flight writes to finish.
2. Wait until the current primary's pending table is empty (allow up to 15 seconds). The sweeper drains it, ignoring its age limit during the pause.
3. Switch only: set the Postgres id sequence to the larger of (the highest `users.id` in MySQL, the highest tombstone id) plus 1,000,000. Ids are not reused, and a new user never collides with a tombstone. Allow up to 5 seconds.
4. In one flag change, set `users.write_mode` to the new value and clear `users.write_paused_until`. A rollback also sets `users.read_from_pg` to 0. This must be issued within 60 seconds of step 1, so the change has 30 seconds to reach every instance inside the 90.
5. If any wait runs out of time or step 4 cannot be issued by then, abort: clear `users.write_paused_until` and leave `write_mode` unchanged. Writes resume where they were.
6. If the script crashes, nobody has to notice. The pause expires at its deadline. `write_mode` is unchanged unless step 4 had already been issued, and that is one atomic change.

New ids come from MySQL `AUTO_INCREMENT` until the switch, and from the Postgres sequence after it. On rollback, MySQL receives those rows with explicit ids, and its auto-increment moves past them.

## Rollout checklist

- [ ] **1. Create tables** (manual migration). Postgres gets `users` (same columns as MySQL, unique `email`), `user_tombstones`, `user_sync_pending` and `backfill_progress`. MySQL gets `user_tombstones` and `user_sync_pending`. They are unused until step 2. If it fails, fix and rerun, because the changes only add tables.
- [ ] **2. Deploy** the new `UserRepository`, sweeper and comparer. `write_mode` is still `mysql_only`, so behavior is unchanged. If it goes wrong, roll the deploy back.
- [ ] **3. Turn on dual writes** (flag change: `write_mode` = `dual_mysql_primary`). Wait until all instances report it. If anything looks wrong, set it back to `mysql_only`; the sweeper keeps draining pending rows.
- [ ] **4. Backfill** (starts when the conditions in the Backfill section hold). Progress lives in `backfill_progress`, and a crash resumes from `last_id`.
- [ ] **5. Run the comparer** until one full pass is clean. Mismatches are repaired automatically, so just rerun passes. Keep it running from here on.
- [ ] **6. Ramp reads** (flag change: `read_from_pg` 1, 10, 50, 100). Hold each step at least 1 hour. Go on only if the fallback rate to the replica is under 0.1%, Postgres read p99 latency is at most 1.5 times MySQL's, and the comparer is still clean. Otherwise set the flag back to the previous value. At 100%, hold for at least 3 days, and the latest comparer pass must be clean.
- [ ] **7. Switch the source of truth** (an operator runs the switch script with `write_mode` = `dual_pg_primary`). Writes pause for at most 90 seconds with 503s. Reads keep going.
- [ ] **8. Wait 14 days.** MySQL is now the secondary and gets every write through the same pending and sweeper mechanism, with the roles swapped. To roll back, run the switch script with `write_mode` = `dual_mysql_primary` and `read_from_pg` = 0. It pauses writes for at most 90 seconds, and no write is lost.
- [ ] **9. Postgres only**, no sooner than 14 days after step 7 (flag change: `write_mode` = `pg_only`). No pause is needed, because instances still dual-writing for up to 30 seconds do no harm. After this, rollback is no longer possible. Then back up the MySQL `users` table, drop it, and drop the MySQL pending and tombstone tables.

## What happens when things fail

| What fails | What happens |
|---|---|
| Secondary write fails or times out | The request still succeeds. The pending row stays, and the sweeper repairs it within about a minute. |
| App crashes after the primary commit | The pending row was committed with the write, and the sweeper repairs it. |
| Postgres is down while MySQL is primary | Same as above, and pending rows pile up. The sweeper alerts after 5 minutes and drains them when Postgres returns. |
| Postgres read fails | The read falls back to the MySQL replica. |
| Primary fails while Postgres is primary | The write fails, as it did with MySQL before. This is the cost of a single source of truth. |
| Backfill crashes or the replica lags | It resumes from `last_id`, or waits until lag is under 5 seconds. |
| Switch cannot finish in time | The script aborts and clears the pause. The mode is unchanged; retry later. |
| Switch script crashes while paused | The pause expires at its deadline (at most 90 seconds). The mode is unchanged. |
| Stale copy of a deleted user | It is skipped because of the tombstone, or removed by the comparer and sweeper. |

## Open questions

- The 10 second wait for in-flight writes assumes the longest request is shorter than that. The real request timeout is unknown and should be checked.
- The pause deadline is compared with each instance's own clock. We assume clocks agree to within a few seconds. This is not verified.
- A copy can fail because of the unique `email` index (for example two users swapping emails). It stays pending and retries, and may need a manual look. The brief does not say how to handle it.
- The ramp thresholds (0.1%, 1.5 times, 1 hour), the 1 second secondary timeout, the 60 second step budget and the 1,000,000 id margin are our own picks, not from the brief.
