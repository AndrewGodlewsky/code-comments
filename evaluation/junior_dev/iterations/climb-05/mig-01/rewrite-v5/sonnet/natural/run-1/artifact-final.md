# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

## Summary

Today every read and write of `users` goes through `UserRepository`. Reads use the MySQL replica. Writes go to the MySQL primary. The table has about 38 million rows, with peaks of about 3,000 reads/s and 400 writes/s. The Postgres 16 cluster (`pg-core`) is ready and empty.

The plan moves the table in stages. First we write to both databases, with MySQL as the source of truth (SoT). Then we copy the old rows across (the backfill) and compare the two tables. Then we move reads to Postgres. After a soak, we briefly pause writes (90 s at most) and make Postgres the SoT, while still copying every write back to MySQL so we can roll back. After at least 14 days we stop writing to MySQL, and later drop it. All migration logic lives in `UserRepository`, because a lint rule (`no-raw-users-sql`) forbids SQL on `users` anywhere else.

The design has one guarantee at its heart. A write commits on the SoT together with a durable "to copy" record. So a Postgres failure never fails the request, and nothing the copy missed can be forgotten.

## Terms

- **SoT (source of truth):** the database whose copy of a row wins. Writes commit there first.
- **Version rule:** a copy may only insert a missing row, or replace a row whose `version` is lower than the incoming one. This makes every copy safe to repeat or run out of order.
- **Outbox:** a table `users_sync_outbox(id, user_id, attempts, next_attempt_at)` on each store. It is a durable list of user ids still to be copied to the other store. We use it instead of the job queue, because Redis can be down, `enqueue` can raise, and failed jobs land in `jobs:dead` after about 15 minutes with nothing processing them. That cannot carry an "automatically fixed" promise.
- **Sync worker (`users-sync-worker`):** a separate process that reads outbox rows and copies those users to the other store.
- **Tombstone:** a row `users_tombstone(id, deleted_at)` recording that a user was erased. It holds no personal data. It stops a stale copy from bringing an erased user back.
- **Write fence:** a one-row table `write_fence(writable)` on each store. It is how we pause writes safely.
- **Write mode flag `users_write_mode`:** says where instances should write. Values: `mysql_only`, `dual_mysql_primary`, `dual_pg_primary`, `pg_only`. Instances cache flags and refresh every 30 s, so for up to 30 s they can disagree. Each instance exports its value as the metric `app_flag_value{flag=...}`.
- **Read flag `users_read_pg_percent`:** a percentage flag (0-100). `flags.enabled_for(name, key)` gives the same answer for the same key.
- **Backfill:** a one-time job that copies all existing MySQL rows to Postgres.
- **Comparison:** a job that checks the two tables row by row and reports mismatches.

## How the system runs

**Writes.** Every write transaction on the SoT first takes a shared lock on that store's fence row (`SELECT writable ... FOR SHARE`; `LOCK IN SHARE MODE` on MySQL). If `writable` is false, the repository raises `WritesPaused`, and the HTTP layer returns a retryable 503, which our clients already retry. Next, the transaction makes the user change and re-selects the full row. It also inserts an outbox row in the same transaction. After commit, the instance tries the copy to the other store inline, with a 250 ms timeout inside try/except. On success it deletes its outbox row. On any failure it only logs, and the request still succeeds. A circuit breaker skips the inline attempt for 5 s after repeated failures, so a slow store never slows requests.

**Repair.** The sync worker polls the SoT outbox every second and claims rows with `FOR UPDATE SKIP LOCKED`, so running several workers is safe. For each row it reads the current user from the SoT primary (never the replica) and applies it to the other store. If the user is gone, it deletes the row there and writes a tombstone. Then it deletes only the outbox ids it claimed. Failed rows retry forever, with backoff capped at 60 s. There is no dead-letter list. We alert when the oldest outbox row is older than 5 minutes.

**The copy statement.** Every copy into Postgres, whether inline, backfill or repair, is one statement: `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`, and only if no tombstone exists for the id. `updated_at` is copied as is, never regenerated. The copy into MySQL during rollback follows the same rules.

**Deletes.** The erasure job deletes the user and inserts the tombstone in one transaction on the SoT. The copy applies the same pair on the other store. Because every copy checks for a tombstone, a stale copy held by a backfill or repair cannot resurrect a deleted user. Tombstones are kept until the MySQL table is dropped.

**Why the fence.** Closing the fence (`UPDATE write_fence SET writable = false`) waits for in-flight write transactions and blocks every later one. So correctness never depends on the 30 s flag refresh. An instance with a stale flag hits the closed fence and gets a 503. It can never write to the old SoT.

**Reads.** `get` reads from Postgres for the share of users set by `users_read_pg_percent`. If the Postgres read errors, takes over 250 ms, or finds nothing (before the switch only), it falls back to the MySQL replica. So reads never fail.

**New ids.** While MySQL is the SoT, MySQL assigns ids, and Postgres rows are inserted with that same id. After the switch, Postgres assigns ids from a sequence set to MySQL's `AUTO_INCREMENT` value (not `max(id)+1`). So an id freed by a delete at the top of the range is never reused, which protects tombstones. On rollback, InnoDB raises its counter when a larger explicit id is inserted. The rollback procedure checks this.

**Where code lives.** The backfill, comparison and worker call new repository methods (`copy_batch`, `compare_range`, `apply_outbox`) in `user_repository.py`, or in a sibling module added to the lint allowlist.

## Rollout checklist

Do the steps in order. Tick a step only when its "done when" condition holds. Rehearse the whole plan first on a staging copy.

- [ ] **1. Create the schema.**
  - **Starts when:** a manual migration run.
  - **Changes:** In Postgres: `users` (same columns, unique `email`, `id BIGINT` with a sequence but no default yet, `updated_at timestamptz(3)` in UTC), `users_tombstone`, `users_sync_outbox`, `write_fence` (`writable = true`), and `migration_progress(job, last_id, status, lease_owner, lease_expires_at, run_id)`. In MySQL: `users_tombstone`, `users_sync_outbox`, `write_fence` (`writable = 1`).
  - **State:** the tables.
  - **If it fails:** everything is additive and unused. Drop the new tables and retry.

- [ ] **2. Deploy repository v1 with `users_write_mode=mysql_only` and `users_read_pg_percent=0`.**
  - **Starts when:** a normal deploy, after step 1.
  - **Changes:** the repository supports all four modes, the fence check, the outbox, and the read fallback. In `mysql_only` mode, behaviour is unchanged apart from the fence check.
  - **State:** flags in `app.flags`.
  - **Done when:** the old version is gone from every instance, and all instances export `app_flag_value{flag="users_write_mode"}`.
  - **If it fails:** roll back the deploy. The new tables are harmless.

- [ ] **3. Deploy `users-sync-worker` and alerts.**
  - **Starts when:** a deploy, after step 2.
  - **Changes:** the worker, plus alerts on oldest outbox row over 5 minutes, outbox depth, Postgres apply error rate, and `WritesPaused` count.
  - **State:** the outbox (empty so far).
  - **If it fails:** stop the worker. The outbox is durable, so nothing is lost.

- [ ] **4. Turn on dual writes: set `users_write_mode=dual_mysql_primary`.**
  - **Starts when:** steps 2 and 3 are done and Postgres is healthy.
  - **Changes:** writes behave as described in "How the system runs": MySQL commits first, Postgres is copied after, and a Postgres failure never fails the request.
  - **State:** MySQL holds the data, tombstones and outbox. Postgres holds copies.
  - **If it fails:** set the flag back to `mysql_only`. Postgres is now stale. Reset the backfill cursor to 0 and redo steps 6 to 8. This is cheap because of the version rule.

- [ ] **5. Gate: every instance is dual-writing.**
  - **Starts when:** step 4 is applied.
  - **Condition (all must hold for at least 2 minutes, which covers one flag refresh plus requests started under the old value):**
    - `app_flag_value{flag="users_write_mode"}` reads `dual_mysql_primary` on every instance, and the number of reporting series equals the instance count (a missing instance counts as not ready).
    - No instance runs the old code.
    - The outbox is draining.
  - **State:** Prometheus metrics. The operator records the pass time in `migration_progress` (job `gate`).
  - **If it fails:** wait. Backfill must not start. New instances read the flag on boot, so autoscaling does not break the gate.

- [ ] **6. Run the backfill.**
  - **Starts when:** the step 5 gate has passed. An operator starts the `users-backfill` job by hand.
  - **Changes:** loop:
    1. If `mysql_replica_lag_seconds` is above 5 or unavailable, sleep 10 s and recheck. (Reporting jobs share the replica.)
    2. Read `SELECT * FROM users WHERE id > :last_id ORDER BY id LIMIT 2000` from the replica.
    3. In one Postgres transaction, apply the batch with the copy statement and set `last_id` to the batch's highest id.
    4. Sleep a short throttle interval and repeat. There are about 19,000 batches.
  - **State:** the `backfill` row in `migration_progress`. Updating the cursor in the same transaction as the batch means a crash continues exactly after the last completed batch. A lease (`lease_owner`, `lease_expires_at`) keeps one runner active.
  - **If it fails:** after a crash the lease expires and the next run continues from `last_id`. A Postgres error retries the same batch with backoff, and the cursor does not move. A unique-`email` conflict makes the batch retry row by row. The conflicting row is logged and left for step 8, because another row's pending update usually resolves it. Stale replica rows cannot overwrite newer data (version rule) or revive deleted users (tombstone).

- [ ] **7. Finish the backfill.**
  - **Starts when:** the cursor passes the MySQL `max(id)` and the outbox backlog is empty.
  - **Changes:** one more pass from `last_id` up to the current max id catches rows created during the run. Then the backfill sets its status to `done`.
  - **State:** `migration_progress`.
  - **If it fails:** resume the backfill.

- [ ] **8. Run the full comparison until it is clean.**
  - **Starts when:** step 7 is done. An operator starts the `users-compare` job.
  - **Changes:** it walks id ranges of 100,000 and compares `(id, version, hash of email, name, plan, updated_at)` between the MySQL replica and the Postgres primary, honouring the 5 s lag rule. It finds missing, extra and differing ids, and ids present as both a user and a tombstone. After about 10 s it re-checks each mismatch against the MySQL primary, skipping ids with a pending outbox row. Ids still mismatched are confirmed, and each is inserted into the outbox, so repair is automatic.
  - **State:** `migration_progress` (job `compare`, `run_id`, range cursor, `confirmed_mismatches`).
  - **Pass condition:** a complete run that started after step 7 and has `confirmed_mismatches = 0`. If a run finds mismatches, wait for the outbox to drain and run again.
  - **If it fails:** a crash resumes at the range cursor. Mismatches that keep coming back mean a bug. Stop and investigate, and do not go to step 9.

- [ ] **9. Ramp reads to Postgres.**
  - **Starts when:** step 8 has passed.
  - **Changes:** set `users_read_pg_percent` to 1, 10, 50, then 100, holding at least 30 minutes at each stage. Watch Postgres read errors, fallback rate and latency.
  - **State:** the flag.
  - **If it fails:** lower the percentage (effective within 30 s). If reads were wrong, the nightly comparison will show it.

- [ ] **10. Soak: 100% reads on Postgres for at least 3 days.**
  - **Starts when:** all instances report `users_read_pg_percent = 100`.
  - **Changes:** nothing. The comparison reruns nightly and the outbox alert stays on.
  - **State:** `migration_progress` job `soak` holds the start time.
  - **Pass condition:** 72 hours continuous at 100% with every nightly run clean. Our choice: any drop below 100%, or any confirmed mismatch, restarts the 72 hours.
  - **If it fails:** go back to step 9 or 8.

- [ ] **11. Switch the SoT to Postgres (writes paused 90 s at most).**
  - **Starts when:** step 10 has passed, the outbox is nearly empty, and a named operator is ready with the runbook scripted and rehearsed in staging.
  - **Procedure** (T0 is when the MySQL fence closes):
    1. **T0:** close the MySQL fence. In-flight writes finish, and new writes get 503s. Reads are unaffected.
    2. Wait for the MySQL outbox to reach zero (normally seconds). Since every commit wrote its outbox row atomically, an empty outbox means Postgres holds everything.
    3. Read `AUTO_INCREMENT` from `information_schema.tables` with `information_schema_stats_expiry=0` for the session. Call `setval` on the Postgres id sequence with that value, and attach it as the column default.
    4. Set `users_write_mode=dual_pg_primary` and open the Postgres fence, together. Writes now go to Postgres first and are copied to MySQL under the same rules, using the Postgres outbox.
    5. **Abort deadline T0+40 s:** if steps 2 and 3 are not finished, reopen the MySQL fence and leave the flag alone. The pause ends at about 40 s and nothing has changed.
  - **Timing:** the flag takes up to 30 s to reach every instance. An instance with the old value writes to the closed MySQL fence and gets a retryable 503. Worst case is about 40 s + 30 s = 70 s, under the 90 s limit.
  - **State:** `write_fence` in both stores, the flag, the sequence.
  - **If it fails:** use the abort above. After the flip, use the rollback in step 12.

- [ ] **12. Run reverse dual writes for at least 14 days, rollback ready.**
  - **Starts when:** step 11 has completed. The 14 days count from that moment.
  - **Changes:** MySQL is now the secondary. The worker and nightly comparison keep running. The Postgres outbox is the reverse repair queue, with an alert if it is over 30 s old.
  - **Rollback to MySQL (any time before step 13), mirroring step 11:**
    1. Close the Postgres fence.
    2. Drain the Postgres outbox to zero.
    3. Check that MySQL `AUTO_INCREMENT` is above the maximum Postgres id. If not, raise it.
    4. Set `users_write_mode=dual_mysql_primary` and open the MySQL fence.
    5. Abort deadline T0+40 s, with the same timing as step 11.
    - Postgres keeps receiving copies afterwards, so it stays current.
  - **Known limit:** if Postgres is unreachable, writes committed there but not yet copied are stuck in Postgres. Rollback must wait for Postgres to return. The 30 s alert keeps that exposure small.
  - **State:** the Postgres outbox, the fences, the flag.
  - **If it fails:** if the drain does not finish by T0+40 s, abort as in step 11 and try later. Writes during the attempt are still safe on Postgres.

- [ ] **13. Switch to Postgres-only writes.**
  - **Starts when:** at least 14 days have passed since step 11, the last 3 comparison runs are clean, the Postgres outbox is empty, and nobody wants a rollback.
  - **Changes:** set `users_write_mode=pg_only`. Instances stop copying to MySQL and stop writing outbox rows. The SoT does not change, so no write pause is needed. The 30 s flag disagreement is harmless: stray late copies only reach the MySQL table that is about to be retired.
  - **State:** the flag. After this, rollback to MySQL needs a new backfill from Postgres.
  - **If it fails:** set the flag back to `dual_pg_primary` and run the comparison before trusting MySQL again.

- [ ] **14. Retire MySQL.**
  - **Starts when:** step 13 has been stable for 7 days.
  - **Changes:** revoke the application's write grant on MySQL `users`, and take and keep a final snapshot. Then drop the MySQL `users` table and its outbox, tombstone and fence tables. In a later deploy, remove the dual-write, fence, outbox and fallback code and the migration flags, and drop the Postgres outbox, `write_fence` and tombstone tables.
  - **State:** the snapshot.
  - **If it fails:** a failed revoke or snapshot just stops this step. Never drop before the snapshot exists.

## What happens when things fail

| Failure | Result |
|---|---|
| Postgres copy fails or times out during a write | The request succeeds. The outbox row stays and the worker retries forever. Alert if older than 5 minutes. |
| Crash between commit and inline copy | The outbox row was committed with the change, so the worker copies it. |
| Redis down | No effect. Nothing in this plan uses the job queue. |
| Stale copy of an erased user | The tombstone check blocks it. |
| Stale or older row copied over a newer one | The version rule blocks it. |
| Postgres read fails, is slow, or misses | Falls back to the MySQL replica. |
| Instance has a stale write flag during a switch | It hits the closed fence and returns a retryable 503. No split brain. |
| Switch or rollback not finished by T0+40 s | Abort: reopen the old fence, leave the flag. |
| Backfill crash or replica lag over 5 s | Resumes from the last completed batch, or waits. |

## Open questions

- The throttle interval between backfill batches is not set. Pick it in staging.
- Rollback cannot finish while Postgres is down (see step 12). We accept this, since the brief only requires that no write is lost.
