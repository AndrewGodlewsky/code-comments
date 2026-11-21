# Move `users` from MySQL 8 to Postgres 16, with no downtime

Today every read and write of `users` goes through one class, `UserRepository`. Reads use the MySQL read replica. Writes use the MySQL primary. The table has about 38 million rows (ids have gaps from deletions), with peaks of about 3,000 reads/s and 400 writes/s. Rows are hard-deleted by the GDPR erasure job (about 2,000 per day). The Postgres 16 cluster (`pg-core`) is provisioned, empty, and the app already holds a connection pool to it.

The migration logic goes in `UserRepository`, in four phases:

1. Write every change to both databases. MySQL commits first and stays the source of truth.
2. Copy the old rows over (backfill) and prove the two tables match.
3. Move reads to Postgres.
4. Swap the roles of the two databases with a short write pause (at most 90 seconds), keep MySQL in sync for at least 14 days so we can roll back, then drop MySQL.

Repair of anything Postgres missed is automatic and uses a durable table, not the Redis job queue. The job queue can lose work: Redis can be down (`enqueue` raises after 1 second), and jobs that fail 5 times go to a dead-letter list that nothing processes.

## Terms

- **Primary / follower**: the primary is the database whose commit decides whether a write succeeded. The other is the follower. MySQL is the primary until the switch.
- **MySQL replica**: the read-only copy of MySQL (`mysql-core-replica`). Reporting jobs share it. Its lag is the metric `mysql_replica_lag_seconds`. Normal lag is under 1 second.
- **Flags**: the existing flag system. Each app instance caches all flags and refreshes them every 30 seconds, so instances can disagree for up to 30 seconds. Each instance exports `app_flag_value{flag=...}`, so we can see when every instance has a change.
- **`users.write_mode`**: a string flag that says where writes go:
  - `mysql_only`: today's behaviour.
  - `dual_mysql`: write MySQL first, then Postgres.
  - `frozen`: reject writes with a retryable 503 (clients already retry). Reads continue.
  - `dual_pg`: write Postgres first, then MySQL.
  - `pg_only`: write Postgres only.
- **`users.read_from_pg`**: a percentage flag (0-100). `flags.enabled_for("users.read_from_pg", user_id)` decides each read. True reads Postgres, false reads the MySQL replica. The same user always gets the same answer.
- **`version`**: a column in `users` in both databases. It starts at 1. Every normal update bumps it by 1 inside the primary (`SET version = version + 1 ... WHERE version = <expected>`). If nothing matches, `StaleWrite` is raised. The app never sets it by hand. In `dual_pg` the repository does the same bump in Postgres. Copies carry the incoming version unchanged.
- **Version rule**: any copy into either database (dual write, backfill, repair) may only insert a missing row, or replace a row whose `version` is lower than the incoming one. A copy whose version is not higher is skipped and counts as done, because the follower already has that version or a newer one. So copies are safe to repeat, safe out of order, and safe alongside normal writes.
- **`pending` table**: one in each database. A row (`seq`, `user_id`) means "this user may differ in the other database". A write adds its row in the same transaction as the write, so the repair note cannot be lost. The row lives in the database that was primary when the write happened.
- **`tombstones` table**: one in each database. It holds the ids of erased users (id only, no personal data). It is written in the same transaction as the delete and kept forever. Ids are never reused.
- **Sweeper**: a loop in its own process, two copies running. It does not depend on `write_mode`. Every 10 seconds it repairs pending rows older than 10 seconds, in both databases' `pending` tables. The age wait only avoids racing the request that just wrote the row. Two copies doing the same work is harmless because of the version rule. It can also be run on demand (steps 7 and 9).
- **Comparer**: a job that checks the two tables against each other.
- **Backfill**: a process that copies existing rows from the replica into Postgres. Its progress is kept in `backfill_progress`, a one-row Postgres table holding the last completed primary key.

## How it runs once deployed

**Write in `dual_mysql`:**
1. In one MySQL transaction, do the write and add a pending row. Commit.
2. Read the committed row from MySQL and apply the whole row to Postgres with a 1-second timeout, under the version rule. A missing row is inserted (the backfill may not have reached it yet). A row at an equal or newer version is skipped. On a create, use the MySQL id explicitly.
3. If Postgres succeeds or skips, delete the pending row. If it fails or times out, leave the pending row and still succeed the request. A Postgres failure never fails the user's request, and the caller cannot tell.
4. If the app crashes after step 1, the pending row is already committed, and the sweeper repairs it within about 20 seconds.

A delete works the same way, except that MySQL deletes the user and inserts a tombstone in one transaction, and Postgres does the same in its own transaction.

**Write in `dual_pg`:** the same flow with the databases swapped. Postgres commits first and MySQL is the follower.

**Tombstone check:** every copy into a database is one statement or transaction that inserts only if no tombstone exists for that id. This stops a slow backfill or repair from bringing back an erased user. If the delete has not reached the follower yet, a stale copy may briefly appear there. The pending row deletes it, and nothing reads it as the truth.

**Sweeper pass:** for each old pending row, the database holding the row is the primary for it and the other is the follower.
1. Read the user from the database holding the pending row (never the replica).
2. If the user exists, copy it to the follower under the version rule.
3. If the user is gone, delete it from the follower, and copy the tombstone there if the primary has one. (A delete always writes a tombstone, so a missing one should not happen. The follower delete is still the safe result.)
4. Delete that pending row by its `seq`. A newer write has its own `seq` and is untouched.

If the follower is down, the pending row stays and is retried on every pass, with no limit. An alert fires if the oldest pending row is older than 5 minutes.

**Read:** go to Postgres when `read_from_pg` says so. If Postgres errors or times out, fall back to the MySQL replica, so reads never fail. A user reading from Postgres right after a write may briefly see old data if Postgres has not received the write yet. That is normally milliseconds, and up to the repair time if Postgres failed. MySQL replica reads already have this kind of lag today, so this is accepted.

## Rollout steps

- [ ] **1. Create the tables.**
  - Starts: an operator runs the schema change before the deploy.
  - Changes: adds `users` and `backfill_progress` in Postgres, and `tombstones` and `pending` in both databases. The Postgres `users` id is a plain bigint with an identity sequence. Backfill and dual writes insert explicit ids, so the sequence is not used yet.
  - State: the schema only. Nothing reads these tables yet.
  - Fails: fix the schema change and rerun it.
- [ ] **2. Deploy the code with `write_mode` at `mysql_only` and `read_from_pg` at 0.**
  - Starts: a normal deploy.
  - Changes: the new `UserRepository` code, the sweepers and the comparer. Behaviour is unchanged until a flag moves.
  - Fails: roll the deploy back.
- [ ] **3. Turn on dual writes.**
  - Starts: the step 2 deploy is complete, with no old-code instance left.
  - Changes: set `write_mode` to `dual_mysql`. Move on when the metric shows `dual_mysql` on every instance.
  - State: pending rows in MySQL.
  - Fails: a Postgres failure never fails a request, and the sweeper repairs it. If the code misbehaves, set `mysql_only`. The comparer and backfill fix any gap later.
- [ ] **4. Backfill.**
  - Starts: step 3's condition is met, meaning every instance is dual-writing.
  - Changes: one backfill process loops:
    1. Wait while `mysql_replica_lag_seconds` is above 5 (reporting jobs share the replica).
    2. Read up to 2,000 rows from the replica with `id` greater than the last completed id, in primary-key order.
    3. Copy them into Postgres under the version rule and the tombstone check.
    4. In the same Postgres transaction, set `backfill_progress` to the batch's last id.
    5. Stop when a batch comes back empty.
  - State: `backfill_progress` in Postgres. Sharing a transaction with the copy means they cannot disagree.
  - Fails: after a crash, restart. It continues after the last completed batch, not from the start. A stale replica row is ignored by the version rule. Rows created after the backfill started are already dual-written.
- [ ] **5. Compare until clean.**
  - Starts: the backfill has finished. An operator starts the comparer.
  - Changes: the comparer walks both tables in id ranges of 2,000, reading the MySQL replica and Postgres. It flags a row that is missing on either side, differs in `version` or fields, or exists in Postgres but not in MySQL. It re-checks each flagged row 60 seconds later against the current primary (MySQL before step 7, Postgres after it), so replica lag and in-flight writes do not count. Rows that still differ are counted as mismatches and also added to that primary's `pending` table, so they are repaired automatically.
  - Clean: one complete pass with zero mismatches. Rerun until it is. Keep running it afterwards, because step 7 needs a clean pass that finished within the last 24 hours. It is not run during the freeze in step 7.
- [ ] **6. Ramp reads.**
  - Starts: the step 5 pass was clean.
  - Changes: set `read_from_pg` to 1, then 10, then 50, then 100. Move up when Postgres read latency, the fallback-to-MySQL count and the mismatch count look no worse than MySQL reads. Move down a step if they do. Stay at 100% for at least 3 days, with the comparer still clean.
  - Fails: set the percentage back. Reads never fail, because of the fallback.
- [ ] **7. Switch the source of truth to Postgres.**
  - Starts: step 6 is done (3 days at 100%) and a comparer pass that finished within the last 24 hours was clean.
  - Budget: writes pause at most 90 seconds: up to 30 s for all instances to see `frozen`, 5 s for in-flight writes, up to 15 s to drain, and up to 30 s for all instances to see `dual_pg`.
  - Changes:
    1. Set `write_mode` to `frozen`. Wait until the metric shows `frozen` on every instance, then 5 more seconds. Writes get a retryable 503.
    2. Drain: run the sweeper on demand, skipping its 10-second age check (writes are frozen, so no pending row is still being written), until MySQL's pending table is empty. Abort if this takes more than 15 seconds.
    3. Set the Postgres id sequence with `setval` to the largest of: MySQL's next AUTO_INCREMENT value, the largest Postgres user id plus 1, and the largest tombstone id plus 1. Without this, Postgres would start at 1 and clash with existing users, or reuse an erased user's id.
    4. Set `write_mode` to `dual_pg`.
  - Fails: if the drain or any step fails, set `write_mode` back to `dual_mysql`. This pause is bounded the same way. Nothing was written to Postgres as the primary yet.
- [ ] **8. Keep MySQL in sync for at least 14 days.**
  - Starts: step 7 is done. Mode is `dual_pg`: Postgres is primary, and the sweeper repairs MySQL through the Postgres pending table.
  - Rollback during these days: this is the step 7 pause in reverse, also at most 90 seconds. First set `read_from_pg` to 0, because Postgres will lag once MySQL is primary again. Then set `frozen`. Instances refresh all flags together, so once every instance shows `frozen` it also has `read_from_pg` at 0, and no extra wait is needed. Then drain the Postgres pending table (skipping the age check) until empty, set MySQL's AUTO_INCREMENT to at least the Postgres next id, and set `dual_mysql`. No write is lost, because MySQL has everything Postgres had and the version rule cannot lose a newer row. Both pending tables are empty at the switch, so nothing is left over. After this, new writes add pending rows in MySQL, and the sweeper copies them to Postgres.
- [ ] **9. Go Postgres-only, then drop MySQL.**
  - Starts: at least 14 days after step 7, the comparer is clean and no pending rows remain.
  - Changes:
    1. While still in `dual_pg`, back up the MySQL `users` table and check that the backup restores. If the check fails, stay in `dual_pg` and fix the backup. Nothing has changed yet.
    2. Set `write_mode` to `pg_only`. No pause is needed, because the source of truth does not change. This is the point of no return: MySQL no longer receives writes, so rollback is no longer possible.
    3. Wait until the metric shows `pg_only` on every instance. Then run the sweeper on demand until the Postgres pending table is empty. Instances still in `dual_pg` during the 30-second delay may have left pending rows, and these must reach MySQL before it is dropped. After this, no new pending rows appear.
    4. Drop the MySQL `users` table. Remove the dual-write and sweeper code in a later deploy.
  - Fails: before step 2, nothing is lost. After step 2, fix forward on Postgres.

## What happens when things fail

| What fails | What happens |
|---|---|
| Postgres write in `dual_mysql` | The request succeeds. The pending row stays and the sweeper repairs it. |
| MySQL write in `dual_pg` | The same, with the roles swapped. |
| App crash after the primary commit | The pending row was committed with the write. The sweeper repairs it. |
| A sweeper copy keeps failing | Retried on every pass. An alert fires after 5 minutes. No manual step. |
| Unique email clash on a copy (a new user took an erased user's email before the erase reached the follower) | The copy retries until the erase reaches the follower. |
| Backfill crash | Restart and continue after the last completed batch. |
| Postgres read error | Fall back to the MySQL replica. |
| Drain too slow, or any step fails during a switch | Return to the previous mode. |
| Instances disagree during the 30-second flag delay | Safe: in every pair of modes a switch passes through, no two instances write to different primaries, because `frozen` comes first. |

## Open questions

- The exact thresholds for stepping the read ramp up or down (latency and fallback rate) are not set. The hold time per step is also not set.
- Where the sweeper, backfill and comparer processes are deployed is not decided. Who notices a crashed backfill and restarts it is not decided either: it needs a restarting supervisor or an operator. Where an operator runs the on-demand sweeper (steps 7, 8 and 9) is also not decided.
- How long one comparer pass takes over 38 million rows (about 19,000 ranges) is not measured. The 24-hour limit on the last clean pass assumes a pass finishes well within a day.
- Tombstones are kept forever. Revisit if the table gets large (about 2,000 added per day).
