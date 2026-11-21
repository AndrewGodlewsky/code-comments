# Move `users` from MySQL 8 to Postgres 16

## What this is

We are moving the `users` table from MySQL 8 (database `core`) to the new Postgres 16 cluster (`pg-core`) while the service stays up. Every read and write of `users` already goes through `UserRepository`, the only code allowed to touch that table, so the migration logic goes there.

The move happens in three stages. First, MySQL still owns writes, and every change is also copied to Postgres. Second, reads move to Postgres after both tables are proven equal. Third, Postgres owns writes, and MySQL receives copies for at least 14 days so we can roll back. MySQL's table is dropped last.

## How the system works today

Writes go to the MySQL primary and reads go to the MySQL replica, both inside `UserRepository`. Each update adds 1 to a `version` column. Feature flags are cached in every app instance and refreshed every 30 seconds, so instances can disagree for up to 30 seconds after a change. Background jobs retry 5 times, then move to a dead-letter list that nothing reads.

## Terms

- **Primary / replica**: MySQL takes writes on the primary. The replica is a read-only copy. Its lag is exported as `mysql_replica_lag_seconds`.
- **PG**: the Postgres 16 cluster `pg-core`.
- **Owner**: the database that is the source of truth for writes. Either `mysql` or `postgres`.
- **Phases**: A is MySQL owns writes, PG receives copies. B is MySQL owns writes, reads come from PG. C is PG owns writes, MySQL receives copies. D is PG only, with no copies to MySQL.
- **Fence** (`user_migration_state`): a one-row table in each database. It holds `owner`, `mode` (`active` or `frozen`) and `epoch` (a counter that goes up on every change of mode or owner). Every write checks it first.
- **Frozen**: a mode in which that database accepts no writes. Writes get a retryable 503.
- **Outbox** (`user_sync_outbox`): a list of changes the owner has made but the other database has not yet confirmed. Each row holds `user_id`, `version` and `op` (`upsert` or `delete`).
- **Mirror worker**: a loop in every app instance that copies outbox rows from the owner to the other database. It runs on table state, not on the job queue, so it is not affected by job retries or the dead-letter list.
- **Copy function**: the only code that writes a copy into a database. Dual writes, the mirror, the backfill and repairs all use it.
- **Version rule**: a copy may insert a row that is missing, or replace a row whose `version` is lower than the incoming one. Nothing else.
- **Tombstone** (`user_tombstones`): a record that a user was erased. It holds only `user_id` and `erased_at`. A copy never recreates a user who has a tombstone.
- **Advisory lock**: a lock on one user id (`pg_advisory_xact_lock` in PG, `GET_LOCK` in MySQL). It stops two copies of the same id from running at once.
- **Sequence / AUTO_INCREMENT**: the counter that gives each new user an id. MySQL uses `AUTO_INCREMENT`. PG uses `users_id_seq`.
- **Lease**: a claim on the backfill, with an expiry time. Only the runner holding it works, and if that runner dies, the lease expires and another runner takes over.
- **Compare pass**: a sweep through all rows in id order, comparing the two databases.
- **Soak**: the period during which 100% of reads come from PG, with the clock running.
- **PITR**: point-in-time recovery, a backup that can restore PG to any moment.
- **Timestamps**: `updated_at` is stored as UTC `TIMESTAMPTZ(3)`. It is copied as-is. It is never used to decide which version wins.

## How the system runs

**Writes.** A write opens a transaction and reads its own database's fence row with `FOR SHARE` as its first statement. This blocks a freeze until the write finishes.
- If its database is the active owner, the write proceeds.
- If the other database is the owner, the write re-routes once to that database.
- If its database is frozen, the write returns a retryable 503.

The flag `users.source` only chooses which database to try first. Correctness and the pause do not depend on it.

Each create, update or erase also writes an outbox row to the owner, in the same transaction as the change. The row is removed only when the other database confirms the copy, and only if its `version` has not changed since.

**Erase.** The erasure job deletes the user in the owner's transaction, writes a tombstone there, and adds an outbox delete row. The mirror then deletes the user in the other database and writes a tombstone there too. Until the mirror runs, the other database may still hold the user, but no copy can bring the user back once a tombstone exists. Legal must confirm that keeping erased ids in tombstones is acceptable.

**Ids.** In phase A, MySQL assigns ids. Each switch to PG moves the PG sequence to at least MySQL's counter plus 1,000,000, so ids never collide. Each rollback moves MySQL's counter to at least the highest PG id plus 1.

**Reads.** In phase B and later, reads come from PG. If PG fails, or misses a row that MySQL has, the read falls back to the MySQL replica. A miss in both is "not found".

## Checklist

Each step says what starts it, what it changes, where its state lives, and what happens if it fails.

### Preparation

- [ ] **1. Create the PG schema.**
  - **Starts:** a migration is merged.
  - **Changes:** creates `users` (`id BIGINT PRIMARY KEY`, `email VARCHAR(320) UNIQUE NOT NULL`, `name`, `plan`, `version INT NOT NULL`, `updated_at TIMESTAMPTZ(3)`), `user_tombstones`, `user_sync_outbox`, `user_migration_state` (owner `mysql`, mode `active`, epoch 1), `migration_backfill` (one row: `last_id`, lease owner, lease expiry, status) and `migration_compare` (pass results). Also creates `users_id_seq`, which is not yet the default for `id`.
  - **State:** PG.
  - **If it fails:** the DDL can be run again. Nothing user-facing has changed.

- [ ] **2. Add MySQL tables.**
  - **Starts:** step 1 is done.
  - **Changes:** adds `user_sync_outbox`, `user_tombstones` and `user_migration_state` (owner `mysql`, mode `active`, epoch 1) to `core`. `users` is untouched.
  - **State:** MySQL `core`.
  - **If it fails:** drop the new tables. Nothing uses them yet.

- [ ] **3. Deploy build N of the repository.**
  - **Starts:** a release.
  - **Changes:** every write checks the fence and writes an outbox row. Erase also writes a tombstone and an outbox delete row. Every instance runs the mirror worker, which idles when the outbox is empty. Every instance exports a build-version metric. The inline PG copy is controlled by flag `users.dual_write`, default off.
  - **State:** MySQL outbox and fence rows.
  - **If it fails:** roll back to the previous build. Until step 7 is complete, no build below N may run. Older builds write without an outbox row and skip the fence, which would break the backfill gate and the freeze.

- [ ] **4. Turn on inline dual writes.**
  - **Starts:** every instance reports build N, then flag `users.dual_write` is turned on.
  - **Changes:** after the MySQL commit, each write reads the row from the MySQL primary and copies it to PG through the copy function. The copy has a 200 ms timeout and a bounded connection pool.
  - **State:** the outbox row is removed when the copy succeeds.
  - **If it fails:** PG errors and timeouts are swallowed, so the user's request still succeeds. The outbox keeps the change, and the mirror worker repairs it. Alert when the oldest outbox row is more than 5 minutes old. Turning the flag off returns the system to outbox-only mirroring.

### Backfill and verification (phase A)

- [ ] **5. Run the backfill.**
  - **Starts:** the gate passes and flag `users.backfill` is on. The gate needs all of these:
    - every instance reports build N and `users.dual_write` has been on for at least two refresh intervals (60 s);
    - replica lag is fresh and at most 5 s;
    - the oldest outbox row is under 5 minutes old.
  - **Changes:** a watchdog in the worker tier runs every minute and takes the lease in `migration_backfill`. The lease holder runs batches:
    1. If `mysql_replica_lag_seconds` is above 5 s or missing, sleep 5 s and check again.
    2. Read up to 2,000 rows from the replica: `WHERE id > last_id ORDER BY id LIMIT 2000`.
    3. Open a PG transaction. Take the id locks in ascending order, skip tombstoned ids, apply the copy function, and set `last_id` to the batch's highest id.
    4. Commit. A batch with fewer than 2,000 rows marks the backfill complete.
  - **State:** `migration_backfill` in PG. Progress is saved in the same transaction as the rows, so a crash repeats at most one uncommitted batch.
  - **If it fails:**
    - PG down: retry with backoff. Progress does not move.
    - Replica error: retry.
    - Batch error, such as an email collision: stop and alert. Do not skip ids.
    - Runner crash: the lease expires and another runner resumes at `last_id`.
    - PG restored from an older backup: `last_id` goes back and some batches repeat. This is harmless because of the version rule.

- [ ] **6. Run a full compare, repairing as it goes.**
  - **Starts:** the backfill is complete.
  - **Changes:** a compare pass walks the replica in id order and compares `version` and fields for each row. A row that looks different is rechecked on both primaries. Only a mismatch that survives the recheck counts, and it is repaired through the copy function. Each pass writes its result to `migration_compare`.
  - **State:** `migration_compare` in PG.
  - **If it fails:** PG down: the pass pauses. Replica lag can cause false candidates, so nothing counts without a primary recheck. Passes repeat until one is clean. A pass is clean when it finds zero confirmed mismatches and the outbox is empty when it ends.

- [ ] **7. Move reads to PG in steps.**
  - **Starts:** the last compare pass is clean, the outbox is empty, and all instances run build N.
  - **Changes:** flag `users.read_source` (`mysql` or `postgres`) is raised through `flags.enabled_for`, keyed on user id, to 1%, 10%, 50% and 100%. Each step holds for at least one hour. `get` reads from PG. On a PG error, or a PG miss where MySQL has the row, it falls back to the MySQL replica. A row found only in MySQL counts as a mismatch and queues a repair. A miss in both is "not found", which also covers erased users.
  - **State:** the flag store, plus counters `users_read_source_total{source}` and `users_read_fallback_total{reason}`.
  - **If it fails:** reads never fail because of PG. If the fallback or error rate passes the threshold, set the ramp back to 0. This takes effect at once. Accepted trade-off: a PG read can lag the latest write by the outbox delay. Measure the p99 lag. If it is too high, add a read-your-writes check.

- [ ] **8. Soak reads at 100% on PG for at least 72 hours.**
  - **Starts:** the ramp reaches 100% and every instance reports `users.read_source` = `postgres` in `app_flag_value`.
  - **Changes:** the clock runs, and compare passes keep running in the background.
  - **State:** the clock start and reset times are recorded in `migration_compare`.
  - **If it fails:** any fallback caused by an error, any confirmed mismatch, or any instance reverting resets the clock to zero. Investigate, then restart the soak. Switch 1 will not run until the clock shows at least 72 hours.

- [ ] **9. Rehearse both switches and the rollback in staging.**
  - **Starts:** before step 10.
  - **Changes:** runs steps 10 and 12 with faults injected: PG down during the drain, the MySQL owner update failing after the PG flip, the flag stuck, and the rollback path. Measure the pause.
  - **State:** staging only.
  - **If it fails:** do not go to production. The production switch needs a passing rehearsal with a pause of at most 60 s.

### Switch 1: PG becomes the source of truth (writes paused at most 90 s)

- [ ] **10. Switch 1 (phase B to C).**
  - **Starts:** a manual trigger. Before starting, all of these must hold: the soak clock shows at least 72 hours; the last compare pass is clean; the outbox is empty; PG has a synchronous standby and a verified PITR backup; step 9 has passed; no rollback is in progress.
  - **Changes:**
    - a. Freeze MySQL: set `mode = 'frozen'` and increase `epoch`. The freeze waits for in-flight writes, which hold `FOR SHARE`. From here, MySQL-path writes return 503. **The pause starts.**
    - b. Read MySQL's `AUTO_INCREMENT` value N. Drain the MySQL outbox into PG until it is empty. The drain has a 60-second deadline counted from (a). If the deadline passes or PG errors, set MySQL back to `active` and stop. Stopping is allowed only before (c).
    - c. In one PG transaction, set the sequence to `GREATEST(N, current) + 1000000`, then set PG `owner = 'postgres'` and `mode = 'active'`.
    - d. Set MySQL `owner = 'postgres'`. Its mode stays `frozen`. MySQL-path requests now re-route to PG. Retry this update until it succeeds. There is no stopping after (c).
    - e. Set flag `users.source` = `postgres`. This is only a routing preference. Start the PG-to-MySQL mirror, whose direction is read from `owner`.
    - f. Confirm that all instances report `users.source` = `postgres` within 60 s. **The pause ends** when the first PG write commits.
  - **State:** `user_migration_state` in both databases, plus the sequence.
  - **If it fails:** before (c), unfreeze MySQL and stop. After (c), PG is the source of truth. Writes return 503 while PG is down and never fall back to MySQL on their own. The pause is roughly the drain time plus two round trips, bounded by the 60-second drain deadline.

- [ ] **11. Phase C: PG owns writes for at least 14 days.**
  - **Starts:** step 10 is done.
  - **Changes:**
    - Writes run in a PG transaction after the fence check. Ids come from the sequence. Erase writes a tombstone and deletes the row. The outbox row is written in the same transaction, then copied to MySQL through the copy function, and removed once MySQL confirms.
    - Reads come from PG. On a PG error they fall back to the MySQL replica, which checks its tombstones. Any stale result is counted.
    - A reverse compare, with PG as the reference, runs continuously. Rollback depends on it.
  - **State:** PG outbox and fence rows.
  - **If it fails:** MySQL down: the outbox grows in PG, writes still succeed, and an alert fires. PG down: writes return 503. Each committed PG write has its outbox row in PG, so nothing is lost once PG recovers. If PG storage were lost, unmirrored writes would be lost too. That is why synchronous replication and PITR must be in place before this phase starts.

- [ ] **12. Roll back to MySQL (available until step 13).**
  - **Starts:** a manual decision.
  - **Gate:** the outbox is empty and the last reverse compare pass is clean. If no reverse compare has run in the last 24 hours, run one first. That run happens outside the pause.
  - **Changes:** the same pattern as step 10, in reverse.
    - a. Freeze PG (`mode = 'frozen'`).
    - b. Drain the PG outbox into MySQL until it is empty, with a 60-second deadline. Stopping is allowed before (c).
    - c. Set MySQL `AUTO_INCREMENT` to `GREATEST(current, PG max id + 1)`. Set MySQL `owner = 'mysql'` and `mode = 'active'`.
    - d. Set PG `owner = 'mysql'`. PG-path requests re-route to MySQL.
    - e. Set flag `users.source` = `mysql`. The mirror direction flips to MySQL-to-PG.
  - **State:** the same tables.
  - **If it fails:** as in step 10. A later switch to PG repeats step 10.

### Phase D: PG-only writes, then retire MySQL

- [ ] **13. Stop mirroring to MySQL (phase D).**
  - **Starts:** at least 14 days after step 10c. Before starting, all of these must hold: a reverse compare pass is clean within the last 24 hours; the outbox is empty; no rollback is in progress.
  - **Changes:** turns flag `users.mirror_to_mysql` off and deletes outbox rows that would otherwise pile up. The app's MySQL role loses write access to `users`. The MySQL fence row stays frozen. The owner does not change, so there is no pause.
  - **State:** the flag store and MySQL grants.
  - **If it fails:** this step cannot be undone. After it, rollback is not possible. If needed, recover from a MySQL dump.

- [ ] **14. Keep a dump, then drop the MySQL table.**
  - **Starts:** at least 30 days after step 13. The 30-day retention period is a recommendation and needs the owner's approval.
  - **Changes:** take a logical dump of `core.users`, `user_tombstones` and `user_migration_state`. Then drop `users` in MySQL. Remove the dual-write, outbox and MySQL read code, the flags, and the `no-raw-users-sql` lint exception added for this migration.
  - **State:** backup storage.
  - **If it fails:** restore from the dump. Otherwise the drop cannot be undone.

## Open questions

- Should the build floor (no build below N) end at step 7 as written? Steps 8 to 14 also depend on the fence, so a build below N during those steps would break the freeze.
- The 30-day retention period before dropping MySQL (step 14) needs the owner's approval.
- Legal must review keeping erased user ids in `user_tombstones`.
- Do PG reads need a read-your-writes check (step 7)? This depends on the p99 lag measured during the ramp.
- PG high availability and PITR must be in place before step 10.