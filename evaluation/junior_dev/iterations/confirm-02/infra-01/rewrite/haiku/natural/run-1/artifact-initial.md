# catalog-web blue-green deploy procedure

This is the procedure a pipeline follows from merge to the end of a deploy. It covers the decisions the brief left open, and it says where deploy state is kept. Every step is run by CI. Nobody runs deploy steps by hand. The only manual actions are the rollback jobs in the "Rollback" section, which an engineer starts as pipeline jobs.

## Decisions

1. **Idle colour is not running between deploys.** The brief gives each colour 4 instances. This procedure assumes the idle colour's instances are terminated after retention ends (step 18), and that each deploy launches 4 new instances into it (step 8). If the team wants both colours always running, skip the launch in step 8 and keep the rest unchanged.
2. **One immutable image per commit.** Each build is tagged with the commit SHA and pushed with its digest. Blue, green and every rollback use the same digests. The registry keeps the last 5 release images so a rollback target is always available.
3. **Deploy state lives in DynamoDB table `catalog-web-deploy`**, not in the shared PostgreSQL. The state must stay readable when the database is the thing that is failing. The live colour is read from the public listener, which is the source of truth. The state table mirrors it. The migration ledger is the `schema_migrations` table in PostgreSQL. CI run logs are the audit trail.
4. **Migrations run once, in a single migration job, under a PostgreSQL advisory lock**, with `lock_timeout = 5s` and `statement_timeout = 2min`. A migration that waits on a lock fails quickly instead of queueing behind live queries. The lint in step 3 rejects `DROP`, `RENAME`, `ALTER COLUMN ... TYPE`, `SET NOT NULL`, and new `NOT NULL` columns. Indexes must use `CREATE INDEX CONCURRENTLY`, so the migration runner must support non-transactional migrations.
5. **Health gate uses the target group's own check.** Interval 10 s, healthy threshold 3, unhealthy threshold 2. The pipeline also keeps a per-instance streak counter from its own polls, so the gate really means "three passes in a row" rather than the target group's rolled-up state.
6. **Smoke tests run on a private test listener** (port 8443, reachable only from CI runners). That listener forwards only to the idle target group. The public listener is not used. Smoke tests either only read data or write only to the designated smoke-test tenant.
7. **The 10-minute deadline starts when the first new instance is launched.**
8. **5xx rate is measured on the load balancer:** (ELB 5xx + target 5xx) / requests. It is evaluated every minute over the trailing 5 minutes, clipped at the switch time, so a failure in the first minutes after the switch is caught without waiting 5 minutes. A window with zero requests does not trigger. Windows ending by T+15 are evaluated as their metrics arrive, allowing up to 3 minutes of metric lag.
9. **Missing metrics do not cause rollback.** If the watch cannot read metrics for 5 consecutive minutes, it pages an engineer and leaves the new release live. The deploy is marked `watch_unverified`.
10. **One deploy at a time, and deploys queue behind retention.** Only two colours exist, and the old colour must stay untouched until T+30. So a new deploy cannot start until the old colour is shut down. Merges that arrive while a deploy is in progress wait, and when the lock frees, only the newest merged commit is deployed.
11. **The watch is owned by a state machine, not the pipeline runner.** A Step Functions execution (or any scheduler that survives runner loss) carries the watch, the automatic rollback and the T+30 shutdown timer.

## Deploy state

| Item | Contents | Written by |
|---|---|---|
| `lock` | `holder` (deploy_id), `acquired_at`. No auto-expiry. | Step 4 (acquire), step 19 or rollback (release) |
| `deploy#<id>` | `commit`, `image_digest`, `migrations_applied`, `colour_new`, `colour_old`, `status`, timestamps (`instances_started_at`, `gate_passed_at`, `smoke_passed_at`, `switched_at`, `watch_ends_at`, `rollback_at`, `old_shutdown_at`), `events` list | Every step |
| `live` | `colour`, `deploy_id`, `target_group_arn` (mirror only) | Steps 12 and 15 |

Statuses: `queued`, `building`, `migrating`, `launching`, `gating`, `smoke`, `switching`, `watching`, `succeeded`, `watch_unverified`, `rolled_back`, `aborted`, `failed_migration`, `migration_suspect`, `complete`.

A run that stops partway can be restarted. Each step reads the state and skips work already recorded.

## Checklist

### Before the switch

- [ ] **1. Merge triggers the run.**
  - Starts: merge to `main`.
  - Does: creates `deploy#<id>` with status `queued`, records the commit.
  - If it fails: nothing has changed. The pipeline run fails visibly.

- [ ] **2. Build and push the image.**
  - Starts: step 1.
  - Does: builds the image, tags it with the commit SHA, pushes it, records the digest.
  - If it fails: stop. Nothing live has changed. Status `aborted`, reason `build`. Nothing needs cleaning up.

- [ ] **3. Lint the migrations.**
  - Starts: step 2.
  - Does: rejects any non-additive operation listed in decision 4. Checks that no migration in this release is already recorded as applied with a different checksum.
  - If it fails: stop before any change. Status `aborted`, reason `migration_lint`. The fix is a new release, not a manual override.

- [ ] **4. Acquire the lock.**
  - Starts: step 3.
  - Does: conditional write on `lock`. If another deploy holds it, this run waits in the queue (decision 10).
  - If it fails: a stale lock is never cleared automatically. An engineer clears it only after checking the listener and both target groups. Otherwise the run waits.

- [ ] **5. Read the live state.**
  - Starts: step 4.
  - Does: reads the public listener's default action. Its target group is the live colour, and the other colour is the idle colour. Checks that `live` in the state table agrees. Checks that the live colour has at least one healthy target.
  - If it fails: if the listener and the state table disagree, or the live colour has no healthy target, stop. Release the lock. Status `aborted`, reason `live_state_unclear`. Page an engineer. The baseline for the watch is not trustworthy until this is resolved.

- [ ] **6. Run the migrations.**
  - Starts: step 5 passes.
  - Does: one migration job, using the migration role, takes the advisory lock and applies pending migrations in order. Each one is recorded in `schema_migrations`. Transactional migrations are wrapped in a transaction.
  - If it fails: the job exits non-zero. Status `failed_migration`. Do not launch any instance. Leave the listener alone. The live colour keeps serving. Release the lock. Migrations are never reversed. A transactional failure rolls back by itself. A failed `CREATE INDEX CONCURRENTLY` can leave an `INVALID` index, which the next run drops before retrying. An engineer must review before the next run.

- [ ] **7. Check the live colour on the migrated schema.**
  - Starts: step 6 succeeds.
  - Does: confirms the live colour's targets are still healthy.
  - If it fails: the migration is suspect for the release still serving. Stop before launching anything. Status `migration_suspect`. Page an engineer. Migrations are not reversed. The fix is a forward migration in a new release.

- [ ] **8. Launch the idle colour.**
  - Starts: step 7 passes.
  - Does: launches 4 instances from the release digest into the idle colour's target group. The target group is not attached to the public listener. Records `instances_started_at` as the moment the first instance starts. Status `launching`.
  - If it fails: if fewer than 4 instances start, or an instance cannot be launched, go to the abort path (A1).

- [ ] **9. Health gate.**
  - Starts: step 8.
  - Does: every 10 seconds, reads target health for all idle-colour instances and updates a per-instance streak. The gate passes when all 4 instances have a streak of at least 3 at the same poll. Status `gating`.
  - If it fails: if the gate is not passed by `instances_started_at` + 10 minutes, go to A1.

- [ ] **10. Smoke tests.**
  - Starts: all 4 instances have a streak of at least 3 (step 9).
  - Does: runs the smoke suite against the test listener on port 8443, which forwards only to the idle target group. Status `smoke`.
  - If it fails: a failing test, or a suite still running at `instances_started_at` + 10 minutes, goes to A1.

- [ ] **11. Pre-switch check.**
  - Starts: steps 9 and 10 are both passed, and both happened within the 10-minute window.
  - Does: re-reads target health, confirming all 4 instances still have a streak of at least 3. Re-reads the listener, confirming it still points to the live colour. Writes status `switching` and the planned switch time before touching the listener.
  - If it fails: if an instance has dropped out of the gate, return to step 9 until the deadline. If the listener no longer points to the live colour, someone else changed it. Stop, do not switch, release the lock, page an engineer.

- [ ] **12. Switch.**
  - Starts: step 11 passes.
  - Does: one `ModifyListener` call that sets the public listener's default action to the idle target group. Reads the listener back. On success, writes `live` = the new colour and `switched_at` = T.
  - If it fails: read the listener. If it still points to the old colour, nothing moved. Go to A1. If it points to the new colour, the switch happened. Continue from step 13. The listener is the source of truth, so the state table is repaired from it. A failed state write does not change what users see.

### After the switch

- [ ] **13. Hand the watch to the state machine.**
  - Starts: the switch is confirmed (step 12).
  - Does: starts the state machine with the deploy id, T, the old target group and the new target group. The state machine owns the watch (step 14), the automatic rollback (step 15), and the T+30 shutdown timer (step 18). The pipeline run may wait on the state machine for reporting, but nothing depends on that wait.
  - If it fails: the state machine cannot start, so the pipeline runs the watch itself. If the pipeline cannot do that either, it points the listener back at the old colour immediately. That colour is untouched and still ready, so this is the safe default. Then it goes to rollback (step 15).

- [ ] **14. Watch for 15 minutes.**
  - Starts: step 13.
  - Does: every minute, computes the 5xx rate over the trailing 5 minutes, clipped at T (decision 8). If any window is above 1%, the watch triggers step 15. The watch ends at T+15, plus up to 3 minutes for metric lag. Windows that end by T+15 are still evaluated when their metrics arrive.
  - If it fails: if metrics cannot be read for 5 consecutive minutes, follow decision 9. Page an engineer, leave the new release live, and mark the deploy `watch_unverified`. Manual rollback remains available until T+30.

- [ ] **15. Automatic rollback.**
  - Starts: the watch in step 14 finds a window above 1% during the watch.
  - Does: first, conditionally moves the state from `watching` to `rolling_back`. Only one actor can win this transition, so the watch, the pipeline and a manual job cannot race. Then one `ModifyListener` call points the public listener back at the old target group, and the listener is read back. Confirms that at least one target in the old target group is healthy. Sets `live` to the old colour, `rollback_at` to now, and status `rolled_back`. Captures the new colour's logs, then terminates its instances. The old colour is now the live colour, so its 30-minute retention ends. Migrations are not touched.
  - If it fails: retry the listener change with backoff until it succeeds. If the old colour has no healthy target, that is a failed rollback, so page an engineer right away. The new release stays live, and the engineer decides between the two colours and the manual rollback job.

- [ ] **16. Mark the watch passed.**
  - Starts: the watch ends at T+15 with no rollback.
  - Does: status `succeeded`, writes `watch_passed_at`. The lock stays held, because the old colour is still retained.
  - If it fails: retry the state write. The listener is the source of truth, so a failed write does not change what users see.

- [ ] **17. Retention, T+15 to T+30.**
  - Starts: step 16, or the watch expiring as `watch_unverified`.
  - Does: the old colour is not touched. Nothing is deployed to it, and its instances and configuration are not changed. From now on, rollback is manual only (the automatic rollback applies only during the watch). An engineer can start the rollback job (R1) at any time until T+30.
  - If it fails: an unhealthy old-colour instance is left alone, because a rollback needs only one healthy instance. If no instance is healthy, the old colour cannot take a rollback, so page an engineer.

- [ ] **18. Shut down the old colour at T+30.**
  - Starts: the state machine timer at T+30.
  - Does: first checks that the status is `succeeded` or `watch_unverified` and that no rollback is in progress. The check is conditional, so a rollback that has just started wins. Then deregisters the old colour's targets, terminates its instances, and writes `old_shutdown_at`. The listener is not changed.
  - If it fails: retry termination. The old colour receives no traffic, and the lock is still held, so nothing else proceeds. Page an engineer if termination keeps failing. Rollback to the old colour stops being possible once it is shut down, so the procedure at R2 applies from then on.

- [ ] **19. Complete the deploy.**
  - Starts: step 18 passes.
  - Does: writes status `complete`, deletes `lock` (conditional on the holder being this deploy id). Queued merges now start from step 1.
  - If it fails: retry. A lock that cannot be released stops the queue, so it pages an engineer.

### Abort before the switch

- [ ] **A1. Abort without touching the public listener.**
  - Starts: the health gate misses its deadline (step 9), smoke fails or misses its deadline (step 10), or the listener check fails (steps 11, 12).
  - Does: confirms the public listener still points to the live colour. Saves the new instances' logs and the smoke output to the CI run. Deregisters and terminates the new instances. Status `aborted`, with the reason. Releases the lock.
  - Migrations stay applied. They are additive, so the live release works on them. The next deploy skips them, because they are in the ledger. The fix is a forward release.

## Rollback

- [ ] **R1. Manual rollback during retention.**
  - Starts: an engineer runs the `rollback` pipeline job, with the deploy id (default: the latest `succeeded` deploy). It can run from when the watch has ended until T+30. During the watch, the state machine owns the rollback.
  - Does: checks that the deploy status is `succeeded` or `watch_unverified` and that the old colour still exists with at least one healthy target. Conditionally moves the state to `rolling_back`. Points the public listener at the old target group, reads it back, sets `live` to the old colour, and terminates the failed colour after capturing its logs. Marks status `rolled_back`, then releases the lock. Migrations are not reversed.
  - If it fails: the same as step 15. Retry, and page an engineer if it keeps failing.

- [ ] **R2. Rollback after the old colour is shut down.**
  - Starts: an engineer runs the `deploy` pipeline job with the previous release's digest. That digest comes from the most recent `succeeded` deploy in the state table.
  - Does: a normal full deploy of the previous release, from step 1 onwards. The migration step finds nothing pending, because all migrations are in the ledger, so it does nothing. The gate, smoke tests, switch and watch all apply again. This works because every migration is additive, so the previous release runs on the current schema.
  - If it fails: the failures are the same as in a normal deploy. The live colour is unchanged until the switch.

## Assumptions to confirm

- The ALB target group health check settings in decision 5 are the ones deployed. The team uses the metric names and dimensions for the 5xx rate that the load balancer publishes in this account.
- The migration role can reach the database from the pipeline, and the test listener's security group allows CI runners only.
- The idle colour is not kept running between deploys (decision 1). If it is, step 8 is replaced by a check that the idle colour runs the expected previous release.