# catalog-web blue-green deploy procedure

This is the procedure a CI pipeline follows for each `catalog-web` deploy, from a merge to `main` until the deploy is finished. The new release starts in the idle colour, is checked, takes all user traffic in one switch, and is watched for 15 minutes. The old colour stays untouched for 30 minutes so a rollback can point back at it. Nobody runs deploy steps by hand. The only manual actions are the rollback jobs described at the end.

## How the system works today

`catalog-web` is a stateless HTTP service that runs as two colours, blue and green, with 4 instances each. One colour is live and serves users. The other is idle. One load balancer sits in front of both. Its public listener forwards to exactly one target group at a time. Both colours share one PostgreSQL database, which holds one copy of the data. CI deploys when a commit is merged to `main`.

## Terms

- **Colour**: one of the two sets of 4 instances, blue or green.
- **Live colour** and **idle colour**: the colour the public listener points to, and the other one.
- **Target group**: the load balancer's list of instances for one colour.
- **Public listener**: the load balancer rule that sends user traffic to one target group. It is the source of truth for which colour is live.
- **Test listener**: a private listener on port 8443, reachable only from CI runners. It forwards only to the idle target group.
- **`/healthz`**: an HTTP endpoint on each instance that reports whether the instance is healthy.
- **Additive migration**: a database schema change that only adds things, such as new tables, nullable columns or indexes.
- **Migration ledger**: the `schema_migrations` table in PostgreSQL, which records each migration that has been applied.
- **Advisory lock**: a PostgreSQL lock that one session can hold at a time. The migration job takes it so two migration runs cannot overlap.
- **Image digest**: a fingerprint that identifies one exact built image.
- **Deploy lock**: one record in DynamoDB that names the deploy currently using the pipeline.
- **Watch**: the 15 minutes after the switch, during which the 5xx rate is checked.
- **5xx rate**: the share of requests that fail with a server error (HTTP 5xx).
- **State machine**: an AWS Step Functions execution. It runs the watch, the automatic rollback and the shutdown timer, and it keeps running even if the pipeline runner dies.

## Rules that apply across steps

- **Images.** Each build is tagged with the commit SHA and pushed with its digest. Blue, green and every rollback use the same digests. The registry keeps the last 5 release images, so a rollback target is always available.
- **Idle colour between deploys.** The idle colour is not running between deploys. Each deploy launches 4 new instances into it and terminates them after retention. If the team wants both colours always running, skip the launch in the "Launch" step and keep the rest unchanged.
- **Where deploy state lives.** Deploy state is in the DynamoDB table `catalog-web-deploy`, not in the shared PostgreSQL. It stays readable when the database is the thing failing. The state table mirrors the public listener. The migration ledger is in PostgreSQL. CI run logs are the audit trail.
- **One deploy at a time.** Only two colours exist, and the old colour must stay untouched until T+30. So a new deploy cannot start until the old colour is shut down. Merges that arrive during a deploy wait. When the lock frees, only the newest merged commit is deployed.
- **Migrations.** Each release's migrations are applied once, before any new instance starts. They must be additive only: new tables, nullable columns, indexes. The release that is serving traffic must keep working on the migrated schema. Dropping or renaming a column or table happens in a later release, after the release that still uses it has been retired.
- **Migration limits.** The lint step rejects `DROP`, `RENAME`, `ALTER COLUMN ... TYPE`, `SET NOT NULL` and new `NOT NULL` columns. Each migration runs with `lock_timeout = 5s` and `statement_timeout = 2min`, so a migration that waits on a lock fails quickly instead of queueing behind live queries. Indexes use `CREATE INDEX CONCURRENTLY`, so the migration runner must support migrations that are not in a transaction.
- **Health gate.** The target group checks `/healthz` every 10 seconds, with a healthy threshold of 3 and an unhealthy threshold of 2. The pipeline also keeps its own streak counter for each instance, from its own polls. A streak means that instance passed `/healthz` 3 times in a row.
- **Smoke tests.** They run only against the test listener, never the public listener. They either only read data, or write only to the designated smoke-test tenant.
- **The 10-minute deadline.** It starts when the first new instance is launched. The health gate and the smoke tests must both pass within it.
- **5xx rate.** It is measured on the load balancer: (ELB 5xx + target 5xx) / requests. Every minute, it is computed over the trailing 5 minutes, clipped at the switch time. So a failure in the first minutes after the switch is caught without waiting 5 minutes. A window with zero requests does not trigger. A window above 1% triggers rollback. Windows that end by T+15 are still evaluated when their metrics arrive, which can take up to 3 minutes.
- **Missing metrics do not cause rollback.** If the watch cannot read metrics for 5 consecutive minutes, it pages an engineer and leaves the new release live. The deploy is marked `watch_unverified`.
- **Who owns the watch.** The state machine owns the watch, the automatic rollback and the T+30 shutdown timer. The pipeline runner does not.
- **Rollbacks never reverse migrations.**

## Deploy state

| Item | Contents | Written by |
|---|---|---|
| `lock` | `holder` (deploy id), `acquired_at`. It never expires on its own. | Acquire step (set); completion step or a rollback (release) |
| `deploy#<id>` | `commit`, `image_digest`, `migrations_applied`, `colour_new`, `colour_old`, `status`, timestamps (`instances_started_at`, `gate_passed_at`, `smoke_passed_at`, `switched_at`, `watching_started_at`, `watch_ends_at`, `watch_passed_at`, `rollback_at`, `old_shutdown_at`), and an `events` list | Every step |
| `live` | `colour`, `deploy_id`, `target_group_arn`. It mirrors the listener. | Switch step and rollback steps |

Statuses: `queued`, `building`, `migrating`, `launching`, `gating`, `smoke`, `switching`, `watching`, `rolling_back`, `succeeded`, `watch_unverified`, `rolled_back`, `aborted`, `failed_migration`, `migration_suspect`, `complete`.

A run that stops partway can be restarted. Each step reads the state first and skips work already recorded.

## Steps before the switch

- [ ] **1. Merge starts the run.**
  - Starts: a merge to `main`.
  - Does: creates `deploy#<id>` with status `queued`, and records the commit.
  - Data: `deploy#<id>`.
  - If it fails: nothing has changed. The pipeline run fails visibly.

- [ ] **2. Build and push the image.**
  - Starts: step 1.
  - Does: builds the image, tags it with the commit SHA, pushes it, and records the digest.
  - If it fails: stop. Nothing live has changed. Status `aborted`, reason `build`. Nothing needs cleaning up.

- [ ] **3. Lint the migrations.**
  - Starts: step 2.
  - Does: rejects any operation listed under "Migration limits". Checks that no migration in this release is already in the ledger with a different checksum.
  - If it fails: stop before any change. Status `aborted`, reason `migration_lint`. The fix is a new release, not a manual override.

- [ ] **4. Acquire the lock.**
  - Starts: step 3.
  - Does: writes the `lock` item with a conditional write. If another deploy holds it, this run waits in the queue.
  - Data: `lock`.
  - If it fails: a stale lock is never cleared automatically. An engineer clears it only after checking the public listener and both target groups. Otherwise the run keeps waiting.

- [ ] **5. Read the live state.**
  - Starts: step 4.
  - Does: reads the public listener's default action. Its target group is the live colour, and the other colour is idle. Checks that `live` in the state table agrees. Checks that the live colour has at least one healthy target.
  - If it fails: if the listener and the state table disagree, or the live colour has no healthy target, stop. Release the lock. Status `aborted`, reason `live_state_unclear`. Page an engineer. The baseline for the watch is not trustworthy until this is resolved.

- [ ] **6. Run the migrations.**
  - Starts: step 5 passes.
  - Does: one migration job, using the migration role, takes the advisory lock and applies pending migrations in order. Each one is recorded in `schema_migrations`. Transactional migrations run inside a transaction.
  - Data: the migration ledger in PostgreSQL. `migrations_applied` in `deploy#<id>`.
  - If it fails: the job exits non-zero. Status `failed_migration`. Do not launch any instance. Leave the listener alone, so the live colour keeps serving. Release the lock. A transactional failure rolls back by itself. A failed `CREATE INDEX CONCURRENTLY` can leave an `INVALID` index, which the next run drops before retrying. An engineer must review it before the next run.

- [ ] **7. Check the live colour on the migrated schema.**
  - Starts: step 6 succeeds.
  - Does: confirms the live colour's targets are still healthy.
  - If it fails: the migration may be the cause for the release still serving. Stop before launching anything. Status `migration_suspect`. Page an engineer. The fix is a forward migration in a new release.

- [ ] **8. Launch the idle colour.**
  - Starts: step 7 passes.
  - Does: launches 4 instances from the release digest into the idle target group. That target group is not attached to the public listener. Records `instances_started_at` as the moment the first instance starts. Status `launching`.
  - If it fails: if fewer than 4 instances start, or an instance cannot be launched, go to the abort path.

- [ ] **9. Health gate.**
  - Starts: step 8.
  - Does: every 10 seconds, reads target health for the 4 idle instances and updates each instance's streak. The gate passes when all 4 instances have a streak of at least 3 at the same poll. Status `gating`.
  - If it fails: if the gate has not passed by `instances_started_at` + 10 minutes, go to the abort path.

- [ ] **10. Smoke tests.**
  - Starts: all 4 instances have a streak of at least 3 (step 9).
  - Does: runs the smoke suite against the test listener on port 8443. Status `smoke`.
  - If it fails: a failing test, or a suite still running at `instances_started_at` + 10 minutes, goes to the abort path.

- [ ] **11. Pre-switch check.**
  - Starts: steps 9 and 10 have both passed, both within the 10-minute window.
  - Does: re-reads target health and confirms all 4 instances still have a streak of at least 3. Re-reads the listener and confirms it still points to the live colour. Writes status `switching` and the planned switch time before touching the listener.
  - If it fails: if an instance has dropped out of the gate, return to step 9. If the deadline passes, go to the abort path. If the listener no longer points to the live colour, someone else changed it. Stop, do not switch, release the lock, and page an engineer.

- [ ] **12. Switch.**
  - Starts: step 11 passes.
  - Does: one `ModifyListener` call sets the public listener's default action to the idle target group. Then reads the listener back. On success, writes `live` = the new colour and `switched_at` = T.
  - If it fails: read the listener. If it still points to the old colour, nothing moved. Go to the abort path. If it points to the new colour, the switch happened. Continue from step 13 and repair the state table from the listener. A failed state write does not change what users see.

## Steps after the switch

- [ ] **13. Hand the watch to the state machine.**
  - Starts: the switch is confirmed (step 12).
  - Does: starts the state machine with the deploy id, T, the old target group and the new target group. Sets status `watching`, `watching_started_at` = T, and `watch_ends_at` = T+15. The state machine then runs the watch (step 14), the automatic rollback (step 15) and the shutdown timer (step 18). The pipeline run may wait on the state machine to report results, but nothing depends on that wait.
  - If it fails: if the state machine cannot start, the pipeline runs the watch itself. If the pipeline cannot do that either, it points the listener back at the old colour immediately. The old colour is untouched and still ready, so this is the safe default. Then it goes to the automatic rollback (step 15).

- [ ] **14. Watch for 15 minutes.**
  - Starts: step 13.
  - Does: every minute, computes the 5xx rate over the trailing 5 minutes, clipped at T. If any window is above 1%, the watch triggers the automatic rollback (step 15). The watch ends at T+15, plus up to 3 minutes for metric lag.
  - Data: the state machine's run, and `deploy#<id>`.
  - If it fails: if metrics cannot be read for 5 consecutive minutes, page an engineer, leave the new release live, and mark the deploy `watch_unverified`. Manual rollback stays available until T+30.

- [ ] **15. Automatic rollback.**
  - Starts: the watch finds a window above 1% during the watch.
  - Does:
    1. Conditionally moves the state from `watching` to `rolling_back`. Only one actor can win this change, so the watch, the pipeline and a manual job cannot race.
    2. Makes one `ModifyListener` call that points the public listener back at the old target group. Reads the listener back, and confirms at least one target in the old target group is healthy.
    3. Sets `live` to the old colour, `rollback_at` to now, and status `rolled_back`. Then releases the lock.
    4. Captures the new colour's logs, then terminates its instances.
  - Migrations are not touched. The old colour is live again, so the shutdown timer in step 18 does not run for it.
  - If it fails: retry the listener change with backoff until it succeeds. If the old colour has no healthy target, the rollback has failed. Page an engineer right away. The new release stays live, and the engineer chooses between the two colours and the manual rollback job.

- [ ] **16. Mark the watch passed.**
  - Starts: the watch ends at T+15 with no rollback.
  - Does: sets status `succeeded` and writes `watch_passed_at`. The lock stays held, because the old colour is still retained.
  - If it fails: retry the state write. The listener is the source of truth, so a failed write does not change what users see.

- [ ] **17. Retention, T+15 to T+30.**
  - Starts: step 16, or the watch expiring as `watch_unverified`.
  - Does: the old colour is not touched. Nothing is deployed to it, and its instances and configuration do not change. From now on, rollback is manual only. Automatic rollback applies only during the watch. An engineer can run the manual rollback job at any time until T+30.
  - If it fails: an unhealthy old-colour instance is left alone, because a rollback needs only one healthy instance. If no instance is healthy, the old colour cannot take a rollback, so page an engineer.

- [ ] **18. Shut down the old colour at T+30.**
  - Starts: the state machine's timer at T+30.
  - Does: first checks that the status is `succeeded` or `watch_unverified`, and that no rollback is in progress. This check is conditional, so a rollback that has just started wins. Then it deregisters the old colour's targets, terminates its instances, and writes `old_shutdown_at`. The listener is not changed.
  - If it fails: retry the termination. The old colour receives no traffic and the lock is still held, so nothing else proceeds. Page an engineer if termination keeps failing. Once the old colour is shut down, a rollback to it is no longer possible. From then on, rollback is a normal deploy of the previous release (see below).

- [ ] **19. Complete the deploy.**
  - Starts: step 18 passes.
  - Does: sets status `complete`, then deletes the `lock` item, conditional on the holder being this deploy id. Queued merges now start from step 1.
  - If it fails: retry. A lock that cannot be released stops the queue, so page an engineer.

## Abort path (before the switch)

- [ ] **Abort.**
  - Starts: the health gate misses its deadline (step 9), smoke tests fail or miss their deadline (step 10), or the listener check fails (steps 11 and 12).
  - Does: confirms the public listener still points to the live colour. Saves the new instances' logs and the smoke output to the CI run. Deregisters and terminates the new instances. Sets status `aborted`, with the reason. Releases the lock.
  - Migrations stay applied. They are additive, so the live release works on them. The next deploy skips them, because they are in the ledger. The fix is a forward release.

## Manual rollback

- [ ] **Manual rollback during retention.**
  - Starts: an engineer runs the `rollback` pipeline job with a deploy id. The default is the latest `succeeded` deploy. It can run from the end of the watch until T+30. During the watch, the state machine owns the rollback.
  - Does: checks that the deploy status is `succeeded` or `watch_unverified`, and that the old colour still exists with at least one healthy target. Conditionally moves the state to `rolling_back`. Points the public listener at the old target group and reads it back. Sets `live` to the old colour. Captures the failed colour's logs, then terminates it. Sets status `rolled_back`, then releases the lock. Migrations are not reversed.
  - If it fails: retry, the same as the automatic rollback. Page an engineer if it keeps failing.

- [ ] **Rollback after the old colour is shut down.**
  - Starts: an engineer runs the `deploy` pipeline job with the previous release's digest. That digest comes from the most recent `succeeded` deploy in the state table.
  - Does: a normal full deploy of the previous release, starting from step 1. The migration step finds nothing pending, because every migration is already in the ledger, so it does nothing. The health gate, smoke tests, switch and watch all run again. This works because every migration is additive, so the previous release runs on the current schema.
  - If it fails: the failures are the same as in a normal deploy. The live colour is unchanged until the switch.

## Open questions and assumptions to confirm

- The target group health check settings in the health gate are the ones deployed. The team uses the metric names and dimensions for the 5xx rate that the load balancer publishes in this account.
- The migration role can reach the database from the pipeline. The test listener's security group allows CI runners only.
- If the idle colour is kept running between deploys, the "Launch" step is replaced by a check that the idle colour runs the expected previous release.