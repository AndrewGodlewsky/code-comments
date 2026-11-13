# Blue-green deploys for `catalog-web`

We're replacing in-place restarts of `catalog-web` with blue-green deploys. Write down the procedure before anyone builds the pipeline.

## Existing system

- `catalog-web` is a stateless HTTP service that runs as two environments, **blue** and **green**, with 4 instances each. One colour is live; the other is idle.
- One load balancer sits in front of it, with a target group per colour. Its public listener forwards to exactly one target group at a time.
- Both colours share one PostgreSQL database. There is only one copy of the data.
- The CI pipeline runs deploys when something is merged to `main`. Nobody runs deploy steps by hand.

## Fixed requirements

1. Schema migrations are applied once per deploy, before any instance of the new release starts. They must be additive only (new tables, nullable columns, indexes), so the release that is serving traffic keeps working on the migrated schema. Dropping or renaming a column or table happens in a later release, once the release that still uses it has been retired.
2. If a migration fails, the deploy stops. The new release is never started and the live colour keeps serving.
3. The new release gets no user traffic until every instance has passed `/healthz` three times in a row (checks run every 10 seconds) and the smoke test suite has passed against it. If both have not happened within 10 minutes of the instances starting, abort without touching the public listener.
4. Traffic moves in one step: the public listener is repointed from the old target group to the new one. There is no gradual shift.
5. For 15 minutes after the switch, watch the 5xx rate. If it goes above 1% over any 5-minute window, roll back automatically by pointing the listener back at the old colour. A rollback never reverses migrations.
6. The old colour stays running, untouched, for 30 minutes after the switch. Until it is shut down, a rollback (the automatic one, or one an engineer starts as a pipeline job) points the listener back at it. Once it is shut down, any rollback is a normal deploy of the previous release.

## What I need

Write the deploy as a **Markdown checklist of steps, in the order they are done**, from the merge to the end of the deploy. For each step, say what starts it, what it changes and what happens if it fails. Decide anything I haven't, and say where any deploy state is kept.
