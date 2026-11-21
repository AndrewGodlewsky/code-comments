# Blue-green deploys for `catalog-web`: procedure

## Decisions and where state lives

- **Which colour is live** is never stored. The pipeline reads it from the load balancer's public listener (the target group it forwards to). The other colour is the idle one and is the deploy target.
- **The idle colour has 0 running instances.** Step 13 or the rollback step stops them. Step 3 enforces this.
- **Deploy record.** One JSON object, `deploys/catalog-web/state.json`, in the pipeline's state bucket. Every write is a conditional write (compare on the object's version), so two jobs cannot both change it.
  - It holds `deploy_id`, `release` (commit SHA), `old_colour`, `new_colour`, `phase`, `instances_started_at`, `switched_at` and `migration_version`.
  - `phase` is one of: `migrating`, `starting`, `gating`, `switched`, `rolling_back`, `rolled_back`, `aborted`, `migration_failed`, `succeeded`.
  - The timers in steps 10 and 12 are computed from `switched_at` in this record. They are not kept in a job's memory.
- **Migrations applied** are tracked by the migration tool in the PostgreSQL database, as in any migrations table. That is the only deploy state in the database.
- **One deploy at a time.** The pipeline runs `catalog-web` deploys in a single concurrency group. The lock is held from step 3 until the deploy reaches a final phase (`succeeded`, `rolled_back`, `aborted` or `migration_failed`). A merge that arrives meanwhile waits in the queue. If several are waiting, only the newest runs and the rest are marked superseded. The reason is that the old colour must be shut down before it can become the next idle target. A merge can therefore wait up to about 45 minutes.
- **One long-running job.** The deploy runs as one pipeline job from step 3 to step 14. If it crashes, re-running it resumes from `phase`, and every step is safe to repeat.
- **Alerting.** "Alert" means the pipeline pages the on-call engineer.
- **Smoke tests** run directly against the new instances' addresses, not through the load balancer.
- **Rollback is a pipeline job.** It is a manual-trigger job named `catalog-web-rollback`. It is the only way an engineer rolls back.

## Checklist

- [ ] **1. Merge to `main`**
  - **Starts it:** a merge to `main`.
  - **Changes:** nothing yet. The pipeline run is queued in the deploy concurrency group.
  - **If it fails:** not applicable. If another deploy holds the lock, this run waits as described above.

- [ ] **2. Build, test, and check the migrations**
  - **Starts it:** the run reaching the front of the queue.
  - **Changes:** builds the release image tagged with the commit SHA and pushes it to the registry. It runs unit tests. It runs a migration check that rejects anything that is not additive: `DROP`, `RENAME`, a `NOT NULL` column without a default, or a type change.
  - **If it fails:** the pipeline stops. No deploy record is created and nothing is deployed.

- [ ] **3. Take the lock and check the starting state**
  - **Starts it:** step 2 passing.
  - **Changes:** reads the live colour from the listener and sets `old_colour` to it. The other colour becomes `new_colour`. Reads `state.json`: the previous deploy must be in a final phase. If the new colour still has running instances left over from an earlier failure, stops them. This is safe because the listener does not point at them.
  - **If it fails:** if the listener and the record disagree, or the old colour does not have 4 healthy instances, the pipeline stops and alerts. A person fixes it, because the pipeline cannot tell which side is right.

- [ ] **4. Write the deploy record**
  - **Starts it:** step 3 passing.
  - **Changes:** writes `state.json` with a new `deploy_id`, the release, both colours and `phase = migrating`.
  - **If it fails:** the pipeline stops and alerts. Nothing else has changed.

- [ ] **5. Apply the schema migrations (once)**
  - **Starts it:** step 4 passing.
  - **Changes:** a single job runs the release's migrations against the shared database. Each migration runs in its own transaction, and the tool also takes a database advisory lock. If there are no pending migrations, this step does nothing. On success it records `migration_version`. The timeout is 15 minutes.
  - **If it fails:** `phase = migration_failed`. The deploy stops here and no instance of the new release is started. The old colour keeps serving. The failing migration rolls back. Any earlier migration in the same run stays applied, which is harmless because they are all additive. The pipeline alerts. The lock is released.

- [ ] **6. Start the new colour**
  - **Starts it:** step 5 succeeding.
  - **Changes:** sets `phase = starting`. Starts 4 instances of the new release in the new colour's target group. The listener is not touched. Records `instances_started_at`. This starts the **10-minute deadline** that covers steps 7 and 8 together.
  - **If it fails:** if the 4 instances are not started and registered within the deadline, go to the abort procedure below.

- [ ] **7. Health gate**
  - **Starts it:** step 6.
  - **Changes:** sets `phase = gating`. Every 10 seconds the pipeline calls `/healthz` on each instance and keeps a count of consecutive passes per instance. A failed check resets that instance's count to 0. The gate passes when all 4 instances have 3 consecutive passes.
  - **If it fails:** if the gate has not passed by the deadline (10 minutes after `instances_started_at`), go to the abort procedure below.

- [ ] **8. Smoke tests**
  - **Starts it:** step 7 passing.
  - **Changes:** runs the smoke test suite against the new instances. No user traffic is involved.
  - **If it fails:** a failed smoke test aborts straight away, without waiting for the deadline. It is not retried. If the suite has not finished by the deadline from step 6, go to the abort procedure below.

- [ ] **9. Switch the traffic (one step)**
  - **Starts it:** steps 7 and 8 both passed inside the deadline.
  - **Changes:** a single call repoints the public listener from the old target group to the new one. The pipeline reads the listener back to confirm it. Then it sets `phase = switched` and `switched_at = now`. Call this time T.
  - **If it fails:** if the call fails, retry up to 3 times, reading the listener back each time. If the pipeline still cannot confirm that the listener points at the new group, it uses the abort procedure below. This is safe because the old target group is still running. If the listener did move but the record was not written, a re-run of the job sees the listener on the new colour and finishes the write.

- [ ] **10. Watch the 5xx rate (T to T+15 min)**
  - **Starts it:** step 9.
  - **Changes:** nothing. Every minute, from T+5 to T+15, the pipeline computes the 5xx rate over the trailing 5-minute window. The rate is 5xx responses divided by all responses from the new target group, taken from the load balancer's metrics. A window with no requests is not a breach. Because only complete windows are checked, the first check is at T+5.
  - **If it fails:** if any window is above 1%, go to step 11 straight away. If the metrics are unavailable, the pipeline alerts and keeps retrying. It does not treat missing data as a pass.

- [ ] **11. Automatic rollback (only if step 10 breached)**
  - **Starts it:** a breach in step 10.
  - **Changes:** sets `phase = rolling_back`. Repoints the listener to the old target group, reads it back to confirm, then sets `phase = rolled_back`. It then stops the new colour's 4 instances. Migrations are not reversed. The old release keeps working because the migrations are additive. The deploy is marked failed and the pipeline alerts. The lock is released. The release stays on `main`, and the next merge deploys normally.
  - **If it fails:** if the old colour is not healthy or the repoint fails, retry 3 times and then page the on-call engineer. This is the one case that needs a person immediately.

- [ ] **12. Hold the old colour (until T+30 min)**
  - **Starts it:** step 10 finishing without a breach. The hold itself started at T.
  - **Changes:** nothing. The old colour keeps running untouched. The `catalog-web-rollback` job is allowed during this time. It uses the conditional write to set `phase = rolling_back`. It then repoints the listener to the old colour as in step 11, sets `rolled_back` and stops the new colour. The main deploy job sees the new phase and exits.
  - **If it fails:** a failed repoint is retried 3 times and then pages on-call, as in step 11.

- [ ] **13. Shut down the old colour**
  - **Starts it:** the time reaching T+30 min with `phase = switched`.
  - **Changes:** a conditional write sets `phase = succeeded`, and only the job that wins that write continues. If the rollback job got there first, this step does nothing. The winner stops the old colour's 4 instances. From now on a rollback is a normal deploy of the previous release. The `catalog-web-rollback` job refuses to run and tells the engineer to deploy the previous release through the pipeline. That deploy runs steps 2 to 13. Its step 5 does nothing, because the previous release's migrations are already applied.
  - **If it fails:** if some instances do not stop, the pipeline alerts and retries. The deploy still counts as `succeeded`, because the new release is serving. Step 3 of the next deploy stops any left-over instances.

- [ ] **14. Close the deploy**
  - **Starts it:** step 13, or any final phase.
  - **Changes:** writes the final `phase`, releases the lock, and lets the next queued run start.
  - **If it fails:** the lock is released by the pipeline's own timeout. The record is checked at the start of the next deploy in step 3.

## Abort procedure (steps 6 to 9, before traffic moves)

Triggered by: the 10-minute deadline passing, a smoke test failing, or the listener change not being confirmed.

1. Set `phase = aborted`.
2. Stop the new colour's instances.
3. Do not touch the listener. The old colour was serving the whole time.
4. Fail the pipeline, alert, and release the lock.

Migrations stay applied. That is safe because they are additive.

## Failure summary

| Failure point | Who serves traffic afterwards | Final phase |
|---|---|---|
| Steps 2 to 4 | Old colour | no deploy |
| Step 5 (migration) | Old colour | `migration_failed` |
| Steps 6 to 8 (start, health, smoke, deadline) | Old colour | `aborted` |
| Step 9 (switch not confirmed) | Old colour | `aborted` |
| Step 10 (5xx above 1%) | Old colour (rolled back) | `rolled_back` |
| Step 12 (engineer rollback) | Old colour (rolled back) | `rolled_back` |
| After step 13 | New colour; rollback is a normal deploy of the previous release | `succeeded` |

## Open choices I made that you may want to change

- Deploys are serialized, so a merge can wait up to about 45 minutes.
- Smoke tests run against instance addresses, not through the load balancer.
- There is no minimum request count for the 5xx check, so a very quiet window can breach on a handful of errors.
- After a rollback the new colour is stopped immediately, not kept for debugging.