# Move `users` from MySQL 8 to Postgres 16

## What this is

The `users` table moves from MySQL 8 to Postgres 16 with no downtime. Today MySQL is the only store. The plan copies every write to Postgres too (dual write), fills Postgres with the existing rows (backfill), and checks that the two tables match. Reads then move to Postgres in steps. Last, the source of truth switches to Postgres after a short write pause. MySQL stays in sync until a later step, so we can roll back.

## Terms

- **Source of truth**: the store that decides a row's value. Set by the flag `users.source`: `mysql`, `fenced` (writes get a retryable 503), or `postgres`.
- **Copy function**: the only code that writes a row into Postgres. In one Postgres transaction it locks the user id, skips tombstoned ids, and inserts the row or updates it only if the row is missing or has a lower `version`. This is the **version rule**.
- **Version**: starts at 1 on create. Each update adds 1 in the same SQL statement. No database trigger does this.
- **Tombstone**: a record that a user was erased. Kept forever in `users_tombstones` (Postgres) and `user_tombstones` (MySQL), so an erased id cannot come back.
- **Sweeper**: a loop on every instance. The instance holding its advisory lock copies recent changes and tombstones and retries failed copies. Failed copies wait in `migration_pending`.
- **Backfill**: copies all existing rows in id order.
- **Heartbeat**: every instance writes a row to Postgres `instance_status` every 5 s: its id, build, the flag values it uses, its `in_flight` write count, and `seen_at`.
- **in_flight**: a write counts from its start until its response is sent. That includes the Postgres copy and the tombstone apply.
- **Gate**: a check that passes only when every running instance has a heartbeat under 15 s old showing the expected value.
- **Flags**: `users.dual_write` (bool), `users.source`, `users.pg_read_percent` (0 to 100), `users.mysql_shadow` (bool). Each instance refreshes flags every 30 s.

## How the system runs

**Before the switch (source `mysql`)**
- Write: commit to MySQL first, then copy the committed row to Postgres with a 250 ms timeout. A failed copy is counted and recorded in `migration_pending`. It never fails the request.
- Delete: one MySQL transaction removes the user and inserts a tombstone. Then the request applies the tombstone to Postgres: it deletes the row and inserts the tombstone under the copy lock, with a 250 ms timeout. If that fails, the sweeper applies it.

**Which changes reach Postgres.** Three paths together cover every change:
- Writes after dual write is on: the request copy, with the sweeper as backup.
- Changes from 10 minutes before dual write was turned on onward: the sweeper, which scans MySQL by `updated_at`.
- Older rows: backfill. It starts at least 60 s after dual write is on, so it reads each row's current value.

**Reads.** `enabled_for("users.pg_read_percent", user_id)` decides per user, so a user stays on one store as the percentage rises. Bucketed users read the Postgres primary; everyone else reads the MySQL replica. A Postgres read error falls back to the MySQL replica in the same request and is counted. After step 12, all reads go to the Postgres primary.

**Writes after the switch (source `postgres`)**
- Create: take the id from `users_id_seq`, insert into Postgres, then shadow the row to MySQL with that id.
- Update: `UPDATE` in Postgres `WHERE id = ? AND version = <the version the caller read>`, adding 1 to `version`. Zero rows means `StaleWrite`, as today. Then shadow to MySQL.
- Delete: in Postgres, under the copy lock, insert the tombstone and delete the row. Then shadow the delete and tombstone to MySQL.
- Shadow to MySQL (when `mysql_shadow` is on): update where id matches and `version < incoming`. If no row changed, insert. Two writers of one change carry the same version, so the second changes nothing.
- If Postgres fails: return 503 with `Retry-After`. If the MySQL shadow fails: count it. The reverse sweeper repairs it.

**Ids.** Before the switch, MySQL AUTO_INCREMENT assigns ids. After step 12, creates take ids from `users_id_seq`, and MySQL receives the same id explicitly. Steps 11 and 15 move each counter past the other.

**Sweepers.** `migration_state.sot` gives the direction: `mysql` until step 12, `postgres` after it. While `sot=mysql`, the forward sweeper (step 5) runs. While `sot=postgres` and `mysql_shadow` is on, the reverse sweeper (step 14) runs. Each direction has its own cursors.

**Fence.** An instance that sees `fenced` refuses new writes, waits for its own `in_flight` to reach 0, and at once writes a heartbeat showing `fenced` and 0. Clients get the 503 and retry after `Retry-After`. If Postgres is down, heartbeats stop and the gates stay closed.

**Leaders.** The sweeper and the backfill each hold their own advisory lock, so a slow backfill cannot delay repair. An instance without a lock retries every 10 s. If a leader dies, its lock is released and another instance takes over within seconds.

## Checklist

### Phase 0: Prepare (no behaviour change)

- [ ] **1. Create the schemas.**
  - Starts: the migration runs in the normal deploy. First confirm the MySQL collation of `users.email`, and match its case and trailing-space rules in Postgres: a unique index on `lower(email)`, and comparisons on `lower(rtrim(email))`.
  - Does: in Postgres `pg-core`, creates `users` (`id BIGINT PRIMARY KEY`, no default; `email VARCHAR(320)`; `name`; `plan`; `version INT NOT NULL`; `updated_at TIMESTAMP(3)`), the unique index on `lower(email)`, `users_tombstones (seq BIGSERIAL, user_id BIGINT PRIMARY KEY, deleted_at)`, `migration_state (key PRIMARY KEY, value)`, `migration_pending (direction, user_id, attempts, last_error, next_try_at)`, `instance_status`, and `users_id_seq`. In MySQL `core`, creates `user_tombstones (seq BIGINT AUTO_INCREMENT PRIMARY KEY, user_id BIGINT UNIQUE, deleted_at DATETIME(3))`, and an index on `users (updated_at, id)` built with `ALGORITHM=INPLACE, LOCK=NONE`.
  - State: the schemas.
  - If it fails: every statement uses `IF NOT EXISTS` and can be re-run. MySQL aborts a failed online index build, and the build is retried. No request is affected.

- [ ] **2. Rehearse the switch in staging.**
  - Starts: step 1 is done in staging.
  - Does: runs steps 10 to 13 and 15 with the real 30 s flag refresh and measures the 503 window. Target 80 s or less; hard limit 90 s.
  - State: the measurements, kept in the runbook.
  - If it fails: adjust the drain budget and abort thresholds in the runbook. Do not start step 10 in production until the rehearsal is under the limit.

- [ ] **3. Deploy the dual-write build with all flags off.**
  - Starts: the release is on every instance.
  - Does: adds the copy function, the dual-write path, the heartbeat, and the tombstone write in the erasure delete's MySQL transaction. The tombstone write is always on, not behind a flag, so deletes before dual write are tracked too. Sets `users.dual_write=false`, `users.source=mysql`, `users.pg_read_percent=0`. Each instance exports `users_repo_build{version}`. The Postgres pool gets an acquire timeout of 250 ms or less and a statement timeout.
  - State: code, flags and heartbeat rows. No data moves.
  - If it fails: roll back the deploy. If the tombstone insert fails, that erasure attempt fails and the erasure job retries it.

### Phase 1: Dual write, sweeper, backfill, reads

- [ ] **4. Turn on dual write.**
  - Starts: step 3 is on every instance, so no older build runs. An operator sets `users.dual_write=true`.
  - Does: every write uses the dual-write path. The gate for step 6 is: every heartbeat shows `dual_write` on and the new build, held for 60 s. The backfill leader checks this gate.
  - State: the flag. Failed copies go into `migration_pending`.
  - If it fails: set `users.dual_write=false`. MySQL is unaffected. The sweeper scans by `updated_at`, not by flag, so writes made without dual write are still repaired.

- [ ] **5. Start the forward sweeper.**
  - Starts: when `users.dual_write` is on. The cursor starts at the time dual write was turned on, minus 10 minutes. The leader is the instance holding `pg_try_advisory_lock(<sweeper key>)` on a dedicated session.
  - Does: while `sot=mysql`, repeats these three parts:
    1. Read MySQL tombstones with `seq > tomb_seq` on the replica. For each, under the copy lock, delete the user from Postgres and insert the tombstone with `ON CONFLICT DO NOTHING`. Advance `tomb_seq` after each batch.
    2. Read `users WHERE updated_at >= cursor ORDER BY updated_at, id LIMIT 2000` on the replica. Copy each row with the copy function. Set the cursor to the largest `updated_at` seen, minus 60 s, only after the batch is applied or recorded as pending.
    3. Send rows that fail to copy to `migration_pending`. Retry them with backoff. Delete them on success.
    It stops when step 12 sets `sot=postgres`.
  - State: `migration_state` (`sweep_users_cursor`, `sweep_tomb_seq`), `migration_pending`, and the lock.
  - Metrics: repair lag (now minus cursor) and pending count. Alert when lag is above 5 min or a pending row is older than 15 min.
  - If it fails: the loop retries. If the leader dies, another instance takes over within seconds. The cursor never moves past unfinished work.

- [ ] **6. Backfill, then the full comparison.**
  - Starts: automatically, once the step 4 gate has held for 60 s. No operator action.
  - Does: the backfill leader holds `pg_try_advisory_lock(<backfill key>)`, a lock separate from the sweeper's, and loops:
    1. Read `backfill_cursor` (default 0) from `migration_state`.
    2. Read the replica lag. If it is above 5 s or missing, sleep 5 s and check again.
    3. Read `SELECT id, email, name, plan, version, updated_at FROM users WHERE id > :cursor ORDER BY id LIMIT 2000` on the replica.
    4. Check the lag again. If it is above 5 s, drop the batch and go back to 2.
    5. In one Postgres transaction, copy each row with the copy function and set `backfill_cursor` to the last id read. Commit.
    6. Sleep 200 ms between batches.
    When a read returns no rows past the cursor, set `backfill_done=true` and record the max id.
    The same leader then runs the comparison, which must end with zero mismatches:
    - Scan ids in ranges of 2,000. For each range, compare the counts and a hash of `(id, lower(rtrim(email)), rtrim(name), plan, version)` on the replica and on Postgres. For each range whose hash differs, compare the rows one by one.
    - Compare the two tombstone sets. Check that no Postgres row has a tombstoned id.
    - For a row that differs or changed in the last 60 s, reread both sides after a 30 s settle. A row missing in Postgres, or with a lower version there, is fixed with the copy function. A Postgres row with a higher version is never overwritten: it is reported and blocks the gate. A Postgres row with no MySQL row and no tombstone is reported and blocks the gate. Only tombstoned ids are deleted automatically.
    - The gate passes when one full pass ends with no unresolved mismatch. Record the run id and time in `migration_state`.
  - State: `migration_state` (`backfill_cursor`, `backfill_done`, the compare run). Each batch's cursor is committed in the same Postgres transaction as the batch.
  - If it fails: a crash resumes after the last committed cursor. A replayed batch is safe because of the version rule. Replica or Postgres errors back off and retry; users are not affected. If the gate turns red later, backfill need not stop, because the sweeper covers writes. An unexplained mismatch keeps the gate closed until someone investigates it.

- [ ] **7. Ramp reads to Postgres.**
  - Starts: the step 6 gate has passed.
  - Does: sets `users.pg_read_percent` to 1, then 10, 50, 100. Each step is held until every heartbeat shows it, and for at least 1 hour. Move on only when the error rate is flat and sampled reads (1% of Postgres reads, compared with the replica) show no unrepaired mismatch.
  - State: the flag.
  - If it fails: set the percentage to 0. Reads return to MySQL, and no data moves. A read may briefly see an old row whose Postgres copy failed; the sweeper limits that window to the repair lag.

- [ ] **8. Hold reads at 100% on Postgres for 3 days.**
  - Starts: every heartbeat shows 100.
  - Does: nothing new. The sweeper keeps running, and the step 6 comparison runs once a day. The clock is `reads_pg_100_since` in `migration_state`. It resets if the percentage drops below 100, or if a mismatch is not repaired within 1 hour.
  - State: the clock.
  - If it fails: follow step 7's rollback, then restart the clock when reads are back at 100%.

### Phase 2: Switch the source of truth to Postgres

- [ ] **9. Check the preconditions.**
  - Starts: an operator asks for the switch.
  - Does: checks that reads have been at 100% for at least 3 days; a comparison with zero mismatches in the last 24 h; `backfill_done=true`; sweeper lag under 60 s; no pending rows; every heartbeat on the new build.
  - State: nothing changes.
  - If it fails: do not switch. Fix the failing check first.

- [ ] **10. Fence writes (T0).**
  - Starts: the operator's switch command sets `users.source=fenced`.
  - Does: writes return 503 with `Retry-After`. Reads continue. Each instance refuses new writes, finishes its in-flight writes, and reports `fenced` with `in_flight` 0. The command waits until every heartbeat shows `fenced` and `in_flight` 0. Propagation takes up to 30 s.
  - State: the flag and the heartbeats.
  - If it fails: if any instance has not reported `fenced` within 35 s, run step 13.

- [ ] **11. Drain (20 s budget).**
  - Starts: step 10 is complete. The switch command runs this step.
  - Does: one forward sweep against the MySQL primary (not the replica) for rows with `updated_at >= cursor - 60 s` and for tombstones since `tomb_seq`. Then compare the hashes of that window on both sides. The drain is done when the sweep leaves no pending rows and the hashes match. Then read the next AUTO_INCREMENT value from MySQL `information_schema` on the primary, and set `users_id_seq` to that value or the current Postgres sequence value, whichever is larger, plus 1,000,000.
  - State: the cursors and the sequence.
  - If it fails: if the drain is not done within 20 s, or the hashes differ, run step 13.

- [ ] **12. Flip the source to Postgres (T1).**
  - Starts: every heartbeat shows `fenced` and step 11 is done. The switch command runs this step.
  - Does: sets `users.source=postgres`, `migration_state.sot=postgres`, and `sot_switched_at`. Writes now go to Postgres first, as described above. `users.mysql_shadow` is read only from here on: when on, each write is shadowed to MySQL. Reads go to Postgres.
  - Pause: fence 30 s + drain 20 s + flip 30 s = 80 s at worst, measured from the first 503 to the first successful write.
  - State: the flags, `sot`, and the sequence.
  - If it fails: the flag is global, so the realistic risk is an instance that has not refreshed. It stays `fenced`, which refuses writes safely. Investigate before continuing. For a problem found later, see step 15.

- [ ] **13. Abort (any time before step 12 completes).**
  - Starts: a timeout in step 10 or 11, or a failed check.
  - Does: sets `users.source=mysql`. No Postgres-source writes have happened, so no drain is needed.
  - Pause: at most 30 s of propagation. Worst case from step 11: 35 + 20 + 30 = 85 s.
  - State: the flag.
  - If it fails: retry. Writes stay refused until every heartbeat shows `mysql`.

- [ ] **14. Run the reverse sweeper (Postgres as source).**
  - Starts: step 12 sets `sot=postgres`.
  - Does: the same loop as step 5, in the other direction, with its own lock. It reads Postgres `users` by `updated_at` and `users_tombstones` by `seq`, and applies them to the MySQL primary:
    - Update by id where `version < incoming`. If no row changed, insert.
    - A tombstone deletes the MySQL row and inserts the MySQL tombstone.
    - Do not use `ON DUPLICATE KEY UPDATE`: it also fires on the email key and could update the wrong row. Email conflicts go to `migration_pending` with `direction='to_mysql'`.
    - It runs until step 17.
  - State: `rsweep_users_cursor` and `rsweep_tomb_seq` in Postgres `migration_state`, and the pending rows.
  - If it fails: as in step 5. Users do not see the lag, because MySQL is a shadow. Rollback (step 15) is blocked until reverse lag is under 60 s and pending is empty.

- [ ] **15. Roll back to MySQL (allowed until step 17).**
  - Starts: an operator decides to roll back. Precondition: reverse lag under 60 s and no pending rows.
  - Does, in order:
    1. Set `users.source=fenced`.
    2. Wait until every heartbeat shows `fenced` and `in_flight` 0. If not done within 35 s, set `users.source=postgres` to abort. That is a second pause, of up to 30 s.
    3. Run the reverse sweeper once against the Postgres primary for the window. Confirm no pending rows and matching hashes. Budget 20 s. If not, set `users.source=postgres` to abort.
    4. Set the MySQL AUTO_INCREMENT to the larger of its current value and Postgres's last sequence value, plus 1,000,000.
    5. Set `users.pg_read_percent=0`, so reads go back to MySQL.
    6. Set `users.source=mysql` and `sot=mysql`. Reset the forward sweeper cursor to the fence time minus 10 minutes.
  - Pause: 80 s at worst for a full rollback.
  - State: the flags, the MySQL AUTO_INCREMENT, and the cursors.
  - If it fails: use the abort path in step 2 or 3. Writes are never released until the drain has matched.

### Phase 3: Hold and monitor

- [ ] **16. Keep Postgres as source for 14 days.**
  - Starts: step 12.
  - Does: nothing new. Shadow writes to MySQL, the reverse sweeper, and a daily comparison keep running. The clock is `sot_switched_at`.
  - State: `sot_switched_at`.
  - If it fails: run step 15.

- [ ] **17. Switch to Postgres-only writes.**
  - Starts: 14 days after `sot_switched_at`, and reads at 100% on Postgres.
  - Does: takes a final snapshot of MySQL `users` and `user_tombstones` and checks that it restores. Then sets `users.mysql_shadow=false`. Writes go only to Postgres, and the reverse sweeper stops. This does not change the source of truth, so there is no fence and no pause. Instances on an older flag value for up to 30 s may still shadow to MySQL, which is harmless.
  - State: the flag and the snapshot.
  - If it fails: if the snapshot does not restore, do not set the flag. After this step, rollback in step 15 is no longer safe. If the flag is set back to true, MySQL is behind by the gap; run a full comparison in reverse before any further rollback.

- [ ] **18. Drop the MySQL tables.**
  - Starts: step 17 has been live for the retention period. The brief requires only that the drop comes after step 17. A 30-day retention is recommended; the owners decide.
  - Does: drops `users` and `user_tombstones` in MySQL. Removes the dual-write, sweeper, backfill and reverse-sweeper code, the flags, and the `no-raw-users-sql` exception. Updates `existing/users_table.md`.
  - State: the restored snapshot is the only way back.
  - If it fails: the drop cannot be undone. Do not run it until the snapshot restore check has passed.

## Open questions

- If a Postgres copy fails, the old row stays visible until repair, which can take up to the 5-minute lag alert. A user created while its copy failed is not found until repair. It is not known whether the brief accepts this for read-after-write.
- Whether `pg-core` has a read replica is not known from the existing files. The plan reads from the primary; its capacity for read load is unknown.
- The existing files do not say how a gate learns the full list of running instances. Steps 4, 10 and 12 depend on it.
- The plan reads replica lag from `mysql_replica_lag_seconds`. The existing files do not say whether the app can read that metric.
- The plan assumes a user enabled at 1% stays enabled at 10%. The flags file says a key gets the same answer each time, not that the buckets nest. This is not verified.
- The retention period for the MySQL snapshot in step 18 is the owners' decision.