# Blue-green deploys for `catalog-web`: procedure

Every step below is a pipeline job. Nobody runs deploy steps by hand. The only manual action is an engineer starting a rollback job (see "Rollback jobs").

## Terms and decisions

- **Old** is the colour serving traffic when the run starts. **New** is the other colour. After a rollback, the colours swap roles.
- The new colour is normally shut down, with 0 instances, when a deploy starts. The old colour of the previous deploy is shut down 30 minutes after its switch.
- **One deploy at a time.** A run holds the lock from step 1 to step 14, about 40 to 50 minutes. If a run didn't hold the lock for the full 30-minute window, a new deploy would overwrite the idle colour that a rollback needs.
- **"Fails" means** the pipeline run stops, marks itself failed, and posts to the team's deploy alert channel. Each step says what is left behind.
- **Smoke tests and health checks** call the new instances directly by their private addresses (all 4 of them), never through the public listener. That keeps the new release off public traffic.
- **The 10-minute clock** starts when the pipeline issues the start request for the new instances (step 6).
- **The 5xx rate** is 5xx responses divided by all responses, from the new target group's load balancer metrics. It counts only requests after the switch. A window with no requests is not a breach. There is no minimum request count, because you didn't ask for one.

## Where deploy state is kept

| State | Kept in | Why |
|---|---|---|
| Which colour is live | The load balancer's public listener, read fresh every time | It is the only authority, so it cannot drift. Nothing caches it. |
| Release SHA per colour, status (`live`, `candidate`, `retired`), `switched_at` | Tags on each colour's target group, written by the pipeline | They survive pipeline runs and are readable by rollback jobs and by a resumed run. |
| Deploy lock and queue | A pipeline concurrency group, `catalog-web-deploy` | A waiting run is replaced by a newer merge. |
| Timers (10-minute gate, 15-minute watch, 30-minute hold) | Held in the running job, computed from timestamps (`switched_at` in the tags, the start time in the run) | A resumed run can recompute where it was. |
| Applied migrations | The migration tool's own table in PostgreSQL | It is the only record of what was applied. |

There is no separate deploy-state database or table. A table in the shared PostgreSQL would tie deploys to the database being up and would need a migration of its own.

## Checklist

- [ ] **1. Merge to `main` starts the run and takes the lock**
  - **Starts when:** a merge to `main` completes.
  - **Changes:** nothing in the system. The run takes the `catalog-web-deploy` lock. If another run holds it, including during that run's 30-minute hold, this run waits. If a newer merge arrives while it waits, the older waiting run is cancelled and the newest one proceeds.
  - **If it fails:** nothing has changed.

- [ ] **2. Build, test, publish the release**
  - **Starts when:** the lock is held.
  - **Changes:** builds `catalog-web` and the migration bundle, runs the unit tests, and publishes one immutable artifact tagged with the commit SHA. Nothing is deployed.
  - **If it fails:** the deploy stops. Nothing has changed in any environment.

- [ ] **3. Read the current state and check it is sane**
  - **Starts when:** step 2 passes.
  - **Changes:** nothing. The run reads the listener to find the live colour and takes the other as new. It reads the tags on both target groups. It requires that the live target group is tagged `status=live` with a release, and that the new colour has 0 running instances. Stray instances in the new colour (left by a failed earlier cleanup) are stopped first.
  - **If it fails:** if the listener points at neither target group, or the tags disagree with the listener, the deploy stops and pages. Nothing is changed or guessed.

- [ ] **4. Check the migrations are additive**
  - **Starts when:** step 3 passes.
  - **Changes:** nothing. A static check lists the migrations not yet applied and rejects anything other than new tables, nullable columns (or columns with defaults), and indexes. Drops, renames, type changes, and NOT NULL without a default are rejected.
  - **If it fails:** the deploy stops before the database is touched.

- [ ] **5. Apply migrations, once**
  - **Starts when:** step 4 passes. No instance of the new release has started yet.
  - **Changes:** runs the new release's migration bundle against PostgreSQL, one transaction per migration, under the migration tool's database lock. It applies only the migrations not yet recorded as applied. If none are pending, it does nothing and passes. This step changes the shared database.
  - **If it fails:** the deploy stops. The new release is never started, and the live colour keeps serving unchanged. Migrations that already committed in this step stay applied. They are additive, so the live release is unaffected, and the next deploy continues from them. A failed migration rolls back its own transaction. Pages the owner.

- [ ] **6. Start the new release in the idle colour**
  - **Starts when:** step 5 passes.
  - **Changes:** starts 4 instances of the new release in the new colour and registers them in its target group. Sets the new target group's tag to `status=candidate`, `release=<sha>`. Records the start time. The deadline is 10 minutes after this.
  - **If it fails:** if fewer than 4 instances start before the deadline, go to **Abort**.

- [ ] **7. Health gate: three consecutive passes per instance**
  - **Starts when:** the instances are registered (step 6).
  - **Changes:** nothing. Every 10 seconds the run checks `/healthz` on each of the 4 instances. Each instance needs 3 passes in a row, and one failed check resets that instance's count to 0. The step passes when all 4 are at 3 or more at the same time. The fastest possible pass is about 30 seconds.
  - **If it fails:** if this isn't achieved by the deadline, go to **Abort**.

- [ ] **8. Smoke test suite**
  - **Starts when:** step 7 passes.
  - **Changes:** runs the full smoke suite against the new instances. It runs once, with no retry. The suite hits the shared database, so it must be read-only or clean up after itself. It must complete before the deadline, and a suite still running at the deadline is killed.
  - **If it fails:** any failed test, or running past the deadline, goes to **Abort**.

- [ ] **Abort (from step 6, 7 or 8)**
  - **Starts when:** the new release did not pass both gates within 10 minutes of the start request.
  - **Changes:** the public listener is not touched. The 4 new instances are deregistered and stopped, and the new target group's tag is set to `status=failed`. The run ends as failed and pages. The migrations from step 5 stay applied.
  - **If it fails:** if stopping the instances fails, retry 3 times, then page. The next run's step 3 stops any stray instances.

- [ ] **9. Last check before the switch**
  - **Starts when:** step 8 passes.
  - **Changes:** nothing. The run confirms that the listener still points at the old target group, that all 4 new instances passed `/healthz` within the last 10 seconds, and that the deadline has not passed.
  - **If it fails:** if any check fails, go to **Abort**. If the listener has moved by itself, stop and page without touching anything else.

- [ ] **10. Switch: repoint the public listener (one step)**
  - **Starts when:** step 9 passes.
  - **Changes:** a single listener update from the old target group to the new one, conditional on the listener still pointing at the old one. There is no gradual shift. On success the run writes `switched_at` (T0) to both target groups. It sets the new group to `status=live` and the old group to `status=old`, `retire_at=T0+30min`. It reads the listener back to confirm.
  - **If it fails:** the update is a single call, so on an error the listener is unchanged. If the outcome is unknown (timeout), read the listener before doing anything. Retry up to 3 times. If it still fails, go to **Abort**. The old colour is still live and serving.

- [ ] **11. Watch the 5xx rate for 15 minutes (T0 to T0+15)**
  - **Starts when:** the switch is confirmed in step 10.
  - **Changes:** nothing, unless there is a breach. Every minute the run evaluates the trailing 5-minute window of post-switch traffic, beginning when the first full 5 minutes exist (T0+5). It then continues until T0+15.
  - **If it fails:** a window above 1% triggers **11a**. If the metrics can't be read for 3 consecutive minutes, treat that as a breach, because a release nobody is watching shouldn't stay live. If the run itself dies during the watch, the pipeline retries it automatically. The retry re-reads `switched_at` from the tags, re-evaluates the metrics it can still see, and carries on. If it can't resume, it pages.

- [ ] **11a. Automatic rollback (only on a breach)**
  - **Starts when:** step 11 sees a breach.
  - **Changes:** repoints the listener from the new target group back to the old one, conditional on it still pointing at the new one. Sets the tags (old group `live`, new group `rolled_back`). The old colour was untouched, so no start is needed. After the repoint is confirmed, the 4 instances of the failed colour are stopped. **Migrations are never reversed.** The run ends as failed, skips steps 12 and 13, and pages with the 5xx figures.
  - **If it fails:** retry the repoint 3 times, then page as an incident. If the old colour has fewer than 4 healthy instances, still roll back and say so in the page.

- [ ] **12. Hold the old colour untouched (T0 to T0+30)**
  - **Starts when:** step 11 finishes with no breach, and the clock keeps running from T0.
  - **Changes:** nothing. The old colour keeps its 4 instances, with no scaling and no deploys (the lock is still held). Throughout this window an engineer-started rollback job can repoint the listener at the old colour.
  - **If it fails:** an engineer rollback during the hold is handled by that job. If the run dies during the hold, it is retried and resumed from the tags, as in step 11.

- [ ] **13. Shut down the old colour (T0+30)**
  - **Starts when:** the 30 minutes have passed.
  - **Changes:** re-reads the listener. If the old target group is still not live, its 4 instances are deregistered and stopped, and its tag is set to `status=retired` (with its `release`). If the listener has been rolled back in the meantime, the old colour is now the live one and is skipped.
  - **If it fails:** retry 3 times, then page. The deploy is still counted as done, since traffic is on the new release. A running old colour doesn't block the next deploy, because step 3 stops stray instances in the idle colour.

- [ ] **14. Record and release the lock**
  - **Starts when:** step 13 ends, or step 11a, or Abort ends the run.
  - **Changes:** the run marks the tags final, reports the outcome (deployed, aborted, or rolled back) and releases the lock. The next queued run can start.
  - **If it fails:** the lock expires with the run. A stuck lock is released by an engineer from the pipeline UI, after checking the listener against the tags.

## Rollback jobs

Both are pipeline jobs. Neither reverses migrations.

- **Rollback while the old colour is still running (up to T0+30).**
  - **Starts when:** an engineer starts the "rollback catalog-web" job. It runs outside the deploy lock and may overlap the hold in step 12.
  - **Changes:** repoints the listener from the live target group to the other one, conditional on the listener still pointing where the job expects, so two rollbacks at once result in only one change. It then stops the colour that was just taken out of service, as in 11a. The job checks the old colour is still running. If it has been shut down, it refuses.
  - **If it fails:** the job fails and the listener is unchanged. If the old colour has been shut down, the job refuses and points the engineer to the next job.
- **Rollback after the old colour is shut down.**
  - **Starts when:** an engineer starts the "deploy catalog-web" job with the previous release's SHA. The previous SHA is the `release` tag on the retired target group.
  - **Changes:** a normal deploy, steps 1 and 3 to 14, with the build in step 2 skipped. Migrations from the newer release stay applied, and the old release runs on them because migrations are additive. The migration tool has to ignore migrations it doesn't know about, so step 5 is a no-op.
  - **If it fails:** the same abort and rollback rules apply.

## Open for you to confirm

- **No minimum request count** for the 1% rule. A very quiet service could trip on a handful of requests.
- **Metrics unavailable counts as a breach** after 3 minutes.
- **One deploy at a time**, including the 30-minute hold. This makes frequent merges queue.
- **The failed colour is stopped immediately** after a rollback or abort, so it can't be inspected. Its logs and metrics are unaffected.
