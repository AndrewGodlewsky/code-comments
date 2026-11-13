# Deploy checklist: `catalog-web` blue-green

**Terms.** *Live colour*: the colour the public listener forwards to when the run starts. *New colour*: the other colour, which receives the new release. *T*: the moment of the switch in step 8.

**Where state lives**
- Which colour is live: the load balancer's public listener. It is the only lasting record; there is no state file.
- This run's working values: pipeline run variables. CI keeps them for the life of the run and discards them when it ends. Step 2 writes `live_colour` and `new_colour`, step 5 writes `gate_deadline` and step 8 writes `switched_at` (T). Later steps read them to know which colour to act on and when their time limits end.
- Which deploy is running: a CI concurrency group (for example `deploy-catalog-web`). One run holds it and later runs queue.
- Data and schema: the single PostgreSQL database, shared by both colours. Its migration history table records which migrations have been applied.

**Schema rule.** Every migration in a release is additive (new tables, new nullable columns, new indexes), so the live colour keeps working on the migrated schema. A drop or rename ships in a later release, after the release that still used the old column or table has been retired (in step 11 of the deploy that replaced it).

**Failure paths used below**
- **Abort** (before the switch): scale the new colour to 0, so it is idle and empty again. Do not touch the public listener; the live colour keeps serving. Migrations already applied stay applied, which is safe because they are additive. Go to step 12 (failed). If the scale-down fails, alert the team; step 2 of the next deploy scales that colour to 0 before using it.
- **Rollback** (after the switch, until step 11): repoint the public listener to the old colour's target group, scale the new colour to 0 and alert the team. Never reverse a migration. If the repoint call fails, retry it every 10 seconds and page the on-call engineer. The run keeps the deploy slot until the listener is back on the old colour, then goes to step 12 (failed).

---

- [ ] **1. Take the deploy slot**
  - Starts when: a commit is merged to `main` and CI starts a pipeline run.
  - Does: the run joins the concurrency group. If another run holds it, this run waits in the queue. It keeps the slot until step 12, so no second deploy can put its release into the colour this run may still switch back to.
  - On failure: if the run cannot start, or is cancelled while it waits, nothing has changed. A re-run or the next merge starts again here.
- [ ] **2. Find the live colour**
  - Starts when: the run holds the slot.
  - Does: read which target group the public listener forwards to. That colour is live; the other one is the new colour. Write both to run variables. If the new colour still has instances (left by an earlier scale-down that failed), scale it to 0.
  - On failure (load balancer unreachable, or the new colour will not scale to 0): stop; users are unaffected. Go to step 12 (failed).
- [ ] **3. Build and check**
  - Starts when: step 2 completes.
  - Does: build the release image. Find its pending migrations (those not yet in the migration history table) and reject any that drop, rename or change the type of a column or table.
  - On failure: stop; nothing has changed. Go to step 12 (failed).
- [ ] **4. Apply migrations**
  - Starts when: step 3 passes. No instance of the new release exists yet.
  - Does: the pipeline runs one `migrate` task from the new image against the shared database. All pending table and column migrations run in a single transaction, which also writes their rows in the migration history table. Then each new index is built with `CREATE INDEX CONCURRENTLY` outside the transaction, so the build does not block writes from the live colour. Each index is recorded in the history table when its build finishes. Instances never migrate on startup, so migrations run exactly once per deploy.
  - On failure: if the transaction fails, it rolls back and the schema is unchanged. If an index build fails, the task drops the invalid index it left behind. The committed table and column changes stay, which is safe because they are additive, and the unrecorded index migration runs again in the next deploy. Either way, stop: the new colour is never started and the live colour keeps serving. Go to step 12 (failed).
- [ ] **5. Start the new colour**
  - Starts when: step 4 succeeds.
  - Does: start 4 instances of the new release in the new colour's target group. Point the internal test listener (reachable only from CI, for example on port 8443) at that target group. Write `gate_deadline` = now + 10 minutes.
  - On failure: if either call returns an error, Abort. Step 6 catches instances that start and then crash.
- [ ] **6. Health gate**
  - Starts when: step 5 completes. The load balancer checks `/healthz` on each new instance every 10 seconds.
  - Passes when: each of the 4 instances has passed 3 checks in a row.
  - On failure: if `gate_deadline` passes before all 4 have passed, Abort.
- [ ] **7. Smoke tests**
  - Starts when: step 6 passes. The suite runs after the health gate, not alongside it.
  - Does: run the smoke suite through the test listener. Its requests reach the new colour while users stay on the live colour.
  - On failure: if a test fails, or `gate_deadline` passes before the suite finishes, Abort.
- [ ] **8. Switch traffic**
  - Starts when: step 7 passes before `gate_deadline`.
  - Does: repoint the public listener from the old target group to the new one in a single change. All new requests go to the new colour. The old colour keeps running, so requests already in flight there finish. Write `switched_at` = T.
  - On failure: if the call returns an error, read the listener back. If it is still on the old colour, Abort; no user has reached the new release. If it is on the new colour, the switch took effect, so write T and continue.
- [ ] **9. Watch (T to T+15 min)**
  - Starts when: `switched_at` is written.
  - Does: track the public listener's 5xx rate over a rolling 5-minute window. The old colour stays running and unchanged.
  - On failure: if the rate goes above 1%, Rollback automatically. From T onwards, an engineer can also start the pipeline's rollback job, which runs the same Rollback.
- [ ] **10. Hold (T+15 to T+30 min)**
  - Starts when: T+15 passes without a rollback.
  - Does: nothing changes. The automatic watch has ended. The old colour stays running and unchanged, ready to take traffic back.
  - On failure: if a problem is found, an engineer starts the pipeline's rollback job, which runs Rollback.
- [ ] **11. Retire the old colour (at T+30 min)**
  - Starts when: T+30, counted from `switched_at`, passes without a rollback.
  - Does: scale the old colour to 0. There is no fast switch back after this; rolling back means a normal deploy of the previous release through this checklist.
  - On failure: retry 3 times, 1 minute apart. If it still fails, alert the team and go to step 12 (succeeded, with a warning). Users are unaffected because the listener points at the new colour, and step 2 of the next deploy scales this colour to 0 before using it.
- [ ] **12. Finish**
  - Starts when: step 11 completes, or any earlier step stops the run.
  - Does: mark the run succeeded or failed, then release the concurrency group. The run variables are discarded with the run. The next queued run continues from step 2, and the colour left with 0 instances is the one it deploys into.
  - On failure: if a run dies before reaching this step (lost runner, cancellation), CI ends it as failed and releases the group itself.
