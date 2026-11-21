# catalog-web blue-green deploy

Today `catalog-web` is restarted in place. This replaces that with a blue-green deploy: CI builds the release, migrates the shared database, starts it on the idle colour, tests it, moves all traffic to it in one step, watches it, and later shuts down the old colour. It is shaped this way so the old colour stays intact as an instant way back until the new release has proved itself.

The CI pipeline runs this automatically when something is merged to `main`. Nobody runs deploy steps by hand, except the manual rollback job described in step 10. All deploy state lives in the load balancer (LB) and the CI system. Nothing new is stored.

## Terms

- **Blue and green**: the two environments of `catalog-web`, a stateless HTTP service. Each has 4 instances. One colour is live and the other is idle.
- **Target group**: the LB's list of instances for one colour. There is one per colour.
- **Public listener**: the LB's public entry point. It points at exactly one target group at a time.
- **Test listener**: a second LB listener that is not public and points only at the idle colour. Tests use it to reach the new release without user traffic.
- **Old colour / new colour**: the colour that was live before this deploy, and the colour this deploy starts.
- **Deploy lock**: the CI concurrency group for `catalog-web` deploys. Only one deploy job holds it at a time.
- **Shared database**: one PostgreSQL database used by both colours. There is one copy of the data.

## Steps

Each step is done by the deploy job unless it says otherwise.

- [ ] **1. Get the deploy lock.** Starts when the job starts after a merge to `main`. If another deploy holds the lock, this one waits in the queue. The job holds the lock for the whole deploy, including the 30-minute wait in step 10. The next merge's deploy therefore waits until teardown. This is intended: the old colour is the rollback target until it is torn down, so the next deploy must not reuse it before then. CI releases the lock when the job ends, even on failure or cancellation. Set the CI job timeout to at least 60 minutes (up to about 10 minutes of checks, 30 minutes of waiting, plus build and migrations).
- [ ] **2. Work out live / idle colour.** Read which target group the public listener points at. That colour is live and the other is idle. The LB is the only record. If the read fails, stop.
- [ ] **3. Build image + migration lint.** Build the release image. The lint checks that the new migrations in this release contain only additive changes (new tables, nullable columns, indexes). If the build or lint fails, stop. Nothing has changed yet.
- [ ] **4. Run migrations (additive only, indexes built concurrently).** The job runs them once against the shared database, before any new instance starts. They are additive only, so the live colour keeps working on the migrated schema. Dropping or renaming a column or table waits for a later release, after the release still using it has been retired. The runner skips migrations already recorded as applied, so a deploy after a rollback does not re-run them. There is no migration time limit of its own (the brief sets none); the CI job timeout applies. If a migration fails or the job times out, the deploy stops, the new release never starts and the live colour keeps serving. Migrations are never reversed, including by rollback.
- [ ] **5. Deploy new release to idle colour (4 instances).** First stop any instances still in the idle target group. They are left over from an earlier deploy that was cancelled, died or never reached teardown. The live colour is never touched. Then start 4 instances of the new image in the idle target group. The 10-minute limit shared by steps 6 and 7 starts when the instances start.
- [ ] **6. Health checks.** Every 10 seconds, call `/healthz` on each new instance. All 4 must pass 3 times in a row. Step 7 starts only after that.
- [ ] **7. Smoke tests via test listener.** Run the existing smoke test suite against the test listener, so it reaches only the new colour. The new release gets no user traffic until steps 6 and 7 have both passed. If a test fails, or the 10 minutes from step 5 run out (stop the run if it is still going), abort: stop the new instances, leave the public listener untouched, and end the job as failed. The idle colour is left empty for the next deploy.
- [ ] **8. Switch the LB to the new colour.** Repoint the public listener from the old target group to the new one in a single step. There is no gradual shift. The switch time is now. If the repoint fails or its result is unclear, re-read the listener. If it still points at the old colour, abort as in step 7. If it points at the new colour, the switch happened: carry on as if it had succeeded.
- [ ] **9. Watch 5xx for 15 min, roll back if it spikes.** The 15 minutes and the 30 minutes in step 10 both start at the switch. The watch ends inside that window. Read the 5xx rate of the new target group from the LB's own metrics: the share of requests that returned 5xx. There is no minimum request count, and a window with zero requests counts as 0%, so a very quiet period can neither trigger a rollback nor hide one. Check once a minute, starting 5 minutes after the switch, so each check covers a full 5-minute window. If the rate is above 1% over that window, or the metrics cannot be read (health cannot be confirmed), roll back automatically (see Rollback below).
- [ ] **10. Keep old colour up for the rollback window.** The old colour stays running, untouched, for 30 minutes after the switch. This is longer than the 15-minute watch. From minute 15 to 30 nothing watches 5xx automatically (the brief asks for a 15-minute watch only). If errors rise then, an engineer has to notice and start the manual rollback. While waiting, the job rechecks the listener before each 5xx check in step 9 and before teardown. If it no longer points at the new colour, an engineer rolled back: the job does what an automatic rollback does after repointing (see Rollback).
- [ ] **11. Tear down old colour.** At 30 minutes the job stops the 4 instances of the old colour. Both target groups stay, and the old one is now the empty idle colour for the next deploy. After this, any rollback is a normal deploy of the previous release.
- [ ] **12. Release the lock.** The job ends here and CI frees the lock.

## Rollback

A rollback points the public listener back at the old colour. It never reverses migrations. While the old colour is running, both kinds of rollback do this. Once it is shut down, any rollback is a normal deploy of the previous release.

- **Automatic** (step 9): the job repoints only if the listener still points at the new colour. If it already points at the old one, someone else has rolled back and the job leaves the listener alone. Then it stops the new colour's instances and waits until they are stopped. It skips teardown because the old colour is live again, ends as failed and releases the lock. The failed job is the alert; it relies on whatever notification CI already sends for failed jobs.
- **Manual**: an engineer starts it as a pipeline job and gives it the new colour as input. It does not need the lock, because it only repoints the listener. If the listener points at that new colour, it repoints it at the other target group (the old colour), and refuses if the old colour is already shut down. If the listener no longer points at the new colour, it does nothing. So a manual and an automatic rollback at the same moment both aim at the old colour, and the listener ends there. The deploy job then notices in step 10 and cleans up as above.

## When things fail

| Where | What happens |
|---|---|
| Steps 2 to 3 | Stop. Nothing has changed. |
| Step 4 | Deploy stops. New release never starts. Live colour keeps serving. |
| Steps 6 to 7, or 10-minute limit | Abort: stop the new instances, public listener untouched. |
| Stopping instances fails | The job still ends as failed and releases the lock. The next deploy clears leftovers from its idle colour (step 5). |
| Step 8 | Re-read the listener to learn which colour is live; abort or carry on (step 8). |
| Steps 9 to 10 | Rollback, as above. |
| Job dies or is cancelled | Nothing extra runs (see below). |

If the job itself dies or is cancelled, nothing extra runs. This includes the CI system's maximum job duration being hit or the runner being reclaimed during the 30-minute wait. The listener still records which colour is live. An engineer can still run the manual rollback while the old colour is up. The next deploy clears leftover instances from its idle colour before starting.

Cost: if the job died after the switch but before teardown, the lock is released at once. The next deploy then treats the old colour as idle and stops its instances, so the rollback target is lost early. The listener alone cannot show that the idle colour was still wanted. An engineer who needs it must roll back before the next deploy starts. Otherwise the way back is a normal deploy of the previous release.

## Open questions

- What `/healthz` checks and what the smoke suite covers is not specified here; use the existing ones.
- If `CREATE INDEX CONCURRENTLY` fails it can leave an invalid index. Whether the next deploy cleans it up is undecided.
- The exact LB metric and query for the 5xx rate, the migration tool that records applied migrations, and the migration lint tool are not chosen.
- Whether CI is already set up to notify someone when a deploy job fails is not known.
- The CI system's real maximum job duration and runner behaviour are not known; the 60-minute figure is a minimum to configure, not a checked fact.
