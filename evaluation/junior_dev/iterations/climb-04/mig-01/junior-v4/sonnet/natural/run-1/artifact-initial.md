# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Design decisions

These choices are left open by the brief. Every step below depends on them.

- **Repair uses a durable outbox in MySQL, not the Redis job queue.**
  - `jobs.enqueue` raises when Redis is down.
  - A job that fails 5 times lands in `jobs:dead`, which nothing processes, so repair would need a manual step.
  - The outbox row is written in the same MySQL transaction as the user write, so a committed write can never lose its repair record.
  - A dedicated drainer process (not the job queue) retries it forever.
  - The outbox holds only `user_id`. The drainer always copies the current row from the source of truth, so repair is idempotent and order does not matter.
- **Deletes use a tombstone in Postgres.**
  - Table `users_tombstone(id)` holds ids only, no personal data.
  - Ids are never reused, so an id is a safe tombstone key.
  - Every copy into Postgres checks the tombstone.
  - The check and the write run under `pg_advisory_xact_lock(id)`. Without the lock, a stale backfill row could slip in between the tombstone check and the insert.
- **The version rule is one SQL shape, used by every copy into Postgres:**
  `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.version < EXCLUDED.version`
  plus `AND NOT EXISTS (tombstone)`.
- **The switch is coordinated by a database fence, with a flag only as the trigger.**
  - Flags can disagree across instances for up to 30 seconds, so they cannot protect correctness.
  - A fence row lives in the database that is the current source of truth.
  - Every write transaction takes a shared lock on the fence row (`SELECT ... FOR SHARE`) and aborts with a retryable 503 if the fence is closed.
  - Closing the fence is an `UPDATE` that takes an exclusive lock. It waits for in-flight writes and then blocks new ones, on every instance at once, whatever flags they hold.
  - Instances holding a stale flag fail closed (503). They do not write to the wrong database.
- **Backfill progress lives in Postgres, table `migration_state`.** The cursor is updated in the same Postgres transaction as the batch it describes, so "last completed batch" is exact after a crash.
- **New ids after the switch come from a Postgres sequence `users_id_seq`.**
  - It is set during the pause to `GREATEST(MySQL AUTO_INCREMENT, max Postgres id) + 100,000`. The margin makes id reuse impossible. Gaps are already normal.
  - On a rollback, MySQL's counter is explicitly set the same way, so a deleted high id is never reissued.
- **Email uniqueness.** MySQL's default collation is case-insensitive. Postgres uses `citext` (or a unique index on `lower(email)`) so it is never looser than MySQL.
- **After the switch the mirror runs the other way.** Postgres is written first, then MySQL, through an outbox in Postgres and the same version rule on MySQL. This is what makes rollback lossless.

---

## Steps

### Phase A: Preparation

- [ ] **1. Create the schemas (additive only, no app change).**
  - **Starts when:** manual DDL, run through the normal migration tooling.
  - **Changes:**
    - Postgres: `users` (same columns; `id BIGINT PRIMARY KEY` with no default yet; unique email), `users_tombstone(id)`, `migration_state` (see below), and `users_mirror_outbox` for the reverse direction.
    - MySQL: `users_sync_outbox(seq BIGINT AUTO_INCREMENT PK, user_id, attempts, created_at)` and `users_write_fence(open, epoch)`, one row, open.
    - The existing `users` table is not altered.
  - **State:**
    - `migration_state` is a single row: `backfill_last_id`, `backfill_done`, `compare_cursor`, `compare_last_clean_pass_at`, `pg_write_open` (false), `pg_fence_epoch`.
    - The MySQL fence row is the only fence that is open at this point.
  - **If it fails:** nothing depends on these objects yet, so fix and re-run. The DDL is idempotent (`IF NOT EXISTS`).
  - **Prerequisite to confirm before step 9:** Postgres has a synchronous standby and tested backups. From the switch onward, Postgres is the only place newly accepted writes are guaranteed to exist until they are mirrored.

- [ ] **2. Deploy the migration-aware code with every migration flag off.**
  - **Starts when:** a normal deploy, with all behaviour behind these flags:
    - `users_dual_write` (percentage, default 0)
    - `users_write_mode` (string: `mysql_primary` | `pg_primary` | `pg_only`, default `mysql_primary`)
    - `users_read_pg` (percentage, default 0)
    - `users_backfill` (boolean, default false)
  - **Changes:**
    - `UserRepository` gains:
      - the fence check in every MySQL write transaction;
      - the outbox insert in the same transaction as the write, when dual write applies;
      - a Postgres apply after commit, with a 250 ms timeout, wrapped in try/except so it can never fail the request;
      - a short circuit breaker that skips the Postgres attempt for 10 s after repeated failures;
      - read fallback (Postgres failure or miss falls back to the MySQL replica).
    - The drainer, backfill and compare run as separate worker processes. All are deployed idle.
    - **Drainer behaviour (it runs permanently and keeps draining even if `users_dual_write` is later turned off):**
      - It polls the outbox with `FOR UPDATE SKIP LOCKED` in batches.
      - It groups rows by `user_id` and records the max `seq` per user.
      - It reads the current row from the MySQL primary.
      - If the row exists, it applies the version rule; if not, it deletes the Postgres row and writes the tombstone, in one transaction.
      - Only then does it delete outbox rows with `seq <=` that max.
      - It retries forever with backoff capped at 30 s.
      - A persistent failure, such as an email unique conflict that waits for another id's change, is retried every 5 minutes with `attempts` incremented and raises an alert.
      - Alert thresholds on oldest outbox age: warn at 2 minutes, page at 10 minutes.
  - **State:** flags in `app.flags`. Outbox and fence in MySQL. A new instance proves it runs this code by exporting `app_flag_value{flag="users_write_mode"}`, because older instances do not export that flag.
  - **If it fails:** roll back the deploy. With all flags off, behaviour is identical to today, apart from a shared lock on a one-row fence table.

### Phase B: Dual writes

- [ ] **3. Ramp dual writes to 100%.**
  - **Starts when:** step 2 is finished on every instance, confirmed by the `app_flag_value` metric appearing on all of them.
  - **Changes:** set `users_dual_write` to 1%, then 10%, then 100%, holding each stage for at least 15 minutes with a clean check. Buckets are by `user_id` via `enabled_for`.
    - **Create:** MySQL assigns the id, then the row is copied to Postgres with that explicit id.
    - **Update:** the full row is read inside the MySQL transaction and used as the inline snapshot.
    - **Delete:** the outbox row is written in the MySQL transaction. The Postgres deletion and tombstone follow.
  - **State:** outbox in MySQL. Postgres fills with changed rows only.
  - **If it fails:**
    - A Postgres error never reaches the user. The outbox row stays and the drainer fixes it automatically.
    - If the inline attempt is slow or error-prone, the breaker skips it and the drainer carries all copies (about 1 s delay). Nothing is lost.
    - A bug in the new path: set `users_dual_write` back to 0. Any remaining outbox rows are still drained.
    - A crash after the MySQL commit but before the inline attempt is covered by the outbox.

- [ ] **4. Gate: every instance is dual-writing.**
  - **Starts when:** `users_dual_write` is 100 and a script confirms all of the following for 2 consecutive minutes.
  - **Condition:**
    - The count of instances reporting `app_flag_value{flag="users_dual_write"}=100` equals the orchestrator's running instance count. This also proves no old-code instance is left, because old instances do not export the metric.
    - No deploy is in progress.
    - The outbox's oldest row is younger than 1 minute.
  - **Changes:** nothing yet. The script records the result.
  - **If it fails:** wait, or restart the instance that has not caught up. Do not proceed to step 5.

### Phase C: Backfill

- [ ] **5. Backfill 38M rows.**
  - **Starts when:** the step 4 gate passes and an operator sets `users_backfill=true`.
  - **Changes:** a single worker copies the historical rows.
    - It holds a Postgres advisory lock for its whole run, so a second copy cannot start.
    - **Loop:**
      1. Read `mysql_replica_lag_seconds`. If it is above 5, sleep 10 s and re-check. Reporting jobs share the replica.
      2. Run `SELECT * FROM users WHERE id > :last ORDER BY id LIMIT 2000` on the replica.
      3. In one Postgres transaction, take advisory locks on the ids in ascending order, apply every row with the version rule and tombstone check, and set `backfill_last_id` to the batch's max id.
    - A row that fails (an email conflict, for example) is skipped and its id is inserted into the MySQL outbox so the drainer repairs it later. The batch continues.
    - Stale replica rows are harmless. The version rule ignores them if Postgres is already newer, and the tombstone blocks any user erased in the meantime.
    - A short batch (fewer than 2,000 rows) means the end is reached. The worker sets `backfill_done`.
  - **State:** `migration_state.backfill_last_id`, committed atomically with each batch.
  - **If it fails:**
    - **Worker crash:** the restarted worker reads `backfill_last_id` and continues after the last completed batch.
    - **Postgres error:** the transaction rolls back and the cursor does not move. The batch is retried with backoff.
    - **Replica lag above 5 s:** pause, no error.
    - **Disabling:** set `users_backfill=false`. The worker stops after its current batch.

### Phase D: Verify

- [ ] **6. Full comparison until a pass finds zero mismatches.**
  - **Starts when:** `backfill_done` is set and the outbox is under 1 minute old.
  - **Changes:** the compare worker walks ids 0..max in chunks of 10,000, comparing a checksum of `(id, email, name, plan, version)` from the replica against Postgres. The replica lag guard from step 5 applies.
    - It also finds Postgres rows that no longer exist in MySQL.
    - A chunk that differs is checked row by row. A differing row is re-read from the MySQL primary after 60 s. If it is now equal, it was in flight and is not counted.
    - A row still different is counted as a mismatch and its id is added to the MySQL outbox, which repairs it automatically.
  - **State:** `compare_cursor` and the mismatch count in `migration_state`. `compare_last_clean_pass_at` is set only when a whole pass over all ids finishes with 0 counted mismatches.
  - **If it fails:**
    - **Mismatches found:** they are repaired, and a new full pass runs. The gate needs one pass that finds none. A pass that found and repaired some does not count.
    - **Worker crash:** it resumes from `compare_cursor`.
    - **Mismatches that keep returning:** stop and investigate. That is a bug in the dual-write path, not a data problem to keep fixing.
  - The compare worker keeps running (one pass per day or so) until step 12. Step 9 requires a clean pass within the last 24 hours.

### Phase E: Reads move

- [ ] **7. Ramp reads to Postgres.**
  - **Starts when:** `compare_last_clean_pass_at` is set (step 6).
  - **Changes:** set `users_read_pg` to 1%, 10%, 50%, then 100%. Hold each stage for at least 30 minutes with the metric showing all instances on the new value. Bucketing is by `user_id`, so one user always gets the same backend.
    - **Fallback:** a Postgres error, timeout or miss falls back to `mysql.replica` for that request. Reads therefore never fail, and a miss costs one extra query.
    - **Watch:** read error rate, p99 latency, fallback rate, and outbox age.
  - **State:** the flag value. Nothing is moved.
  - **If it fails:**
    - **Problems at any stage:** set `users_read_pg` to 0. Instances return to the MySQL replica within 30 s.
    - **Postgres outage:** the fallback protects users, and an alert fires.
    - **Restart rule:** any drop below 100 restarts the soak clock in step 8.

- [ ] **8. Soak at 100% for at least 3 days.**
  - **Starts when:** all instances report `users_read_pg=100`. Record the time as T0.
  - **Changes:** nothing. The compare worker keeps running daily.
  - **Condition to continue:**
    - 3 days have passed since T0.
    - The reads were at 100% the entire time. A drop restarts the clock.
    - The latest compare pass is clean and under 24 hours old.
    - The outbox age has stayed under 1 minute.
  - **If it fails:** extend the soak, or follow step 7's failure path.

### Phase F: Source of truth moves

- [ ] **9. Switch writes to Postgres (planned pause of about 45 s, hard limit 90 s).**
  - **Starts when:** the step 8 conditions hold, an operator is present, and the Postgres standby and backups are confirmed (step 1 prerequisite). One script `switch_to_pg` performs the sequence and aborts if a deadline passes.
  - **Changes (t0 is the moment the fence closes):**
    1. **t0: close the MySQL fence** with `UPDATE users_write_fence SET open=0, epoch=epoch+1`. It waits for in-flight writes to commit (lock wait timeout 10 s), then every MySQL write on every instance fails closed with a retryable 503. The pause has started. Reads are untouched.
    2. **Drain the outbox to zero.** This normally takes a second or two. Every committed MySQL write is now in Postgres.
    3. **Spot-check** 10,000 random ids against Postgres.
    4. **Set the sequence:** `setval('users_id_seq', GREATEST(MySQL AUTO_INCREMENT, max pg id) + 100000)`.
    5. **Open the Postgres fence** (`pg_write_open=true`, `pg_fence_epoch` incremented).
    6. **Set `users_write_mode=pg_primary`.** Each instance picks it up on its next refresh (at most 30 s). Until then, that instance returns 503 for writes because its MySQL fence is closed. After that:
       - **Create:** the id is `nextval('users_id_seq')`.
       - **Update/delete:** run in Postgres with the same `version` rule and tombstone, with a row in `users_mirror_outbox` in the same transaction.
       - **Mirror:** the change is applied to MySQL inline (250 ms timeout, errors ignored) and the version rule is applied there too. The mirror drainer repairs misses forever, as in step 2.
    7. Wait until all instances report `pg_primary`. Restart any instance that does not refresh.
  - **State:** the sequence, both fences with their epochs, `users_write_mode`.
  - **Pause budget:** about 10 s for steps 1 to 5, plus at most 30 s flag propagation, for roughly 45 s per instance.
  - **If it fails:**
    - **Before step 5 (any deadline of 30 s missed, lock wait timeout, drain not finishing):** the script reopens the MySQL fence and the pause ends. Postgres was never source of truth, so nothing is lost.
    - **After step 5:** use the rollback in step 10. That is a second pause under the same 90 s limit.
    - **Script crash mid-way:** the fences themselves are the state. At most one is open, so there is no split brain. An operator reruns the script from the recorded step.
  - **From now on, if Postgres is down, writes get 503.** That is correct when Postgres is the source of truth. Reads continue through the fallback.

### Phase G: Rollback window (14 days)

- [ ] **10. Hold the rollback window; use rollback if needed.**
  - **Starts when:** step 9 completes. Record the time as T1.
  - **Changes during the window:**
    - All writes go to Postgres first and are mirrored to MySQL, so MySQL stays complete.
    - The mirror drainer runs continuously.
    - The compare worker keeps checking in both directions.
  - **Rollback procedure (`switch_to_mysql`):** the same script with roles reversed.
    1. Close the Postgres fence.
    2. Drain `users_mirror_outbox` to zero.
    3. Run `ALTER TABLE users AUTO_INCREMENT = (sequence last value + 100000)` on MySQL, so a deleted id is never reissued.
    4. Open the MySQL fence.
    5. Set `users_write_mode=mysql_primary`.
    - Dual writes then run MySQL to Postgres again. Pause: about 45 s, under the 90 s limit. No write is lost because the mirror outbox is drained before MySQL reopens.
  - **State:** the outbox, both fences, the flags, as in step 9.
  - **If it fails:**
    - **Mirror backlog:** it grows but is safe, and alerts fire at the same thresholds. Rollback waits for it to drain, which is the cost of no-loss rollback.
    - **Rollback itself fails before step 4:** reopen the Postgres fence. If the rollback is invoked during a Postgres outage, it cannot drain and cannot complete. The Postgres standby from step 1 is the protection against that.

### Phase H: Final cut-over

- [ ] **11. Switch to Postgres-only writes (the point of no return).**
  - **Starts when:** at least 14 days after T1 (step 10), and all of the following hold:
    - the mirror outbox is empty;
    - a clean compare pass exists within 24 hours;
    - there has been no rollback in the last 14 days (a rollback restarts the clock, since T1 resets at the next step 9);
    - the team has explicitly approved.
  - **Changes:** set `users_write_mode=pg_only`.
    - Instances stop writing the mirror outbox and stop applying to MySQL.
    - Read fallback to the MySQL replica is switched off in this mode (it would be stale).
    - After the metric shows all instances on `pg_only`, wait for the mirror outbox to reach zero, then stop the mirror drainer and the compare worker.
    - No source-of-truth change and no pause is needed. MySQL simply stops being updated.
  - **State:** the flag, plus Postgres.
  - **If it fails:**
    - Before the flag is propagated everywhere, setting it back to `pg_primary` restores the mirror, and the drain catches up.
    - After the mirror drainer is stopped, rollback to MySQL is no longer possible without a rebuild. This step is irreversible.

- [ ] **12. Decommission MySQL.**
  - **Starts when:** step 11 completed with a clean week of metrics.
  - **Changes (in order):**
    1. Deploy a cleanup release that removes the MySQL branches, fences, outbox code, and the migration flags from `UserRepository`. The no-raw-users-sql lint rule stays.
    2. Drop `core.users`, `users_sync_outbox` and `users_write_fence` from MySQL.
    3. Remove the MySQL-only Postgres artifacts: `users_mirror_outbox` and the migration rows. Keep `users_tombstone`.
    4. Keep no extra copy of `core.users` beyond normal backup retention, so erased users do not persist in a long-lived dump.
  - **State:** none left. Postgres is the only copy.
  - **If it fails:** a deploy fault is rolled back with the normal deploy tooling. Dropping the table is irreversible, which is why it comes last.
