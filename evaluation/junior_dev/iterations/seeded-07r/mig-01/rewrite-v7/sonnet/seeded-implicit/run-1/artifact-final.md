# Users migration plan: MySQL to Postgres

We are moving the `users` table (about 38M rows, up to ~3,000 reads/s and ~400 writes/s at peak) from MySQL 8 to the new, empty Postgres 16 cluster `pg-core` with no downtime. Today every read and write of `users` goes through `UserRepository`: reads hit the MySQL replica, writes hit the MySQL primary. The migration logic lives only in that class. The flow is: write to both databases, copy old rows over, prove the two match, move reads, then move writes. MySQL stays the source of truth until the switch, so each stage can be undone.

## Terms

- **Source of truth**: the database whose write commits first and wins any disagreement. MySQL at first, Postgres after the switch.
- **Dual write**: commit to the source of truth first, then apply the same change to the other database.
- **Version rule**: any copy into a database (dual write, backfill or repair) may only insert a missing row or replace a row whose `version` is lower than the incoming one. A copy is skipped if a tombstone exists for that id.
- **Tombstone**: a record that an id was erased by the GDPR job (about 2,000 per day). It stops that user reappearing. Tombstones are never deleted.
- **Pending list**: a table `pending_sync(user_id)` that lives in the source-of-truth database. A write inserts its row in the same transaction as the change itself, so a failed second write is never forgotten.
- **Sweeper**: a background loop (not the Redis job queue, which can be down and drops jobs after 5 retries). Every few seconds it takes each id in the pending list, reads the current row (or its tombstone) from the source of truth, copies it with the version rule, and removes the id from the list.
- **Comparer**: a background scan that compares all rows of both tables by id, in both directions, and reports mismatches.
- **`users.write_mode`**: a string flag with values `mysql_only` (today), `dual_mysql_primary`, `paused`, `dual_pg_primary`, `pg_only`. `users.read_from_pg`: a percentage flag, bucketed by user id.
- **Flag refresh**: each instance caches flags and refreshes every 30 seconds, so instances can disagree for up to 30 seconds. The metric `app_flag_value{flag=...}` shows what each instance is using now.
- **Replica lag**: seconds the MySQL replica is behind, from `mysql_replica_lag_seconds`. Reporting jobs share the replica.

## How it runs

**Writes** (`create`, `update`, `delete`) in a dual mode:
1. Commit to the source of truth, and in the same transaction insert the id into its pending list. Deletes also insert the tombstone in that transaction.
2. Apply the change to the other database with the version rule (a delete removes the row and inserts the tombstone there). On success, remove the id from the pending list.
3. If step 2 fails, ignore the error. The user's request succeeds and the sweeper repairs it later with no manual step. If step 1 fails, the request fails as it does today.

A new user's id is assigned by MySQL while MySQL is the source of truth, and copied to Postgres as an explicit id. After the switch, a Postgres sequence assigns ids (see the switch step).

**Reads**: if `enabled_for("users.read_from_pg", user_id)` is true, read from Postgres, otherwise from the MySQL replica. If the Postgres read errors, fall back to MySQL, so reads never fail.

**Backfill** (one worker, run from the MySQL replica): select rows with `id > last_id` in primary-key order, at most 2,000 per batch. Copy them to Postgres with the version rule. In the same Postgres transaction, save the batch's highest id as `last_id` in the one-row table `backfill_progress`. Before each batch, wait while replica lag is above 5 seconds. After a crash the worker restarts from `last_id`. A second worker would be harmless, because of the version rule.

**Comparer**: skips ids in the pending list and rows changed in the last 60 seconds (replica delay) and checks them on the next pass. Each mismatch id is added to the pending list, so the sweeper repairs it. A pass with no mismatches counts as clean.

**Switching the source of truth** (used for the planned switch and for a rollback, which is the same steps in reverse). Aim for under 90 seconds of paused writes per instance:
1. Set `write_mode=paused`. Instances answer writes with a retryable 503 (clients already retry). Reads continue.
2. Wait until `app_flag_value` shows every instance on `paused`, plus 5 seconds for in-flight writes to finish (about 35 seconds).
3. Wait for the sweeper to empty the pending list. For the switch to Postgres, also set the Postgres id sequence to MySQL's current max id + 1 (exact, because writes are frozen).
4. Set `write_mode` to the new mode. Each instance resumes within 30 seconds.
5. Deadline: if step 4 has not happened 45 seconds after step 1, set `write_mode` back to the previous mode and investigate. Worst case per instance is then about 75 seconds.

After the switch the roles reverse: Postgres is the source of truth, the pending list lives in Postgres, and MySQL receives the copies. MySQL accepts explicit ids and moves its AUTO_INCREMENT past them, so a rollback needs no id fix.

## Rollout checklist

- [ ] **1. Create tables.** Trigger: a manual schema deploy, before any code. Creates Postgres `users` (same columns and types as MySQL, `id` as a sequence-backed bigint), `tombstones`, `pending_sync` and `backfill_progress`, and MySQL `tombstones` and `pending_sync`. State: the tables. Failure: nothing uses them yet, so fix and rerun.
- [ ] **2. Deploy code.** Trigger: a normal deploy. Ships the new `UserRepository`, the sweeper and the comparer, all inert while `write_mode=mysql_only` (the default) and `read_from_pg=0`. State: none. Failure: roll back the deploy.
- [ ] **3. Turn on dual writes.** Trigger: set `write_mode=dual_mysql_primary`. Changes: writes also go to Postgres. State: the pending list in MySQL. Failure: set the flag back to `mysql_only`. Rows that missed Postgres are copied again later by the backfill.
- [ ] **4. Backfill.** Trigger: `app_flag_value` shows every instance on `dual_mysql_primary`. Moves all existing rows with the backfill described above. State: `backfill_progress` in Postgres. Failure: the worker restarts and continues; it never restarts from the beginning.
- [ ] **5. Compare.** Trigger: backfill finished. Run the comparer until one full pass finds zero mismatches. State: none. Failure: mismatches are repaired automatically and the next pass is judged again.
- [ ] **6. Move reads.** Trigger: the clean pass. Set `read_from_pg` to 1, then 10, 50, 100 percent, watching errors and comparer results at each level, then keep 100 percent for at least 3 days with the comparer still running. Failure: set `read_from_pg=0` (takes effect within 30 seconds); the 3 days restart after the fix.
- [ ] **7. Switch the source of truth.** Trigger: 3 days at 100 percent reads with a clean comparer. Run the switching procedure above to `dual_pg_primary`. State: the flag, the sequence and the pending list. Failure: the deadline puts the flag back; to roll back later, run the same procedure to `dual_mysql_primary`. Nothing is lost because MySQL still receives every write.
- [ ] **8. Rollback window.** Trigger: step 7 done. For at least 14 days MySQL stays in sync and rollback stays possible. Failure: use the rollback above.
- [ ] **9. Postgres only.** Trigger: 14 days or more after step 7, with the pending list empty. Set `write_mode=pg_only`, then take a backup of the MySQL table, then drop it. No pause is needed because the source of truth does not change. Failure: before the drop, set `dual_pg_primary` again. After the drop there is no rollback, so check the backup first.

## Failures at a glance

| Where | What happens |
|---|---|
| Postgres write fails after the MySQL commit | The user succeeds. The sweeper repairs it from the pending list. |
| Process dies between commit and the second write | The pending row was committed with the change, so the sweeper repairs it. |
| Backfill copies a row that was just erased | The tombstone blocks the insert. |
| Backfill copy of an older row | The version rule skips it. |
| Backfill crash | Restart at `last_id`. |
| Replica lag above 5 s | Backfill waits. |
| Postgres read error | Fall back to the MySQL replica. |
| Switch not finished in 45 s | The flag goes back to the old mode. |
| Redis down | No effect, because nothing here uses the queue. |

## Open questions

- Reading from Postgres can be briefly behind a just-committed write (the second write follows the first). Not measured; the comparer's 60-second window is a guess.
- The 35-second and 45-second switching timings are untested estimates based on the 30-second flag refresh.
- The sweeper interval and the pending list size alert level are not decided.