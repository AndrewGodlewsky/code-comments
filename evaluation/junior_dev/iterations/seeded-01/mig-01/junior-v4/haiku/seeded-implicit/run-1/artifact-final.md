# Users migration plan

## What this is and how it goes

Today `UserRepository` reads from the MySQL replica, writes to the MySQL primary, and uses `version` for optimistic locking. We move the `users` table to Postgres 16 (`pg-core`) without downtime. Every write is copied to Postgres while MySQL stays the source of truth. Old rows are backfilled, and the two tables are compared until they match. Reads then move to Postgres in steps. Postgres becomes the source of truth, and MySQL stays in sync for 14 days so we can roll back. After that, the MySQL table is dropped.

Each copy to the other database is best effort. If a copy fails, a `pending` row remembers it, and a sweep copies it later.

## Terms

- **Source of truth**: the database that takes each write first. Set by the flag `users.write_mode`.
- **`users.write_mode`**: a string flag in `app.flags`. Values: `mysql`, `dual`, `paused` (writes get a retryable 503), `pg_primary`, `pg_only`.
- **Version**: the `version` column. Create sets it to 1. Each update adds 1. Erase does not change it.
- **Copy rule**: how a row reaches the other database. In one transaction that locks the user id in the target: if the target has a tombstone for the id, do nothing; if it has no row, insert the row; if its row has a lower `version`, replace it; otherwise do nothing.
- **Tombstone**: a record that a user id was erased. Every erase writes one in both databases. Tombstones are never removed.
- **Pending row**: one per user id whose copy is not confirmed. It lives in the source database and is written in the same transaction as the change. It holds the user id, the `version`, and an `erased` flag. A newer write replaces it.
- **Sweep**: a job that runs every minute. For each pending row, it copies the current source row to the other database. For an erased row, it copies the tombstone and removes the row there. Then it deletes the pending row only if the row's `version` still matches the copied version. If not, the next sweep copies again.
- **Comparer**: a job that compares the two tables id by id.
- **Job progress**: one MySQL row each for backfill and the comparer. It holds `last_id`, a `done` flag, and a heartbeat (the last time the job saved progress).
- **Dead-lettered**: after 5 failed retries (about 15 minutes), the job system moves a job to `jobs:dead`, where nothing picks it up again.
- **Migration state**: one MySQL row that holds the time `read_from_pg` reached 100%.

Each instance refreshes flags every 30 seconds. A step that changes a flag waits until `app_flag_value{flag=...}` shows the new value on every instance.

## Steps

- [ ] **1. Create the tables.**
  - Starts: a one-time migration run.
  - Does: Postgres gets `users` (primary key `id`, no sequence yet), `tombstones` and `pending`. MySQL gets `tombstones`, `pending`, the job progress table and `migration_state`.
  - State: the new tables.
  - If it fails: drop the new tables. Nothing reads them yet.

- [ ] **2. Deploy the new UserRepository, sweep and comparer.**
  - Starts: a normal deploy. `write_mode` stays `mysql`.
  - Does: writes still go only to MySQL. An erase also writes a tombstone in MySQL. The sweep is scheduled to run every minute.
  - State: nothing new moves.
  - If it fails: roll back the deploy. No data has moved.

- [ ] **3. Turn on dual writes.**
  - Starts: set `write_mode` to `dual`. Wait until every instance shows `dual`.
  - Does:
    - Create or update: commit in MySQL, with the pending row in the same transaction. Then, in the same request and before the response, run the copy rule in Postgres for that user, with a short timeout. On success, delete the pending row if its `version` is unchanged.
    - Erase: in MySQL, delete the user row, write a tombstone and write a pending row with `erased` set. Then the Postgres copy writes the tombstone and deletes the Postgres row in one transaction.
  - State: MySQL is the source. Pending rows in MySQL show what Postgres lacks.
  - If it fails:
    - MySQL fails: the request fails as it does today. Nothing is copied.
    - Postgres fails or times out: the request still succeeds. The pending row stays, and the sweep retries it.
    - The process dies after the MySQL commit: the pending row is already committed, so the sweep copies it.

- [ ] **4. Backfill from the replica.**
  - Starts: an operator enqueues the backfill job once every instance shows `dual`.
  - Does, for each batch, in id order:
    1. Wait while `mysql_replica_lag_seconds` is above 5. Recheck every 10 seconds.
    2. Read up to 2,000 rows from the replica with `id` above `last_id`.
    3. On the MySQL primary, skip any id that has a pending or tombstone row. The sweep or the erase handles those.
    4. Copy the rest with the copy rule.
    5. In one MySQL transaction, set `last_id` to the batch's highest id and update the heartbeat.
    
    Stop when a batch is empty, and set `done`.
  - State: the backfill progress row in MySQL.
  - Restart: the sweep enqueues a new run when backfill is not `done` and its heartbeat is more than 10 minutes old. This covers a dead-lettered job.
  - If it fails:
    - The job crashes: the next run continues from `last_id`. Copying a batch twice is harmless, and `last_id` only moves forward.
    - Postgres fails: `last_id` is not saved, so the batch is retried.

- [ ] **5. Compare until clean.**
  - Starts: an operator enqueues the comparer once backfill is `done`.
  - Does: a pass compares both tables in id order, from the first id, 2,000 ids per batch, with the same lag wait. For each id that differs, it re-reads the row from the MySQL primary. If the row still differs, it applies the copy rule and counts a mismatch. An id missing on both sides, or tombstoned in Postgres, is not a mismatch.
  - Clean: one full pass with zero mismatches and no pending rows in MySQL. Run passes back to back until one is clean.
  - State: the comparer progress row in MySQL.
  - If it fails: the sweep restarts it, using the same heartbeat rule as backfill.

- [ ] **6. Ramp reads.**
  - Starts: a clean comparison. Set `read_from_pg` to 1, then 10, 50 and 100 percent. Each step waits 24 hours (our choice; the brief does not set it). Each step needs the comparer still clean and no Postgres read errors.
  - Does: a user reads from Postgres when `enabled_for("users.read_from_pg", user_id)` is true, so the same user always gets the same answer. Other users read from the MySQL replica. A Postgres read error falls back to the replica, so reads never fail because of Postgres.
  - State: the flag. At 100%, write the time to migration state.
  - If it fails or needs backing out: lower the percentage. Reads move back within 30 seconds. Clear the time in migration state.
  - Known gap: if a write's Postgres copy failed, the sweep has not copied it yet. For up to about one minute, a Postgres read can show the old row after an update, or no row after a create. It does not error. This includes the user's own change. We accept this, because checking pending on every read would add a query to a path that runs about 3,000 times a second.

- [ ] **7. Make Postgres the source (`pg_primary`).** Writes pause for this step, and the pause must stay under 90 seconds.
  - Starts: a person, by hand, once reads have been at 100% for at least 3 days and the comparer is clean. No script runs this step.
  - Does, in order:
    1. Set `write_mode` to `paused`. Wait until every instance shows it. Writes get a retryable 503.
    2. Wait 10 seconds for in-flight writes to finish.
    3. Run the sweep and wait until pending is empty in MySQL. Also check that Postgres has no pending rows. It should have none, because it is not the source before this step.
    4. Set the Postgres id sequence to the larger of the two tables' max ids, plus 1,000,000.
    5. Set `write_mode` to `pg_primary`. Wait until every instance shows it.
  - State: the Postgres sequence and the flag.
  - If it fails: if not every instance shows `pg_primary` within 75 seconds of substep 1, set `write_mode` back to `dual`. MySQL is complete, so nothing is lost.
  - After this step, new ids come from the Postgres sequence. Copies to MySQL keep the ids they were given.

- [ ] **8. Keep MySQL in sync for 14 days.**
  - Starts: step 7 is done. This runs with `write_mode` at `pg_primary` for at least 14 days.
  - Does: each create, update or erase commits in Postgres, with its pending row in the same transaction. Then the copy rule runs in MySQL, in the same request. On success, the pending row is deleted. An operator starts the comparer in the Postgres-to-MySQL direction, as in step 5. It must stay clean.
  - State: Postgres is the source. Pending rows in Postgres show what MySQL lacks.
  - If it fails:
    - Postgres fails: the request fails with a retryable 503. Postgres is now the source, so the write cannot be saved anywhere else. The "never fail the request" rule applies only before step 7.
    - The MySQL copy fails: the request still succeeds. The sweep retries it.

- [ ] **9. Switch to `pg_only`.**
  - Starts: at least 14 days after step 7, a clean comparison in both directions, and a manual flag change.
  - Does: set `write_mode` to `pg_only`. Wait until every instance shows it. Writes stop reaching MySQL.
  - State: the flag.
  - If it fails partway: instances that still copy to MySQL do no harm. Once this step starts, do not roll back.

- [ ] **10. Drop the MySQL table.**
  - Starts: every instance shows `pg_only`.
  - Does: back up the MySQL `users` table, check its row count against Postgres, then drop it.
  - State: a backup of the MySQL table. The live table is removed.
  - If the backup or the check fails: do not drop.

## Roll back to MySQL

Use this only before step 9 starts. Its pause must stay under 90 seconds.

- [ ] **R-1. Decide to roll back.**
  - Starts: a manual decision.
  - Does, in order:
    1. Set `write_mode` to `paused`. Wait until every instance shows it.
    2. Run the sweep and wait until pending is empty in Postgres. This copies every Postgres-only write into MySQL, with its id.
    3. Set MySQL `AUTO_INCREMENT` to the larger of the two tables' max ids, plus 1,000,000.
    4. Set `write_mode` to `dual`. Wait until every instance shows it.
    5. Clear the time in migration state. Reads stay on Postgres, which holds every write. If reads misbehave, set `read_from_pg` to 0.
  - State: the flag and MySQL `AUTO_INCREMENT`. No write is lost, because the sweep in substep 2 copies every Postgres-only write first.
  - If it fails: if not every instance shows `dual` within 75 seconds of substep 1, set `write_mode` to `pg_primary`. Postgres still has every write.

## Open questions

- Which scheduler runs the sweep every minute? The existing docs list none.
- How long does the longest write take? Step 7 substep 2 assumes 10 seconds.
- Can step 7 fit under 90 seconds? It includes a 10-second wait, a sweep run and two 30-second flag refreshes. Measure it in a rehearsal.
- How long does one full comparison take over about 38 million rows? This sets how long step 5 takes.
- A copy can hit a unique email clash. The plan only retries, which may never clear.
- A backfill copy that starts before an erase commits can insert the row again in Postgres, if the erase's Postgres copy also fails. The sweep removes it within about a minute. The brief says an erased user must never reappear, so decide whether to accept this or add a check.
- Who changes `users.write_mode`, and with which tool? The flags doc names no admin tool.
- Does the product accept stale reads for up to about one minute during step 6, including a user's own change?