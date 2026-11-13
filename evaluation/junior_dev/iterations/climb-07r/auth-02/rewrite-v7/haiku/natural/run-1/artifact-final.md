# Migration plan: orders-api third-party API keys into the managed secret store

## Summary

Today, `orders-api` reads three live provider keys from `config/app.yaml`. That file is committed to git and copied into every container image, so the keys are effectively public and can only change with a new image. This plan moves the keys into the managed secret store. The app loads them at startup, refreshes them every 5 minutes, and every key is rotated at its provider. The rollout sets up the store and access rules, issues and stores new keys, ships the new code with a clean config, rolls it out, confirms every running pod uses the new keys, and only then revokes the old keys, one provider at a time. Old keys stay valid until every pod is confirmed on new keys, so no customer request should fail.

## Terms

- **Provider**: an outside company whose API we call. Here: payments, email and geocoding.
- **Secret store**: the managed service that holds secret values by name. Each write creates a new version.
- **Version id**: the id the store gives each written version of a secret. Logs may show version ids, never values.
- **KMS key**: the encryption key the store uses to encrypt secrets at rest. There is one per environment.
- **Workload identity (service identity)**: the account a running app uses to log in to the store. Prod pods run as `orders-api-prod`.
- **Environment (`APP_ENV`)**: a non-secret setting that picks `dev` or `prod`. It defaults to `dev`.
- **Pod**: one running copy of the app in the cluster. Prod runs 4.
- **Readiness probe**: a check the cluster uses to decide whether a pod gets customer traffic. It calls `GET /healthz`.
- **Liveness probe**: a check the cluster uses to decide whether to restart a pod.
- **Rolling deploy with `maxUnavailable: 0`**: pods are replaced one at a time. An old pod is stopped only after its replacement is ready.
- **Atomic reference**: a single variable that is swapped in one step, so a reader sees the old value or the new one, never a half-written mix.
- **Jitter**: a small random delay, so all pods do not read the store at the same moment.
- **Secret accessor**: the one function that provider clients call to get the current key.
- **`SecretValue`**: a wrapper type that prints as `***`, so a key does not leak when logged.
- **Revoke**: stop a key from working at the provider. Disable first, then delete.
- **CI gate**: an automatic check that must pass before a change can merge or an image can be built.
- **Migration log**: the record of what was done, with version ids, pod names and timestamps.

## Assumptions

- The store holds each secret as a named item with immutable versions. A write returns a version id. A read returns the latest version.
- Prod runs 4 replicas under `orders-api-prod`, with rolling deploys and `maxUnavailable: 0`.
- "Retry 3 times, 2 seconds apart" means 1 attempt plus 3 retries. This is unconfirmed (see open questions).
- Old container images that embed the keys are treated as sensitive.
- Git history is not rewritten. The three old keys are treated as leaked.

## Part A: How the app reads keys at runtime

**Today:** the app reads `config/app.yaml` once at process start. Each provider client copies its key into itself when it is built. Changing a key means a new image and a redeploy.

**Rules for every step in Part A:**

- Key values live only in process memory. They never go to disk, into environment variables or into logs. Logging version ids is fine.
- Key values are wrapped in `SecretValue`, which prints as `***` in `repr` and `str`.
- Exception handlers and HTTP client debug logging must not print request headers. The `Authorization` header is the most likely leak.
- On exit, values are dropped from memory on a best-effort basis. Nothing is persisted.

### Part A, step 1: Startup load (before ready)

- **Starts when:** the process starts.
- **What it does:** reads `orders-api/<env>/payments_api_key`, `orders-api/<env>/email_api_key` and `orders-api/<env>/geocoding_api_key` from the store, using the workload identity for that environment. `<env>` comes from `APP_ENV`.
- **Guard:** if `APP_ENV=prod` and the identity is not `orders-api-prod`, the app refuses to start.
- **Where state lives:** an in-memory map from secret name to (value, version id, loaded-at time).
- **Retries:** 1 attempt plus 3 retries, 2 seconds apart. All three secrets must load before the app is ready.
- **If it fails:** after the last retry, the app logs the error class and the secret name, never the value, and exits with a non-zero code. The pod never becomes ready. During a rollout, the old pods keep serving.

### Part A, step 2: Readiness gate

- **Starts when:** the HTTP server starts.
- **What it does:** the server may start listening early. `GET /healthz` returns 503 until step 1 succeeds, then 200 with `{"status": "ok"}`. Today `/healthz` returns ok as soon as the server listens, so this is a change.
- **Where state lives:** an in-memory "keys loaded" flag.
- **If it fails:** the pod gets no traffic. After startup, readiness does not depend on the store. If it did, a store outage would make every pod unready and drop customer traffic.
- **Liveness:** the liveness probe uses its own endpoint, for example `/livez`, which does not depend on the store. Otherwise a store outage could restart pods.

### Part A, step 3: Client access

- **Starts when:** a provider call is made.
- **What it does:** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in their constructor. Each request reads the current value through the secret accessor.
- **Where state lives:** the current value sits in an atomic reference, so a request sees either the old or the new value.
- **If it fails:** nothing to do here. The accessor only returns values that step 1 already loaded.

### Part A, step 4: Periodic refresh (every 5 minutes)

- **Starts when:** a background timer fires every 5 minutes, with a small jitter.
- **What it does:** for each secret, reads the latest version. If the version id has changed, it checks that the value is non-empty and well-formed. If the check passes, it swaps the value in and logs `rotated <name> version=<id>`. A value that fails the check is not swapped in, so the last good value stays.
- **Each secret is independent.** One failure does not block the others.
- **Where state lives:** in memory.
- **If it fails:** the app keeps the last good value for that secret, logs a warning with the error class, and tries again on the next tick. It does not exit and does not fail readiness.

### Part A, step 5: Bad new key

- **Starts when:** a provider answers 401 or 403 after a refresh has swapped in a new value.
- **What it does:** the client logs the secret name and version id. The request fails as it would today.
- **Prevention:** each new key is validated before it is written to the store, and before any old key is revoked (Part B). Keeping the previous version as a one-cycle fallback is an open question.

## Part B: Rollout

### Part B, step 1: Create the store layout and access rules

- **Starts when:** the migration issue is approved.
- **What it does:** creates `orders-api/dev/*` and `orders-api/prod/*`, each with its own KMS key.
- **Access rules:**
  - `orders-api-prod` gets read on `orders-api/prod/*` and nothing else, plus decrypt on the prod KMS key only.
  - The security on-call engineer is the only one who can write `orders-api/prod/*`.
  - Engineers get no read or write access to prod.
  - Engineers get read and write on `orders-api/dev/*`.
- **Where state lives:** the store policy and KMS key policy, under version control in the infrastructure repo.
- **If it fails:** if the prod identity cannot read, Part A step 1 fails at startup and the rollout halts before any customer impact. If engineers can read prod, stop and fix the policy before continuing.

### Part B, step 2: Issue, check and store new keys

- **Starts when:** step 1 is complete and verified.
- **What it does:** the security on-call engineer creates a new key at each provider. The old keys stay valid. Security checks each new key with a read-only provider call made outside the app, then writes it to `orders-api/prod/<name>`. The store returns a version id, which goes in the migration log.
- **Where state lives:** each provider holds two valid keys. The store holds the new values. Running pods still use the old keys from their images.
- **If it fails:** if a provider will not issue a second key, or the check call fails, do not write to the store. Re-plan. Revoke nothing. Engineers never see key values.

### Part B, step 3: Move local development off live keys

- **Starts when:** it can run in parallel with step 2.
- **What it does:** creates sandbox or test keys at each provider and stores them under `orders-api/dev/*`. Changes `make run` to set `APP_ENV=dev` and load these keys through the developer's own identity. Removes the live keys from any local copy of the config. Today `make run` uses the live keys, so this step is needed for local work to keep running without prod secrets.
- **Where state lives:** dev keys live only in the dev store, and in memory during a run.
- **If it fails:** if a provider has no sandbox, the developer uses a local stub for that provider. Prod keys never go on laptops. Dev keys never go on disk.

### Part B, step 4: Ship the code and clean the config, in one merge

- **Starts when:** step 2 is complete and step 3 is merged.
- **What it does:**
  - Merges the runtime code from Part A.
  - Removes every `api_key` line from `config/app.yaml`. Non-secret settings stay: app name, port, log level, base URLs, timeouts and the from-address.
  - Adds an integration test. It runs the app against a fake store and a fake provider with known key values, then fails if those values appear in stdout, stderr or log output.
  - Adds a CI gate. It is a required check on `main`. It fails any change that adds an `api_key` key to `config/app.yaml`, and it fails on common secret patterns in that file. It also runs on the built image's copy of the config.
  - CI builds one image. The image's config contains no keys.
- **Where state lives:** the repo, and the image.
- **If it fails:** a failing CI check means no image is built, so nothing reaches production.

### Part B, step 5: Roll out the new image

- **Starts when:** the image from step 4 is available.
- **What it does:** the rolling deploy replaces one pod at a time. Each new pod runs Part A steps 1 and 2 before an old pod is stopped.
- **Where state lives:** each new pod logs the version id of each of the three keys. Old pods still hold the old keys.
- **If it fails:** a new pod that cannot read the store retries, exits and never becomes ready. The rollout halts and the old pods keep serving. Fix the cause and redeploy. Customers are not affected, because the old keys are still valid.

### Part B, step 6: Confirm every instance uses the new keys

- **Starts when:** all 4 replicas run the new image.
- **What it does:** checks that every running pod, including any leftover pods from the old set, logs the new version id for all three keys. The central log service keeps logs for 30 days, so the check queries it. The check runs only after a full 5-minute refresh cycle has passed since the last store write. Where the provider offers per-key usage data, it must show no requests with the old keys.
- **Where state lives:** the evidence (version ids, pod names and timestamps) goes in the migration log.
- **If it fails:** if any pod still shows an old version id, or refresh warnings persist, do not revoke. Investigate, then repeat this check.

### Part B, step 7: Revoke old keys, one provider at a time

- **Starts when:** step 6 has passed and security has signed off.
- **What it does:** if the provider can disable a key, disable it first and watch error rates for an agreed period. Then delete it. Start with the provider that has the lowest traffic.
- **Where state lives:** at the provider only.
- **If it fails:** a revoked key cannot be restored, which is why step 6 and the disable period come first. If error rates rise after disabling, re-enable the old key if the provider allows it, and return to step 6. If it does not allow that, write a new key and repeat steps 2 to 6 for that provider.

### Part B, step 8: Lock down rollback

- **Starts when:** right after step 7, for each provider.
- **What it does:** deploy tooling blocks any image built before step 4. Those images contain revoked keys and would fail. Rollback targets are limited to images built after the migration.
- **Where state lives:** the deploy tooling's allow-list.
- **If it fails:** if a pre-migration image is deployed by mistake, the new pods fail at startup or at the first request. Because `maxUnavailable: 0` keeps the other pods running, the impact is limited to that rollout.

### Part B, step 9: Clean up and close out

- **Starts when:** steps 7 and 8 are complete.
- **What it does:** asks each provider to confirm that the old keys are deleted. Removes old local copies. Updates `deploy.md` for local development, readiness behavior and the rotation procedure. Records the changes in the migration log.
- **Where state lives:** the docs and the migration log.
- **If it fails:** if a stale local copy is found, treat it as a new exposure. Repeat steps 2 to 7 for that key.

### Later rotation (after the migration)

Write the new key to the store as a new version. Running pods pick it up within 5 minutes through Part A step 4, so no restart is needed. Confirm with the step 6 check. Then revoke the old key. How often this happens is not decided (see open questions).

## Open questions

1. **Rotation cadence.** Not decided. Security must decide whether keys rotate on a schedule after the migration, and how often. This plan does not choose one.
2. **Provider capabilities.** Do the three providers support two active keys at once, a disabled state before delete, and per-key usage data? Steps 2, 6 and 7 depend on all three.
3. **Retry count.** Does "retry 3 times" mean 3 total attempts, or 1 plus 3 retries? This plan assumes 1 plus 3.
4. **Staging.** The deploy doc mentions only prod and local. Is there a staging environment that should go through the rollout first?
5. **Liveness endpoint.** Which endpoint does the liveness probe use today? If it is `/healthz`, Part A step 2 needs a separate liveness endpoint.
6. **Bad-key fallback.** Should the app keep the previous version as a one-cycle fallback on 401 or 403 during the migration (Part A step 5), or rely only on the checks in Part B step 2?
7. **Rollback window.** How long must the old keys stay valid for rollback, given that a pre-migration image cannot be deployed after step 7?
8. **Cluster access.** Can engineers `exec` into prod pods or read their memory? If they can, they could read keys in memory despite the store policy. Security must decide.
9. **Store labels.** Does the store support a "current" label? This plan reads the latest version. If the store offers a label, Part A step 4 may use it instead.
10. **Image registry.** Who can pull old images that contain the keys? Access should be restricted until step 8 is complete.