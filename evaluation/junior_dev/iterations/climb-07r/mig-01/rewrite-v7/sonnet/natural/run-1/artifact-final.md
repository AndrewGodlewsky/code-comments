# Plan: move `users` from MySQL 8 to Postgres 16 with no downtime

Today every read and write of `users` goes through `UserRepository` to MySQL (writes to the primary, reads from the replica). We add the migration logic inside that class. First every write is copied to Postgres, then old rows are backfilled, then reads move, then the source of truth moves, and MySQL is retired last. Each stage is gated by a measurable condition, and every copy is safe to repeat, so a failure at any point is repaired automatically and rollback loses no write.

## Terms

- **Source / follower.** The source is the store that takes writes first. The follower gets a copy after commit. MySQL is the source at first. After the switch, Postgres is the source and the copy runs in reverse.
- **Outbox (`users_sync_outbox`).** A table of `(seq, user_id, kind)` rows meaning "this user still needs copying". It lives in the source's database. A row exists only until the copy is done.
- **Relay (`sync-relay`).** A worker that drains the outbox forever.
- **Copy function.** The one function that writes into the follower. It applies the version rule and the erasure check (below).
- **Tombstone (`user_tombstones`).** In Postgres, a row holding only the id of an erased user. Ids are never reused. Tombstones are kept indefinitely (about 2,000 new rows per day).
- **Fence (`users_fence`).** A one-row table in each database. Its mode is `mysql`, `pg` or `closed`. A write transaction first reads its own database's fence with `FOR SHARE`. If the fence is not open for that database, the request gets a retryable 503.
- **Reconciler.** A worker that compares both tables and queues repairs for differences.
- **Flags** (`app.flags`; each instance caches them and refreshes every 30 s, so instances can disagree for up to 30 s; `app_flag_value{flag=...}` shows what each instance uses):
  - `users.dual_write` (bool, default false).
  - `users.source` (`mysql` | `pg`, default `mysql`). It is only a routing hint. The fence decides.
  - `users.read_pg_pct` (percentage, default 0), bucketed per user with `flags.enabled_for("users.read_pg_pct", user_id)`.
- **Every instance** means every web instance and every worker process. The erasure job runs in workers and calls `UserRepository.delete`, so workers need the new code and flags too.
- **Backfill.** A one-off job that copies existing MySQL rows to Postgres.

## How the system runs

**Write path.**
1. The request reads the fence of the source database (the fence guards against a stale flag cache, so a stale flag can never lose a write).
2. In one transaction on the source it writes the user row and an outbox row. The two commit or fail together.
3. After commit, it tries to copy inline to the follower, with a 200 ms timeout and a circuit breaker. On success it deletes the outbox row. On any failure it logs, increments a metric and still returns success.
4. The relay repairs whatever inline copying missed. It claims outbox rows with `FOR UPDATE SKIP LOCKED`, re-reads the current row from the source primary (never a replica), copies it, then deletes the outbox row. If the row is gone from the source, it copies a delete. It retries forever.

Repair uses this outbox and not Redis jobs, because `jobs.enqueue` raises when Redis is down, and failed jobs end in `jobs:dead` after about 15 minutes where nothing processes them. That cannot guarantee a missed row is eventually fixed.

**Copy function (version rule and erasure, enforced in one place).** Dual writes, backfill, relay repair and the reconciler all use it.
- Into Postgres: a transaction starting with `pg_advisory_xact_lock(id)`. If `user_tombstones` has the id, do nothing. Otherwise run `INSERT ... ON CONFLICT (id) DO UPDATE ... WHERE users.version < EXCLUDED.version`.
- Into MySQL: `INSERT ... ON DUPLICATE KEY UPDATE`, each column set only when `version < VALUES(version)`.
- A delete, under the same lock, inserts the tombstone and deletes the row.
- So a copy only inserts a missing row or replaces a lower version, and a stale replica read can never bring back an erased user.

**Reads.** `read_pg_pct` picks which users read from Postgres. A Postgres read that errors or misses falls back to the other store, and a metric counts each fallback, so reads never fail because of the migration. A read right after a write can lag by the copy time, usually milliseconds, or seconds if the inline copy failed and the relay must run. An `update` that read a stale version fails the version check on the source and raises `StaleWrite`, which is safe and which the caller retries.

**Postgres column types.** `updated_at` is `timestamp(3)` without time zone, to match MySQL `DATETIME(3)`. The email index starts non-unique so that out-of-order copies (a user changes an email, then another user takes it) cannot block a copy mid-migration.

**Where state lives**

| State | Lives in |
|---|---|
| Forward repair queue | `users_sync_outbox` in MySQL |
| Reverse repair queue (after the switch) | `users_sync_outbox` in Postgres |
| Write routing | `users_fence` in each database |
| Backfill progress | `migration_state(name, last_id, done)` in Postgres, updated in the same transaction as each batch |
| Erasure guard | `user_tombstones(id)` in Postgres |
| New ids | MySQL `AUTO_INCREMENT` until the switch, then the Postgres sequence `users_id_seq` |

## Rollout checklist

- [ ] **1. Create the schemas.**
  - **Starts:** a reviewed migration, run by hand on both databases.
  - **Changes:** Postgres gets `users` (`id BIGINT PRIMARY KEY`, no default yet, `email`, `name`, `plan`, `version INT`, `updated_at timestamp(3)`, a non-unique email index), `user_tombstones`, `migration_state`, `users_fence` (closed), `users_sync_outbox` and `users_id_seq`. MySQL gets `users_sync_outbox` and `users_fence` (mode `mysql`). All are empty.
  - **If it fails:** nothing reads these tables yet. Drop what was created, fix and rerun.

- [ ] **2. Deploy the new code with every flag at its default.**
  - **Starts:** a normal deploy.
  - **Changes:** `UserRepository` gains the fence check, outbox writes, the copy function, read fallback and flag handling. The `sync-relay`, `backfill` and `reconciler` workers ship too. With defaults (`dual_write=false`, `source=mysql`, `read_pg_pct=0`) behavior is unchanged except one extra fence read per write.
  - **Gate:** the deploy has finished, no old-build process runs, and the count of `app_flag_value{flag="users.dual_write"}` series equals the orchestrator's instance count (web plus worker).
  - **If it fails:** roll back the deploy. The step 1 schemas are harmless.

- [ ] **3. Rehearse in staging.**
  - **Starts:** step 2 is done.
  - **Changes:** nothing in production. Tests cover version ordering, tombstone-before-insert and insert-before-tombstone, Postgres down mid-write (the request must succeed and the relay must repair the row), and the switch and rollback scripts with a timing check.
  - **If it fails:** fix, redeploy, and do not continue.

- [ ] **4. Turn on dual writes.**
  - **Starts:** step 3 passes and a human sets `users.dual_write=true`.
  - **Changes:** each write now adds an outbox row, commits to MySQL, then tries Postgres inline. Nothing is backfilled yet.
  - **State:** the MySQL outbox. Alert if its oldest row is older than 60 s.
  - **If it fails:** if Postgres is down, requests are unaffected, the outbox grows and the relay catches up later. If dual writes add user-visible latency, the circuit breaker already skips the inline copy. Do not set the flag back to false once the backfill has started, because later missed writes would go unrecorded.

- [ ] **5. Wait until every instance is dual-writing.**
  - **Starts:** step 4.
  - **Condition, all of:** every instance reports `users.dual_write=1` and the series count equals the instance count, for at least 2 consecutive scrapes; at least 60 s have passed since the last instance changed (30 s refresh plus in-flight requests); outbox age is under 60 s; a test erasure shows the tombstone and the Postgres delete.
  - **Why:** rows written earlier by an instance that was not dual-writing are not in the outbox. The backfill picks them up because it starts only after this gate.
  - **If it fails:** a series is missing or stuck at 0. Investigate that instance and do not start the backfill.

- [ ] **6. Run the backfill.**
  - **Starts:** step 5's condition is met and a human runs `backfill`, which refuses to start otherwise.
  - **Changes:**
    - It reads `WHERE id > last_id ORDER BY id LIMIT 2000` from `mysql-core-replica`.
    - Before each batch it checks `mysql_replica_lag_seconds`. While the value is above 5 it sleeps and rechecks (reporting jobs share the replica).
    - It copies the batch with the copy function and, in the same Postgres transaction, sets `migration_state.last_id` to the batch's last id.
    - When a read returns no rows it sets `done`. At about one batch per second, the roughly 38 million rows take about 5 hours.
  - **State:** `migration_state`. After a crash it continues from `last_id`, so a batch is either fully applied with its progress recorded or not applied.
  - **If it fails:** replica or Postgres errors are retried with backoff. Two copies running at once are safe because the copy function is idempotent and `last_id` only moves forward. Stale replica rows are rejected by the version rule or the tombstone.

- [ ] **7. Run the relay and reconciler continuously.**
  - **Starts:** step 6 is done.
  - **Changes:** the reconciler scans both tables in id order in chunks, reading MySQL from the replica. A difference counts as a mismatch only if it persists after re-reading both primaries and no outbox row is pending. Each confirmed mismatch gets an outbox row, and the relay fixes it with no manual step.
  - **State:** a `mismatch_count` metric per pass.
  - **If it fails:** a crashed pass is simply rerun.

- [ ] **8. Run the full comparison, then make email unique.**
  - **Starts:** step 6 is `done`.
  - **Changes:** one full pass compares all columns of every row in both tables, including rows on one side only. Repeat until a complete pass that started after `done` ends with zero confirmed mismatches. Then run `CREATE UNIQUE INDEX CONCURRENTLY` on `users(email)` in Postgres.
  - **Gate for step 9:** a zero-mismatch pass and the unique index built.
  - **If it fails:** the relay repairs a mismatch and the pass is rerun. A mismatch that persists across passes is a bug: stop and investigate. If the index build fails on duplicate emails, treat the duplicates as mismatches, repair and retry. Once the index exists, a copy blocked by an email conflict stays in the outbox and is retried until the earlier change lands.

- [ ] **9. Ramp reads to Postgres.**
  - **Starts:** step 8's gate is met. A human sets `users.read_pg_pct` to 1, 10, 50, then 100. Each stage holds at least 1 hour with fallback and error rates flat, and the next starts only if the reconciler still shows zero mismatches.
  - **Changes:** reads for the chosen users come from Postgres. Writes are unchanged.
  - **If it fails:** lower the percentage, and reads fall back to MySQL immediately. Any confirmed mismatch holds the ramp until it is repaired.

- [ ] **10. Soak for at least 3 days at 100% reads.**
  - **Starts:** every instance reports `read_pg_pct=100`. The 3-day clock starts when the last one does, and restarts if the percentage is ever lowered.
  - **Changes:** nothing. The reconciler and outbox monitoring keep running.
  - **Gate for step 11:** 3 days elapsed, a zero-mismatch pass in the last 24 hours, and the outbox empty or under 60 s old.
  - **If it fails:** a regression sends you back to step 9 at a lower percentage and restarts the clock.

- [ ] **11. Switch the source of truth to Postgres (writes paused, at most 90 s).**
  - **Starts:** the step 10 gate is met and a human launches `switch-to-pg`. This is the first pause.
  - **The script, in order:**
    1. Set the MySQL fence to `closed`. The update waits for in-flight writes, then every write gets a retryable 503. Reads continue. The clock starts.
    2. Wait for the MySQL outbox to reach zero rows, telling the relay to run immediately. Postgres then holds every committed MySQL write.
    3. Set `users_id_seq` with `setval` to `max(MAX(id) in MySQL, AUTO_INCREMENT − 1) + 1000`. The gap leaves room for ids issued but unused. Then give `id` the default `nextval('users_id_seq')`.
    4. Open the Postgres fence (mode `pg`) and set `users.source=pg`. Writes now commit to Postgres and are copied to MySQL through the Postgres outbox, with `dual_write` still true.
  - **Timing:** steps 1 to 3 take a few seconds. An instance with a stale `source=mysql` gets 503 from the closed MySQL fence until it refreshes, at most 30 s, so each instance's pause is under about 45 s. The script aborts at 60 s if step 2 has not finished, so the 90 s budget is never reached.
  - **State:** both fences, the flag and the Postgres outbox.
  - **If it fails:** before script step 4 nothing has moved. An abort reopens the MySQL fence and leaves `source=mysql`. A failed outbox drain is retried until the deadline, then aborts. After script step 4, do not abort: finish, or run the rollback below.

- [ ] **12. Rollback (available from step 11 until step 14).**
  - **Starts:** a human decides, or an alert fires on error rate, mismatches or outbox lag.
  - **The script, in order:**
    1. Set the Postgres fence to `closed`. This is a second pause, again at most 90 s.
    2. Drain the Postgres outbox to zero, so MySQL has every write made while Postgres was the source.
    3. Raise MySQL `AUTO_INCREMENT` if it is below max id + 1 across both stores.
    4. Set the MySQL fence to `mysql`, `users.source=mysql` and `users.read_pg_pct=0`.
  - Forward dual writes then resume by themselves.
  - **If it fails:** the script aborts at 60 s and reopens the Postgres fence, so nothing is lost. Instances with a stale flag get 503 until they refresh. Every copy is safe to repeat because of the version rule. A rollback restarts the 14-day soak from the next switch.

- [ ] **13. Soak for at least 14 days with Postgres as source.**
  - **Starts:** step 11 completes. The clock starts when the flag change reaches the last instance.
  - **Changes:** nothing. Reverse copies keep MySQL current. The reconciler runs in both directions, and the source always overrides the follower under the version rule.
  - **State:** the Postgres outbox, alerting when its oldest row passes 60 s.
  - **If it fails:** run the rollback (step 12).

- [ ] **14. Switch to Postgres-only writes.**
  - **Starts:** at least 14 days after step 11 with no rollback in between, the Postgres outbox empty, and a full comparison in the last 24 hours with zero mismatches. A human sets `users.dual_write=false`.
  - **Changes:** writes stop being copied to MySQL. No pause is needed because the source does not change. Instances that have not refreshed still write outbox rows and the relay applies them, so nothing is lost in the 30 s window.
  - **Gate:** every instance reports `dual_write=0` and the Postgres outbox is empty.
  - **If it fails:** set the flag back to true and run a full reconciliation pass to bring MySQL up to date, which restores rollback. Once MySQL has fallen behind, plain rollback is gone, so use this only soon after the change.

- [ ] **15. Retire MySQL `users`.**
  - **Starts:** step 14's gate is met and no `users` queries have reached MySQL for at least 7 days.
  - **Changes:**
    1. Rename `users` to `users_retired`, so any missed reader fails loudly.
    2. After another 7 days with no errors, take a last dump only if policy allows (erased users would still be in it). Then drop `users_retired`, `users_sync_outbox` and `users_fence`.
    3. In a cleanup deploy, remove the dual-write, fence, outbox and backfill code and the three flags. Keep `user_tombstones`.
  - **If it fails:** before the drop, rename the table back. After the drop there is no way back, so confirm steps 13 and 14 were clean first.

## What happens when things fail

| Failure | Effect on users | Repair |
|---|---|---|
| Postgres write fails or times out | None | The outbox row remains and the relay retries forever |
| Redis down | None, since repair does not use Redis | None needed |
| Backfill crash or restart | None | Resumes from `last_id` in Postgres |
| Replica lag above 5 s | None | Backfill pauses |
| Stale replica row during backfill | None | Rejected by the version rule or tombstone |
| Erased user's row copied late | None | Rejected by the tombstone, and the Postgres delete applies |
| Instance with stale flag at a switch | Retryable 503 for at most about 30 s | The fence blocks the write and the instance refreshes its flag |
| Switch or rollback exceeds 60 s | Retryable 503 | The script aborts and reopens the previous fence |

## Open questions

- Whether policy allows a final MySQL dump that would still contain erased users (step 15).
- Tombstones grow without limit (about 2,000 per day). No retention rule is decided.
