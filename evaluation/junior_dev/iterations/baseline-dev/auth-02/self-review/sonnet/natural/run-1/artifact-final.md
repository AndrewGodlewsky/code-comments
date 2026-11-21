# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

**Today.** The three live API keys (payments, email, geocoding) are in `config/app.yaml`. That file is committed to git and copied into every container image. `app/config_loader.py` reads it once, when the module is first imported. Each provider client copies its key into itself when it is built, and the client is a module-level singleton. So a key cannot change without a new image and a redeploy. `/healthz` returns 200 as soon as the HTTP server is listening.

**The change has two parts.**
1. **Part A, rollout (steps 1-9).** Create new keys at each provider, put them in the store, deploy the new code, then revoke the old keys.
2. **Part B, runtime behavior (steps 10-15).** How the new code works. It loads the keys from the store into memory. It reports ready only when all three are loaded. It re-reads them every 5 minutes. CI blocks keys from coming back into the yaml.

**Why customers see no errors.** During the rollout, old and new keys are both valid. An old key is revoked only after every running instance is confirmed to be using the new one.

**Rotation cadence** (a regular rotation schedule after this migration) is undecided. This plan does not pick one. It is listed under Open questions.

### Terms

- **The store**: the managed secret store. Secrets live at `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The store encrypts them at rest with a per-environment KMS key. Every write creates a new **version id**. Version ids are not secret, so they are safe to log.
- **Pod**: one running replica of the app. Production runs 4, all under the service identity `orders-api-prod`.
- **Readiness probe**: the cluster's periodic `GET /healthz`. A pod receives traffic only while it returns 200.
- **`SecretProvider`**: a new in-process component. It holds the keys in memory and refreshes them from the store (steps 10-13).
- **Canary**: the first new pod. It is checked on its own before the rest of the rollout continues.
- **Security on-call**: the only group allowed to write prod secrets.

## Assumptions to check before starting

The brief does not state these. Step 1 checks them.

- **A1.** Each provider allows two API keys to be valid at the same time. The zero-failure requirement cannot be met without this. If any provider allows only one live key, stop and ask Security for a provider-specific plan.
- **A2.** The store authenticates `orders-api-prod` through the cluster's workload identity, so no credential is stored anywhere. If a static credential turns out to be needed, it is itself a new secret and must follow the same rules.
- **A3.** Each provider offers sandbox or test keys for development. If one does not, local runs for that provider use the offline fakes in step 14.
- **A4.** The store's audit log shows which identity read which secret. This is how we show that engineers cannot read prod.

## Part A: Rollout

Order: prepare the store (1), create and store new keys (2), merge the code (3), preflight (4), deploy (5), confirm (6), cut over local development (7, in parallel with 5-6), revoke old keys (8), clean up (9).

### 1. Prepare the store and access

- **Starts when:** the plan is approved. The platform team does the work and Security reviews it.
- **What moves:**
  - No secret values yet.
  - Create the paths `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key` and `orders-api/prod/geocoding_api_key`, plus the matching `orders-api/dev/*` paths. Prod secrets use the prod KMS key. Dev secrets use the dev KMS key.
  - Set policies:
    - `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. If the store needs a separate KMS decrypt grant, it covers the prod KMS key only.
    - Only the security on-call group can write to `orders-api/prod/*`.
    - Engineers get no prod access. They get read access to `orders-api/dev/*`, and write access there if the team wants it.
  - Run these checks and attach the results to the tracking ticket:
    - An engineer identity is denied reading and writing prod.
    - `orders-api-prod` is denied reading `orders-api/dev/*` or any other path, and is denied all writes.
    - A non-security identity is denied writing prod.
  - Confirm A1 and A3 with each provider.
- **State lives in:** the store, its policies and its audit log.
- **If it fails:** nothing in production has changed, so customers are unaffected. Fix the policy and rerun. Do not go on until every negative check is denied.

### 2. Create new keys and write them to the store

- **Starts when:** step 1's checks pass. The security on-call does this, as the only prod writer.
- **What moves:**
  - For each provider, the on-call creates a **new** key in the provider console. The old key stays active.
  - The on-call checks the new key with a harmless provider call, then writes it straight into the store as `orders-api/prod/<name>`.
  - The value never goes into a ticket, chat, shell history, CI variable, environment variable or file.
  - Sandbox keys go into `orders-api/dev/*` the same way.
  - Record the **old key IDs** (not values) and the new version ids.
- **State lives in:** the store (new keys) and the providers (old and new keys both active). All 4 running pods still use the old keys.
- **If it fails:**
  - If the provider rejects the check, do not write the key. Create another.
  - If the write fails, retry. Nothing depends on it yet.
  - A bad value that did get written is replaced by writing a corrected value, which creates a new version id.
  - Customers are unaffected because the pods still use the old keys.

### 3. Ship the code change as one PR

- **Starts when:** step 2 is complete. Someone other than the author reviews the PR.
- **What moves:** the code described in Part B, plus the CI guard.
  - Remove all three `api_key` lines from `config/app.yaml`. Keep `base_url`, timeouts and `from_address`.
  - Add `SecretProvider` (step 10).
  - Change the clients to read the key on each request (step 12).
  - Make `/healthz` depend on the three keys being loaded (step 11).
  - Add `config/app.dev.yaml` and the `make run` changes (step 14).
  - Add the CI check (step 15).
  - Merging to `main` builds an image (per `deploy.md`). That image contains no keys.
- **State lives in:** git and the image registry. Old images, which still contain the old keys, stay in the registry until step 9.
- **If it fails:**
  - If tests or the CI check fail, the PR does not merge.
  - Required tests:
    - Startup retry count and spacing, and the non-zero exit.
    - A failed refresh keeps the last good value.
    - Readiness is false until all three keys are loaded.
    - A log-capture test showing no key value appears in logs, including on error paths.
  - Merging does not change production unless deploys are automatic on merge. In that case step 5 would start at merge, so steps 2 and 4 must be done first (see Open questions).

### 4. Preflight in production, before any rollout

- **Starts when:** the image from step 3 exists. The platform team does this.
- **What moves:**
  - Run a one-off job as `orders-api-prod` that reads the three prod secrets.
  - It logs only secret names and version ids, never values.
  - It exits 0 only if all three reads succeed.
- **State lives in:** the store and the job's logs (version ids only).
- **If it fails:**
  - Fix access or the secret path, then rerun. Nothing is deployed, so customers are unaffected.
  - Do not start step 5 until the job passes.
  - This catches the most likely failure: a missing grant that would leave new pods never becoming ready.

### 5. Rolling deploy with a canary hold

- **Starts when:** step 4 passes. Whoever runs deploys does this.
- **What moves:**
  - Use the normal rolling deploy: one pod at a time, `maxUnavailable: 0`. A new pod loads its keys before `/healthz` returns 200, so an old pod stops only after a new one is ready.
  - **Pause the rollout after the first new pod is ready.** Check that this pod's calls to each provider succeed with the new key, using the provider success metric and the version ids the pod reports. Then resume.
  - While the rollout runs, old pods use the old keys and new pods use the new keys. Both are valid, so this is safe.
- **State lives in:** the pods (keys in memory only) and the store.
- **If it fails:**
  - If a new pod cannot reach the store, it exits non-zero after its retries (step 10). It never becomes ready, the rollout halts, and the old pods keep serving.
  - If the canary shows provider errors, redeploy the previous image. This is safe because the old keys are still valid. Then investigate the new key (step 2).
  - Rolling back to a pre-migration image is allowed only before step 8.

### 6. Confirm every instance is on the new keys

- **Starts when:** the rollout is complete and no old-image pods remain. The platform team does this.
- **What moves:**
  - Query each of the 4 pods for the version ids it reports for each secret (exposed on `/healthz`, step 11). Compare them with the version ids from step 2.
  - Wait at least 10 minutes (two refresh intervals) after the last old pod stopped. Then check each provider console for the last-used time of each old key. Require that nothing has used it since.
  - Look for other users of the old keys, such as scripts or developer machines. Developers' `make run` used the live keys, so expect some laptop use. That does not affect customers. Any unexplained service-side use blocks step 8.
- **State lives in:** the pods' reported versions, the provider usage data and the ticket.
- **If it fails:**
  - If any pod reports a different version, or something unidentified still uses an old key, do not revoke. Find the cause first.
  - A pod that cannot show the right version is restarted. It reads the current store value on startup.
  - Confirmation rests on reported version ids, never on "enough time has passed".

### 7. Cut local development over to dev secrets

- **Starts when:** the PR from step 3 is merged. This can run in parallel with steps 5 and 6.
- **What moves:** engineers pull the new `main` and use the new `make run` (step 14). Local runs now read `orders-api/dev/*` or use offline fakes. They never touch prod secrets.
- **State lives in:** the dev store paths and the engineers' own identities.
- **If it fails:** an engineer whose local run breaks can use offline mode. There is no production impact. The old live keys stop working at step 8, so there is no fallback to them.

### 8. Revoke the old keys

- **Starts when:** step 6 is fully confirmed and the security on-call approves. After this point no pre-migration image can work.
- **What moves:**
  - Revoke one provider's old key at a time in the provider console. Watch that provider's error rate for a few minutes before moving to the next.
  - Record the time and key ID in the ticket.
- **State lives in:** the providers.
- **If it fails:**
  - If errors appear after a revoke, find the instance still using the old key. Step 6 should have made that impossible, so treat it as an incident.
  - Restart that instance. It loads the current store value.
  - Do not re-enable the leaked key. If the provider cannot undelete it, create a new key and write it to the store (as in step 2). Instances pick it up within 5 minutes.

### 9. Clean up what still holds old keys

- **Starts when:** step 8 is complete.
- **What moves:**
  - Mark every pre-migration image do-not-deploy, or delete it from the registry. From now on, "rollback = redeploy an earlier image" is valid only for images built after step 3.
  - Update `deploy.md` with this, and with the new startup, readiness and local-run behavior.
  - Git history is not rewritten, so the old keys stay visible there. They are now revoked and harmless.
- **State lives in:** the registry and the docs.
- **If it fails:** if a pre-migration image is redeployed by mistake, its provider calls fail with auth errors. Redeploy a post-migration image. This is why marking the old images matters.

## Part B: Runtime behavior

This is what the code from step 3 does. Steps 10-13 run in every environment. Step 14 covers local runs. Step 15 is a CI check.

### 10. Startup: load all three keys before ready

- **Starts when:** the process starts. The app reads non-secret settings from the yaml first. Then, before the HTTP server accepts requests, it calls `SecretProvider.start()`.
- **What moves:**
  - Read `orders-api/<env>/payments_api_key`, `email_api_key` and `geocoding_api_key` from the store. `<env>` comes from the non-secret `APP_ENV` variable.
  - Hold the values, with their version ids, in one in-memory object.
  - Give each store call a bounded timeout (an implementation choice).
  - If any read fails, retry 3 times, 2 seconds apart. That is up to 4 attempts and about 6 seconds of waiting.
  - Once all three are loaded, log the version ids only, then start the server.
- **State lives in:** process memory only. No disk cache, environment variable or log. Disable core dumps in the container.
- **If it fails:**
  - After the last retry, log the secret names and the error class (never values) and exit non-zero.
  - The cluster restarts the pod. In a rolling deploy the rollout halts and the old pods keep serving, because `maxUnavailable` is 0.
  - There is no fallback to the yaml, because the keys are no longer in it.

### 11. Readiness

- **Starts when:** the cluster probes `GET /healthz`.
- **What moves:**
  - Return 200 only if all three keys are loaded. Otherwise return 503.
  - The body includes the three version ids, which step 6 uses.
  - After startup, readiness does **not** turn off when a refresh fails. The pod keeps its last good keys and keeps serving.
- **State lives in:** the in-memory key object.
- **If it fails:** a 503 keeps the pod out of rotation and, during a deploy, halts the rollout. The probe never calls the store itself, so a store outage cannot take down healthy pods.

### 12. Using a key on each request

- **Starts when:** a provider client makes a call (`charge`, send email, geocode).
- **What moves:**
  - Clients no longer copy the key in `__init__`. They call `secrets.get("payments_api_key")` each time.
  - `get()` returns the current value from memory and never touches the network.
  - A request already in progress keeps the key it read, so a swap never changes a request halfway.
  - The module-level client singletons can stay, because they no longer hold a key.
  - If `get()` is called before the keys are loaded, it raises an error. It never returns an empty value.
- **State lives in:** process memory.
- **If it fails:** an unexpected `get()` error is a code bug, caught by the tests in step 3.

### 13. Refresh every 5 minutes

- **Starts when:** a timer fires every 5 minutes after startup. Add small random jitter so the 4 pods do not all read at once.
- **What moves:**
  - Read each secret from the store.
  - If the version id changed, swap the new value into the in-memory object in one step (replace the object reference under a lock). Log the secret name and the old and new version ids.
  - Expose the current version ids on `/healthz` (step 11) and a "seconds since last successful read" metric. The team sets the alert threshold.
- **State lives in:** process memory.
- **If it fails:**
  - If a read fails, or returns an empty or malformed value, keep the last good value and log a **warning**. The warning carries the secret name, the error class and the current version id, never a value.
  - Try again at the next interval. There is no retry loop.
  - Each of the three secrets is handled separately, so one failure does not block the others.
  - A pod that keeps failing keeps working on its old value. That is why revocation in step 8 depends on reported versions.

### 14. Local development

- **Starts when:** an engineer runs `make run`.
- **What moves:**
  - `make run` sets `APP_ENV=dev` and `APP_CONFIG=config/app.dev.yaml`. The dev yaml holds sandbox `base_url`s and no keys.
  - The engineer's own identity reads `orders-api/dev/*`. The path prefix is built from `APP_ENV`, so the code has no prod fallback.
  - `make run-offline` uses fake provider stubs with fake keys held in memory. It is allowed only when `APP_ENV=local`. In any other environment the app refuses to start with the fake source.
  - Engineers are denied prod reads anyway (step 1), so a mistake fails rather than leaks.
- **State lives in:** the dev store, or process memory for the fakes.
- **If it fails:** if the dev store is unreachable, the same retry-then-exit behavior applies. Use `make run-offline` instead.

### 15. CI guard against keys returning

- **Starts when:** every pull request and every push to `main`. Make the check **required** in branch protection.
- **What moves:**
  - A CI job parses `config/app.yaml` and any other `config/*.yaml` as YAML.
  - It fails the build if a key named `api_key` appears at any depth, compared case-insensitively.
  - It also fails if a file cannot be parsed, so a parse error cannot hide a key.
  - It uses a parser, not a text search, so quoting or indentation changes cannot bypass it.
  - As a second line of defense, `config_loader` refuses to start if it finds an `api_key` in the loaded settings.
- **State lives in:** CI and branch protection.
- **If it fails:** the failing check blocks the merge. The author moves the key to the store and removes it from the yaml.

## Failure summary

| Where | Failure | What happens |
|---|---|---|
| Steps 5 and 10 | Store unreachable at startup | Pod exits non-zero after its retries. Rollout halts. Old pods keep serving. |
| Step 5 | New key bad at the provider | Caught by the canary hold. Redeploy the previous image while the old keys are still valid. |
| Step 6 | A pod reports an old version, or an old key is still in use | Do not revoke. Find the cause, restart the pod if needed. |
| Step 13 | Store unreachable during refresh | Last good value kept. Warning logged. Retry in 5 minutes. |
| Step 8 | An instance still on an old key | Step 6 should prevent this. If it happens, it is an incident. Restart the instance. |
| Step 9 | Pre-migration image redeployed | Provider calls fail on revoked keys. Prevented by marking the images. |

## Open questions

1. **Scheduled rotation: not decided.** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence. The runtime refresh and the rotate-confirm-revoke procedure (steps 2, 6 and 8) work for any cadence, so nothing here needs to change once Security decides. The decision depends on the providers (A1).
2. **A1:** does each provider allow two live keys at once? This must be answered before step 2.
3. **A3:** do all three providers offer sandbox keys? If not, which should run on fakes locally?
4. **Alerting:** what threshold should alert on "seconds since last successful read"?
5. **Automatic deploys:** if merging to `main` auto-deploys, steps 2 and 4 must be finished before the merge in step 3.