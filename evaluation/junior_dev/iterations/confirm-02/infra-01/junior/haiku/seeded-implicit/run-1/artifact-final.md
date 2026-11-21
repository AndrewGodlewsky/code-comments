# catalog-web blue-green deploy

Today every merge to `main` restarts `catalog-web` in place. This procedure deploys the new release to the idle colour, checks it there, and then moves all public traffic to it in one load balancer change. The old colour stays up for 30 minutes after that switch, so a rollback is also one change. Migrations are additive only, so the live release keeps working on the migrated database.

## Terms

- **Colour**: a set of 4 instances of `catalog-web`, called blue or green. The **live** colour takes public traffic. The **idle** colour takes none.
- **Instance**: one running copy of the service.
- **Load balancer**: the service in front of both colours. It routes user requests to the live colour.
- **Target group**: the load balancer's list of one colour's instances.
- **Public listener**: the load balancer port that users reach. It forwards to exactly one target group, the live colour.
- **Test listener**: a second load balancer port, reachable only from CI. Its rule forwards to one target group. The deploy points that rule at the idle group.
- **Health check**: the load balancer calls each instance's `/healthz` every 10 seconds. An instance is healthy after 3 passes in a row.
- **Smoke tests**: the suite that checks the new release through the test listener.
- **Additive change**: a new table, a nullable column or an index. A drop, rename, type change or non-nullable column is not additive.
- **Concurrent index**: an index built without blocking reads and writes on its table. A failed build can leave an invalid index behind.
- **Migration tool**: the program that applies schema changes. It keeps a history table of the ones it has run.
- **Deploy lock**: CI's single-run lock for `catalog-web`. Only one deploy runs at a time.
- **Switch time**: the moment step 10 moves the public listener.
- **Rollback window**: the 30 minutes after the switch time, while the old colour stays up.
- **Rollback**: pointing the public listener back at the old colour.
- **Release tag**: the image tag last deployed to a colour. Once a colour is shut down, its release tag names the previous release, which a normal deploy redeploys after a rollback.

## Steps

The steps run in order, from a merge to `main` to the end of the deploy. Each step says what starts it, what it does, what keeps its data and what happens if it fails.

1. [ ] **Take the deploy lock.**
   - Starts: a merge to `main`.
   - Does: CI takes the deploy lock. A second deploy waits in the queue and does not cancel this run. The lock is held until step 15. That can be up to 30 minutes after the switch, so a queued merge may wait that long. This stops a second deploy from taking the old colour as idle while it is still the rollback target.
   - Keeps: CI.
   - If the run dies: CI releases the lock.

2. [ ] **Clear the non-live colour left by an earlier run.**
   - Starts: after step 1. This wait comes before step 6, so the 10-minute deadline has not started.
   - Does: look at the colour that is not live, and act on its state tag:
     - `rollback-window`, and its switch time is less than 30 minutes ago: wait until 30 minutes have passed since that switch. The lock stays held. The wait lasts at most 30 minutes. Then apply the next case. The wait is there because an engineer may still start a manual rollback (step 13) while the window is open.
     - `rollback-window`, and 30 minutes or more have passed since the switch: shut down its 4 instances and tag it `retired`.
     - Any other non-live colour that still has running instances: shut them down. Leave its tag as it is.
     - Anything else: do nothing.
   - Why this case exists: a normal run never leaves a `rollback-window` colour behind, because step 14 shuts it down. This case comes only from a run that stopped or died during its watch or window, or from a step 14 shutdown that failed.
   - Keeps: the state tags.
   - If a shutdown fails: the deploy stops and reports. Nothing new has started, and the live colour is untouched.

3. [ ] **Find the live and idle colours.**
   - Starts: after step 2.
   - Does: read the target group that the public listener forwards to. That group is live. The other group is idle.
   - Keeps: the load balancer. The listener is the only record of the live colour.
   - If the listener cannot be read: the deploy stops. Nothing has changed.

4. [ ] **Build the image and lint the migrations.**
   - Starts: after step 3.
   - Does: builds the release image from the merged commit. The lint accepts only additive changes: new tables, nullable columns and concurrent indexes. It rejects any drop, rename, type change, non-nullable column or non-concurrent index. Those changes would break the live release, which still reads the old columns and tables. A drop or rename waits for a later release, after the release that uses the old column or table has been retired.
   - Keeps: nothing.
   - If the lint or build fails: the deploy stops before any migration runs. Nothing has changed.

5. [ ] **Run the migrations once.**
   - Starts: when the lint passes, and before any instance of the new release starts.
   - Does: applies the migrations to the shared PostgreSQL database, the only copy of the data. Every migration uses `IF NOT EXISTS`, so a re-run is safe.
   - Keeps: the database, in the migration tool's history table.
   - If a migration fails: the deploy stops. The new release never starts, and the live colour keeps serving. Migrations that already finished stay applied, because rollback never reverses them. To recover, fix the cause, drop any invalid index left by the failed concurrent build, and re-run the deploy.

6. [ ] **Start 4 new instances on the idle colour.**
   - Starts: when step 5 succeeds.
   - Does: starts 4 instances of the new release and joins them to the idle target group. The public listener does not point at them. The test listener's rule is pointed at the idle target group, so the smoke tests can reach them. The 10-minute deadline starts now.
   - Keeps: the image tag, as the `release` tag on the idle target group.
   - If an instance does not become healthy: handled in step 7.

7. [ ] **Wait for health checks.**
   - Starts: after step 6.
   - Does: the load balancer checks each instance's `/healthz`. This passes when all 4 instances are healthy.
   - Keeps: nothing.
   - If not all 4 are healthy within 10 minutes of step 6: go to step 9.

8. [ ] **Run the smoke tests against the test listener.**
   - Starts: when all 4 instances are healthy.
   - Does: runs the smoke suite against the test listener.
   - Passes: the suite passes before the 10-minute deadline.
   - If it fails, or does not finish before the deadline: go to step 9.

9. [ ] **Abort without touching the public listener.**
   - Starts: step 7 or step 8 fails, or misses the deadline.
   - Does: shuts down the 4 new instances, so the idle colour is empty for the next deploy. The public listener and the live colour are unchanged. The idle group's state tag does not change. The test listener is left pointing at the empty idle group, and the next deploy repoints it. Migrations stay applied. Then go to step 15.
   - Keeps: nothing new.
   - If the shutdown fails: the run stops and reports. Step 2 of the next deploy shuts the instances down.

10. [ ] **Switch the public listener.**
    - Starts: only when steps 7 and 8 both pass within the 10-minute deadline.
    - Does: one change. The public listener is repointed from the old target group to the new one. There is no gradual shift. Then the new colour is tagged `live` and the old colour `rollback-window`, both with `switched-at` set to the switch time.
    - Keeps: the listener and the tags.
    - If the listener change is refused: the listener still points at the old colour. Go to step 9.
    - If the listener change succeeds but a tag write fails: retry the tag write. If it still fails, the run stops and reports. Do not move the listener back, because it already points at the new colour and users are on it. No watch runs until the tags are fixed.

11. [ ] **Watch the 5xx rate for 15 minutes.**
    - Starts: at the switch time.
    - Does: every minute, the run reads the load balancer's 5xx count and its total response count. Rate = 5xx responses divided by all responses. A spike is a rate above 1% over any 5-minute window that lies within the 15 minutes after the switch.
    - Before each reading, the run checks that the public listener still points at the new colour. If it does not, an engineer has rolled back (step 13). The run stops the watch, changes nothing, and goes to step 15.
    - Keeps: nothing. The counts are read live.
    - If there is a spike: go to step 12.
    - If the 15 minutes end with no spike, and the listener still points at the new colour: the watch ends and the run goes to step 14. The lock stays held.
    - If the counts cannot be read: do not roll back. Leave the old colour up, stop the run and go to step 15. The old colour keeps its `rollback-window` tag, so step 2 of the next deploy handles it.

12. [ ] **Roll back automatically.**
    - Starts: a spike in step 11.
    - Does, in this order:
      1. Repoint the public listener to the old target group, the reverse of step 10. Skip this if it already points there.
      2. Tag the old colour `live` and the new colour `failed`.
      3. Shut down the new colour's 4 instances.
    - The order means that if the shutdown fails, the tags are already right. Migrations are not touched. Then go to step 15.
    - Keeps: the listener and the tags.
    - If the repoint is refused: the run fails and stops, and an engineer runs step 13.
    - If a tag write fails: retry it, as in step 10.
    - If the shutdown fails: the listener already points at the old colour, and the new colour stays tagged `failed`. The run stops and goes to step 15. Step 2 of the next deploy shuts the instances down.

13. [ ] **Roll back manually (optional).**
    - Starts: an engineer starts it as a separate pipeline job, when they decide to. The procedure does not say when a rollback is advisable. See the open questions.
    - Works only while the old colour is still up, that is, tagged `rollback-window`.
    - Does the same repoint, tags and shutdown as step 12.
    - Does not take the deploy lock, so it can run while a deploy run holds it. A run in step 11, 12 or 14 notices this through the listener checks in those steps, and skips what is already done.
    - Once the old colour is shut down, this job is refused. From then on, a rollback is a normal deploy of the previous release.

14. [ ] **Shut down the old colour 30 minutes after the switch.**
    - Starts: 30 minutes after the switch time. From the end of the watch until then, the run waits, still holding the lock. The old colour stays up and untouched during the wait.
    - Does: before shutting anything down, checks that the public listener does not point at the old colour. If it does, a rollback has happened, so this step is skipped. Otherwise it shuts down the old colour's 4 instances, then tags its target group `retired`. Then go to step 15.
    - Keeps: the state tag.
    - If the shutdown fails: the tag stays `rollback-window`. The run stops and goes to step 15. Step 2 of the next deploy retries it.

15. [ ] **Release the lock.**
    - Starts: when the run ends. Every run ends here: after step 9, 12 or 14, or at any stop.
    - Does: CI releases the deploy lock.
    - Keeps: CI.
    - If it fails: none defined.

## Where deploy state is kept

- **Deploy lock**: CI's concurrency group for `catalog-web`.
- **Live colour**: the public listener's target group. Nothing else records it.
- **Test listener rule**: the target group it forwards to. Step 6 sets it.
- **Tags on each target group**:
  - `release`: the image tag last deployed to that colour. No step reads it. It keeps the record of the previous release, which a normal deploy needs after a rollback.
  - `state`: `live`, `rollback-window`, `failed`, `retired`, or `idle`. A colour is given `idle` when it is first created. An idle colour is never `live` or `rollback-window`. It keeps whichever of `idle`, `failed` or `retired` it was left with. Abort (step 9) changes none of them.
  - `switched-at`: the switch time, set on both colours in step 10.
- **Schema**: the migration tool's history table in the shared PostgreSQL database.

## How to set it up

This is a one-time rollout step. It is not part of each deploy.

- The test listener is set up once, before the first deploy, as part of load balancer setup. It is a second listener, reachable from CI only, with one rule. The deploy does not create it. It only repoints the rule (step 6).

## Open questions

- If the CI run dies during the 15-minute watch, no automatic rollback happens. The next deploy clears the old colour in step 2, once its 30-minute window has closed.
- If a tag write fails after the switch, the run stops and no watch runs. Until an engineer fixes the tags, the next deploy would see the old colour as untagged and idle, and could overwrite it.
- Steps 13 and 14 check the state before acting, but the check and the action are not atomic. A manual rollback that starts at the same moment as the step 14 shutdown could collide. Not solved here.
- Between minute 15 and minute 30 nothing watches the 5xx rate or tells an engineer that a rollback is advisable. The procedure adds no alert.
- Which metric is the 5xx source (load balancer or application) is not specified. This procedure reads the load balancer's counts.
- The smoke suite's contents are not specified.
- The test listener is not in the requirements. Who sets it up is not specified.
- Which tool or API CI calls to shut down instances and tag target groups is not specified. What counts as shutdown finished (instances gone, or deregistered from the target group) is not defined.