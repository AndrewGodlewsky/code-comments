# Move `users` from MySQL to Postgres

We are moving the `users` table from MySQL 8 to the new Postgres 16 cluster without taking the service down. Read `existing/user_repository.py`, `existing/users_table.md` and `existing/flags_and_jobs.md` first. Every read and write of `users` already goes through `UserRepository`, so the migration logic goes there.

Fixed requirements:

- **Dual writes.** MySQL stays the source of truth until we deliberately switch. Until then, every write commits to MySQL first and is then applied to Postgres. A Postgres failure must never fail the user's request. Whatever Postgres missed must be fixed automatically, with no manual step.
- **Version rule.** Any copy into Postgres (dual write, backfill or repair) may only insert a missing row or replace a row whose `version` is lower than the incoming one.
- **Deletes.** A user removed by the erasure job must never reappear in Postgres.
- **Backfill.** It may only start once every app instance is dual-writing. It reads from the MySQL replica in primary-key order, at most 2,000 rows per batch, and pauses whenever replica lag is above 5 seconds (reporting jobs share that replica). After a crash it must continue after the last completed batch, not start over.
- **Reads before writes.** Reads move to Postgres only after a full comparison of the two tables finds zero mismatches. The source of truth moves to Postgres only after reads have been 100% on Postgres for at least 3 days.
- **Availability.** Reads must never fail during the migration. Writes may be paused for at most 90 seconds each time the source of truth changes (the planned switch, or a rollback). During a pause, write requests get a retryable 503, which our clients already retry.
- **Rollback.** Until we switch to Postgres-only writes, we must be able to go back to MySQL without losing any write. Make that switch no sooner than 14 days after Postgres becomes the source of truth; the MySQL table is dropped only after it.

You decide how repair works, how the switch is coordinated across instances, where backfill progress is kept and how new ids are assigned after the switch.

**Format:** a Markdown checklist of steps, in the order they are done. For each step, say what starts it (a deploy, a flag change, a condition being met), what it changes or moves, where any state lives, and what happens if it fails.
