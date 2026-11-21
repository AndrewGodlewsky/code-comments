# Plan: move `users` from MySQL 8 to Postgres 16

## Design decisions

- **Repair is a durable outbox, not the job queue.** Redis `enqueue` can raise, and `jobs:dead` is never processed, so jobs can't guarantee repair. Each write adds a row to a `users_sync_outbox` table in the same transaction as the write, in whichever database is currently the source of truth. A long-running sweeper process retries each outbox row forever. A Postgres failure therefore costs only a retry.
- **Copy rule.** Every copy (dual write, backfill, repair) goes through one function, `apply_copy(row)`. It runs in one target transaction under `pg_advisory_xact_lock(id)` (the MySQL equivalent is `GET_LOCK`).
  - If a tombstone exists for the id, it does nothing.
  - Otherwise it runs `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
  - Batches lock ids in sorted order. Set `max_locks_per_transaction` to at least 4096.
- **Deletes.** `delete(id)` removes the row and inserts a tombstone (`id`, `deleted_at`) in the target. It does this even when the row is absent, so a late copy cannot bring the row back. Tombstones live in a `users_tombstones` table in each database, and an id is never reused. The sweeper treats "row absent on the source" as "deleted".
- **Switch coordination uses a fence in the database, not the flag.**
  - Each database has a one-row `users_write_state(owner, epoch)`.
  - Every client write transaction first runs `SELECT owner ... FOR SHARE`. If `owner` is not this database, the write returns a retryable 503.
  - A switch takes an exclusive lock on that row. It waits for in-flight writers and blocks new ones, so a stale 30-second flag cache cannot cause a write to the wrong database.
  - The `users_source` flag only routes requests. A stale instance gets 503s until its flag refreshes (30 seconds at most), not wrong writes.
- **Reads fall back.** A Postgres read that errors, times out after 300 ms, or finds no row falls back to the MySQL replica. During the migration, reads never fail on a single-database outage.
- **Backfill progress lives in Postgres.** It is a one-row table, `migration_backfill(last_id)`, updated in the same transaction as each batch.
- **New ids after the switch.** At the switch, the Postgres sequence is set to `max(MySQL AUTO_INCREMENT counter, max PG id) + 100000`. Mirrored copies keep their explicit ids. On rollback, MySQL's counter is checked against the maximum id and raised if needed.
- **Migration clocks.** All timestamps and gate results are kept in `migration_state` in Postgres: `dual_write_all_since`, `reads_100_since`, `source_pg_since`, and compare results.

## Steps

### Phase 0: prepare (nothing user-visible)

- [ ] **0. Create schemas.**
  - **Starts:** a migration deploy.
  - **Changes:**
    - Postgres:
      - `users` has the same columns. `email` uses `citext` with a unique constraint, because MySQL's unique email is case-insensitive and plain Postgres text would allow duplicates. `id` is `BIGINT` with a sequence that stays unused for now.
      - Also `users_tombstones`, `users_sync_outbox`, `users_write_state(owner='mysql')`, `migration_backfill`, `migration_state`, and `migration_compare_runs`.
    - MySQL: new `users_sync_outbox`, `users_tombstones` and `users_write_state(owner='mysql')`.
  - **State:** the tables themselves.
  - **If it fails:** the DDL is idempotent (`IF NOT EXISTS`), so rerun it. Nothing reads the new tables yet.

- [ ] **1. Deploy "code A" with everything flagged off.**
  - **Starts:** a rolling deploy, with `users_mirror=false`, `users_source=mysql`, `users_read_pg_pct=0`.
  - **Changes:** `UserRepository` becomes symmetric (source and target chosen by `users_source`).
    - Write path:
      1. Open a transaction on the source and check the fence.
      2. Write the row and, if `users_mirror` is on, an outbox row in that same transaction.
      3. Commit.
      4. Within 500 ms, call `apply_copy` on the other database.
      5. On success, delete the outbox row by `seq`. On any error, swallow it, log it and bump a metric. The request still succeeds.
    - Read path: `get` uses the `users_read_pg_pct` flag, bucketed by `enabled_for(name, user_id)`, with the fallback described above.
    - Also deployed: the sweeper, the backfill runner, the `compare` tool and `switchctl` (the switch tool in step 8), as separate worker processes.
    - The sweeper runs every second. It picks outbox rows older than 5 seconds and deduplicates by id. It reads the current row from the source primary and calls `apply_copy`, or the delete with tombstone if the row is absent. It backs off per row and never gives up.
    - Email conflict: if the target has a different id with the same email, the sweeper checks that other id on the source. If the other row is gone, it deletes it in the target. If its email changed, it repairs that id first and then retries.
  - **State:** none new.
  - **If it fails:** roll back the deploy. The flags are off, so behavior is unchanged.

### Phase 1: dual writes and backfill

- [ ] **2. Turn on dual writes.**
  - **Starts:** a staging drill passes, in which Postgres is blocked, writes still succeed, and the outbox drains after unblocking. Then `users_mirror=true`.
  - **Changes:** every write now also lands in Postgres, or in the outbox if that fails.
  - **Gate G1 (all instances dual-writing):** `app_flag_value{flag="users_mirror"}` is 1 on every instance, the number of series equals the number of deployed code-A instances, and one more minute has passed. Record `dual_write_all_since`.
  - **State:** the outbox in MySQL, plus the flag.
  - **If it fails:** the immediate Postgres call has its own kill switch, `users_inline_copy=false`, which skips the inline copy but keeps writing outbox rows, so repair continues. Do not set `users_mirror=false` after G1. If it must be turned off, writes made while it was off are unmirrored, so reset `migration_backfill.last_id` to 0 and redo G1.

- [ ] **3. Backfill.**
  - **Starts:** `backfill` refuses to run unless G1 holds. It rechecks G1 every minute and stops if it ceases to hold.
  - **Changes:** one runner at a time, guarded by a Postgres advisory lock.
    - Loop: wait until `mysql_replica_lag_seconds` is 5 or less (poll every 5 seconds, so it pauses whenever lag is above 5). Then read `WHERE id > last_id ORDER BY id LIMIT 2000` from the replica.
    - In one Postgres transaction, `apply_copy` the rows and set `last_id` to the batch's last id. Rows that hit an email conflict are skipped and added to the MySQL outbox for the sweeper.
    - Stale replica rows are harmless: the version rule blocks old versions, and tombstones block deleted rows. A row deleted on MySQL whose Postgres delete failed is removed by the outbox repair.
  - **State:** `migration_backfill.last_id`, committed atomically with each batch.
  - **If it fails:**
    - A crash: the supervisor restarts it and it continues after `last_id`.
    - Postgres errors: it retries the same batch, which is idempotent.
    - It ends when a batch comes back empty. Record `backfill_done_at`.

### Phase 2: verify and move reads

- [ ] **4. Full comparison.**
  - **Starts:** backfill is done and the oldest outbox row is under 1 minute old.
  - **Changes:** `compare` walks both tables in primary-key chunks, in both directions, so it finds missing rows, extra rows and any differing column. Replica reads are gated by lag. Each candidate mismatch is rechecked against the MySQL primary and Postgres after 60 seconds, and ids with a pending outbox row are retried until they clear.
  - **State:** a row in `migration_compare_runs` with the confirmed mismatch count.
  - **Gate G2:** a full run that finishes with 0 confirmed mismatches.
  - **If it fails:** a mismatch count above 0 enqueues those ids to the outbox (repair), and the run is declared failed. Start a new full run until one is clean. A crash restarts the run.

- [ ] **5. Ramp reads to Postgres.**
  - **Starts:** G2 holds. Then raise `users_read_pg_pct` through 1, 10, 50 and 100. Each stage is held until error rate, latency and the fallback-to-MySQL rate look normal.
  - **Changes:** reads by user id move to Postgres. The same user always gets the same answer.
  - **State:** the flag only.
  - **If it fails:** lower the percentage. It takes effect within 30 seconds, and reads never fail because of the fallback.

- [ ] **6. Hold at 100% reads for at least 3 days.**
  - **Starts:** the metric shows 100 on every instance. Set `reads_100_since`.
  - **Changes:** nothing. A fresh `compare` runs daily and must stay at 0.
  - **If it fails:** any drop below 100% clears `reads_100_since` and restarts the 3 days. A non-zero daily compare is repaired and rerun, and the next step waits for a clean run.

### Phase 3: change the source of truth

- [ ] **7. Pre-checks.**
  - **Starts:** 3 days or more at 100%, G2 clean within the last 24 hours, the oldest outbox row under 10 seconds, and a staging dry run of the switch and the rollback.
  - **Changes:** nothing. The checks also confirm the application's MySQL account can write `users` with explicit ids.
  - **If it fails:** do not proceed.

- [ ] **8. Switch to Postgres (write pause of at most 90 seconds).**
  - **Starts:** an operator runs `switchctl --to postgres`. It holds a lease row in `migration_state` so only one run exists.
  - **Changes, in order:**
    1. T0: set the MySQL fence `owner='switching'`. The exclusive lock waits for in-flight writers (`lock_wait_timeout=5s`). Writes now return a retryable 503.
    2. Drain: force the sweeper to empty the MySQL outbox. Once it is empty, Postgres holds every committed MySQL write.
    3. Set the Postgres sequence as described above.
    4. Commit point: set the MySQL `owner='postgres'`, then the Postgres `owner='postgres'`, and then the flag `users_source=postgres`. The mirror direction is now Postgres to MySQL, with the outbox in Postgres and tombstones written to MySQL.
    5. Instances pick up the flag within 30 seconds. Until then they get 503s, never writes to the wrong database.
  - **State:** the two `users_write_state` rows (authoritative), the flag, and `source_pg_since` recorded at the commit point.
  - **If it fails:**
    - Before the commit point: if the drain is not finished 40 seconds after T0, or any step errors, `switchctl` sets the MySQL fence back to `owner='mysql'`. Writes resume at once, because the fence is read in the transaction and needs no flag propagation.
    - After the commit point: the worst case is about 40 seconds plus a 30-second flag refresh, which is under 90 seconds. If the pause is longer than expected, use the rollback in step 9.

- [ ] **9. Rollback window (at least 14 days) and rollback procedure.**
  - **Starts:** the switch commits.
  - **Changes:** every write commits to Postgres first and is mirrored to MySQL through the same repair machinery, so MySQL stays complete. Run `compare` daily. Alert if the oldest outbox row is over 5 minutes old.
  - **Rollback (any time before step 10):** `switchctl --to mysql`.
    1. Fence Postgres with `owner='switching'`.
    2. Drain the Postgres outbox into MySQL.
    3. Check that the MySQL `AUTO_INCREMENT` is above the maximum id, and `ALTER` it if not.
    4. Set the MySQL `owner='mysql'`, then the flag `users_source=mysql`. Mirroring then runs MySQL to Postgres again.
    - This pause follows the same 90-second budget and the same abort-before-commit rule as step 8. Reset `source_pg_since` if a later switch happens.
  - **If it fails:** if MySQL is down, rollback waits. Nothing is lost because the Postgres outbox keeps accumulating.

### Phase 4: finish

- [ ] **10. Stop mirroring to MySQL (writes become Postgres-only).**
  - **Starts:** at least 14 days since `source_pg_since` with no rollback in between, a clean `compare` from the last 24 hours, and an empty Postgres outbox. Take a MySQL snapshot first.
  - **Changes:** set `users_mirror=false`. Wait until every instance shows it, then 2 more minutes. Stop the sweeper once the outbox is empty. Revoke the application's write grants on MySQL `users` and set `users_write_state.owner='retired'`.
  - **State:** the flag and the grants. This is the point after which rolling back to MySQL needs a restore.
  - **If it fails:** before the grants are revoked, set `users_mirror=true`. Run `compare --repair` to re-enqueue any ids that changed while mirroring was off, then wait for a clean run before retrying.

- [ ] **11. Deploy "code B" (remove MySQL paths).**
  - **Starts:** step 10 is complete.
  - **Changes:** `UserRepository` uses Postgres only. The mirror, outbox, fence, read-percentage flags and fallback code are deleted. The Postgres `users_tombstones` table is no longer needed once copying has stopped.
  - **If it fails:** roll back the deploy. The old paths still exist in the MySQL read-only state.

- [ ] **12. Retire the MySQL table.**
  - **Starts:** code B has been deployed and stable for at least 7 days. A check of `performance_schema` shows no queries on `users`, including from reporting jobs on the replica.
  - **Changes:** rename `core.users` to `users_retired`, wait a week, then `DROP TABLE`. Also drop the MySQL helper tables.
  - **If it fails:** rename it back. The drop is the only irreversible action, so do it last.
