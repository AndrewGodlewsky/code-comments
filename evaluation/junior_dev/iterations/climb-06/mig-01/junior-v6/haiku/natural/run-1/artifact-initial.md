# Plan: move `users` from MySQL 8 to Postgres 16 without downtime

## Design decisions

- **Repair is an outbox in MySQL.** Each users write also inserts an outbox row in the same MySQL transaction, holding the committed row snapshot. The inline Postgres apply is an optimisation. A relay drains the outbox until Postgres has it, with no retry limit and no dependence on Redis or `jobs:dead`. A slow reconciliation sweep catches anything the outbox misses.
- **Tombstones block resurrection.** Postgres keeps a `users_tombstones` table (id and timestamp only). Every copy into Postgres takes a per-id advisory lock, checks the tombstone, and applies the version guard. Erasure writes the tombstone and deletes the row in one Postgres transaction.
- **Every copy obeys the version rule.** Inserts use `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. The same rule applies in both directions after the switch.
- **Control rows fence the switch.** Each database holds a `users_migration` row (`sot`, `epoch`). A primary write to a database checks in the same transaction that this database is the source of truth. A stale instance therefore gets a retryable 503 and cannot split the data, even if a flag has not propagated yet.
- **Ids come from one owner at a time.** At each switch, the new source of truth sets its id generator past the maximum id on both sides, while writes are paused.
- **Long-running work is not on `app.jobs`.** Backfill and the relay run as leased workers (a Postgres or MySQL advisory lock, or `SKIP LOCKED`), because `jobs:dead` is never processed and Redis enqueue can fail.

## Phase 0: preparation (no user-visible change)

- [ ] **1. Create the Postgres schema in `pg-core`.**
  - Starts: a change ticket approved by the owner.
  - Changes: `users` with the same columns (`id BIGINT PRIMARY KEY`, `version INT`, `updated_at timestamp(3)` in UTC). Email is unique on `lower(email)` to match MySQL's case-insensitive collation. Also `users_tombstones(id PRIMARY KEY, erased_at)`, `users_backfill_state`, `users_compare_runs`, `users_sync_outbox` (for the reverse direction later) and `users_migration(id=1, sot='mysql', epoch=1)`.
  - State: `pg-core`.
  - If it fails: drop and recreate the empty schema. Nothing reads it yet.

- [ ] **2. Create the MySQL outbox and control tables in `core`.**
  - Starts: step 1 done.
  - Changes: `users_sync_outbox(seq AUTO_INCREMENT, user_id, op ['upsert'|'delete'], version, row_json, created_at)` and `users_migration(id=1, sot='mysql', epoch=1)`. Also `users_tombstones` for the reverse direction.
  - State: `mysql-core-primary`.
  - If it fails: it is additive. Drop the tables and retry.

- [ ] **3. Deploy the code with every migration flag off.**
  - Starts: normal deploy.
  - Changes: `UserRepository` writes an outbox row in every write transaction, always, so no write is missed between deploy and dual writes. Reads are routed by flag `users_read_source` (default `mysql`). Writes are routed by flag `users_write_mode` (default `mysql`). Each instance exports `app_build_info{version}`.
  - Checks: insert latency for the outbox row at about 400 writes/s, measured in staging.
  - If it fails: roll back the deploy. The old path is unchanged apart from the extra insert.

## Phase 1: dual writes and repair

- [ ] **4. Turn on dual writes (flag `users_dual_write`).**
  - Starts: step 3 is on every instance, and the flag is switched on.
  - Changes: a write commits to MySQL with its outbox row, then applies inline to Postgres with a 200 ms timeout (my choice). On success the outbox row is deleted. On failure the request still succeeds and the row stays. The relay (a single leader, batches of 500 in `seq` order) drains the outbox to Postgres. Erasure rows are handled in step 6.
  - Gate before step 5: `app_flag_value{flag="users_dual_write"}` is 1 on every instance, and `app_build_info` is the release version on every instance. The flag alone is not enough.
  - State: the outbox in MySQL.
  - If it fails: switch the flag off. Outbox rows keep accumulating and drain once it is back on. Alert if the oldest outbox row is older than 5 minutes.

- [ ] **5. Backfill (resumable).**
  - Starts: step 4 gate passed. A single leader takes the lease.
  - Each batch:
    1. Read the replica's lag directly. If it is unknown or above 5 s, sleep 5 s and check again.
    2. Read at most 2,000 rows from the replica with `WHERE id > :cursor ORDER BY id LIMIT 2000`.
    3. In one Postgres transaction, for each id take the advisory lock, skip tombstoned ids, upsert with the version guard, and update `users_backfill_state.cursor_id`.
    4. Commit, then pause briefly (100 ms, my choice) to share the replica with reporting.
  - State: `users_backfill_state` in `pg-core`, updated in the same transaction as the batch, so the cursor is never ahead of the data.
  - If it fails: after a crash, restart the worker. It resumes after the last committed cursor, and the one batch in flight is redone safely because the copy is idempotent. Postgres errors are retried with backoff and the cursor does not move.

- [ ] **6. Continuous repair sweep, with erasure handling.**
  - Starts: step 4 is on. It runs alongside step 5.
  - Changes:
    - Compare id chunks of 2,000 by a hash of the row contents (UTC timestamps) between the replica and Postgres.
    - Re-read any mismatch on the MySQL primary and check the outbox before acting.
    - If MySQL has a newer or missing row, copy it with the version guard.
    - If Postgres has a row that MySQL lacks (and there is no pending outbox row), delete it and write a tombstone.
    - If Postgres has a higher version than MySQL, do not overwrite. Alert.
  - Erasure: the erasure job deletes the user in MySQL, deletes that user's pending `upsert` outbox rows (they hold personal data), and inserts a `delete` outbox row, all in one MySQL transaction. The relay and the inline path then write the tombstone and delete the row in Postgres.
  - Email conflict: if a new user takes an email still held by an erased user whose delete has not reached Postgres, the copy fails on the unique index. The relay then applies that owner's pending delete and retries. If the owner still exists in MySQL, record a conflict and alert.
  - State: `users_compare_runs` and the sweep cursor in `pg-core`.
  - If it fails: the sweep is idempotent. Investigate alerts and rerun.

- [ ] **7. Full comparison gate.**
  - Starts: `users_backfill_state` is `done`, the outbox is empty, and one full sweep has passed.
  - Pass rule: a full run over all ids in both tables finds zero mismatches after the primary re-check. A mismatch counts only if it persists on the primary and no outbox row exists for that id.
  - State: `users_compare_runs`.
  - If it fails: repair, then rerun the full comparison from the first id. A partial rerun does not pass the gate.

## Phase 2: reads on Postgres

- [ ] **8. Move reads to Postgres in steps: 1%, 10%, 50%, 100%.**
  - Starts: step 7 passed.
  - Changes: `flags.enabled_for("users_read_source", user_id)` decides per user, so the answer is sticky. Each PG read has a short timeout. Any error or timeout falls back to the MySQL replica in the same request, so reads never fail.
  - Known risk: a PG read can be stale by the outbox backlog. A stale read can only cause a `StaleWrite`, because writes still check versions in MySQL. Hold each ramp step until outbox lag p99 is under 1 s.
  - If it fails: set the flag back to `mysql`. No data changes.

- [ ] **9. Soak: reads 100% on Postgres for at least 3 days.**
  - Starts: every instance reports `users_read_source=pg` and the 100% step is in place.
  - The clock starts then. Any fallback to MySQL or any flag change resets it.
  - If it fails: move reads back to `mysql`. This needs no write pause, because reads do not affect writes. The clock restarts on the next attempt.

## Phase 3: source-of-truth switch to Postgres (writes paused at most 90 s)

- [ ] **10. Planned switch to Postgres as source of truth.**
  - Starts: step 9 passed, and all of these hold:
    - the outbox is empty on both sides;
    - replica lag is normal;
    - a full comparison run finished within the last 24 hours with zero mismatches (my choice of freshness).
  - Runbook:
    - **(a)** Set `users_write_mode=paused`. Writes get a 503 with `Retry-After`. Wait until every instance reports `paused` (about 30 s).
    - **(b)** Drain. Wait until the MySQL-to-Postgres outbox is empty. If 60 s pass without that, set `users_write_mode=mysql` and stop. Nothing has changed yet.
    - **(c)** Commit point, in MySQL: lock `users_migration`, set `sot='pg'`, `epoch+1`.
    - **(d)** Postgres: `setval(users_id_seq, GREATEST(max id on Postgres, max id on MySQL) + 1000000)`, then set `users_migration` to `sot='pg'`, `epoch+1`. Start the reverse outbox.
    - **(e)** Set `users_write_mode=pg`. Wait until every instance reports `pg` (about 30 s). Writes now go to Postgres first, then to MySQL.
  - Pause budget: about 30 s + drain + 30 s. Target 60 s, alert at 75 s, hard limit 90 s.
  - State: the control rows in each database, and the flag.
  - If it fails: before (c), set mode back to `mysql` with no source change. After (c), roll forward by rerunning (d) and (e). Do not roll back, because the control row already fences MySQL.

- [ ] **11. Reverse sync and rollback path (up to 14 days after step 10e).**
  - Writes go to Postgres, then to MySQL inline, with the reverse outbox in Postgres, relayed to MySQL with the version guard. Erasure in this phase also writes a tombstone to MySQL.
  - Rollback to MySQL: set `users_read_source=mysql`, then run the step 10 runbook with the roles swapped (`sot='mysql'`, MySQL `AUTO_INCREMENT` set past both maxima). The pause is at most 90 s.
  - If it fails: same rules as step 10.

- [ ] **12. Hold for at least 14 days after step 10e.**
  - This is the rollback window. The clock restarts after any rollback and re-promotion.

## Phase 4: retire MySQL

- [ ] **13. Switch to Postgres-only writes.**
  - Starts: at least 14 days after step 10e. The reverse outbox is empty, and a full comparison of the reverse direction shows zero mismatches.
  - Changes: set flag `users_reverse_sync` off on every instance, then revoke INSERT, UPDATE and DELETE on `core.users` for the app role. This does not change the source of truth, so no pause is needed. It is irreversible in practice.
  - If it fails: turn the flag back on, and re-grant the privileges while MySQL is still in place.

- [ ] **14. Drop the MySQL `users` table.**
  - Starts: at least 7 days after step 13 (my proposal). Take a final backup first.
  - Changes: drop `users`, `users_sync_outbox` and `users_tombstones` in MySQL.
  - If it fails: restore from the backup.

## Open items for the owner

- **Tombstone retention:** the tombstone keeps only an id. Legal should confirm that this is acceptable under the erasure policy, and whether backups need the same treatment.
- **Numbers I chose:** 200 ms inline timeout, 60 s drain limit, 75 s alert, 1,000,000 id headroom, 24-hour freshness for the comparison, and 7 days before the drop. These need confirming.
- **Propagation assumption:** the pause budget assumes the 30 s flag refresh. If the refresh interval changes, recheck the 90 s budget.
- **Relay capacity:** a single relay must keep up with about 400 writes/s with the outbox. Measure this in staging before step 4.