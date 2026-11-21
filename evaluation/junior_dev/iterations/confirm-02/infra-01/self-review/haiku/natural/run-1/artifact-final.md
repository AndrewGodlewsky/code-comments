# Blue-green deploy procedure for `catalog-web`

Scope: from the merge to `main` until the deploy is finished. This includes keeping the old colour running for 30 minutes after the switch, and shutting it down afterwards.

## How to read this

`catalog-web` runs as two identical halves, called **colours**. One half is **live** and serves all user traffic. The other is **idle** and receives no user traffic.

A deploy works like this:

1. Database migrations run once. They only add things, so the live release keeps working on the migrated database.
2. The new release starts on the idle half. It is checked directly, with no user traffic.
3. All user traffic moves to the new half in one step.
4. The new half is watched for 15 minutes.
5. The old half keeps running, unchanged, for 30 minutes after the switch, so a rollback can send traffic back to it at once. After that, it is shut down.

Deploys run one at a time. Any other merges wait in a queue.

## Terms

- **Colour**: one full copy of the `catalog-web` service, either **blue** or **green**. Each colour has 4 **instances**. One colour is **live** and the other is **idle**. A colour's name does not say which release it runs. The live colour may run the old release or the new one.
- **Instance**: one running copy of the service on one machine. Each instance has a private address that only the pipeline can reach.
- **Public listener**: the load balancer rule that receives user traffic. Its **default action** names the one **target group** that traffic is sent to.
- **Target group**: the list of one colour's instances that the listener can send traffic to. Each colour has its own target group.
- **Idle target group**: the target group of the idle colour.
- **`/healthz`**: a health endpoint on each instance. It reports whether the instance is ready.
- **Smoke test suite**: a short set of checks that confirms the new release works.
- **5xx response**: an HTTP response with a status code from 500 to 599, which means the server failed.
- **Migration**: a script that changes the database schema. It is **additive** if it only adds things (new tables, nullable columns, indexes). Anything else is not additive. That includes dropping, renaming, changing a type, and adding `NOT NULL` to an existing column.
- **Deploy runner**: the CI job that is running a deploy.
- **Heartbeat**: a timestamp that the deploy runner writes to the state item every minute, to show it is still running.
- **Retention**: the period after the switch when the old colour keeps running with no traffic. During retention, a rollback can send traffic back to it.
- **Deploy lock**: a claim on the deploy state that stops two deploys from running at once. It is taken with a **conditional write**, which is a database write that succeeds only if its condition holds. Here the condition is that no other deploy holds the lock.
- **Queue**: merges that arrive while a deploy, a rollback or a retention window is active. They wait in order and are not cancelled.
- **T0**: the time the new instances are asked to start.
- **Ts**: the time the public listener is switched to the new colour.

## Decisions made here

- **Deploy state** is kept in a DynamoDB table, `catalog-web-deploy`. One item (`environment=catalog-web`) holds the current state of the environment. One item per deploy holds that deploy's history. The deploy lock is a conditional write on the state item.
- **Two sources of truth.** The listener shows where traffic actually goes (**traffic truth**). The state item shows what the pipeline intends, including retention, shutdown time and lock owner (**intent truth**). Before each step that changes traffic or stops instances (steps 10, R, R2 and 13), the pipeline checks that the two agree. If they disagree at any check, the pipeline stops, releases nothing and sends an alert.
- **Schema history** is kept in the migration tool's own table in PostgreSQL. Each migration is recorded there as it is applied, so a re-run skips migrations that have already applied.
- **Health checks and smoke tests** go straight to each idle instance's private address, not through the listener. The idle target group is never on the listener before the switch, so the new release gets no user traffic until then.
- **One deploy at a time.** Merges that arrive during a deploy, a rollback or a retention window are queued. A queued deploy does not start until the non-live colour has been shut down. Deploying onto the idle colour during retention would destroy the rollback path.
- **Smoke tests** must be read-only or use a test tenant. The database is shared, and the new release is not yet live.
- **5xx rule.** The 5xx rate is the number of 5xx responses from the new target group, divided by the number of requests to it. It is measured over a trailing 5-minute window that counts only traffic after Ts. The window is evaluated every minute. Each evaluation uses data up to 2 minutes before now, to allow for late metrics. For example, at 12:10 the window covers 12:03 to 12:08. A window never starts before Ts. So an evaluation at Ts + 3 min covers Ts to Ts + 1 min. A rate strictly above 1% triggers a rollback. A window with zero requests raises an alert, not a rollback.
- **Metric delay.** Assume metrics can be up to 2 minutes late.
- **Extra rollback triggers.** Zero healthy targets in the new target group for 2 consecutive checks. No metric data for 5 minutes during the watch (a fail-safe).
- **No retries of the smoke suite.** One failure aborts the deploy.
- **Shutdown safety rule.** The shutdown job stops only the colour that the listener does not forward to. It never stops the live colour.

## A. Build and start

- [ ] **1. Build and tag the release.**
  - Starts: a merge to `main`.
  - Changes: builds the image, tags it with the commit SHA, pushes it to the registry and runs the unit tests.
  - If it fails: the pipeline stops. Nothing has changed.

- [ ] **2. Take the deploy lock and read state.**
  - Starts: step 1 passes.
  - Changes: a conditional write sets `lock_owner` on the state item to this deploy's ID, and `status` to `in_progress`. The write succeeds only if no other deploy holds the lock. Then the run reads the listener and the state item.
  - If the lock is held, or a retention window is active: this run waits in the queue and checks again every minute. Nothing has changed.
  - If the write fails for any other reason (such as a network error): retry it.
  - If the listener and the state item disagree: stop, release the lock and alert. No traffic has changed.

- [ ] **3. Pre-flight checks.**
  - Starts: step 2 holds the lock.
  - Checks:
    - (a) Every migration file is additive. Reject `DROP`, `RENAME`, column type changes, and `NOT NULL` added to an existing column.
    - (b) The public listener forwards to exactly one target group, the live one. No rule or weight refers to the idle target group.
    - (c) The idle colour has no running instances. A queued deploy starts only after step 13 has stopped any retained colour, so this should always hold. If it does not, stop and alert.
    - (d) The release image exists in the registry.
  - Changes: none.
  - If it fails: stop, release the lock and alert.

## B. Schema

- [ ] **4. Apply migrations once.**
  - Starts: step 3 passes.
  - Changes: runs the migration tool once against the shared database. `lock_timeout` and `statement_timeout` are set, so a migration cannot block live traffic for long. Each migration is recorded in the migration table as it applies.
  - If a migration fails: its transaction rolls back and the run stops. No new release is started. The live colour keeps serving. The deploy is marked `migration_failed`, the lock is released and an alert is sent.
  - Migrations that already applied stay in place. They are additive, so they are harmless.
  - A failed concurrent index build leaves an invalid index. Fix it with a later migration, not by redeploying.
  - The app never runs migrations on startup.

## C. Bring up the idle colour

- [ ] **5. Clear and start the idle colour.**
  - Starts: step 4 succeeds. This sets T0.
  - Changes: stops and deregisters any leftover instances on the idle colour, and waits until they are gone. Starts 4 instances of the new release and registers them in the idle target group.
  - If the 4 instances are not all started and ready by T0 + 10 min: go to procedure A.

- [ ] **6. Health gate.**
  - Starts: step 5.
  - Changes: polls `/healthz` on each instance's private address every 10 seconds. Each instance keeps its own count of passes in a row. A failed check resets that instance's count to zero. The gate passes when all 4 instances have 3 passes in a row.
  - If not all 4 pass by T0 + 10 min: go to procedure A.

- [ ] **7. Smoke test suite.**
  - Starts: all 4 instances have passed step 6.
  - Changes: runs the suite once against the idle instances' private addresses. It uses test data only, or a read-only suite.
  - If it fails: go to procedure A. There is no automatic retry.

- [ ] **8. Gate check.**
  - Starts: steps 6 and 7 have both passed.
  - Checks: both finished by T0 + 10 min.
  - If yes: go to step 9. If no: go to procedure A.

## Procedure A: abort before the switch

- Starts: any failure in steps 5 to 9, or in step 10 when the listener still forwards to the old target group.
- Changes: the listener is not touched, and the run checks that it is unchanged. Logs from the failed instances are collected into the CI run logs. The idle instances are deregistered and stopped. Migrations stay applied. The state item is set to `aborted`, with the reason and the time.
- Then: release the lock and send an alert. The idle colour is now empty, so the next deploy starts clean.

## D. Cutover

- [ ] **9. Record the pre-switch snapshot.**
  - Starts: step 8 passes.
  - Changes: writes to the state item: `previous_live_tg` (the current live target group), `new_tg` (the idle target group, now holding the new release), the listener ARN, and `status = switch_pending`.
  - If the write still fails after retries: go to procedure A.

- [ ] **10. Switch the listener.**
  - Starts: step 9.
  - Changes: one API call sets the public listener's default action to forward to the new target group. All traffic moves at once. The run then reads the listener back to confirm the switch. The state item records `switched_at = Ts` and `shutdown_due_at = Ts + 30 min`. The old colour stays registered and running, untouched.
  - If the call fails: retry up to 3 times with backoff. Then read the listener. If it forwards to the new target group, the switch happened, so continue to step 11. If it forwards to the old target group, go to procedure A.
  - If the result of the call is unknown (for example, a timeout): read the listener and decide as above.

## E. Watch (Ts to Ts + 15 min)

- [ ] **11. Watch the 5xx rate.**
  - Starts: Ts.
  - Changes: every minute, evaluates the 5xx rule and the healthy-target check, and writes the readings to the state item. The deploy runner also writes its heartbeat to the state item every minute.
  - Triggers procedure R if any of these happen:
    - the 5xx rate is above 1% in any window;
    - the new target group has zero healthy targets for 2 consecutive checks;
    - there is no metric data for 5 minutes.
  - A window with zero requests raises an alert, but does not trigger a rollback.
  - If the deploy runner's heartbeat stops for 3 minutes, a scheduled watcher job (running every minute) takes over. It reads the state item and continues the watch with the same rules.
  - Runs until Ts + 15 min. The last evaluation is at Ts + 15 min.

- [ ] **12. Promote.**
  - Starts: Ts + 15 min, with no trigger.
  - Changes: sets `status = live_new` and `retained` to the old colour. The new colour is now the live one. The old colour stays running and idle until `shutdown_due_at`. The deploy lock is released, but queued deploys still wait for step 14. A success notice is sent.

## F. Rollback

- [ ] **R. Automatic rollback.**
  - Starts: a trigger from step 11.
  - Precondition: the old colour is still running and registered. It is, because it is untouched until shutdown, and shutdown is 30 minutes after the switch, which is after the watch ends.
  - Changes: sets the listener's default action back to the old target group, then reads it back to confirm. The state item records `status = rolled_back`, the reason and the metric readings. The failed colour stays running and idle, for diagnosis, with its own shutdown time of now + 30 min. The old colour is now the live one, and it is not on any shutdown timer. Migrations are not reversed.
  - If the repoint fails: retry 3 times. Until one succeeds, traffic keeps going to the new colour. If all retries fail, page an engineer and set `status = rollback_failed`. The engineer then uses R2.

- [ ] **R2. Manual rollback (started by an engineer as a pipeline job).**
  - If the previous live colour is still running: repoint the listener to it, as in R, and write the same state updates.
  - If it has been shut down: run steps 1 to 12 for the previous release tag. Step 1 reuses the image already in the registry for that tag, so nothing is rebuilt. Migrations do nothing, because they are additive and already applied.

## G. Retention and shutdown

- [ ] **13. Shut down the non-live colour.**
  - Starts: the scheduled job runs at `shutdown_due_at` (Ts + 30 min). After a rollback, the same job runs at the failed colour's own shutdown time.
  - Preconditions: no deploy or rollback is running, and the colour to be stopped is not the one the listener forwards to. For a normal deploy, this means `status = live_new` and the listener forwards to the new target group. After a rollback, the failed colour is the one stopped. If any precondition fails, shut nothing down and send an alert instead.
  - Changes: deregisters the instances from their target group and waits for connection draining (up to 5 minutes). Then stops the instances and sets `retained = none`.
  - If stopping fails: leave the instances running. They are idle and safe. Retry and send an alert. The queue cannot start until the colour is stopped.

- [ ] **14. Release the queue.**
  - Starts: step 13 completes, so the non-live colour is stopped. After a rollback, this is when the failed colour is stopped, 30 minutes after the rollback.
  - Changes: the oldest queued deploy goes to step 2. Queued merges are not cancelled.
  - End of deploy: after a normal deploy, `status = complete`, with the new release live and the old colour stopped. After a rollback, the previous release is live and the failed colour is stopped, so the record keeps `status = rolled_back`.

## Where deploy state is kept

| What | Where | When it is written |
|---|---|---|
| Current state: lock owner, status, live and idle colour, current and previous release, `switched_at`, `shutdown_due_at`, `retained`, last watch reading, heartbeat | DynamoDB item `environment=catalog-web` in `catalog-web-deploy` | Before each irreversible action (steps 2, 9, 10, 11, R, 13) |
| Deploy history: one item per deploy | DynamoDB items keyed by deploy ID | At each step |
| Live traffic | The public listener's default action | Step 10, R and R2 |
| Applied migrations | The migration table in PostgreSQL | Step 4 |
| Logs and reasons | CI run logs, plus the history items | Every step |