# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Design decisions

- **Durable outbox for repair.** Every MySQL write also inserts an outbox row in the same MySQL transaction, and a dedicated relay process applies it to Postgres.
  - The existing Redis `jobs` queue is not used for repair. `enqueue` raises when Redis is down, a crash between commit and enqueue loses the repair, and dead-lettered jobs in `jobs:dead` are never processed. Any of these would leave a manual step.
- **Switch coordination.**
  - Each database holds a `users_control` row (`accepting_writes`, `epoch`). Every write transaction takes `SELECT ... FOR SHARE` on that row in the database it writes to.
  - Closing a database is an `UPDATE` of that row. It waits for in-flight writers, and every later writer gets a retryable 503.
  - The 30-second flag skew therefore cannot cause a split-brain write. Stale instances only get 503s.
- **Backfill progress** lives in Postgres, in the same transaction as each batch's rows.
- **New ids** come from a Postgres sequence, set above MySQL's AUTO_INCREMENT counter during the switch pause.
- **Version rule everywhere.** One function per direction does the copy.
  - Postgres uses `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
  - MySQL uses the equivalent `ON DUPLICATE KEY UPDATE` with per-column `IF(VALUES(version) > version, ...)`.
- **Erasure safety.**
  - Each store has a `users_erased(id)` table that holds no personal data. Ids are never reused.
  - Every copy runs in a transaction that first takes a per-id lock and then checks `users_erased`.
    - Postgres: `pg_advisory_xact_lock` on `hash(id) % 256` stripes, taken in sorted order.
    - MySQL: `SELECT ... FROM users_erased WHERE id=? FOR SHARE`, which also takes a gap lock.
  - The delete path inserts the tombstone and deletes the row under the same lock.
  - Whatever order a delete and a stale copy arrive in, the row cannot come back.

Flags used:
- `users.dual_write` (boolean)
- `users.read_source` (percentage of reads sent to Postgres)
- `users.writer` (`mysql` or `postgres`)
- `users.mirror_to_mysql` (boolean)

## Steps

- [ ] **Step 0. Monitoring and alerts first.**
  - Starts when: the work begins.
  - Changes: adds dashboards and pages for the following.
    - `users_outbox` oldest-row age (page above 5 minutes) and the equivalent for `pg_outbox`.
    - Postgres write error rate and fallback-read rate.
    - `mysql_replica_lag_seconds`.
    - A count of instances per `app_flag_value{flag=...}` value, compared with the running instance count.
  - State: metrics only.
  - If it fails: do not continue. Every later gate depends on these.

- [ ] **Step 1. Additive schema, no behaviour change.**
  - Starts when: step 0 is done. It is a manual migration run.
  - Changes: creates the following tables.
    - **MySQL:**
      - `users_outbox(seq PK auto, user_id, op, row_json, attempts, created_at)`
      - `users_erased(id PK, erased_at)`
      - `users_control(id=1, accepting_writes='yes', epoch)`
    - **Postgres:**
      - `users`, same columns, PK `id`, unique `email`, `updated_at timestamptz(3)`
      - `users_erased`
      - `users_control(accepting_writes='no')`
      - `users_backfill_progress(id=1, last_completed_id=0, run_id)`
      - `pg_outbox`, the mirror of `users_outbox`
      - `users_id_seq`, created but unused
  - State: schema only.
  - If it fails: drop the new tables. Nothing reads them yet.

- [ ] **Step 2. Deploy the new `UserRepository` with all flags off.**
  - Starts when: step 1 is verified. It is a rolling deploy.
  - Changes: the repository gains these paths, all dormant except the fence check.
    - **Fence check:** each MySQL write transaction runs `FOR SHARE` on `users_control` and raises a retryable 503 if `accepting_writes` is not `yes`.
    - **Dual write:** when `dual_write` is on, the transaction also reads back the full row inside the transaction and inserts an outbox row with the full row payload. After commit it tries `copy_to_pg(row)` inline with a 300 ms timeout and swallows every exception. On success it deletes the outbox row. A circuit breaker skips the inline attempt for 10 seconds after repeated failures. The request never fails because of Postgres.
    - **Delete:** deletes in MySQL, inserts into `users_erased`, and writes an outbox `delete` op, all in one transaction.
    - **Postgres read path:** `read_source` chooses Postgres by `enabled_for("users.read_source", user_id)`. On a Postgres error, timeout or miss, it falls back to the MySQL replica, so reads cannot fail.
    - **Postgres-first write path** for `writer=postgres`, used in step 10. It includes the PG fence, the `pg_outbox`, and `mirror_to_mysql`.
  - State: code and flags only (defaults are off or `mysql`).
  - If it fails: roll the deploy back. The schema is additive and unused.
  - Do not go on until every instance runs the new build. Instances still on old code would write without outboxes.

- [ ] **Step 3. Deploy the relay and comparator workers.**
  - Starts when: step 2 has finished everywhere. It is a new worker deployment, separate from the Redis job workers.
  - Changes:
    - **MySQL-to-Postgres outbox relay.**
      - It claims rows with `SELECT ... ORDER BY seq LIMIT 200 FOR UPDATE SKIP LOCKED`, applies each with `copy_to_pg` (or a delete under the tombstone lock), then deletes the outbox row.
      - Failures increment `attempts` and retry with capped backoff. There is no dead-letter, so the row stays until the retry succeeds or an alert fires.
      - An email unique-violation counts as a failure and is retried, because the conflicting row is normally a pending delete that is earlier in sequence.
    - **Reverse relay.** `pg_outbox` to MySQL, with the version rule and MySQL tombstones. It is idle for now.
    - **Backfill and comparator.** Deployed but not started.
  - State: outbox tables in the source databases (the MySQL one for this direction).
  - If it fails: scale to zero. Nothing depends on them yet.

- [ ] **Step 4. Turn on dual writes.**
  - Starts when: step 3 is healthy. The trigger is `users.dual_write=true`.
  - Changes: from now on, every MySQL write also reaches Postgres.
  - Gate: do not call this done until the instance count with `app_flag_value{flag="users.dual_write"}=1` equals the running instance count (at least 30 seconds, normally within about 35).
    - The completion timestamp is stored in `users_backfill_progress` as `dual_write_confirmed_at`.
    - If the instance count is ever short, wait. Instances started later read the flag at startup.
  - State: flag, plus outbox rows in MySQL.
  - If it fails (errors or load): set the flag to `false`.
    - The relay still drains the outbox that exists.
    - Writes made while it was off will not reach Postgres, so if backfill had started, reset its progress to 0 and require a fresh comparison afterwards.

- [ ] **Step 5. Start the backfill.**
  - Starts when, all of:
    - Step 4's gate is met.
    - At least 10 minutes have passed since `dual_write_confirmed_at`. This lets the replica catch up with any deletes made just before the flag landed.
    - `mysql_replica_lag_seconds` is below 5.
  - Changes: one backfill worker, guarded by a Postgres advisory lease, loops:
    - Check lag. If it is above 5 seconds, sleep and recheck, reading nothing.
    - Read the next batch from `mysql.replica`: `WHERE id > :last_completed_id ORDER BY id LIMIT 2000`.
    - In one Postgres transaction:
      - take the stripe locks;
      - upsert all rows with the version rule, skipping ids present in `users_erased`;
      - set `last_completed_id` to the batch's last id.
    - Commit and repeat. A batch that returns fewer than 2000 rows marks the backfill complete.
  - State: `users_backfill_progress` in Postgres. The progress update commits atomically with the batch, so a crash mid-batch rolls back both. On restart the worker resumes at `last_completed_id`, not at 0.
  - If it fails: a crash, replica lag, or a Postgres error simply resumes. The upserts are idempotent, and rows that dual writes already updated are never regressed by the version rule.

- [ ] **Step 6. Full comparison until clean.**
  - Starts when: the backfill is complete and the outbox backlog is below 60 seconds. Run the comparator.
  - Changes: it walks the id space in 2,000-id chunks on the MySQL replica (same lag pause) and on Postgres, comparing row checksums over all columns.
    - Each mismatching row is rechecked 60 seconds later against the MySQL primary, by primary key, with the outbox row for that id out of the way.
    - Mismatches that persist are classified.
      - **Missing in Postgres, or older version in Postgres:** `copy_to_pg`.
      - **In Postgres but absent in MySQL and not in `users_erased`:** delete it from Postgres and add the tombstone. The primary check ensures a brand-new row is not removed.
      - **A newer version in Postgres than in MySQL:** this should be impossible. Page a human and stop; it is a bug.
  - Done when: a complete pass finds zero persistent mismatches and made zero repairs. Any repair makes that pass non-clean, so run the comparison again.
  - State: comparator results and run id in Postgres.
  - If it fails: fix the cause and rerun. The comparator runs nightly until MySQL is dropped. A non-zero result resets the gates below.

- [ ] **Step 7. Move reads in stages.**
  - Starts when: step 6 has a clean pass. The trigger is `users.read_source` at 1, 10, 50, then 100, with at least 1 hour per stage.
  - Changes: reads for the user ids in that bucket come from Postgres, falling back as set in step 2.
  - Each stage needs:
    - Postgres read errors and fallback rate low.
    - p99 latency within the target.
    - The nightly comparator still clean.
  - State: the flag.
  - If it fails: set the percentage back to 0, or to the previous stage. No data moves, and the fallback means reads never fail.

- [ ] **Step 8. Soak at 100% reads for at least 3 days.**
  - Starts when: every instance reports 100 in `app_flag_value{flag="users.read_source"}`. Record the timestamp.
  - Changes: nothing. Writes still go to MySQL first.
  - The clock restarts if the flag drops below 100 on any instance, or if the comparator reports a persistent mismatch.
  - State: timestamp in the runbook ticket and in `users_control` as `reads_100_since`.
  - If it fails: fix and restart the 3 days.

- [ ] **Step 9. Pre-switch readiness check.**
  - Starts when: step 8 has run for 72 hours or more.
  - Changes: nothing. Check that:
    - A comparator pass completed within the last 24 hours with zero mismatches.
    - Both outbox ages are small.
    - `users.mirror_to_mysql=true` has been set ahead of time (harmless while the writer is MySQL).
    - The reverse relay is healthy.
    - The switch script has been rehearsed in staging, including the abort path.
  - If it fails: do not switch.

- [ ] **Step 10. Switch the source of truth to Postgres (write pause at most 90 seconds).**
  - Starts when: step 9 passes. A switch script is run by an operator, with a watchdog process alongside it.
  - Changes, with times measured from the start of the pause:
    1. **T+0.** In MySQL, `UPDATE users_control SET accepting_writes='no', epoch=epoch+1`. This waits for in-flight writers. Immediately set `users.writer=postgres`. Writes now get a 503, while reads keep working throughout.
    2. **T+0 to T+30.** The flag reaches all instances within 30 seconds. Instances with a stale flag that hit MySQL get a 503 from the fence. Instances with the new flag hit the Postgres fence, which is still closed, and also get a 503.
    3. Wait until `users_outbox` is empty (the relay is still running). MySQL is closed, so nothing new can arrive.
    4. Set the Postgres sequence: `setval('users_id_seq', GREATEST(MySQL AUTO_INCREMENT, max(id) in Postgres, current value) + 1,000,000)`. Read the MySQL counter with `SET SESSION information_schema_stats_expiry=0`, or `ANALYZE TABLE` first.
    5. In Postgres, set `accepting_writes='yes'`. Writes on Postgres now succeed, and creates take their ids from `users_id_seq`.
    6. Stale-flag instances recover by about T+35 at the latest.
  - State: `users_control` rows in both databases, plus the `users.writer` flag. The script records its steps in these rows, so a rerun after a crash resumes.
  - If it fails: the watchdog aborts if Postgres is not open by T+45. It re-opens MySQL, sets the flag back to `mysql`, and Postgres never accepted a write.
    - Instances with the new flag cached get a 503 from the Postgres fence for up to 30 more seconds, so the pause ends by about T+75, under the 90-second limit.
    - Postgres is never opened before the drain is verified.

- [ ] **Step 11. Run with Postgres as source and MySQL as a live mirror (day 0 to day 14 or more).**
  - Starts when: step 10 completes. This is the rollback window.
  - Changes:
    - Writes commit to Postgres first, together with a `pg_outbox` row.
    - The reverse relay applies them to MySQL, keeping `users_outbox` unused.
    - A MySQL failure never fails the request.
    - A failed Postgres write now does fail the request, because Postgres is the source of truth.
    - Deletes are mirrored with a tombstone in MySQL. Copies into MySQL honour the version rule and the tombstone check.
    - Ids created now carry explicit values into MySQL, which raises its AUTO_INCREMENT counter, so a rollback cannot reuse ids.
  - Watch: `pg_outbox` age (alert above 5 minutes) and the comparator, which runs against Postgres and the MySQL replica.
  - State: `pg_outbox` in Postgres, with the same retry behaviour as before.
  - If a problem appears: see step 12.

- [ ] **Step 12. Rollback to MySQL (only before step 13).**
  - Starts when: an operator decides to roll back, and `pg_outbox` age is under about 10 seconds.
  - Changes: the same procedure as step 10, mirrored.
    1. Close Postgres (`users_control` set to `no`).
    2. Set `users.writer=mysql`.
    3. Drain `pg_outbox` to MySQL.
    4. Open MySQL.
    - Writes pause for at most 90 seconds, and no write is lost because both sides are fenced and drained.
    - Afterwards, MySQL-to-Postgres dual writes resume through `users_outbox`, and the comparator reruns.
    - The 14-day clock and the 3-day soak restart before the next switch.
  - If it fails: the watchdog aborts and re-opens Postgres, the same as in step 10.
  - If only Postgres reads are the problem, set `read_source=0`. Writes are unaffected.

- [ ] **Step 13. Stop mirroring to MySQL (point of no return).**
  - Starts when, all of:
    - At least 14 days have passed since step 10 completed (or since the last rollback's switch).
    - The comparator is clean.
    - `pg_outbox` is empty.
    - There is explicit sign-off.
  - Changes:
    - Set `users.mirror_to_mysql=false`.
    - Wait until all instances report it.
    - Drain `pg_outbox` and stop the reverse relay.
    - Revoke the app and relay users' write grants on `core.users` to catch any stray writer.
  - There is no pause, because the source of truth does not change.
  - State: flag and grants. From here, rollback to MySQL is impossible.
  - If it fails: leave `mirror_to_mysql` on.
    - Do not re-enable it after a gap without first running a one-time repair that copies Postgres to MySQL.

- [ ] **Step 14. Retire MySQL.**
  - Starts when: step 13 has been stable for at least 7 days. Drop the MySQL table only after this step.
  - Changes:
    - First rename `users` to `users_archived` and take a final snapshot.
    - After 7 days with no errors, drop `users_archived`, `users_outbox`, `users_erased` and `users_control` in MySQL.
    - Remove the MySQL paths, the fence code and the flags from `UserRepository`, and remove the outbox, backfill and comparator workers.
  - Erased users: the archive holds users erased after step 13, so keep it only as long as the GDPR erasure deadline allows and purge its backups on the same schedule.
  - If it fails: rename the table back. The code no longer reads it, so nothing else is affected.
