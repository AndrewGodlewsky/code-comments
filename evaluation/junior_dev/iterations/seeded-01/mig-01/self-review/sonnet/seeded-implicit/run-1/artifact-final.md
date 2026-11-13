# Users migration plan: MySQL to Postgres, no downtime

Goal: move the `users` table from MySQL 8 (`mysql-core-primary`, with read replica `mysql-core-replica`) to Postgres 16 (`pg-core`) while the service keeps running. All access to `users` already goes through `UserRepository`, so all migration logic lives there.

## How it works (read this first)

**Terms.**
- *Source of truth*: the database whose commit decides whether a write succeeded. The other database is a copy.
- *Pending row*: a record, written in the same transaction as a user write, saying "this user still has to be copied to the other database".
- *Sweeper*: a loop in the worker processes that reads pending rows and performs the copies.
- *Tombstone*: a row in `user_tombstones` recording that a user was deleted, so that a stale copy cannot bring the user back.
- *Comparer*: a worker job that compares the two tables and reports mismatches.
- *Backfill*: a worker job that copies the existing rows into Postgres.

**Flags.** Two flags control everything. Instances cache flags and refresh them every 30 seconds, so after a change instances can disagree for up to 30 seconds. Each instance exports the value it is using as the metric `app_flag_value{flag=...}`. **"Confirmed"** below means: every running instance reports the new value in that metric (the number of instances reporting it equals the number of running instances).

- `users.write_mode` (string):

  | value | what a write does |
  |---|---|
  | `mysql_only` | MySQL only. This is today's behaviour and the starting value. |
  | `dual` | Commit to MySQL (source of truth), then copy to Postgres. |
  | `paused` | Return a retryable 503 without touching either database. |
  | `pg_primary` | Commit to Postgres (source of truth), then copy to MySQL. |
  | `pg_only` | Postgres only. |

- `users.read_from_pg` (percentage, bucketed by user id with `flags.enabled_for`, so a given user always gets the same answer). A read routed to Postgres falls back to the MySQL replica if Postgres errors or has no row, so reads never fail. (The fallback is removed with the MySQL table in step 11.)

**The copy rule (MySQL to Postgres).** Every copy into Postgres, whether from a dual write, the backfill or a repair, goes through one function, `copy_to_pg(row)`. In a single Postgres transaction it:

1. takes `pg_advisory_xact_lock(user_id)`, a lock on that user id that serialises copies and deletes of the same user;
2. does nothing if `user_tombstones` has that user;
3. otherwise inserts the row, or updates the existing row only if the stored `version` is lower than the incoming one (`ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`).

Deletes go through `delete_in_pg(user_id)`: under the same advisory lock, insert a row into `user_tombstones` and delete the user. Example of what the tombstone prevents: a backfill batch was read from the replica just before the erasure job ran, and is applied after the delete. Without the tombstone it would re-insert the deleted user. Tombstones are tiny (about 2,000 per day) and are kept.

**Repair uses a pending table, not the job queue.** Jobs are retried for only about 15 minutes and then go to a dead-letter list that nothing processes, and `enqueue` itself can fail. So jobs cannot guarantee "fixed automatically, always". Instead:

- In `dual` mode, each write also puts a row into the MySQL table `users_pg_pending (user_id PRIMARY KEY, seq, created_at)` **inside the same MySQL transaction** as the write. Repeated writes to one user bump `seq`. The write is therefore either fully recorded or not committed at all, even if the app crashes right after the commit.
- After the commit, the repository tries the Postgres copy (1 second timeout). If it succeeds, it deletes the pending row `WHERE user_id = ? AND seq = ?`. If it fails or times out, it logs and counts the failure and still returns success to the user. The pending row stays.
- The **sweeper** runs every 5 seconds. For each pending row older than 5 seconds it re-reads the user's current state from the MySQL primary. If the row exists it calls `copy_to_pg`. If the row is gone it calls `delete_in_pg`. Then it deletes the pending row with the same `seq` check, so a write that arrived in the meantime keeps its row for the next pass. The sweeper is idempotent, so running more than one is safe.
- Alerts: pending row count, and age of the oldest pending row.

**Reverse direction (used after the switch).** In `pg_primary` mode the roles swap. The Postgres table `users_mysql_pending` is written in the same Postgres transaction as the write, and the sweeper copies from Postgres to MySQL with the same version rule (insert, or update only if the stored version is lower). No tombstones are needed in this direction: every copy to MySQL is driven by a pending row, and a delete bumps that row's `seq`, so a stale copy is corrected on the next sweep.

## Checklist

- [ ] **1. Create the tables**
  - **Starts when:** this is the first step, run as a manual schema migration.
  - **Changes:** nothing in app behaviour. Creates:
    - Postgres `users`, with the same columns as MySQL, a unique `email`, and `id BIGINT GENERATED BY DEFAULT AS IDENTITY`. "By default" means explicit ids can be inserted now (the backfill needs that), and the sequence supplies ids after the switch.
    - Postgres `user_tombstones (user_id PRIMARY KEY, deleted_at)`, `migration_progress (name PRIMARY KEY, last_id)` and `users_mysql_pending`.
    - MySQL `users_pg_pending`.
  - **State:** the empty tables only.
  - **If it fails:** the DDL is idempotent (`IF NOT EXISTS`). Re-run it. Nothing uses these tables yet.

- [ ] **2. Deploy the new code, with everything still off**
  - **Starts when:** step 1 is done. Normal rolling deploy.
  - **Changes:** the new `UserRepository` (all five write modes and the `read_from_pg` path), plus three worker jobs: the sweeper, the backfill and the comparer. Flags stay at `users.write_mode=mysql_only` and `users.read_from_pg=0`, so behaviour is unchanged.
  - **State:** none new.
  - **If it fails:** roll the deploy back. Nothing depends on it.
  - **Done when:** every instance runs the new version and exports `app_flag_value{flag="users.write_mode"}`.

- [ ] **3. Turn on dual writes**
  - **Starts when:** step 2 is done. Set `users.write_mode=dual`.
  - **Changes:** from now on every create, update and delete commits to MySQL together with its pending row, then is copied to Postgres under the copy rule. Ids still come from MySQL `AUTO_INCREMENT` and are inserted into Postgres explicitly.
  - **State:** `users_pg_pending` in MySQL (drained continuously by the sweeper).
  - **Confirm:** every instance reports `dual`, then wait one more minute so requests that started under the old value finish. **The backfill must not start before this.**
  - **If it fails:** a Postgres failure only grows the pending table, and the sweeper fixes it once Postgres is back. If the code itself misbehaves, set the flag back to `mysql_only`. Pending rows already written are still swept. Before turning `dual` on again, reset the backfill progress (step 4) to 0, because writes made in `mysql_only` mode were not recorded.

- [ ] **4. Backfill existing rows**
  - **Starts when:** step 3 is confirmed (all instances dual-writing). A worker starts the backfill. A Postgres advisory lock allows only one backfill runner at a time.
  - **Changes:** copies about 38 million rows (about 19,000 batches of 2,000) into Postgres. Each batch:
    1. Wait while `mysql_replica_lag_seconds` is above 5, checking again every 10 seconds. The reporting jobs share this replica.
    2. Read from the replica: `WHERE id > last_id ORDER BY id LIMIT 2000`.
    3. In one Postgres transaction, apply `copy_to_pg` to every row **and** set `migration_progress.last_id` to the batch's highest id.
  - **State:** `migration_progress.last_id` in Postgres. It is updated in the same transaction as the batch, so it is never ahead of or behind the copied data. After a crash the job continues from `last_id`, not from the start.
  - **If it fails:** a failed batch rolls back as a whole and is retried after a backoff. A stale replica read is harmless because of the version rule, and tombstones cover users deleted in the meantime. Rows created or changed during the backfill arrive through dual writes.
  - **Done when:** a batch returns no rows. Record that in `migration_progress`.

- [ ] **5. Compare the two tables until they match**
  - **Starts when:** the backfill is done and the pending table is nearly empty. The comparer is a worker job.
  - **Changes:** nothing in user-facing behaviour. It walks both tables in id ranges (MySQL read from the replica, with the same lag pause as the backfill) and compares every column. It also flags any row that exists on only one side, and any Postgres row whose id has a tombstone.
    - To ignore writes still in flight, it skips ids that have a pending row, and re-checks every other difference against the MySQL primary and Postgres after one minute.
    - A difference that survives the re-check counts as a mismatch. The comparer also creates a pending row for that user, so the normal repair path fixes it.
  - **State:** results are logged and exported as a metric. A crashed pass simply restarts.
  - **If it fails:** a pass with mismatches is not clean. Investigate the cause (the repair path should already be fixing the rows), then run another full pass.
  - **Done when:** one full pass finds **zero** mismatches.

- [ ] **6. Move reads to Postgres gradually**
  - **Starts when:** step 5 has produced a clean pass. Set `users.read_from_pg` to 1, then 10, then 50, then 100. Wait at least 5 minutes at each level, and watch the error rate and read latency before going up.
  - **Changes:** the share of reads served by Postgres. Writes are unaffected (still MySQL first).
  - **State:** only the flag.
  - **If it fails:** Postgres errors fall back to the replica, so users do not see failures. If errors or latency are worse than at 0%, set the flag back to 0 and investigate. When 100% is reached again, the 3-day clock in step 7 starts over.

- [ ] **7. Soak at 100% reads for 3 days**
  - **Starts when:** `users.read_from_pg` reaches 100%.
  - **Changes:** nothing. The comparer runs daily, and the pending table must stay near zero.
  - **State:** the clock is the time since the flag reached 100% and stayed there.
  - **If it fails:** any rollback of the read flag, or a comparer pass with mismatches, restarts the 3 days once it is fixed.
  - **Done when:** at least 3 days have passed at 100%, the last comparer pass was clean and started within the last 24 hours, and the pending table is empty.

- [ ] **8. Switch the source of truth to Postgres (writes paused for at most 90 seconds)**
  - **Starts when:** step 7 is done. An operator runs this as a short runbook while watching the clock.
  - **Changes:**
    1. Set `users.write_mode=paused`. Instances stop writing within 30 seconds and return a retryable 503. Reads continue. Wait until `paused` is confirmed, then 5 more seconds so in-flight writes finish. After this no instance can still be on `dual`, so no write can reach MySQL later.
    2. Wait for `users_pg_pending` to be empty. With writes stopped, the sweeper empties it within seconds. Postgres then holds every committed MySQL write.
    3. Set the Postgres identity sequence with `setval` to the larger of two values: MySQL's next `AUTO_INCREMENT` value (read after `SET SESSION information_schema_stats_expiry=0`, so it is not a cached value), and `max(id)+1` over Postgres `users` and `user_tombstones`. The `AUTO_INCREMENT` value is needed because the highest id ever issued may belong to a deleted user, and that id must never be reused.
    4. Set `users.write_mode=pg_primary`. Writes resume within 30 seconds, when the instances load the flag. From now on a write commits to Postgres first, together with a row in `users_mysql_pending`, and is then copied to MySQL.
  - **Time budget:** 30 s to pause + 5 s drain + at most 20 s for steps 2 and 3 + 30 s to resume = about 85 s, under the 90 s limit. Rehearse in staging.
  - **State:** the flag, the sequence value, and `users_mysql_pending` in Postgres. A `migration_progress` row records the switch time, which starts the 14-day clock in step 9.
  - **If it fails:** if steps 2 and 3 are not finished 20 seconds after the 5-second wait, set `users.write_mode=dual`. Writes resume on MySQL within 30 seconds (about 85 s in total) and nothing has changed. Fix the problem and start again.

- [ ] **9. Run on Postgres as source of truth for at least 14 days, with rollback available**
  - **Starts when:** step 8 completes.
  - **Changes:** nothing new. The sweeper keeps MySQL in sync from `users_mysql_pending`. The comparer runs daily in both directions. If MySQL is unavailable the user's write still succeeds, because the pending row waits in Postgres.
  - **State:** Postgres is the truth. MySQL is a copy that is never more than the pending backlog behind.
  - **Rollback to MySQL (any time before step 10):**
    1. Set `users.write_mode=paused` and wait until `paused` is confirmed, plus 5 seconds.
    2. Wait for `users_mysql_pending` to be empty.
    3. Run `ALTER TABLE users AUTO_INCREMENT = <Postgres sequence value>`, so MySQL cannot reuse an id that Postgres issued and then deleted. A reused id would hit a Postgres tombstone and be silently dropped.
    4. Set `users.write_mode=dual`. If reads on Postgres are the problem, also set `users.read_from_pg` to 0.
    5. Same 90-second budget and abort rule as step 8: if rollback steps 2 and 3 take more than 20 seconds after the 5-second wait, set `pg_primary` again.
  - No write is lost, because MySQL is only unpaused after its backlog is empty. To try the switch again, repeat steps 7 and 8 first. The 14 days then start again.
  - **If it fails:** a persistent backlog in `users_mysql_pending` or a comparer mismatch blocks step 10 until it is fixed.

- [ ] **10. Stop copying to MySQL: `pg_only`**
  - **Starts when:** at least 14 days have passed since step 8, the last comparer pass was clean, and `users_mysql_pending` is empty. Set `users.write_mode=pg_only`.
  - **Changes:** writes go to Postgres only. No pause is needed, because the source of truth does not change. Instances that still copy to MySQL for up to 30 seconds do no harm.
  - **State:** just the flag. The pending table is no longer written.
  - **If it fails:** this is the point of no return for rollback. Once `pg_only` is confirmed on all instances, MySQL stops receiving writes and can no longer be used to roll back. If a problem shows up right away, set `pg_primary` again. Writes made under `pg_only` have no pending row, so MySQL is missing them. Run a comparer pass; it creates pending rows for the differences and the sweeper catches MySQL up.

- [ ] **11. Back up and drop the MySQL table**
  - **Starts when:** step 10 is confirmed on all instances and nothing has needed rollback.
  - **Changes:** take a full dump of MySQL `users` and check that it restores. Only then run `DROP TABLE users` and drop `users_pg_pending`. Then deploy a cleanup that removes the MySQL code paths, the fallback read, the sweeper, the backfill, the comparer and the migration flags. The tombstone table can stay.
  - **State:** the backup file is the only remaining copy of the MySQL data. Keep it for as long as the retention policy requires.
  - **If it fails:** the drop is the only irreversible action, and only restoring the backup can undo it. If the restore check fails, do not drop the table; take a new dump.
