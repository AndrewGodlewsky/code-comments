# Blue-green deploy procedure for `catalog-web`

Today `catalog-web` is restarted in place. This procedure replaces that: it starts a full set of new instances on the idle colour, checks them, moves all user traffic with one listener change, and then watches the 5xx rate. The old colour keeps running for 30 minutes after the switch, so a rollback is one listener change.

## Terms

- **Colour:** one of two identical copies of the service, `blue` or `green`. Each has 4 instances and one target group. The live colour serves users. The idle colour is the other one.
- **Instance:** one running copy of `catalog-web`.
- **Target group:** the load balancer's list of one colour's instances.
- **Public listener:** the load balancer entry that users reach. Its forward action names exactly one target group. Repointing it means changing that name.
- **Desired count:** how many instances the platform keeps running for one colour. 4 starts them. 0 stops them.
- **Health check:** a `GET /healthz` call to one instance. A pass means the instance is up.
- **Internal test path:** a private address for each instance, reachable from the pipeline's network. The public listener is never on this path.
- **Smoke suite:** a fixed set of end-to-end requests. A new release gets no user traffic until it passes.
- **Response counts:** the load balancer's counts of all responses and of 5xx responses, for the new target group while the listener forwards to it.
- **5xx rate:** 5xx responses divided by all responses in the same window.
- **Hold:** the 30 minutes after a switch. During the hold the non-live colour keeps running and is not touched.
- **T0:** the launch time of the first new instance. The health and smoke deadline is T0 + 10 minutes.
- **Deploy ID:** the ID of one pipeline run that tries to take the lock. Each run gets its own.
- **SHA:** the commit ID of a merge. `release_sha` is the SHA being deployed.
- **Digest:** the fixed content ID of a built image.
- **Migration:** a script that changes the PostgreSQL schema. The migration tool records which migrations exist and have run in its own table.
- **Advisory lock:** a named PostgreSQL lock. The migration task holds it, so two migrators cannot run at once.
- **INVALID index:** a PostgreSQL index left unusable because its concurrent build failed part way.
- **Compare-and-set:** a write that succeeds only if the `version` field still holds the value the writer read. Shortened to CAS below.
- **Watch job:** a scheduled pipeline job that runs every minute and drives steps 10 to 14.
- **Heartbeat:** a timestamp (`heartbeat_at`) that a running job writes to show it is alive.

## Rules

- Migrations are additive only: new tables, nullable columns and indexes. A column or table is dropped or renamed in a later release, once the release that still uses it is retired. So the live release keeps working on the migrated schema.
- The public listener is the source of truth for the live colour. `live_colour` in the state record is checked against it and is never trusted over it.
- The lock is held from step 1 until step 8 or step 14 releases it. That includes the whole hold, so no deploy writes to a colour before its hold ends.
- `hold_until` is set once, at the original switch + 30 minutes. A rollback does not move it.
- Whatever colour is not live is shut down at `hold_until`, whichever direction the last switch went.

## Deploy state record

One JSON record per environment, `catalog-web/<env>/deploy-state`, in a small key-value store that the pipeline owns (for example a parameter-store entry). Every write is a CAS on `version`. The record is not in the application database, because the deploy must read it while migrations are running or failing, and a migration must not be able to change it. The CI run log is a second, append-only audit trail. It is not the state.

Fields: `version`, `env`, `deploy_id`, `release_sha`, `image_digest`, `live_colour`, `idle_colour`, `previous_release_digest`, `previous_release_sha`, `status`, `lock`, `queued_sha`, `rolled_back_from`, `t0`, `switch_at`, `watch_until` (switch + 15 min), `hold_until` (switch + 30 min), `migrations_applied`, `heartbeat_at`.

- `lock`: the `deploy_id` of the one deploy allowed to run. Set in step 1. Cleared in step 8 or step 14.
- `queued_sha`: the SHA of the one waiting merge. A newer merge replaces it.
- `rolled_back_from`: the colour that the last rollback moved away from. Empty when no rollback has happened. Cleared with the lock.
- `migrations_applied`: the migrations this deploy applied. The migration tool's own table is the record of which migrations exist and have run.
- `previous_release_digest` and `previous_release_sha`: the rollback target after step 13.

Statuses:

- `deploying`: a run holds the lock and is working towards the switch.
- `migration_failed`: migrations failed. The lock is released. The live colour serves.
- `aborted`: the new release was not switched in. The lock is released.
- `watching`: the listener forwards to the new colour, and the 5xx watch is running.
- `rolling_back`: a rollback is moving the listener.
- `rollback_failed`: the listener could not be moved. The lock stays held.
- `holding`: the watch has ended, or a rollback has finished. The deploy waits for `hold_until`.
- `shut_down`: the non-live colour is being shut down, or has been.
- `complete`: the deploy has finished. The lock is cleared.

## How the run is driven

- Nobody runs these steps by hand. CI runs them on every merge to `main`.
- Steps 1 to 9 run in one pipeline run for each deploy. That run ends at the switch.
- Steps 10 to 14 run in the watch job. It runs every minute from the switch until step 14 finishes. Each run reads the state record, writes `heartbeat_at`, does the step that is due and exits. No run lasts 30 minutes. A failed run loses nothing, because the state is in the record.
- After a rollback the 5xx watch stops. The job keeps running until step 14, so that step 13 can run when `hold_until` passes. In a status that has no step for it, such as `rolling_back` or `rollback_failed`, the job does nothing.
- The pipeline run writes `heartbeat_at` when it starts each step. If the lock is held and `heartbeat_at` is more than 15 minutes old, the stale-lock alert fires. The alert restarts nothing. An engineer reads the listener and the state record and decides what to do.
- A queued merge waits in `queued_sha` until step 8 or step 14 releases the lock. After a successful switch it therefore waits the full 30-minute hold. After an abort it waits less.
- Two kinds of rollback are started by an engineer from the pipeline, and each needs approval: the rollback in step 12, and the rollback deploy at the end of this document.

## Steps

1. **Merge takes the lock.**
   - *Starts:* a merge to `main`.
   - *Does:* if `lock` is empty, sets `lock = deploy_id` and `status = deploying` by CAS. Otherwise writes the SHA into `queued_sha`, replacing any earlier one, and ends.
   - *Keeps:* the state record.
   - *If it fails:* if the state cannot be read, or the CAS loses a race, retry up to 3 times, then stop. The listener is not touched, and an alert is sent.

2. **Confirm the live colour.**
   - *Starts:* step 1 took the lock.
   - *Does:* reads the listener's forward target and maps it to a colour. That colour must match `live_colour`. The other colour is `idle_colour`. If the idle colour has running instances, they were left by an aborted deploy (step 8). Scale them to 0 and wait until they stop. Then record `idle_colour` and `release_sha`.
   - *Keeps:* the state record.
   - *If it fails:* if the listener and the state disagree, or the idle colour's instances do not stop, stop and release the lock. Nothing is changed. An engineer must reconcile the listener and the state first.

3. **Build and test.**
   - *Starts:* step 2 succeeded.
   - *Does:* builds one image from `release_sha` and records its `image_digest`. That digest is the only artifact deployed to every instance. Runs the unit and integration tests. Lints the migrations, and rejects any that drop or rename a table or column, change a column type, or add `NOT NULL` to an existing column without a default. A new column must be nullable or have a default.
   - *Keeps:* `image_digest` in the state record.
   - *If it fails:* stop and release the lock. The live colour is untouched, and nothing was migrated.

4. **Apply migrations once.**
   - *Starts:* step 3 succeeded.
   - *Does:* runs a one-off migration task from `image_digest`. The task takes the advisory lock, so only one migrator runs at a time. It sets `lock_timeout` to 5 seconds and `statement_timeout` to 10 minutes. It runs the pending migrations in order. Each index is built with `CREATE INDEX CONCURRENTLY`, and the task fails if one leaves an INVALID index. A failed transactional migration is rolled back by the database. Each applied migration is recorded in the migration tool's table and listed in `migrations_applied`. Migrations are never reversed.
   - *Keeps:* the migration tool's table, and `migrations_applied`.
   - *If it fails:* set `status = migration_failed` and release the lock. No new-release instance is started, and the live colour keeps serving. Migrations that finished before the failure stay applied, which is safe because they are additive. The next deploy's migration task drops any INVALID index, with `DROP INDEX CONCURRENTLY`, before it runs its own migrations.

5. **Start the new release on the idle colour.**
   - *Starts:* step 4 succeeded.
   - *Does:* sets the idle colour's desired count to 4 with `image_digest`. Tags each instance with `deploy_id`, `release_sha`, `image_digest` and its colour. The platform adds each started instance to that colour's target group. How it does this is not known (see open questions). The listener does not forward to the idle colour, so no user traffic reaches it. Records the first launch time as T0.
   - *Keeps:* the instance tags. They record each colour's release for as long as its instances run.
   - *If it fails:* a launch error counts against the deadline in step 6. If the platform reports that no instance can be launched, abort now through step 8.

6. **Health gate (deadline T0 + 10 minutes).**
   - *Starts:* T0.
   - *Does:* every 10 seconds, the pipeline calls `/healthz` on each new instance directly. It counts consecutive passes per instance. An instance is ready at 3 passes in a row. A failure resets that instance's count. The gate passes when all 4 instances are ready.
   - *Keeps:* the pass counts, in the pipeline run only. They are not in the state record.
   - *If it fails:* a single failed check does not abort the deploy. If the gate has not passed by T0 + 10 minutes, abort through step 8. The listener is not touched.

7. **Smoke suite (must finish by T0 + 10 minutes).**
   - *Starts:* the health gate passes.
   - *Does:* the CI runner runs the smoke suite against each new instance through its internal test path. The public listener is not used.
   - *Keeps:* the result, in the CI run log.
   - *If it fails:* a failing suite, or a suite that does not finish by the deadline, aborts the deploy through step 8.

8. **Abort without touching the listener.**
   - *Starts:* step 5, 6 or 7 failed, or the deadline passed.
   - *Does:* sets the idle colour's desired count to 0. Its logs stay in the log system. In one CAS, sets `status = aborted`, clears `rolled_back_from` and `lock`, and takes `queued_sha`, clearing it. If a SHA was taken, starts a new pipeline run of step 1 for it. That run gets its own `deploy_id`. The migrations from step 4 stay applied, because they are additive.
   - *Keeps:* the state record, and the logs.
   - *If it fails:* if the scale-down call fails, retry, then alert. The lock is still released, because an aborted colour is not live and has no hold. The next deploy's step 2 scales it to 0. The listener is never touched on this path.

9. **Switch the listener.**
   - *Starts:* steps 6 and 7 both passed by the deadline.
   - *Does:* re-checks that the listener forwards to `live_colour` and that all 4 new instances pass `/healthz`. Repoints the forward action to the new target group in one update, with no weights. Reads the listener back to confirm. Then writes `live_colour`, `switch_at`, `watch_until`, `hold_until` and `status = watching`.
   - *Keeps:* the listener, which is the record of the live colour.
   - *If it fails:*
     - If the listener forwards to the new colour, the switch happened. Continue with step 10. If the state write fails, retry it 3 times, then page an engineer.
     - If the listener still forwards to the old colour, the switch did not happen. Follow step 8.
     - If the listener cannot be read, stop and page an engineer. Do not guess.

10. **Watch the 5xx rate (switch to `watch_until`).**
    - *Starts:* step 9 wrote `status = watching`.
    - *Does:* on every run of the watch job, while `status = watching`, computes the 5xx rate over the trailing window of min(5 minutes, time since switch), from the response counts. A window breaches when its 5xx rate is strictly above 1% and it holds at least 100 responses. A breach starts step 11. When `watch_until` passes with no breach, sets `status = holding`.
    - *Missing counts:* if the response counts are missing for 2 consecutive evaluations, page an engineer and do not roll back. Missing means the query fails or returns no data for the window. Zero traffic is not missing. Fewer than 100 responses cannot breach.
    - *Keeps:* the state record, and the response counts in the load balancer's metrics.
    - *If it fails:* if `heartbeat_at` is more than 2 minutes old, an alert fires. The hold cannot end (step 13) while the watch is unconfirmed.

11. **Automatic rollback.**
    - *Starts:* step 10 finds a breach.
    - *Does:* by CAS from `watching`, sets `status = rolling_back` and `rolled_back_from` to the new colour. Repoints the listener to the old target group in one update, without waiting for the old colour's health check. Reads the listener back. On success, sets `live_colour` to the old colour and `status = holding`. The 5xx watch stops. The new colour keeps running as the non-live colour until `hold_until`. Migrations are not reversed.
    - *Keeps:* the state record, and the listener.
    - *If the listener update fails:* retry 3 times. If it still fails, set `status = rollback_failed` and page an engineer. Do not repeat the automation. The listener still forwards to the new colour, so the new colour stays live. The lock stays held, and the watch job does nothing more until an engineer acts.
    - *If the old colour fails `/healthz` after the rollback:* page an engineer. Do not switch again automatically.

12. **Manual rollback during the hold.**
    - *Starts:* an engineer starts the rollback job from the pipeline and approves it. It runs only when `status = holding` and the non-live colour is still running.
    - *Does:* refuses a target that equals `rolled_back_from`. A release that was rolled back from must come back through a new deploy. Otherwise, sets `status = rolling_back` by CAS from `holding`. That stops step 13 from acting at the same time. Repoints the listener to the non-live colour in one update, and reads it back. Then sets `live_colour` to that colour, `rolled_back_from` to the colour it moved away from, and `status = holding`. It does not change `hold_until`. The lock stays held, so queued deploys wait.
    - *Keeps:* the state record, and the listener.
    - *If it fails:* as in step 11. Retry the listener update 3 times, then set `status = rollback_failed` and page an engineer. The live colour stays as it is.

13. **Shut down the non-live colour at `hold_until`.**
    - *Starts:* the watch job sees that `hold_until` has passed while `status = holding`.
    - *Does:* confirms that the listener forwards to `live_colour` and that the live colour's 4 instances pass `/healthz`. Then sets `status = shut_down` by CAS from `holding`. If the CAS fails, step 12 or another change got there first. This run stops, and the next run checks again. Next, reads the non-live colour's `release_sha` and `image_digest` from its instance tags, while its instances still run. If `rolled_back_from` is empty, sets `previous_release_digest` and `previous_release_sha` to those values. If a rollback happened, leaves them unchanged, because the live colour's release is then the one before the release that was rolled back from, and that is already recorded. Sets the non-live colour's desired count to 0 and waits until its instances stop.
    - *Keeps:* `previous_release_digest` and `previous_release_sha`. They are the rollback target after this point.
    - *If it fails:* if the live colour is unhealthy, do not shut down the non-live colour. Page an engineer and keep `status = holding`, because that colour is the only rollback target left. If the scale-down call fails, retry. `status` stays `shut_down`, and step 14 does not run until the instances stop.

14. **Finish.**
    - *Starts:* step 13 succeeded, and the non-live instances have stopped.
    - *Does:* in one CAS, sets `status = complete`, clears `rolled_back_from` and `lock`, and takes `queued_sha`, clearing it. If a SHA was taken, starts a new pipeline run of step 1 for it, with its own `deploy_id`. The run log records the deploy, its outcome and its timestamps. A notification is sent.
    - *Keeps:* the state record, and the run log.
    - *If it fails:* retry the CAS. Until the lock is cleared, all deploys wait. The stale-lock alert covers this case.

## Rollback after the old colour is shut down

After step 13 there is no colour to repoint to. A rollback is then a normal deploy of `previous_release_digest`. An engineer starts it from the pipeline, with approval. It runs steps 1 to 14 with three changes:

- Step 3 does not build. It uses `previous_release_digest` as `image_digest` and `previous_release_sha` as `release_sha`.
- Step 4 applies nothing new, because those migrations are already recorded. It still runs, to keep the same path.
- If `previous_release_digest` is empty, the rollback stops before step 2 and releases the lock.

Because the migrations are additive, the previous release works on the current schema.

## Open questions

- The compute platform is not named. How each colour's instances join its target group, and where they run, is not known.
- The contents and run time of the smoke suite are not in the brief. This procedure assumes a suite exists.
- The name and source of the response-count metric, and how long it lags, are not known. A lag of more than a minute could cause false "missing" alerts.
- The 10-minute `statement_timeout` may be too short for `CREATE INDEX CONCURRENTLY` on large tables.
- The old colour is not tested against the migrated schema before the switch. Safety relies on the additive rule and the step 3 lint.
- If the watch job cannot run during the 15-minute window, no automatic rollback happens. Only the alert fires.
- If the live colour is unhealthy at step 13, the lock stays held until an engineer acts.
- A run that crashes is not picked up by anything. Only the stale-lock alert fires. A crash after the switch but before `status = watching` leaves no watch running, and the next deploy's step 2 stops because the listener and the state disagree.
- The brief does not say how an engineer clears `rollback_failed` and hands the deploy back to the watch. Until that is decided, the lock stays held and deploys wait.
- A merge can arrive while a queued SHA is being started. It can take the lock first, and the older queued SHA then waits behind it. The brief does not say how the two are ordered.
- Who approves the rollback jobs (step 12 and the rollback deploy) is not stated.