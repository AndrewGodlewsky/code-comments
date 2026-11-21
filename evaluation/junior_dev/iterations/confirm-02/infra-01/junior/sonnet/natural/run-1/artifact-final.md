# Blue-green deploys for `catalog-web`: procedure

`catalog-web` is a stateless HTTP service. Today it is restarted in place. This procedure replaces that with blue-green deploys. The service runs as two environments, **blue** and **green**, with 4 instances each. One is live and the other is idle. Behind one load balancer, a public listener forwards to exactly one colour's target group at a time. Both colours share one PostgreSQL database.

A deploy starts when a merge to `main` completes. The pipeline applies additive database migrations, starts the new release in the idle colour, and proves it healthy without public traffic. It then moves all traffic in one step by repointing the listener, and watches errors for 15 minutes. The old colour stays running for 30 minutes so that a rollback is only a repoint. This shape keeps the live release serving until the new one is proven, and keeps rollback cheap.

Every step is a pipeline job. Nobody runs deploy steps by hand. The only manual action is an engineer starting a rollback job (see "Rollback jobs").

## Terms

- **Listener**: the load balancer's public listener. It decides which target group gets user traffic.
- **Target group**: the load balancer's list of one colour's instances. Each colour has one.
- **Old** is the colour serving traffic when the run starts. **New** is the other colour, always simply the opposite of the listener.
- **Migration**: a database schema change. The migration tool keeps its own table of applied migrations.
- **Tags**: key/value labels on each target group, written by the pipeline. Fields: release SHA, `status` (`live`, `candidate`, `old`, `retired`, `failed`, `rolled_back`) and `switched_at`. `old` is a label for humans only; no step reads it.
- **T0** is the time of the switch (step 10), stored as `switched_at`.
- **The deadline** is 10 minutes after the start request in step 6. The health gate and the smoke suite share this one budget.
- **Health check**: the pipeline job calls `/healthz` on an instance's private address. A pass is HTTP 200 within 5 seconds. Health checks and smoke tests call all 4 new instances directly, never through the listener, so the new release gets no public traffic before the switch. The pipeline runner is assumed to reach those addresses.
- **5xx rate** for a window is the count of 5xx responses divided by the count of all responses. Both counts are read each minute from the new target group's load balancer metrics, using only datapoints from T0 onward. A window with no requests is not a breach. There is no minimum request count, because none was asked for.
- **Breach**: one evaluation, at any minute check, where the trailing 5-minute window is above 1%. It does not need to repeat.
- **"Fails"** means the pipeline run stops, marks itself failed, and posts to the team's deploy alert channel (a page).

## Rules that apply to the whole deploy

- **One deploy at a time.** A run holds the lock from step 1 to step 14, about 40 to 50 minutes. Without the full 30-minute hold under the lock, a new deploy would overwrite the idle colour that a rollback needs.
- **Which colour is live** is read fresh from the listener every time. It is the only authority. Nothing caches it.
- **Tags on the idle colour are never trusted.** Whatever they say, step 3 ignores them and step 6 overwrites them. Only the live group's tags are checked.
- **Migrations are additive only**: new tables, nullable columns (or columns with defaults), and indexes. Dropping or renaming a column or table happens in a later release, once the release that still uses it has been retired. A rollback never reverses migrations.
- **Where state is kept:**

| State | Kept in | Why |
|---|---|---|
| Live colour | The listener | Cannot drift. |
| Release SHA, status, `switched_at` | Tags on each target group | Survive pipeline runs. Readable by rollback jobs and by a resumed run. |
| Deploy lock and queue | Pipeline concurrency group `catalog-web-deploy` | A waiting run is replaced by a newer merge. |
| Timers (10-minute deadline, 15-minute watch, 30-minute hold) | Computed from timestamps (`switched_at` in the tags, the start time in the run) | A resumed run recomputes where it was. |
| Applied migrations | The migration tool's own table in PostgreSQL | The only record of what was applied. |

There is no separate deploy-state table. A table in the shared PostgreSQL would tie deploys to the database being up and would need a migration of its own.

## Checklist

- [ ] **1. Merge to `main` starts the run and takes the lock**
  - **Starts when:** a merge to `main` completes.
  - **Changes:** nothing in the system. The run takes the `catalog-web-deploy` lock. If another run holds it, including during that run's 30-minute hold, this run waits. If a newer merge arrives while it waits, the older waiting run is cancelled (the platform reports it as cancelled) and the newest proceeds. No change is lost: `main` is one line of history, so the newest merge contains every earlier one.
  - **If it fails:** nothing has changed.

- [ ] **2. Build, test, publish the release**
  - **Starts when:** the lock is held.
  - **Changes:** builds `catalog-web` and the migration bundle, runs the unit tests, and publishes one immutable artifact tagged with the commit SHA. Nothing is deployed.
  - **If it fails:** the deploy stops. Nothing has changed in any environment.

- [ ] **3. Read the current state and check it is sane**
  - **Starts when:** step 2 passes.
  - **Changes:** nothing, except on the very first deploy, when no target group has tags yet: the live group is then tagged `status=live`, `release=unknown`. The run reads the listener to find the live colour and takes the other as new. It requires that the live group is tagged `status=live` with a release, and that the new colour has 0 running instances. The new colour is normally shut down at this point. Stray instances there (left by a failed earlier cleanup) are stopped first, then the count is checked again.
  - **If it fails:** if the listener points at neither target group, or the live group's tags disagree with the listener, the deploy stops and pages. If stray instances will not stop, the deploy stops and pages. Nothing else is changed or guessed.

- [ ] **4. Check the migrations are additive**
  - **Starts when:** step 3 passes.
  - **Changes:** nothing. A static check lists the migrations not yet recorded as applied and rejects anything other than additive changes. Drops, renames, type changes, and NOT NULL without a default are rejected. This is what keeps the old release working on the migrated schema: it never meets a required column or a missing one.
  - **If it fails:** the deploy stops before the database is touched.

- [ ] **5. Apply migrations, once**
  - **Starts when:** step 4 passes. No instance of the new release has started yet.
  - **Changes:** runs the new release's migration bundle against PostgreSQL, one transaction per migration, under the migration tool's database lock. That lock is assumed to be a PostgreSQL advisory lock that stops two runs migrating at once, released when the connection ends, so a run that dies mid-step does not block the next. Only migrations not recorded as applied are run. If none are pending, the step passes doing nothing. This step changes the shared database.
  - **If it fails:** the deploy stops. The new release is never started and the live colour keeps serving. The failed migration rolls back its own transaction. Migrations that already committed stay applied, and since they are additive the live release is unaffected. The next deploy's steps 4 and 5 see only the unrecorded ones. Pages the owner, naming the failed migration.

- [ ] **6. Start the new release in the idle colour**
  - **Starts when:** step 5 passes.
  - **Changes:** the pipeline sends a start request to the platform's instance launcher, naming the step 2 artifact SHA. This starts the 10-minute deadline. The launcher starts 4 instances of that release in the new colour and registers them in its target group. The pipeline overwrites the new group's tags with `status=candidate`, `release=<sha>` and records the start time. The old group's tags are untouched: it stays `live` until step 10.
  - **If it fails:** if fewer than 4 instances start before the deadline, go to **Abort**.

- [ ] **7. Health gate: three consecutive passes per instance**
  - **Starts when:** the instances are registered (step 6).
  - **Changes:** nothing. Every 10 seconds the pipeline job health-checks each of the 4 instances. Each needs 3 passes in a row, and one failed check resets that instance's count to 0. The step passes when all 4 are at 3 or more at the same time. The fastest possible pass is about 30 seconds.
  - **If it fails:** if this is not achieved by the deadline, go to **Abort**.

- [ ] **8. Smoke test suite**
  - **Starts when:** step 7 passes.
  - **Changes:** runs the full smoke suite against the 4 new instances, once, with no retry. It gets only the time left before the deadline, and a suite still running at the deadline is killed. The suite hits the shared database, so it must be read-only or clean up after itself.
  - **If it fails:** any failed test, or running past the deadline, goes to **Abort**.

- [ ] **Abort (from step 6, 7, 8 or 10)**
  - **Starts when:** the new release did not pass both gates within the deadline, or step 10 failed with the listener confirmed still on the old group.
  - **Changes:** the listener is not touched. The 4 new instances are deregistered and stopped, and the new group is tagged `status=failed` (kept until the next deploy's step 6 overwrites it). The run ends as failed and pages. The page lists the step 5 migrations, which stay applied, and says the database is ahead of the live release.
  - **If it fails:** if stopping the instances fails, retry 3 times, then page. The next run's step 3 stops any stray instances.

- [ ] **9. Last check before the switch**
  - **Starts when:** step 8 passes.
  - **Changes:** nothing. The smoke suite may have taken minutes, so the run makes a fresh health check of all 4 new instances (it does not reuse step 7). It also confirms the listener still points at the old group and the deadline has not passed.
  - **If it fails:** a failed check goes to **Abort**. If the listener has moved by itself, stop and page without touching anything else. The 4 new instances are left running, and the page says so. The engineer decides what to stop, following "When a page arrives". No new deploy starts until the tags agree with the listener.

- [ ] **10. Switch: repoint the public listener (one step)**
  - **Starts when:** step 9 passes.
  - **Changes:** a single listener update from the old group to the new one, conditional on the listener still pointing at the old one (the load balancer API is assumed to support this). There is no gradual shift. On success the run writes `switched_at` (T0) to both groups, sets the new group `status=live` and the old group `status=old`, and reads the listener back to confirm.
  - **If it fails:** a failed call leaves the listener unchanged. If the outcome is unknown (timeout), read the listener before doing anything, and before each retry. If it points at the new group, the switch worked: carry on. Retry up to 3 times. If it still fails and the listener is confirmed on the old group, go to **Abort**. If the condition fails because the listener moved by itself, stop and page without touching anything else.

- [ ] **11. Watch the 5xx rate for 15 minutes (T0 to T0+15)**
  - **Starts when:** the switch is confirmed in step 10. The new instances now get public traffic.
  - **Changes:** nothing, unless there is a breach. Every minute the run evaluates the trailing 5-minute window of post-switch traffic, beginning when the first full 5 minutes exist (T0+5), until T0+15.
  - **If it fails:** a breach triggers **11a**. If the metrics cannot be read for 3 consecutive minutes, treat that as a breach, because a release nobody is watching should not stay live.

- [ ] **11a. Automatic rollback (only on a breach)**
  - **Starts when:** step 11 sees a breach.
  - **Changes:** repoints the listener back to the old group, conditional on it still pointing at the new one. Tags the old group `live` and the new group `rolled_back`. The old colour was untouched, so nothing needs starting. After the repoint is confirmed, the 4 instances of the failed colour are stopped. The run ends as failed, skips steps 12 and 13, and pages with the 5xx figures.
  - **If it fails:** retry the repoint 3 times, then page as an incident. If the old colour has fewer than 4 healthy instances, still roll back and say so in the page. If the condition fails because an engineer's rollback job already moved the listener back, read the listener, confirm it is on the old group, and carry on with the tags and stopping the failed colour, which write the same values the job wrote.

- [ ] **12. Hold the old colour untouched (T0 to T0+30)**
  - **Starts when:** step 11 finishes with no breach. The clock keeps running from T0.
  - **Changes:** nothing. The old colour keeps its 4 instances, with no scaling and no deploys (the lock is still held). An engineer-started rollback job can repoint the listener at it during this window.
  - **If it fails:** an engineer rollback is handled by that job. If the run itself dies, see "If a run dies".

- [ ] **13. Shut down the old colour (T0+30)**
  - **Starts when:** 30 minutes have passed since `switched_at`.
  - **Changes:** re-reads the listener. If the old group is still not live, its 4 instances are deregistered and stopped, and it is tagged `status=retired` (keeping its `release`). If an engineer's rollback job has moved the listener back, the old colour is live again and is skipped, and the run ends as rolled back in step 14. After this step any rollback is a normal deploy of the previous release.
  - **If it fails:** retry 3 times, then page. The deploy still counts as done, since traffic is on the new release. A leftover old colour does not block the next deploy, because step 3 stops stray instances in the idle colour.

- [ ] **14. Record and release the lock**
  - **Starts when:** step 13, step 11a or Abort ends the run.
  - **Changes:** reports the outcome (deployed, aborted, or rolled back) and releases the lock, so the next queued run can start. Tags are already final, since each earlier step writes its own. If the tags show a `rolled_back` group, the outcome is rolled back, whoever did it.
  - **If it fails:** the lock expires with the run. An engineer can release a stuck lock from the pipeline UI after checking the listener against the tags.

## If a run dies

The pipeline's automatic job retry restarts the same run, which keeps the lock (assumed, not verified). The retry reads the listener and the tags, then decides:

- Listener on the old group: the switch never happened. Restart from step 3, which stops any stray instances.
- Listener on the new group but no `switched_at` on the new group (the run died between the switch and the tag write): write `switched_at` as now and use it as T0. This is later than the true switch, so the watch runs slightly longer, which is safe. Resume at step 11.
- Listener on the new group with `switched_at` under 15 minutes ago: resume at step 11. Under 30 minutes: step 12. Otherwise: step 13.
- If it cannot decide, it pages.

## Rollback jobs

Both are pipeline jobs. Neither reverses migrations.

- **Rollback while the old colour is still running (up to T0+30).**
  - **Starts when:** an engineer starts the "rollback catalog-web" job. It runs outside the deploy lock and may overlap the hold in step 12.
  - **Changes:** repoints the listener from the live group to the other one, conditional on the listener still pointing where the job expects, so two rollbacks at once produce only one change. The job writes the tags as 11a does (restored group `live`, the group taken out of service `rolled_back`) and stops the colour it took out of service. That group ends with 0 instances and a `rolled_back` tag, which the next deploy ignores and overwrites. The still-running deploy run sees this at step 13 and ends as rolled back. The job first checks the old colour is still running.
  - **If it fails:** the listener is unchanged. If the old colour has been shut down, the job refuses and points the engineer to the next job. If the condition fails because 11a or another rollback already moved the listener, the job changes nothing, reports "already rolled back" and exits.
- **Rollback after the old colour is shut down.**
  - **Starts when:** an engineer starts the "deploy catalog-web" job with the previous release's SHA, which is the `release` tag on the retired target group.
  - **Changes:** a normal deploy, steps 1 and 3 to 14, with the build in step 2 skipped. It reuses the artifact already published for that SHA and goes through the same health gate and smoke tests as any deploy. Migrations from the newer release stay applied, and the old release runs on them because migrations are additive. Its own migrations were applied long ago, so step 4 finds nothing pending. The migration tool must ignore migrations it does not know about, so step 5 does nothing.
  - **If it fails:** the same abort and rollback rules apply.

## When a page arrives

Check the listener first, then compare the tags against it. The listener is the truth, and the tags are fixed to match it. Do not start a deploy until they agree.

## Open for you to confirm

- **No minimum request count** for the 1% rule. A very quiet service could trip on a handful of requests.
- **Metrics unavailable counts as a breach** after 3 minutes.
- **One deploy at a time**, including the 30-minute hold. This makes frequent merges queue.
- **The failed colour is stopped immediately** after a rollback or abort, so it cannot be inspected. Its logs and metrics are unaffected.

## Open questions

- Which tool launches the instances in step 6, and how it fetches the artifact, is not known.
- What the smoke suite contains and how long it takes is not known.
- Who is paged, and who "the owner" is, is not known. Someone must name the alert channel's recipients.
- Whether the platform's job retry keeps the concurrency lock is assumed, not verified.
- Whether the migration tool's lock is released when a run dies is assumed, not verified.
- Whether the pipeline runner can reach the instances' private addresses is assumed, not verified.
- Whether the load balancer's listener update can be made conditional is assumed, not verified.
