# Move `users` from MySQL to Postgres: migration plan

## Shared mechanisms (used by the steps below)

- **Write fence.** A control row `users_pg_control` (fields `mode` and `epoch`) lives in MySQL. Modes are `mysql`, `paused`, `pg` and `pg_only`. Every instance polls the primary every 2 s and holds a lease that lasts 10 s from its last successful poll. A write starts only if the lease is valid, the mode allows writes, and at least 3 s of lease remain. Each write has a 3 s deadline. So 12 s after `paused` is set, no write can still be in flight. This does not depend on the 30 s flag cache. A write that is not allowed returns a retryable 503.
- **Per-user lock.** Copies, repairs, backfill rows and erasure steps take a per-user lock: `GET_LOCK('users:<id>')` in MySQL, `pg_advisory_xact_lock(id)` in Postgres. Under the lock, a copy checks the tombstone first and then applies the version rule.
- **Version rule (`copy(row)`).** Insert if the id is missing. Otherwise update only if `existing.version < incoming.version`. Otherwise do nothing. A unique-email conflict caused by out-of-order copies is retried, not treated as permanent.
- **Tombstones.** `users_tombstones(id, erased_at)` exists in both stores. Rows are never removed. Any copy into a store is skipped when a tombstone exists for that id.
- **Forward outbox (MySQL, `users_pg_outbox`).** A row is inserted in the same MySQL transaction as each user write. A worker copies the current primary row to Postgres, then deletes that user's outbox rows with seq up to the one it read. It never drops a row. This is the repair mechanism. It does not use the job queue, because `jobs:dead` has no processor and `enqueue` can raise when Redis is down.
- **Reverse outbox (Postgres, `pg_outbox`).** Used after the source switch. The same rules apply in the other direction, with MySQL as the target.

## Steps, in order

- [ ] **1. Add the schema. No behavior change.**
  - Starts: the normal migration deploy.
  - Does: MySQL gets `users_pg_outbox`, `users_tombstones` and `users_pg_control` (mode `mysql`, epoch 1). Postgres gets `users` (same columns; `id` BIGINT primary key; unique `email`), `user_tombstones`, `pg_outbox`, and `migration_state` (backfill checkpoint, backfill lease, compare results, timestamps).
  - State: MySQL and Postgres.
  - If it fails: the tables are additive and unused. Drop them and redeploy.

- [ ] **2. Deploy the code with every switch off.**
  - Starts: deploy of the build that contains the fence, the outbox writes (behind a flag), the repair worker, the read path with fallback, the backfill runner and the compare job.
  - Does: flags `users.dual_write`=off, `users.backfill`=off and `users.pg_read_percent`=0. Every instance polls the control row and reports `users_mode_applied` and its build version. The repair worker runs but has nothing to do while dual writes are off. All new SQL on `users` lives in `UserRepository` or a module the lint rule explicitly allows. Do not widen `no-raw-users-sql` silently.
  - State: flags and the MySQL control row.
  - If it fails: roll back the deploy. Nothing has changed, because dual writes are off.

- [ ] **3. Erasure ordering (active from step 2 onward).**
  - Starts: each erasure request.
  - Does, in this order: (a) under the per-user lock, insert the Postgres tombstone and delete the Postgres row, and commit; (b) in MySQL, in one transaction, insert the MySQL tombstone, delete the row and write an outbox row. Step (b) never starts before step (a) commits. Erasure writes go through the fence and get a 503 during a pause, so the sweeper retries them.
  - Why it holds: every copy checks the tombstone under the same lock. A backfill or dual-write copy that read the row before the delete finds the tombstone and skips it. A copy that starts after the delete also finds the tombstone.
  - State: the durable erasure work list lives in MySQL. A sweeper drives it until done. The job queue is not relied on, because its dead letters are never processed.
  - If it fails: the sweeper retries. If Postgres is down during dual-write mode, erasure waits and an alert fires. No user request is delayed.

- [ ] **4. Turn on dual writes.**
  - Starts: an operator sets `users.dual_write`=on. This is allowed only after step 2 is live on every instance. Verify that every instance reports `app_flag_value{flag="users.dual_write"}`=on, then wait at least 60 s.
  - Does: `create`, `update` and `delete` commit in MySQL with their outbox row. Then one Postgres copy is attempted with a 200 ms timeout. Any failure or timeout is logged and counted, and is never raised to the caller. The copy reads the current primary row after commit, so it carries the source's values, including `updated_at`.
  - State: the MySQL outbox and Postgres.
  - If it fails: a Postgres failure does not fail the request, and the outbox keeps the row. If the flag is turned off again, writes made in the gap are not in the outbox. Before reads move, a full compare (step 6) is then required.

- [ ] **5. Backfill.**
  - Starts: an operator sets `users.backfill`=on. This is allowed only after step 4 has been on everywhere for at least 60 s and the outbox age is under 5 min.
  - Does: one runner holds a lease row in Postgres. It reads from the replica with `WHERE id > last ORDER BY id LIMIT 2000`. Before each batch it checks `mysql_replica_lag_seconds`. If lag is above 5 s, it waits and rechecks every 5 s. For each row, under the per-user lock, it applies the copy rule with the tombstone check. In the same Postgres transaction as the batch, it updates `migration_state.backfill_last_id`, so the rows and the checkpoint commit together. The backfill is done when a batch returns 0 rows. That is about 19,000 batches.
  - Why it is safe: the outbox covers writes made after the replica read, and the version rule stops a lagging replica copy from overwriting newer data.
  - State: the Postgres checkpoint and lease.
  - If it fails: a Postgres error rolls back the batch and retries with backoff. Replica errors or lag pause the run. After a crash, the next runner resumes from the last committed checkpoint. The interrupted batch was rolled back, and replays are safe because of the copy rule.

- [ ] **6. Full comparison and repair. No read moves until this passes.**
  - Starts: step 5 is complete.
  - Does: walk ids in order on both sides (replica and Postgres) in chunks of 2,000 ids. Compare a hash of `(id, version, email, name, plan, updated_at)` per chunk, skipping tombstoned ids. Any chunk that differs is rechecked row by row against both primaries under the per-user lock, and repaired with the copy rule. The pass succeeds only if the outbox is empty at its start and end and the recheck finds no mismatch. The pass also pauses on replica lag.
  - State: `migration_state` records the pass start, end and mismatch count.
  - If it fails: repair the mismatches and run the pass again. Do not move reads until a clean pass has finished. If clean passes keep failing, stop and investigate the cause.

- [ ] **7. Move reads to Postgres in steps.**
  - Starts: an operator raises `users.pg_read_percent` after step 6 passes. The steps are 1, 10, 50 and 100. Hold at each step while sampled comparisons and error rates are watched.
  - Does: `flags.enabled_for('users.pg_read_percent', user_id)` picks the users who read from the Postgres primary. Everyone else stays on the replica. A Postgres error, timeout or missing row falls back to the MySQL replica, so reads never fail.
  - State: the flag only. No data moves.
  - If it fails: set the percentage to 0. That takes effect within 30 s. Clients see no errors, because the fallback handles them. During outbox lag, which is normally seconds, a read can return an older version. Outbox age is the metric for that lag.
  - Stop rule: any sampled mismatch stops the ramp and returns the process to step 6.

- [ ] **8. Hold reads at 100% on Postgres for at least 3 days.**
  - Starts: 100% is reached.
  - Does: `migration_state.reads_100_since` is set. If the percentage drops below 100, or sampling finds a mismatch, the timestamp is cleared and the clock restarts. Step 9 is blocked until at least 72 h have passed on this clock.
  - State: Postgres `migration_state`.

- [ ] **9. Planned switch: Postgres becomes the source of truth (writes paused for at most 90 s).**
  - Starts: an operator or automation starts it, only when all of these hold: step 8 shows at least 72 h; the latest full compare was clean; outbox age is under 5 min and depth is small; every instance reports the fenced build; and the reverse worker is healthy.
  - Does:
    1. Set the control row to `paused` (epoch+1). Writes now get a 503. Wait 12 s. No write is in flight after that.
    2. Drain the forward outbox to zero. Writes are paused, so this terminates. Verify the outbox is empty.
    3. Set the Postgres id sequence to MySQL's `AUTO_INCREMENT` plus 1,000,000. MySQL assigns no new ids after this point, so the ids stay unique and increasing.
    4. Set the mode to `pg` (epoch+2). Writes now go to Postgres. Each write takes the per-user lock, checks the version, writes the row and writes a reverse-outbox row, all in one commit. Each instance applies the change within about 2 s.
    5. Record `source_switched_at` in Postgres.
  - Pause budget: target about 30 s. Abort at 75 s.
  - Reads: not affected. Postgres already holds every row.
  - If it fails: a failed control write changes nothing. If the drain is still running at 60 s, set `mysql` (epoch+3) and resume. The source is still MySQL, so nothing is lost. If instances cannot apply `pg` by 75 s, use the rollback procedure in step 11, not a plain flip. Once `pg` has been set, Postgres may hold newer writes.

- [ ] **10. Reverse sync (from step 9 until step 12).**
  - Starts: step 9 is complete.
  - Does: writes go to Postgres first. The reverse worker copies each changed row to MySQL under the per-user lock, with the MySQL tombstone check and the copy rule, then deletes the reverse-outbox rows. Reads come from Postgres only. The MySQL replica is no longer read, except as a counted, stale fallback.
  - ID assignment: Postgres assigns ids from the sequence set in step 9. MySQL assigns none. Reverse copies insert explicit ids, which moves MySQL's counter forward.
  - Monitoring: reverse-outbox depth and age, and a daily sampled compare of the two stores.
  - If it fails: if MySQL is down, the reverse outbox grows with no user impact, and rollback stays possible once it drains. If Postgres is down, writes return 503. This is the only point where a Postgres failure fails writes, and it happens only after the switch.

- [ ] **11. Rollback to MySQL (available until step 12). Same pause, drain and flip as step 9, in reverse.**
  - Starts: an operator decision.
  - Does: (1) set `paused` (epoch+1) and wait 12 s. (2) Drain the reverse outbox to zero and verify that every Postgres row has a MySQL row at the same version. (3) Set MySQL's `AUTO_INCREMENT` to max(id)+1, so MySQL assigns no id that collides with one assigned in Postgres. (4) Set the mode to `mysql` (epoch+2). Dual writes from step 4 resume. The Postgres copies are no-ops, because the rows are equal.
  - Pause budget: at most 90 s. Abort at 75 s by setting `pg` again (epoch+3). No write is lost, because writes went to Postgres and the reverse outbox holds whatever MySQL has not yet received.
  - If it fails: follow the abort path above. Run a full compare before any new source switch.

- [ ] **12. Postgres-only writes (no sooner than 14 days after `source_switched_at` from step 9).**
  - Starts: an operator approves it. The 14-day gate has passed. A full reverse compare is clean. A snapshot of the MySQL table has been taken.
  - Does: set the mode to `pg_only`. This does not change the source of truth, so no write pause is needed. The reverse worker drains the reverse outbox to zero and then stops. MySQL is no longer written. Reads keep the MySQL fallback, counted as stale, until step 13.
  - Note: rolling back to MySQL is impossible after this step.
  - If it fails: nothing changes before the flip. After it, recovery comes from the snapshot, not from MySQL.

- [ ] **13. Drop the MySQL `users` table.**
  - Starts: step 12 is complete and a separate change request is approved after the snapshot is verified.
  - Does: remove the reverse worker, the forward outbox, the MySQL tombstone table and the MySQL read fallback. Remove the MySQL paths in `UserRepository` and update the lint rule. Then drop the table.
  - If it fails: there is no rollback to MySQL. Restore from the snapshot.
