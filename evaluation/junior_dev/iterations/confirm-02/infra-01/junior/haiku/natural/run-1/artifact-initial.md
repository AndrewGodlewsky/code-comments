# Blue-green deploy procedure for `catalog-web`

This document is the procedure the pipeline must implement, in the order it runs, from a merge to `main` until the deploy is finished. Nobody runs these steps by hand. The only human-started job is the manual rollback in step 12.

## Decisions made here

- **Source of truth for the live colour:** the public listener's forward action. Every other record is checked against it and is not trusted over it.
- **Deploy state:** one JSON record per environment, `catalog-web/<env>/deploy-state`, in a small key-value store that the pipeline owns (for example a parameter-store entry). It is separate from the application database. Each write is a compare-and-set on a `version` field, so two runs cannot both win. The store is not in the shared PostgreSQL database because the deploy must read its state while migrations are running or failing, and a migration must not be able to alter it. The CI run log is a second, append-only audit trail; it is not the state.
- **Schema version:** the migration tool's own tracking table in PostgreSQL. The deploy state only records which migrations this deploy applied.
- **One deploy at a time:** a `lock` field in the state record holds the `deploy_id`. A merge that arrives while the lock is held, or while the idle colour is still in its hold, waits in a single queue slot. A newer merge replaces the queued SHA, so the queue never holds more than one deploy.
- **Timing clock:** T0 is the launch time of the first new instance. The deadline is T0 + 10 minutes.
- **Health checks:** the pipeline calls each new instance's `/healthz` directly, every 10 seconds. An instance is ready after 3 passes in a row. A failure resets that instance's count. A failure does not abort the deploy before the deadline.
- **Smoke tests:** they run against the new instances' own addresses through an internal test path. They never go through the public listener.
- **5xx rate:** 5xx responses divided by all responses served through the public listener while it forwards to the new colour. Evaluated every minute from the switch until switch + 15 minutes, over the trailing window of min(5 minutes, time since switch). A window breaches when the rate is strictly above 1% and it contains at least 100 responses. If the metrics are missing for 2 consecutive evaluations, the pipeline pages an engineer and does not roll back automatically.
- **Rollback:** repoints the listener immediately. It does not wait for the old colour's health check. The old colour is checked afterwards.
- **Hold rule:** whatever colour is not live is shut down at `hold_until` (switch + 30 minutes), whichever direction the last switch went. No deploy writes to a colour before its hold ends.

## Deploy state record

Fields: `version`, `env`, `deploy_id`, `release_sha`, `image_digest`, `live_colour`, `idle_colour`, `previous_release_digest`, `status`, `lock`, `queued_sha`, `t0`, `switch_at`, `watch_until` (switch + 15m), `hold_until` (switch + 30m), `migrations_applied`, `heartbeat_at`.

Statuses: `deploying`, `migration_failed`, `aborted`, `watching`, `rolling_back`, `rollback_failed`, `holding`, `shut_down`, `complete`.

## Checklist

- [ ] **1. Merge starts the deploy and takes the lock.**
  - *Starts:* a merge to `main`.
  - *Does:* reads the state record. If `lock` is empty and the idle colour has no hold running, it sets `lock = deploy_id` and `status = deploying` with a compare-and-set. Otherwise it writes the SHA into `queued_sha` (replacing any earlier one) and ends. The queued deploy starts when the lock is released.
  - *If it fails:* if the state cannot be read or the compare-and-set loses a race, the run retries up to 3 times and then stops. The listener is not touched, and an alert is sent.

- [ ] **2. Confirm the live colour.**
  - *Starts:* step 1 succeeded.
  - *Does:* reads the public listener's forward target and maps it to a colour. It checks that this matches `live_colour` in the state record. The idle colour is the other one. It checks that the idle colour has no running instances or that its hold has ended. Then it records `idle_colour` and the planned `release_sha`.
  - *If it fails:* if the listener and the state disagree, or the idle colour still has running instances, the deploy stops and releases the lock. Nothing is changed. An engineer must reconcile the two first.

- [ ] **3. Build and test the release.**
  - *Starts:* step 2 succeeded.
  - *Does:* builds one image from `release_sha` and records its digest. That digest is the only artifact deployed to every instance. The run executes the unit and integration tests. It also lints the migrations and rejects any that drop or rename a table or column, change a column type, or add `NOT NULL` to an existing column without a default. New columns must be nullable or have a default.
  - *If it fails:* the deploy stops and releases the lock. The live colour is untouched, and nothing was migrated.

- [ ] **4. Apply migrations once.**
  - *Starts:* step 3 succeeded.
  - *Does:* runs a one-off migration task from the new image digest. It takes a PostgreSQL advisory lock so only one migrator can run, sets `lock_timeout` to 5 seconds and a statement timeout, and runs the migrations in order. Each applied migration is recorded in the migration tool's own table. Each index is built with `CREATE INDEX CONCURRENTLY`, and the task fails if one leaves an `INVALID` index. Transactional migrations are rolled back by the database if they fail. Migrations are never reversed by a rollback.
  - *If it fails:* the state becomes `migration_failed`, the lock is released, and no new-release instance is ever started. The live colour keeps serving. The next deploy's migration task drops any `INVALID` index left behind before it runs its own migrations.

- [ ] **5. Start the new release on the idle colour.**
  - *Starts:* step 4 succeeded.
  - *Does:* sets the idle colour's desired count to 4 with `image_digest`. Each instance is tagged with `deploy_id`, `release_sha` and the colour. The idle target group stays detached from the public listener. The first launch time is recorded as T0.
  - *If it fails:* a launch error counts toward the deadline in step 6. If the platform reports that no instance can be launched, the deploy aborts immediately, following the abort path in step 8.

- [ ] **6. Health gate (deadline T0 + 10 minutes).**
  - *Starts:* the first instance launches (T0).
  - *Does:* every 10 seconds, calls `/healthz` on each new instance. Counts consecutive passes per instance and marks an instance ready at 3. The gate passes only when all 4 instances are ready.
  - *If it fails:* if the gate is not passed by T0 + 10 minutes, the deploy aborts through step 8 and the listener is not touched.

- [ ] **7. Smoke suite.**
  - *Starts:* all 4 instances are ready.
  - *Does:* runs the smoke suite against the idle colour's instance addresses through the internal test path. The suite has a timeout that must end by T0 + 10 minutes.
  - *If it fails:* the deploy aborts through step 8. The suite failing means the deadline's condition was not met.

- [ ] **8. Abort without touching the public listener.**
  - *Starts:* step 5, 6 or 7 failed, or the deadline passed.
  - *Does:* sets the idle colour's desired count to 0 and leaves its logs in the log system. Sets `status = aborted`, releases the lock and starts the queued deploy if there is one. The migrations from step 4 stay applied. That is safe because they are additive.
  - *If it fails:* if the scale-down call fails, the pipeline retries and alerts. The idle colour is not live, so it can keep running until the next deploy replaces it. The listener is never touched on this path.

- [ ] **9. Switch the listener.**
  - *Starts:* steps 6 and 7 passed by the deadline.
  - *Does:* re-checks that the listener still forwards to the live colour and that all 4 new instances still pass `/healthz`. Then it repoints the public listener's forward action to the new target group in one update, without weights. It reads the listener back to confirm. It then sets `live_colour` to the new colour, `switch_at`, `watch_until`, `hold_until` and `status = watching`.
  - *If it fails:* the pipeline reads the listener. If it forwards to the new colour, the switch is treated as done and the run continues from step 10. If it still forwards to the old colour, the switch did not happen, so the run follows the step 8 abort. If the listener cannot be read, the run stops and pages an engineer. It does not guess.

- [ ] **10. Watch the 5xx rate (switch to switch + 15 minutes).**
  - *Starts:* step 9 succeeded.
  - *Does:* every minute, computes the 5xx rate over the trailing window of min(5 minutes, time since switch). If a window is above 1% with at least 100 responses, it starts step 11. If the metrics are missing for 2 consecutive evaluations, it pages an engineer and does not roll back. The watch runs as a scheduled pipeline job that reads and updates the state record. It updates `heartbeat_at` each run. If the heartbeat is more than 2 minutes old, an alert fires. When `watch_until` passes with no breach, `status` becomes `holding`.
  - *If it fails:* if the watch job cannot run, the alert fires, and the hold in step 13 cannot end while the watch is unconfirmed.

- [ ] **11. Automatic rollback.**
  - *Starts:* step 10 finds a breach.
  - *Does:* sets `status = rolling_back` with a compare-and-set. Repoints the listener to the old colour's target group in one update, and reads it back to confirm. Then checks the old colour's `/healthz`. The new colour keeps running as the non-live colour until its hold ends. Migrations are not reversed.
  - *If it fails:* the listener update is retried 3 times. If it still fails, `status = rollback_failed`, the pipeline pages an engineer and does not repeat the automation. The new colour stays live, because that is the only colour the listener can reach.

- [ ] **12. Hold the old colour, and manual rollback.**
  - *Starts:* step 10 ends without a breach, or step 11 finishes.
  - *Does:* the non-live colour stays running and untouched until `hold_until`, which is switch + 30 minutes. A rollback job, which an engineer starts from the pipeline and which needs approval, can repoint the listener to the non-live colour, but only while that colour is still running and not yet shut down. It uses the same repoint and read-back as step 11. The lock stays held, so queued deploys wait.
  - *If it fails:* the same handling as step 11. A rollback that fails leaves the live colour as it is and pages an engineer.

- [ ] **13. Shut down the non-live colour at `hold_until`.**
  - *Starts:* `hold_until` passes, `status` is `holding` (or the rollback in step 11 has finished), and the watch has been confirmed by its heartbeat.
  - *Does:* confirms the listener forwards to the live colour and the live colour's 4 instances pass `/healthz`. Then it sets the non-live colour's desired count to 0 and waits for the instances to drain. It writes `status = shut_down` and sets `previous_release_digest` to the non-live colour's image digest.
  - *If it fails:* if the live colour is unhealthy, the non-live colour is not shut down. The run pages an engineer and keeps the hold, because that colour is the only rollback target left. If the shutdown call fails, it is retried and the status stays `holding`.

- [ ] **14. Finish.**
  - *Starts:* step 13 succeeded.
  - *Does:* sets `status = complete` and clears `lock`. The next queued deploy starts if there is one. The run log records the deploy, its outcome and its timestamps, and a notification is sent.
  - *If it fails:* if clearing the lock fails, the run retries. Until the lock is cleared, all deploys wait. The alert for a stale lock is set to fire after 15 minutes.

## Rolling back after the old colour is shut down

Once step 13 has run, there is no colour to repoint to. A rollback is a normal deploy of `previous_release_digest`, using the same steps 1 to 14. Step 4 still runs. It applies nothing new, because the migrations are already recorded. Because the migrations are additive, the previous release still works on the current schema.
