# `catalog-web` blue-green deploy procedure

This is the order of steps the CI pipeline follows for every deploy of `catalog-web`, from the merge to `main` to the end of the deploy. Nobody runs these steps by hand. Engineers act only through the named pipeline jobs (`catalog-web-rollback`, `catalog-web-redeploy`, `catalog-web-resume-deploys`).

Terms used below:

- **Old colour**: the colour the public listener points at when the deploy starts.
- **New colour**: the other colour, which gets the new release.
- **T0**: the moment the pipeline sends the request to start the new colour's instances.
- **T-switch**: the moment the public listener is confirmed to point at the new colour.
- **Abort** and **Rollback**: the shared procedures defined after the checklist. Each step says which one it runs.

## Where deploy state is kept

| State | Where | Why there |
|---|---|---|
| Which colour is live | The public listener's forward target, on the load balancer | This is what actually routes traffic, so it is the source of truth. Everything else is checked against it. |
| Deploy record and lock | One JSON document, `catalog-web/deploy-state.json`, in the deploy-state bucket. It is versioned, and every write is conditional: it succeeds only if the version read is still current. | It lasts beyond a single pipeline run. It is kept out of the catalog database, so a database failure cannot hide or corrupt it. Conditional writes settle races between jobs. |
| Which migrations are applied | The migration tool's history table in PostgreSQL | It changes in the same transaction as each migration. |
| Release artifacts | The image registry, as `catalog-web:<commit-sha>` | This lets a redeploy use the exact earlier build. |
| 5xx and request counts | The metrics system, from load balancer metrics for the public listener | It keeps history, so a resumed monitor can look back at time it missed. |
| Audit trail | Each write to the state document is also appended to `catalog-web/deploy-log/` in the same bucket | Pipeline logs are kept per run and are not used for decisions. |

Fields in `deploy-state.json`:

- `live_colour`: a mirror of the listener, checked at every step.
- `paused` and `paused_reason`.
- `lock`, with `deploy_id`, `job_id`, `acquired_at` and `heartbeat_at`.
- `colours.blue` and `colours.green`, each with `release` and `status`. The status is one of `off`, `starting`, `candidate`, `live`, `standby` or `stopping`.
- `deploy`, with `id`, `release`, `from_colour`, `to_colour`, `step`, `t0`, `health_deadline`, `switched_at`, `watch_ends_at`, `retire_at`, `outcome` and `reason`.

## Decisions this procedure makes (not fixed by the brief)

1. **The idle colour has no running instances.** It runs only during a deploy and during the 30-minute standby after the switch.
2. **Only one deploy runs at a time, and it holds the lock until it ends.** A deploy ends after the old colour is retired, or after an abort or a rollback. A successful deploy therefore holds the lock for roughly 40–45 minutes. While it does, the colour being retired is the rollback target, so no other deploy may use it.
3. **Queued merges are collapsed.** When the lock is free, only the newest merged commit that has built successfully deploys. Older runs that are still waiting end as `superseded`. Their changes are included in the newer commit.
4. **Smoke tests reach the new colour through a test listener.** This is a second listener on the same load balancer, on port 8443, reachable only from the CI network. It forwards to the new colour's target group. This also means the load balancer runs health checks on that target group before the switch.
5. **The health gate is the load balancer's own target health.** Each target group's health check is set to path `/healthz`, interval 10 s, healthy threshold 3 and unhealthy threshold 2. "Healthy" therefore means exactly three passes in a row, and it is also what decides whether an instance gets traffic after the switch.
6. **The 10-minute deadline starts at T0.** Boot time counts against it.
7. **Smoke tests run against the production database** because there is only one database. The suite only reads, or writes only as the reserved account `smoke-test@catalog.internal`. Tests that do anything else are rejected in review.
8. **5xx rate:** this counts 5xx responses on the public listener divided by all responses on it. It includes 5xx responses the load balancer generates itself (502/503/504). It is evaluated every 60 s over the trailing 5 minutes, counting only requests after T-switch, so during the first 5 minutes the window is shorter. There is no minimum request volume.
9. **If metrics can't be read for 3 evaluations in a row during the watch, the pipeline rolls back.** The old colour is still available, so failing safe is cheap.
10. **After any rollback, automatic deploys pause.** Otherwise the next unrelated merge would redeploy the same bad code. An engineer clears the pause with `catalog-web-resume-deploys` once `main` has a fix or a revert.
11. **Migrations are protected from blocking the live release.** They run with `lock_timeout = 5s` and `statement_timeout = 15min`. Indexes are created `CONCURRENTLY`. The whole migration job times out after 30 minutes.
12. **A migration that drops or renames something is a "contract" migration.** It must start with a header, `-- contract-after: <commit-sha>`, naming the commit that removed the last use of the object. The pipeline runs it only if the live release contains that commit.
13. **The switch and the retirement are fenced by conditional writes.** The state document moves to `switching` before the listener is repointed, and to `retiring` before the old colour is stopped. A rollback job that finds `retiring` is refused. Whichever conditional write lands first wins.
14. **Instances get a 30-second drain** (deregistration delay) before they are stopped.

## Precondition: before merge

The migration check runs as a required pull request check. A pull request cannot merge if any new migration does any of the following without a valid `contract-after` header: `DROP`, `RENAME`, `ALTER COLUMN ... TYPE`, `SET NOT NULL`, adding a `NOT NULL` column, adding a constraint that validates existing rows, or `CREATE INDEX` without `CONCURRENTLY`. Step 4 runs the same check again, so a bypassed pull request check is still caught.

## The checklist

- [ ] **1. Queue the deploy**
  - *Starts it:* a merge to `main`.
  - *Changes:* creates a pipeline run for the merge commit's SHA. Nothing else.
  - *If it fails:* CI alerts the deploy channel. Nothing has changed, and the next merge deploys everything up to its own commit.

- [ ] **2. Build and publish the release image**
  - *Starts it:* the run starts. Building happens before taking the lock, so it doesn't delay a deploy already in progress.
  - *Changes:* builds the image, runs unit tests, and pushes `catalog-web:<sha>` to the registry. No environment is touched.
  - *If it fails:* the run ends as `build_failed` and the merge author is notified. Nothing has changed.

- [ ] **3. Acquire the deploy lock**
  - *Starts it:* the build succeeded.
  - *Changes:* waits until `lock` is empty and `paused` is false. If a newer commit on `main` has also built successfully, this run ends as `superseded`. Otherwise it writes `lock` and a new `deploy` record with `step: locked` in one conditional write.
  - *If it fails:* if the conditional write loses a race, the run re-reads the document and tries again. If the state bucket can't be reached for 5 minutes, the run fails without changes and pages on-call. While `paused` is set, the run just waits.

- [ ] **4. Preflight checks**
  - *Starts it:* the lock is held.
  - *Changes:* records `from_colour`, `to_colour` and the list of pending migrations, then sets `step: preflight_ok`. The checks are:
    - The public listener's target matches `live_colour`.
    - The new colour has no running instances. If it does, they are leftovers from a crashed run. They get no public traffic (the listener confirms this), so they are stopped and the event is logged.
    - The migration check passes on every pending migration. Pending means present in the release but not in the history table.
    - Every pending contract migration's `contract-after` commit is contained in the live release.
  - *If it fails:*
    - If the listener and the state document disagree, the run sets `paused: true` with the reason, releases the lock and pages on-call. A person must reconcile the state before any deploy runs.
    - If a migration check fails, the run ends as `rejected`, releases the lock and notifies the author.
    - In both cases, the colours and the database are unchanged.

- [ ] **5. Apply schema migrations (once per deploy)**
  - *Starts it:* preflight passed. If nothing is pending, the step records `migrations: none` and moves on.
  - *Changes:* runs the new image's migrate command as a one-off job against PostgreSQL. The migration tool's database advisory lock stops two runs from overlapping. Each migration runs in its own transaction, except the `CONCURRENTLY` index builds. The tool updates the schema and the history table, and the step sets `step: migrated`.
  - *If it fails:*
    - The pipeline runs **Abort** with reason `migration_failed`, naming the migration and the error. No instance of the new release has started. The live colour keeps serving and the public listener is untouched.
    - The failed migration's transaction rolls back. Migrations that succeeded earlier in this run stay applied. They are additive, so the live release is unaffected.
    - A failed `CREATE INDEX CONCURRENTLY` leaves an invalid index, which the fix-forward migration must drop.
    - The fix is a new merge, which applies whatever is still pending.

- [ ] **6. Point the test listener at the new colour**
  - *Starts it:* migrations applied.
  - *Changes:* sets the test listener (port 8443, CI network only) to forward to the new colour's target group. The public listener is not touched.
  - *If it fails:* the pipeline runs **Abort** with reason `test_listener_failed`.

- [ ] **7. Start the new colour**
  - *Starts it:* the test listener points at the new colour.
  - *Changes:* launches 4 instances of `catalog-web:<sha>` and registers them in the new colour's target group. It records `t0`, sets `health_deadline = t0 + 10 min`, and sets the new colour to `release: <sha>` and `status: starting`.
  - *If it fails:* if the platform rejects the launch, the pipeline runs **Abort** with reason `launch_failed` at once. Instances that crash or restart are not a launch failure. They just stay unhealthy, and step 8's deadline handles them.

- [ ] **8. Health gate**
  - *Starts it:* instances launched.
  - *Changes:* every 10 s, the pipeline reads the load balancer's target health for the new target group. The gate passes when all 4 registered targets are healthy, meaning three `/healthz` passes in a row. A replaced instance has to earn its own three passes. On success it sets `step: healthy` and the new colour's status to `candidate`.
  - *If it fails:* if `health_deadline` passes first, the pipeline runs **Abort** with reason `health_timeout`, attaching each instance's check history.

- [ ] **9. Smoke tests**
  - *Starts it:* health gate passed.
  - *Changes:* runs the smoke test suite through the test listener against the new colour. The suite's timeout is the time left until `health_deadline`. Infrastructure is unchanged. The only database writes come from the reserved smoke-test account. On success it sets `step: smoke_passed`.
  - *If it fails:* if any test fails, or the deadline passes while the suite is running (the suite is killed), the pipeline runs **Abort** with reason `smoke_failed` or `health_timeout`. Failed tests are not retried automatically.

- [ ] **10. Pre-switch check**
  - *Starts it:* smoke tests passed.
  - *Changes:* nothing. The pipeline re-reads and confirms all of these:
    - All 4 new targets are still healthy.
    - The public listener still points at the old colour.
    - The lock is still this run's.
    - `paused` is false.
  - *If it fails:* the pipeline runs **Abort** with the condition that failed. The public listener is untouched.

- [ ] **11. Switch traffic (one step)**
  - *Starts it:* pre-switch check passed.
  - *Changes:*
    - A conditional write sets `step: switching`.
    - The public listener's forward target changes from the old target group to the new one, in a single call. The pipeline reads the listener back to confirm.
    - It records `switched_at` (T-switch), `watch_ends_at = T-switch + 15 min` and `retire_at = T-switch + 30 min`.
    - It sets `live_colour` to the new colour, the new colour's status to `live` and the old colour's status to `standby`. The old colour is not touched in any other way.
  - *If it fails:*
    - If the call errors, the pipeline reads the listener. If it still points at the old colour, the call is retried up to 3 times within 60 s, and then the pipeline runs **Abort** with reason `switch_failed`.
    - If the read-back shows the new colour, the switch counts as done and the pipeline carries on.
    - If the listener can't be read, the pipeline keeps retrying the read and pages on-call. It shuts nothing down while it doesn't know which colour is live.

- [ ] **12. Watch the 5xx rate for 15 minutes**
  - *Starts it:* switch confirmed.
  - *Changes:* every 60 s until `watch_ends_at`, the pipeline computes the 5xx rate as defined in decision 8. Nothing changes unless a trigger fires. If none fires, it sets `step: watched`.
  - *If it fails:*
    - If the rate is above 1% in any evaluation, the pipeline runs **Rollback** (automatic, reason `5xx_breach`, with the rate and window).
    - If metrics can't be read for 3 evaluations in a row, the pipeline runs **Rollback** (automatic, reason `metrics_unavailable`).
    - An engineer can also run `catalog-web-rollback` at any point.

- [ ] **13. Hold the old colour on standby until T-switch + 30 min**
  - *Starts it:* the watch ended without a rollback.
  - *Changes:* nothing. The old colour keeps running, untouched. There is no automatic rollback in this period, but the service's normal alerts still apply. `catalog-web-rollback` is still available to engineers.
  - *If it fails:* if an engineer runs `catalog-web-rollback`, the pipeline runs **Rollback** (manual).

- [ ] **14. Retire the old colour**
  - *Starts it:* `retire_at` is reached. The time is read from the state document, not a timer in memory.
  - *Changes:*
    - A conditional write sets `step: retiring`. From this point, rollback jobs are refused, and a rollback means a redeploy.
    - The pipeline confirms the public listener points at the new colour.
    - It deregisters the old colour's instances (30 s drain), stops them, and sets the old colour to `status: off, release: none`.
  - *If it fails:*
    - If the conditional write loses to a rollback, the rollback wins and this step does nothing.
    - If the listener does not point at the new colour, the pipeline stops nothing, pauses deploys and pages on-call.
    - If stopping the instances fails, it retries for 5 minutes. After that the deploy still ends as succeeded but is flagged `retire_failed`, and a non-urgent alert goes out. Those instances get no public traffic, and the next run's preflight (step 4) stops them.

- [ ] **15. Finish**
  - *Starts it:* the old colour is retired.
  - *Changes:* sets `outcome: succeeded`, appends the deploy record to the audit trail, clears `deploy` and `lock`, and posts to the deploy channel. The newest queued run (if any) can now take the lock.
  - *If it fails:* if the state write fails, it is retried. Until it succeeds, the lock stays held and the next deploy waits. After 5 minutes the pipeline pages on-call.

## Shared procedures

### Abort (before the switch)

This runs on any failure in steps 5–11. It never touches the public listener, and the old colour keeps serving throughout.

1. Deregister and stop any new-colour instances, and set the new colour to `status: off, release: none`.
2. Leave migrations in place. They are additive and are never reversed.
3. Record `outcome: aborted` with the step and the reason.
4. Release the lock. Deploys are **not** paused, so the next merge (normally the fix) deploys as usual.
5. Notify the merge author and the deploy channel.

If stopping the instances fails, it is retried for 5 minutes and then flagged. The instances get no public traffic, and the next preflight cleans them up.

### Rollback (after the switch, before retirement)

This runs automatically from step 12, or when an engineer runs the `catalog-web-rollback` pipeline job during steps 12–13.

1. A conditional write sets `step: rolling_back`. If the step is already `retiring` or later, the job is refused and points the engineer to `catalog-web-redeploy`.
2. Repoint the public listener back to the old colour's target group and read it back. This step keeps retrying and paging until it succeeds. It is the one step that never gives up.
3. Set `live_colour` to the old colour and the old colour's status to `live`. Record `outcome: rolled_back` with the reason and the time.
4. Deregister the new colour (30 s drain), stop it, and set it to `status: off`.
5. Leave migrations in place. A rollback never reverses migrations.
6. Set `paused: true` with the reason, release the lock, and page on-call.

The old colour stays live with no time limit. It is the normal live colour from then on.

### Rolling back after retirement: `catalog-web-redeploy <release-sha>`

Once the old colour is shut down, a rollback is a normal deploy of the previous release.

- This job runs steps 3–15 using the existing image `catalog-web:<release-sha>`, with no build.
- It may run while deploys are paused, and it does not clear the pause.
- Step 5 normally finds nothing pending. The migration tool runs in a mode that accepts applied migrations the release doesn't know about.
- Step 4 refuses the redeploy if the release predates the `contract-after` commit of any contract migration already applied. That release would use a column or table that has since been dropped.

### Resuming deploys: `catalog-web-resume-deploys`

An engineer runs this after a rollback, once `main` contains a fix or a revert. It clears `paused`, and the newest commit on `main` then deploys through the checklist.

### If the pipeline job dies mid-deploy

- The running job updates `lock.heartbeat_at` every 30 s.
- A scheduled pipeline job runs every 5 minutes. If the lock is held and the heartbeat is more than 2 minutes old, it restarts the deploy job and notifies on-call.
- The restarted job reads the state document and resumes at the recorded `step`, using the stored absolute timestamps:
  - **Steps 5–10:** if `health_deadline` has passed, run **Abort**. Otherwise continue. Migrations that already succeeded are in the history table and are not run again.
  - **`switching`:** read the public listener to see whether the switch happened, then continue at step 11's read-back.
  - **Step 12:** first evaluate any windows that were missed, from metrics history. If any of them breached, run **Rollback**, provided `retire_at` has not passed. Then continue watching until `watch_ends_at`.
  - **Steps 13–14:** if `retire_at` has passed, go to step 14.
- If the job can't be restarted within 10 minutes, the scheduled check pages on-call. Nothing is changed automatically while no job holds the deploy.
