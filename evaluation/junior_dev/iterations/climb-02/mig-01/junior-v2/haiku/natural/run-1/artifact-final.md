# Move `users` from MySQL 8 to Postgres 16

## Systems and names

- **MySQL primary** (`mysql-core-primary`): takes writes. The `users` table is in database `core`.
- **MySQL replica** (`mysql-core-replica`): serves reads and reporting jobs. Its lag is the metric `mysql_replica_lag_seconds`.
- **Postgres** (`pg-core`): Postgres 16 cluster, provisioned and empty. The app holds a pool to it (`app.db.postgres`).
- **Workers**: processes separate from the web instances. They run `app.jobs`, the sweepers, the backfill and the comparison job.
- **UserRepository**: the only code that touches `users`. Writes go to the MySQL primary and reads to the MySQL replica. From Phase 0 it also does the copies and the Postgres reads.
- **Erasure job**: a worker job that calls `UserRepository.delete`, about 2,000 deletes a day. Its deletes follow the source flag like every other write.
- **version**: maintained by UserRepository. An insert sets 1, an update adds 1. A delete removes the row and writes a tombstone.
- **Queues**: `users_sync_queue` in MySQL is the forward queue, used while MySQL is the source. The same table in Postgres is the reverse queue, used while Postgres is the source. Both have `user_id` (PK) and `queued_at DATETIME(3)`.
- **Tombstones**: `user_tombstones` (`user_id` PK, `deleted_at`) in each database. It is written in the same transaction as any removal from that database. Every copy checks it.
- **Copy rule**: a copy into the non-source database runs under a per-id lock (`pg_advisory_xact_lock(id)` in Postgres, `GET_LOCK('users:<id>')` in MySQL), taken in ascending id order. Under the lock: if a tombstone exists, the copy does nothing. Otherwise it inserts the row if missing, or replaces it only when the stored `version` is lower than the incoming one. In Postgres: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. In MySQL: a conditional `UPDATE ... WHERE version < new`, then an `INSERT` if no row exists. A unique-email conflict rolls the copy back and leaves the id queued. A copy never skips a row. Repeated or out-of-order copies never make a row older.
- **Id generator**: MySQL `AUTO_INCREMENT` while MySQL is the source, a Postgres sequence once Postgres is the source.
- **Source flag `users_source`**, read by every instance from `app.flags`:
  - `mysql`: MySQL is the source. Writes commit to MySQL and are copied forward.
  - `paused`: user writes get a retryable 503 with `Retry-After: 2`. Reads continue.
  - `pg`: Postgres is the source. Writes commit to Postgres and are copied back through the reverse queue.
  - `pg_only`: reverse copies stop.
- **Flag `users_dual_write`**: turns on the copy code on an instance. It is on from 1.1 to the end. The source flag sets the direction: forward copies under `mysql`, reverse copies under `pg`, none under `paused` or `pg_only`.
- **Gates**: the operator reads `app_flag_value{flag=...}`. An instance that does not report the metric counts as not converged.
- **In-flight writes**: a per-instance gauge (new in 0.3). It goes up when a user write enters UserRepository and down when the write returns. The operator adds it up across instances.

## Phase 0: Prepare, no user-visible change

- [ ] **0.1 Create the Postgres schema.**
  - Starts: a reviewed migration, run by hand.
  - Changes: in `pg-core`, creates `users` (`id BIGINT PRIMARY KEY` with no default, `email VARCHAR(320) UNIQUE`, `name VARCHAR(200)`, `plan VARCHAR(20)`, `version INT NOT NULL`, `updated_at TIMESTAMP(3)` in UTC), `user_tombstones`, `users_sync_queue` and `migration_state`. Session time zone is UTC.
  - State: `pg-core`.
  - On failure: nothing is live yet. Fix and rerun. Every statement uses `IF NOT EXISTS`.
- [ ] **0.2 Create the MySQL queue and tombstone tables.**
  - Starts: a schema migration on `core`.
  - Changes: creates `users_sync_queue` and `user_tombstones` in `core`. No code uses them yet.
  - State: `mysql-core-primary`.
  - On failure: as 0.1.
- [ ] **0.3 Deploy the code with every flag off.**
  - Starts: the normal deploy of web instances and worker processes.
  - Changes: `UserRepository` gains the dual-write, copy, read-fallback and source-switch paths, gated by `users_dual_write` (off), `users_read_source` (percentage, 0) and `users_source` (`mysql`). Workers gain the sweeper, the backfill worker and the comparison job, each holding a lease in `migration_state`. The lint rule `no-raw-users-sql` allows only the repository and the migration module. New metrics: `users_read_total{source}`, queue depth, oldest queued age, in-flight writes.
  - State: the code, plus `app.flags`.
  - On failure: roll back the deploy. With the flags off, the new paths do nothing.

## Phase 1: Dual writes, MySQL is the source

- [ ] **1.1 Turn on dual write on every instance.**
  - Starts: the operator sets `users_dual_write = on`.
  - Gate: every instance reports `app_flag_value{flag="users_dual_write"}=on`, then wait 60 s (covers the 30 s cache and a margin).
  - Changes, per write: in the same MySQL transaction as the `INSERT`, `UPDATE` or `DELETE` on `users`, upsert a forward-queue row (`ON DUPLICATE KEY UPDATE queued_at = NOW(3)`). A delete also writes the MySQL tombstone. After commit, the same request applies the row to Postgres under the copy rule (for a delete: the tombstone, then the delete). The apply has a 500 ms statement timeout. The request waits for it at most 500 ms, then returns its normal response whatever the apply did. On timeout the statement is cancelled and the queue row stays. On success the instance removes its queue row with a compare-and-delete (`WHERE user_id = ? AND queued_at = ?`).
  - State: the forward queue in MySQL is the durable record of pending work.
  - On failure: a Postgres error or timeout never changes the user's response; the row stays queued for the sweeper. A MySQL error on the queue insert fails the write, as it does today.
- [ ] **1.2 Run the repair sweeper.**
  - Starts: the worker's scheduled loop, running continuously once 1.1 is on.
  - Changes: reads queue rows ordered by `queued_at`, 500 at a time, from the MySQL primary. For each id it reads the current MySQL row. If the row exists, it applies the copy rule. If it is absent, it writes a Postgres tombstone and deletes the Postgres row under the lock. Then it compare-and-deletes the queue row. Mismatches confirmed in 3.1 go into this same queue.
  - State: the MySQL queue. The sweeper holds a lease in `migration_state` in Postgres, so only one sweeper runs at a time.
  - On failure: queue rows stay in MySQL and a restarted sweeper resumes from them. Retries back off exponentially with no cap. Alert when the oldest queued row is older than 5 min, and when an id stays queued on a unique-email conflict (see Open questions). Do not use `app.jobs` for repair: failed jobs go to `jobs:dead`, which nothing processes, and `enqueue` raises when Redis is unreachable.

## Phase 2: Backfill

- [ ] **2.1 Start the backfill worker.**
  - Starts: the operator sets `users_backfill = on`. Allowed only after the 1.1 gate has held for 60 s on every instance.
  - Changes: the worker takes the lease in `migration_state`, reads `backfill_last_id` (absent means 0), and processes batches from there.
  - State: `migration_state` in Postgres.
  - On failure: a crashed worker's lease expires after 60 s. Another worker resumes from the saved cursor.
- [ ] **2.2 Copy batches.**
  - Per batch: wait while `mysql_replica_lag_seconds > 5`, polling once per second. Then run `SELECT * FROM users WHERE id > :cursor ORDER BY id LIMIT 2000` on the replica. In one Postgres transaction, copy every row under the copy rule in ascending id order and set `migration_state.backfill_last_id` to the batch's last id. Commit.
  - Ends when a batch returns no rows: set `backfill_status = done`.
  - State: the cursor is written in the same transaction as the copies, so the two cannot disagree.
  - On failure: a restarted worker continues after `backfill_last_id`. Redoing a batch is safe because the copy rule is idempotent. A batch rolled back on an email conflict is retried after a sleep. Rows are never skipped. A conflict that persists raises an alert and stops the backfill.

## Phase 3: Verify

- [ ] **3.1 Run a full comparison pass.**
  - Starts: the operator starts one pass by hand on a worker. Run it after 2.2 reports done, after any later change to the source, read ramp or repair, and during the 4.2 hold. Results go to `migration_state`.
  - Changes: walks both tables in id ranges of 2,000. For each range it compares the row count and a hash of `(id, version, email, name, plan, updated_at)`, with `updated_at` at millisecond precision in UTC. For each mismatched range it re-reads every mismatched id from the MySQL primary and from Postgres. If a row changed between the two reads, it waits 2 s and checks again, so in-flight writes are not counted. Each confirmed mismatch goes into the forward queue and the sweeper in 1.2 repairs it: if the id has a MySQL row, it is copied to Postgres; if the id is Postgres-only, the Postgres tombstone is written and the Postgres row deleted.
  - Pass criterion: one full pass ends with zero confirmed mismatches. A pass that finds mismatches repairs them and does not count; the next pass must be clean.
  - State: pass id, progress cursor and mismatch count in `migration_state`.
  - On failure: the pass resumes from its cursor. Users are not affected.
- [ ] **3.2 Run a reverse comparison (Phases 5 to 7).**
  - Starts: the operator starts it by hand: once at the start of 5.5, at least daily during 5.5, and before 7.1.
  - Changes: the same job as 3.1 with the roles swapped. Postgres is the source. Confirmed mismatches go into the reverse queue. The reverse sweeper copies a Postgres row to MySQL under the copy rule, or for a MySQL-only id writes the MySQL tombstone and deletes the MySQL row.
  - Pass criterion and failure handling: as 3.1.

## Phase 4: Move reads to Postgres

- [ ] **4.1 Ramp reads: 1%, 10%, 50%, 100%.**
  - Starts: a flag change to `users_read_source`, bucketed by user id with `flags.enabled_for`. Gate before the first step: a clean 3.1 pass within the last 24 h, and no forward-queue row older than 5 min.
  - Changes: `UserRepository.get` tries Postgres with a 200 ms timeout. It falls back to the MySQL replica on an error, a timeout or a missing row, so reads never fail. A row found in Postgres is returned even if its version is older (see Known trade-offs). Each step holds at least 1 h and checks the error rate and the fallback rate.
  - State: `app.flags`, plus `users_read_total{source=pg|mysql_fallback}`.
  - On failure: set the flag to a lower percentage, or to 0. Reads return to MySQL at once. A fallback rate above 0.1% stops the ramp and triggers a 3.1 pass.
- [ ] **4.2 Hold reads at 100% on Postgres for 3 days.**
  - Starts: `users_read_source = 100` on every instance, confirmed by the metric.
  - Gate: at least 72 h with no change below 100. During the hold, run 3.1 once more and require zero mismatches.
  - On failure: any change below 100 or any mismatch restarts the 72 h clock, and the ramp in 4.1 begins again from the step that failed.

## Phase 5: Switch the source of truth to Postgres

The pause runs from the `paused` flag (5.2) until every instance shows `pg` (5.4). It must stay within 90 s.

- [ ] **5.1 Check the gates.**
  - Preconditions: 4.2 is complete. The latest 3.1 pass has zero mismatches. The forward queue is empty. `mysql_replica_lag_seconds < 5`. Every instance reports `users_dual_write=on`.
  - On failure: no change is made. Wait.
- [ ] **5.2 Pause user writes.**
  - Starts: the operator sets `users_source = paused`.
  - Changes: each instance returns 503 with `Retry-After: 2` for user writes. Reads keep running. The erasure job's deletes get the same retryable error and retry through `app.jobs`; its five attempts over about 15 min are far longer than the pause.
  - Gate: every instance shows `paused` within 30 s (the cache refresh). Then the in-flight writes gauge must reach 0 on all instances within 5 s.
  - On failure: if not every instance shows `paused` within 30 s, set `users_source = mysql` and stop. Nothing was written to Postgres as the source, so this is safe. If in-flight writes are still above 0 at 5 s, keep waiting in `paused`. If they are still above 0 at 10 s, set `users_source = mysql` and stop. Those writes committed to MySQL with their queue rows, so the forward sweeper finishes them.
- [ ] **5.3 Drain the queue and set the Postgres id generator.**
  - While paused, with in-flight writes at 0: the sweeper drains the forward queue to zero, with a cap of 10 s. Then, in `pg-core`, set the users id sequence to `max(id)` across both databases plus 1,000,000. Read the MySQL maximum from the primary.
  - On failure: if the drain is not done within 10 s, or the sequence update fails, set `users_source = mysql` and abort. Nothing was committed as the Postgres source.
- [ ] **5.4 Make Postgres the source.**
  - Starts: the operator sets `users_source = pg` by hand, after 5.3 is done and checked.
  - Changes, per write: one Postgres transaction assigns the id from the sequence (or bumps `version` by 1 on update), writes the row and writes a reverse-queue row. After commit it applies the row to MySQL under the copy rule with a 500 ms timeout, and removes the reverse-queue row on success. The reverse sweeper works like 1.2 with the roles swapped.
  - Gate: every instance reports `users_source=pg`. The pause budget is 30 s to show `paused`, 5 s for in-flight writes, 10 s to drain the queue in 5.3 and 30 s to show `pg`: at most 75 s, inside the 90 s limit.
  - State: the reverse queue in Postgres.
  - On failure: this step cannot be aborted. Restart any instance still reporting `paused`; it re-reads flags on start. Record any pause over 90 s as a violation. Do not set the flag back to `mysql`: once Postgres has assigned ids, MySQL could assign the same ids, and rows still in the reverse queue would not reach MySQL. Roll back through Phase 6 instead.
- [ ] **5.5 Hold in `pg` for at least 14 days.**
  - Rollback stays possible throughout (Phase 6). Run 3.2 as described there. Watch the reverse-queue age, the reverse copy error rate and the reverse comparison results.

## Phase 6: Roll back to MySQL

Available from 5.4 until 7.2. No write is lost: every Postgres write is either already in MySQL or in the reverse queue, which is drained below. The pause here counts against the same 90 s limit.

- [ ] **6.1 Pause user writes.** Set `users_source = paused` and run the 5.2 gate. On failure, set `pg` again.
- [ ] **6.2 Drain the reverse queue and set the MySQL id generator.** Drain the reverse queue in Postgres to zero, with a cap of 10 s. Then set MySQL `AUTO_INCREMENT` on `users` to `max(id)` across both databases plus 1,000,000. On failure, set `users_source = pg` and abort. Nothing was lost.
- [ ] **6.3 Set `users_source = mysql`.** Forward dual writes resume. Reads stay on Postgres, which is current. Gate: every instance shows `mysql`. On failure, restart stragglers, as in 5.4.

## Phase 7: Postgres-only writes

- [ ] **7.1 Check the gate.** `users_source = pg` has held for at least 14 days. The reverse queue is empty. The latest 3.2 pass has zero mismatches. Record the decision.
- [ ] **7.2 Stop reverse copies.**
  - Starts: the operator sets `users_source = pg_only`. No pause is needed, because the source of truth does not change.
  - Changes: writes commit to Postgres and write no reverse-queue row. Reverse copies to MySQL stop.
  - Gate: 30 s after the change, the reverse queue is still empty. A lagging instance may write a row in that window; any row found is an open item for the operator to resolve before 8.1.
  - On failure: after this step, rollback to MySQL is no longer possible. If the flag is ever reversed, set `pg` again. MySQL then needs a full 3.2 pass with zero mismatches before any rollback is safe.
- [ ] **7.3 Remove the dual-write code.** Remove the forward and reverse queues, the sweeper branches and the `users_source` branches. Do not run 3.1 here: MySQL no longer receives copies, so it would report mismatches by design. Keep MySQL tombstones until the table is dropped.

## Phase 8: Drop the MySQL table

- [ ] **8.1 Drop `core.users`.**
  - Starts: a planned change, not before 7.2. The brief requires a further hold, which is a team choice; a 30-day hold is suggested.
  - Changes: take a logical dump of `users` and store it outside the cluster, then `DROP TABLE users`.
  - On failure: restore from the dump. The drop cannot be undone without it.

## Known trade-offs

- A Postgres read can lag a write by the time the inline apply or the sweeper takes, typically under a second. Such a read returns the previous version of the row, or nothing for a new user. A read-after-write check against the forward queue would cost a MySQL primary query on every read, so it is not in the design (open, see Open questions).
- A Postgres miss falls back to the MySQL replica, which also lags. During that lag window a fallback can return a user deleted within the last second or so.
- Erasure deletes depend on `app.jobs` retries. Alert on any erasure entry in `jobs:dead`, because nothing else processes it.

## Open questions

- Does `app_flag_value` show string flags such as `users_source`? The flags doc says it exports the values in use, but not their format. The gates in 5.2 and 5.4 depend on seeing `paused` and `pg`.
- Must an erasure done in `pg_only` also delete the MySQL row? After 7.2 reverse copies stop, so the MySQL row stays until 8.1. This needs a legal decision.
- Read-after-write on Postgres reads (see the first trade-off). Open decision.
- A unique-email conflict (one email held by two ids, for example after an email change that one database has not applied yet) leaves an id queued. The brief allows no manual repair, but this design does not say which id wins. Frequency unknown; check it in 3.1 results before 4.1.