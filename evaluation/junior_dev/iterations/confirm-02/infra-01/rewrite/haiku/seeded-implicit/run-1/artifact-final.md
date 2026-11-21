# catalog-web blue-green deploy

## Summary

Today `catalog-web` is restarted in place. This replaces that with blue-green deploys. `catalog-web` runs as two identical environments, blue and green, with 4 instances each. One colour is live and takes all user traffic through one load balancer listener. A deploy puts the new release on the idle colour, checks it, and moves all traffic to it in one step. The old colour stays up for 30 minutes, so a rollback is only a listener change. CI runs every step after a merge to `main`. No one runs them by hand, except a rollback job that an engineer starts.

Migrations are additive only, so the old release still works on the migrated schema. This is what makes a rollback safe without reversing any database change.

## Terms

- **Colour**: one full set of 4 instances, either blue or green.
- **Listener**: the load balancer's public entry point. It forwards all traffic to one target group.
- **Target group**: the list of instances in one colour. The switch changes which target group the listener forwards to.
- **Test listener**: a second listener on the same load balancer. It forwards only to the idle colour, so the smoke tests can reach the new release and no user can.
- **/healthz**: a page each instance serves to say it is ready.
- **Smoke tests**: a test suite that runs against the new release.
- **Migration**: a database schema change. Additive means only new tables, nullable columns or indexes.
- **5xx rate**: the share of responses that are server errors.
- **Deploy state record**: one small record per service, stored under one key in the cloud parameter store. It holds the live colour, the current release, the switch time and the lock. The next deploy and the rollback job both read it, so it must live outside any one run.
- **Deploy lock**: the lock field in the state record. While a deploy runs, it holds that run's CI ID. A second deploy cannot start while the lock is held. The lock is held for the whole 30-minute window, because during that window the idle colour still runs the old release, and a second deploy would overwrite it.

## Rules for every step

- The listener is the source of truth for which colour is live. The state record is a copy of it.
- A colour is shut down only if the listener does not point at it.
- Migrations are never reversed, not even by a rollback.
- Dropping or renaming a column or table waits for a later release, once the release that uses it has been retired.
- A run that ends releases the lock, unless a step says to keep it.
- Once the old colour has been shut down, a rollback is a normal deploy of the previous release. It runs every step again, including migrations, which is safe because they are additive.

## Steps

1. **Build and lint.** Trigger: a merge to `main`. Build the container image and tag it with the commit ID. Run the migration lint, which rejects any migration that is not additive. If either fails, the pipeline stops. Nothing has changed.

2. **Take the lock.** Trigger: step 1 passed. Read the state record. If the lock is empty, write this run's ID into it. If another run holds it, stop and fail. Nothing has changed.

3. **Find the idle colour.** Trigger: step 2 passed. Read which target group the listener forwards to. The other colour is idle. If the state record and the listener disagree, stop and release the lock. A person must check which colour is right before any deploy continues.

4. **Migrate.** Trigger: step 3 passed. Apply the pending additive migrations once, against the shared PostgreSQL database. Build indexes concurrently, so the live colour keeps serving. Record each migration as soon as it finishes. If a migration fails, stop and release the lock. The new release is never started, and the live colour keeps serving. A failed concurrent index build leaves an invalid index. The next run drops it, then runs only the migrations not yet recorded.

5. **Start the new release on the idle colour.** Trigger: step 4 passed. Start 4 instances of the new release and add them to the idle target group. The listener still points at the live colour, so they get no user traffic. The 10-minute clock for step 6 starts when the first instance starts.

6. **Gate: health checks and smoke tests.** Trigger: step 5. Run two checks in parallel. Both must pass within 10 minutes of the first instance starting.
   - Each instance must pass `/healthz` three times in a row. Checks run every 10 seconds. A failed check resets that instance's count to zero.
   - The smoke test suite must pass through the test listener.

   If both pass, go to step 7. If either fails, or 10 minutes pass first, abort. An abort never touches the public listener. Shut down the new colour's instances, leave the state record unchanged and release the lock. Users are not affected.

7. **Switch.** Trigger: step 6 passed. Repoint the public listener from the live target group to the idle one, in one step. There is no gradual shift. Then write the new live colour, the current release and the switch time to the state record. If the repoint fails, the listener stays on the old colour. Handle this as the abort in step 6.

8. **Watch for 15 minutes.** Trigger: step 7. Watch the 5xx rate for 15 minutes after the switch. If any 5-minute window goes above 1%, go to step 9. If 15 minutes pass with no trip, go to step 10. If the metrics cannot be read, page an engineer. Do not roll back on missing data alone.

9. **Roll back automatically.** Trigger: step 8 trips. Repoint the public listener to the old target group, which is still running and untouched. Write the old colour back as live in the state record. Shut down the new colour's instances. Migrations stay in place. The run ends here, with no teardown, and releases the lock. If the repoint fails, retry until it works, and page an engineer at once.

10. **Hold the old colour.** Trigger: the switch in step 7. Wait until 30 minutes after the switch, and leave the old colour running. During this wait, a rollback is possible. An engineer starts a rollback job, which repoints the listener to the old colour and writes it as live in the state record. The job does not take the lock, so it works while a deploy holds it. A rollback during the wait is the same listener change as step 9.

11. **Tear down.** Trigger: 30 minutes after the switch. Read the listener, and shut down whichever colour it does not point at. Normally that is the old colour. Update the state record, then release the lock. If the shutdown fails, retry it. If it still fails, page an engineer and keep the lock held until a person clears it.

## What happens when things fail

| Failure | Listener | Serving | Migrations | Next |
|---|---|---|---|---|
| Lint, lock or colour check (steps 1-3) | unchanged | live colour | not run | stop |
| Migration (step 4) | unchanged | live colour | partly applied and recorded | stop; next run continues |
| Health or smoke test, or 10-minute timeout (step 6) | unchanged | live colour | kept | stop; new colour shut down |
| Switch fails (step 7) | unchanged | live colour | kept | stop; new colour shut down |
| 5xx trip (step 9) | back on old colour | old colour | kept | rollback done |
| Teardown fails (step 11) | as set | live colour | kept | retry, then page |

## Open questions

- Which metrics source feeds the 5xx rate? The brief does not say.
- Does the migration tool record each migration as it finishes? Step 4 assumes it does.
- Does a test listener already exist on the load balancer? Step 6 assumes one that forwards only to the idle colour.
- Who clears a stuck lock, and how do they confirm that no deploy is running? Step 2 assumes a person does this by hand.
- What is the parameter store key that holds the state record? The pipeline owner must name it.