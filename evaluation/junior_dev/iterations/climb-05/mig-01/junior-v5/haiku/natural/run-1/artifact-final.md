# Move `users` from MySQL to Postgres: migration plan

## What this is

The `users` table moves from MySQL 8 to the Postgres 16 cluster (`pg-core`) with no downtime. Today, every read and write of `users` goes through `UserRepository`. Reads come from the MySQL replica and writes go to the MySQL primary, and MySQL is the source of truth.

The plan runs in this order. First, every write also goes to Postgres (dual writes). Second, old rows are copied across (backfill). Third, the two tables are compared and any differences are repaired. Fourth, reads move to Postgres in small steps. Fifth, Postgres becomes the source of truth. MySQL stays available for rollback for 14 days after that. Only then are writes moved to Postgres alone, and the MySQL table is dropped.

The plan is shaped this way so that a Postgres failure never fails a user request. Until the switch, MySQL is the source of truth, and Postgres is repaired in the background. Every copy into either store follows one version rule, so a late or repeated copy cannot overwrite newer data. Only two moments change the source of truth. Each uses a short write pause, which is set through a control row that every app instance polls.

## Terms

- **MySQL primary** (`mysql-core-primary`): the MySQL server that takes writes. The control row lives here until the switch.
- **Replica** (`mysql-core-replica`): a read-only copy of MySQL. Reporting jobs also use it. Its lag is the metric `mysql_replica_lag_seconds`.
- **Source of truth:** the store whose rows win when the two stores disagree. It is MySQL until step 9, then Postgres.
- **Mode:** a value in the control row that says where writes go. `mysql`: writes go to MySQL, and copies go to Postgres when dual writes are on. `paused`: no writes; requests get a 503. `pg`: writes go to Postgres. `pg_only`: like `pg`, and MySQL is no longer written.
- **Control row:** a row holding `mode` and `epoch`. Every change raises `epoch` by 1. Until step 9 it is `users_pg_control` in MySQL. From step 9 it is in Postgres `migration_state`.
- **Lease:** an instance's permission to write. It lasts 10 s, counted from when the instance sent the poll that last succeeded.
- **Write fence:** the check an instance makes before each write. The write runs only if the lease is valid, at least 3 s of it remain, and the mode allows writes.
- **Per-user lock:** a lock on one user id in the store being written. `GET_LOCK('users:<id>')` in MySQL, `pg_advisory_xact_lock(id)` in Postgres.
- **Version:** the `version` column. It is 1 on create and goes up by 1 on each update, in the app. Both stores have it. A copy keeps the version it was given.
- **Version rule:** a copy inserts the row if its id is missing. If the id exists, it replaces the row only when the existing `version` is lower than the incoming one. Otherwise it does nothing.
- **Tombstone:** a row that marks an erased user. It is `users_tombstones` in MySQL and `user_tombstones` in Postgres. Tombstones are never deleted. A copy into a store is skipped if that store has a tombstone for the id.
- **Erasure:** the GDPR erasure job's hard delete of a user. It is the only code path that deletes a user.
- **Forward outbox:** `users_pg_outbox` in MySQL. Each user write adds one row in the same transaction. A row means "this user's Postgres copy may be stale."
- **Reverse outbox:** `pg_outbox` in Postgres. The same idea, used after the switch with MySQL as the target.
- **Outbox age:** the age of the oldest outbox row. It shows how far copies may lag.
- **Dual-write flag:** `users.dual_write`. When it is on and the mode is `mysql`, each write also copies to Postgres.
- **Erasure work list:** `users_erasure_work` in MySQL. The erasure job adds one row per user to erase. Each row is in one of three states: not started, half done (part (a) done, part (b) not), or done.
- **Sweeper:** a job on every instance that works through the erasure work list on a timer, until every row is done.
- **Backfill:** the one-time copy of existing rows from the replica into Postgres.

## How the system runs

### Write fence

Each instance polls the control row every 2 s. It reads the store that holds the source of truth, and it reads the mode directly, not from the 30 s flag cache. A write starts only when the lease is valid, at least 3 s of it remain, and the mode allows writes. Each write has a 3 s deadline. A write that is not allowed returns a retryable 503. Clients already retry 503s. Reads are never fenced.

If polls fail, the instance keeps writing until its lease runs out, 10 s after its last successful poll was sent. Then its writes return 503. Its reads continue.

Why no write runs 12 s after `paused` is set: call the moment `paused` is written T. An instance that has not yet seen `paused` last polled before T, so its lease ends before T+10. It starts no write once its lease has under 3 s left, which is before T+7. Each write ends within 3 s of its start, so every write ends by T+10. The drain waits until T+12, a 2 s margin. A write that starts between T and the instance's next poll is still allowed. It commits to MySQL with an outbox row, so the drain includes it.

### Where the control row lives

- Before step 9, the control row is in MySQL. From step 9 it is in Postgres. After a rollback in step 11 it is in MySQL again.
- Each instance polls the store that holds the source of truth.
- A pause is written only to the store the instances read now: MySQL before the switch, Postgres during a rollback.
- A mode change is written first to the store the instances are moving to, then to the other store, both with the same new epoch. Instances keep polling the old store until they see the new mode there. So a `pg` written only to Postgres leaves every instance paused, because they still poll MySQL and see `paused`.

### Copy rules

Every copy into a store does three things, in order. It takes the per-user lock. It checks the tombstone and skips the copy if one exists. It applies the version rule. A unique-email conflict caused by out-of-order copies is retried. It is not a permanent failure.

### Forward outbox worker (MySQL to Postgres)

Each instance runs this worker every 1 s. It runs when the mode is `paused`, so the drain in step 9 can finish, or when the mode is `mysql` and `users.dual_write` is on. It stops in `pg` and `pg_only`. Each pass does four things:

1. Reads up to 500 outbox rows, oldest first, and notes the highest `seq` for each user.
2. For each of those users, reads the current MySQL row. This read comes after step 1.
3. Copies that row to Postgres with the copy rules. If the MySQL row is gone, it does nothing. Erasure has already removed the Postgres row and written the tombstone.
4. Deletes that user's outbox rows with `seq` up to the noted value.

A row is deleted only after its copy succeeds. If a copy fails, the row stays, and the next pass retries it. A write that commits after step 1 gets a higher `seq`, so step 4 keeps its row, and a later pass copies it. Several instances can run a pass at once, because copies are idempotent. A copy that lands after the switch is harmless, because the version rule makes it a no-op.

### Reverse outbox worker (Postgres to MySQL)

This worker runs in mode `pg`, from the switch on. It also runs during the rollback drain in step 11, and it stops when that drain finishes. In `pg_only` it drains the outbox to zero and stops. It uses the same four steps as the forward worker, with Postgres as the source and MySQL as the target. It takes the MySQL per-user lock and checks the MySQL tombstone.

## Rollout checklist

The steps run in this order.

- [ ] **1. Add the schema.**
  - Starts: the normal migration deploy.
  - Does: adds `users_pg_outbox`, `users_tombstones`, `users_erasure_work` and `users_pg_control` (mode `mysql`, epoch 1) to MySQL. Adds `users`, `user_tombstones`, `pg_outbox` and `migration_state` to Postgres. Nothing reads or writes them yet.
  - State: MySQL and Postgres.
  - If it fails: drop the new tables and redeploy. Nothing depends on them.

- [ ] **2. Deploy the code with every switch off.**
  - Starts: the deploy of the build that contains the write fence, copy rules, outbox writes, forward worker, read path with fallback, backfill runner, sweeper and compare job.
  - Does: sets `users.dual_write`, `users.backfill` and `users.pg_read_percent` to off, off and 0. Each instance reports its build version and `users_mode_applied`. From now on every user write also adds an outbox row, so no write is missing when dual writes start. The forward worker waits while dual writes are off. All new SQL on `users` lives in `UserRepository` or in a module the lint rule explicitly allows. The `no-raw-users-sql` rule is not widened silently.
  - State: flags and the MySQL control row.
  - If it fails: roll back the deploy. The only new effect is outbox rows, which are harmless.

- [ ] **3. Erasure ordering (active from step 2 on).**
  - Starts: the erasure job adds a row per user to the erasure work list, in the store that holds the source of truth (MySQL until step 9, Postgres after).
  - Does: the sweeper on every instance works through that list on a timer. Its writes are fenced like any other write. It does not depend on dual writes. Several instances can run it at once. For each row, in this order:
    - (a) Under the Postgres per-user lock, insert the Postgres tombstone, delete the Postgres row, and commit.
    - (b) Then, in one MySQL transaction, insert the MySQL tombstone, delete the MySQL row, write an outbox row, and mark the work row done.
  - Part (b) never starts before part (a) commits. During a write pause, erasure writes get a 503, so the sweeper retries them. Both parts are idempotent.
  - Why part (a) runs before dual writes: backfill copies rows from the replica, so the Postgres tombstone must exist before backfill can copy an erased user.
  - Why this holds: every copy checks the tombstone under the same lock. A copy that read the row before the delete finds the tombstone and skips. A copy that starts later finds it too.
  - A row can stop half done, for example when a pause or crash falls between the two parts. It stays that way until the sweeper runs part (b). Step 9 covers a row that is half done at the switch.
  - The job queue is not used for this, because its dead letters are never processed.
  - State: the erasure work list.
  - If it fails: the sweeper retries the row. If Postgres is down, erasure waits and an alert fires. No user request waits.

- [ ] **4. Turn on dual writes.**
  - Starts: an operator sets `users.dual_write` to on. This is allowed only after steps 2 and 3 are live on every instance. Check that every instance reports `app_flag_value{flag="users.dual_write"}` as on, then wait at least 60 s.
  - Does: in mode `mysql`, `create` and `update` commit in MySQL together with their outbox row. Then one Postgres copy is tried, with a 200 ms timeout. The request waits for that copy to finish or time out, then returns. Any failure or timeout is logged and counted. It is never raised to the caller. The copy uses the MySQL row read after commit, so it carries the source's values, including `updated_at`. The inline copy does not delete its outbox row. The forward worker deletes it on its next pass, so only one path deletes outbox rows. Erasure is not on this path.
  - Cost: each outbox row lasts about 1 s, so there are roughly 400 rows at peak.
  - State: the MySQL outbox and Postgres.
  - If it fails: the user's request still succeeds. The outbox row stays. The forward worker retries it every 1 s until Postgres recovers. If dual writes are turned off, the rows stay in the outbox and are copied when dual writes come back on.

- [ ] **5. Backfill.**
  - Starts: an operator sets `users.backfill` to on. This is allowed only after step 4 has been on everywhere for at least 60 s and outbox age is under 5 min.
  - Does: one runner copies rows from the replica in primary-key order. Each batch runs `WHERE id > last ORDER BY id LIMIT 2000`. `last` is `migration_state.backfill_last_id`, the highest id in the last committed batch. It starts at 0. Before each batch, the runner checks `mysql_replica_lag_seconds`. If lag is above 5 s, the runner waits and checks again every 5 s. Each row goes through the copy rules. In the same Postgres transaction as the rows, the runner sets `backfill_last_id` to the batch's last id. The backfill is done when a batch returns 0 rows. That is about 19,000 batches.
  - Lease: the runner holds a row in Postgres `migration_state` with an owner token and a 60 s expiry. It renews the lease before each batch and every 5 s while it waits for lag. The checkpoint update applies only if the lease still has this runner's token. If another runner has taken over, the update matches nothing. The batch rolls back and the runner stops.
  - Why it is safe: the forward outbox covers writes made after the replica read. The version rule stops a lagging replica copy from overwriting newer data. A tombstone stops a copy of an erased user.
  - State: the checkpoint and the lease, in Postgres `migration_state`.
  - If it fails: a Postgres error rolls back the batch, which is retried with backoff. Replica errors or lag pause the run. After a crash, the next runner resumes after the last committed checkpoint. A rolled-back batch is replayed, which the copy rules make safe.

- [ ] **6. Full comparison and repair. Reads do not move until a pass is clean.**
  - Starts: the backfill is complete.
  - Does: walks ids in order on both sides, in chunks of 2,000 ids. It compares a hash of `(id, version, email, name, plan, updated_at)` per chunk, skipping ids tombstoned in either store. For each chunk that differs, it checks each row:
    - Under the per-user lock, it reads the row from MySQL and from Postgres.
    - If that user still has rows in the MySQL forward outbox, the row is deferred. The forward worker will copy it.
    - Otherwise, if the rows still differ, the copy rules repair Postgres, and the row counts as a mismatch.
  - Deferred rows are checked again at the end of the pass, once their outbox rows have drained.
  - The pass pauses while replica lag is high.
  - A pass is clean when it has zero mismatches and no deferred row still differs at the end.
  - Why the test is not "outbox empty": at about 400 writes per second the outbox is almost never empty, so that test would never pass.
  - State: `migration_state` records the pass start, end and mismatch count.
  - If it fails: repair the mismatches and run another pass. If clean passes keep failing, stop and investigate the cause.

- [ ] **7. Move reads to Postgres in steps.**
  - Starts: an operator raises `users.pg_read_percent` after a clean pass. The steps are 1, 10, 50 and 100. The operator holds at each step while watching the sampled comparison and error rates.
  - Does: `flags.enabled_for('users.pg_read_percent', user_id)` picks the users who read from the Postgres primary. Everyone else stays on the MySQL replica. A Postgres error, timeout or missing row falls back to the replica, so reads never fail. The read path does not check the outbox. A user who has just written can therefore read an older version until their copy lands. That lag is normally seconds, and it is bounded by outbox age.
  - Sampled comparison: the read path picks 1% of the reads it serves from Postgres. For each, it reads the replica for the same user and compares `version` and the fields. If they differ, it checks `users_pg_outbox` in MySQL for that user. A difference counts as a mismatch only if that user has no outbox rows. Each counted mismatch increments `users_read_mismatch_total`, which the operator watches with its alert.
  - State: the flag only. No data moves.
  - If it fails: set the percentage to 0. That takes effect within 30 s, and clients see no errors.
  - Stop rule: any counted mismatch stops the ramp, and the process returns to step 6.

- [ ] **8. Hold reads at 100% on Postgres for at least 3 days.**
  - Starts: reads reach 100%.
  - Does: sets `migration_state.reads_100_since` to now. The 72 h clock runs on this value. If the percentage drops below 100, or the sampled comparison finds a mismatch, the value is cleared and the clock restarts. A full compare (step 6) must run during the hold, after the latest clock start, and finish clean. A compare that started before the latest clock start does not count. Writes made during the hold do not fail the compare by themselves. A differing row with pending outbox rows is deferred. Only a difference with no outbox rows counts.
  - State: Postgres `migration_state`.
  - If it fails: no data changes. The clock restarts, and the full compare must run again after that restart.

- [ ] **9. Planned switch: Postgres becomes the source of truth. Writes are paused for at most 90 s.**
  - Starts: an operator or automation starts it, only when all of these hold. The step 8 clock shows at least 72 h. A full compare that started after the latest clock start finished clean. Outbox age is under 5 min and depth is small. Every instance reports the fenced build. The reverse worker is deployed on every instance and passes its checks.
  - Does:
    1. Write `paused` (epoch+1) to MySQL. Writes now get a 503. Wait 12 s. No write is still running after that.
    2. Drain the forward outbox to zero. Writes are paused, so the outbox can only shrink. Check that it is empty.
    3. Set the Postgres id sequence to MySQL's `AUTO_INCREMENT` plus 1,000,000. MySQL assigns no new ids after this, so ids stay unique and increasing.
    4. In one Postgres transaction, write mode `pg` (epoch+2) to `migration_state`, and copy the erasure work list rows from MySQL into Postgres, keeping each row's state. Then write the same mode and epoch to MySQL. Instances keep polling MySQL, so they stay paused until they see `pg` there. Then each instance applies `pg` within about 2 s and reads and writes Postgres. Each write takes the per-user lock, checks the version, and writes the row and a reverse-outbox row in one commit. A half-done work row keeps its state. Part (a) already left the Postgres tombstone and the Postgres row deleted. So after the switch the sweeper only does the rest of part (b) in MySQL: insert the MySQL tombstone, delete the MySQL row, and mark the row done.
    5. Record `source_switched_at` in Postgres.
  - A request refused with a 503 was never applied, because the 503 comes before any write starts. Clients retry it after the switch, and the retry hits the new mode.
  - Pause budget: target about 30 s. Abort by 75 s, as described below.
  - Reads: not affected. Postgres already holds every row.
  - State: the control row in MySQL and then in Postgres, the sequence, and `migration_state`.
  - If it fails, find the last write that succeeded:
    - Before step 4 writes anything, nothing is in Postgres. If the drain is still running at 60 s, write `mysql` (epoch+3) to MySQL and resume. Instances read MySQL and see it.
    - If Postgres has `pg` but MySQL does not, instances read MySQL, which still says `paused`, so they write nothing. Retry the MySQL write of `pg` with the same epoch. If MySQL cannot take it by 75 s, abort. Write `mysql` (epoch+3) to MySQL, then to Postgres. No instance has applied `pg`, so no write was lost. The work-list rows copied to Postgres are ignored. If MySQL is down, writes stay paused until it is back, and the operator is paged.
    - If MySQL has `pg` and some instances have applied it, those instances now read and write Postgres, and the rest follow within about 2 s. Do not flip back with a plain write. Use the rollback in step 11, whose pause goes to Postgres, where these instances now read.

- [ ] **10. Reverse sync (from the switch until step 12).**
  - Starts: the switch is complete.
  - Does: writes go to Postgres first. The reverse worker copies each changed row to MySQL under the MySQL per-user lock, with the MySQL tombstone check and the version rule. It then deletes the reverse-outbox rows it has copied, using the same read-first order as the forward worker. Reads come from Postgres. The MySQL replica is read only as a counted, stale fallback.
  - Erasure: the work list is now in Postgres, so the order is reversed. (a) Under the MySQL per-user lock, insert the MySQL tombstone, delete the MySQL row, and commit. (b) Then, in one Postgres transaction, insert the Postgres tombstone, delete the row, write a reverse-outbox row, and mark the work row done. A reverse copy then skips the erased user.
  - Unique-email conflict: a reverse copy can hit a MySQL row that still has the email, because that other user's change is still in the reverse outbox. The copy is retried in outbox order and clears when that change lands. If it does not clear, outbox age alerts.
  - IDs: Postgres assigns ids from the sequence set at the switch. Reverse copies insert explicit ids, which moves MySQL's counter forward. MySQL assigns no new ids.
  - Monitoring: reverse-outbox depth and age, and a daily sampled compare of the two stores.
  - State: `pg_outbox` and the erasure work list, both in Postgres.
  - If it fails: if MySQL is down, the reverse outbox grows with no user impact, and rollback stays possible once it drains. If Postgres is down, writes return 503. This is the one point where a Postgres failure fails writes, and it happens only after the switch.

- [ ] **11. Rollback to MySQL (until step 12).**
  - Starts: an operator decision.
  - Does:
    1. Write `paused` (epoch+1) to Postgres, the store the instances read now. Wait 12 s. No write is still running after that.
    2. Drain the reverse outbox to zero. Check that every Postgres row has a MySQL row at the same version, and that every Postgres tombstone has a MySQL tombstone. The reverse worker stops here.
    3. Copy the erasure work list rows from Postgres to MySQL, keeping each row's state, so the MySQL sweeper can finish them. Set MySQL's `AUTO_INCREMENT` to max(id)+1, so MySQL cannot assign an id that Postgres already used.
    4. Write mode `mysql` (epoch+2) to MySQL first, then to Postgres. Instances keep polling Postgres, which says `paused`, until they see `mysql` there. Then they read and write MySQL. The `users.dual_write` flag is not changed and stays on. The forward worker runs again, so each write commits to MySQL with an outbox row and an inline copy. Copies of rows that already match are no-ops. New MySQL rows are inserted into Postgres.
  - Pause budget: at most 90 s. If step 4 has not been applied by 75 s, abort. Write `pg` (epoch+3) to Postgres first, then to MySQL. The reverse worker runs again. Writes went to Postgres, and the reverse outbox holds whatever MySQL has not received, so no write is lost. If step 4 has already been applied, MySQL is the source of truth and the abort is no longer possible. Run a full compare before any new switch.
  - State: the control row in Postgres and MySQL, the erasure work list, and the MySQL `AUTO_INCREMENT`.
  - If it fails: follow the abort path above. Run a full compare before any new switch.

- [ ] **12. Postgres-only writes.** No sooner than 14 days after `source_switched_at`.
  - Starts: an operator approves it. The 14-day gate has passed, the latest reverse compare is clean, and a snapshot of the MySQL table has been taken.
  - Does: sets the mode to `pg_only`. The source of truth does not change, so no write pause is needed. The reverse worker drains the outbox to zero and stops. MySQL is no longer written. Reads keep the MySQL fallback, counted as stale.
  - Note: rollback to MySQL is impossible after this step.
  - If it fails: nothing changes before the flip. After it, recovery comes from the snapshot.

- [ ] **13. Drop the MySQL `users` table.**
  - Starts: step 12 is complete, and a separate change request is approved after the snapshot is verified.
  - Does: removes the reverse worker, the forward outbox, the MySQL tombstone table and the MySQL read fallback. Removes the MySQL paths in `UserRepository` and updates the lint rule. Then drops the table.
  - If it fails: there is no rollback to MySQL. Restore from the snapshot.

## What happens when things fail

| Failure | What happens | How it is noticed |
|---|---|---|
| Postgres down during dual writes | Requests succeed. Outbox rows pile up. The forward worker retries every 1 s. | Outbox age alert |
| An instance cannot poll the control row | Its writes stop when its lease runs out, 10 s after its last poll was sent. Its reads continue. | Lease and `users_mode_applied` metrics |
| MySQL down before the switch | Writes fail as they do today, because MySQL is the source of truth. | Existing MySQL alerts |
| MySQL down after the switch | Writes continue. The control row and erasure work list are in Postgres, so leases stay valid. The reverse outbox grows and drains when MySQL returns. | Reverse outbox depth |
| Postgres down after the switch | Writes return 503. Reads continue from the MySQL fallback, counted as stale. | Reverse worker and write error alerts |
| Switch stalls with `pg` in Postgres only | Instances stay paused. Retry the MySQL write, or abort as in step 9. | Operator sees the error and the paused writes |
| Replica lag above 5 s | Backfill and compare pause. Reads are not affected. | `mysql_replica_lag_seconds` |
| Backfill runner crashes | The next runner resumes after the last committed checkpoint. | Checkpoint age |
| Erasure while Postgres is down | Erasure waits and is retried by the sweeper. No user request waits. | Alert |
| Read returns an older version | A user who has just written may read the old row until their copy lands. This is normally seconds. | Outbox age |
| Sampled read mismatch | The ramp stops and returns to the compare step. | `users_read_mismatch_total` |
| Control-row write fails | Nothing changes. Retry the failed write with the same epoch before any other step. For the switch, see step 9. | Operator sees the error |

## Open questions

- A user who has just written may see their old row until the copy lands. The plan accepts this. Decide whether a read-your-writes rule is needed before the 1% ramp.
- The Postgres id headroom is 1,000,000. The real create rate has not been checked against that number.
- The values 10 s (lease), 60 s (backfill lease), 1% (read sampling) and 500 (outbox pass size) are first choices. They need a load test before dual writes are turned on.