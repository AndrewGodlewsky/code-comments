# Migrate `users` from MySQL 8 to Postgres 16

## Decisions

- **Outbox in the source database.** Every `UserRepository` write inserts or updates one row in `user_sync_outbox` in the same MySQL transaction as the `users` write. The row is keyed by user id, and `seq` is bumped on every change. A relay worker reads the outbox and applies the current row to Postgres. The write path never calls Redis, so a Redis outage (1 s enqueue timeout) cannot fail a request. The outbox also avoids the `jobs:dead` trap, because nothing is dead-lettered.
- **Repair, backfill and comparison run as long-lived worker loops**, not as Redis jobs. A multi-day backfill does not fit the job retry budget (5 attempts, about 15 minutes), and copies must never be dropped.
- **Deletes leave tombstones.** Every copy into a store takes a per-id lock, checks the tombstone table, and only then applies the version rule. Tombstones are kept forever. They are small: about 2,000 per day.
- **Switch coordination uses a control row** (`user_store_control`, in MySQL). Each write reads it `FOR SHARE` inside its transaction. A switch takes it `FOR UPDATE`, which waits for in-flight writes and blocks new ones. Flags are not used for switches, because they can disagree for 30 s and cannot fence in-flight writes. Flags are used only for the read ramp and kill switches.
- **Ids.** Before Phase 1, MySQL assigns ids as it does today. At the switch to Postgres, the Postgres identity sequence is set while writes are paused, to the greater of the Postgres max id and the MySQL `AUTO_INCREMENT` counter. During the reverse-mirror window, Postgres-created rows are written to MySQL with their explicit ids, so the MySQL counter always stays above every id Postgres has issued. A rollback therefore needs no sequence step.
- **Rule for every copy into either store**: insert if the row is missing and no tombstone exists, or replace only where the stored `version` is lower. Never otherwise.

## Phase 0: Prepare schemas (no behaviour change)

- [ ] **0.1 Create Postgres objects in `pg-core`.**
  - Starts: a one-off migration, run by hand or CI.
  - Changes: `users` (`id BIGINT PRIMARY KEY`, `email VARCHAR(320) NOT NULL`, `name`, `plan`, `version INT NOT NULL`, `updated_at timestamp(3) NOT NULL`, with a unique index on `lower(email)` to match MySQL's case-insensitive unique key; confirm the MySQL column collation first). Also `user_tombstones(user_id BIGINT PRIMARY KEY, erased_at)`, `user_backfill_state(job PRIMARY KEY, last_id, lease_owner, lease_expires_at, completed_at)` and `user_compare_state(pass_id, last_id, mismatches_found, started_at, completed_at)`.
  - State: Postgres.
  - If it fails: all statements use `IF NOT EXISTS`. Nothing reads these tables yet, so a wrong definition can be dropped and recreated.

- [ ] **0.2 Create MySQL objects in `core`.**
  - Starts: the same migration tooling.
  - Changes: `user_sync_outbox(user_id PRIMARY KEY, op ENUM('upsert','delete'), seq BIGINT NOT NULL, attempts, next_attempt_at, updated_at)`. Also `user_tombstones(user_id PRIMARY KEY, erased_at)`, which the reverse mirror needs later. Also `user_store_control(id = 1, source = 'mysql', mode = 'normal', paused = 0, epoch = 1)`.
  - State: MySQL.
  - If it fails: the changes are additive and have no effect until Phase 1 is deployed.

## Phase 1: Dual write (release R1)

- [ ] **1.1 Deploy release R1 (`UserRepository` writes outbox rows).**
  - Starts: a normal web-tier deploy.
  - Changes: `create`, `update` and `delete` each write `users` and the outbox row in one MySQL transaction. `update` keeps its `StaleWrite` check, and the outbox row is written only after the update succeeds. The `users.sync_paused` kill-switch flag stops the relay (see 1.2). With the flag on, the outbox keeps growing and MySQL is unaffected.
  - State: the outbox row, in the same MySQL transaction as the write.
  - If it fails: a MySQL failure fails the request exactly as it does today. A failed outbox insert rolls back the write, which is also MySQL-only. Rolling back R1 is dangerous: pre-R1 pods write without outbox rows, so those changes never reach Postgres. Any rollback of R1 after this point must reset the backfill cursor to zero and run a full comparison again.

- [ ] **1.2 Start the relay worker `users-sync-relay` (N replicas).**
  - Starts: deployed with R1, runs continuously. Replicas coordinate with `FOR UPDATE SKIP LOCKED`.
  - Changes: claims up to 500 outbox rows on the MySQL primary, then for each row reads the current `users` row from the primary (not the replica).
    - Upsert, row found: in one Postgres transaction, take the per-id lock, skip if a tombstone exists, otherwise `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
    - Delete, or row absent on the primary: in one Postgres transaction, take the per-id lock, insert the tombstone, delete the Postgres row.
    - On success, delete the outbox row only if its `seq` still equals the claimed value, so a change made during the copy is not lost.
  - State: the outbox in MySQL, and the Postgres data itself.
  - If it fails: Postgres errors back off exponentially, from 1 s up to 5 min, and the outbox row stays. Rows are never dead-lettered. Alert when the oldest outbox row is more than 60 s old (warning) or more than 5 min old (page). A unique violation on `lower(email)` is retried. The row that holds the conflicting email always has its own pending outbox entry, which resolves the conflict.

- [ ] **1.3 Gate G1: all instances dual-write, then the operator starts backfill.**
  - Starts: the gate is checked automatically, then the operator sets the flag `users.backfill_enabled = true`.
  - Gate: every pod reports R1 on the deploy-version metric for at least 10 minutes. The relay has been running with oldest-outbox age under 60 s for the last hour. Reading the `app_flag_value` metric is not enough on its own, because old binaries cannot be flagged into writing outbox rows.
  - Why it matters: a row updated after the backfill cursor has passed its id is caught only by the outbox. A row can also get a low id from a long-running transaction that commits late. Both cases require every writer to produce outbox rows.
  - If it fails: the flag stays off. Nothing has changed.

## Phase 2: Backfill

- [ ] **2.1 Start the backfill worker `users-backfill` (one replica, with a lease in Postgres).**
  - Starts: Gate G1 holds and `users.backfill_enabled` is true.
  - Changes: copies rows from the MySQL replica into Postgres, in batches. Loop:
    1. Acquire or renew the lease in `user_backfill_state` (60 s expiry, renewed every batch). Stop if the lease is lost.
    2. Read `last_id` from Postgres.
    3. Check replica lag, from `mysql_replica_lag_seconds`, before every batch. If lag is above 5 s, or the reading is more than 10 s old, sleep 1 s and check again. Export a `backfill_paused_lag` metric while paused.
    4. `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` on the replica.
    5. If no rows come back, set `completed_at` and go to 2.2.
    6. In one Postgres transaction: for each row, take the per-id lock, check the tombstone, apply the version-rule upsert, then set `last_id` to the batch's last id. Commit.
  - State: the cursor is in Postgres, committed in the same transaction as the batch. A crash after the commit resumes after that batch. A crash before it redoes the batch, which is harmless because of the version rule.
  - If it fails: replica or Postgres errors back off and leave the cursor unchanged. If a batch hits an email unique violation, the transaction rolls back and the batch is retried row by row. The cursor advances only past rows that have been copied. A row still blocked after 10 min raises an alert, and the comparator (3.1) keeps tracking it.

- [ ] **2.2 Backfill complete.**
  - Starts: automatically, when the last batch comes back empty and `completed_at` is set.
  - Changes: nothing more. Phase 3 is already running.
  - State: `user_backfill_state`.
  - If it fails: not applicable. Rows created after this point are covered by the outbox.

## Phase 3: Continuous verification and repair

- [ ] **3.1 Run the comparator `users-compare` (one replica, lease in Postgres).**
  - Starts: when 2.1 starts. It runs continuously, and each full pass is what the read gate in 4.1 relies on.
  - Changes: compares id ranges of 2,000 ids between the replica and Postgres, using row counts and a hash over `(id, version, email, name, plan, updated_at)`. Normalise first: trailing spaces (MySQL pads), and `updated_at` in UTC on both sides. Skip ids with a pending outbox row. For ranges with a mismatch, re-read those ids from the MySQL primary and compare again. A confirmed mismatch gets an outbox upsert row in MySQL, so the relay repairs it automatically. A Postgres row with no MySQL row and no tombstone is also a mismatch. The relay turns it into a delete and tombstone, and the comparator raises a high-severity alert, because this should not happen.
  - Also pauses for replica lag, as in 2.1.
  - State: `user_compare_state`, in Postgres.
  - If it fails: a restart resumes the pass from `last_id`. Mismatches are never cleared silently, because each one is counted.

## Phase 4: Read cutover

- [ ] **4.1 Gate G2: a clean full comparison.**
  - Starts: when 2.2 has completed and a full comparator pass that started after 2.2 finishes with zero mismatches found. At the start of the pass the outbox must be empty.
  - Changes: nothing. This is a go or no-go check.
  - State: `user_compare_state`.
  - If it fails: any mismatch found, even one that was repaired, starts a new full pass. The gate counts mismatches found, not mismatches left open.

- [ ] **4.2 Read ramp with the flag `users.read_from_pg` (percentage).**
  - Starts: Gate G2 holds. The operator changes the flag.
  - Changes: reads go through `flags.enabled_for(users.read_from_pg, user_id)`, which keeps each user on one store. Steps: 1%, then 10%, 50%, 100%. Hold each step for at least 1 hour and until every instance reports the new value on `app_flag_value{flag="users.read_from_pg"}` (at most 30 s of skew). The read path tries Postgres with a 100 ms timeout. On any error, or any miss, it falls back to the MySQL replica. A miss is never returned as a 404.
  - Staleness: Postgres trails the source by the outbox lag, normally seconds. Writes still use the MySQL primary with `expected_version`, so no update is lost. Reads may be a few seconds old. Track this with `users_outbox_oldest_age_seconds`.
  - State: the flag only. No user data is held here.
  - If it fails: move the flag back down. It takes effect in at most 30 s, and reads continue through the MySQL fallback. Each step needs its gates met before the next step: the fallback rate under 0.1%, Postgres p99 under 20 ms, and no new mismatches from the comparator.

- [ ] **4.3 Hold at 100% for 72 hours.**
  - Starts: when every instance reports 100 on the read flag.
  - Changes: nothing.
  - Clock resets: if the flag drops below 100 at any point, or the comparator finds a mismatch, the clock stops and the step goes back to 4.1 for a new full pass. The clock also resets if any outbox row is older than 5 min.
  - State: the flag and the comparator's state.
  - If it fails: as above.

## Phase 5: Switch the source of truth to Postgres (S1)

- [ ] **5.1 Pre-checks.**
  - Starts: the operator begins the switch runbook once 4.3 is satisfied.
  - Checks: 4.3 is met. The most recent full comparator pass has zero mismatches and finished after the read flag reached 100. The outbox's oldest row is under 5 s old. The replica lag is normal. The Postgres identity sequence for `users` exists. A rollback owner is on call.
  - If it fails: do not start.

- [ ] **5.2 Pause writes (t0).**
  - Starts: the runbook.
  - Changes: `UPDATE user_store_control SET paused = 1, epoch = epoch + 1` on the MySQL control row, with a 5 s lock-wait timeout. Writes that start after this get a retryable 503 with `Retry-After: 1`. Writes already in flight finish. Reads are unaffected.
  - State: the control row.
  - If it fails: if the lock cannot be taken within 5 s, abort and do not pause. Abort if the pause would exceed the 60 s budget for this step.

- [ ] **5.3 Drain the outbox.**
  - Starts: when 5.2 completes.
  - Changes: waits until `user_sync_outbox` is empty, which means the relay has applied every final change to Postgres. Checked every second.
  - State: the MySQL outbox.
  - If it fails: if the outbox is not empty by t0 + 60 s, set `paused = 0, epoch = epoch + 1` and leave the source as it is. Alert and abort. No data is lost, and writes resume.

- [ ] **5.4 Set the Postgres sequence.**
  - Starts: when 5.3 completes. The MySQL counter is frozen because writes are paused.
  - Changes: `setval('users_id_seq', GREATEST(max(id) in Postgres, MySQL AUTO_INCREMENT from information_schema))`.
  - State: the Postgres sequence.
  - If it fails: abort as in 5.3.

- [ ] **5.5 Flip the source to Postgres (within the pause budget).**
  - Starts: when 5.4 completes.
  - Changes: one MySQL transaction sets `source = 'pg', paused = 0, epoch = epoch + 1`. From now on each write holds the control row `FOR SHARE`, writes to Postgres first with a Postgres outbox row in the same transaction, and returns. The reverse relay (7.1) begins draining the Postgres outbox into MySQL.
  - State: the control row. Postgres now holds the authoritative data.
  - If it fails: a failed flip is an abort, handled as in 5.3.

- [ ] **5.6 Confirm the switch.**
  - Starts: when 5.5 completes.
  - Checks: writes succeed on Postgres, `users_store_epoch` matches on every instance, and the reverse outbox is draining. Record the total pause, which must be 90 s or less.
  - If it fails: a rollback is possible at any time in Phase 6.

Reads after S1 use Postgres with the MySQL replica as fallback. The MySQL copy is kept close to current by the reverse mirror. If Postgres is unavailable, writes return a retryable 503. They never go to MySQL, because that would create two sources of truth.

## Phase 6: Reverse-mirror window (rollback possible, at least 14 days)

- [ ] **6.1 Run the reverse mirror.**
  - Starts: at the S1 flip (5.5).
  - Changes: the same design as 1.2, with the roles reversed. Postgres outbox rows are read with `FOR UPDATE SKIP LOCKED`, and the current row is read from Postgres. Each row is written to MySQL with `INSERT ... ON DUPLICATE KEY UPDATE`, applying the version guard, so an existing row changes only where its `version` is lower. Explicit ids are written, which moves the MySQL `AUTO_INCREMENT` counter above them. Deletes write a MySQL tombstone and remove the row.
  - State: the Postgres outbox, and MySQL.
  - If it fails: the same backoff and alerting as 1.2. Writes are not affected, because the source is Postgres.

- [ ] **6.2 Run the reverse comparator.**
  - Starts: at S1.
  - Changes: the same as 3.1, comparing Postgres (source) with MySQL. Repairs go through the reverse outbox.
  - State: its own pass state.
  - If it fails: a mismatch pauses nothing, but any mismatch is an alert and must be explained before Phase 7.

- [ ] **6.3 Roll back to MySQL (if needed, any time in this window).**
  - Starts: the operator, on a rollback decision.
  - Changes: the same procedure as 5.2 to 5.6, with `source = 'mysql'`. The drain step waits for the reverse outbox to empty. The MySQL counter is already above every Postgres id, because each Postgres-created row was mirrored with its explicit id, so no sequence change is needed. Reads follow the source, with fallback to the other store.
  - Abort rule: if the drain does not finish within 60 s, set `paused = 0` and stay on Postgres. The mirror keeps running, and no write is lost.
  - State: the control row.
  - If it fails: as above. Writes are paused for at most 90 s.

## Phase 7: Postgres-only writes (S2, no sooner than 14 days after S1)

- [ ] **7.1 Gate.**
  - Starts: 14 days after the flip in 5.5 (required by the brief). The reverse comparator must also show zero mismatches over those 14 days. This second condition is our addition.
  - Changes: nothing.
  - If it fails: stay in Phase 6.

- [ ] **7.2 Pause, drain and switch to Postgres-only (S2).**
  - Starts: the operator, once 7.1 is met.
  - Changes: repeat 5.2 and 5.3, then set `mode = 'pg_only'`. Writes stop producing reverse outbox rows and the reverse mirror stops. The application's read fallback to MySQL is removed, because MySQL is no longer kept current, and serving it would return stale data. The MySQL app user is also revoked from `INSERT`, `UPDATE` and `DELETE` on `core.users`, so nothing can write to the frozen table by mistake.
  - State: the control row.
  - If it fails: abort as in 5.3. Before this step, rolling back remains possible.
  - Trade-off: from this point, reads depend on Postgres availability, so they are no longer served from MySQL. Postgres failover handles the availability risk.

- [ ] **7.3 Point of no return.**
  - Starts: when 7.2 completes.
  - Changes: rollback to MySQL is no longer possible. Take a final logical snapshot of `core.users` and restore it to a scratch instance to test it.
  - If it fails: if the snapshot or restore test fails, do not move on to Phase 8.

## Phase 8: Retire MySQL

- [ ] **8.1 Read-only retention (our addition).**
  - Starts: 7.3 completes.
  - Changes: keep `core.users` read-only for 30 days. Only the snapshot is needed.
  - State: MySQL and the snapshot.
  - If it fails: extend the retention period.

- [ ] **8.2 Drop the MySQL table.**
  - Starts: the operator, after 8.1 is met and the restore test has passed.
  - Changes: `DROP TABLE core.users`. Also drop `user_sync_outbox` and the MySQL tombstones. Keep the Postgres tombstones permanently. Remove the reverse-relay code, the comparator and the lint allowlist entry for migration code. Remove the MySQL fallback code.
  - State: none remaining in MySQL.
  - If it fails: the drop cannot be undone. If the restore test is not good, do not drop.

## Cross-cutting rules

- The migration SQL lives in a module that is added to the `no-raw-users-sql` lint allowlist in the same PR as R1. Review that module as the only other place allowed to touch `users`.
- Alerts: oldest outbox row age, replica lag, backfill rate and `last_id`, comparator mismatches found (any non-zero value is an alert), Postgres read fallback rate, the count of 503s per pause, and `users_store_epoch` per instance.
- Every switch (5.5, 6.3, 7.2) has a 90 s total pause budget. Each one aborts and unpauses if its drain runs past 60 s.
