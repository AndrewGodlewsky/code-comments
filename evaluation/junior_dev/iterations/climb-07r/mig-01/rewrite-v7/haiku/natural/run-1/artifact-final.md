# Move `users` from MySQL 8 to Postgres 16: migration plan

## Summary

Today every read and write of the `users` table goes through `UserRepository`, and MySQL 8 is the only database for it. This plan moves the table to Postgres 16 while the service stays up. For now MySQL stays the source of truth. Each write commits to MySQL first and is then copied to Postgres. If the copy fails, a repair worker retries it until it works, so a Postgres problem never fails a user request. When Postgres has every row and matches MySQL, reads move to Postgres. Then the source of truth moves to Postgres in a planned pause of at most 90 seconds. MySQL keeps receiving copies after that, so you can roll back without losing a write until the final step.

The plan is shaped this way so the old database stays authoritative until the new one is proven. Every copy follows one rule, so a copy can be repeated safely. Each stage has a gate that must pass before the next stage starts.

Current system, for scale: about 38 million rows, about 3,000 reads/s and 400 writes/s at peak, and about 2,000 hard deletes a day from the GDPR erasure job. The MySQL primary is `mysql-core-primary`. The read replica is `mysql-core-replica`, and reporting jobs read it too. The Postgres cluster `pg-core` is provisioned and empty, and the app already has a connection pool to it.

## Terms

- **Source of truth:** the database whose row wins when the two differ. Writes go to it first.
- **Instance:** one running copy of the web app or a background worker. Each instance reads the flags itself.
- **Feature flag:** a named setting in `app.flags`. Instances refresh flags every 30 seconds, so after a change they can disagree for up to 30 seconds. The metric `app_flag_value{flag=...}` shows the value each instance is using.
- **Version:** a number on each row that goes up by 1 on every update.
- **Outbox:** a table of copies still to do. A write inserts an outbox row in the same transaction as its change, so the copy is recorded even if the process crashes.
- **Repair worker:** a background job that reads the outbox, copies the current row, and then deletes the outbox row.
- **Tombstone:** a record that a user id was erased. It holds only the id and the time.
- **Copy rule:** the one rule that every copy follows (see Rules).
- **Per-user lock:** a lock keyed on the user id, so two copies of the same user never run at once.
- **Replica:** a read-only copy of the MySQL primary. It lags behind the primary. Its lag in seconds is the metric `mysql_replica_lag_seconds`.
- **Backfill:** copying the rows that already exist, in batches.
- **Lease:** a claim on the backfill, stored as an owner name and an expiry time. An expired lease can be taken by another worker, so a crash cannot block the backfill.
- **Compare pass:** a full read of both tables to find rows that differ.
- **Mirror:** after the switch, the copy of each write that goes back to MySQL.
- **Id counter:** the counter that gives new ids. MySQL calls it `AUTO_INCREMENT`. Postgres uses an identity sequence, and `setval` moves it forward.
- **Circuit breaker:** after repeated failures, it stops calling a service for a short time.
- **Retryable 503:** an HTTP "service unavailable" reply that tells the client to try again. Our clients already retry.

## How the system runs

### Rules

- **Write state.** The flag `users_write_state` decides how writes are handled. It has five values:
  - `legacy`: MySQL only. No outbox and no Postgres writes. This is today's behaviour.
  - `mysql`: MySQL is the source of truth. Each write goes to MySQL, then is copied to Postgres.
  - `paused`: every write returns a retryable 503 with `Retry-After: 1`. Reads continue.
  - `postgres`: Postgres is the source of truth. Each write goes to Postgres, then is copied to MySQL.
  - `postgres_only`: writes go only to Postgres. MySQL is frozen.

  Every change between `mysql` and `postgres` goes through `paused`. So no instance writes to the old side once the new side is authoritative.
- **Read source.** The flag `users_read_source` is `mysql` or `postgres`. It can ramp by percentage with `flags.enabled_for(name, user_id)`. That keeps each user in the same bucket every time.
- **Backfill switch.** The flag `users_backfill_enabled` starts the backfill.
- **Copy rule.** Every copy into either database uses this one function: the inline copy after a write, repair, the backfill, the mirror, and repair after a compare pass. It does the following:
  1. Take the per-user lock.
  2. If a tombstone exists for the id, skip the user.
  3. If the row is missing, insert it.
  4. If the row exists, update it only when its version is lower than the incoming version.
  5. Release the lock.

  Step 4 means a stale copy can never overwrite a newer row. Step 2 means a late copy cannot bring back an erased user.
- **Deletes.** Only the erasure job deletes users, and it does a hard delete. In the same transaction it writes a tombstone. The tombstone table stores only the id, so it holds no personal data. A delete is mirrored the same way: the row is removed on the other side, and that side gets the tombstone.
- **Repair reads the source-of-truth primary.** The repair worker reads each row from the primary of the current source of truth, never from a replica. It deletes the outbox row after copying. A replica read could copy an old version and then delete the only note that a newer one is needed.
- **Repair retries and alerts.** A failed copy is retried with exponential backoff, capped at 5 minutes. Rows are never dead-lettered. Alert when the oldest outbox row is older than 10 minutes, or when the outbox holds more than 10,000 rows.
- **Why not the job queue.** The outbox does not use `jobs.enqueue`. It raises when Redis is down, and its retries end in `jobs:dead`, which nothing processes. The outbox needs no Redis.
- **Ids.** The Postgres `users.id` column is `GENERATED BY DEFAULT AS IDENTITY`, so ids copied from MySQL can be inserted explicitly. Before Postgres becomes the source of truth, its id counter is moved above MySQL's `AUTO_INCREMENT` plus a 1,000,000 margin, while writes are paused. After that, new ids come from `INSERT ... RETURNING id` on Postgres. While MySQL is a mirror, explicit inserts push its counter forward too, so MySQL stays safe for rollback.
- **Backfill progress** (`last_id`, the lease owner and the lease expiry) is stored in the Postgres table `users_migration_state`. A batch's rows and its checkpoint commit in one transaction.

### Where state lives

| Item | Where | Purpose |
|---|---|---|
| `users_write_state`, `users_read_source`, `users_backfill_enabled` | `app.flags` | Phase control. Instances cache them for 30 s. |
| `users`, `users_outbox`, `user_tombstones` | MySQL (`core`) | Source of truth before the switch. Mirror and outbox after it. |
| `users`, `users_outbox`, `user_tombstones` | Postgres (`pg-core`) | Copy target before the switch. Source of truth after it. |
| `users_migration_state` | Postgres | Backfill checkpoint and lease, compare-pass progress, and milestone times (`pg_sot_since`, `pg_reads_full_since`, `pg_only_since`). |
| `app_flag_value{flag=...}`, `mysql_replica_lag_seconds` | Metrics | Show that every instance has a value. Gate the backfill. |
| Outbox age, outbox rows, `pg_apply_failures_total`, `read_fallback_total`, `compare_mismatches` | New metrics | Health and gates. |

## Rollout checklist

Do the steps in order. Each step says what starts it, what it does, where its state lives, and what happens if it fails.

### Phase 0: Prepare (no user-visible change)

- [ ] **0.1 Create the new tables.** This change only adds tables.
  - **Starts:** a migration run.
  - **What it does:** MySQL gets `users_outbox` (`id`, `user_id`, `op`, `created_at`, `attempts`, `next_attempt_at`, `last_error`) and `user_tombstones` (`user_id` primary key, `deleted_at`). Postgres gets `users` (BIGINT identity `id`, unique `email`, `name`, `plan`, `version` INT, `updated_at` `timestamp(3)` in UTC), `users_outbox` (the same columns as MySQL's), `user_tombstones`, and `users_migration_state`.
  - **Where state lives:** both databases.
  - **If it fails:** nothing reads these tables yet, so run the migration again.

- [ ] **0.2 Deploy the new code with `users_write_state = legacy`.**
  - **Starts:** the normal deploy. It must cover the web instances and the worker fleet, because the erasure job runs on workers.
  - **What it does:** `UserRepository` gets the new logic. With `legacy`, behaviour matches today: MySQL only, no outbox, no Postgres writes. The repair worker is deployed but idle.
  - **Where state lives:** flags in `app.flags`. Set `users_read_source` to `mysql`.
  - **If it fails:** roll back the deploy. `legacy` is the old behaviour.

- [ ] **0.3 Verify the fleet.**
  - **Starts:** 0.2 is finished.
  - **What it does:** nothing changes. Check that every web and worker instance runs the new build and reports `users_write_state` in `app_flag_value`.
  - **If it fails:** an instance that is missing or still on the old build blocks Phase 1. Fix it and check again.

### Phase 1: Dual writes (MySQL is the source of truth)

- [ ] **1.1 Turn on dual writes.**
  - **Starts:** the operator sets `users_write_state` from `legacy` to `mysql`, after 0.3 passes.
  - **What it does:** each write runs one MySQL transaction that changes `users` and inserts an outbox row. For an update, the transaction reads the row back from the primary to get the new version. After the commit, the write copies the row to Postgres inline, with a 200 ms timeout behind a circuit breaker. If the copy succeeds, the outbox row is deleted. A Postgres error never fails the request.
  - **Where state lives:** the flag, and the outbox rows in MySQL.
  - **If it fails:** set the flag back to `legacy`. Existing outbox rows still drain, so nothing already written is lost. Writes made under `legacy` have no outbox row. The backfill in 1.3 copies them.

- [ ] **1.2 Confirm every instance dual-writes.**
  - **Starts:** 1.1 is finished.
  - **Condition to pass:** `app_flag_value{flag="users_write_state"}` reads `mysql` on every web and worker instance for at least 60 seconds (two refresh cycles plus a margin). Outbox rows are being created. `pg_apply_failures_total` is not climbing.
  - **If it fails:** find the instance that does not report `mysql`. Do not start the backfill until every instance dual-writes.

- [ ] **1.3 Run the backfill.**
  - **Starts:** 1.2 passes, and the operator sets `users_backfill_enabled` to true. Only one backfill runs at a time.
  - **What it does:** it repeats these steps until it is done.
    1. Take the lease. If it is free or expired, set `lease_owner` and `lease_expires_at` (now + 60 s) in `users_migration_state`. Renew it on every batch.
    2. Check the replica lag. If the metric is missing or above 5 s, sleep 2 s and check again. Do not read.
    3. Read the next batch from the replica: `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000`. The batch is at most 2,000 rows, in primary-key order.
    4. If the batch is empty, mark the backfill done and stop.
    5. In one Postgres transaction, apply the copy rule to each row. Then set `last_id` to the batch's largest id, but only if `lease_owner` is still this worker.
  - **Where state lives:** `users_migration_state` in Postgres. The checkpoint commits with the rows, so no batch is half applied.
  - **If it fails:** a crash, a lost lease, or a Postgres error rolls back the batch. The next run resumes after the last committed `last_id`. It does not start over. Replaying a batch is harmless because the copy rule is idempotent. Reading a stale replica is also harmless, because the version rule blocks older data.

- [ ] **1.4 Keep the repair worker running.**
  - **Starts:** the worker is deployed in 0.2 and active from 1.1.
  - **What it does:** it claims up to 100 outbox rows on the MySQL primary with `SELECT ... FROM users_outbox ORDER BY id LIMIT 100 FOR UPDATE SKIP LOCKED`. For each row, it reads the current row from the primary.
    - If the row exists, it applies the copy rule to Postgres.
    - If the row is gone, it writes the tombstone and deletes the row in Postgres, under the per-user lock.

    Then it deletes the outbox row. Postgres is written before the outbox row is removed, so a crash only causes a harmless replay.
  - **Where state lives:** the outbox in MySQL, and the target rows in Postgres.
  - **If it fails:** the row's attempt count goes up, and the row is retried with backoff (see Rules). An email unique-key conflict is also retried, because another user's email change may not have reached Postgres yet.

### Phase 2: Verify

- [ ] **2.1 Run full compare passes.**
  - **Starts:** 1.3 reports done, and the oldest outbox row is under 1 minute old.
  - **What it does:** it scans the replica and Postgres together in id order, in batches of 2,000, with the same lag pause as step 1.3. It compares `(id, email, name, plan, version, updated_at)` and flags any id that exists only in Postgres. For each mismatch, it re-reads the row from the MySQL primary and waits briefly. Only differences that remain count as confirmed. It repairs confirmed differences with the copy rule. If the primary no longer has the row, it writes a tombstone and deletes the row. A pass is clean only when it finds zero confirmed mismatches. Repeat passes until one is clean.
  - **Where state lives:** progress and results in `users_migration_state`.
  - **If it fails:** the job resumes from its checkpoint. A mismatch that remains after repair stops the cutover and needs investigation. Mismatches caused by in-flight writes usually disappear on re-check.

### Phase 3: Reads on Postgres

- [ ] **3.1 Ramp reads to Postgres.**
  - **Starts:** the latest 2.1 pass is clean and finished within the last 24 hours. The operator sets `users_read_source` to `postgres` at 1%, then 10%, 50%, and 100%, waiting about an hour at each step.
  - **What it does:** `UserRepository.get` reads from Postgres for users in the current bucket. If the Postgres read errors or takes longer than 200 ms, the same request reads from the MySQL replica. Reads never fail. `read_fallback_total` counts the fallbacks.
  - **Where state lives:** the flag. When 100% is reached, the operator records `pg_reads_full_since` in `users_migration_state`.
  - **If it fails:** if fallbacks exceed 0.1% or errors persist, set the ramp back to 0%. Reads stay on MySQL, and no user request fails.

- [ ] **3.2 Hold reads at 100% on Postgres for at least 3 days.**
  - **Starts:** `pg_reads_full_since` is recorded.
  - **What it does:** nothing changes. Compare passes keep running, at least daily.
  - **Where state lives:** `pg_reads_full_since` in `users_migration_state`.
  - **If it fails:** the clock resets if the read source leaves 100%, if the hourly fallback rate goes above 0.1%, or if a compare pass finds a confirmed mismatch.
  - **Gate for 4.1:** at least 72 hours have passed since `pg_reads_full_since`, and the last clean pass finished within 24 hours.

### Phase 4: Planned switch to Postgres as the source of truth

Budget: writes are paused for at most 90 seconds. The switch aims to flip by about 50 seconds and aborts if it has not flipped by 55 seconds.

- [ ] **4.1 Pause writes.**
  - **Starts:** the 3.2 gate is met, and the operator sets `users_write_state` to `paused`.
  - **What it does:** every write returns a retryable 503 with `Retry-After: 1`. Reads continue. Wait until `app_flag_value` reads `paused` on every web and worker instance. That takes up to about 30 seconds.
  - **If it fails:** if not every instance reports `paused` by 35 seconds, abort (4.5).

- [ ] **4.2 Let in-flight writes finish.**
  - **Starts:** 10 seconds after the last instance reports `paused`.
  - **What it does:** nothing. Write transactions have a hard 5-second timeout in both databases, so any write that passed the gate before the pause has ended by then.

- [ ] **4.3 Drain the MySQL outbox.**
  - **Starts:** 4.2 is finished.
  - **What it does:** the repair worker keeps running and drains `users_outbox` in MySQL to zero.
  - **If it fails:** if the outbox is not empty 50 seconds after the pause started, abort (4.5). If Postgres is unavailable, the drain cannot finish, and the switch must not proceed.

- [ ] **4.4 Set the id counter and flip.**
  - **Starts:** 4.3 is finished.
  - **What it does:**
    1. Read MySQL's `AUTO_INCREMENT` for `users` from `information_schema`.
    2. In Postgres, run `SELECT setval('users_id_seq', GREATEST(last_value, :auto_inc + 1000000))`.
    3. Check that `max(id)` and the row counts match in both databases.
    4. Set `users_write_state` to `postgres`.
    5. Record `pg_sot_since` in `users_migration_state`.

    From then on, writes go to Postgres first, and new ids come from `INSERT ... RETURNING id`. Reads stay on Postgres, which is already at 100%.
  - **Where state lives:** the flag, and `pg_sot_since` in `users_migration_state`.
  - **If it fails:** if the setval or a check fails, or the flip has not happened by 55 seconds, abort (4.5).

- [ ] **4.5 Abort, if any step in Phase 4 fails.**
  - **Starts:** a Phase 4 failure or timeout.
  - **What it does:** set `users_write_state` back to `mysql`. Instances resume MySQL-first writes within about 30 seconds, so the pause ends by about 85 seconds at worst.
  - **Why no data is lost:** MySQL was still the source of truth. Any change it held that Postgres lacked is still in the outbox. The advanced Postgres id counter is harmless.

### Phase 5: Postgres is the source of truth (mirror on, rollback possible)

- [ ] **5.1 Write to Postgres first.**
  - **Starts:** 4.4 is finished.
  - **What it does:** each write runs one Postgres transaction that changes `users`, inserts a row in the Postgres outbox, and, for a delete, writes the tombstone. After the commit, the write copies the row to MySQL inline, using the copy rule. MySQL uses `GET_LOCK` for the per-user lock and a version check. On success, the outbox row is deleted. A delete is mirrored the same way.
  - **Where state lives:** Postgres `users` and `users_outbox`, and the MySQL mirror.
  - **If it fails:** the outbox row stays, and the mirror worker retries it. A MySQL outage does not affect writes.

- [ ] **5.2 Run the mirror repair.**
  - **Starts:** 5.1 is finished.
  - **What it does:** the same repair worker runs in reverse. It drains the Postgres outbox into MySQL, reading each current row from the Postgres primary.
  - **If it fails:** retry with backoff and alert on age, as in Rules. Reads that fall back to MySQL can be as stale as the mirror lag. That lag is bounded by outbox age, and outbox age is alerted on. This trade-off is accepted.

- [ ] **5.3 Keep verifying.**
  - **Starts:** 5.1 is finished.
  - **What it does:** run a full compare pass in the Postgres-to-MySQL direction at least daily, and always before any rollback. Repair mismatches with the copy rule.

- [ ] **5.4 Hold for at least 14 days.**
  - **Starts:** `pg_sot_since` is recorded.
  - **What it does:** nothing changes. Writes and the mirror keep running.
  - **Gate for 7.1:** at least 14 days have passed since `pg_sot_since`. The last mirror pass is clean and finished within 24 hours. The mirror outbox is empty. The owner has signed off.

### Phase 6: Rollback to MySQL (available until 7.1)

Budget: the same as Phase 4. Writes are paused for at most 90 seconds, and the rollback aborts if it runs long. Abort here means setting `users_write_state` back to `postgres`, not `mysql`. Postgres is still the source of truth until 6.5, and MySQL does not yet have the Postgres outbox changes.

- [ ] **6.1 Pause writes.**
  - **Starts:** the operator decides to roll back.
  - **What it does:** the operator sets `users_write_state` to `paused`. Every write returns a retryable 503 with `Retry-After: 1`. Wait until every instance reports `paused`, up to about 30 seconds.
  - **If it fails:** if not every instance reports `paused` by 35 seconds, abort: set `users_write_state` back to `postgres`.

- [ ] **6.2 Let in-flight writes finish.**
  - **Starts:** 10 seconds after the last instance reports `paused`.
  - **What it does:** nothing. Write transactions have a hard 5-second timeout in both databases.

- [ ] **6.3 Drain the Postgres outbox into MySQL.**
  - **Starts:** 6.2 is finished.
  - **What it does:** the mirror drains the Postgres outbox to zero.
  - **If it fails:** if the outbox is not empty 50 seconds after the pause started, or either database is unavailable, abort: set `users_write_state` back to `postgres`. Postgres is still the source of truth, so writes resume there and nothing is lost.

- [ ] **6.4 Check the id ranges.**
  - **Starts:** 6.3 is finished.
  - **What it does:** confirm that MySQL `max(id)` equals Postgres `max(id)`. MySQL's id counter is already past every mirrored id, because explicit inserts advance it.
  - **If it fails:** if the ids do not match, abort as in 6.3.

- [ ] **6.5 Flip to `mysql`.**
  - **Starts:** 6.4 passes.
  - **What it does:** set `users_write_state` to `mysql`. Writes resume MySQL-first, and Postgres becomes the dual-write target again. Reads stay on Postgres if it is healthy. Otherwise, set `users_read_source` to `mysql`.
  - **If it fails:** abort as in 6.3.

- [ ] **6.6 Switch back to Postgres later.**
  - **Starts:** the operator decides to switch again.
  - **What it does:** run Phase 4 again. Its `GREATEST(...)` setval keeps the id counter above every id already used, so ids do not collide.

### Phase 7: Postgres only (point of no return)

- [ ] **7.1 Stop the mirror.**
  - **Starts:** the gates in 5.4 are met, and the mirror outbox is empty.
  - **What it does:** the operator sets `users_write_state` to `postgres_only`. This is not a change of source of truth, so no pause is needed. Writes go only to Postgres, and MySQL is frozen. `pg_only_since` is recorded in `users_migration_state`.
  - **Where state lives:** the flag, and `pg_only_since` in `users_migration_state`.
  - **If it fails:** set the flag back to `postgres` until the change takes effect. After it takes effect, rollback to MySQL is no longer possible, so problems must be fixed forward.

### Phase 8: Retire MySQL

- [ ] **8.1 Export `users` for retention.**
  - **Starts:** the team's agreed period after 7.1 has passed.
  - **What it does:** export the MySQL `users` table to restricted storage. The export holds personal data, so the erasure job must cover it, or it must expire under the retention policy.
  - **If it fails:** do not start 8.3 until the export exists.

- [ ] **8.2 Remove the MySQL write path and the flags.**
  - **Starts:** 8.1 is finished.
  - **What it does:** deploy code without the MySQL branches. Remove the flags. Keep the `no-raw-users-sql` lint rule.
  - **If it fails:** roll back the deploy. The flags stay until this deploy is confirmed.

- [ ] **8.3 Drop the MySQL tables.**
  - **Starts:** 8.2 is finished.
  - **What it does:** drop `users`, `users_outbox`, and `user_tombstones` in MySQL. This cannot be undone, except through the 8.1 export. Keep `user_tombstones` in Postgres permanently, since it holds only ids.

## Open questions

- **Erased users could reappear briefly.** A backfill or repair copy can read a user from the replica before the erasure, then insert that user into Postgres before the delete reaches Postgres. The repair removes the row later, but the brief says an erased user must never reappear. Decide whether to accept this window or close it, for example by checking MySQL tombstones on the primary before inserting.
- **Postgres lock not named.** The plan names `GET_LOCK` for the MySQL side of the per-user lock. It does not name the lock for the Postgres side. Choose one before 1.1.
