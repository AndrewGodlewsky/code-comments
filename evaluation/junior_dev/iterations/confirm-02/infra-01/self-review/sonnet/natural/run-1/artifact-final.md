# Blue-green deploys for `catalog-web`: procedure

## How it works in brief

`catalog-web` is a stateless HTTP service. It runs as two identical environments, **blue** and **green**, with 4 instances each. A load balancer has one public **listener** that forwards user traffic to exactly one **target group** (the set of instances for one colour) at a time. The colour the listener points at is **live**. The other colour is **idle**.

A deploy starts the new release on the idle colour and tests it while it gets no user traffic. If it passes, the listener is repointed to the new colour in one step. The old colour keeps running for a while, so going back is just repointing the listener again.

Both colours share one PostgreSQL database, so schema changes must be additive only (new tables, nullable columns, indexes). That way the old release still works on the migrated schema. Dropping or renaming a column or table happens in a later release, after the release that still uses it has been retired.

Deploys run only from CI, when something is merged to `main`. Nobody runs deploy steps by hand.

Terms used below:

- **old colour**: the colour that was live when the deploy began. **new colour**: the idle colour being deployed to.
- **T**: the moment the listener is repointed to the new colour (step 9). T+15 and T+30 mean 15 and 30 minutes after T.
- **Alert**: the pipeline pages the on-call engineer.
- **Final phase**: one of `succeeded`, `rolled_back`, `aborted` or `migration_failed`.
- **Abort procedure**: the short clean-up routine defined after the checklist. It is used when a deploy fails before traffic has moved.
- **Conditional write**: a write to the state object that succeeds only if the object has not changed since it was read. If two jobs try at once, only one wins.

## Decisions and where state lives

- **Which colour is live** is never stored. The pipeline reads it from the load balancer's public listener each time.
- **The idle colour has 0 running instances.** Steps 11, 12 and 13 and the abort procedure stop instances so this stays true. Step 3 repairs it if an earlier failure left instances running.
- **Deploy record.** One JSON object, `deploys/catalog-web/state.json`, in the pipeline's state bucket. Every write is a conditional write, so two jobs cannot both change it.
  - Fields: `deploy_id`, `release` (commit SHA), `old_colour`, `new_colour`, `phase`, `instances_started_at`, `switched_at`, `migration_version`.
  - `phase` is one of: `migrating`, `starting`, `gating`, `switched`, `rolling_back`, `rolled_back`, `aborted`, `migration_failed`, `succeeded`.
  - All timers (the 10-minute deadline, T+15, T+30) are computed from timestamps in this record, not kept in a job's memory.
- **Migrations applied** are tracked by the migration tool in a table in the PostgreSQL database. That is the only deploy state in the database.
- **One deploy at a time.** All `catalog-web` deploy runs share one pipeline concurrency group (a CI setting that lets only one run in the group execute at a time). It acts as the lock. A run holds it from step 2 until step 14. A merge that arrives meanwhile waits in the queue. If several are waiting, only the newest runs and the rest are marked superseded.
  - Why serialise: the old colour must be shut down (step 13) before it can be the next deploy's idle target.
  - Cost: a merge can wait up to about 45 minutes.
- **One long-running job.** The deploy runs as one pipeline job from step 3 to step 14. If it crashes, re-running it resumes from `phase` in the record instead of starting over. Every step is safe to repeat.
- **Smoke tests** (a quick end-to-end test suite) run directly against the new instances' addresses, not through the load balancer.
- **Rollback is a pipeline job.** It is a manual-trigger job named `catalog-web-rollback`, and it is the only way an engineer rolls back. It is allowed from T until step 13 shuts down the old colour.

## Checklist

Steps are in the order they happen. Each says what starts it, what it changes, and what happens if it fails.

- [ ] **1. Merge to `main`**
  - **Starts it:** a merge to `main`.
  - **Changes:** nothing yet. The pipeline run is queued in the deploy concurrency group.
  - **If it fails:** not applicable. If another deploy holds the lock, this run waits.

- [ ] **2. Build, test, and check the migrations**
  - **Starts it:** the run reaching the front of the queue (it now holds the lock).
  - **Changes:** builds the release image tagged with the commit SHA and pushes it to the registry. Runs unit tests. Runs a migration check that rejects anything not additive: `DROP`, `RENAME`, a `NOT NULL` column without a default, or a type change.
  - **If it fails:** the run stops and releases the lock. No deploy record is created and nothing is deployed.

- [ ] **3. Check the starting state**
  - **Starts it:** step 2 passing.
  - **Changes:** reads the live colour from the listener and sets `old_colour` to it. The other colour is `new_colour`. Reads `state.json`: the previous deploy must be in a final phase. If the new colour still has running instances left from an earlier failure, stops them. This is safe because the listener does not point at them. (If this is a re-run of a crashed job, it instead resumes from the existing record's `phase`.)
  - **If it fails:** if the listener and the record disagree, the previous deploy is not in a final phase, or the old colour does not have 4 healthy instances, the run stops, alerts and releases the lock. A person fixes it, because the pipeline cannot tell which side is right.

- [ ] **4. Write the deploy record**
  - **Starts it:** step 3 passing.
  - **Changes:** writes `state.json` with a new `deploy_id`, the release, both colours and `phase = migrating`.
  - **If it fails:** the run stops, alerts and releases the lock. Nothing else has changed.

- [ ] **5. Apply the schema migrations (once)**
  - **Starts it:** step 4 passing.
  - **Changes:** a single job runs the release's pending migrations against the shared database. Each migration runs in its own transaction, and the tool also takes a database advisory lock so two runs cannot migrate at once. If nothing is pending, this step does nothing. On success it records `migration_version`. Timeout: 15 minutes.
  - **If it fails:** `phase = migration_failed`. No instance of the new release is started, and the old colour keeps serving. The failing migration rolls back. Any earlier migration in the same run stays applied, which is harmless because all are additive. The pipeline alerts and releases the lock.

- [ ] **6. Start the new colour**
  - **Starts it:** step 5 succeeding.
  - **Changes:** sets `phase = starting`. Starts 4 instances of the new release in the new colour's target group. The listener is not touched. Records `instances_started_at`, which starts the **10-minute deadline**. The deadline covers steps 6 to 8 together.
  - **If it fails:** if the 4 instances are not all started and registered by the deadline, go to the abort procedure.

- [ ] **7. Health gate**
  - **Starts it:** step 6.
  - **Changes:** sets `phase = gating`. Every 10 seconds the pipeline calls `/healthz` on each new instance and counts consecutive passes per instance. A failed check resets that instance's count to 0. The gate passes when all 4 instances have 3 consecutive passes.
  - **If it fails:** if the gate has not passed by the deadline (10 minutes after `instances_started_at`), go to the abort procedure.

- [ ] **8. Smoke tests**
  - **Starts it:** step 7 passing.
  - **Changes:** runs the smoke test suite against the new instances. No user traffic is involved.
  - **If it fails:** a failed test goes to the abort procedure straight away, with no retry and no waiting for the deadline. If the suite has not finished by the deadline, also go to the abort procedure.

- [ ] **9. Switch the traffic (one step)**
  - **Starts it:** steps 7 and 8 both passed within the deadline.
  - **Changes:** a single call repoints the public listener from the old target group to the new one. The pipeline reads the listener back to confirm. Then it sets `phase = switched` and `switched_at = now` (this is T).
  - **If it fails:** if the call fails, retry up to 3 times, reading the listener back each time. If the listener still is not confirmed on the new group, go to the abort procedure. This is safe because the old colour is still running. If the listener did move but the record was not written, a re-run of the job sees the listener on the new colour and finishes the write.

- [ ] **10. Watch the 5xx rate (T to T+15 min)**
  - **Starts it:** step 9.
  - **Changes:** nothing. Every minute from T+5 to T+15, the pipeline computes the 5xx rate over the trailing 5-minute window: 5xx responses divided by all responses from the new target group, taken from the load balancer's metrics. Only complete windows are checked, so the first check is at T+5. A window with no requests is not a breach. Before each check the job also reads `phase`. If an engineer's rollback has changed it, the job exits.
  - **If it fails:** if any window is above 1%, go to step 11 immediately. If the metrics are unavailable, the pipeline alerts and keeps retrying. Missing data is never treated as a pass.

- [ ] **11. Automatic rollback (only if step 10 found a breach)**
  - **Starts it:** a breach in step 10.
  - **Changes:** sets `phase = rolling_back`. Repoints the listener to the old target group and reads it back to confirm. Sets `phase = rolled_back`. Stops the new colour's 4 instances. Migrations are not reversed; the old release works on the migrated schema because migrations are additive. The deploy is marked failed, the pipeline alerts, and the lock is released. The release stays on `main`, and the next merge deploys normally.
  - **If it fails:** if the old colour is unhealthy or the repoint fails, retry 3 times, then page the on-call engineer. This is the one case that needs a person immediately.

- [ ] **12. Hold the old colour (T to T+30 min)**
  - **Starts it:** step 9. It runs alongside step 10 and continues after it if step 10 finds no breach.
  - **Changes:** nothing by default: the old colour keeps running untouched. During this time an engineer may start `catalog-web-rollback`. That job uses a conditional write to set `phase = rolling_back`, repoints the listener to the old colour as in step 11, sets `rolled_back`, and stops the new colour. The main deploy job sees the new phase and exits, and the rollback job releases the lock.
  - **If it fails:** a failed repoint is retried 3 times, then pages on-call, as in step 11.

- [ ] **13. Shut down the old colour**
  - **Starts it:** the time reaching T+30 min with `phase = switched`.
  - **Changes:** a conditional write sets `phase = succeeded`, and only the job that wins that write continues. If the rollback job won first, this step does nothing. The winner stops the old colour's 4 instances.
    - From now on, rolling back means a normal deploy of the previous release. `catalog-web-rollback` refuses to run and tells the engineer to do that.
    - That deploy runs steps 2 to 14. Its step 5 does nothing, because the previous release's migrations are already applied.
  - **If it fails:** if some instances do not stop, the pipeline alerts and retries. The deploy still counts as `succeeded`, because the new release is serving. Step 3 of the next deploy stops any left-over instances.

- [ ] **14. Close the deploy**
  - **Starts it:** step 13, or any final phase reached earlier (including the abort procedure and failures in steps 5 and 11).
  - **Changes:** writes the final `phase`, releases the lock, and lets the next queued run start.
  - **If it fails:** the pipeline's own timeout releases the lock. The next deploy's step 3 checks the record.

## Abort procedure (steps 6 to 9, before traffic moves)

Triggered by: the 10-minute deadline passing, a smoke test failing, or the listener change not being confirmed.

1. Set `phase = aborted`.
2. Stop the new colour's instances.
3. Do not touch the listener. The old colour was serving the whole time.
4. Fail the pipeline, alert, and release the lock (step 14).

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

- Deploys are serialised, so a merge can wait up to about 45 minutes.
- Smoke tests run against instance addresses, not through the load balancer.
- There is no minimum request count for the 5xx check, so a very quiet window can breach on a handful of errors.
- After a rollback the new colour is stopped immediately, not kept for debugging.