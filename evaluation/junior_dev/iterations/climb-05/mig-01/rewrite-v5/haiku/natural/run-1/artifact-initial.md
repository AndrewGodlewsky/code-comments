# Move `users` from MySQL 8 to Postgres 16

## Mechanisms the steps rely on

- **Phases.** A: MySQL owns writes, Postgres (PG) receives dual writes and backfill. B: MySQL owns writes, reads come from PG. C: PG owns writes, MySQL receives mirror writes, rollback is possible. D: PG only, mirroring to MySQL stopped.
- **Owner fence.** Each database has a `user_migration_state` row with `owner` (`mysql` or `postgres`), `mode` (`active` or `frozen`) and `epoch`. Every write transaction reads its own database's row with `FOR SHARE` as its first statement. If its database is the active owner, it proceeds. If the other database is the owner, it re-routes once to that path. If its database is frozen, it returns a retryable 503. The flag `users.source` only picks which path to try first. Correctness and the pause do not depend on the 30-second flag refresh.
- **Outbox.** Every create, update and erase inserts a row into the owner's `user_sync_outbox` (`user_id`, `version`, `op` = upsert or delete) in the same transaction as the change. A row is removed only after the other database confirms the copy, and only if its `version` is unchanged. A mirror worker in every instance drains the outbox from the owner to the other database. It is a loop driven by table state, not a queued job, so it does not depend on the job system's 5 retries or the dead-letter list.
- **One copy function.** Every copy (dual write, mirror, backfill, repair) goes through one function. It takes a per-id lock (`pg_advisory_xact_lock(id)` in Postgres, `GET_LOCK` in MySQL), skips ids in the target's `user_tombstones`, inserts the row if missing, and otherwise updates `WHERE version < incoming`. Nothing else writes copies, so the version rule holds everywhere.
- **Erasure.** Erasure deletes in the owner's transaction, writes a tombstone there, and adds an outbox delete row. The mirror applies the delete and writes the tombstone in the other database. Tombstones hold only `user_id` and `erased_at`. Legal should confirm that keeping the id is acceptable. Once a target tombstone exists, no copy can recreate the user. Between the owner's delete and the mirror's delete, the other database may still hold the row for the mirror lag, but nothing can bring it back.
- **Ids.** Phase A uses MySQL `AUTO_INCREMENT`. Each switch to PG sets the PG sequence to at least MySQL's counter plus 1,000,000. Each rollback sets MySQL's `AUTO_INCREMENT` to at least the PG maximum id plus 1.
- **Timestamps.** `updated_at` is stored as UTC `TIMESTAMPTZ(3)`. It is copied as-is and is never used for version decisions.

## Checklist

### Preparation

- [ ] **1. Create the PG schema (pg-core).**
  - **Starts:** a migration merged.
  - **Changes:** creates `users` (`id BIGINT PRIMARY KEY`, `email VARCHAR(320) UNIQUE NOT NULL`, `name`, `plan`, `version INT NOT NULL`, `updated_at TIMESTAMPTZ(3)`), `user_tombstones`, `user_sync_outbox`, `user_migration_state` (owner `mysql`, mode `active`, epoch 1), `migration_backfill` (single row: `last_id`, lease owner, lease expiry, status) and `migration_compare` (pass results). It also creates `users_id_seq`, not yet the default for `id`.
  - **State:** pg-core.
  - **If it fails:** DDL is re-runnable. Nothing user-facing has changed.

- [ ] **2. Add MySQL tables (core).**
  - **Starts:** step 1 done.
  - **Changes:** adds `user_sync_outbox`, `user_tombstones` and `user_migration_state` (owner `mysql`, mode `active`, epoch 1). The `users` table is untouched.
  - **State:** core database.
  - **If it fails:** drop the new tables. Nothing depends on them yet.

- [ ] **3. Deploy build N of the repository.**
  - **Starts:** release.
  - **Changes:** every write checks the owner fence and writes an outbox row. Erase writes a tombstone and an outbox delete row. Each instance runs the mirror worker, which is idle until there is work. Each instance exports a build-version metric. The inline PG copy is controlled by flag `users.dual_write`, default off.
  - **State:** MySQL outbox and state rows.
  - **If it fails:** roll back to the previous build. After this deploy, no build below N may run until step 7 is complete. Old builds write without an outbox row and do not check the fence, so they would break both the backfill gate and the freeze.

- [ ] **4. Turn on inline dual writes.**
  - **Starts:** all instances report build N, then flag `users.dual_write` is set to on.
  - **Changes:** after the MySQL commit, each write reads the row from the MySQL primary and copies it to PG through the copy function. The copy has a 200 ms timeout and a bounded connection pool.
  - **State:** the outbox row is removed when the copy succeeds.
  - **If it fails:** PG errors and timeouts are swallowed, so the user's request still succeeds. The outbox keeps the change, and the mirror worker repairs it automatically. Alert when the oldest outbox row is older than 5 minutes. Setting the flag off returns to outbox-only mirroring.

### Backfill and verification (phase A)

- [ ] **5. Start the backfill.**
  - **Starts:** the gate passes and flag `users.backfill` is on. The gate requires every instance to report build N and `users.dual_write` on for at least two refresh intervals (60 s), replica lag to be fresh and at most 5 s, and the oldest outbox row to be under 5 minutes old.
  - **Changes:** a watchdog in the worker tier (every minute) takes the lease in `migration_backfill`. Each batch does the following:
    1. If `mysql_replica_lag_seconds` is above 5 s or missing, sleep 5 s and recheck.
    2. Read up to 2,000 rows from the replica with `WHERE id > last_id ORDER BY id LIMIT 2000`.
    3. Open a PG transaction. Take the per-id locks in ascending id order, skip tombstoned ids, apply the copy function, and set `last_id` to the batch's maximum id.
    4. Commit. A batch shorter than 2,000 rows marks the backfill complete.
  - **State:** `migration_backfill` in PG. Progress is written in the same transaction as the rows, so a crash replays at most one uncommitted batch.
  - **If it fails:**
    - PG down: retry with backoff. Progress does not move.
    - Replica error: retry.
    - Batch error, such as an email uniqueness collision: stop and alert. Do not skip ids.
    - Runner crash: the lease expires and another runner resumes at `last_id`.
    - PG restored from an older backup: `last_id` rewinds and some batches repeat. This is harmless because of the version rule.

- [ ] **6. Run a full compare with automatic repair.**
  - **Starts:** backfill complete.
  - **Changes:** sweeps the replica in id order and compares `version` and fields for each row. Candidate mismatches are rechecked against both primaries before they count. Confirmed mismatches are repaired through the copy function. Each pass writes its result to `migration_compare`.
  - **State:** `migration_compare` in PG.
  - **If it fails:** PG down: pause the pass. Replica lag can cause false candidates, so nothing is counted without a primary recheck. Passes repeat until one is clean. A pass is clean when it has zero confirmed mismatches and the outbox is empty when it ends.

- [ ] **7. Move reads to PG in canary steps.**
  - **Starts:** the last compare pass is clean, the outbox is empty, and all instances run build N.
  - **Changes:** flag `users.read_source` (`mysql` or `postgres`) is ramped with `flags.enabled_for` keyed on user id, at 1%, 10%, 50% and 100%, holding each step for at least one hour. `get` reads from PG. On a PG error, or on a PG miss where MySQL has the row, it falls back to the MySQL replica. The second case counts as a mismatch and queues a repair. If both miss, the result is "not found", which covers erased users.
  - **State:** flag store, plus counters `users_read_source_total{source}` and `users_read_fallback_total{reason}`.
  - **If it fails:** reads never fail because of PG. If the fallback rate or error rate exceeds the threshold, set the ramp back to 0. This is instant. Accepted trade-off: a PG read can lag the last write by the outbox delay. Measure p99 lag, and add a read-your-writes check if it is too high.

- [ ] **8. Soak reads at 100% on PG for at least 72 hours.**
  - **Starts:** 100% is reached and every instance reports `users.read_source` = `postgres` in `app_flag_value`.
  - **Changes:** the clock runs and the compare keeps passing in the background.
  - **State:** clock start and reset times are recorded in `migration_compare`.
  - **If it fails:** any fallback caused by an error, any confirmed mismatch, or any instance reverting resets the clock to zero. Investigate, then restart the soak. Switch 1 refuses to run until the clock reads at least 72 hours.

- [ ] **9. Rehearse both switches and the rollback in staging.**
  - **Starts:** before step 10.
  - **Changes:** runs the steps in 10 and 12 with fault injection: PG down during the drain, the MySQL owner update failing after the PG flip, the flag stuck, and the rollback path. Measure the pause.
  - **State:** staging only.
  - **If it fails:** do not proceed. The production switch needs a passing rehearsal with a pause of at most 60 s.

### Switch 1: source of truth moves to PG (writes paused at most 90 s)

- [ ] **10. Switch 1 (phase B to C).**
  - **Starts:** a manual trigger. Preconditions: the soak clock is at least 72 hours, the last compare is clean, the outbox is empty, PG has a synchronous standby with a verified PITR backup, step 9 has passed, and no build rollback is in progress.
  - **Changes:**
    - a. Freeze MySQL: set `mode = 'frozen'` and increment `epoch`. This waits for in-flight writes, which hold `FOR SHARE`. From here MySQL-path writes return 503. The pause starts.
    - b. Read MySQL's `AUTO_INCREMENT` value N. Drain the MySQL outbox into PG until it is empty, with a 60-second deadline measured from (a). If the deadline passes or PG errors, set MySQL back to `active` and abort. Abort is allowed only before (c).
    - c. In one PG transaction, set the sequence to `GREATEST(N, current) + 1000000` and set PG `owner = 'postgres'`, `mode = 'active'`.
    - d. Set MySQL `owner = 'postgres'` (mode stays `frozen`). MySQL-path requests now re-route to PG. Retry this update until it succeeds. There is no abort after (c).
    - e. Set flag `users.source` = `postgres`, a routing preference only. Start the PG-to-MySQL mirror, whose direction is read from `owner`.
    - f. Confirm that all instances report `users.source` = `postgres` within 60 s. The pause ends when the first PG write commits.
  - **State:** `user_migration_state` in both databases, plus the sequence.
  - **If it fails:** before (c), unfreeze MySQL and abort. After (c), PG is the source. Writes return 503 while PG is unavailable and never go back to MySQL on their own. The pause is roughly the drain time plus two round trips, bounded by the 60-second drain deadline.

- [ ] **11. Phase C: PG owns writes for at least 14 days.**
  - **Starts:** step 10 done.
  - **Changes:**
    - Writes run in a PG transaction after the fence check. Ids come from the sequence. Erase writes a tombstone and deletes. The outbox row is written in the same transaction, then the row is copied to MySQL through the copy function, and the outbox row is removed once confirmed.
    - Reads come from PG. On a PG error they fall back to the MySQL replica, which checks its tombstones. Any stale result is counted.
    - A reverse compare with PG as the reference runs continuously. Rollback relies on it.
  - **State:** PG outbox and state rows.
  - **If it fails:** MySQL down: the outbox grows in PG, and writes still succeed. Alert. PG down: writes return 503. Each committed PG write has its outbox row in PG, so nothing is lost once PG recovers. If PG storage were lost, un-mirrored writes would be lost too. That is why PG needs synchronous replication and PITR before this phase starts.

- [ ] **12. Roll back to MySQL (available until step 13).**
  - **Starts:** a manual decision.
  - **Changes:** the same pattern in reverse.
    - a. Freeze PG (`mode = 'frozen'`).
    - b. Drain the PG outbox into MySQL until it is empty, with a 60-second deadline. Abort is allowed before (c).
    - c. Set MySQL `AUTO_INCREMENT` to `GREATEST(current, PG max id + 1)`. Set MySQL `owner = 'mysql'`, `mode = 'active'`.
    - d. Set PG `owner = 'mysql'`. PG-path requests re-route to MySQL.
    - e. Set flag `users.source` = `mysql`. The mirror direction flips to MySQL-to-PG.
  - **Gate:** the outbox is empty, and the last reverse compare pass is clean. If none has run in 24 hours, run one first. That run is outside the pause.
  - **State:** the same tables.
  - **If it fails:** as in step 10. A later switch to PG repeats step 10.

### Phase D: Postgres-only writes and retirement of MySQL

- [ ] **13. Stop mirroring to MySQL (phase D).**
  - **Starts:** at least 14 days after step 10c. Preconditions: a reverse compare pass is clean within the last 24 hours, the outbox is empty, and no rollback is in progress.
  - **Changes:** set flag `users.mirror_to_mysql` off and delete the outbox rows that would otherwise accumulate. The app role on MySQL loses write access to `users`. The MySQL state row stays frozen. Source of truth does not change, so no pause occurs.
  - **State:** flag store and MySQL grants.
  - **If it fails:** the step is one-way. After it, rollback is not possible. Recover from a MySQL dump if needed.

- [ ] **14. Retain, then drop the MySQL table.**
  - **Starts:** at least 30 days after step 13. The 30-day retention period is a recommendation and needs the owner's approval.
  - **Changes:** take a logical dump of `core.users`, `user_tombstones` and `user_migration_state`. Then drop `users` in MySQL. Remove the dual-write, outbox and MySQL read paths, the flags, and the lint exception for `no-raw-users-sql` that the migration added.
  - **State:** backup storage.
  - **If it fails:** restore from the dump. The drop cannot be undone otherwise.

## Open decisions for the owner

- The 30-day retention period before dropping MySQL (step 14).
- Legal review of keeping erased user ids in `user_tombstones`.
- Whether PG reads need a read-your-writes check (step 7).
- PG high availability and PITR must be in place before step 10.