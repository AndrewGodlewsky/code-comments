# Move `users` from MySQL 8 to Postgres 16

We move the `users` table from MySQL 8 to Postgres 16 in stages, with no downtime. Today every read and write goes through `UserRepository`, which reads from the MySQL replica and writes to the MySQL primary. MySQL stays the source of truth while each write is also copied to Postgres, and a queue table in MySQL records every user whose latest change Postgres may not have yet, so a missed copy is retried. Reads then move to Postgres in steps, the source of truth moves last, and MySQL keeps receiving copies for at least 14 days so we can roll back. Every copy goes through one routine that never overwrites a newer row, so copies can be retried or run out of order safely.

## Terms

- **Source of truth**: the store that decides what a user's data is. Writes commit there first.
- **Primary and replica**: MySQL's write server and its read copy. The replica trails the primary by its lag, in seconds (metric `mysql_replica_lag_seconds`).
- **Dual write**: each write goes to MySQL and then to Postgres.
- **Queue (`user_sync_queue`)**: one row per user whose latest change the other store may not have. It lives in the source store. It has one row per user, so its size follows the number of pending users, not the write rate.
- **`marked_at`**: the time of the latest change to a queued user. Every write sets it to now.
- **`claimed_until` and lease**: a sweeper's claim on a queue row, lasting 10 seconds. The claim expires on its own.
- **Sweeper**: a background worker that copies queued users to the other store.
- **apply_copy**: the one routine that copies a user row, or a deletion, into a store.
- **Version**: the `users.version` counter. It starts at 1 and goes up by 1 on each update.
- **Version rule**: a copy may insert a missing row, or replace a row whose version is lower. Nothing else.
- **Tombstone**: a record that a user id was erased. It blocks any later copy of that id.
- **Per-id lock**: a lock on one user id, so two copies of the same user run one at a time.
- **Digest**: a hash of a chunk of rows, used to find chunks that differ.
- **AUTO_INCREMENT and sequence**: MySQL's and Postgres's id counters. Each only moves up.
- **citext**: a Postgres text type that ignores case when comparing.
- **Flag**: a runtime setting that each instance reads. A percentage flag gives each user key a fixed bucket.
- **Status endpoint**: `GET /internal/users-migration`. It tells the switch tooling what an instance is doing.
- **In-flight write**: a `users` write that has started and not yet finished.
- **Gate**: a check that must pass before the next step starts.
- **Drain**: wait until a queue is empty and no lease is held.
- **Pause**: writes return 503 with `Retry-After: 1`. Reads continue.
- **Backfill**: a copy of all existing rows from the replica into Postgres, in id order.
- **Comparison**: a chunk-by-chunk check of the two tables for differences.
- **Shadow copy**: the store that is not the source of truth. After the write switch, MySQL is the shadow.
- **Build M1**: the app build that adds the queue, `apply_copy` and the status endpoint, with every flag at its safe default.
- **Orchestrator**: the system that runs the app's instances. How the switch tooling reads its replica count is an open question.
- **Redis**: an in-memory store behind the job queue (`jobs.enqueue`). Jobs run at least once. Failed jobs go to the dead-letter list `jobs:dead`, which nothing reads.

## How the system works

### Writes before the write switch

- Each write (create, update or delete) commits to MySQL. In the same MySQL transaction it upserts the user's queue row: `INSERT INTO user_sync_queue ... ON DUPLICATE KEY UPDATE marked_at = NOW(3)`. Deletes mark the user too.
- The queue is the durable record of what Postgres still owes. `jobs.enqueue` only wakes the sweeper early. It is not the record, because Redis can be down and failed jobs are never retried.
- After the MySQL commit, the write calls `apply_copy` to Postgres with a 200 ms wait. The result is ignored, and the copy may still finish after the wait ends. The design does not depend on that, because the queue row covers any missed copy and any crash between the commit and the copy.
- A Postgres failure never fails the user's request.

### apply_copy

One routine serves dual write, the sweeper, backfill and comparison repair. It takes `(target, user_id, row or deleted)`:

1. Take a per-id lock on the target: `pg_advisory_xact_lock` on Postgres, `GET_LOCK('users:<id>')` on MySQL.
2. If the target holds a tombstone for this id, stop.
3. For a row, run a conditional upsert. Postgres: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`. MySQL: `INSERT ... AS new ON DUPLICATE KEY UPDATE ... IF(users.version < new.version, ...)`. It inserts a missing row and replaces a row only when the target version is lower.
4. For a deletion, delete the row and insert a tombstone in one transaction.
5. Commit, then release the lock. Statements run after the lock is acquired, so they see committed data.

The version rule and the tombstone check make every copy safe to retry and safe to run out of order.

### Versions

- MySQL: create sets `version` to 1. Update adds 1 in the same SQL statement as the change. Delete removes the row. Only `UserRepository` writes `users`, because a lint rule blocks other SQL on it.
- Postgres: copies carry the source's version unchanged. In `pg` mode, the same update runs on Postgres and adds 1 there, and a create sets `version` to 1.

### Sweeper

- Runs on the worker fleet. It claims up to 500 queue rows, each with a 10 s lease, so only one sweeper works on a row.
- For each claimed row, it reads the current row from the source primary, never the replica, and applies it to the target with `apply_copy`. A missing row means the user was erased, so the sweeper applies a deletion.
- After the copy, it deletes the queue row only if `marked_at` is unchanged. If a write changed `marked_at` during the copy, the delete does nothing and the row stays.
- A write does not reset the lease. The row is retried when the lease ends, within 10 s.
- Retries back off exponentially, with no cap.

### Tombstones

- `users_tombstones(id PK, deleted_at)` lives in the target store and is never removed.
- Ids are never reused, because AUTO_INCREMENT and the Postgres sequence only move up.
- Every copy checks for a tombstone first, so a user removed by the erasure job never reappears. At about 2,000 deletes a day, the table stays small.

### Flags

- `users_pg_dual_write`: boolean, default off.
- `users_read_source`: percentage keyed by user id. 0 = MySQL, 100 = Postgres. It is read with `flags.enabled_for`, so each user stays on one source during the ramp.
- `users_write_source`: string `mysql`, `paused` or `pg`. Default `mysql`.
- Each instance refreshes its flags every 30 s, so instances can disagree for up to 30 s. Each transition therefore waits until every instance confirms it, not for a fixed sleep.
- Confirmation comes from the status endpoint, not the `app_flag_value` metric. Metrics are scraped, which adds delay, and exporting string flags is unverified.
- Write-source changes always pass through `paused`: `mysql -> paused -> pg` and `pg -> paused -> mysql`. The switch tooling refuses a direct change, so no instance writes to one store while another writes to the other.

### Status endpoint

- Every web and worker instance serves `GET /internal/users-migration`. It returns its build id, the flag values it is using now, and its in-flight `users` write count.
- A `users` write adds 1 to the count before it reads `users_write_source`, and subtracts 1 when it ends. A write that passes the check is therefore counted until it finishes.
- An instance reports `paused` when the flag says `paused` and its count is zero. That happens after in-flight writes finish, which takes at most the 5 s request timeout.
- During a pause the client sees only the 503 with `Retry-After: 1`. A write that already passed the check finishes normally.

### Ids

- MySQL allocates ids until the write switch.
- Each switch to `pg` sets the Postgres sequence, during the pause, to `max(MySQL AUTO_INCREMENT, max(id) in both stores) + 10,000,000`, then verifies it.
- In `pg` mode, creates take ids from the Postgres sequence. The MySQL shadow receives the row with that explicit id, which moves InnoDB's counter up.
- Each rollback checks that MySQL AUTO_INCREMENT is above `max(id)` before writes return to MySQL.

### Postgres schema

`users` mirrors MySQL: `id bigint primary key` (explicit ids until the switch), `email varchar(320)`, `name varchar(200)`, `plan varchar(20)`, `version integer`, `updated_at timestamp(3) without time zone`. Values are copied unchanged. MySQL's unique key on `email` ignores case under its default collation, so Postgres uses `citext` or a unique index on `lower(email)` to match.

### Signals to watch

Oldest queue row age (both stores); copy failure rate; read fallback rate; comparison mismatches and repairs; replica lag; backfill `last_id`; write-pause duration; reverse queue age in state `pg`.

## Rollout checklist

Each step says what starts it, what it does, where its state lives, and what happens if it fails. The write pause in steps 9 and 11 must stay within the 90 s limit in the brief. The plan aims for about 80 s.

- [ ] **0. Prepare Postgres. No user impact.**
  - **Starts:** The plan is approved.
  - **Does:** Creates `users`, `users_tombstones`, `migration_state` and `migration_runs` in `pg-core` through the repo's migrations. Confirms that the `app.db.postgres` pool connects from the web and worker fleets.
  - **State:** Postgres schema only.
  - **If it fails:** Nothing user-facing. Fix the cause and re-run the migrations, which are idempotent.

- [ ] **1. Create the MySQL support tables and deploy build M1 (dark) to every web and worker fleet.**
  - **Starts:** Step 0 is done. Normal deploy pipeline.
  - **Does:** Before the deploy, creates MySQL `user_sync_queue` and an empty `users_tombstones`. Build M1 adds the queue upsert to every write (create, update, delete), `apply_copy`, the status endpoint, and flag reads with defaults (dual write off, read source 0, write source `mysql`). Reads stay on MySQL, so users see no change.
  - **State:** MySQL `user_sync_queue` starts receiving rows. Flags are unchanged.
  - **If it fails:** Roll back the deploy. Queue rows already written are harmless and are processed once M1 runs again. The queue table must exist before M1 ships, because a missing table would fail user writes.

- [ ] **2. Gate 1: every instance runs M1.**
  - **Starts:** The deploy has finished.
  - **Does:** The switch tooling polls the status endpoint on every web and worker instance. The gate passes when, for every fleet, the reported count equals the orchestrator's replica count, and every instance reports build M1 for two consecutive minutes. Then it writes `gate_m1_at` to `migration_state`.
  - **State:** Postgres `migration_state`.
  - **If it fails:** The gate stays closed. Redeploy or restart the instance that is behind. Users are unaffected.

- [ ] **3. Turn on dual write and start the sweeper.**
  - **Starts:** Gate 1 has passed. An operator sets `users_pg_dual_write = true`.
  - **Does:** Dual write starts, as described under "Writes before the write switch". The sweeper starts on the worker fleet.
  - **State:** The flag; the MySQL queue, which holds all pending work; the Postgres copy.
  - **If it fails:** If Postgres is down or slow, writes still commit. Each write can wait up to 200 ms for Postgres, and that is its only cost. The queue grows, and the sweeper catches up when Postgres returns. Alert on the oldest queue row's age. To stop dual writes, set the flag to false. The queue keeps working.

- [ ] **4. Gate 2: every instance dual-writes.**
  - **Starts:** The step 3 flag is on.
  - **Does:** The gate passes when every web and worker instance reports build M1 and `users_pg_dual_write = true` continuously for 60 s, and the counts match the orchestrator. It writes `gate_dual_write_at`. The backfill refuses to start without this record.
  - **State:** Postgres `migration_state`.
  - **If it fails:** The gate stays closed. Investigate the instance that is behind (stale cache, hung process) and restart it. Users are unaffected.

- [ ] **5. Backfill `users` from the replica.**
  - **Starts:** `gate_dual_write_at` is recorded. One backfill worker at a time runs the batch loop, guarded by a lease.
  - **Does:** Repeats these steps:
    1. Take or renew the lease in `migration_state` (row `backfill`: owner, expires_at, last_id, done_at). Renew it every 30 s.
    2. Check replica lag with `SHOW REPLICA STATUS`. If it is above 5 s, sleep 5 s and check again. Do not read while lagging.
    3. Read up to 2,000 rows from the replica: `WHERE id > :last_id ORDER BY id LIMIT 2000`.
    4. Check lag again. If it is above 5 s, discard the batch and go back to 2.
    5. In one Postgres transaction, run `apply_copy` for each row in id order, then set `last_id` to the last id read. Commit.
    6. Sleep 250 ms to keep replica load low for reporting jobs. When a batch comes back empty, set `done_at` and release the lease.
  - **State:** The Postgres checkpoint commits in the same transaction as its batch.
  - **If it fails:** A crash before commit re-reads the batch on restart, from the last committed `last_id`. `apply_copy` is idempotent, so the re-read is safe. Replica or Postgres errors trigger exponential backoff. When the lease expires, another worker resumes from the checkpoint. A user erased after the replica read is removed by its queue row, and the tombstone blocks any later copy.

- [ ] **6. Compare until one clean run.**
  - **Starts:** `done_at` is set. Comparisons run hourly until the first clean run, then nightly.
  - **Does:** Walks ids in order, in chunks of 2,000, on the replica and in Postgres, and compares chunk digests over `(id, email, name, plan, version, updated_at at millisecond precision)`. For each differing chunk, it checks each id:
    - If the id is in the queue of the current source (checked on the primary), skip it. The change is in flight.
    - Otherwise, read the row from the primary and apply it to Postgres with `apply_copy`. Count it as a mismatch and a repair. A Postgres row that the primary does not have is applied as a deletion, and counts as a mismatch and a repair too.
    - If Postgres has a higher version than the primary, do not overwrite. Raise an alert and block the read ramp.
    A run is clean only if it finds zero mismatches and makes zero repairs. Each run writes a `migration_runs` row.
  - **State:** Postgres `migration_runs` and chunk checkpoints. Data changes only through `apply_copy`.
  - **If it fails:** The run resumes from its checkpoint. Users are unaffected. It throttles itself and pauses when replica lag exceeds 5 s.

- [ ] **7. Ramp reads to Postgres.**
  - **Starts:** A clean run from step 6 finished within the last 24 h, the queue's oldest row is within SLO, and there are no open anomalies.
  - **Does:** Sets `users_read_source` to 1, then 10, 50, 100. Holds each step long enough to cover a daily traffic cycle, and checks the signals. `get(id)` reads Postgres if `flags.enabled_for('users_read_source', id)` is true, otherwise the MySQL replica. A Postgres error, or a read over 200 ms, falls back to the MySQL replica for that request. Reads never fail during the migration.
  - **Stale reads:** A Postgres row can lag by the queue age, which is seconds when healthy. A user may briefly see old values after their own update, because there is no read-your-writes guarantee. A write made from a stale read fails with the existing `StaleWrite` (409), so stale data cannot silently overwrite newer data.
  - **Done when:** Every instance reports 100 on the status endpoint. Then write `reads_100_at`.
  - **State:** The flag; `migration_state.reads_100_at`.
  - **If it fails:** Set the flag back to 0, or to a lower step. MySQL is still the source of truth, so no pause is needed. The 3-day clock restarts.

- [ ] **8. Hold reads at 100% for three days.**
  - **Starts:** `reads_100_at` is recorded.
  - **Does:** Records the fallback rate, queue age and comparison result each day. A clean run must complete at least once every 24 h. Any violation resets the clock and returns to the read ramp. The write switch is allowed at `reads_100_at` + 72 h.
  - **State:** `migration_state`.
  - **If it fails:** As in the read ramp.

- [ ] **9. Write switch: Postgres becomes the source of truth. Writes are paused for at most 90 s (aim: about 80 s).**
  - **Starts:** An operator's go decision, with every precondition met: 72 h at 100% reads; a clean comparison within 24 h; queue age within SLO; fresh backups of both stores; Postgres sized for the write load.
  - **Does:** Let T0 be the moment `users_write_source` is set to `paused`.
    1. At T0, set `paused`. Writes return `503` with `Retry-After: 1`. Reads continue.
    2. From T0 until T0 + 45 s, the forward sweeper drains the queue. It runs until `user_sync_queue` has no rows and no leases. Writes are stopped, so the queue reaches empty. Poll all instances during this window.
    3. Decision point at T0 + 45 s. If every instance reports `paused` and the queue is drained, continue. Otherwise abort by setting `mysql`. This is safe because no Postgres writes have happened.
    4. Set the Postgres sequence `users_id_seq` to `max(MySQL AUTO_INCREMENT, max(id) in both stores) + 10,000,000`, then verify it.
    5. At T0 + 50 s at the latest, set `pg`. From this point the switch cannot be aborted back to MySQL, because some instances may already be writing to Postgres.
    6. Poll all instances until each reports `pg`. The flag refresh is 30 s, so this completes by about T0 + 80 s, and the pause ends then.
    7. Start the reverse sweeper, as described under "Keep MySQL in sync" below. Stop the forward sweeper.
  - **State:** The `users_write_source` flag; the Postgres sequence; the queue. Postgres is now the source of truth.
  - **If it fails:** Before step 5, abort as in step 3. After step 5, do not switch back to MySQL. Failures after this point are handled by the rollback. If an instance has not reported `pg` by T0 + 120 s, restart it. Until it does, its writes return 503.

- [ ] **10. Keep MySQL in sync as a shadow (ongoing).**
  - **Starts:** The write switch is done. This runs for at least 14 days.
  - **Does:** In `pg` mode, a write commits to Postgres, with its queue row in the Postgres `user_sync_queue` in the same Postgres transaction. It then applies to MySQL inline, with a 200 ms wait. The reverse sweeper drains the Postgres queue into MySQL with `apply_copy`, using the version rule and MySQL's `users_tombstones`. An erasure deletes in Postgres and marks the Postgres queue, and the sweeper then deletes in MySQL. The reverse comparison (the comparison in step 6 with the roles swapped) runs daily. The MySQL copy is the rollback target.
  - **State:** Postgres `users`, `user_sync_queue` and `users_tombstones`; the MySQL shadow copy and `users_tombstones`.
  - **If it fails:** If MySQL is down, writes continue in Postgres, the queue grows, and reverse sync resumes when MySQL returns. If Postgres is down, writes return 503. That is an incident, not the planned pause, and it is outside the 90 s budget. Reads fall back to the MySQL shadow, which can be behind by the queue age.

- [ ] **11. Roll back to MySQL. Allowed until step 12. Writes are paused for at most 90 s (aim: about 80 s).**
  - **Starts:** An operator decision, such as a Postgres data or latency incident. It needs Postgres to be reachable for the drain.
  - **Does:**
    1. At T0, set `paused`, as in the write switch.
    2. From T0 until T0 + 45 s, the reverse sweeper drains until the Postgres queue is empty and every row has reached MySQL. This drain is the no-loss proof: each acknowledged write stays in the queue until MySQL holds it. At T0 + 45 s, if not every instance is paused and drained, abort back to `pg`. This is safe because nothing was written to MySQL.
    3. Verify that MySQL `AUTO_INCREMENT` is above `max(id)`. If it is not, set it to `max(id) + 1`.
    4. At T0 + 50 s, set `mysql`. Start the forward sweeper. Its queue starts empty, so this is quick.
    5. Poll all instances until each reports `mysql`.
    6. After the write switch is confirmed, set `users_read_source` back to 0.
    7. Run a clean comparison (step 6) before reads may move back to Postgres.
  - **State:** The flags; the Postgres queue; the MySQL counter.
  - **If it fails:** Before the switch to `mysql`, abort back to `pg`. After it, restart any instance that has not reported `mysql`. It returns 503 until it does.

- [ ] **12. Point of no return: stop writing to MySQL. No pause.**
  - **Starts:** All of these hold: at least 14 days since the switch to `pg`; a clean reverse comparison within the last 24 h; reverse queue age within SLO; a sign-off recorded in `migration_state` (`pg_only_approved_by`, `pg_only_approved_at`).
  - **Does:** Drains the reverse queue into MySQL. Sets a new boolean flag `users_write_targets = pg_only`, which stops the inline MySQL copy. The status endpoint reports this flag too. Confirms that every instance reports it, then records `pg_only_at`. Takes a final export and backup of MySQL `users`. The rollback (step 11) is withdrawn from this point. No pause is needed, because the source of truth does not change. An instance that still copies to MySQL after the flag change is harmless, since MySQL is no longer read.
  - **State:** The flag; `migration_state`; the backup.
  - **If it fails:** Until every instance confirms the flag, a problem can still be handled by the rollback. Do not start step 13 until every instance has confirmed.

- [ ] **13. Drop the MySQL `users` table.**
  - **Starts:** Step 12 is done. MySQL `users` has had no reads or writes for at least 7 days (team decision). A backup restore test has passed. The team agrees.
  - **Does:** Drops MySQL `users`, `users_tombstones` and `user_sync_queue`. Removes the MySQL code from `UserRepository`. Updates the `no-raw-users-sql` lint rule for Postgres.
  - **State:** Postgres is the only store.
  - **If it fails:** Nothing user-facing, because the drop is the last step. Restore from the backup if needed.

## Open questions

- **How the switch tooling finds every web and worker instance, and where the expected count comes from.** The plan names the orchestrator's replica count but does not say how it is read. This must be settled before the first gate.
- **Whether the Postgres driver cancels a statement when the 200 ms wait ends.** The design works either way, so this does not block the plan.
- **Read-your-writes.** A user may briefly see old values after their own update. Is that acceptable for the product? Decide before the read ramp.
- **Rollback depends on Postgres durability.** If Postgres data is lost while it is the source of truth, writes acknowledged after the last drain are lost. Use synchronous replication and backups before the write switch. The 14-day minimum in step 12 ends this exposure.
- **The 90 s budget assumes the 30 s flag refresh.** If the refresh interval changes, recompute the abort points (T0 + 45 s and T0 + 50 s).
- **Erasure timing.** A user erased in MySQL can remain in Postgres until the sweeper applies the delete. Legal must set the target (proposed: 5 minutes).
- **Load.** Each write adds a queue upsert on the MySQL primary. Backfill and comparisons add load on the replica. The pacing values (2,000 rows, 5 s lag limit, 250 ms sleep, 500-row sweeps) are starting points to tune against reporting jobs.
- **Writes outside the repository** are not seen by the queue. The periodic comparison repairs them on its next run.
- **Team decisions:** read ramp step sizes and hold times, the 7-day quiet period before the drop, and the rollback window beyond its 14-day minimum (the brief sets 14 days as the minimum).