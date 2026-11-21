# catalog-web blue-green deploy

This is the procedure the CI pipeline runs after every merge to `main`. Nobody runs these steps by hand. The one exception is that an engineer can start a rollback as a pipeline job (see step 10).

## How the system fits together

- **Blue and green** are two copies of the `catalog-web` HTTP service, each with 4 instances. One colour is **live** and serves users. The other is **idle**. A deploy puts the new release on the idle colour, checks it, then makes it live.
- **Old colour and new colour.** The old colour is the one that was live before the switch. The new colour is the idle one that gets the new release.
- **Load balancer.** It has one **public listener** that forwards user requests to exactly one **target group**. A target group is the list of one colour's instances, and each colour has its own. "Switching traffic" means changing which target group the public listener forwards to. It is one operation and it moves all traffic at once.
- **Database.** Both colours share one PostgreSQL database. There is only one copy of the data.
- **Rollback** means pointing the public listener back at the old colour's target group. It never reverses database migrations. It works only while the old colour is still running (see step 11).

## Decisions made here

The brief did not settle these.

- **The idle colour has no running instances between deploys.** A deploy starts 4 instances on it (step 5). Step 11 stops the old colour's 4 instances once they are no longer needed for rollback.
- **The live colour is always read from the public listener.** No stored record is trusted for this.
- **Smoke tests run through a test listener.** This is a second listener on the same load balancer, on a private port that only CI runners can reach. It forwards to the new colour's target group and carries no user traffic.
- **The deploy lock is a CI concurrency group named `catalog-web-deploy`.** Only one deploy runs at a time. If several merges are waiting, only the newest runs and the older ones are cancelled, because the newest contains their commits. The lock is held until step 12, after the old colour has been shut down. Otherwise the next deploy would reuse the old colour while it is still the rollback target.
- **The deploy record is one row in a `deploy_state` table in the shared PostgreSQL database.** It holds the release id, the old and new colour, a status, `instances_started_at` and `switched_at`. Status is one of `started`, `verified`, `switched`, `rolled_back`, `aborted`, `failed` or `done`. The record exists so that the 10-minute and 30-minute timers survive a CI job restart, and so that people can see what happened. It never decides which colour is live, and rollback does not need it.
- **Abort** means a stop before any user traffic moved. It stops the new colour's instances, leaves the public listener alone, sets the status to `aborted` and alerts on-call. Migrations already applied stay, because they are additive and harmless. After an abort the deploy goes straight to step 12.
- **5xx rate** is the share of responses on the public listener that are 5xx, out of all responses, over a 5-minute window.
- **Missing 5xx data counts as a bad sign.** If the 5xx metric cannot be read for 3 minutes in a row, the deploy rolls back.
- **Any failure not described below** stops the deploy, sets the status to `failed` and alerts on-call. Step 12 still runs.

## Steps

- [ ] **1. Get the deploy lock**
  - Starts: the merge to `main` starts the pipeline.
  - Changes: it takes the `catalog-web-deploy` lock. Nothing else changes.
  - If it fails: if another deploy holds the lock, this one waits for up to 60 minutes. If the wait runs out, it ends with nothing changed.

- [ ] **2. Work out the live and idle colour**
  - Starts: the lock is held.
  - Changes: it reads which target group the public listener points at. That colour is the old colour and the other is the new colour. It writes the deploy record with status `started`. It stops any instances still running on the new colour from an earlier failed deploy.
  - If it fails: if the listener cannot be read, or points at neither target group, the deploy stops with nothing changed.

- [ ] **3. Build the image and lint the migrations**
  - Starts: step 2 is done.
  - Changes: it builds the release image, tags it with the commit SHA and pushes it to the registry. The lint reads the new migration files. It allows only new tables, nullable columns and indexes, and rejects everything else (drops, renames, type changes, `NOT NULL` columns without a default).
  - If it fails: the deploy stops. Nothing is deployed and the database is untouched.

- [ ] **4. Run the migrations**
  - Starts: build and lint passed.
  - Changes: the pipeline applies the pending migrations to the shared database, once. Instances never run migrations themselves. Each migration runs in a transaction, except index builds, which use `CREATE INDEX CONCURRENTLY` so they do not block writes. The old colour keeps serving throughout, and the additive-only rule means it keeps working on the new schema.
  - If it fails: the deploy stops and the new release is never started. The live colour keeps serving. A failed migration rolls back its own transaction. A failed concurrent index build leaves an invalid index, which the migration tool drops before the next attempt.

- [ ] **5. Start the new release on the idle colour**
  - Starts: migrations are done, or none were pending.
  - Changes: it starts 4 instances of the new image on the new colour and registers them in its target group. It records `instances_started_at`, which starts the **10-minute clock** for steps 6 and 7. No user traffic reaches them, because the public listener still points at the old colour.
  - If it fails: if the instances cannot be started or registered, abort.

- [ ] **6. Health checks**
  - Starts: the instances are started.
  - Changes: nothing. Every 10 seconds the pipeline calls `/healthz` on each of the 4 instances. An instance is ready after 3 passes in a row, and one failure resets its count to zero. All 4 must be ready.
  - If it fails: if all 4 are not ready by the 10-minute deadline, abort.

- [ ] **7. Smoke tests through the test listener**
  - Starts: all 4 instances are ready.
  - Changes: it points the test listener at the new colour's target group and runs the smoke suite against it. It sets the status to `verified` when the suite passes.
  - If it fails: if any test fails, or the 10-minute deadline passes before the suite finishes, abort. A failed suite is not retried within the same deploy.

- [ ] **8. Switch traffic to the new colour**
  - Starts: steps 6 and 7 have both passed within 10 minutes of step 5.
  - Changes: one operation repoints the public listener from the old target group to the new one. All user traffic moves at once, with no gradual shift. The pipeline then reads the listener back to confirm. It records `switched_at` and sets the status to `switched`. The old colour is not touched.
  - If it fails: the pipeline retries the call up to 3 times, checking the listener each time. If the listener still points at the old group, abort. Users have been on the old colour the whole time.

- [ ] **9. Watch the 5xx rate for 15 minutes**
  - Starts: the switch is confirmed.
  - Changes: nothing while the rate is healthy. Every minute the pipeline computes the 5xx rate over the last 5 minutes (or the time since the switch, if shorter). If it is **above 1%**, or the metric has been unreadable for 3 minutes, the pipeline rolls back automatically.
  - A rollback does three things:
    1. It repoints the public listener at the old target group, only if the listener currently points at the new one, so repeated or concurrent rollbacks are safe.
    2. It sets the status to `rolled_back` and alerts.
    3. It stops the new colour's instances.

    The old colour is live again, and the deploy then goes to step 12 (steps 10 and 11 are skipped).
  - If it fails: if the rollback's repoint call fails, the pipeline retries it, then pages on-call. The old colour is still running, so the fix is a single listener change.

- [ ] **10. Keep the old colour running for 30 minutes after the switch**
  - Starts: the 15-minute watch ended without a rollback.
  - Changes: nothing. The old colour's 4 instances keep running untouched until `switched_at` + 30 minutes. During this time a rollback is still just the repoint described in step 9. An engineer can start it as a pipeline job, which does not need the deploy lock. If that happens, this deploy sets the status to `rolled_back`, stops the new colour, skips step 11 and goes to step 12.
  - If it fails: if the deploy job dies, nothing stops the old colour. A restarted job reads `switched_at` and carries on with the timer.

- [ ] **11. Shut down the old colour**
  - Starts: 30 minutes after the switch, with no rollback.
  - Changes: it stops the old colour's 4 instances, which leaves that colour idle for the next deploy. It sets the status to `done`. From now on a rollback is a **normal deploy of the previous release**, going through all of these steps. Its migrations are already applied, so step 4 does nothing.
  - If it fails: it retries, then alerts. Instances left running do no harm, and step 2 of the next deploy stops them.

- [ ] **12. Release the lock**
  - Starts: this is the last step of every run, whether it succeeded, aborted, rolled back or failed. CI also frees the lock if the job dies.
  - Changes: it releases the lock, so the next queued deploy can start.
  - If it fails: there is nothing to retry. CI frees the lock when the run ends.