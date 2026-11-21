# catalog-web blue-green deploy

Today `catalog-web` is restarted in place. This procedure replaces that with blue-green deploys. The CI pipeline starts on every merge to `main`, applies additive database migrations, starts the new release on the idle colour, and proves it healthy while it gets no user traffic. It then repoints the public listener to the new colour in one step and watches errors for 15 minutes. It keeps the old colour running for 30 minutes so a rollback is just a repoint. Nobody runs deploy steps by hand.

## Terms

- **catalog-web**: a stateless HTTP service. It runs as two environments, blue and green, with 4 instances each.
- **Live colour**: the colour whose target group the public listener forwards to. **Idle colour**: the other one, which is not serving users.
- **Target group**: the load balancer's list of instances for one colour. There is one per colour.
- **Public listener**: the load balancer's user-facing entry point. It forwards to exactly one target group at a time.
- **Test listener**: an internal-only listener on the same load balancer, not reachable by users. The pipeline points it at the idle colour's target group so it can test the new release without touching the public listener. (Decided: added for this procedure.)
- **`/healthz`**: the health endpoint each instance serves.
- **Smoke test suite**: a short set of end-to-end checks run against the new release.
- **Additive migration**: a schema change that only adds things (new tables, nullable columns, indexes), so the release now serving traffic keeps working after it.
- **Deploy lock**: a CI concurrency group named `catalog-web-deploy`. Only one run can hold it, and later runs wait in the queue. (Decided: the lock is CI's, so no new lock service is needed.)

## Where state is kept

There is no separate deploy-state store. (Decided: keep state in places that already exist.)

- Which colour is live: the public listener's target. This is the source of truth.
- Whether the old colour is still running: whether its instances exist.
- Which release each colour runs: a `release` tag on its instances.
- Which deploy holds the lock: CI.
- Timers (the 10-minute, 15-minute and 30-minute clocks): the running pipeline job.
- Data: one shared PostgreSQL database used by both colours. There is only one copy.

## Steps

Each step starts when the one before it succeeds. If a step fails, follow the failure table below.

- [ ] **1. Take the deploy lock.** Starts on a merge to `main`. Changes nothing yet. The lock is held until step 10, because the old colour must stay untouched for 30 minutes and cannot be the target of the next deploy.
- [ ] **2. Work out the colours.** Read the public listener's target. That colour is live; the other is idle. The idle colour is the target of this deploy.
- [ ] **3. Build and lint.** Build the image for the merged commit. A migration lint then rejects any migration that drops or renames a column or table, or that is not additive. Dropping or renaming happens in a later release, after the release that still uses the old column has been retired. Changes nothing in production.
- [ ] **4. Run migrations, once.** Apply the migrations to the shared database before any instance of the new release starts. They must be additive only. Indexes are built with `CREATE INDEX CONCURRENTLY` so that writes are not blocked. This changes the database.
- [ ] **5. Start the new release on the idle colour.** Replace all 4 idle instances with the new image and tag them with the release. Point the test listener at the idle colour's target group. The 10-minute clock for step 6 starts when the instances start.
- [ ] **6. Prove the new release healthy.** Every instance must pass `/healthz` three times in a row (checked every 10 seconds). Then the smoke test suite must pass against the new release through the test listener. Both must be done within 10 minutes of the instances starting. The new release gets no user traffic until both are done.
- [ ] **7. Switch traffic.** Repoint the public listener from the old target group to the new one, in one step. There is no gradual shift. The 15-minute and 30-minute clocks start now.
- [ ] **8. Watch for 15 minutes.** Every minute, read the new colour's 5xx rate over the last 5 minutes. (Decided: the rate comes from the load balancer's metrics for the target group.) If it goes above 1% in any 5-minute window, roll back automatically (see Rollback).
- [ ] **9. Hold the old colour until 30 minutes after the switch.** Leave it running and untouched, so a rollback stays a repoint.
- [ ] **10. Tear down and release.** First check that the public listener still points at the new colour. If it does, shut down the old colour's instances. If it does not (a rollback happened), leave both colours as they are. Then release the lock.

## Rollback

- A rollback points the public listener back at the old colour. It never reverses migrations, which is safe because they are additive.
- The automatic rollback runs from step 8. An engineer can also start a rollback as a pipeline job at any time in the 30 minutes. That job does not wait for the deploy lock, because the deploy holds it until step 10. (Decided: this is the only exception to the lock.)
- After a rollback, the pipeline leaves the failed new colour running for investigation. The next deploy replaces it. The deploy that was running ends at step 10 without tearing anything down.
- Once the old colour has been shut down, any rollback is a normal deploy of the previous release.

## What happens when a step fails

In every case below, the pipeline releases the lock and alerts the engineers who own the deploy.

| Step | Failure | What happens |
|---|---|---|
| 1 | Lock is held | The run waits in the queue. It is not cancelled. |
| 2 | Listener cannot be read | Stop. Nothing has changed. |
| 3 | Build or lint fails | Stop before any migration. The live colour keeps serving. |
| 4 | Migration fails | The deploy stops. The new release is never started. The live colour keeps serving. |
| 5 | Instances do not start | Treated as step 6 failing: abort. |
| 6 | Health checks or smoke tests not done in 10 minutes | Abort without touching the public listener. Shut down the new instances. Migrations stay, since they are additive and the live release still works. |
| 7 | Repoint call fails | Retry once. If it still fails, abort. A single repoint either happens or does not, so the listener is never half-switched. |
| 8 | 5xx above 1% | Automatic rollback. |
| 8 | Rollback repoint fails | Alert for an immediate manual rollback job. The old colour is still running. |
| 9 | Pipeline job dies or is cancelled | CI frees the lock. Both colours stay running. The next run re-reads the listener (step 2), so it needs no saved state. An engineer shuts down the old colour. |
| 10 | Teardown fails | Alert. The live colour is unaffected. |

## Open questions

- Who receives the alerts, and through which channel? Not decided here.
- Does the smoke test suite already exist? It is assumed to, and this document does not define its contents.
