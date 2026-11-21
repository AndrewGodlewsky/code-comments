# Move `users` from MySQL 8 to Postgres 16

The `users` table moves from MySQL 8 (database `core`) to the Postgres 16 cluster `pg-core`. The service stays up throughout. Every read and write of `users` already goes through `UserRepository`, so the migration code goes there too.

The plan has three phases:

1. **Mirror.** MySQL stays the source of truth. Every write is also copied to Postgres. Anything a copy misses is repaired automatically.
2. **Switch.** Postgres becomes the source of truth, but MySQL is kept up to date as a mirror so we can roll back.
3. **Finish.** Once the rollback window closes, MySQL stops receiving writes and the old table is dropped.

## Terms

- **Source of truth (source):** the database that accepts writes and holds the authoritative data. It starts as MySQL and later becomes Postgres.
- **Mirror:** the other database. It is kept up to date by copying writes into it.
- **Replica:** a read-only copy of the MySQL primary. It normally lags the primary by under 1 s. Reporting jobs also read it.
- **Version:** an integer on each row. It starts at 1 and goes up by 1 on every update. The copy with the higher version is the newer one.
- **Guarded copy:** the one operation that writes a user row into a store. Every path that writes a row into a store uses it: dual writes, repair, backfill, verifier fixes and mirroring. It is defined under Design decisions.
- **Outbox:** a table of user ids that still need to be copied to the other store. A write adds its outbox row in the same transaction as the write. The row is deleted once the copy succeeds.
- **Repairer:** a background worker that works through the outbox and copies each id whose immediate copy did not succeed.
- **Verifier:** a background worker that compares the two tables and queues mismatches for repair.
- **Tombstone:** a permanent record that a user id was erased. It holds only the id.
- **Control row:** one row per store, in that store's `users_control` table. It records which store is the source, whether writes are paused, the epoch and the switch step.
- **Epoch:** a counter that goes up by 1 each time the source changes.
- **Lease:** a lock stored as a row, with an expiry time. Only the holder may do the work. If the holder stops renewing the lease, another worker may take over.
- **Idempotent:** safe to run more than once. Running the same copy twice gives the same result as running it once.
- **Procedure S:** the six-step switch used for every change of source. It is defined below.

Feature flags (`app.flags`) are cached on each instance and refresh every 30 s, so instances can disagree for up to 30 s. Flags are good for turning features on gradually. Pauses and switches use control rows instead, because a flag change can take up to 30 s to reach every instance.

## Design decisions

- **The outbox lives in the source database.** Each write inserts one outbox row in the same MySQL transaction as the write. The row holds only the user id. We did not use `app.jobs` for two reasons. Enqueueing can raise an error when Redis is down, so it cannot sit on the request path. And a job that keeps failing ends up in `jobs:dead`, which nothing reads, so repair would not happen automatically.

- **One guarded copy for every write into a store.** Each guarded copy does these steps in order:
  1. Lock the id.
  2. If a tombstone exists for the id, skip the copy.
  3. If the row is missing, insert it.
  4. Otherwise, replace the row only if its stored `version` is lower than the incoming one. If the stored version is equal or higher, leave the row alone.

  In Postgres, step 1 is `pg_advisory_xact_lock(id)` and steps 3 and 4 are `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
  In MySQL, step 1 is a locking read on the tombstone key, and steps 3 and 4 are `INSERT ... ON DUPLICATE KEY UPDATE col = IF(version < VALUES(version), VALUES(col), col)` for each column.

  **Erase** (the guarded delete) takes the same lock, then writes the tombstone and deletes the row in one transaction. Tombstones are kept forever.

- **Repair copies the current state of a row, not the events.** The repairer reads the row from the source primary after the outbox row has committed, then copies that row. The copy is therefore at least as new as the write that queued it, so events never have to be applied in order. Ids are never reused. So if a source row is missing, the user was erased, and the repairer erases the id in the other store.

- **Control state is one row per store.** Each store's control row holds `source`, `epoch`, `write_paused`, `switch_step` and `mirror`. Every write reads its own store's control row inside its own transaction. It takes a shared lock and holds it until the commit. Shared locks let many writes read the row at the same time. A pause needs the exclusive lock, so it waits for in-flight writes to finish. Pauses use this row rather than a flag. If a pause, a switch and an unpause were made with flags, they could together take up to 90 s with no margin.

- **Ids.** Postgres uses `GENERATED BY DEFAULT AS IDENTITY`, which accepts explicit ids, so mirrored rows keep their original ids. Each time the source changes, the new source's id sequence is set above the largest id seen in either store, plus 1,000,000.

- **Timestamps.** `NOW(3)` follows the MySQL session time zone. Before backfill, check that the MySQL server time zone is UTC. Postgres stores `updated_at` as `timestamp(3)` in UTC, and the verifier compares it.

## Switch procedure S

Every change of source uses these six steps. The **old source** is the store that is the source now. The **new source** is the store that takes over. The checklist refers to this as "procedure S".

1. **Pause.** On the old source, set `write_paused = 1` in its control row. This update needs the exclusive lock, so it waits for writes that already passed the check to commit. After the update commits, record `max_outbox_id`, the largest id in the old source's outbox. From now on, new writes get `503` with `Retry-After`.
2. **Drain.** Wait until the old source's outbox has no row with an id at or below `max_outbox_id`. The repairer copies those ids to the other store. Limit: 45 s.
3. **Prepare the new source.** Set its identity sequence (or check its AUTO_INCREMENT) above the largest id in either store, plus 1,000,000. Make sure its control row exists with `write_paused = 1`.
4. **Commit point.** In the new source's control row, set `source = new`, `epoch = epoch + 1` and `switch_step = 4`. It stays paused.
5. **Fence the old source.** In the old source's control row, set `source = new` and `epoch = epoch + 1`. Any write that reaches the old source now is refused with 503.
6. **Unpause.** In the new source's control row, set `write_paused = 0`.

Each step also writes `switch_step` to the control row, so a crash can resume at the next step.

- **Before step 4 commits:** abort by setting the old source's `write_paused = 0`. No data has moved and the source has not changed.
- **After step 4:** the procedure always rolls forward. It never rolls back.

**Write check.** A write is refused with 503 unless its own store's control row says all of the following: `source` is this store, `write_paused = 0`, and `epoch` equals the epoch the instance has cached. Each instance refreshes its cached control value every 1 s. The epoch check stops an instance that missed an earlier switch from writing. Step 5 makes the old source's control row name the new source, so a stale instance can find the current source from either store.

**Pause budget.** The pause runs from step 1 to step 6. It is made of the drain (at most 45 s), a few commits (about 1 s each) and one cache refresh (about 1 s). That is about 50 s at most, inside the 90 s limit.

## Checklist

Steps run in this order. Each one says what starts it, what it changes, where its state lives and what happens if it fails.

- [ ] **0. Create the schemas, control rows and monitoring**
  - **Starts when:** the migration owner starts it. `pg-core` is already provisioned.
  - **Does:**
    - In `pg-core`, create `users` (`id BIGINT` identity primary key, `email VARCHAR(320)` unique, `name`, `plan`, `version INT`, `updated_at timestamp(3)`), `users_tombstones`, `users_outbox` and `users_control`.
    - In the MySQL primary, add new tables only. Do not alter `users`. Create `users_outbox` (`id` AUTO_INCREMENT, `user_id`, `enqueued_at`, `claimed_until`, `attempts`, `next_attempt_at`, `last_error`, with indexes on `user_id` and `next_attempt_at`), `users_tombstones`, `users_control`, `users_migration_state` (`backfill_last_id`, `backfill_status`, `lease_owner`, `lease_until`, `read_100_since`, `last_clean_pass_at`, `source_changed_at`) and `users_verify_mismatch` (`user_id`, `found_at`).
    - Insert the control row in both stores: `source = mysql`, `epoch = 1`, `write_paused = 0`, `switch_step = 0`, `mirror = on`.
    - The lint rule `no-raw-users-sql` rejects SQL on `users` anywhere outside `UserRepository`. The repairer, backfill and verifier must read `users` directly. Exempt them by file name, not by pattern, and keep them in review as part of the `users` boundary.
    - Set up monitoring for: the outbox row count and oldest `enqueued_at` in each store; the Postgres write error rate; verifier mismatches; the backfill `last_id` and its age; replica lag; and `app_flag_value` for each flag. Set the thresholds used by the gates in steps 8 and 10 here.
  - **State:** the new tables in both databases.
  - **If it fails:** nothing user-facing changes. Creation is idempotent, so rerun it.

- [ ] **1. Deploy the migration build with dual writes off**
  - **Starts when:** a normal deploy, with the flag `users_dual_write` off.
  - **Does:** the write path checks the control row. The outbox insert and the Postgres copy run only when the flag is on. The repairer runs on every instance (or on one instance holding a lease) and does nothing while the outbox is empty. Reads still use the MySQL replica.
  - **State:** the MySQL control row (source = MySQL) and the outbox.
  - **If it fails:** roll back the deploy. The new tables and control row do no harm.

- [ ] **2. Turn on dual writes**
  - **Starts when:** the operator sets `users_dual_write` to 100% after step 1 is live on every instance.
  - **Does:** each write runs these steps:
    1. In one MySQL transaction: check the control row (shared lock), apply the write, read the row back, insert the outbox row, and commit.
    2. After the commit, run the guarded copy to Postgres with a 500 ms timeout, using the row that was read back. On success, delete this write's outbox row.
    3. Return the response.
  - Any Postgres error is caught, logged and counted. The request still succeeds, and the repairer handles what is left.
  - Erasure uses the same path. The delete writes the tombstone and an outbox row in MySQL, and the guarded delete runs after the commit. The erasure job must treat 503 as retryable.
  - **State:** the MySQL outbox. The Postgres copy is idempotent, so running it again is harmless.
  - **If it fails:** if Postgres is down, the outbox grows and requests still succeed. Alert on outbox age. Once backfill (step 4) has started, keep the flag on. A write made with the flag off reaches neither Postgres nor the outbox, so the verifier would find it only on a later full pass.

- [ ] **3. Gate: every instance is dual-writing**
  - **Starts when:** every deployed instance reports `app_flag_value{flag="users_dual_write"} = on`, and the number of reporting instances equals the number deployed. Old builds that do not export the metric count as not ready. Then wait a further 60 s, which is longer than any write transaction plus the 5 s replica-lag bound.
  - **State:** none. This is a check only.
  - **If it fails:** keep waiting. Redeploy any stuck instance first.

- [ ] **4. Backfill from the replica**
  - **Starts when:** step 3 passes and the operator sets `users_backfill_enabled`. Backfill runs in a dedicated worker, not in a web instance and not as a jobs-queue job. Only one worker is active at a time. It holds a lease in `users_migration_state` (60 s, renewed after each batch).
  - **Does:** for each batch, the worker:
    1. Stops if it has lost the lease.
    2. Reads `mysql_replica_lag_seconds`. If the lag is above 5 s, it sleeps 1 s and checks again, without reading any rows.
    3. Reads `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` from the replica.
    4. If the batch is empty, marks the backfill complete.
    5. In one Postgres transaction, runs the guarded copy for each row in ascending id order.
    6. Sets `backfill_last_id` in the MySQL primary to the largest id in the batch.
  - **State:** `backfill_last_id` and the lease, both in the MySQL primary.
  - **If it fails:** a crash between steps 5 and 6 re-reads and re-copies the batch. That is safe because the copy is idempotent. Replica lag above 5 s pauses the worker. Postgres errors retry with backoff and lose no progress. Alert if `last_id` has not moved for 10 minutes. Erased ids are blocked by tombstones.

- [ ] **5. Verify until a pass is clean**
  - **Starts when:** step 4 completes. The verifier then runs continuously.
  - **Does:** it walks both tables in primary-key order with a merge join, reading the MySQL side from the replica. It compares `id`, `email`, `name`, `plan`, `version` and `updated_at`. It also finds Postgres rows that have no MySQL row. Each mismatched id is rechecked after its outbox rows are gone, comparing the MySQL primary with Postgres. If the ids still differ, the verifier inserts an outbox row, and the repairer fixes it with no manual step. A tombstoned id found in Postgres is removed.
  - **Clean pass:** a full walk that ends with no unresolved mismatches. Record `last_clean_pass_at`.
  - **State:** `users_verify_mismatch` and `users_migration_state`.
  - **If it fails:** an unfinished pass is not clean, so it is retried. A mismatch that repeats after its recheck blocks the next gate. It does not stop the verifier.

- [ ] **6. Ramp reads to Postgres**
  - **Starts when:** `last_clean_pass_at` is set after step 4 completes. The operator sets `users_read_source` to 1%, then 10%, then 50%, then 100%. The flag is keyed on `user_id`, so each user always reads from the same store.
  - **Does:** a read tries Postgres with a 200 ms timeout. While MySQL is the source, the read also checks `users_outbox` on the MySQL primary for that user id. If a pending row exists, the read goes to the MySQL primary, because Postgres may be behind. If Postgres errors or times out, the read falls back to the MySQL replica. Reads never fail.
  - **State:** the flag. The pending check reads MySQL.
  - **If it fails:** a mismatch or a Postgres read error sets `users_read_source` back to 0. Reads return to MySQL within about 30 s, with no outage. Instances can disagree on the flag for up to 30 s. That is harmless, because both stores are verified equal.

- [ ] **7. Soak for three days at 100% Postgres reads**
  - **Starts when:** every instance reports `users_read_source = 100%`. The clock `read_100_since` is set automatically.
  - **Does:** nothing beyond the verifier and monitoring. Any read served from MySQL resets the clock. This includes fallbacks and reads that the pending-write check sends to MySQL. Those are rare in normal operation. A Postgres outage therefore delays the switch, which is the intended strictness.
  - **State:** `read_100_since` in MySQL.
  - **If it fails:** the clock resets to zero. Mismatches found during the soak are repaired and logged. A mismatch that repeats blocks step 8.

- [ ] **8. Switch: Postgres becomes the source of truth**
  - **Starts when:** the operator runs procedure S, with MySQL as the old source and Postgres as the new source. These gates must pass before step 1 of procedure S:
    - `now - read_100_since >= 72 h`;
    - `last_clean_pass_at` is less than 24 h old, with no open mismatches;
    - the outbox row count is below the threshold set in step 0, and the oldest row is less than 60 s old;
    - Postgres is healthy;
    - replica lag is normal;
    - no backfill lease is held;
    - the operator approves.
  - **Does:** procedure S. Afterwards, writes commit to Postgres first. The outbox lives in Postgres, and the repairer mirrors writes to MySQL.
  - **State:** the control rows in both stores. `source_changed_at` in `users_migration_state` is set when step 6 of procedure S runs.
  - **If it fails:** before step 4 of procedure S, abort (see procedure S). After step 4, roll forward.

- [ ] **9. Mirror to MySQL while Postgres is the source (at least 14 days)**
  - **Starts when:** step 8 is complete. This runs automatically.
  - **Does:** a write goes to Postgres, with the control check and an outbox row in Postgres. Then the guarded copy runs into MySQL. The repairer copies Postgres outbox rows to MySQL. The verifier keeps comparing the MySQL mirror with the source. Reads go to Postgres. If Postgres errors, reads fall back to the MySQL replica. The mirror can be stale, so every such fallback is logged.
  - **State:** the Postgres outbox and control row. The MySQL mirror is the rollback target.
  - **If it fails:** if MySQL is down, writes still succeed on Postgres and the mirror backlog grows in the Postgres outbox. Rollback is blocked until that backlog drains.

- [ ] **10. Roll back to MySQL (possible only during step 9)**
  - **Starts when:** the operator runs procedure S, with Postgres as the old source and MySQL as the new source. Gates: the mirror backlog is drained, or can drain within the pause; the last clean pass is after step 8 and less than 24 h old; MySQL is reachable. At the start, set `users_read_source` to MySQL. Flag skew during the change is harmless.
  - **Does:** procedure S. Before unpausing (step 6 of procedure S), check that MySQL's AUTO_INCREMENT is above the largest id. InnoDB advances AUTO_INCREMENT only when the mirror inserts explicit ids, so it must be checked, not assumed.
  - **State:** the control rows.
  - **If it fails:** a drain that does not finish within 45 s aborts before step 4, and Postgres stays the source. Nothing is lost, because the Postgres outbox still holds every unmirrored write.

- [ ] **11. Postgres-only writes (no earlier than 14 days after step 8)**
  - **Starts when:** at least 14 days have passed since `source_changed_at` was set in step 8. The mirror outbox is empty. Postgres is healthy. The operator approves.
  - **Does:** run procedure S with Postgres as both the old and the new source. Steps 3 and 5 only matter when the source changes store, so they are skipped. In the step 4 commit, also set `mirror = off`. From then on, MySQL receives no writes. Rollback to MySQL is no longer possible, and the MySQL copy goes stale.
  - **State:** the Postgres control row.
  - **If it fails:** before step 4 of procedure S, abort (see procedure S). After step 4, roll forward. Postgres errors now fail writes with a retryable 503, because there is no other store to write to.

- [ ] **12. Drop the MySQL `users` table**
  - **Starts when:** step 11 has been in effect, a final logical dump of `users` has been taken and stored, and the change has been reviewed on its own. This is not part of the migration deploy. We recommend waiting a further 7 days after step 11. That number is our suggestion, not part of the brief.
  - **Does:** drops `users` and the MySQL migration tables (`users_outbox`, `users_control`, `users_migration_state`, `users_verify_mismatch`, and the MySQL `users_tombstones`). The tombstones remain in Postgres, because they are permanent. Remove the MySQL code paths.
  - **State:** the dump is the only copy of the old data.
  - **If it fails:** the drop cannot be reversed. Restore from the dump.

## Open questions and assumptions

- **Reads after step 11.** Postgres is then the only store. "Reads never fail" can hold only through a stale MySQL fallback, or by accepting a Postgres outage as a read outage. The brief does not settle this. Decide before step 11.
- **Outbox threshold.** The threshold for the step 8 gate is not yet set. Set it in step 0 monitoring.
- **Outbox load.** Each write adds an outbox insert and delete in MySQL, about 800 extra statements per second at peak (400 writes per second). During step 6, each read adds an indexed primary lookup, about 3,000 per second at peak. Check primary capacity before step 2.
- **Email uniqueness.** A copy can collide with a changed row's old email if copies arrive out of order. On a unique violation, the repairer re-reads the conflicting holder from the source, copies both rows, and retries them in one target transaction in id order, with backoff. Alert on repeats.
- **Id margin.** The 1,000,000-id margin is our assumption. It must be larger than any gap the sequence can create during a pause.
- **Erasure job.** It must treat 503 as retryable, or erasures fail silently during pauses.
- **Verifier scope.** The verifier reads the MySQL side from the replica, so it can report false mismatches for rows that are changing right now. The primary recheck exists for this reason.