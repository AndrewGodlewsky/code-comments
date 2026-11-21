# Plan: move orders-api third-party keys to the managed secret store

## What this is

Today `orders-api` reads three live third-party API keys (payments, email, geocoding) from `config/app.yaml`. That file is committed to git and copied into every container image. The app reads the file once, when its config module is first imported, and copies each key into its provider client. Changing a key means a new image and a redeploy.

This plan moves the keys into the managed secret store. At startup the app reads the keys into memory. It re-reads them every 5 minutes, so a new key version takes effect without a restart. The keys are changed with an overlap: each provider keeps the old key valid while the new key is issued and deployed. Old keys are revoked only after every running instance is confirmed on the new keys, so no customer request fails.

The main flow, from start to finish:

1. Confirm each provider can hold two active keys at once.
2. Create the store entries and access rules.
3. Issue a new key at each provider and write it to the store.
4. Ship code that reads keys from the store, and remove the keys from the config file.
5. Replace pods one at a time. Each new pod must load all three keys before it becomes ready.
6. Confirm every pod runs the new image and the new key versions.
7. Revoke the old keys.
8. Clean up the repo and the logs.

It is shaped this way so that old pods keep serving until new pods prove they are ready (the rollout uses `maxUnavailable: 0`), and so that old and new keys both work during the mix of pods.

## Terms

- **Secret store**: the managed service that holds secret values. It encrypts them at rest and gives every write a new version id.
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. `<env>` is `prod` or `dev`.
- **Version id**: the id the store gives each write. It is not secret, so logs may contain it.
- **KMS key**: the encryption key the store uses. Each environment has its own.
- **Service identity**: the identity a pod uses to log in to the store. Production pods use `orders-api-prod`.
- **Secret holder**: the in-memory object that holds the current value of each key. Its text form is redacted.
- **Refresh**: the background re-read of all three keys, every 5 minutes.
- **Readiness**: the answer `/healthz` gives. The rollout uses it to decide when a new pod may replace an old one.
- **Liveness**: a separate check that the process is alive. It does not depend on the store.
- **Provider overlap**: the provider accepts two active keys at the same time, so a new key can be added without revoking the old one.
- **Revoke**: disable a key at its provider so that it stops working.
- **Image digest**: a fixed fingerprint of one container image. It shows which image a pod runs.
- **Soak window**: the wait between confirming that all pods use the new keys and revoking the old ones.

## Scope and assumptions

- Keys in scope: payments, email and geocoding. All three have been in git history for two years and are treated as leaked.
- Git history is not rewritten. Rotating each key at its provider is what makes the old values useless.
- Production runs 4 replicas under `orders-api-prod`. Deploys are rolling, one pod at a time, with `maxUnavailable: 0`.
- The first thing to verify is provider overlap. The whole plan depends on it.
- Not decided: whether keys must be rotated on a regular schedule after this migration, and how often. This plan sets no cadence (see open questions).

---

## Part A: How the app reads keys at runtime

### 1. Startup

- **Starts:** the container process starts. Locally, `make run` starts it (see Part C).
- **What it does:**
  1. Loads `config/app.yaml`, which now holds only non-secret settings.
  2. Checks that the file has no `api_key` at any depth. If it has one, the process refuses to start.
  3. Logs in to the store with the pod's service identity.
  4. Reads the current version of each of the three secrets into the secret holder.
  5. Reports ready only when all three keys are loaded.
- **Where the data lives:** process memory only. No key value goes to disk, into environment variables or into logs. Logs show the secret name and version id.
- **Why at startup, not at import:** importing a module makes no network calls, and tests can give the app a fake store.
- **If the store cannot be reached:** the process makes one attempt, then up to 3 retries, 2 seconds apart. That is about 6 seconds in total. It then logs the failure without any secret values and exits with a non-zero code. Kubernetes restarts it with backoff, and the rollout halts (see the rollout step that replaces pods).
- **If a secret is missing, or the identity is denied:** this is treated the same as an unreachable store. The pod never becomes ready and exits after the same retries (see open questions).

### 2. Readiness and liveness

- **Starts:** the kubelet probes the pod.
- **Readiness** (`/healthz`): returns 200 only after all three keys are loaded. Before that, it returns a non-200 status. This changes today's behaviour, which returns 200 as soon as the HTTP server listens. The deploy document must be updated when this ships.
- **Liveness:** a separate check that returns 200 while the process is serving. It does not depend on the store, so a store outage cannot restart healthy pods.
- **If a new pod never becomes ready:** the rollout halts. Old pods keep serving on their current keys. This is the main protection against a bad store, bad access rules or a missing secret reaching customers.

### 3. Refresh every 5 minutes

- **Starts:** a timer in each process. Each run waits a random jitter first, so the 4 replicas do not call the store at the same moment.
- **What it does:** reads the current version of each of the three secrets. If a version id has changed, it swaps the new value into the secret holder. Each key is swapped on its own, and each swap is atomic.
- **Where the data lives:** memory. The last good value of each key stays in use until a newer one is read successfully.
- **Logs:** each swap logs the secret name, the old version id and the new version id. Values are never logged.
- **If a re-read fails** (store down, throttled, or an access error): the process keeps the last good value for that key, logs a warning with the secret name and error class, and tries again at the next run. Requests are not affected.
- **Known limit:** a refresh cannot tell a good new version from a bad one. A version the provider rejects will be used within 5 minutes. The protections are the provider check before rollout (see the step that issues new keys) and an alert on provider 401 and 403 responses per pod.

### 4. Provider calls

- **Starts:** each provider call (charge, email send, geocode).
- **What it does:** the client asks the secret holder for the current key on every call. It does not copy the key when it is built. A copy would freeze the key for the life of the process and defeat the refresh.
- **Keeping keys out of logs:**
  - The secret holder prints as a redacted value, so tracebacks and debug output cannot show a key.
  - HTTP logging either scrubs the `Authorization` header or is turned off.
  - Error messages do not include request headers or key values.
- **If a provider call fails:** it is handled as it is today. A store problem does not touch the request path, because requests use the value already in memory.

### 5. Shutdown and host settings

- **Starts:** pod termination.
- **What it does:** nothing is saved. The secret holder is cleared on a best-effort basis.
- **Host settings:** production containers run with core dumps disabled, because a core dump would write key values to disk. The platform team confirms the swap and memory-dump settings.
- **If this check fails:** the platform team must fix it before the rollout starts. Until then, the "never on disk" requirement is not met.

---

## Part B: Rollout

Run the steps in order. Each step needs the one before it to pass.

### 1. Confirm provider overlap

- **Starts:** plan approval. Security on-call and the service owner do this together.
- **What it does:** for payments, email and geocoding, check the provider's documentation or support. Confirm that two keys can be active at once, and that creating a new key does not revoke the old one. Nothing in our systems changes.
- **Where the record lives:** the rollout ticket. It holds only the provider name and the answer.
- **If a provider does not allow overlap:** stop, and do not rotate that provider. Rotating a key that other pods still use causes an outage, which the requirements forbid. Escalate to security for a different design, such as an approved provider-side maintenance window.

### 2. Create store entries, KMS keys and access rules

- **Starts:** security on-call, through infrastructure-as-code or the store console, after the overlap check passes.
- **What it does:**
  - Creates `orders-api/prod/*` and `orders-api/dev/*`, each environment with its own KMS key.
  - Gives `orders-api-prod` read-only access to `orders-api/prod/*` and nothing else.
  - Lets only the security on-call role write prod secrets.
  - Lets engineers read `orders-api/dev/*` only.
- **Where the data lives:** the store, encrypted with the environment's KMS key. The access rules live in infrastructure-as-code.
- **Checks:** a test read as `orders-api-prod` succeeds on `orders-api/prod/*` and fails on any other path. A test read as an engineer fails on `orders-api/prod/*`.
- **If it fails:** nothing has changed for customers. Fix the access rules before continuing. Any gap would show up as a non-ready pod during the rollout, which halts it.

### 3. Issue new keys at each provider

- **Starts:** security on-call, after the access checks pass.
- **What it does:** creates a new key at each provider and tests it with a read-only call. The old key stays active. This is the provider check that protects the refresh from a bad key.
- **Where the data lives:** the provider dashboard. New key values never go into tickets, chat, the repo or logs.
- **If the provider cannot issue a key:** nothing has changed and the old key still works. Retry later.
- **If the test call fails:** discard that new key, create another, and do not write it to the store.

### 4. Write the new values to the store (version 1)

- **Starts:** security on-call, once the test call passes for that key.
- **What it does:** writes each new value to `orders-api/prod/<name>`. The store assigns the version ids. Each version id is recorded in the rollout ticket.
- **Where the data lives:** the store. Running pods are not affected. They keep their old keys from the config file in their image until they are replaced.
- **If the write fails:** nothing changes. Retry the write.

### 5. Staging, then the prod rollout

- **Starts:** a pull request with the Part A code change, the Part D config change and the deploy document update. Merging to `main` starts CI and builds the image.
- **Staging:** deploy the image to staging with staging keys, and check:
  - startup and readiness behaviour;
  - a refresh that picks up a new version;
  - a failed re-read that keeps the last good value and logs a warning;
  - a store outage at startup, which gives 3 retries and then a non-zero exit;
  - a denied identity, which never becomes ready;
  - no key values in logs or on disk.
- **If staging fails:** do not deploy to prod. Fix the problem and repeat staging.
- **Prod rollout:** the image is built from `main` and contains no `api_key`. Pods are replaced one at a time. For each new pod:
  1. It starts with the new image and reads all three keys from the store with `orders-api-prod`.
  2. It becomes ready only when all three keys are loaded.
  3. Only then is one old pod stopped.
- **Mixed fleet during the rollout:** old pods use the old keys from their image. New pods use the store keys. Both sets are valid because of the overlap check, so customers see no failures from the mix.
- **If a new pod fails to start** (store unreachable, identity denied, key missing): it retries as the startup step describes, exits non-zero, and is restarted with backoff. The rollout halts and old pods keep serving.
- **Recovery:** fix the cause, then continue the rollout or roll back (Part E).

### 6. Confirm every instance is on the new keys

- **Starts:** the rollout reports complete, with all 4 replicas on the new image.
- **What it does:** a check only. Nothing changes.
- **Checks, all required:**
  - All 4 pods run the new image digest. No pod runs an older image.
  - Each pod's logs show the version ids recorded when the keys were written, for all three keys. This happens at startup or at a refresh. The log window covers at least one full refresh cycle after the last pod was replaced.
  - If a newer version id exists, check against the newest id and repeat.
- **Where the data lives:** the cluster's pod list, and the central log service (30-day retention).
- **If any check fails:** stop. Find out why that pod is not on the new key or the new image. Do not revoke anything.

### 7. Revoke the old keys

- **Starts:** the confirmation step passes for all 4 replicas, and security on-call approves. This is the only point at which an old key may be revoked.
- **What it does:** revokes each old key at its provider, one provider at a time.
- **Watch:** after each revocation, watch for 401 and 403 responses and the error rate for 15 minutes.
- **Where the data lives:** the provider dashboard.
- **If a revoked key was still in use:** the revocation cannot be undone. If the new key is still valid, write it to the store and treat the incident as customer impact. This is why the confirmation step is strict.
- **Soak window:** the owner decides how long to wait between confirmation and revocation. This plan sets no value (see open questions).

### 8. Clean up the repo and the logs

- **Starts:** after revocation.
- **What it does:** confirms that the current tree has no live key strings and no `api_key`. The pull request already removed `api_key` from the config, so this is the final check. Git history is not rewritten.
- **Log check:** searches the central logs for the three old key strings.
- **If a hit is in the logs:** record it as an incident note. The keys are already revoked, so no further rotation is needed.
- **If a hit is in an active config or image:** remove it and rebuild.

---

## Part C: Local development

### 1. Running `make run`

- **Starts:** a developer runs `make run`.
- **What it does:** reads the same non-secret `config/app.yaml`. Then it reads `orders-api/dev/*` with the developer's dev-only identity, using the same loader as production.
- **Where the data lives:** memory only. No `.env` file, shell variable or file on disk holds key values.
- **Dev keys:** provider sandbox keys or the team's agreed test keys. Live keys are never used locally.
- **Production protection:** the loader refuses to run in the `prod` environment. The developer identity has no read access to `orders-api/prod/*`.
- **If the developer has no dev access:** the process refuses to start and prints a clear message. The documented fallback is to point `base_url` at a provider sandbox or a local stub. The fallback is opt-in and never reads production.
- **If the store is unreachable locally:** the same retry-then-exit behaviour as the startup step. Developers can use stub mode.

---

## Part D: CI guard

### 1. Block `api_key` in config

- **Starts:** every pull request, and every push to `main`.
- **What it does:** parses `config/app.yaml` as YAML and fails if any key named `api_key` appears at any depth. It also searches the whole current tree for the known live key prefixes (`pk_live_`, `ml_live_`, `geo_live_`).
- **Image build:** the build fails if the built image's `config/app.yaml` contains `api_key`.
- **Required check:** the job is a required status check on `main`, so merging cannot skip it.
- **If it fails:** the pull request is blocked. The author removes the key and uses the store.
- **Limit:** CI cannot stop a direct commit that bypasses branch protection. Branch protection is the control for that case.

---

## Part E: Rollback

### 1. Roll back a bad deploy

- **Starts:** an alert, or a failed readiness check during the rollout.
- **What it does:** redeploys an earlier image.
- **Constraint:** before the old keys are revoked, a pre-migration image still works, because its keys are still valid. After revocation, a pre-migration image holds revoked keys and must never be deployed. Roll back only to migration-era images from then on.
- **Enforcement:** the deploy pipeline rejects any image whose config contains `api_key`. This is the same check as the CI guard, applied at deploy time.
- **If the store is the cause:** roll back the store, not the image. Set the current version back to the previous version id, as recorded when it was written. The app picks up the change at its next refresh. Running pods are not restarted.

---

## Open questions

1. **Rotation cadence (not decided):** security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan sets no cadence. The 5-minute refresh is not a rotation policy.
2. **Provider overlap:** the overlap check must be answered for each provider before any rotation. If a provider cannot keep two keys active, this plan does not apply to that provider as written.
3. **Soak window before revocation:** the owner must decide how long to wait after all pods are confirmed before revoking old keys. The plan sets no value.
4. **Retry count:** the plan reads "retry 3 times, 2 seconds apart" as one initial attempt plus 3 retries, about 6 seconds in total. This reading needs confirmation.
5. **Missing secret with a reachable store:** the plan treats it as a startup failure with the same retry budget. This needs confirmation.
6. **Bad version in the store:** a refresh cannot detect a version the provider rejects. Decide whether to add a validation call before a refresh swaps a value, or to rely on the provider check and the 401/403 alert.
7. **Refresh jitter and version-id reporting:** confirm the jitter window. Decide whether version ids should also be exposed on an internal endpoint, not only in logs. An endpoint would make the confirmation step faster.
8. **Core dumps and host memory:** the platform team must confirm the host settings in Part A before the rollout starts.