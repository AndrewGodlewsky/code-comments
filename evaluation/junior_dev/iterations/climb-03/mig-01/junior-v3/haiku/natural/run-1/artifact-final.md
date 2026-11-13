# Move `users` from MySQL 8 to Postgres 16 without downtime

## What this is

MySQL stays the source of truth until the switch in step 9. Every write commits to MySQL and leaves an outbox row there in the same transaction. The request then tries to copy the row to Postgres, and a sweeper retries any copy that failed. Background workers backfill old rows, compare the two tables, repair gaps and handle erasure. Reads move to Postgres in steps 7 and 8. Writes move once, in step 9, and that switch can be reversed until step 11.

Phases:
- **Phase A**: MySQL owns writes.
- **Phase B**: Postgres owns writes, and a reverse copy keeps MySQL current.
- **Phase C**: Postgres-only writes. No rollback.

## Terms

- **Owner**: the `owner` column of `users_control`, one row in each database. Values are `mysql`, `paused` or `pg`. `mode` is `pg_reverse` (phase B), `pg_only` (phase C) or empty (phase A).
- **Fence**: the first statement of every write is `SELECT owner, mode FROM users_control FOR SHARE` in MySQL, held until the transaction commits. Routing reads these rows, not a flag, because flags can be up to 30 seconds stale.
- **`users.write_owner` flag**: used only when MySQL cannot be reached. It is `mysql` until the step 9 commit point, then `pg`, and back to `mysql` at the rollback commit point.
- **Version**: `users.version`. It starts at 1 and goes up by 1 on every update, in whichever database takes the write.
- **Outbox**: `user_sync_outbox(user_id, version, queued_at)`. It holds one row per user whose copy in the other database may be stale. It is written in the same transaction as the change. `queued_at` is set on first insert and kept on later updates, so the oldest one gives the age. A row is deleted only after a copy succeeds. The outbox is in MySQL during phase A and in Postgres during phase B.
- **Copy**: any write into the non-owning database. This covers the inline apply, sweeper, backfill, repair and reverse copy. Every copy takes the per-id lock, checks for a tombstone, and follows the version rule.
- **Version rule**: a copy inserts a missing row, or replaces an existing row only if that row's version is lower than the incoming one. An equal or higher version is never replaced.
- **Per-id lock**: in Postgres, `pg_advisory_xact_lock(ns, id)`. In MySQL, `SELECT ... FOR SHARE` on the id's row in `user_tombstones`, which locks the gap even when no tombstone exists.
- **Tombstone**: a `user_tombstones` row for an erased id, in each database. It blocks every copy into that database.
- **Lease**: a Postgres session lock, `pg_try_advisory_lock(ns, task number)`, held on a dedicated connection by one worker per background task. A crash releases it, so another worker can take over.
- **Ids**: never reused. MySQL AUTO_INCREMENT is persistent, and the Postgres sequence only moves forward.

Rules that always hold:
- From step 1 on, every build that writes `users` includes the outbox and the fence. Never roll back below the Phase 0 build once the backfill has started.
- Repair and comparison re-check every suspected mismatch against the primary of the source database. A replica is never the authority for a repair.
- Email matching follows MySQL's case-insensitive collation. Step 0 chooses a unique index on `lower(email)` or `citext` for Postgres, and the comparison uses the same rule.
- Timestamps are UTC. `DATETIME(3)` maps to `timestamp(3) without time zone`, and comparisons use UTC milliseconds.
- Extend the `no-raw-users-sql` lint rule to cover `user_*` tables and the control tables.
- Alerts: outbox depth and age, compare mismatches, Postgres read errors and fallbacks, and `mysql_replica_lag_seconds`.

Where the code runs: the steps of a write run inside the web request, in `UserRepository`, on every app instance. Sweepers, backfill, compare runs, erasure retries, and the switch and rollback jobs run in worker processes. `app.jobs` only wakes a worker early. Workers find their work in the databases, so a lost job delays work but does not lose it.

## How a write works

**Phase A write** (inside the web request, on every instance):
1. Open a MySQL transaction and run the fence read. If `owner` is `pg`, roll back and take the phase B path. If it is `paused`, roll back and return 503.
2. Insert or update `users`, then read the row back in the same transaction. That row, with its version, is the copy to apply.
3. Upsert the outbox row with that version, then commit.
4. If `users.dual_write` is on for this user, try to copy the row to Postgres and wait at most 200 ms. On success, delete the outbox row only if its version is at most the copied version. On failure or timeout, leave the outbox row for the sweeper. The copy is not cancelled at 200 ms.
5. Respond. Step 4 never fails the request.

Step 4 runs after the fence lock is released, and that is safe. It copies only committed rows, and the version rule rejects stale copies. The outbox row stays until a copy succeeds, so the drain in step 9 waits for any copy still in flight. A late copy is harmless: an equal version is not replaced, and the outbox delete removes only entries at or below its own version.

**Phase B write:** the routing read sends the write here. The write runs the fence read in Postgres, writes `users` in Postgres, and upserts the reverse outbox row in the same Postgres transaction when `mode` is `pg_reverse`. There is no inline apply.

**Erasure:** the erasure request writes a `user_erasures` row with status `pending` in the source database. A worker retries pending rows until they are done. Each attempt has two steps:
1. **Target database**: write the tombstone, then delete any copy of the user. Both are idempotent. If this fails, the source is unchanged.
2. **Source database, one transaction through the fence**: delete the `users` row and its outbox row, and set the erasure to `done`. If this fails, the transaction rolls back and the next attempt repeats step 1. A 503 means retry later.

The tombstone blocks any copy that races the erasure. A sweeper that finds no source row checks the target for a tombstone. If one exists, it deletes the outbox row. If not, it alerts and keeps the row. In phase B the roles swap: the target is MySQL and the source is Postgres.

## Steps

- [ ] **0. Create schemas and control rows.**
  - Starts: the plan is approved and the email rule is chosen.
  - Changes: Postgres gets `users` (identity `GENERATED BY DEFAULT`, UTC `timestamp(3)`, the email rule), `user_tombstones`, `user_erasures`, an empty reverse `user_sync_outbox`, and `users_control` with `owner=mysql`. MySQL gets `users_control` (`owner=mysql`), `user_sync_outbox`, `user_erasures`, `user_tombstones` and `migration_state`. Both outboxes have `queued_at`.
  - State: the DDL and the control rows.
  - If it fails: drop the new objects. Behaviour has not changed.

- [ ] **1. Deploy the Phase 0 build to every instance.**
  - Starts: step 0 is done and the deploy pipeline runs.
  - Changes: writes use the fence and the outbox (always on). The inline apply stays off while `users.dual_write` is 0. Reads stay on MySQL. The phase B path ships but is unused, because `owner=mysql`.
  - State: the control rows, the outbox, and the flag `users.dual_write` (0).
  - If it fails: roll back to the previous build only if no instance has written `users` with the new build. Otherwise roll forward.

- [ ] **2. Start the forward sweeper, with dual write still off.**
  - Starts: step 1 is on every instance.
  - Changes: the forward sweeper takes its lease and works in batches of up to 500 outbox rows, oldest `queued_at` first. For each batch it reads the current rows from the MySQL primary, copies them under the version rule, and deletes each outbox row whose `version` is at most the copied version. With dual write off it does all the copying, so it must keep up with peak writes (about 400 per second).
  - State: the lease, and the outbox depth and age metrics.
  - If it fails: the outbox grows with no user impact. Fix the sweeper before continuing.

- [ ] **3. Turn on dual write.**
  - Starts: step 2 is healthy and outbox depth is near zero.
  - Changes: the flag `users.dual_write` goes from 0 to 100. It is a percentage bucketed by user id (for a create, the new id), so 100 means every write tries the inline apply.
  - State: the flag.
  - If it fails: set the flag back to 0. Outbox rows keep arriving, so nothing is lost.

- [ ] **4. Backfill gate (automatic).**
  - Starts: the backfill job checks the gate every 30 seconds. No person opens it.
  - Opens when all of these hold for two continuous minutes: every instance reports the Phase 0 build and `app_flag_value{flag="users.dual_write"}` = 100; outbox depth is below 1,000 and its oldest entry is under 60 s old; Postgres is healthy.
  - State: `migration_state.backfill_gate_at`, set when the conditions have held for two minutes.
  - If it fails: the gate stays closed and an alert fires. Nothing else changes.

- [ ] **5. Backfill.**
  - Starts: the gate is open. The backfill task takes its lease.
  - Changes, per batch:
    1. If replica lag (`SHOW REPLICA STATUS`) is above 5 s, sleep 5 s and check again.
    2. Read up to 2,000 rows from the replica: `WHERE id > last ORDER BY id LIMIT 2000`.
    3. Copy them in one Postgres transaction, taking the id locks in id order, with tombstone checks and the version rule.
    4. Commit, then set `migration_state.last_completed_id` to the batch's largest id.
  - An empty batch means the backfill is done. A replica row may be older than the primary. The version rule and the outbox make that harmless, and repair fixes anything missing.
  - State: `migration_state` in MySQL, holding the checkpoint and counters.
  - If it fails: when a worker dies, its lease is released and the next worker resumes after `last_completed_id`. A repeated batch is safe because copies are idempotent. If Postgres is down, the batch retries with backoff. Users are unaffected.

- [ ] **6. Full comparison and repair, repeated until clean.**
  - Starts: the backfill is done.
  - Changes: compare the tables in id chunks of 2,000 ids, reading the replica and Postgres and pausing on replica lag as in step 5. Classify each difference: missing in Postgres, lower version in Postgres, higher version in Postgres (alert, should never happen), field difference, or extra in Postgres. Re-check each candidate against the MySQL primary and the outbox. A confirmed missing or lower-version row is repaired by inserting an outbox row, so the sweeper copies it. Other classes are investigated, not repaired automatically. Ids with a tombstone do not count. A run is clean when it has zero confirmed mismatches. Clean runs continue daily through steps 7 and 8 as a guard.
  - State: compare-run records in `migration_state`, with start time and counts.
  - If it fails: users are unaffected. Investigate, then run again.

- [ ] **7. Move reads to Postgres in steps.**
  - Starts: a clean compare run.
  - Changes: the flag `users.read_source` goes 1, 10, 50, 100 percent, keyed by user id. A read tries Postgres first. If Postgres errors or the row is missing, it reads the MySQL replica, so reads never fail. The read path counts Postgres errors and fallbacks. Each step waits until every instance reports the value and 30 minutes pass with no new Postgres read errors and no confirmed mismatch from the compare run. A person checks the dashboards and sets the next value.
  - State: the flag, and `migration_state.reads_pg_since` once every instance reports 100.
  - If it fails: set the flag to 0. Writes are unaffected, and the clock resets.

- [ ] **8. Soak reads at 100% on Postgres for at least 3 days.**
  - Starts: `reads_pg_since` is recorded.
  - Changes: none. The daily compare continues.
  - Trade-off: a read can return an older row while that user's repair is still in the outbox. The window is bounded by the outbox-age alert, which should be a few seconds.
  - State: `reads_pg_since`.
  - If it fails: any read rollback resets `reads_pg_since`, and the 3-day soak starts again.

- [ ] **9. Switch writes to Postgres (phase B), with a pause of at most 90 s.**
  - Starts: the switch job runs only when all of these hold: `reads_pg_since` is at least 3 days old; a clean compare run finished within the last 24 hours; outbox depth is below 100; there are no pending erasures; Postgres is healthy.
  - Changes, in order:
    1. **Pre-drain**: the forward sweeper empties the outbox while writes still use MySQL.
    2. **Pause in MySQL**: `UPDATE users_control SET owner='paused' WHERE owner='mysql'`, with `lock_wait_timeout` of 5 s. This waits for in-flight writes. New writes get a 503.
    3. **Drain and check**: with writes paused, the sweeper empties the outbox. Then run a delta check of rows with `updated_at` at or after the last clean run's start. Zero mismatches are required.
    4. **Commit point, in Postgres**: set the sequence to MySQL `MAX(id)` + 10,000,000, set `users_control` to `owner='pg', mode='pg_reverse'`, and set the flag `users.write_owner` to `pg`. Before this point, abort by setting MySQL `owner='mysql'`.
    5. **Finish in MySQL**: set `owner='pg'`. Writes resume on the phase B path. Start the reverse sweeper and stop the forward sweeper. Record `migration_state.pg_owner_since`.
  - Resume rule: after the commit point the job always completes step 5. If it dies, the next run takes the lease, sees Postgres `owner='pg'` while MySQL is not `pg`, and finishes step 5. Every part is idempotent.
  - Budget: abort at 80 s if steps 2 to 4 have not finished. After the commit point, step 5 is one UPDATE, retried until it succeeds.
  - Ids: from this point Postgres assigns ids from its sequence. The MySQL counter moves only when reverse copies insert ids.
  - State: both control rows, `pg_owner_since`, and the flag `users.write_owner`.
  - If it fails before step 4: restore MySQL to `owner='mysql'`. Nothing changes. After step 4, while MySQL is unreachable, writes take the phase B path through the `users.write_owner` flag. When MySQL is reachable again, the resume rule sets its row to `pg`. Writes never run on both paths at once: a write takes the MySQL path only if MySQL says `mysql`, and takes the Postgres path only if MySQL says `pg` or cannot be reached while the flag is `pg`.

- [ ] **10. Phase B soak, at least 14 days.**
  - Starts: step 9 is committed and `pg_owner_since` is recorded.
  - Changes: writes take the phase B path. Reads stay on Postgres. The reverse sweeper copies each reverse outbox row to MySQL under the version rule and tombstone check, then deletes the outbox row. The forward sweeper, the inline apply and `users.dual_write` are no longer used. Erasure runs with the roles swapped.
  - State: the reverse outbox in Postgres, and the copy in MySQL.
  - If it fails: if MySQL is down, the reverse outbox grows in Postgres and writes continue. A read that falls back to the MySQL replica may be stale, because the replica lags the reverse outbox. A rollback waits until the outbox has drained.

- [ ] **Rollback (available any time before step 11).**
  - Starts: a decision to roll back.
  - Changes, in order:
    1. Set `users.read_source` to 0, so reads go back to MySQL.
    2. Pre-drain: the reverse sweeper empties the reverse outbox into MySQL.
    3. **Pause in Postgres**: set `owner='paused'` under an exclusive lock. This waits for in-flight Postgres writes. New writes get a 503.
    4. Drain the reverse outbox. Run the delta check against the MySQL primary. Zero mismatches are required.
    5. Check that the MySQL AUTO_INCREMENT is above `MAX(id)`. If it is not, set it. In MySQL 8 this is a metadata-only change.
    6. **Commit point, in MySQL**: set `owner='mysql'`, then set `users.write_owner` to `mysql`. Writes resume on the phase A path. Then set Postgres `owner='mysql'` and clear `mode`.
    7. Stop the reverse sweeper and start the forward sweeper. Make sure `users.dual_write` is 100.
  - Budget: 90 s. Abort before step 6 by setting Postgres back to `owner='pg'`. Nothing is lost, because the reverse outbox is durable.
  - Resume rule: after step 6 the job always completes the Postgres update and step 7, even if it died in between.
  - State: both control rows.
  - If it fails: before step 6, abort as above. After step 6, the resume rule finishes the rollback.

- [ ] **11. Postgres-only writes (phase C).**
  - Starts: at least 14 days after `pg_owner_since`, no rollback planned, and the reverse outbox is empty.
  - Changes: set the Postgres `users_control.mode` to `pg_only` under an exclusive lock. This waits briefly for writers and produces no 503. Writers stop writing the reverse outbox, and the reverse sweeper stops. MySQL is now frozen, and rollback is no longer possible.
  - State: `users_control.mode`.
  - If it fails: if the lock wait times out, the system stays in phase B and nothing else changes.

- [ ] **12. Retire the MySQL table.**
  - Starts: phase C has been stable for the period the team chooses.
  - Changes: take a final MySQL snapshot and verify it. Revoke the app's MySQL access to `users`. Drop the table only after the backup is verified.
  - State: the snapshot and its verification record.
  - If it fails: keep the table. Dropping is gated on the verified backup.

## Open questions

- How long do clients keep retrying a 503? The 90 s pause is invisible to users only if clients retry at least that long. The files do not say.
- After phase C, MySQL is frozen. If Postgres errors, the read fallback returns the frozen MySQL copy, which can be stale. Decide before step 11: accept stale fallback reads, or fail those reads.
- What starts an erasure request, and who writes its `pending` row? The files do not say.
- The two-key advisory lock needs ids that fit in 32 bits. The sequence starts near 51.2M, which fits. If ids grow past 2^31, use the single bigint key form.
- Measure the real drain time in staging before step 9, to confirm the 80 s abort point and whether one sweeper task keeps up with 400 writes per second.
- Confirm the outbox-age alert threshold (a few seconds).
- Choose the backup retention period before the MySQL table is dropped.
- How does each instance report its build version to the gate check in step 4? The files do not say.