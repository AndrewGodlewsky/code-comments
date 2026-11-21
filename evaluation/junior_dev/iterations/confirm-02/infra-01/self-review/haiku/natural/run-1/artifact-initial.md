# Blue-green deploy procedure for `catalog-web`

Scope: from the merge to `main` to the end of the deploy, including the 30-minute retention of the old colour and its shutdown. "Live" is the colour the public listener forwards to. "Idle" is the other colour. T0 is the time the new instances are asked to start. Ts is the time the listener is switched.

## Decisions made here

- **Deploy state** lives in a DynamoDB table, `catalog-web-deploy`. One item holds the current state for the environment. One item per deploy holds its history. Conditional writes provide the deploy lock.
- **Traffic truth** is the public listener's default action. **Intent truth** (retention, shutdown due time, lock owner) is the state item. If they disagree at any check, the pipeline stops, releases nothing, and alerts.
- **Schema history** is the migration tool's table in PostgreSQL. Each migration is recorded there as it applies, so a re-run skips applied migrations.
- **Health checks and smoke tests** go to each idle instance's private address, not through the listener. The idle target group is never added to the listener, so the new release gets no user traffic.
- **One deploy at a time.** Merges that arrive while a deploy, rollback or retention window is active are queued, not cancelled. A queued deploy does not start until the old colour is shut down. Deploying onto the idle colour during retention would destroy the rollback path.
- **Smoke tests** must be read-only or use a test tenant. The database is shared and the new release is not yet live.
- **5xx rule.** Rate = 5xx responses from the new target group / requests to the new target group, over a trailing 5-minute window that counts only traffic after Ts. The window is evaluated every minute. A rate strictly above 1% triggers rollback. A window with zero requests raises an alert, not a rollback.
- **Metric delay.** Assume up to 2 minutes. Each evaluation uses data up to now minus 2 minutes.
- **Extra rollback triggers.** Zero healthy targets in the new target group for 2 consecutive checks. No metric data for 5 minutes during the watch (fail-safe).
- **No retries of the smoke suite.** One failure aborts the deploy.
- **Shutdown safety rule.** The shutdown job stops only the colour that the listener does not forward to. It never stops the live colour.

## A. Build and start

- [ ] **1. Build and tag the release.**
  - Starts: merge to `main`.
  - Changes: builds the image, tags it with the commit SHA, pushes it to the registry, runs unit tests.
  - If it fails: the pipeline stops. Nothing has changed.

- [ ] **2. Acquire the deploy lock and read state.**
  - Starts: step 1 passes.
  - Changes: conditional write to the state item sets `lock_owner = <deploy id>` and `status = in_progress`. Reads the listener and the state item.
  - If the lock is held, or a retention window is active, this run waits in the queue and re-checks every minute.
  - If the conditional write fails, retry. If the listener and the state item disagree, stop, release the lock, and alert. No traffic has changed.

- [ ] **3. Pre-flight checks.**
  - Starts: step 2 holds the lock.
  - Checks: (a) every migration file is additive only. Reject `DROP`, `RENAME`, column type changes, and `NOT NULL` added to an existing column. (b) The public listener has exactly one forward to the live target group, and no rule or weight refers to the idle target group. (c) The idle colour has no running instances, or only instances that retention has released. (d) The release image exists.
  - Changes: none.
  - If it fails: stop, release the lock, alert.

## B. Schema

- [ ] **4. Apply migrations once.**
  - Starts: step 3 passes.
  - Changes: runs the migration tool once against the shared database, with `lock_timeout` and `statement_timeout` set so a migration cannot block live traffic for long. Each applied migration is recorded in the migration table.
  - If a migration fails: its transaction rolls back and the run stops. No new release is started. The live colour keeps serving. The deploy is marked `migration_failed`, the lock is released, and an alert is sent.
  - Migrations that already applied stay in place. They are additive, so they are harmless.
  - A failed concurrent index build leaves an invalid index. Fix it with a later migration. Do not re-run the release.
  - The app must not run migrations on startup.

## C. Bring up the idle colour

- [ ] **5. Clear and start the idle colour.**
  - Starts: step 4 succeeds. This sets T0.
  - Changes: stops and deregisters any leftover instances on the idle colour and waits until they are gone. Starts 4 instances of the new release and registers them in the idle target group.
  - If the instances are not started and ready by T0 + 10 min: go to procedure A (abort).

- [ ] **6. Health gate.**
  - Starts: step 5.
  - Changes: polls `/healthz` on each instance's private address every 10 seconds. Each instance keeps its own streak. A failed check resets that instance's streak to zero. The gate passes when all 4 instances have 3 passes in a row.
  - If not all 4 pass by T0 + 10 min: procedure A.

- [ ] **7. Smoke test suite.**
  - Starts: all 4 instances have passed step 6.
  - Changes: runs the suite once against the idle instances' private addresses. Test data only, or a read-only suite.
  - If it fails: procedure A. There is no automatic retry.

- [ ] **8. Gate check.**
  - Starts: steps 6 and 7 have both passed.
  - Checks that both finished by T0 + 10 min.
  - If yes: go to step 9. If no: procedure A.

## Procedure A: abort (before the switch)

- Starts: any failure in steps 5 to 9.
- Changes: the listener is not touched, and the run verifies that. Logs are collected from the failed instances. The idle instances are deregistered and stopped. Migrations stay applied. The state item is set to `aborted` with the reason and time.
- Then: release the lock and alert. The idle colour is empty, so the next deploy starts clean.

## D. Cutover

- [ ] **9. Record the pre-switch snapshot.**
  - Starts: step 8 passes.
  - Changes: writes `previous_live_tg`, `new_tg`, the listener ARN and `status = switch_pending` to the state item.
  - If the write fails after retries: procedure A.

- [ ] **10. Switch the listener.**
  - Starts: step 9.
  - Changes: one API call sets the public listener's default action to forward to the new target group. All traffic moves at once. Then the listener is read back and the switch is confirmed. The state item records `switched_at = Ts` and `shutdown_due_at = Ts + 30 min`.
  - The old colour stays registered and running, untouched.
  - If the call fails, retry up to 3 times with backoff. If the listener still forwards to the old target group, procedure A. If the call's result is unknown, the listener read decides.

## E. Watch (15 minutes after Ts)

- [ ] **11. Watch the 5xx rate.**
  - Starts: Ts.
  - Changes: every minute, evaluates the 5xx rule above and the healthy-target check. Writes readings to the state item.
  - Triggers rollback (procedure R) if any of these happen: the rate is above 1% in any window; zero healthy targets in the new group for 2 consecutive checks; no metric data for 5 minutes.
  - If the deploy runner stops heartbeating for 3 minutes, a scheduled watcher job (every minute) reads the state item and continues the watch with the same rules.
  - Runs until Ts + 15 min.

- [ ] **12. Promote.**
  - Starts: Ts + 15 min with no trigger.
  - Changes: sets `status = live_new` and the new colour is now live. The old colour stays running and idle until `shutdown_due_at`. The deploy lock is released, but the queue still waits for step 14. Sends a success notice.

## F. Rollback

- [ ] **R. Automatic rollback.**
  - Starts: a trigger from step 11.
  - Precondition: the old colour is still running and registered. It is, because it is untouched until shutdown.
  - Changes: sets the listener's default action back to the old target group and reads it back. The state item records `status = rolled_back`, the reason and the metric readings. The failed colour stays running, idle, for diagnosis, with its own shutdown time of now + 30 min. The old colour is now live and is not on any shutdown timer. Migrations are not reversed.
  - If the repoint fails: retry 3 times, then page an engineer and set `status = rollback_failed`. The engineer uses R2.

- [ ] **R2. Manual rollback job (started by an engineer as a pipeline job).**
  - If the old colour is still running: repoint the listener as in R.
  - If the old colour has been shut down: run steps 1 to 12 for the previous release tag. Migrations are a no-op, because they are additive and already applied.

## G. Retention and shutdown

- [ ] **13. Shut down the non-live colour.**
  - Starts: `shutdown_due_at` (Ts + 30 min), run by a scheduled job.
  - Preconditions: `status = live_new`, no deploy or rollback is running, and the listener forwards to the new target group. If any precondition fails, do not shut down. Alert.
  - Changes: deregisters the instances from the old target group and waits for connection draining (up to 5 minutes). Stops the instances. Sets `retained = none`.
  - If stopping fails: leave the instances running. They are idle and safe. Retry, and alert. The queue cannot start until the colour is stopped.
  - After a rollback, the same job applies to the failed colour, and only if it is not live.

- [ ] **14. Release the queue.**
  - Starts: step 13 completes, or R completes and the idle colour is free.
  - Changes: the oldest queued deploy goes to step 2. Queued merges are not cancelled.
  - End of deploy: `status = complete`, with the new release live and the old colour stopped.

## Where deploy state is kept

| What | Where | Written when |
|---|---|---|
| Current state: lock owner, status, live and idle colour, current and previous release, `switched_at`, `shutdown_due_at`, `retained`, last watch reading | DynamoDB item `environment=catalog-web` in `catalog-web-deploy` | Before each irreversible action (steps 2, 9, 10, 11, R, 13) |
| Deploy history: one item per deploy | DynamoDB items keyed by deploy id | At each step |
| Live traffic | Public listener default action | Step 10, R, R2 |
| Applied migrations | Migration table in PostgreSQL | Step 4 |
| Logs and reasons | CI run logs, plus the history items | Every step |
