# Move `users` from MySQL 8 to Postgres 16

## Names used below

- **Forward queue**: table `users_sync_queue` in MySQL (`user_id` PK, `queued_at DATETIME(3)`). Used while MySQL is the source.
- **Reverse queue**: table `users_sync_queue` in Postgres, same shape. Used while Postgres is the source.
- **Tombstones**: table `user_tombstones` (`user_id` PK, `deleted_at`) in each database. Written whenever a user is removed from that database. Every copy checks it.
- **Copy rule**: a copy into the non-source database runs under a per-id lock (`pg_advisory_xact_lock(id)` in Postgres, `GET_LOCK('users:<id>')` in MySQL), taken in ascending id order. Under the lock it checks the tombstone, then inserts the row if it is missing or replaces it only when the stored `version` is lower than the incoming one. In Postgres this is `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. In MySQL it is a conditional `UPDATE ... WHERE version < new`, then an `INSERT` if no row exists. A unique-email conflict rolls the copy back and leaves the id queued for a later retry. It never skips the row.
- **Id generator**: MySQL `AUTO_INCREMENT` while MySQL is the source, a Postgres sequence once Postgres is the source.
- **Source flag** `users_source`, read by every instance from `app.flags`: `mysql` (MySQL is the source, forward dual write), `paused` (user writes get a retryable 503, reads continue), `pg` (Postgres is the source, every write also copied to MySQL through the reverse queue), `pg_only` (reverse copies stop).

## Phase 0: Prepare, no user-visible change

- [ ] **0.1 Create the Postgres schema.**
  - Starts: a reviewed migration, run by hand.
  - Changes: in `pg-core`, creates `users` (`id BIGINT PRIMARY KEY` with no default, `email VARCHAR(320) UNIQUE`, `name VARCHAR(200)`, `plan VARCHAR(20)`, `version INT NOT NULL`, `updated_at TIMESTAMP(3)` stored as UTC), `user_tombstones`, `users_sync_queue` and `migration_state`. The session time zone is UTC.
  - State: `pg-core`.
  - On failure: nothing is live yet. Fix and rerun; every statement uses `IF NOT EXISTS`.

- [ ] **0.2 Create the MySQL queue and tombstone tables.**
  - Starts: a schema migration on `core`.
  - Changes: creates `users_sync_queue` and `user_tombstones` in `core`. No code uses them yet.
  - State: `mysql-core-primary`.
  - On failure: same as 0.1.

- [ ] **0.3 Deploy the code with every flag off.**
  - Starts: the normal deploy of web instances and worker processes.
  - Changes: `UserRepository` gains the dual-write, copy, read-fallback and source-switch paths. They are gated by `users_dual_write` (off), `users_read_source` (percentage, 0), and `users_source` (`mysql`). The worker process gains the sweeper, the backfill worker and the comparison job, each holding a lease in `migration_state`. The lint rule `no-raw-users-sql` allows only the repository and the migration module. New metrics: `users_read_total{source}`, queue depth, oldest queued age, in-flight writes.
  - State: the code, plus `app.flags`.
  - On failure: roll back the deploy. With the flags off, the new paths do nothing.

## Phase 1: Dual writes, MySQL is the source

- [ ] **1.1 Turn on dual write on every instance.**
  - Starts: a flag change, `users_dual_write = on`.
  - Gate: every instance in the deploy reports `app_flag_value{flag="users_dual_write"}=on`. An instance that does not report the metric counts as not converged. Then wait 60 s, which covers the 30 s cache and a margin.
  - Changes, per write: inside the same MySQL transaction as the `INSERT`, `UPDATE` or `DELETE` on `users`, the instance upserts a forward-queue row (`ON DUPLICATE KEY UPDATE queued_at = NOW(3)`). After commit it applies the row image (for a delete, a tombstone plus a delete) to Postgres under the copy rule, with a 500 ms timeout. On success it removes its queue row with a compare-and-delete (`WHERE user_id = ? AND queued_at = ?`).
  - State: the forward queue in MySQL is the durable record of pending work.
  - On failure: a Postgres error or timeout never changes the response to the user. The row stays queued and the sweeper in 1.2 handles it. A MySQL error on the queue insert fails the write, as it does today.

- [ ] **1.2 Run the repair sweeper.**
  - Starts: the worker's scheduled loop, which runs continuously once 1.1 is on.
  - Changes: reads queue rows ordered by `queued_at`, 500 at a time, from the MySQL primary. For each id it reads the current row from MySQL. If the row exists, it applies the copy rule. If the row is absent, it writes a Postgres tombstone and deletes the Postgres row under the lock. It then compare-and-deletes the queue row. Retries back off exponentially with no retry cap.
  - State: the queue in MySQL. The sweeper holds a lease in `migration_state` in Postgres, so only one sweeper runs at a time.
  - On failure: queue rows stay in MySQL. A restarted sweeper resumes from them. Alert when the oldest queued row is older than 5 min. Do not use `app.jobs` for repair: failed jobs go to `jobs:dead`, which nothing processes, and `enqueue` raises when Redis is unreachable.

## Phase 2: Backfill

- [ ] **2.1 Start the backfill worker.**
  - Starts: the backfill flag, `users_backfill = on`. It may start only after 1.1's gate has held for 60 s on every instance.
  - Changes: the worker takes the lease in `migration_state`, reads `backfill_last_id` (absent means 0), and processes batches from there.
  - State: `migration_state` in Postgres.
  - On failure: a crashed worker's lease expires after 60 s. Another worker resumes from the saved cursor.

- [ ] **2.2 Copy batches.**
  - Per batch: wait while `mysql_replica_lag_seconds > 5`, polling once per second. Then run `SELECT * FROM users WHERE id > :cursor ORDER BY id LIMIT 2000` on the replica. In one Postgres transaction, copy every row under the copy rule, in ascending id order, and set `migration_state.backfill_last_id` to the last id in the batch. Commit.
  - Ends when a batch returns no rows. Then set `backfill_status = done`.
  - State: the cursor is written in the same transaction as the copies, so the two cannot disagree.
  - On failure after a crash: the restarted worker continues after `backfill_last_id`. Redoing a batch is safe because the copy rule is idempotent. A batch that rolls back on an email conflict is retried after a sleep. Rows are never skipped. A conflict that persists raises an alert and stops the backfill.

## Phase 3: Verify

- [ ] **3.1 Run a full comparison pass.**
  - Starts: after 2.2 reports done. Also run after any later change to the source, read ramp or repair.
  - Changes: walks both tables in id ranges of 2,000. For each range it compares the row count and a hash of `(id, version, email, name, plan, updated_at)`, with `updated_at` at millisecond precision in UTC. For each mismatched range it re-reads every mismatched id from the MySQL primary and from Postgres. If a row changed between the two reads, it waits 2 s and re-checks, so in-flight writes are not counted. Confirmed mismatches are sent through the forward queue. A Postgres-only id with no MySQL tombstone counts as a mismatch.
  - Pass criterion: one full pass ends with zero confirmed mismatches. A pass that finds mismatches repairs them and does not count. The next pass must be clean.
  - State: pass id, progress cursor and mismatch count in `migration_state`.
  - On failure: the pass resumes from its cursor. Users are not affected.

## Phase 4: Move reads to Postgres

- [ ] **4.1 Ramp reads: 1%, 10%, 50%, 100%.**
  - Starts: a flag change to `users_read_source`, which is bucketed by user id with `flags.enabled_for`. Gate before the first step: a clean comparison from 3.1 within the last 24 h, and no forward queue row older than 5 min.
  - Changes: `UserRepository.get` tries Postgres with a 200 ms timeout. On an error, a timeout or a missing row, it falls back to the MySQL replica, so reads never fail. Each step holds at least 1 h and checks the error rate and the fallback rate.
  - State: `app.flags`, plus `users_read_total{source=pg|mysql_fallback}`.
  - On failure: set the flag to a lower percentage, or to 0. Reads return to MySQL at once. A fallback rate above 0.1% stops the ramp and triggers a comparison in 3.1.

- [ ] **4.2 Hold reads at 100% on Postgres for 3 days.**
  - Starts: `users_read_source = 100` on every instance, confirmed by the metric.
  - Gate: at least 72 h with no change below 100. During the hold, run 3.1 once more and require zero mismatches.
  - On failure: any change below 100 or any mismatch restarts the 72 h clock, and the ramp in 4.1 begins again from the step that failed.

## Phase 5: Switch the source of truth to Postgres

- [ ] **5.1 Check the gates.**
  - Preconditions: 4.2 is complete. The latest comparison pass has zero mismatches. The forward queue is empty. `mysql_replica_lag_seconds < 5`. Every instance reports `users_dual_write=on`.
  - On failure: no change is made. Wait.

- [ ] **5.2 Pause user writes.**
  - Starts: `users_source = paused`.
  - Changes: each instance returns 503 with `Retry-After: 2` for user writes. Reads keep running. The erasure job's deletes receive the same retryable error and retry through `app.jobs`. Its five attempts over about 15 min are far longer than the pause.
  - Gate: the metric shows `paused` on every instance. Each instance refreshes within 30 s. Then wait for in-flight writes to drain, with a cap of 5 s.
  - On failure: if not every instance shows `paused` within 45 s, set `users_source = mysql` and stop. Nothing was written to Postgres as the source, so this is safe.

- [ ] **5.3 Drain the queue and set the Postgres id generator.**
  - While paused: the sweeper drains the forward queue to zero, with a cap of 10 s. Then, in `pg-core`, set the users id sequence to `max(id)` across both databases plus 1,000,000. Read the MySQL maximum from the primary.
  - On failure: if the drain is not done within 10 s, or the sequence update fails, set `users_source = mysql` and abort. Nothing was committed as the Postgres source.

- [ ] **5.4 Make Postgres the source.**
  - Starts: `users_source = pg`.
  - Changes, per write: one Postgres transaction assigns the id from the sequence (or bumps `version` by 1 on update), writes the row, and writes a reverse-queue row in the same transaction. After commit it applies the row to MySQL under the copy rule, with a 500 ms timeout, and removes the reverse-queue row on success. The reverse sweeper runs with the same design as 1.2, with the roles swapped.
  - Gate: every instance reports `users_source=pg`. The pause ends at this point. Budget: about 30 s to show `paused`, up to 5 s to drain in-flight writes, up to 10 s to drain the queue, and up to 30 s to show `pg`. That is at most 75 s, inside the 90 s limit.
  - State: the reverse queue in Postgres.
  - On failure: this step cannot be aborted. Restart any instance still reporting `paused`. It re-reads flags on start. Record any pause over 90 s as a violation.

- [ ] **5.5 Hold in `pg` for at least 14 days.**
  - Rollback is possible throughout (Phase 6). Watch the reverse-queue age, the reverse copy error rate and the reverse comparison results.

## Phase 6: Roll back to MySQL

Available from 5.4 until 7.2. No write is lost, because every Postgres write is in MySQL before the rollback, or in the reverse queue, which is drained below.

- [ ] **6.1 Pause user writes.** Set `users_source = paused` and run the gate from 5.2. On failure, set `pg` again.
- [ ] **6.2 Drain the reverse queue and set the MySQL id generator.** Drain the reverse queue in Postgres to zero, with a cap of 10 s. Then set MySQL `AUTO_INCREMENT` on `users` to `max(id)` across both databases plus 1,000,000. On failure, set `users_source = pg` and abort. Nothing was lost.
- [ ] **6.3 Set `users_source = mysql`.** Forward dual writes resume. Reads stay on Postgres, which is current. Gate: every instance shows `mysql`. On failure, restart stragglers, as in 5.4.

## Phase 7: Postgres-only writes

- [ ] **7.1 Check the gate.** `users_source = pg` has held for at least 14 days. The reverse queue is empty. The latest reverse comparison has zero mismatches. Record the decision.
- [ ] **7.2 Stop reverse copies.** Set `users_source = pg_only`. No pause is needed, because the source of truth does not change. A lagging instance that still copies to MySQL is harmless. After this step, rollback to MySQL is no longer possible. If it is ever reversed, set `pg` again. MySQL then needs a full reverse comparison with zero mismatches before any rollback is safe.
- [ ] **7.3 Remove the dual-write code.** Remove the forward queue, the sweeper branch and the `users_source` branches. Run 3.1 one last time. Keep MySQL tombstones until the table is dropped.

## Phase 8: Drop the MySQL table

- [ ] **8.1 Drop `core.users`.**
  - Starts: a planned change, not before 7.2. The brief requires a further hold, which is a team choice. A 30-day hold is suggested.
  - Changes: take a logical dump of `users`, then `DROP TABLE users`.
  - State: the dump is stored outside the cluster.
  - On failure: restore from the dump. The drop cannot be undone without it.

## Known trade-offs

- Reads on Postgres can lag a write by the time the inline apply or the sweeper takes, typically under a second. A read-after-write check against the forward queue would cost a MySQL primary query on every read, so it is not in the design. Open decision.
- Postgres reads fall back to the MySQL replica on a miss. A miss is also a mismatch signal, so a rising fallback rate halts the ramp.
- The erasure job's deletes depend on `app.jobs` retries. Alert on any erasure entry in `jobs:dead`, because nothing else processes it.