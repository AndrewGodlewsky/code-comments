# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Summary

Today every read and write of `users` goes through `UserRepository`. Writes go to the MySQL 8 primary. Reads go to the MySQL replica. The Postgres 16 cluster (`pg-core`) is empty and the app already holds a connection pool to it. The migration logic goes into `UserRepository`.

The main flow has five phases.

1. Add empty tables and deploy code with every flag off.
2. Turn on dual writes: each write commits to MySQL, then is copied to Postgres.
3. Backfill old rows and compare the two tables until they match.
4. Move reads to Postgres in stages, then soak at 100% for 3 days.
5. Switch the source of truth to Postgres with a pause of at most 90 seconds. Keep MySQL as a live mirror for 14 days for rollback. Then stop mirroring and drop MySQL.

Every copy into Postgres follows one rule, the version rule. A copy that fails is recorded in a durable outbox table, so repair is automatic and needs no manual step. Switching the source of truth is guarded by a gate on each database, so slow flag updates cannot cause two databases to accept writes.

## Terms

- **Source of truth:** the database whose copy of a user wins. It is MySQL until the switch in step 10, then Postgres.
- **Dual write:** a write commits to the source of truth first, then is copied to the other database. A failure of the other database never fails the request.
- **Version rule:** a copy may only insert a missing row, or replace a row whose `version` is lower than the incoming one. `version` already exists in MySQL `users`: `create` sets it to 1 and every successful `update` adds 1 (optimistic locking). In Postgres: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. In MySQL: `ON DUPLICATE KEY UPDATE` with per-column `IF(VALUES(version) > version, ...)`. Because of this rule, the inline copy, the relay, the backfill and the comparator can apply the same row twice or out of order with the same result. Nothing needs to stop them overlapping. One function per direction does the copy; `copy_to_pg(row)` is the MySQL-to-Postgres one.
- **Outbox (`users_outbox` in MySQL, `pg_outbox` in Postgres):** a table written in the same transaction as the write. Each row is a copy still owed to the other database (`op`, and the full row as `row_json`). It is deleted only after the copy succeeds.
- **Repair:** any copy the inline attempt did not finish: the other database is down or slow, the 300 ms timeout fires, the circuit breaker skips the attempt, or the app crashes after the commit. The outbox row is the durable record, so the relay applies it. We do not use the Redis `jobs` queue for this: `enqueue` raises when Redis is down, a crash between commit and enqueue loses the repair, and dead-lettered jobs in `jobs:dead` are never processed. Any of these would leave a manual step.
- **Relay:** a dedicated worker that reads outbox rows in `seq` order and applies them. It is separate from the Redis job workers. There is one per direction.
- **Fence (`users_control`):** one row per database with `accepting_writes` (`yes` or `no`). Every write transaction takes `SELECT ... FOR SHARE` on that row in the database it writes to. Closing a database is an `UPDATE` to `no`. The update waits for in-flight write transactions and blocks later ones. A refused write gets a retryable 503, which our clients already retry. The share lock is held only until the transaction commits, not during the inline copy that follows.
- **Tombstone (`users_erased(id, erased_at)`):** a table in each database holding the ids of erased users, with no personal data. Ids are never reused.
- **Backfill:** a one-off copy of all existing MySQL rows into Postgres.
- **Comparator:** a worker that compares the two tables by row checksums and repairs differences.
- **Flags:** set by an operator in the existing flag system. Every instance caches all flags and refreshes them every 30 seconds, so instances can disagree for up to 30 seconds. Each instance exports the values it uses as `app_flag_value{flag=...}`.
  - `users.dual_write` (boolean)
  - `users.read_source` (percentage of reads sent to Postgres)
  - `users.writer` (`mysql` or `postgres`)
  - `users.mirror_to_mysql` (boolean)
- **Watchdog:** a separate process, run alongside the switch script, that aborts the switch if it stalls.

## How the system runs

### Writes while MySQL is the source of truth (`users.writer=mysql`)

An instance reads its cached `users.writer` once at the start of each request. `mysql` selects this path. `postgres` selects the Postgres-first path below, and `dual_write` is then ignored. If the cached flag is stale, the fence of the database it picks refuses the write with a 503.

If `dual_write` is off, a write only goes to MySQL. No outbox row is written and nothing is copied. If it is on, for one write:

1. In one MySQL transaction: take the fence (`FOR SHARE` on `users_control`; 503 if not `yes`), do the write, read the full row back, insert an outbox row with the full row. Commit.
2. Try `copy_to_pg(row)` inline, with a 300 ms timeout, swallowing every exception. A circuit breaker skips the inline attempt for 10 seconds after repeated failures.
3. On success, delete the outbox row.
4. Return to the client. The client waits at most 300 ms extra and never sees an error from Postgres.

If the inline copy fails, the outbox row stays and the MySQL-to-Postgres relay applies it. The relay claims rows with `SELECT ... ORDER BY seq LIMIT 200 FOR UPDATE SKIP LOCKED`, applies each with `copy_to_pg` (or a delete under the tombstone lock), then deletes the outbox row. If a failure occurs, it increments `attempts` and retries with capped backoff. There is no dead-letter: the row stays until a retry succeeds or the alert fires. An email unique-violation counts as a failure and is retried, because the conflicting row is normally a pending delete that is earlier in sequence. If the inline copy and the relay both apply a row, the version rule and the per-id lock make the second a no-op.

### Deletes and erasure safety

Only the GDPR erasure job deletes (hard delete, about 2,000 per day). A user it removes must never reappear in Postgres.

- Every copy runs in a transaction that first takes a per-id lock, then checks `users_erased`.
  - Postgres: `pg_advisory_xact_lock` on `hash(id) % 256` stripes, taken in sorted order.
  - MySQL: `SELECT ... FROM users_erased WHERE id=? FOR SHARE`, which also takes a gap lock.
- The delete path inserts the tombstone and deletes the row under the same lock. Whatever order a delete and a stale copy arrive in, the row cannot come back.
- On the MySQL path, one transaction deletes the row, inserts into `users_erased`, and (when `dual_write` is on) writes an outbox `delete` op. It then follows the same inline-then-relay sequence, and the client sees success whatever Postgres does.
- Until the delete reaches Postgres (normally seconds, alerted at 5 minutes), the row can still be read from Postgres. This is accepted because erasure is a batch job with a deadline measured much longer than that.

### Writes after the switch (`users.writer=postgres`)

For one write:

1. In one Postgres transaction: take the Postgres fence, do the write, read the full row back, insert a `pg_outbox` row with the full row. Commit.
2. Try the copy to MySQL inline, with a 300 ms timeout, swallowing every exception. It uses the version rule and the MySQL tombstone check.
3. On success, delete the `pg_outbox` row and return to the client. If the inline copy fails, the row stays and the reverse relay (`pg_outbox` to MySQL) applies it. `users_outbox` is unused.

A MySQL failure never fails the request. A failed Postgres write does, because Postgres is now the source of truth.

- **Versions:** Postgres assigns `version` as MySQL did: a create sets 1, an update adds 1 under optimistic locking on the expected version. The outbox row carries the resulting version, so MySQL receives the identical value.
- **Ids:** a create takes its id from `users_id_seq`. The copy inserts that id explicitly into MySQL, which raises its AUTO_INCREMENT counter, so a rollback cannot reuse ids.
- **Deletes:** in one Postgres transaction, delete the row, insert into Postgres `users_erased`, and insert a `pg_outbox` delete op. The inline copy or reverse relay then deletes the row in MySQL and inserts the MySQL tombstone under the per-id lock.

### Reads

`read_source` chooses Postgres by `enabled_for("users.read_source", user_id)`, so the same user always gets the same answer. Otherwise reads use the MySQL replica.

- On a Postgres error or timeout, a read falls back to the MySQL replica, so reads never fail.
- On a Postgres miss, it also falls back to the replica, but only while `users.writer=mysql` (the row may not be copied yet). Once `writer=postgres`, a miss is final: a MySQL fallback could return a user whose delete has not been mirrored yet. A user created or deleted in Postgres is therefore seen at once.
- Freshness: a read right after a write may hit Postgres while the copy is still in the outbox. Normally the inline copy finished before the client got its response. When it is delayed, a read can return the older row. This is accepted, because the MySQL replica is also slightly behind today. The 5-minute outbox alert bounds it, and no extra mechanism is added.

### Switching the source of truth

Close the old database's fence, drain its outbox, then open the new database's fence. Both fences are closed in between, so a stale instance can only get a 503, whichever flag value it has cached. The 30-second flag skew therefore cannot cause a split-brain write. The script does not need to confirm the flag has arrived. Because the share lock is released at commit, a writer that committed just before the gate closed may still be doing its inline copy. Its outbox row stays until that copy succeeds, so waiting for an empty outbox catches it.

## Rollout steps

- [ ] **Step 0. Monitoring and alerts first.**
  - Starts when: the work begins.
  - Changes: adds dashboards and pages for the following.
    - `users_outbox` oldest-row age (page above 5 minutes) and the equivalent for `pg_outbox`.
    - Postgres write error rate and fallback-read rate.
    - `mysql_replica_lag_seconds` (exported by the replica).
    - A count of instances per `app_flag_value{flag=...}` value, compared with the running instance count.
  - State: metrics only.
  - If it fails: do not continue. Every later gate depends on these.

- [ ] **Step 1. Additive schema, no behaviour change.**
  - Starts when: step 0 is done. It is a manual migration run.
  - Changes: creates the following tables.
    - **MySQL:**
      - `users_outbox(seq PK auto, user_id, op, row_json, attempts, created_at)`
      - `users_erased(id PK, erased_at)`
      - `users_control(id=1, accepting_writes='yes')`
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
  - Changes: the repository gains the write paths, delete path and read path described above. All are dormant except the fence check on MySQL writes.
  - State: code and flags only (defaults are off or `mysql`).
  - If it fails: roll the deploy back. The schema is additive and unused.
  - Do not go on until every instance runs the new build. Instances still on old code would write without outboxes.

- [ ] **Step 3. Deploy the relay and comparator workers.**
  - Starts when: step 2 has finished everywhere. It is a new worker deployment.
  - Changes:
    - The MySQL-to-Postgres outbox relay (described above).
    - The reverse relay, `pg_outbox` to MySQL, with the version rule and MySQL tombstones. It is idle for now.
    - The backfill and comparator, deployed but not started.
  - State: outbox tables in the source databases (the MySQL one for this direction).
  - If it fails: scale to zero. Nothing depends on them yet.

- [ ] **Step 4. Turn on dual writes.**
  - Starts when: step 3 is healthy. An operator sets `users.dual_write=true`.
  - Changes: from now on, every MySQL write also reaches Postgres.
  - Gate: do not call this done until the instance count with `app_flag_value{flag="users.dual_write"}=1` equals the running instance count (at least 30 seconds, normally within about 35). The step 0 dashboard shows this. If the count is ever short, wait. Instances started later read the flag at startup.
    - Writes made by instances that still have the flag off during those seconds get no outbox row. They still reach Postgres later: the backfill starts only after this gate and reads the current MySQL rows then, and the comparator checks the result.
    - The completion timestamp is stored in `users_backfill_progress` as `dual_write_confirmed_at`.
  - State: flag, plus outbox rows in MySQL.
  - If it fails (errors or load): set the flag to `false`. The relay still drains the outbox that exists. Writes made while it was off will not reach Postgres. Whenever the flag is turned on again after being off, repeat the gate, reset `last_completed_id` to 0 (whether or not a backfill had started), rerun the backfill from step 5, and require a fresh clean comparison in step 6. The backfill copies the current rows, which covers every write made during the gap.

- [ ] **Step 5. Start the backfill.**
  - Starts when, all of:
    - Step 4's gate is met.
    - At least 10 minutes have passed since `dual_write_confirmed_at`. This lets the replica catch up with any deletes made just before the flag landed.
    - `mysql_replica_lag_seconds` is below 5.
  - Changes: one backfill worker, guarded by a Postgres advisory lease, loops. It reads from the replica (not the primary) so the bulk read does not load the primary. Reporting jobs share the replica, hence the lag limit.
    - Check lag. If it is above 5 seconds, sleep and recheck, reading nothing.
    - Read the next batch from `mysql.replica`: `WHERE id > :last_completed_id ORDER BY id LIMIT 2000`.
    - In one Postgres transaction: take the stripe locks; upsert all rows with the version rule, skipping ids present in `users_erased`; set `last_completed_id` to the batch's last id.
    - Commit and repeat. A batch that returns fewer than 2000 rows marks the backfill complete.
  - A stale replica row cannot overwrite a newer Postgres row because of the version rule. A deleted user cannot come back because deletes made after dual writes started leave a tombstone in Postgres, and the 10-minute wait covers deletes just before that.
  - State: `users_backfill_progress` in Postgres. The progress update commits atomically with the batch, so a crash mid-batch rolls back both. On restart the worker resumes at `last_completed_id`, not at 0.
  - If it fails: a crash, replica lag, or a Postgres error simply resumes. The upserts are idempotent, and rows that dual writes already updated are never regressed.

- [ ] **Step 6. Full comparison until clean.**
  - Starts when: the backfill is complete and the outbox backlog is below 60 seconds. Run the comparator.
  - Changes: it walks the id space in 2,000-id chunks on the MySQL replica (same lag pause) and on Postgres, comparing row checksums over all columns.
    - Each mismatching row is rechecked 60 seconds later against the MySQL primary, by primary key. If that id still has a row in `users_outbox`, its copy is still owed, so the comparator skips it and checks it again on a later pass.
    - Mismatches that persist are classified.
      - **Missing in Postgres, or older version in Postgres:** `copy_to_pg`.
      - **In Postgres but absent in MySQL and not in `users_erased`:** delete it from Postgres and add the tombstone. The primary check ensures a brand-new row is not removed.
      - **A newer version in Postgres than in MySQL:** this should be impossible. Page a human and stop; it is a bug.
  - Done when: a complete pass finds zero persistent mismatches and made zero repairs. Any repair makes that pass non-clean, so run the comparison again.
  - State: comparator results and run id in Postgres.
  - If it fails: fix the cause and rerun. The comparator runs nightly until MySQL is dropped. A non-zero result resets the gates below.

- [ ] **Step 7. Move reads in stages.**
  - Starts when: step 6 has a clean pass. An operator sets `users.read_source` to 1, 10, 50, then 100, with at least 1 hour per stage.
  - Changes: reads for the user ids in that bucket come from Postgres, with the fallbacks described above.
  - Each stage needs: Postgres read errors and fallback rate low; p99 latency within the target; the nightly comparator still clean.
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
  - Starts when: step 9 passes. An operator runs the switch script, with the watchdog alongside it.
  - Changes, with times measured from the start of the pause:
    1. **T+0.** In MySQL, `UPDATE users_control SET accepting_writes='no'`. This waits for in-flight write transactions. Immediately set `users.writer=postgres`. Writes now get a 503, while reads keep working throughout.
    2. **T+0 to T+30.** The flag reaches all instances within 30 seconds. Instances with a stale flag that hit MySQL get a 503 from the fence. Instances with the new flag hit the Postgres fence, which is still closed, and also get a 503.
    3. Wait until `users_outbox` is empty (the relay is still running). MySQL is closed, so nothing new can arrive. If it is not empty by T+45, for example because the relay is stuck on one failing row, the watchdog aborts.
    4. Set the Postgres sequence: `setval('users_id_seq', GREATEST(MySQL AUTO_INCREMENT, max(id) in Postgres, current value) + 1,000,000)`. Read the MySQL counter with `SET SESSION information_schema_stats_expiry=0`, or `ANALYZE TABLE` first.
    5. In Postgres, set `accepting_writes='yes'`. Postgres opens only after the drain is verified, so the two never overlap. Writes on Postgres now succeed, and creates take their ids from `users_id_seq`.
    6. Stale-flag instances recover by about T+35 at the latest.
  - State: `users_control` rows in both databases, plus the `users.writer` flag. The script records its steps in these rows, so a rerun after a crash resumes.
  - If it fails: the watchdog aborts if Postgres is not open by T+45. It re-opens MySQL, sets the flag back to `mysql`, and Postgres never accepted a write.
    - Left behind after an abort: MySQL open, Postgres closed, and any stuck outbox row still in place, where the 5-minute alert and an operator deal with it before the next attempt.
    - Instances with the new flag cached get a 503 from the Postgres fence for up to 30 more seconds, so the pause ends by about T+75, under the 90-second limit.

- [ ] **Step 11. Run with Postgres as source and MySQL as a live mirror (day 0 to day 14 or more).**
  - Starts when: step 10 completes. This is the rollback window.
  - Changes: writes take the Postgres-first path described above. `users.dual_write` is ignored and the MySQL-first path is unused. At 100% reads come from Postgres and a miss is final. The MySQL replica is used only when Postgres errors or times out.
  - Watch: `pg_outbox` age (alert above 5 minutes) and the comparator, which runs against Postgres and the MySQL replica.
  - State: `pg_outbox` in Postgres, with the same retry behaviour as the MySQL outbox.
  - If a problem appears: see step 12.

- [ ] **Step 12. Rollback to MySQL (only before step 13).**
  - Starts when: an operator decides to roll back, and `pg_outbox` age is under about 10 seconds.
  - Changes: the same procedure as step 10, mirrored.
    1. Close Postgres (`users_control` set to `no`).
    2. Set `users.writer=mysql`.
    3. Drain `pg_outbox` to MySQL.
    4. Open MySQL.
  - Writes pause for at most 90 seconds, and no write is lost because both sides are fenced and drained.
  - Afterwards, MySQL-to-Postgres dual writes resume through `users_outbox`, and the comparator reruns. The 14-day clock and the 3-day soak restart before the next switch.
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
  - If it fails: leave `mirror_to_mysql` on. Do not re-enable it after a gap without first running a one-time repair that copies Postgres to MySQL.

- [ ] **Step 14. Retire MySQL.**
  - Starts when: step 13 has been stable for at least 7 days. Drop the MySQL table only after this step.
  - Changes:
    - First rename `users` to `users_archived` and take a final snapshot.
    - After 7 days with no errors, drop `users_archived`, `users_outbox`, `users_erased` and `users_control` in MySQL.
    - Remove the MySQL paths, the fence code and the flags from `UserRepository`, and remove the outbox, backfill and comparator workers.
  - Erased users: the archive holds users erased after step 13, so keep it only as long as the GDPR erasure deadline allows and purge its backups on the same schedule.
  - If it fails: rename the table back. The code no longer reads it, so nothing else is affected.

## What happens when things fail while running

| Failure | Result |
|---|---|
| Postgres down or slow on a MySQL-first write | The client still succeeds. The outbox row stays and the relay applies it later. |
| App crashes after the MySQL commit | The outbox row survives. The relay applies it. |
| Relay stuck on one row | Retried with backoff. The alert fires at 5 minutes. A switch aborts if the outbox is not empty by T+45. |
| MySQL down on a Postgres-first write (after the switch) | The client still succeeds. The `pg_outbox` row stays and the reverse relay applies it later. |
| Postgres read error, timeout or miss before the switch | The read falls back to the MySQL replica. |
| Postgres read error or timeout after the switch | The read falls back to the replica. A miss is final. |
| Stale flag on an instance | The fence of the database it picks returns a retryable 503. |
| Copy of a deleted user arrives late | The tombstone check blocks it. |

## Open questions

- Which host or job system runs the switch script and its watchdog is not decided. Choose one that is independent of the web instances.
- The exact GDPR erasure deadline is not stated in the brief. The delete path assumes it is much longer than the outbox delay.
