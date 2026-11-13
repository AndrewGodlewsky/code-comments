# Plan: move orders-api third-party keys into the managed secret store

## What this is

`orders-api` uses three live third-party keys: payments, email and geocoding. Today they sit in `config/app.yaml`. That file is committed to git and copied into every container image. At start-up the app reads the file once, and each provider client copies its key at construction. Changing a key means building a new image and redeploying.

This plan does two things:

- **Rollout.** It puts the keys in the managed secret store, creates new keys at each provider, deploys new code, and revokes the old keys last.
- **Runtime.** It changes the app so that it loads the keys from the store at start-up, keeps them in memory only, refreshes them every 5 minutes, and reads them from memory on each provider call.

The rollout is shaped by one fact. The old keys stay valid at the providers until every running pod is on the new code. Each image carries its own copy of `config/app.yaml`, so an old pod keeps using its old key and a new pod uses the new key. Both key sets work during the change, so no customer request fails. The old keys are revoked only after two checks pass. Every running pod must be on the new code, and old images must be blocked from deployment, so that no one can roll back onto a revoked key.

The runtime section comes first, because the rollout deploys that code.

## Terms

- **Managed secret store.** The organisation's service that holds named values, such as `orders-api/prod/payments_api_key`. Each write creates a new version. The brief does not name the product (see Open questions).
- **Secret path.** The name of a value in the store, in the form `orders-api/<env>/<name>`. `<env>` is `dev`, `staging` or `prod`. `<name>` is `payments_api_key`, `email_api_key` or `geocoding_api_key`.
- **KMS key.** An encryption key. The store encrypts each value at rest, using one KMS key per environment.
- **Version id.** The store's id for one write of a value. It is safe to log.
- **Service identity.** The account a running pod uses to call the store. Production pods run as `orders-api-prod`. The platform attaches the identity to the pod, so the app holds no password (see Open questions).
- **Old keys.** The three keys in `config/app.yaml` today and in git history. They are treated as leaked.
- **New keys.** The three keys created at each provider during the rollout.
- **Overlap.** The period when a provider accepts both the old and the new key.
- **Revocation.** The provider permanently disables a key. This cannot be undone.
- **Pre-migration image.** Any image built before the rollout's code merge. It contains `config/app.yaml` with the old keys.
- **Post-migration image.** Any image built from the code merge or a later commit on `main`. It has no keys and reads the store.
- **SecretStore.** A class in the app that holds the current value and version id of each key, in memory only.
- **Readiness.** `GET /healthz` returns 200. A pod receives traffic only while it is ready.
- **Liveness.** A probe that restarts a pod when it fails. It must not depend on the store.
- **Config guard.** A CI check that fails any change which adds an `api_key` line to `config/app.yaml`.
- **Deny policy.** A registry rule that refuses to deploy certain images.

Who does what:

- **Security on-call.** The only writer of `orders-api/prod/*`. Creates each new provider key and writes it to the store in one step, so no engineer sees a value. Performs revocations.
- **`orders-api-prod`.** Read-only on `orders-api/prod/*`. No other access.
- **Engineers (dev identity `orders-api-dev`).** Read on `orders-api/dev/*` only. No prod read.
- **CI.** No secret access. Runs the config guard only.

---

## Part 1: How the app reads keys at runtime

### Runtime step 1: Load the three keys at start-up

- **Starts when:** the process starts. Nothing happens at import time.
- **What moves where:** the loader reads `config/app.yaml` for non-secret settings only: base URLs, timeouts, `from_address`, app name, port and log level. Then `SecretStore` fetches the latest version of each of the three secret paths, using the pod's `orders-api-prod` identity. No credential is held in an environment variable or on disk.
- **Retry:** one first attempt, then up to 3 retries, 2 seconds apart. That is about 6 seconds in total. This reading of "retry 3 times" is an assumption (see Open questions).
- **Validation:** a fetched value must be non-empty and contain no whitespace. Otherwise it counts as a failed read.
- **State lives in:** process memory only, as a map from name to (value, version id, time fetched).
- **If it fails:** if any of the three keys is still missing after the retries, the process logs an error with the name and the error class, never the value, and exits with a non-zero code. It never starts serving with only some of the keys.

### Runtime step 2: Report ready or not ready

- **Starts when:** runtime step 1 completes.
- **What moves where:** the HTTP server starts. `GET /healthz` returns 503 until the start-up load sets a ready flag. After that it returns 200.
- **Why:** a pod must not take customer traffic until it holds all three keys.
- **Readiness does not depend on refresh.** A store outage after start-up does not make pods unready.
- **Liveness, if a liveness probe exists,** only checks that the process is listening. A store outage must never restart pods.
- **State lives in:** one process-local flag.
- **If it fails:** a pod that never becomes ready gets no traffic. The rollout halts and the old pods keep serving. This is a change: today `/healthz` returns ok as soon as the listener is up. `deploy.md` must say so.

### Runtime step 3: Provider clients read the key on each call

- **Starts when:** a request needs a provider call.
- **What moves where:** `PaymentsClient`, `EmailClient` and `GeocodingClient` no longer copy their key at construction. On each call, a client asks `SecretStore` for the current value of its key. This is a read from memory under a lock. It makes no network call to the store. The client then builds the `Authorization` header. The clients are created at import without any network access, so the key is read after start-up, not during import.
- **State lives in:** `SecretStore` memory.
- **If it fails:** after start-up the value is always present, because start-up refuses to run without all three. A missing entry at request time is a programming error. That request fails with an internal error, which is logged. An empty value is never sent.

### Runtime step 4: Refresh the keys every 5 minutes

- **Starts when:** the ready flag is set. A timer thread runs every 5 minutes, plus about 30 seconds of random jitter, so the four replicas do not read the store at the same moment.
- **What moves where:** for each of the three names, the store is read for its latest version.
  - If the version id is unchanged, nothing happens.
  - If the version id has changed and the value is valid, the entry is swapped under the lock. The log records `secret rotated name=... version=...`, with no value.
  - If the read fails (store error, timeout, access denied or invalid value), the last good value is kept. A warning is logged with the name and the error class. The next attempt is in the next cycle.
- **Staleness check:** if no refresh has succeeded for more than 15 minutes, the app logs a warning and increments a metric. A dead timer thread must not go unnoticed, because the app would keep serving old keys with no sign of trouble.
- **State lives in:** `SecretStore` memory.
- **If it fails:** the app keeps serving on the last good key. Customers are unaffected unless the provider has already revoked the old key that this pod holds. The rollout's confirmation check exists to prevent that. A provider 401 on a migrated pod is logged with the key name and version id, and counted.

### Runtime step 5: Logs and metrics

- **Starts when:** any load, rotation, failure or request.
- **What moves where:** logs and metrics carry only names and version ids. Logging version ids is fine. The metric `secret_version_info{name, version}` is exported, so the rollout can check each replica. HTTP client logging must not record request headers. A log filter removes anything that matches a key prefix. That filter is a safety net, not the main control.
- **State lives in:** the central log service (30-day retention) and the metrics system.
- **If it fails:** if the metric is missing, the rollout uses the log lines instead. A missing metric is never treated as a passed check.

### Runtime step 6: Shutdown and crashes

- **Starts when:** the process gets SIGTERM, or it crashes.
- **What moves where:** nothing is written to disk, and nothing needs flushing. Core dumps are disabled for the container, because a dump would capture key values from memory.
- **State lives in:** memory, which is released on exit.
- **If it fails:** if core dumps cannot be disabled, the rollout's code merge is blocked.

### Runtime step 7: Local development

- **Starts when:** a developer runs `make run` with `APP_ENV=dev`.
- **What moves where:** the developer's SSO identity (`orders-api-dev`) reads `orders-api/dev/*`, which holds the provider test keys written in rollout step 3. Engineers have no prod identity, so a local run cannot read prod.
- **State lives in:** `SecretStore` memory on the developer's machine.
- **If it fails:** a developer without dev access sees a clear start-up error, and the process exits. There is no fallback to committed keys, a local key file or prod. For offline work, use recorded responses or stubs, never real keys.

---

## Part 2: Rollout

### Rollout step 1: Find every consumer of the old keys

- **Starts when:** the change ticket is approved.
- **What moves where:** nothing moves. Each team that uses the same provider accounts lists where it uses the old keys: other services, scripts, jobs, dashboards and partner integrations.
- **State lives in:** the change ticket.
- **If it fails:** a consumer that cannot be found or moved blocks revocation (rollout step 10). Its owner must move it first, or accept an outage at revocation.

### Rollout step 2: Create the store layout, KMS keys and access

- **Starts when:** rollout step 1 is complete.
- **What moves where:** one KMS key is created for each environment (dev, staging, prod). The paths `orders-api/dev/*`, `orders-api/staging/*` and `orders-api/prod/*` are created, with these policies:
  - `orders-api-prod` can read `orders-api/prod/*` only.
  - The security on-call group can write `orders-api/prod/*`.
  - The engineer group can read `orders-api/dev/*` only.
- **State lives in:** the secret store and KMS. The app is not involved yet.
- **If it fails:** production is unchanged. Fix the policy and apply it again. Test with test identities: `orders-api-prod` must read `orders-api/prod/*` and be refused on every other path, and engineers must be refused on prod.

### Rollout step 3: Write dev and staging values from provider test keys

- **Starts when:** rollout step 2 is verified.
- **What moves where:** provider sandbox or test keys are written to `orders-api/dev/*` and `orders-api/staging/*`. Live keys never go into dev or staging.
- **State lives in:** the store, at the dev and staging paths.
- **If it fails:** only dev and staging are affected. Retry the write. Local development is unavailable until it succeeds. Production is not affected.

### Rollout step 4: Create the new prod keys and write them to the store

- **Starts when:** rollout step 3 is complete, and the runtime code (Part 1) is reviewed and approved in the change ticket. "Approved" means reviewed and ready to merge, but not yet merged or deployed. The change owner records that approval in the ticket. The order matters: the new keys are used only once the new code runs, so the code must be ready first.
- **What moves where:** security on-call creates a new live key at each provider. The old keys stay valid. Security on-call writes each new value straight into `orders-api/prod/<name>` as a new version, so no engineer sees it. The version ids go into the change ticket. The values do not. Nothing reads the new keys yet, because the old pods run their old images.
- **State lives in:** the provider (the new key) and the store (the new version, encrypted with the prod KMS key).
- **If it fails:** the old keys still work, and no customer-facing change has happened. If a provider cannot issue a second active key, stop here (see Open questions).

### Rollout step 5: Check prod read access as the production identity

- **Starts when:** the writes in rollout step 4 are complete.
- **What moves where:** security on-call starts a one-off check job that runs as `orders-api-prod`. The job reads the three latest versions. It prints only the version ids and value lengths, never the values. On-call copies the ids into the ticket. Security on-call starts the job because that role already holds the prod write access used in step 4. How the job takes on the `orders-api-prod` identity is the same mechanism as for pods (see Open questions).
- **State lives in:** the job output, which holds ids and lengths only.
- **If it fails:** a read failure means the policy or the identity is wrong. Fix it before any deploy. Do not go on to rollout step 6.

### Rollout step 6: Merge the code change and turn on the CI guard

- **Starts when:** rollout step 5 passes. The change merges to `main` through normal review.
- **What moves where:**
  - `config/app.yaml` keeps the non-secret settings. The three `api_key` lines are removed.
  - The old key values stay in git history. History is not rewritten.
  - The runtime code from Part 1 is included.
  - `/healthz` reports ready only after the keys are loaded.
  - `deploy.md` is updated to describe the new readiness meaning.
  - The config guard is added in the same change. It fails any change that adds an `api_key` line to `config/app.yaml`. It must be in place now, because the keys are out of the file now.
- **State lives in:** git (`main`) and the built image. The image holds no keys.
- **Interim exposure:** from this merge until revocation in rollout step 10, the old keys still work at the providers, and anyone who can read the repo history can still see them. The plan accepts this window, because the brief allows revocation only after every instance uses the new keys. Security must confirm this is acceptable (see Open questions).
- **If it fails:** if the guard fails, the merge is blocked and production does not change. If the build fails, nothing is released.

### Rollout step 7: Canary one pod on the new image

- **Starts when:** the image from rollout step 6 is built.
- **What moves where:** the rolling deploy replaces one pod with the new image. The new pod loads the three keys from the store before it reports ready (runtime step 1).
- **State lives in:** the new pod's memory. The store holds the keys.
- **If it fails:** if the store cannot be reached or the identity is denied, the new pod retries, then exits with a non-zero code. It never becomes ready. With `maxUnavailable: 0`, the rollout halts. The old pods keep serving on the old keys, which are still valid. Customer impact: none. Find the cause, fix it and redeploy.

### Rollout step 8: Roll the remaining pods

- **Starts when:** the canary pod is ready, and its logs show the three version ids from rollout step 4.
- **What moves where:** pods are replaced one at a time, so the fleet is mixed for a while. An old pod uses the key baked into its image's `config/app.yaml`, and it never reads the store. A new pod uses the key it loaded from the store. The image decides which key a pod uses, not the store. Both key sets are valid at the providers, so the mixed fleet works. That is why revocation waits.
- **State lives in:** each pod's memory.
- **If it fails:** the rollout halts at the first pod that cannot become ready. The old pods keep serving. Diagnose, fix and redeploy. Revoke nothing while the fleet is mixed.

### Rollout step 9: Confirm every instance uses the new versions

- **Starts when:** all replicas run the new image, and at least 10 minutes have passed since the last replacement. That covers one 5-minute refresh cycle plus jitter.
- **What moves where:** nothing moves. Three checks run:
  - Each replica reports the new version ids for all three names. The source is the start-up and refresh logs, and the `secret_version_info` metric.
  - No replica runs an old image.
  - The provider dashboards show traffic on the new keys, and old-key traffic has dropped to zero for an agreed window. If a provider does not show per-key usage, see Open questions.
- **State lives in:** logs, metrics and provider dashboards.
- **If it fails:** a replica on an old version, or one that reports no version, means the check has not passed. Do not revoke. Find out why the replica did not refresh, for example a stuck timer thread or a failing store read. A missing metric is not a passed check. Use the log lines instead.

### Rollout step 10: Block pre-migration images, then revoke the old keys

- **Starts when:** rollout step 9 passes, and the soak period agreed by security and the service owner has elapsed (see Open questions).
- **What moves where**, in this order:
  1. **Deny policy first.** The registry denies every image that is not a post-migration image. Each image carries the commit it was built from as a label. The policy allows an image only if that commit is the code merge from rollout step 6 or a later commit on `main`. This block must be in place before any revocation. Otherwise a rollback to an old image would bring back a revoked key from that image's copy of `config/app.yaml`.
  2. **Revoke.** Security on-call revokes each old key at its provider, one at a time. Error rates are watched after each revocation.
- **State lives in:** the registry policy and the provider consoles. The store holds only the new versions.
- **If it fails:**
  - If errors appear after a revocation, the cause is a consumer missed in rollout step 1, not the migrated fleet. Do not re-enable the old key, because revocation is final. Issue a new key at the provider and write it to the store as a new version. Running pods pick it up within 5 minutes.
  - If the deny policy cannot be applied, do not revoke.

### Rollout step 11: Clean up and verify

- **Starts when:** rollout step 10 is complete.
- **What moves where:**
  - Old images that contain the old keys are removed from the registry, or kept only under the deny policy.
  - The central log service (30-day retention) is searched for the old and new key prefixes. Any hit is a logging defect and an exposure. Fix it and treat it as an exposure.
  - `deploy.md` is updated: readiness meaning, the rollback rule and the local-dev setup.
  - The revocation and the version ids are recorded in the change ticket.
- **State lives in:** the registry, logs, docs and the ticket.
- **If it fails:** a failed log search is an observability gap, not an outage. Run the search again later and record the gap.

### Rollback rule

Rolling back means redeploying an earlier image. The rows overlap on purpose. Before revocation, both key sets are valid, so either kind of image works. After revocation, only post-migration images work.

| Point in the rollout | Images you can roll back to | Why |
|---|---|---|
| Rollout steps 4 and 5 (before the merge) | Pre-migration images only. No post-migration image exists yet. | The old keys are active. |
| Rollout steps 6 to 9 | Pre-migration or post-migration images | Both key sets are valid. Post-migration images read the store, so the store must be reachable. |
| After rollout step 10 | Post-migration images only | The old keys are revoked. Pre-migration images hold revoked keys. |

---

## What happens when things fail

| Failure | Where | What happens | Response |
|---|---|---|---|
| Store unreachable or access denied at start-up | Runtime step 1 | Pod never becomes ready | Retry, then exit. Old pods keep serving. |
| Value empty or contains whitespace | Runtime steps 1 and 4 | Counts as a failed read | Start-up exits. A refresh keeps the last good value. |
| Refresh read fails | Runtime step 4 | Last good key is used | Warning logged. Retry in 5 minutes. |
| No successful refresh for 15 minutes | Runtime step 4 | Warning and metric | Investigate the timer thread and the store. |
| Key missing at request time | Runtime step 3 | That request fails | Programming error. Logged. |
| Config guard fails | Rollout step 6 | Merge blocked | Remove the `api_key` line. |
| Rollout halts on a pod that is not ready | Rollout steps 7 and 8 | Old pods keep serving | Diagnose, fix, redeploy. |
| Replica not on the new version at the check | Rollout step 9 | Revocation blocked | Find the cause. Do not revoke. |
| Errors after a revocation | Rollout step 10 | A consumer was missed | Do not re-enable. Issue a new key and store it. |
| Deny policy cannot be applied | Rollout step 10 | Revocation blocked | Do not revoke. |
| Log search finds a key | Rollout step 11 | Logging defect and exposure | Fix it. Treat it as an exposure. |
| Core dumps cannot be disabled | Runtime step 6 | Code merge blocked | Fix the container before merging. |

---

## Open questions

- **Store product and pod identity.** The brief does not name the managed secret store. It also does not say how a pod proves the `orders-api-prod` identity. This plan assumes the platform attaches the identity to the pod and that no password is stored in the app. Confirm both. The same question applies to the check job in rollout step 5.
- **Store and provider features.** The plan assumes the store returns a version id on each read, supports an exact "latest" read and writes access audit logs. It also assumes each provider can show per-key usage. If any of these is missing, runtime step 4 and rollout step 9 must change.
- **Overlapping keys at each provider.** The no-failure requirement assumes each provider allows two active keys at once. This must be verified for each provider before rollout step 4. If a provider allows only one key, the plan needs another way to overlap keys. This plan does not cover that.
- **Retry count.** The brief says "retry 3 times". This plan reads that as one first attempt plus 3 retries, about 6 seconds in total. Confirm whether 3 total attempts was meant.
- **Interim exposure.** From the code merge until revocation, the leaked keys stay valid and visible in git history. The brief ties revocation to fleet confirmation, so this plan does not shorten the window. Security must accept it or choose another path.
- **Soak period before revocation.** The brief does not set one. Security and the service owner must agree on it. Rollout step 10 cannot run until they do.
- **Rotation cadence after migration.** Not decided. Security has not chosen whether keys must rotate on a schedule, or how often. This plan does not choose one. The 5-minute refresh is a read interval, not a rotation policy.
- **Deny policy mechanism and owner.** The plan assumes the registry can read a build-commit label and enforce a deny rule. It does not say who owns the policy or how the registry applies it.
- **Pre-migration images in the registry.** They are blocked in rollout step 10. Whether and when they are deleted is not decided.
- **Sign-off and the check job.** The brief does not name who signs off the runtime code as ready (rollout step 4) or who starts the check job (rollout step 5). This plan gives both roles to the change owner and security on-call. Confirm.
- **Liveness probe.** The plan assumes one may exist and that it must not depend on the store. Confirm whether one exists.