# Blue-green deploys for `catalog-web`: deploy procedure

## Decisions this procedure makes

These cover the points the brief left open.

- **Live colour.** The load balancer's public listener is the only source of truth for which colour is live. The deploy state record (below) never overrides it. If the two disagree, the pipeline stops and alerts an engineer.
- **Idle colour.** The idle colour has no running instances between deploys. Step 11 stops the old colour, and a rollback stops the failed colour.
- **One deploy at a time.** A deploy lock (a CI concurrency group named `catalog-web-deploy`) is held from step 2 until the deploy finishes. That includes the 30-minute wait before the old colour is shut down.
  - A merge during that time queues behind the running deploy.
  - Only the newest queued merge runs. Older queued ones are skipped, because the newest includes their changes.
- **Smoke tests do not go through the public listener.** They call the new colour's instances through the new target group's internal addresses, so no user traffic is involved.
- **Release id.** The merge commit SHA of `main` is the release id. A release is a single immutable build artifact (the application image plus its migrations), and the same artifact is used for every step.
- **5xx rate.** The pipeline reads the load balancer's 5xx count divided by its request count for the public listener. It evaluates this every 60 seconds over a rolling 5-minute window.
  - In the first 5 minutes after the switch, the window is "since the switch".
  - A window with fewer than 100 requests is not evaluated. Low traffic cannot trigger a rollback on a handful of errors.
  - Errors the load balancer generates itself count as 5xx.
- **Metric outage.** If the 5xx rate cannot be read for 3 checks in a row, the pipeline alerts an engineer and keeps watching. It does not roll back on missing data.
- **Timers.** Nothing relies on a CI job sleeping. Every deadline is written to the deploy state record, and a job is scheduled for it. A scheduled reaper job (every 5 minutes) also runs any shutdown whose deadline has passed, so a lost timer cannot leave the old colour running.

## Where deploy state is kept

The state is one JSON record, `catalog-web/deploy-state.json`, in the pipeline's versioned artifact storage. It lives outside any CI runner. Every write is a compare-and-set on the record's version. When two jobs try to change the phase at once, such as an automatic rollback and a manual rollback, only one succeeds and the other stops.

The record holds:

| Field | Meaning |
|---|---|
| `phase` | `idle`, `migrating`, `verifying`, `watching`, `soaking`, `done`, `aborted`, `failed`, or `rolled_back` |
| `release` | Release id being deployed |
| `previous_release` | Release id that was live before this deploy |
| `old_colour`, `new_colour` | Colours of the old and new release |
| `instances_started_at` | Start of the 10-minute verification limit |
| `switched_at` | Time of the listener repoint |
| `watch_until` | `switched_at` + 15 minutes |
| `old_colour_shutdown_at` | `switched_at` + 30 minutes |
| `migrations_applied` | Whether step 4 completed |

The database records which migrations have been applied in its own migrations table. The pipeline reads that table to know whether a migration ran. It does not rely on the state record for this.

## The deploy, in order

- [ ] **1. Merge to `main`: build and test the release**
  - **Starts when:** a merge lands on `main`.
  - **Changes:** nothing in any environment. The pipeline builds the release artifact, tags it with the release id, runs unit and integration tests, and checks that every new migration is additive (new tables, nullable columns, indexes only). A migration that drops or renames anything fails this check.
  - **If it fails:** the pipeline stops and notifies the author. No lock is taken and no environment is touched. The live colour keeps serving.

- [ ] **2. Take the deploy lock and read the current state**
  - **Starts when:** step 1 passes.
  - **Changes:** the pipeline takes the deploy lock. It reads which target group the public listener points at and sets `old_colour` to that colour and `new_colour` to the other. It reads the state record and compares the two. It then writes `phase = migrating`, `release`, `previous_release`, and both colours.
  - **If it fails:** if the lock is held, the run queues, and only the newest queued run survives. If the listener and the state record disagree, or the state record's phase is not `idle`, `done`, `aborted`, `failed`, or `rolled_back`, the pipeline stops and alerts an engineer. It changes nothing else. Any other failure at this step also stops the pipeline with the lock released.

- [ ] **3. Make sure the new colour is idle**
  - **Starts when:** step 2 finishes.
  - **Changes:** if the new colour still has running instances (for example, left from a failed earlier deploy), the pipeline stops them and waits for them to leave the target group. It confirms the new colour's target group is empty and is not the public listener's target.
  - **If it fails:** if the instances cannot be stopped, or the new colour's target group is the listener's target, the pipeline sets `phase = failed`, alerts an engineer, releases the lock, and stops. The live colour keeps serving.

- [ ] **4. Apply the database migrations (once)**
  - **Starts when:** step 3 finishes. This step must complete before any instance of the new release starts.
  - **Changes:** a single job runs the release's migrations against the shared database, each in its own transaction. The limit is 10 minutes. It sets `migrations_applied = true`. A release with no new migrations has nothing to apply, and the step records that.
  - **If it fails:** the deploy stops here. A migration that times out counts as failed. The pipeline sets `phase = failed` and alerts the author. No new instance has started and the listener is untouched, so the live colour keeps serving the migrated schema. The pipeline never reverses migrations. Migrations that completed before the failure stay, which is safe because they are additive. The author fixes the migration with a new merge, and migrations must be safe to re-run.

- [ ] **5. Start the 4 instances of the new release on the new colour**
  - **Starts when:** step 4 succeeds.
  - **Changes:** the pipeline starts 4 instances running the release on the new colour and registers them in its target group. The target group receives no traffic, because the public listener does not point at it. It sets `phase = verifying` and `instances_started_at`.
  - **If it fails:** if instances cannot be started, the pipeline continues to step 6, which then fails the deploy. The pipeline does not retry. No instance of the new release is exposed to users.

- [ ] **6. Health gate: every instance passes `/healthz` 3 times in a row**
  - **Starts when:** step 5 starts the instances.
  - **Changes:** nothing. The pipeline checks `/healthz` on each instance every 10 seconds. An instance counts as healthy after 3 consecutive passes, and a failed check resets that instance's count to zero. The gate passes when all 4 instances are healthy at the same time.
  - **If it fails:** if all 4 are not healthy within 10 minutes of `instances_started_at`, the pipeline aborts. It stops the new instances and sets `phase = aborted`. It alerts the author and releases the lock. The public listener is untouched and migrations stay applied.

- [ ] **7. Smoke tests against the new colour**
  - **Starts when:** step 6 passes.
  - **Changes:** nothing. The smoke test suite runs against the new colour's instances through the new target group's internal addresses. The whole verification limit still counts from `instances_started_at`: steps 6 and 7 together must finish within 10 minutes.
  - **If it fails:** a failing test aborts the deploy immediately, with no re-run. Running out of the 10 minutes also aborts. Both follow step 6's abort: stop the new instances, `phase = aborted`, alert, release the lock, and leave the listener untouched.

- [ ] **8. Switch traffic in one step**
  - **Starts when:** step 7 passes. This is the first step that touches the public listener.
  - **Changes:** one API call repoints the public listener from the old target group to the new one. The pipeline reads the listener back to confirm the change, then writes `phase = watching`, `switched_at`, `watch_until = switched_at + 15 min`, and `old_colour_shutdown_at = switched_at + 30 min`. There is no gradual shift.
  - **If it fails:** the pipeline retries the call up to 3 times. If every retry fails and the read-back shows the listener still on the old group, the pipeline treats it as an abort: stop the new instances, `phase = aborted`, alert, release the lock. If the read-back is ambiguous (it cannot be read, or shows an unexpected target), the pipeline does not guess. It alerts an engineer, keeps both colours running, and leaves the lock held.

- [ ] **9. Watch the 5xx rate for 15 minutes (automatic rollback)**
  - **Starts when:** step 8 confirms the switch.
  - **Changes:** nothing unless a rollback happens. A monitor job evaluates the 5xx rate every 60 seconds (see the decisions above). If the rate goes above 1% over any 5-minute window, it starts the automatic rollback (see Rollback paths). If `watch_until` passes with no breach, the pipeline sets `phase = soaking`.
  - **If it fails:** if the monitor job itself fails, it is restarted and resumes from `switched_at`, because it reads its deadlines from the state record. A failed or missing metric read follows the rule in the decisions above. If the rollback itself fails, see Rollback paths.

- [ ] **10. Keep the old colour untouched until `old_colour_shutdown_at`**
  - **Starts when:** step 8 succeeds. It overlaps with step 9.
  - **Changes:** nothing. The old colour keeps running its 4 instances and receives no traffic. Until step 11, either rollback in Rollback paths points the listener back at it.
  - **If it fails:** nothing in this step can fail, because nothing runs. If an old-colour instance dies, the automatic or manual rollback check in Rollback paths finds the old colour unhealthy and refuses to repoint.

- [ ] **11. Shut down the old colour**
  - **Starts when:** the clock reaches `old_colour_shutdown_at` (30 minutes after the switch) and `phase` is still `soaking`. The scheduled job and the reaper both try this step, and only one wins the compare-and-set.
  - **Changes:** the pipeline sets `phase = done`, stops the 4 old instances, and waits for them to leave the old target group. After this, a rollback is a normal deploy of `previous_release` (see Rollback paths). It then releases the deploy lock.
  - **If it fails:** the pipeline retries the shutdown 3 times. If it still fails, it alerts an engineer, and `phase` stays `done` with the failure noted on the record. The deploy lock is held until an engineer confirms the old colour is stopped. The next deploy's step 3 also stops it.

## Rollback paths

These are not steps in the sequence. They apply while step 9 or 10 is running.

- [ ] **Automatic rollback (from step 9)**
  - **Starts when:** the 5xx rate goes above 1% over a 5-minute window.
  - **Changes:** the pipeline first writes `phase = rolled_back`. This blocks step 11 and any other rollback. It checks that all 4 old-colour instances are healthy. It repoints the public listener back to the old target group and reads it back to confirm. It then stops the new colour's instances after the deregistration delay and releases the deploy lock. It alerts the author. The deploy ends there.
  - **Never changes:** migrations. They stay applied.
  - **If it fails:** the pipeline retries the repoint up to 3 times. If it still fails, or an old-colour instance is unhealthy, it pages an engineer straight away. The listener stays on the new colour in that case. The new colour is not stopped while it is the live colour.

- [ ] **Manual rollback while the old colour is running (from step 10)**
  - **Starts when:** an engineer starts the rollback pipeline job during the 30 minutes after the switch.
  - **Changes:** the same as the automatic rollback. The job does nothing and exits if `phase` is already `done`, `rolled_back`, `aborted`, or `failed`. Anything other than `watching` or `soaking` blocks it.
  - **If it fails:** the same as the automatic rollback. If the old colour is unhealthy, the job refuses to repoint. It leaves the listener where it is and tells the engineer to do a normal deploy of `previous_release`.

- [ ] **Rollback after the old colour is shut down (after step 11)**
  - **Starts when:** an engineer merges a revert, or re-runs the pipeline for `previous_release`.
  - **Changes:** this is a normal deploy of the previous release, steps 1 to 12 above. Migrations are not reversed, so the old release runs on the migrated schema.
  - **If it fails:** it fails like any deploy at the failing step.

- [ ] **12. Finish**
  - **Starts when:** step 11 completes, or a rollback path ends the deploy.
  - **Changes:** the pipeline writes the final record and releases the deploy lock. The next queued merge, if any, starts from step 2. After step 11 completes, the live colour is the new colour and the idle colour has no instances.
  - **If it fails:** if the record cannot be written, the pipeline alerts an engineer and does not release the lock. The next deploy waits until the record is checked against the listener.
