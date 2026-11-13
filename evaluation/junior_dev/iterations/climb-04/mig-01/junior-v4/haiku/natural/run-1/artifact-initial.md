# Move `users` from MySQL 8 to Postgres 16

## Design decisions

- **One copy rule everywhere.** Dual write, the repair sweeper, backfill and the erasure copy all use one function. In one Postgres transaction it takes `pg_advisory_xact_lock(user_id)`, skips the id if it is in `users_tombstones`, and then runs `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. The lock makes a copy and an erasure of the same id run one after the other, so a copy cannot commit after the erasure has checked for a tombstone.
- **Repair is an in-app sweeper, not the job queue.** `jobs.enqueue` raises when Redis is down, and dead-lettered jobs are never retried. The sweeper is a loop run by every instance, with one leader chosen by a session-level Postgres advisory lock. It scans `users` by `updated_at` on the replica, with a 60 s overlap, and scans tombstones by sequence number. Cursors and progress live in Postgres `migration_state`.
- **Dual write never raises.** After the MySQL commit, the write reads the row back inside the same MySQL transaction and copies that snapshot to Postgres with a 250 ms timeout. Any error is logged and counted in `users_pg_dual_write_failures_total`.
- **Deletes.** The MySQL delete and an insert into MySQL `user_tombstones` happen in one transaction. Tombstones are kept forever, so a deleted id can never be copied back.
- **Coordination.** One flag, `users.source`, takes the values `mysql`, `fenced` or `postgres`. In `fenced`, writes return a retryable 503. The source only flips after every instance reports `fenced`, so two instances can never write to different stores.
- **Ids.** MySQL AUTO_INCREMENT assigns ids until the first switch. On each entry to Postgres-as-source, `users_id_seq` is set to MySQL's next id (from `information_schema` on the primary, not `max(id)`) or the current Postgres value, whichever is higher, plus a margin of 1,000,000. While Postgres is the source, MySQL receives explicit ids. On rollback, MySQL AUTO_INCREMENT is set above the Postgres sequence.
- **Email.** Confirm the MySQL collation first. Then match its case and trailing-space rules: unique index on `lower(email)` in Postgres, and compare on `lower(rtrim(email))`. An out-of-order copy can hit a unique collision (an email still held by another row). Treat it as retryable: record the row in `migration_pending` and retry it later.
- **Flags** (used throughout): `users.dual_write` (bool), `users.source` (string), `users.pg_read_percent` (percentage, bucketed with `enabled_for(name, user_id)` so a user stays on one store while the percentage ramps), `users.mysql_shadow` (bool). Each instance refreshes flags every 30 s, so every gate below is checked on `app_flag_value{flag=...}` across all instances, not on the flag value alone.

## Checklist

### Phase 0: Prepare (no behaviour change)

- [ ] **1. Create the schemas.**
  - Starts: the migration is merged and runs in the normal deploy.
  - Changes: Postgres `pg-core` gets `users` (`id BIGINT PRIMARY KEY`, with no default; `email VARCHAR(320)`, `name`, `plan`, `version INT NOT NULL`, `updated_at TIMESTAMP(3)`), a unique index on `lower(email)`, `users_tombstones (seq BIGSERIAL, user_id BIGINT PRIMARY KEY, deleted_at)`, `migration_state (key PRIMARY KEY, value)`, `migration_pending (direction, user_id, attempts, last_error, next_try_at)` and `users_id_seq`. MySQL `core` gets `user_tombstones (seq BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT UNIQUE, deleted_at DATETIME(3))`, and an index on `users (updated_at, id)` built online with `ALGORITHM=INPLACE, LOCK=NONE`.
  - State: the schemas.
  - If it fails: every statement is `IF NOT EXISTS` and can be re-run. MySQL aborts a failed online index build, and the build is retried. No request is affected.

- [ ] **2. Rehearse the switch timing in staging.**
  - Starts: step 1 is done in staging.
  - Changes: nothing in production. Run steps 10 to 13 and 15 with the real flag refresh interval and measure the 503 window. The target is 80 s or less, and the hard limit is 90 s.
  - State: the measurements are recorded with the runbook.
  - If it fails: adjust the drain budget and abort thresholds in the runbook before production. Do not start step 10 until the rehearsal is under the limit.

- [ ] **3. Deploy the dual-write build with every flag off.**
  - Starts: the release is deployed to every instance.
  - Changes: `UserRepository` gets the copy function, the dual-write path and the tombstone write. The erasure delete writes a tombstone in the MySQL transaction, always and not behind a flag, so that deletes before dual write are tracked too. Flags start as `users.dual_write=false`, `users.source=mysql`, `users.pg_read_percent=0` and `users.mysql_shadow=true`. Each instance exports `users_repo_build{version}`. The Postgres pool gets an acquire timeout of 250 ms or less and a statement timeout.
  - State: code and flags only. No data moves.
  - If it fails: roll back the deploy. If the tombstone insert fails inside the erasure transaction, that erasure attempt fails and the erasure job retries it.

- [ ] **4. Turn on dual write.**
  - Starts: step 3 is live on every instance, meaning no instance runs an older build. An operator sets `users.dual_write=true`.
  - Gate for step 6: every instance shows `app_flag_value{flag="users.dual_write"}=1` and the new `users_repo_build` version. The gate stays green for 60 s, which is two refresh cycles, before it counts as passed.
  - Changes: every write commits to MySQL, then copies its snapshot to Postgres. A Postgres failure is counted and never returned to the caller.
  - State: the flag. Failed copies go into `migration_pending`.
  - If it fails: set the flag back to false. MySQL is unaffected. The sweeper in step 5 scans by `updated_at` and not by flag, so writes made without dual write are still repaired.

- [ ] **5. Start the repair sweeper.**
  - Starts: step 4 is switched on (the operator flips the flag). The sweeper's cursor starts at the flip time minus 10 minutes.
  - Loop, run by the instance that holds the advisory lock `pg_try_advisory_lock(<sweeper key>)` on a dedicated session. Other instances retry the lock every 10 s.
    1. Read MySQL tombstones with `seq > tomb_seq` on the replica. For each one, under the copy lock, `DELETE` the user from Postgres and `INSERT` the tombstone with `ON CONFLICT DO NOTHING`. Advance `tomb_seq` after each batch.
    2. Read MySQL `users WHERE updated_at >= cursor ORDER BY updated_at, id LIMIT 2000` on the replica, with the lag check from step 6. Copy each row with the copy function. Set the cursor to the largest `updated_at` seen minus 60 s, and only after the batch has been applied or recorded as pending.
    3. Rows that fail to copy go into `migration_pending`. Retry them with backoff and delete them on success.
  - Metrics: repair lag (now minus cursor) and pending count. Alert when lag is above 5 min or any pending row is older than 15 min.
  - State: `migration_state` (`sweep_users_cursor`, `sweep_tomb_seq`), `migration_pending`, and the advisory lock.
  - If it fails: the loop retries. If the leader dies, its session lock is released and another instance takes over within seconds. The cursor never moves past work that has not been done.

- [ ] **6. Backfill, then the full comparison.**
  - Starts automatically once step 4's gate is green. No operator action is needed.
  - Backfill loop:
    1. Read `backfill_cursor` (default 0) from `migration_state`.
    2. Read `mysql_replica_lag_seconds`. If it is above 5 s or missing, sleep 5 s and check again. A missing value counts as too high.
    3. Read `SELECT id, email, name, plan, version, updated_at FROM users WHERE id > :cursor ORDER BY id LIMIT 2000` on the replica.
    4. Check the lag again. If it is above 5 s, drop the batch and return to step 2.
    5. In one Postgres transaction, run the copy function on each row and set `backfill_cursor` to the last id read. Commit.
    6. Sleep 200 ms between batches to share the replica with reporting jobs.
  - When a read returns no rows past the cursor, set `backfill_done=true` and record the max id.
  - Full comparison, which must end with zero mismatches:
    - Scan ids in order in ranges of 2,000. For each range, hash `(id, lower(rtrim(email)), rtrim(name), plan, version)` on the replica and on Postgres, and compare counts too. For each range whose hash differs, compare the rows one by one.
    - Compare the two tombstone sets, and check that no Postgres row has a tombstoned id.
    - For any row that differs, or was updated in the last 60 s, reread both sides after a 30 s settle. Missing rows or rows with a lower version in Postgres are fixed with the copy function. A Postgres row with a higher version is never overwritten. It is reported and blocks the gate. Postgres rows that are not tombstoned and have no MySQL row are reported and block the gate. Only tombstoned ids are deleted automatically.
    - The gate passes when one complete pass ends with no unresolved mismatch. Record the run id and time in `migration_state`.
  - State: `migration_state` (`backfill_cursor`, `backfill_done`, the compare run). Progress is committed in the same Postgres transaction as each batch.
  - If it fails: a crash resumes after the last committed cursor. The replayed batch is safe because the version rule makes copies idempotent. Postgres or replica errors back off and retry, and users are not affected. If the gate turns red later, backfill need not stop, because the sweeper covers writes. An unexplained mismatch keeps the gate closed until someone has investigated it.

### Phase 1: Reads

- [ ] **7. Ramp reads to Postgres.**
  - Starts: the step 6 comparison gate has passed.
  - Changes: set `users.pg_read_percent` to 1, 10, 50, then 100. Hold each step for at least 1 hour. Move on only when the error rate is flat and sampled shadow reads (1% of Postgres reads, compared with the replica) show no unrepaired mismatch.
  - Reads never fail: a Postgres read error falls back to the MySQL replica in the same request, and `users_pg_read_fallback_total` is counted.
  - State: the flag.
  - If it fails: set the percentage back to 0. Reads return to MySQL, and no data moves. A read may briefly see a row whose Postgres copy failed. The sweeper bounds that window to the repair lag.

- [ ] **8. Hold reads at 100% on Postgres for at least 3 days.**
  - Starts: the percentage reaches 100 on every instance (checked on the metric). The clock is `reads_pg_100_since` in `migration_state`.
  - Changes: nothing. Keep the sweeper running, and run the step 6 comparison once a day.
  - The clock resets if the percentage drops below 100, or if a mismatch is not repaired within 1 hour.
  - If it fails: follow step 7's rollback, then restart the clock when reads are back at 100%.

### Phase 2: Switch the source of truth to Postgres

- [ ] **9. Check the preconditions.**
  - Starts: an operator asks for the switch.
  - Check: reads at 100% for at least 3 days; a comparison pass with zero mismatches in the last 24 h; `backfill_done=true`; sweeper lag under 60 s; no pending rows; every instance on the new build.
  - State: none changed.
  - If it fails: do not start the switch. Fix the failing check first.

- [ ] **10. Fence writes (T0).**
  - Starts: an operator sets `users.source = fenced`.
  - Changes: writes return 503 with `Retry-After`. Reads continue. Each instance finishes its in-flight writes, reported on `users_writes_in_flight`.
  - Wait until every instance reports `fenced` and in-flight is 0. Propagation takes up to 30 s.
  - If it fails: if any instance has not reported `fenced` within 35 s, run step 13 (abort).

- [ ] **11. Drain (20 s budget).**
  - Starts: step 10 is complete.
  - Changes: run the forward sweeper once against the MySQL primary, not the replica, for rows with `updated_at >= cursor - 60 s` and for tombstones since `tomb_seq`. Confirm that no rows are pending and the hashes match for the drained window. Read the next AUTO_INCREMENT value from MySQL `information_schema` on the primary. Set `users_id_seq` to the larger of that value and the current Postgres sequence value, plus 1,000,000.
  - State: cursors and the sequence.
  - If it fails: if the drain is not finished within 20 s, run step 13 (abort).

- [ ] **12. Flip the source to Postgres (T1).**
  - Starts: every instance reports `fenced` (checked on the metric), and step 11 is done.
  - Changes: set `users.source = postgres` and record `sot_switched_at`. Writes now go to Postgres first. Creates take ids from `users_id_seq`. Updates and deletes check `version` in Postgres, then the MySQL shadow copy is written with an explicit id and a 250 ms timeout. A Postgres failure during a write returns a retryable 503, because Postgres is now the source and there is nothing else to fall back to. A MySQL shadow failure is counted and repaired by step 14.
  - Pause: the global pause is the fence propagation (30 s) plus the drain (20 s) plus the flip propagation (30 s), which is 80 s at worst. Measure it from the first 503 to the first successful write.
  - If it fails: the flag is global, so the only realistic problem is an instance that has not refreshed. It stays `fenced` and refuses writes, which is safe. Investigate before continuing.

- [ ] **13. Abort (any time before step 12 completes).**
  - Starts: a step 10 or 11 timeout, or a failed check.
  - Changes: set `users.source = mysql`. No Postgres-source writes have happened, so no drain is needed. The pause is at most 30 s of propagation. Worst case, a step 11 abort is 35 + 20 + 30 = 85 s.
  - State: the flag.
  - If it fails: retry. Writes stay refused until every instance sees `mysql`.

- [ ] **14. Run the reverse sweeper (Postgres as source).**
  - Starts: step 12.
  - Loop: the same as step 5, but in the other direction, and leader-elected with its own lock. It scans Postgres `users` by `updated_at` and `users_tombstones` by `seq`, and applies to MySQL primary:
    - Update by id where `version < incoming`; if no row changed, insert.
    - Deleting a tombstoned id deletes it from MySQL and inserts the tombstone.
    - Do not use `ON DUPLICATE KEY UPDATE`, because it also fires on the email unique key and could update the wrong row. Email conflicts are recorded in `migration_pending` with `direction='to_mysql'`.
  - State: `rsweep_users_cursor`, `rsweep_tomb_seq` in Postgres `migration_state`, and pending rows.
  - If it fails: as in step 5. MySQL is a shadow and no user sees the lag. Rollback in step 15 is blocked until reverse lag is under 60 s and pending is empty.

- [ ] **15. Roll back to MySQL (allowed until step 17).**
  - Starts: an operator decides to roll back. Preconditions: reverse lag under 60 s and pending empty.
  - Changes, in order:
    1. Set `users.source = fenced`.
    2. Wait until every instance reports `fenced` and in-flight is 0. If not within 35 s, set `users.source = postgres` to abort. That is a second pause of at most 30 s.
    3. Drain: run the reverse sweeper once against the Postgres primary for the window. Confirm no rows are pending and the hashes match. Budget 20 s. If it fails, set `users.source = postgres` to abort.
    4. Set the MySQL AUTO_INCREMENT to the larger of its current value and Postgres `last_value`, plus 1,000,000.
    5. Set `users.pg_read_percent = 0`, so reads go back to MySQL.
    6. Set `users.source = mysql` and reset the forward sweeper cursor to the fence time minus 10 minutes.
  - State: the flags, the MySQL AUTO_INCREMENT, and the cursors.
  - If it fails: as in the abort path above. Writes are never released until the drain has matched.

### Phase 3: Hold and monitor

- [ ] **16. Keep Postgres as source for 14 days.**
  - Starts: step 12.
  - Changes: nothing. Dual write (the MySQL shadow), the reverse sweeper and the daily comparison keep running. The clock is `pg_source_since` in `migration_state`.
  - Rollback (step 15) stays possible for the whole period.
  - If it fails: run step 15.

- [ ] **17. Switch to Postgres-only writes.**
  - Starts: 14 days have passed since `sot_switched_at`, and reads have been at 100% on Postgres.
  - Changes: take a final snapshot of MySQL `users` and `user_tombstones`, and check that it restores. Then set `users.mysql_shadow = false`. Writes go only to Postgres, and the reverse sweeper stops. This does not change the source of truth, so there is no fence and no pause. Instances on older flag values for up to 30 s still write MySQL, which does no harm.
  - State: the flag and the snapshot.
  - Rollback to MySQL is no longer possible after this step. If the flag is set back to true, MySQL is behind by the gap. Run a full comparison in reverse before any further rollback.

- [ ] **18. Drop the MySQL table.**
  - Starts: step 17 has been live for the retention period. The brief requires only that the drop happens after step 17. A 30-day retention is recommended but is a decision for the owners.
  - Changes: drop `users` and `user_tombstones` in MySQL. Remove the dual-write, forward and reverse sweeper code, the backfill code, the flags and the `no-raw-users-sql` exception. Update `existing/users_table.md`.
  - State: the restored snapshot is the only way back, so the snapshot must be verified before the drop.
  - If it fails: the drop cannot be undone. Do not run it until the snapshot restore check has passed.
