# Move `users` from MySQL 8 to Postgres 16

## Design decisions

1. **Durable dirty set in the source store.** Every `UserRepository` write (create, update, delete) upserts `user_sync_queue(user_id PK, marked_at, claimed_until)` in the same MySQL transaction as the `users` change, using `ON DUPLICATE KEY UPDATE marked_at = NOW(3)`. The table holds one row per user with unsynced changes, so its size follows the number of distinct pending users, not the ~400 writes/s (an event log would add about 35M rows a day). Deletes mark the user too. This table is the durable record of what Postgres still owes. `jobs.enqueue` is only a wake-up nudge: Redis can be down, and failed jobs land in `jobs:dead`, which nothing reads.
2. **Copies come from the primary, never the replica.** A sweeper claims queue rows with a 10-second lease, reads the current row from the source primary, and applies it to the target. A missing row means the user was erased. After the copy commits, the sweeper deletes the queue row only if `marked_at` is unchanged. If it changed, a newer change is pending and is handled on the next pass.
3. **One copy routine for every writer.** Dual write, sweeper, backfill and comparison repair all call `apply_copy(target, user_id, row | deleted)`:
   1. Take a per-id lock on the target: `pg_advisory_xact_lock` on Postgres, `GET_LOCK('users:<id>')` on MySQL.
   2. If the target holds a tombstone for the id, stop.
   3. For a row, run a conditional upsert: Postgres `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`; the MySQL equivalent is `INSERT ... AS new ON DUPLICATE KEY UPDATE ... IF(users.version < new.version, ...)`. Insert if missing, replace only if the target version is lower. Nothing else.
   4. For a deletion, delete the row and insert a tombstone in one transaction.
   5. Commit, then release the lock. Statements run after the lock is acquired, so they see committed data.

   The version rule and the tombstone check make every copy safe to retry and safe to run out of order.
4. **Tombstones.** `users_tombstones(id PK, deleted_at)` lives in the target store and is never removed. Ids are never reused: MySQL `AUTO_INCREMENT` only moves up, and the Postgres sequence only moves up. At about 2,000 deletes a day the table stays small.
5. **Flags coordinate the switches, and each instance is confirmed directly.** Flags:
   - `users_pg_dual_write` (boolean, default off)
   - `users_read_source` (percentage, keyed by user id; 0 = MySQL, 100 = Postgres; read with `flags.enabled_for`, so each user stays on one source while the ramp runs)
   - `users_write_source` (string: `mysql`, `paused`, `pg`; default `mysql`)

   Every web and worker instance exposes `GET /internal/users-migration`, returning its build id, the three flag values it is using now, and its count of in-flight `users` writes. The switch tooling polls that endpoint on every instance. It does not rely on the `app_flag_value` metric: metrics are scraped, which adds delay, and the export of string-valued flags is unverified. Flag caches refresh every 30 s, so each transition waits for confirmation from every instance, not for a fixed sleep.
6. **Write-source changes always go through `paused`.** The only allowed transitions are `mysql -> paused -> pg` and `pg -> paused -> mysql`. The switch tooling refuses a direct change, so no instance writes to one store while another writes to the other.
7. **New ids.** MySQL allocates ids until the write switch. Each switch to Postgres sets the Postgres sequence during the pause to `max(MySQL AUTO_INCREMENT, max(id) in both stores) + 10,000,000`. In `pg` mode, creates take ids from that sequence and MySQL receives the row with the explicit id. Explicit inserts raise InnoDB's counter. Each rollback verifies that the counter is above `max(id)` before writes return to MySQL.
8. **Schema.** Postgres `users` mirrors MySQL: `id bigint primary key` (explicit ids until the switch), `email varchar(320)`, `name varchar(200)`, `plan varchar(20)`, `version integer`, `updated_at timestamp(3) without time zone`. Values are copied unchanged. MySQL's unique key on `email` is case-insensitive under its default collation, so Postgres uses `citext` or a unique index on `lower(email)` to match.
9. **Signals to watch.** Oldest row age in `user_sync_queue` (both stores); copy failure rate; read fallback rate; comparison mismatches and repairs; replica lag; backfill `last_id`; write-pause duration; reverse queue age in state `pg`.

## Checklist

Each step gives what starts it, what it changes, where its state lives, and what happens on failure.

- [ ] **0. Prepare Postgres. No user impact.**
  - **Starts:** This plan is approved.
  - **Does:** Creates `users`, `users_tombstones`, `migration_state` and `migration_runs` in `pg-core` through the repo's migrations. Confirms that the `app.db.postgres` pool connects from web and worker fleets.
  - **State:** Postgres schema only.
  - **If it fails:** Nothing user-facing. Fix the cause and re-run the migrations, which are idempotent.

- [ ] **1. Create the MySQL support tables and deploy build M1 (dark) to web and every worker fleet.**
  - **Starts:** Step 0 is done. Normal deploy pipeline.
  - **Does:** Before the deploy, creates MySQL `user_sync_queue` and an empty `users_tombstones`. M1 adds: the queue upsert in every `UserRepository` write transaction (create, update, delete); `apply_copy`; the status endpoint; flag reads with defaults (dual write off, read source 0, write source `mysql`). Reads stay on MySQL. Users see no change.
  - **State:** MySQL `user_sync_queue` starts receiving rows. Flags are unchanged.
  - **If it fails:** Roll back the deploy. Queue rows already written are harmless and are processed once M1 runs again. The queue table must exist before M1 ships, because a missing table would fail user writes.

- [ ] **2. Gate 1: every instance runs M1.**
  - **Starts:** Deploy finished.
  - **Does:** The switch tooling polls the status endpoint on every web and worker instance. The gate passes when, for all fleets, the reported count equals the orchestrator's replica count and every instance reports build M1 for two consecutive minutes. Writes `gate_m1_at` to `migration_state`.
  - **State:** Postgres `migration_state`.
  - **If it fails:** The gate stays closed. Redeploy or restart the instance that is behind. Users are unaffected.

- [ ] **3. Turn on dual write and start the queue sweeper.**
  - **Starts:** Gate 1 has passed. An operator sets `users_pg_dual_write = true`.
  - **Does:** After each MySQL commit, the write applies its change to Postgres inline, with a 200 ms timeout. The result is ignored, and the queue row covers any miss. A crash between the MySQL commit and the inline copy is also covered by the queue row. The sweeper starts on the worker fleet. It claims up to 500 queue rows, applies each with `apply_copy` to Postgres, and deletes each queue row only if `marked_at` is unchanged. Retries use exponential backoff, with no cap.
  - **State:** The flag; the MySQL queue, which holds all pending work; the Postgres copy.
  - **If it fails:** If Postgres is down or slow, writes still commit. Each write can wait up to 200 ms for Postgres, and that is its only cost. The queue grows and the sweeper catches up when Postgres returns. Alert on the oldest queue row's age. To stop dual writes, set the flag to false; the queue keeps working.

- [ ] **4. Gate 2: every instance dual-writes.**
  - **Starts:** Step 3 flag is on.
  - **Does:** The gate passes when every web and worker instance reports build M1 and `users_pg_dual_write = true` continuously for 60 s, and the counts match the orchestrator. Writes `gate_dual_write_at`. The backfill refuses to start without this record.
  - **State:** Postgres `migration_state`.
  - **If it fails:** The gate stays closed. Investigate the instance that is behind (stale cache, hung process) and restart it. Users are unaffected.

- [ ] **5. Backfill `users` from the replica.**
  - **Starts:** `gate_dual_write_at` is recorded. The backfill worker runs one batch loop at a time, guarded by a lease.
  - **Does:** Loops as follows.
    1. Take or renew the lease in `migration_state` (row `backfill`: owner, expires_at, last_id, done_at). Renew it every 30 s.
    2. Check replica lag with `SHOW REPLICA STATUS`. If it is above 5 s, sleep 5 s and check again. Do not read while lagging.
    3. Read up to 2,000 rows from the replica: `WHERE id > :last_id ORDER BY id LIMIT 2000`.
    4. Check lag again. If it is above 5 s, discard the batch and go back to 2.
    5. In one Postgres transaction, run `apply_copy(pg, row)` for each row in id order, then set `last_id` to the last id read. Commit.
    6. Sleep 250 ms to keep replica load low for reporting jobs. When a batch comes back empty, set `done_at` and release the lease.
  - **State:** The Postgres checkpoint commits in the same transaction as its batch.
  - **If it fails:** A crash before commit re-reads the batch on restart from the last committed `last_id`; `apply_copy` is idempotent. Replica or Postgres errors trigger exponential backoff. The lease expires and another worker resumes from the checkpoint. A user erased after the replica read is removed by its queue row, and the tombstone blocks any later copy.

- [ ] **6. Compare until one clean run.**
  - **Starts:** `done_at` is set. Comparisons run hourly until the first clean run, then nightly.
  - **Does:** Walks ids in order, in chunks of 2,000, on the replica and in Postgres, and compares chunk digests over `(id, email, name, plan, version, updated_at at millisecond precision)`. For each differing chunk, checks each id:
    - If the id is in the MySQL queue (checked on the primary), skip it. The change is in flight.
    - Otherwise, read the row from the primary and apply it to Postgres with `apply_copy`. Count it as a mismatch and a repair. A Postgres row that the primary does not have is applied as a deletion.
    - If Postgres has a higher version than the primary, do not overwrite. Raise an alert and block the read ramp.

    A run is clean only if it finds zero mismatches and makes zero repairs. Each run writes a `migration_runs` row.
  - **State:** Postgres `migration_runs` and chunk checkpoints. Data changes only through `apply_copy`.
  - **If it fails:** The run resumes from its checkpoint. Users are unaffected. The run throttles itself and pauses when replica lag exceeds 5 s.

- [ ] **7. Ramp reads to Postgres.**
  - **Starts:** A clean run from step 6 finished within the last 24 h, the queue's oldest row is within SLO, and there are no open anomalies.
  - **Does:** Sets `users_read_source` to 1, then 10, 50, 100. Holds each step long enough to cover a daily traffic cycle and checks the signals. The read path for `get(id)` reads Postgres if `flags.enabled_for('users_read_source', id)` is true, otherwise the MySQL replica. A Postgres error, or a read over 200 ms, falls back to the MySQL replica for that request. A stale Postgres row is bounded by queue age. A write made from a stale read fails with the existing `StaleWrite` (409), so stale data cannot silently overwrite newer data. When every instance reports 100 (the status endpoint, not the metric), writes `reads_100_at`.
  - **State:** The flag; `migration_state.reads_100_at`.
  - **If it fails:** Set the flag back to 0, or to a lower step. MySQL is still the source of truth, so no pause is needed. The 3-day clock restarts.

- [ ] **8. Hold reads at 100% for three days.**
  - **Starts:** `reads_100_at` is recorded.
  - **Does:** Records the fallback rate, queue age and comparison result each day. A clean run must complete at least once every 24 h. Any violation resets the clock and returns to step 7. Eligible for step 9 at `reads_100_at` + 72 h.
  - **State:** `migration_state`.
  - **If it fails:** As in step 7.

- [ ] **9. Write switch: MySQL becomes the Postgres source. Writes are paused for at most 80 s.**
  - **Starts:** An operator's go decision, with all preconditions met: 72 h at 100% reads; a clean comparison within 24 h; queue age within SLO; fresh backups of both stores; Postgres sized for the write load.
  - **Does:** Let T0 be the moment `users_write_source` is set to `paused`.
    1. At T0, set `paused`. Writes return `503` with `Retry-After: 1`. Reads continue. Each instance reports `paused` only after its in-flight `users` writes finish, which takes at most the 5 s request timeout.
    2. Poll all instances. Decision point T0 + 45 s: if every instance reports `paused` and the queue is drained, continue. Otherwise abort by setting `mysql`. This is safe because no Postgres writes happened.
    3. Drain: the sweeper runs until `user_sync_queue` has no rows and no leases. Writes are stopped, so the queue reaches empty.
    4. Set the Postgres sequence `users_id_seq` to `max(MySQL AUTO_INCREMENT, max(id) in both stores) + 10,000,000`, then verify it.
    5. At T0 + 50 s at the latest, set `pg`. From this point the switch cannot be aborted back to MySQL, because some instances may already be writing to Postgres.
    6. Poll all instances until each reports `pg`. The refresh interval is 30 s, so this completes by about T0 + 80 s and the pause ends then.
    7. Start the reverse sweeper (step 10). Stop the forward sweeper.
  - **State:** The `users_write_source` flag; the Postgres sequence; the queue. Postgres is now the authoritative store.
  - **If it fails:** Before step 5, abort as in step 2. After step 5, do not switch back to MySQL. Failures after this point are handled by the rollback in step 11. If one instance has not reported `pg` by T0 + 120 s, restart it; until it does, its writes return 503.

- [ ] **10. Keep MySQL in sync as a shadow (ongoing).**
  - **Starts:** Step 9 is done. This runs for at least 14 days.
  - **Does:** In `pg` mode, a write commits to Postgres, with its queue row in the Postgres `user_sync_queue`, and then applies to MySQL inline with a 200 ms timeout. The reverse sweeper drains the Postgres queue into MySQL with `apply_copy`, using the version rule and the MySQL `users_tombstones`. An erasure deletes in Postgres, marks the queue, and the sweeper then deletes in MySQL. The reverse comparison (step 6 with the roles swapped) runs daily. The MySQL copy is the rollback target.
  - **State:** Postgres `users`, `user_sync_queue` and `users_tombstones`; the MySQL shadow copy and `users_tombstones`.
  - **If it fails:** If MySQL is down, writes continue in Postgres, the queue grows, and reverse sync resumes when MySQL returns. If Postgres is down, writes return 503. That is an incident, not the planned pause, and it is outside the 90 s budget. Reads fall back to the MySQL shadow, which can be behind by the queue age.

- [ ] **11. Roll back to MySQL.** Allowed until step 12. Writes are paused for at most 80 s.
  - **Starts:** An operator decision, such as a Postgres data or latency incident. It needs Postgres reachable for the drain.
  - **Does:**
    1. At T0, set `paused`, as in step 9. If not every instance is paused and drained by T0 + 45 s, abort back to `pg`. That is safe because nothing was written to MySQL.
    2. Drain: the reverse sweeper runs until the Postgres queue is empty and every row has reached MySQL. This drain is the no-loss proof: each acknowledged write stays in the queue until MySQL holds it.
    3. Verify that MySQL `AUTO_INCREMENT` is above `max(id)`. If it is not, set it to `max(id) + 1`.
    4. At T0 + 50 s, set `mysql`. Start the forward sweeper. Its queue starts empty, so this is quick.
    5. Poll all instances until each reports `mysql`.
    6. After the write switch is confirmed, set `users_read_source` back to 0.
    7. Run a clean comparison (step 6) before reads may move back to Postgres.
  - **State:** The flags; the Postgres queue; the MySQL counter.
  - **If it fails:** Before step 4, abort back to `pg`. After step 4, restart any instance that has not reported `mysql`. It returns 503 until it does.

- [ ] **12. Point of no return: stop writing to MySQL. No pause.**
  - **Starts:** All of these hold: at least 14 days since the step 9 flip to `pg`; a clean reverse comparison within the last 24 h; reverse queue age within SLO; a sign-off recorded in `migration_state` (`pg_only_approved_by`, `pg_only_approved_at`).
  - **Does:** Drains the reverse queue into MySQL. Sets a new boolean flag `users_write_targets = pg_only`, which stops the inline MySQL copy. Confirms every instance reports it, then records `pg_only_at`. Takes a final export and backup of MySQL `users`. The rollback runbook (step 11) is withdrawn from this point. No pause is needed, because the source of truth does not change. An instance that still copies to MySQL after the flag change is harmless, since MySQL is no longer read.
  - **State:** The flag; `migration_state`; the backup.
  - **If it fails:** Until every instance confirms the flag, a problem can still be handled by step 11. Do not start step 13 until every instance has confirmed.

- [ ] **13. Drop the MySQL `users` table.**
  - **Starts:** Step 12 is done, MySQL `users` has had no reads or writes for at least 7 days (team decision), a backup restore test has passed, and the team agrees.
  - **Does:** Drops MySQL `users`, `users_tombstones` and `user_sync_queue`. Removes the MySQL code from `UserRepository`. Updates the `no-raw-users-sql` lint rule for Postgres.
  - **State:** Postgres is the only store.
  - **If it fails:** Nothing user-facing, because the drop is the last step. Restore from the backup if needed.

## Open items and risks

- **Rollback depends on Postgres durability.** If Postgres data is lost during step 10, writes acknowledged after the last drain are lost. Use synchronous replication and backups before step 9. The 14-day window in step 12 ends this exposure.
- **Postgres outage in `pg` mode** returns 503s for writes. These are not planned pauses, so they fall outside the 90 s budget.
- **Read staleness.** Postgres reads can lag by the queue age, which is seconds when healthy. A stale read surfaces as a `StaleWrite` 409, not as data loss.
- **The 90 s budget** assumes the 30 s flag-cache refresh. The abort points at T0 + 45 s and T0 + 50 s keep the worst case near 80 s. If the refresh interval changes, these numbers must be recomputed.
- **The status endpoint is a required build item.** The switch decisions do not use the `app_flag_value` metric, whose export of string flags is unverified.
- **Erasure timing.** A user erased in MySQL can remain in Postgres until the sweeper applies the delete. Legal must set the target (proposed: 5 minutes).
- **Load.** Each write adds a queue upsert on the MySQL primary. Backfill and comparisons add load on the replica. The pacing values (2,000 rows, 5 s lag limit, 250 ms sleep, 500-row sweeps) are starting points to tune against reporting jobs.
- **Writes outside the repository** are not seen by the queue. The periodic comparison repairs them on its next run.
- **Team decisions:** read ramp step sizes and hold times, the 7-day quiet period before the drop, and the 14-day rollback window.