# Plan: move `users` from MySQL 8 to Postgres 16 without downtime

## Summary

Today every read and write of `users` goes through `UserRepository`. A lint rule (`no-raw-users-sql`) rejects SQL on `users` anywhere else, so all migration logic goes in that class. Reads use the MySQL read replica, whose lag is normally under 1 s. Writes use the MySQL primary. The `version` column is an INT that starts at 1 and goes up by 1 on every update. An update whose expected version no longer matches raises `StaleWrite`.

The table holds about 38 million rows, with gaps in the ids. Peak load is about 3,000 reads/s and 400 writes/s. The GDPR erasure job hard-deletes about 2,000 rows a day. There is no soft-delete column. The Postgres 16 cluster `pg-core` exists and is empty. The app already holds a connection pool to it, which nothing uses yet.

The move has four stages. MySQL stays the source of truth (SoT) until the copy is proven, so a Postgres failure never fails a request.

1. Every write commits to MySQL and is then copied to Postgres. Repair fixes anything Postgres missed.
2. Reads move to Postgres only after a full comparison finds zero mismatches, and only after reads have been 100% on Postgres for at least 3 days.
3. The SoT moves to Postgres. Writes pause for at most 90 s during the switch.
4. For at least 14 days after that, writes can go back to MySQL. Only after that window are MySQL writes stopped and the MySQL table dropped.

Every copy follows one version rule. An erased user gets a tombstone in Postgres, so the user cannot come back. Each database holds a control row that refuses app writes once that database is no longer the SoT. Until step 13, a rollback to MySQL loses no write.

## Terms

- **Source of truth (SoT)**: the database whose rows win. Writes commit there first. It is MySQL until step 10, then Postgres.
- **Dual write**: a write commits to MySQL, then is copied to Postgres.
- **Outbox**: the MySQL table `users_sync_outbox`. Each `users` write adds one row that holds the user's row as it is after the write. A row stays until Postgres has it.
- **Relay**: the single worker that copies outbox rows to Postgres.
- **Inline apply**: the request's own copy to Postgres, made right after the MySQL commit, with a 200 ms timeout (chosen value).
- **Version rule**: a copy inserts a row if it is missing. It replaces the Postgres row only when that row's `version` is lower. It never replaces a row with an equal or higher version. In SQL: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
- **Tombstone**: a row `(id, erased_at)` in `users_tombstones` for an erased user. No copy writes an id that has a tombstone. Postgres has tombstones from step 1. MySQL gets them for the reverse direction, in step 2.
- **Advisory lock**: a named lock held by one database session. It is released if that session dies. Copies into Postgres take one per id. The MySQL relay lock uses `GET_LOCK`.
- **Shared and exclusive lock on `users_migration`**: many writers can hold this lock in shared mode at once. The commit point takes it exclusively, so it waits for writers already in flight.
- **Control row**: the `users_migration` row in each database, with `sot` (`mysql` or `pg`) and `epoch` (a counter that rises at each SoT change).
- **Fence**: an app write checks, in its own transaction and under the shared lock, that its database is still the SoT. If it is not, the write gets a retryable 503.
- **StaleWrite**: raised when an update matches no row with the expected version. The caller's copy was out of date.
- **Flags**: `flags.get` returns a boolean, a string or a percentage (0 to 100). `flags.enabled_for(name, key)` buckets by key, so one key always gets the same answer. Each instance caches all flags and reloads them every 30 s, so instances can disagree for up to 30 s. Each instance exports the value it uses as `app_flag_value{flag=...}`.
- **Write mode** (`users_write_mode`, a string): where app writes go. `mysql` means MySQL first. `paused` means every write gets a 503. `pg` means Postgres first.
- **Dual-write flag** (`users_dual_write`): in mode `mysql`, on means each write also runs the inline apply, and the relay drains the outbox to Postgres. Off means nothing is copied and the outbox grows. The flag is not used in mode `pg`. It stays on through the switch, so it is ready if the system rolls back.
- **Reverse sync flag** (`users_reverse_sync`): off until step 10d. When on, in mode `pg`, each Postgres write also inserts a reverse outbox row, copies the row to MySQL inline, and lets the reverse relay run. Step 13 turns it off.
- **Read source flag** (`users_read_source`, a percentage): the share of users who read from Postgres. Default `mysql`.
- **Reverse outbox**: the Postgres table `users_sync_outbox`. It is used only after the switch, to copy writes back to MySQL.
- **Reverse copy**: a copy of a Postgres write into MySQL, made inline or by the reverse relay.
- **Reverse relay**: the single worker that copies reverse outbox rows to MySQL. It holds the Postgres advisory lock `users_reverse_relay` (name chosen).
- **Backfill**: the one-time copy of existing rows into Postgres (step 5).
- **Sweep**: the repair job that compares the two tables and fixes differences (step 6).

## How the system runs

### Writes before the switch (mode `mysql`)

Starts: a request calls `UserRepository` to create, update or delete a user.

1. The repository takes the shared lock on `users_migration` in its own MySQL transaction, and reads the control row under it. If the row says `pg`, the write gets a 503. This is the fence.
2. In the same transaction, it writes `users` and inserts the outbox row. The outbox row holds the row's new contents, read in that transaction.
3. After the commit, if `users_dual_write` is on and the mode is `mysql`, the inline apply copies the row to Postgres, with a 200 ms timeout. It takes the same advisory lock and tombstone check as every other copy.
4. On success, the inline apply deletes its own outbox row, by `seq`. Deleting a row that is already gone does nothing.
5. On failure or timeout, the request still succeeds, and the row stays for the relay.

A late inline commit (one that finishes after its timeout) carries the same or an older version. The version rule stops it from overwriting newer data. If the user was erased in the meantime, the tombstone check stops it. If the relay later picks up a row that the inline apply already applied, the copy is skipped as an equal version, so the row is never applied with a different result.

### Relay before the switch

- One leader at a time. The leader holds the MySQL lock `users_relay` (`GET_LOCK`) on a dedicated connection to the primary. Other instances retry every 5 s (chosen value).
- The leader reads outbox rows in batches of 500, in `seq` order. It applies the copy rules to each row, then deletes the rows it applied, by `seq`.
- If the leader dies, its connection closes, and MySQL releases the lock. A slow leader keeps the lock, and the outbox-age alert shows it. No takeover rule is added.
- Copies are safe to repeat, and two leaders overlapping is harmless, because of the version rule.
- The relay runs while the dual-write flag is on. When the outbox is empty, it does nothing.

### Why not `app.jobs`

Jobs are delivered at least once. A job is retried up to 5 times with exponential backoff (about 15 minutes in total). Then it moves to `jobs:dead`, which nothing processes. Enqueue raises after a 1 s timeout if Redis is unreachable. So backfill, the relay and the sweep run as leased workers that hold a lock.

### Copies into Postgres

Backfill, relay, inline apply and sweep copy rows the same way. Each takes the Postgres advisory lock for the id, skips tombstoned ids, and applies the version rule. Copies and erasure take turns on each id, because they share that lock.

### Erasure before the switch

The GDPR erasure job calls `UserRepository.delete`, which is the only caller. In one MySQL transaction it:

- deletes the user,
- deletes that user's pending `upsert` outbox rows, because they hold personal data,
- inserts a `delete` outbox row.

The relay then writes the tombstone and deletes the Postgres row, in one Postgres transaction. This works even if the user was never backfilled. A copy that commits first is removed by the delete. A copy that starts later sees the tombstone and is skipped. Either way the user does not come back.

### Writes after the switch (mode `pg`, reverse sync on)

1. The write runs in one Postgres transaction. It checks that the Postgres control row says `pg` (the fence), updates `users`, and inserts a reverse outbox row.
2. After the commit, the row is copied to MySQL inline, with a 200 ms timeout.
3. If the MySQL copy fails or times out, the request still succeeds, and the reverse outbox row stays.
4. The reverse relay copies the remaining rows to MySQL, and deletes the rows it applied.

A reverse copy goes straight to MySQL. It does not use the MySQL outbox. It takes the shared lock on MySQL's `users_migration` in its own transaction, as an app write does, but with the opposite check. An app write refuses when MySQL says `pg`. A reverse copy runs only when MySQL says `pg`, and it never returns a 503. So app writes to MySQL run only while `sot='mysql'`, and reverse copies run only while `sot='pg'`. The reverse copy applies the version rule and checks the MySQL tombstones in the same transaction. It writes no outbox row. If it finds `sot='mysql'`, it stops and leaves its row in the reverse outbox.

### Erasure after the switch

The erasure job still calls `UserRepository.delete`. In one Postgres transaction it:

- deletes the user,
- deletes that user's pending reverse `upsert` rows,
- writes a tombstone to Postgres `users_tombstones`,
- inserts a reverse `delete` row.

Then the reverse copy deletes the MySQL row and writes the MySQL tombstone, in one MySQL transaction. A copy therefore sees either the row or the tombstone. If that copy fails, the reverse relay does it.

### Email conflicts

An email is unique in each database. Two cases can clash.

- **Before the switch.** A new user takes an email still held by an erased user, and that erasure has not reached Postgres. The copy fails on the unique index. The relay then applies that erased user's pending delete and retries. If the holder still exists in MySQL, the relay records a conflict and alerts. The sweep handles the same case in step 6.
- **After the switch.** The same race in the other direction. A reverse copy fails on the unique index in MySQL. The reverse relay finds the user who holds that email in MySQL, applies that user's pending reverse delete, and retries. If that user still exists in MySQL, the relay records a conflict and alerts.

### Ids

- Before the switch, MySQL `AUTO_INCREMENT` assigns every id. Postgres gets ids only through copies, which carry the MySQL id.
- Step 1 creates `users_id_seq`, but nothing draws from it before the switch.
- At the switch, in step 10d, while writes are paused: `setval(users_id_seq, GREATEST(max id on Postgres, max id on MySQL) + 1000000)`. The 1,000,000 headroom is a chosen value. Then the default of `users.id` becomes the sequence, so Postgres assigns ids.
- After the switch, a reverse copy carries the Postgres id to MySQL as given. MySQL assigns no ids in mode `pg`, so the copied ids cannot collide with new MySQL ids. Postgres-assigned ids start at least 1,000,000 above the old maximum.
- MySQL's `AUTO_INCREMENT` is set past both maxima only on rollback, in step 11d.

### What happens when things fail

| Failure | What happens | Who or what fixes it |
|---|---|---|
| Postgres write or inline copy fails or times out | The request succeeds. The row stays in the outbox. | The relay, once Postgres is back. |
| The relay leader dies | MySQL releases its lock. Another instance takes it within 5 s. | Automatic. |
| The relay is slow | The lock stays with it. The outbox-age alert fires at 5 minutes. | Operator. |
| Backfill crashes | It resumes after the last committed cursor. | Automatic, on restart. |
| Backfill hits a Postgres error | It retries with backoff. The cursor does not move. | Automatic. |
| Sweep finds a Postgres row with a higher version | It never overwrites. It alerts. | Operator. |
| Email conflict | The relay applies the holder's pending delete and retries. If the holder still exists, it alerts. | Automatic, then operator. |
| Drain takes longer than 20 s at the switch or rollback | The mode goes back, and nothing has changed. | Operator, per runbook. |
| Crash after commit point (c) in step 10 or 11 | Writes stay paused until roll-forward. | Operator. Open question. |
| Reverse copy fails | The row stays in the reverse outbox. | The reverse relay. |
| Stale Postgres read | A write may fail with `StaleWrite`, and the user retries. | The caller's retry handling. |

## Rollout checklist

- [ ] **1. Create the Postgres schema in `pg-core`.**
  - Starts: a change ticket approved by the owner.
  - Changes: table `users` with the same columns as MySQL. These are `id BIGINT PRIMARY KEY` (no default yet), `email` (up to 320 characters, unique on `lower(email)` to match MySQL's case-insensitive unique email), `name` (up to 200 characters), `plan` (up to 20 characters), `version INT`, and `updated_at timestamp(3)` in UTC. Also create `users_id_seq` (a sequence, unused until the switch), `users_tombstones (id PRIMARY KEY, erased_at)`, `users_backfill_state`, `users_compare_runs`, `users_sync_outbox` (used later, in reverse), and `users_migration (id=1, sot='mysql', epoch=1)`.
  - State: `pg-core`.
  - If it fails: drop and recreate the empty schema. Nothing reads it yet.

- [ ] **2. Create the MySQL outbox and control tables in `core`.**
  - Starts: step 1 is done.
  - Changes: `users_sync_outbox (seq AUTO_INCREMENT, user_id, op 'upsert' or 'delete', version, row_json, created_at)`, `users_migration (id=1, sot='mysql', epoch=1)`, and `users_tombstones` (used later, in reverse).
  - State: `mysql-core-primary`.
  - If it fails: these tables are additive. Drop them and retry.

- [ ] **3. Deploy the code with every migration flag off.**
  - Starts: a normal deploy. `users_dual_write` and `users_reverse_sync` stay off.
  - Changes: `UserRepository` writes an outbox row in every write transaction, from now on, so no write is missed once dual writes start. Rows wait in the outbox until step 4 starts the relay. Reads follow `users_read_source` (default `mysql`). Writes follow `users_write_mode` (default `mysql`). Each instance exports `app_build_info{version}`.
  - Check: outbox insert latency at about 400 writes/s, measured in staging.
  - State: the outbox in MySQL.
  - If it fails: roll back the deploy. The old path is unchanged apart from the extra insert.

- [ ] **4. Turn on dual writes (flag `users_dual_write`).**
  - Starts: step 3 is live on every instance, and the flag is switched on.
  - Changes: in mode `mysql`, each write commits to MySQL with its outbox row, then runs the inline apply to Postgres. The relay starts and drains the outbox to Postgres, in batches of 500, in `seq` order. Erasure is covered in its own section above.
  - Gate for step 5: `app_flag_value{flag="users_dual_write"}` is 1 on every instance, and `app_build_info` shows the release version on every instance. The flag alone is not enough.
  - State: the outbox in MySQL.
  - If it fails: set the flag off. Outbox rows keep accumulating, and they drain once it is back on. Alert when the oldest outbox row is older than 5 minutes.

- [ ] **5. Backfill, resumable.**
  - Starts: the step 4 gate has passed. One leader takes the Postgres advisory lock `users_backfill`.
  - Each batch:
    1. Read replica lag from `mysql_replica_lag_seconds`. If it is unknown or above 5 s, wait 5 s and check again. Reporting jobs share this replica.
    2. Read at most 2,000 rows from the replica, in primary-key order: `WHERE id > :cursor ORDER BY id LIMIT 2000`.
    3. In one Postgres transaction, for each id, take the advisory lock, skip tombstoned ids, and apply the version rule. In the same transaction, set `users_backfill_state.cursor_id`.
    4. Commit, then wait 100 ms (chosen value) so reporting can use the replica.
  - State: `users_backfill_state` in `pg-core`. The cursor moves in the same transaction as the data, so it is never ahead of the data.
  - If it fails: after a crash, restart the worker. It resumes after the last committed cursor. The batch in flight is redone safely, because copies are idempotent. A Postgres error is retried with backoff, and the cursor does not move.

- [ ] **6. Continuous repair sweep.**
  - Starts: step 4 is on. The sweep runs alongside step 5 and keeps running.
  - Each run:
    - Compares chunks of 2,000 ids by a fingerprint, which is a hash of the row contents. Both sides hash UTC timestamps.
    - For each mismatching chunk, re-reads the row on the MySQL primary, and checks the outbox first.
    - If MySQL has a newer or missing row, copies it with the version rule.
    - If Postgres has a row that MySQL lacks, and no outbox row is pending for it, deletes it and writes a tombstone.
    - If Postgres has a higher version than MySQL, never overwrites. Alerts.
  - Email conflicts are handled as described above.
  - State: `users_compare_runs` and the sweep cursor in `pg-core`.
  - If it fails: the sweep is idempotent. Investigate the alerts and rerun.

- [ ] **7. Full comparison gate.**
  - Starts: `users_backfill_state` is `done`, the outbox is empty, and one full sweep has passed.
  - Pass rule: a run over all ids in both tables finds zero mismatches after the primary re-check. A mismatch counts only if it persists on the primary and no outbox row exists for that id.
  - State: `users_compare_runs`.
  - If it fails: repair, then rerun the full comparison from the first id. A partial rerun does not pass.

- [ ] **8. Move reads to Postgres: 1%, 10%, 50%, 100%.**
  - Starts: step 7 has passed. Each ramp step is a change to `users_read_source`.
  - Changes: `flags.enabled_for` buckets by user id, so each user always gets the same source. Each Postgres read has a short timeout. Any error or timeout falls back to the MySQL replica in the same request, so reads never fail.
  - Known risk: a Postgres read can be behind MySQL by the outbox backlog, and the read cannot tell. A stale read can only make a write fail with `StaleWrite`, because the write checks the version in MySQL. The user then gets the caller's `StaleWrite` handling and must retry the action. The retry reads again. Hold each ramp step until outbox lag is under 1 s at p99 (the 99th percentile). Outbox lag is the age of the oldest pending outbox row.
  - State: the flag only.
  - If it fails: set the flag back to `mysql`. No data changes.

- [ ] **9. Soak: reads 100% on Postgres for at least 3 days.**
  - Starts: every instance reports `users_read_source` at 100% (`app_flag_value`), and the 100% step is in place.
  - The clock starts then. Any fallback to MySQL, or any flag change, resets it.
  - State: the flag. Where the clock is recorded is an open question.
  - If it fails: move reads back to `mysql`. No write pause is needed, because reads do not change data. The clock restarts on the next attempt.

- [ ] **10. Planned switch: Postgres becomes the SoT (writes paused at most 90 s).**
  - Starts: step 9 has passed, and all of these hold:
    - the outbox is empty;
    - replica lag is normal;
    - a full comparison finished within the last 24 hours with zero mismatches (chosen value).
  - Runbook. During the pause, every write through `UserRepository`, including erasure, gets a 503 with `Retry-After`, and the client retries.
    - **(a)** Set `users_write_mode=paused`. Wait until every instance reports `paused`, about 30 s. An instance reports `paused` only after its in-flight writes finish.
    - **(b)** Drain. Wait until the MySQL outbox is empty. The relay keeps running. If 20 s pass without that, set `users_write_mode=mysql` and stop. Nothing has changed yet.
    - **(c)** Commit point, in MySQL, in one transaction: lock `users_migration` exclusively, check that the outbox is still empty, set `sot='pg'`, and set `epoch` + 1. If the outbox is not empty, roll back and go to (b). Every app write to MySQL holds the shared lock. So a write from an instance that has not seen the pause either commits before (c), which makes (c) retry, or sees `sot='pg'` and gets a 503. No MySQL ids are assigned after (c).
    - **(d)** In Postgres: run `setval(users_id_seq, GREATEST(max id on Postgres, max id on MySQL) + 1000000)`. Set the default of `users.id` to `users_id_seq`. Set Postgres `users_migration` to `sot='pg'` and copy the MySQL `epoch`. Do not increment it. Then start reverse sync: set `users_reverse_sync` on, and start the reverse relay, which takes `users_reverse_relay`. No Postgres write reaches the database in this window, because the mode is still `paused`.
    - **(e)** Set `users_write_mode=pg`. Wait until every instance reports `pg`, about 30 s. Writes now go to Postgres first, then to MySQL.
  - Pause budget: about 30 s for (a), up to 20 s for (b), about 30 s for (e), and a few seconds for (c) and (d). Alert at 75 s. Hard limit 90 s. A 60 s drain limit would allow a worst case near 120 s, so the drain limit is 20 s.
  - State: the control rows in each database, and the flag.
  - If it fails: before (c), set the mode back to `mysql`. The source does not change. After (c), roll forward by rerunning (d) and (e). Do not roll back, because the MySQL control row already fences app writes to MySQL. Until (d) finishes, the Postgres control row still says `mysql`, so Postgres refuses writes. Detect this state when MySQL's `epoch` is ahead of Postgres's, or when MySQL says `pg` while Postgres says `mysql`. The rerun is safe, because no Postgres ids are assigned before (e), so the sequence value comes out the same.

- [ ] **11. Reverse sync and rollback path (for 14 days after step 10e).**
  - Starts: step 10d turns on reverse sync. This phase runs from step 10e, when writes go to Postgres first. It also covers erasure after the switch.
  - A rollback starts when someone decides to go back during this window. It is the step 10 runbook with the roles swapped:
    1. Set `users_read_source` to `mysql`. Reads now come from the MySQL replica, which can lag until the drain ends. A stale read is handled as in step 8.
    2. **(a)** Set `users_write_mode=paused`. Wait until every instance reports `paused`, about 30 s.
    3. **(b)** Drain. Wait until the reverse outbox in Postgres is empty. The reverse relay keeps running. If 20 s pass without that, set `users_write_mode=pg` and stop. Nothing has changed yet.
    4. **(c)** Commit point, in Postgres, in one transaction: lock `users_migration` exclusively, check that the reverse outbox is still empty, set `sot='mysql'`, and set `epoch` + 1. If the outbox is not empty, roll back and go to (b). After (c), no Postgres writes can happen, because writes are paused, so nothing is left to copy.
    5. **(d)** In MySQL: set `AUTO_INCREMENT` past both maxima (the largest id on each side). Set MySQL `users_migration` to `sot='mysql'` and copy the Postgres `epoch`. Do not increment it. Then set `users_reverse_sync` off and stop the reverse relay, which releases `users_reverse_relay`.
    6. **(e)** Check that `users_dual_write` is on (it stayed on through the switch). Set `users_write_mode=mysql` and wait until every instance reports `mysql`. MySQL is the SoT again. The MySQL outbox and relay run, and inline copies to Postgres resume.
  - Pause budget: at most 90 s, as in step 10.
  - State: the reverse outbox in Postgres, and the control rows.
  - If it fails: before (c), set the mode back to `pg`. The source does not change. After (c), roll forward by rerunning (d) and (e). Detect this state when Postgres's `epoch` is ahead of MySQL's, or when Postgres says `mysql` while MySQL says `pg`.

- [ ] **12. Hold for at least 14 days after step 10e.**
  - Starts: step 10e.
  - This is the rollback window. The clock restarts after any rollback and after any re-promotion.

- [ ] **13. Switch to Postgres-only writes.**
  - Starts: at least 14 days after step 10e, the reverse outbox is empty, and a full comparison in the reverse direction shows zero mismatches. The reverse comparison is step 7 with the roles swapped.
  - Changes: set `users_reverse_sync` off on every instance. Then revoke INSERT, UPDATE and DELETE on `core.users` from the app role. This does not change the SoT, so no pause is needed. It is irreversible in practice.
  - State: the flag and the database grants.
  - If it fails: turn the flag back on and re-grant the privileges, while MySQL is still in place.

- [ ] **14. Drop the MySQL `users` table.**
  - Starts: at least 7 days after step 13 (chosen value). Take a final backup first.
  - Changes: drop `users`, `users_sync_outbox` and `users_tombstones` in MySQL.
  - State: MySQL, and the backup.
  - If it fails: restore from the backup.

## Open questions

- **Tombstone retention:** a tombstone keeps only an id and a time. Legal must confirm this is acceptable under the erasure policy, and whether backups need the same treatment.
- **Chosen values:** 200 ms inline timeout, 100 ms batch pause, 5 s relay retry, 20 s drain limit, 75 s alert, 1,000,000 id headroom, 24-hour comparison freshness, 7 days before the drop. The owner must confirm them.
- **Flag refresh:** the pause budget assumes the 30 s flag refresh. If that interval changes, recheck the 90 s budget.
- **Crash during a switch:** if a crash happens after commit point (c) in step 10 or step 11, writes stay paused until someone runs the roll-forward. That can exceed 90 s. No automatic roll-forward exists yet.
- **Relay capacity:** a single relay must keep up with about 400 writes/s. Measure this in staging before step 4.
- **Outbox-lag metric:** the files do not define a metric for outbox lag. Add one before step 8.
- **StaleWrite display:** the files do not say how callers show `StaleWrite` to users.
- **Fallback reads after the switch:** the MySQL replica is fed only by reverse copies and normal replication, so a fallback read can be behind by the reverse outbox lag. The files give no bound and no freshness check. The same applies during a rollback drain.
- **Sweep after the switch:** step 6 is defined for the period before the switch. Its direction and behavior after step 10 are not defined.
- **Clock records:** where the soak clock (step 9), the 14-day window (step 12) and the 7-day wait (step 14) are recorded is not defined.
- **Erasure job owner:** the files do not name the team that runs the GDPR erasure job.