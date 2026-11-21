# Blue-green deploys for `catalog-web`: deploy procedure

Today `catalog-web` is restarted in place. This procedure replaces that: CI builds the release, migrates the shared database, starts it on the idle colour, checks it with no user traffic, then moves all traffic in one step by repointing the load balancer. It watches errors for 15 minutes and rolls back automatically if they are too high. Two colours, each with a target group, mean the old release stays untouched as an instant way back.

## Existing system

- `catalog-web` is a stateless HTTP service. It runs as two environments, **blue** and **green**, with 4 instances each. One colour is live; the other is idle.
- One load balancer sits in front. Each colour has a target group. The public listener forwards to exactly one target group at a time.
- Both colours share one PostgreSQL database, so there is one copy of the data.
- CI runs deploys when something is merged to `main`. Nobody runs deploy steps by hand.

## Terms

- **Old colour / new colour:** the colour live before the deploy, and the other one, which gets the new release.
- **Target group:** the load balancer's list of a colour's instances. A colour gets traffic only when the public listener points at its target group.
- **Release id:** the merge commit SHA on `main`. A release is one immutable build artifact (application image plus migrations), used for every step.
- **`/healthz`:** each instance's health endpoint.
- **Smoke tests:** a suite that calls the new colour's instances directly through the new target group's internal addresses, so no user traffic is involved.
- **Deploy lock:** a CI concurrency group named `catalog-web-deploy`. It allows one deploy at a time.
- **Deploy state record:** one JSON record, `catalog-web/deploy-state.json`, described below.
- **Additive migration:** only new tables, nullable columns and indexes.

## Rules that apply to several steps

- **Live colour:** the load balancer's public listener is the only source of truth. The state record never overrides it. If they disagree, the pipeline stops and alerts an engineer.
- **Idle colour:** it has no running instances between deploys. Step 11 stops the old colour, and a rollback stops the failed colour.
- **Queueing:** the lock is held from step 2 until the deploy finishes, including the 30-minute wait before the old colour shuts down. A merge during that time queues. Only the newest queued merge runs, because it contains the older ones' changes.
- **Migrations:** they are applied once per deploy, before any new instance starts, and must be additive. That keeps the release now serving traffic working on the migrated schema. Dropping or renaming a column or table happens in a later release, after the release that uses it is retired. A rollback never reverses migrations.
- **5xx rate:** the load balancer's 5xx count divided by its request count for the public listener, including errors the load balancer generates itself. It is evaluated every 60 seconds over a rolling 5-minute window. In the first 5 minutes after the switch, the window is "since the switch". A window with fewer than 100 requests is not evaluated, so a handful of errors at low traffic cannot trigger a rollback.
- **Metric outage:** if the 5xx rate cannot be read for 3 checks in a row, the pipeline alerts an engineer and keeps watching. It does not roll back on missing data.
- **Timers:** nothing relies on a CI job sleeping. Every deadline is written to the state record and a job is scheduled for it. A reaper job runs every 5 minutes and runs any shutdown whose deadline has passed, so a lost timer cannot leave the old colour running.
- **Nobody retries by hand:** no step is retried unless it says so.

## Where deploy state is kept

The state record lives in the pipeline's versioned artifact storage, outside any CI runner. Every write is a compare-and-set on the record's version. When two jobs try to change the phase at once, such as an automatic and a manual rollback, one succeeds and the other stops.

| Field | Meaning |
|---|---|
| `phase` | `idle`, `migrating`, `verifying`, `watching`, `soaking`, `done`, `aborted`, `failed`, or `rolled_back` |
| `release`, `previous_release` | Release id being deployed, and the one live before |
| `old_colour`, `new_colour` | Colours of the old and new release |
| `instances_started_at` | Start of the 10-minute verification limit |
| `switched_at` | Time of the listener repoint |
| `watch_until` | `switched_at` + 15 minutes |
| `old_colour_shutdown_at` | `switched_at` + 30 minutes |
| `migrations_applied` | Whether step 4 completed |

Whether a migration ran is read from the database's own migrations table, not from this record.

## The deploy, in order

- [ ] **1. Build and test the release**
  - **Starts when:** a merge lands on `main`.
  - **Changes:** nothing in any environment. The pipeline builds the artifact, tags it with the release id, runs unit and integration tests, and checks that every new migration is additive. A migration that drops or renames anything fails.
  - **If it fails:** the pipeline stops and notifies the author. No lock is taken. The live colour keeps serving.

- [ ] **2. Take the deploy lock and read the current state**
  - **Starts when:** step 1 passes.
  - **Changes:** the pipeline takes the lock. It reads which target group the listener points at, sets `old_colour` to that colour and `new_colour` to the other, and compares this with the state record. It then writes `phase = migrating`, `release`, `previous_release` and both colours.
  - **If it fails:** if the lock is held, the run queues (see queueing). If the listener and the record disagree, or `phase` is not one of `idle`, `done`, `aborted`, `failed`, `rolled_back`, the pipeline alerts an engineer and stops, changing nothing else. Any other failure stops the pipeline with the lock released.

- [ ] **3. Make sure the new colour is idle**
  - **Starts when:** step 2 finishes.
  - **Changes:** if the new colour still has instances (for example from a failed earlier deploy), the pipeline stops them and waits for them to leave the target group. It confirms that target group is empty and is not the listener's target.
  - **If it fails:** if the instances cannot be stopped, or the target group is the listener's target, the pipeline sets `phase = failed`, alerts an engineer, releases the lock and stops. The live colour keeps serving.

- [ ] **4. Apply the database migrations, once**
  - **Starts when:** step 3 finishes. It must complete before any new instance starts.
  - **Changes:** one job runs the release's migrations against the shared database, each in its own transaction, with a 10-minute limit. It sets `migrations_applied = true`. With no new migrations it records that there was nothing to apply. Migrations must be safe to re-run.
  - **If it fails:** a timeout counts as failure. The pipeline sets `phase = failed`, alerts the author and stops. No new instance has started and the listener is untouched, so the live colour keeps serving. Migrations that finished before the failure stay, which is safe because they are additive. The author fixes the migration with a new merge.

- [ ] **5. Start 4 instances of the new release on the new colour**
  - **Starts when:** step 4 succeeds.
  - **Changes:** the pipeline starts 4 instances and registers them in the new target group. They get no traffic because the listener does not point there. It sets `phase = verifying` and `instances_started_at`.
  - **If it fails:** the pipeline does not retry. It goes on to step 6, which fails the deploy when the instances never become healthy. No instance is exposed to users.

- [ ] **6. Health gate: every instance passes `/healthz` 3 times in a row**
  - **Starts when:** step 5 starts the instances.
  - **Changes:** nothing. The pipeline checks `/healthz` on each instance every 10 seconds. An instance is healthy after 3 consecutive passes; a failed check resets its count to zero. The gate passes when all 4 are healthy at the same time.
  - **If it fails:** if all 4 are not healthy within 10 minutes of `instances_started_at`, the pipeline aborts: it stops the new instances, sets `phase = aborted`, alerts the author and releases the lock. The listener is untouched and migrations stay applied.

- [ ] **7. Smoke tests against the new colour**
  - **Starts when:** step 6 passes.
  - **Changes:** nothing. The suite runs through the new target group's internal addresses. Steps 6 and 7 together must finish within 10 minutes of `instances_started_at`.
  - **If it fails:** a failing test aborts at once, with no re-run. Running out of the 10 minutes also aborts. Both abort as in step 6.

- [ ] **8. Switch traffic in one step**
  - **Starts when:** step 7 passes. This is the first step that touches the listener.
  - **Changes:** one API call repoints the public listener from the old target group to the new one. There is no gradual shift. The pipeline reads the listener back to confirm, then writes `phase = watching`, `switched_at`, `watch_until` and `old_colour_shutdown_at`.
  - **If it fails:** the pipeline retries the call up to 3 times. If every try fails and the read-back shows the listener still on the old group, it aborts as in step 6. If the read-back is ambiguous (unreadable, or an unexpected target), it does not guess: it alerts an engineer, keeps both colours running and keeps the lock held.

- [ ] **9. Watch the 5xx rate for 15 minutes**
  - **Starts when:** step 8 confirms the switch.
  - **Changes:** nothing unless a rollback happens. A monitor job evaluates the 5xx rate every 60 seconds. If it goes above 1% over any 5-minute window, the automatic rollback starts. If `watch_until` passes with no breach, the pipeline sets `phase = soaking`.
  - **If it fails:** if the monitor job dies, it restarts and resumes from `switched_at`, because its deadlines are in the state record. A failed metric read follows the metric outage rule. A failed rollback is covered under Rollback paths.

- [ ] **10. Keep the old colour running and untouched**
  - **Starts when:** step 8 succeeds. It overlaps with step 9, and lasts until `old_colour_shutdown_at`.
  - **Changes:** nothing. The 4 old instances keep running with no traffic. Until step 11, either rollback points the listener back at them.
  - **If it fails:** nothing runs, so nothing here fails. If an old instance dies, a rollback finds the old colour unhealthy and refuses to repoint.

- [ ] **11. Shut down the old colour**
  - **Starts when:** the clock reaches `old_colour_shutdown_at` (30 minutes after the switch) and `phase` is still `soaking`. The scheduled job and the reaper both try it, and only one wins the compare-and-set.
  - **Changes:** the pipeline sets `phase = done`, stops the 4 old instances and waits for them to leave the old target group. From now on a rollback is a normal deploy of `previous_release`. Then step 12 runs.
  - **If it fails:** the pipeline retries the shutdown 3 times. If it still fails, it alerts an engineer, `phase` stays `done` with the failure noted on the record, and the lock stays held until an engineer confirms the old colour is stopped. The next deploy's step 3 also stops it.

- [ ] **12. Finish**
  - **Starts when:** step 11 completes, or a rollback path ends the deploy.
  - **Changes:** the pipeline writes the final record and releases the lock. The next queued merge, if any, starts from step 2. After step 11 the live colour is the new colour and the idle colour has no instances.
  - **If it fails:** if the record cannot be written, the pipeline alerts an engineer and keeps the lock. The next deploy waits until the record is checked against the listener.

## Rollback paths

These are not steps in the sequence. They apply while steps 9 and 10 run, and afterwards.

- [ ] **Automatic rollback (from step 9)**
  - **Starts when:** the 5xx rate goes above 1% over a 5-minute window.
  - **Changes:** the pipeline first writes `phase = rolled_back`, which blocks step 11 and any other rollback. It checks that all 4 old instances are healthy, repoints the listener to the old target group and reads it back. It then stops the new colour's instances after the deregistration delay, alerts the author and runs step 12's lock release. Migrations stay applied.
  - **If it fails:** the pipeline retries the repoint up to 3 times. If that fails, or an old instance is unhealthy, it pages an engineer at once. The listener stays on the new colour, which is not stopped while it is live.

- [ ] **Manual rollback while the old colour is running (from step 10)**
  - **Starts when:** an engineer starts the rollback pipeline job within the 30 minutes after the switch.
  - **Changes:** the same as the automatic rollback. It runs only when `phase` is `watching` or `soaking`. If `phase` is `done`, `rolled_back`, `aborted` or `failed`, it does nothing and exits.
  - **If it fails:** the same as the automatic rollback. If the old colour is unhealthy, the job leaves the listener where it is and tells the engineer to do a normal deploy of `previous_release`.

- [ ] **Rollback after the old colour is shut down**
  - **Starts when:** an engineer merges a revert, or re-runs the pipeline for `previous_release`.
  - **Changes:** a normal deploy, steps 1 to 12. Migrations are not reversed, so the old release runs on the migrated schema.
  - **If it fails:** it fails like any deploy, at the failing step.

## Open questions

- The length of the load balancer's deregistration delay is not set here. It is whatever the load balancer is configured with.
- Who is alerted for each failure is only partly stated: the author for build, migration, abort and rollback outcomes, an engineer for state disagreements and stuck rollbacks. The alert channel is not chosen.
