# catalog-web blue-green deploy

This document is the procedure for deploying `catalog-web` without restarting the live instances. The steps run in order, from a merge to `main` until the deploy is finished. CI runs every step. Nobody runs them by hand, except the rollback job that an engineer can start during the rollback window (step 11).

This document assumes an AWS Application Load Balancer (ALB). The ALB is the single entry point for user traffic. It accepts requests and passes each one to a target group.

## Terms

- **Instance**: one running copy of the service.
- **Colour**: one of two identical sets of 4 instances, **blue** or **green**. The **live** colour receives all user traffic. The **idle** colour receives none. The two colours swap roles at each deploy.
- **Target group**: the ALB's list of instances for one colour.
- **Listener**: an entry point on the ALB that accepts requests and forwards them to one target group. A listener's **forward target** is the target group it currently sends requests to.
- **Public listener**: the listener users reach. Its forward target is the live target group.
- **Test listener**: a second, private listener on the same ALB. Its forward target is the idle target group, so smoke tests can reach the new release while users cannot.
- **Release**: one built version of the service, identified by its image tag (the commit SHA).
- **Candidate release**: the new release that the current deploy is trying to put live.
- **Migration**: a script that changes the shared PostgreSQL database schema. Both colours use the same database.
- **/healthz**: an endpoint each instance answers to report that it is ready to serve.
- **Smoke suite**: a set of end-to-end checks run against a release to confirm its main paths work.
- **5xx**: an HTTP response with a status code of 500 or above, meaning the server failed.
- **Lock**: the CI concurrency group `catalog-web-deploy`. CI allows one holder at a time, and other runs queue behind it.
- **Deploy state**: a record of what is live and what can be rolled back to. It is described under Decisions and under "Where deploy state is kept".
- **Rollback target**: the colour and release that a rollback would restore. It is the old colour and release, or none.
- **Rollback window**: the 30 minutes after the switch, during which the old colour is still running and can take traffic back.
- **T**: the moment of the switch in step 9.

## Decisions

- **Deploy state** is one record in AWS Systems Manager Parameter Store, a key-value store. It holds the live colour and release, the rollback target (colour and release, or none), the status of the candidate release, the switch time T, and the rollback window end (T+30). It is kept outside the shared database, so the lock and the state do not depend on database health, and migrations never change it.
- **Lock**: a run holds the lock from step 1 until its watch ends or it aborts. An automatic rollback in step 10 releases the lock when it finishes. The lock is always released before the rollback window opens, so the teardown job can take it. A run that finds a rollback window open does not keep the lock while it waits. It releases the lock, waits, and starts again at step 1 once the window has closed and teardown has finished.
- **Migration lint** is a check on the migration files, run before anything is deployed. It rejects any migration that:
  - drops, renames, or changes the type of a column or table;
  - adds a `NOT NULL` column without a default;
  - sets `NOT NULL` on an existing column;
  - creates an index on an existing table without `CONCURRENTLY`.
- **Traffic floor**: a 5-minute window with fewer than 100 requests is not judged. The engineer is alerted if a whole watch passes with no window judged.
- **Smoke failure** aborts the deploy at once. It does not wait for the 10-minute limit.
- **Rollback outcome**: after any rollback, automatic or manual, the old colour is live again, the candidate release is marked failed, the rollback target is cleared, and the rollback window closes. No teardown is left to run. Migrations are never reversed by a rollback.

## Steps

- [ ] **1. Take the deploy lock and read state**
  - **Starts when**: a merge to `main`.
  - **Does**: waits for the lock and takes it. Then reads deploy state. If a rollback window is open, the run releases the lock, waits without holding it, and starts again from step 1 once the window has closed and teardown (step 12) has finished.
  - **If it fails**: the run stops. Nothing has changed.

- [ ] **2. Work out the live and idle colours**
  - **Starts when**: step 1 completes.
  - **Does**: reads the forward target of the public listener, and compares the target group it names with the `live` colour in deploy state. The colour the listener forwards to is live. The other colour is idle. This step changes nothing.
  - **If it fails**: if the listener and the state disagree, or the idle colour still has running instances, the run stops and alerts. Nobody guesses which colour is live.

- [ ] **3. Build the image and lint the migrations**
  - **Starts when**: step 2 completes.
  - **Does**: builds the release image, tags it with the commit SHA, and pushes it to the image registry. Then checks the migration files against the lint rules in Decisions.
  - **If it fails**: the run stops. Nothing has been deployed. A lint failure needs a code fix.

- [ ] **4. Run the migrations once**
  - **Starts when**: step 3 passes.
  - **Does**: runs all pending migrations once, as a single one-off job, before any new instance starts. Every migration must be additive: new tables, nullable columns, and indexes. Indexes are built with `CREATE INDEX CONCURRENTLY`, so the live colour keeps reading and writing during the build. The live release uses only things that already exist, so it keeps working on the migrated schema.
  - **If it fails**: the deploy stops here. The new release is never started, and the live colour keeps serving. Migrations that already succeeded stay in place. That is safe because they are additive. A concurrent index build that fails is left marked INVALID. The job drops it before exiting, so the next run can build it again. Nothing is rolled back automatically. The fix is a new forward migration.

- [ ] **5. Start the new release on the idle colour**
  - **Starts when**: step 4 completes.
  - **Does**: starts 4 instances of the new image and registers them in the idle target group. That target group is not behind the public listener, so no user reaches these instances. Deploy state records the new release as the candidate, with status in progress. The 10-minute limit starts when the first instance starts.
  - **If it fails**: an instance that cannot start, or keeps restarting, is not repaired by this step. The 10-minute clock keeps running, and step 8 applies if the gates do not pass in time.

- [ ] **6. Health gate**
  - **Starts when**: each instance starts. Its checks begin then.
  - **Does**: checks `/healthz` on each of the 4 instances every 10 seconds. An instance passes after 3 passes in a row. A failed check resets its count to zero. The gate passes when all 4 instances have passed.
  - **If it fails**: if the gate has not passed within 10 minutes of the first instance starting, go to step 8.

- [ ] **7. Smoke tests through the test listener**
  - **Starts when**: the health gate passes. Smoke tests never run against instances that are not yet ready.
  - **Does**: runs the full smoke suite against the idle colour through the test listener. The health gate and the smoke suite must both pass within 10 minutes of the first instance starting.
  - **If it fails**: any failed test goes to step 8 at once.

- [ ] **8. Abort without touching users**
  - **Starts when**: a smoke test fails, or 10 minutes pass after the first instance started without both the health gate and the smoke suite passing.
  - **Does**: removes the 4 new instances from the idle target group and stops them. The public listener is not touched. Deploy state marks the candidate release as failed. The lock is released, and the engineer is alerted. The migrations from step 4 stay, since they are additive.
  - **Result**: the live colour kept serving throughout.

- [ ] **9. Switch the public listener to the new colour**
  - **Starts when**: both gates have passed. Just before switching, each of the 4 new instances is checked on `/healthz` once more.
  - **Does**: makes one change to the public listener. It changes the listener's forward target from the old target group to the new one. There is no gradual shift. Deploy state records the new colour as live, the old colour and release as the rollback target, and the switch time T.
  - **If it fails**: the listener change is a single API call, so it either applies fully or not at all. If the listener change is refused, the run stops and alerts. The old colour is still live. If the final check finds an instance unhealthy, the deploy goes to step 8 instead of switching.

- [ ] **10. Watch 5xx for 15 minutes; roll back if it spikes**
  - **Starts when**: the switch in step 9 completes (time T).
  - **Does**: once a minute, computes the share of 5xx responses over the most recent 5 minutes of traffic served by the new colour. Only traffic after T counts, so the windows in the first 5 minutes cover only the time since T. Windows with fewer than 100 requests are not judged. If the whole watch passes with no window judged, the engineer is alerted.
  - **If any judged window goes above 1%**: roll back automatically.
    - Repoint the public listener's forward target to the old target group.
    - Stop the 4 new instances, so the next deploy starts from a clean idle colour. Do this only after the listener has been repointed.
    - Record the rollback in deploy state, as described in Decisions.
    - Migrations are not reversed.
    - If the listener change is refused, retry it. If it keeps failing, alert the engineer. The new colour stays live, the old colour keeps running, and no instances are stopped while the listener still points at the new colour.
  - **If 15 minutes pass with no judged window above 1%**: the watch ends at T+15. The lock is released, and the deploy moves to step 11.

- [ ] **11. Keep the old colour for the rollback window (T+15 to T+30)**
  - **Does**: the old colour keeps running and is not changed. Deploy state keeps the rollback target recorded and the rollback window open until T+30. New deploy runs wait at step 1, without holding the lock, until the window closes.
  - **Manual rollback**: during this window, an engineer can start a rollback job in the pipeline. The job takes the lock, repoints the public listener's forward target to the old target group, stops the new colour's instances, and records the rollback as described in Decisions. It has the same retry and alert rules as the automatic rollback in step 10. While the watch is still running, the lock is held by the deploy, so the job waits. In practice the job can start from T+15.

- [ ] **12. Tear down the old colour at T+30**
  - **Starts when**: a scheduled teardown job runs at T+30. The job takes the lock first.
  - **Does**: reads deploy state first.
    - If there is no rollback target, a rollback has already happened. The job does nothing more and releases the lock.
    - Otherwise, it checks that the public listener still forwards to the new colour's target group. If it does not, the job stops and alerts without changing anything.
    - If the listener forwards to the new colour, the job removes the old colour's instances from their target group and stops them. Only after the instances are confirmed stopped does it clear the rollback target and close the window. It then releases the lock.
  - **If it fails**: the job retries. The public listener is not touched. The rollback target stays recorded until the old instances are confirmed stopped, so a rollback stays possible. If retries keep failing, the engineer is alerted, and new deploys keep waiting at step 1.
  - **After this step**: the old colour is gone. A rollback is now a normal deploy of the previous release, meaning the release that was live before the switch. It runs steps 1 to 9 again. The migrations are additive, so the older release still works with the migrated schema.

## Where deploy state is kept

One record in AWS Systems Manager Parameter Store holds:

- the live colour and live release
- the rollback target colour and release, or none
- the candidate release and its status (in progress, failed, or live)
- the switch time T and the rollback window end (T+30)

The lock is the CI concurrency group `catalog-web-deploy`. The state is written only by the deploy, rollback, and teardown jobs, and only while they hold the lock.