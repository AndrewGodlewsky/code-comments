# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

Each step is a checkbox. Do the steps in order and tick one only when its "done when" condition holds. Each step gives its trigger, what it changes, where its state lives, and what happens on failure.

## Design decisions (referenced by the steps)

1. **Repair uses a durable outbox, not the job queue.**
   - Redis can be down, `enqueue` can raise, and jobs go to `jobs:dead` after about 15 minutes with nothing processing them. That can't carry a "fixed automatically" guarantee.
   - Each store gets a table `users_sync_outbox(id, user_id, attempts, next_attempt_at)`. The write transaction on the current source of truth (SoT) inserts the outbox row in the same transaction as the user change. A crash between the commit and the copy therefore cannot lose the repair intent.
   - A separate `users-sync-worker` process claims rows with `FOR UPDATE SKIP LOCKED`.
     - It reads the current row from the SoT primary, never the replica.
     - It applies the row to the other store using the version rule.
     - If the row is gone, it applies a delete and writes a tombstone.
     - Then it deletes only the outbox ids it claimed.
   - Rows retry forever with capped backoff (60 s). There is no dead-letter list. The alert is: oldest outbox row older than 5 minutes.
   - The worker is idempotent, so running several is safe.
2. **The version rule is a single SQL statement.**
   - `INSERT ... ON CONFLICT (id) DO UPDATE SET ... WHERE users.version < EXCLUDED.version`, and only when no tombstone exists for the id.
   - Every copy path uses it: inline dual write, backfill, repair and rollback sync. `updated_at` is copied verbatim from the source, never regenerated.
3. **Deletes use tombstones.**
   - `users_tombstone(id, deleted_at)` exists in both stores. It holds no PII.
   - Delete means: delete the user row and insert the tombstone in one transaction on the target.
   - Every copy statement includes `AND NOT EXISTS (tombstone for id)`. This closes the race where backfill or repair holds a stale copy of a row that erasure just removed.
   - Tombstones are kept until the MySQL table is dropped.
4. **Write coordination uses a fence row plus a flag.**
   - Each store has a one-row table `write_fence(writable)`. Every write transaction on the SoT store starts with `SELECT writable ... FOR SHARE` (`LOCK IN SHARE MODE` on MySQL). If it is false, the repository raises `WritesPaused`, which the HTTP layer maps to a retryable 503.
   - Closing the fence is `UPDATE write_fence SET writable = false`. It waits for in-flight write transactions and then blocks every later one.
   - Correctness therefore never depends on the 30-second flag refresh. A stale instance hits the closed fence and gets a 503. It can never write to the old SoT and cause a split brain.
   - The flag `users_write_mode` only says where instances should go. Its values are `mysql_only`, `dual_mysql_primary`, `dual_pg_primary` and `pg_only`.
5. **Backfill progress lives in Postgres.**
   - The cursor is in `migration_progress(job, last_id, status, lease_owner, lease_expires_at, run_id)`.
   - It is updated in the same Postgres transaction as the batch it describes, so a crash continues exactly after the last completed batch.
6. **After the switch, Postgres assigns ids.** The sequence is set during the pause to MySQL's `AUTO_INCREMENT` value, not `max(id)+1`. That way an id freed by a deletion at the top of the range is never reused, which protects tombstones. During the earlier dual-write phase, Postgres rows are inserted with the explicit MySQL id. A later rollback is safe because InnoDB raises its counter when an explicit larger id is inserted, and the rollback step checks this.
7. **All SQL on `users` stays inside the repository module** because of the `no-raw-users-sql` lint rule. The backfill, comparison and worker call new repository methods (`copy_batch`, `compare_range`, `apply_outbox`) in `user_repository.py`, or in a sibling module added to the lint allowlist.

---

## Steps

- [ ] **1. Create the schema (migration run, no app change).**
  - **Starts when:** a manual migration run, after a rehearsal of the whole plan on a staging copy.
  - **Changes:**
    - Postgres `users` with the same columns and unique `email`, `id BIGINT` with a sequence (no default yet), `updated_at timestamptz(3)` in UTC.
    - `users_tombstone`, `users_sync_outbox`, `write_fence` (`writable = true`) and `migration_progress` in Postgres.
    - `users_tombstone`, `users_sync_outbox` and `write_fence` (`writable = 1`) in MySQL.
  - **State:** the tables themselves.
  - **If it fails:** every change is additive and unused, so drop the new tables and retry.

- [ ] **2. Deploy repository v1 with `users_write_mode=mysql_only` and `users_read_pg_percent=0`.**
  - **Starts when:** a normal deploy, after step 1.
  - **Changes:**
    - The repository supports all four modes.
    - Every MySQL write transaction checks the fence.
    - `create` and `update` re-select the row inside the transaction so the full row is available for copying.
    - Reads on Postgres fall back to the MySQL replica on a Postgres error, a timeout of 250 ms, or a miss (before the switch only).
    - In `mysql_only` mode behaviour is unchanged apart from the fence check.
  - **State:** the flags in `app.flags`.
  - **Done when:** the old version is gone from every instance and all instances export `app_flag_value{flag="users_write_mode"}`.
  - **If it fails:** roll back the deploy. The new tables are harmless.

- [ ] **3. Deploy `users-sync-worker` and the alerts.**
  - **Starts when:** a deploy, after step 2.
  - **Changes:**
    - A new worker process that polls the SoT outbox every 1 s.
    - Alerts on outbox age over 5 minutes, outbox depth, Postgres apply error rate and `WritesPaused` count.
  - **State:** the outbox (empty so far).
  - **If it fails:** stop the worker. The outbox is durable, so nothing is lost.

- [ ] **4. Turn on dual writes: set `users_write_mode=dual_mysql_primary`.**
  - **Starts when:** steps 2 and 3 are done and Postgres is healthy.
  - **Changes:**
    - Each write commits to MySQL together with its outbox row. Then the instance tries the Postgres copy inline with a 250 ms timeout, inside try/except. On success it deletes its outbox row.
    - A circuit breaker skips the inline attempt for 5 s after repeated Postgres failures, so a slow Postgres never slows requests.
    - A Postgres failure is only logged. The request succeeds and the worker repairs the row within seconds.
  - **State:** MySQL (the data, tombstones and outbox) and Postgres (copies).
  - **If it fails:** set the flag back to `mysql_only`. Postgres is then stale, so reset the backfill cursor to 0 and re-run steps 6 to 8. This is cheap because of the version rule.

- [ ] **5. Gate: confirm every instance is dual-writing.**
  - **Starts when:** step 4 has been applied.
  - **Condition, all required:**
    - `app_flag_value{flag="users_write_mode"}` reads `dual_mysql_primary` on every running instance. The number of reporting series must equal the instance count, so a missing instance counts as not ready.
    - No instance runs the old code.
    - Both conditions have held for at least 2 minutes. That covers one flag refresh plus in-flight requests that started under the old value.
    - The outbox is draining.
  - **State:** Prometheus metrics. The operator records the pass time in `migration_progress` (job `gate`).
  - **If it fails:** wait. Backfill must not start. New instances read the flag on boot, so autoscaling does not break the gate.

- [ ] **6. Run the backfill.**
  - **Starts when:** the step 5 gate has passed. A manually started `users-backfill` job.
  - **Changes:** copies MySQL to Postgres in a loop.
    1. Check `mysql_replica_lag_seconds`. If it is above 5, or the metric is unavailable, sleep 10 s and recheck. This fails closed.
    2. Read `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` from the replica.
    3. In one Postgres transaction, apply the batch with the version-rule statement (tombstone-guarded) and set `last_id` to the batch's highest id.
    4. Sleep a short throttle interval, then repeat. There are about 19,000 batches.
  - **State:** `migration_progress` row `backfill`, with a lease (`lease_owner`, `lease_expires_at`) so only one runner is active.
  - **If it fails:**
    - After a crash the lease expires and the next run continues from `last_id`.
    - A Postgres error means retry the same batch with backoff, and the cursor does not move.
    - A unique-`email` conflict in a batch makes it retry row by row. The conflicting row is logged and left for step 8, because another row's pending update usually resolves it.
    - A stale replica row cannot overwrite newer data (version rule) or resurrect a deleted user (tombstone).

- [ ] **7. Confirm the backfill is finished.**
  - **Starts when:** the cursor passes the MySQL `max(id)` and the outbox backlog is empty.
  - **Changes:** the backfill sets its status to `done`. One more pass runs from `last_id` up to the current max id to catch rows created during the run.
  - **State:** `migration_progress`.
  - **If it fails:** resume the backfill.

- [ ] **8. Run the full comparison until it is clean.**
  - **Starts when:** step 7 is done. A `users-compare` job.
  - **Changes:**
    - It walks fixed id ranges of 100,000 ids and compares `(id, version, hash of email, name, plan, updated_at)` from the MySQL replica and the Postgres primary. It honours the 5 s lag rule.
    - It finds ids that are missing, extra, differing, or present in both a user row and a tombstone.
    - Every mismatch is re-checked about 10 s later against the MySQL primary, skipping ids with a pending outbox row. Ids still mismatched are confirmed. Each confirmed id is inserted into the outbox, so repair is automatic.
  - **State:** `migration_progress` (job `compare`, `run_id`, range cursor, `confirmed_mismatches`).
  - **Pass condition:** a complete run that started after step 7 and has `confirmed_mismatches = 0`. If a run finds mismatches, wait for the outbox to drain and run again.
  - **If it fails:** a crash resumes at the range cursor. Persistent mismatches that keep coming back mean a bug. Stop and investigate, and do not go to step 9.

- [ ] **9. Ramp reads to Postgres.**
  - **Starts when:** step 8 has passed.
  - **Changes:** set the percentage flag `users_read_pg_percent` to 1, 10, 50, then 100. Hold at least 30 minutes at each stage. `get` uses `flags.enabled_for("users_read_pg", user_id)`, so a user always gets the same answer. A Postgres read that errors, times out or misses falls back to the MySQL replica, so reads never fail.
  - **State:** the flag. Watch the Postgres read error rate, the fallback rate and latency.
  - **If it fails:** lower the percentage (effective within 30 s). If reads were wrong, the comparison in step 10 will show it.

- [ ] **10. Soak: 100% reads on Postgres for at least 3 days.**
  - **Starts when:** all instances report `users_read_pg_percent = 100`.
  - **Changes:** nothing. The comparison reruns nightly, and the outbox alert stays on.
  - **State:** `migration_progress` job `soak` holds the start time.
  - **Pass condition:** 72 hours continuous at 100% with all nightly runs clean. My choice: any drop below 100% or any confirmed mismatch restarts the 72 hours.
  - **If it fails:** go back to step 9 or 8 as needed.

- [ ] **11. Switch the source of truth to Postgres (writes paused, 90 s maximum).**
  - **Starts when:**
    - Step 10 has passed.
    - The outbox is near empty.
    - A named operator is ready, with the scripted runbook rehearsed in staging.
  - **Procedure** (T0 is the moment the old fence closes):
    1. **T0:** close the MySQL fence. In-flight writes finish, and new writes get 503s. Reads are unaffected.
    2. Wait for the MySQL outbox to reach zero (normally a few seconds). Because every commit wrote its outbox row atomically, an empty outbox means Postgres holds everything.
    3. Read `AUTO_INCREMENT` from `information_schema.tables` with `information_schema_stats_expiry=0` for the session. Call `setval` on the Postgres id sequence to that value and attach it as the column default.
    4. Set `users_write_mode` to `dual_pg_primary` and open the Postgres fence, together. Writes now go to Postgres first, then are copied to MySQL under the same rules, with the outbox in Postgres.
    5. **Abort deadline: T0+40 s.** If steps 2 and 3 are not finished by then, reopen the MySQL fence and leave the flag alone. The pause ends at about 40 s and nothing has changed.
  - **Timing:** the flag takes up to about 30 s to reach every instance. An instance that still has the old value writes to the closed MySQL fence and gets a retryable 503. The worst case is about 40 s + 30 s = 70 s, which is under the 90 s limit.
  - **State:** `write_fence` in both stores, the flag, and the sequence.
  - **If it fails:** use the abort above. After the flip, use the rollback in step 12.

- [ ] **12. Run reverse dual writes for at least 14 days, with rollback ready.**
  - **Starts when:** step 11 completed. The 14 days are counted from the time step 11 finished.
  - **Changes:** MySQL is now the secondary. The worker and nightly comparison keep running. The Postgres outbox is the reverse repair queue, with an alert if it is over 30 s old.
  - **Rollback to MySQL (any time before step 13), as a mirror of step 11:**
    1. Close the Postgres fence.
    2. Drain the Postgres outbox to zero.
    3. Check that MySQL `AUTO_INCREMENT` is above the maximum Postgres id. If it isn't, raise it.
    4. Set `users_write_mode` to `dual_mysql_primary` and open the MySQL fence.
    5. Abort deadline: T0+40 s, with the same timing as step 11.
    - Postgres keeps receiving writes afterwards, so it stays current.
  - **Known limit:** if Postgres is unreachable, writes committed there but not yet copied stay inside Postgres. Rollback has to wait for Postgres to come back. Keeping the reverse outbox near-empty (the 30 s alert) keeps that exposure small.
  - **State:** the Postgres outbox, the fences and the flag.
  - **If it fails:** if the drain does not finish before T0+40 s, abort as in step 11 and try again later. Writes during that attempt are still safe on Postgres.

- [ ] **13. Switch to Postgres-only writes.**
  - **Starts when:**
    - At least 14 days have passed since step 11.
    - The last 3 comparison runs are clean.
    - The Postgres outbox is empty.
    - Nobody wants a rollback.
  - **Changes:** set `users_write_mode=pg_only`. Instances stop copying to MySQL and stop writing outbox rows. The source of truth does not change, so no write pause is needed. The 30 s flag difference is harmless because stray late copies only go to the MySQL table that is about to be retired.
  - **State:** the flag. Rollback to MySQL is no longer possible without a new backfill from Postgres.
  - **If it fails:** set the flag back to `dual_pg_primary`, and run the comparison before trusting MySQL again.

- [ ] **14. Retire MySQL.**
  - **Starts when:** step 13 has been stable for 7 days.
  - **Changes:**
    - Revoke the application's write grant on MySQL `users`, and take and keep a final snapshot.
    - Then drop the MySQL `users` table, its outbox, tombstone and fence tables.
    - In a later deploy, remove the dual-write, fence, outbox and fallback code and the migration flags. Drop the Postgres outbox, `write_fence` and tombstone tables.
  - **State:** the snapshot.
  - **If it fails:** a failed grant revoke or snapshot just stops this step. Do not drop before the snapshot exists.
