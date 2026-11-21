# Plan: move the `orders-api` API keys into the secret store

## What changes, in short

Today the payments, email and geocoding API keys sit in `config/app.yaml`. That file is committed to git and baked into every container image. The app reads it once at import time, and each provider client copies its key at construction. Changing a key therefore means a new image and a redeploy.

After this plan:

- The keys live only in the managed secret store, under `orders-api/<env>/<name>`. The three names are `payments_api_key`, `email_api_key` and `geocoding_api_key`. The store encrypts them at rest with a per-environment KMS key (a managed encryption key) and gives every write a new version id.
- `<env>` is `prod` or `dev`. The app reads it from the `APP_ENV` environment variable. This is the only environment setting involved, and it is not a secret.
- The app loads the keys into process memory at startup and re-reads them every 5 minutes. Provider clients ask for the current key on every request instead of copying it once.
- All three keys are rotated at their providers, because the old ones have been in git history for two years and count as leaked. Git history is not rewritten.

The order of the rollout is what keeps customer requests working:

1. Deploy the new mechanism with the same key values. Only the delivery path changes.
2. Rotate by writing new values to the store. No redeploy is needed.
3. Revoke the old keys only after every running instance is confirmed to be using the new ones.

Terms:

- "Store" is the managed secret store.
- "Version id" is the id the store gives every write. It is not secret and may be logged and shown.
- Key values must never be logged, written to disk or placed in environment variables.

Deploy background:

- Production runs 4 replicas (pods) under the service identity `orders-api-prod`.
- Deploys are rolling, one pod at a time, with `maxUnavailable: 0`. A new pod must pass its readiness probe (`GET /healthz` returns 200) before an old pod is stopped.
- If a new pod never becomes ready, the rollout halts and the old pods keep serving.
- Rollback means redeploying an earlier image.

## Part 1: Rollout

Each step says what starts it, what moves where, where the state lives, and what happens on failure.

### 1. Set up access policies

- **Starts when:** the plan is approved. Security owns this step.
- **What moves:** nothing yet. Policies are created as follows.
  - Identity `orders-api-prod`: read-only on `orders-api/prod/*`, plus decrypt-only on the prod KMS key if the store requires it. Nothing else.
  - Security on-call: write on `orders-api/prod/*`.
  - Engineers: read and write on `orders-api/dev/*`. No access to `orders-api/prod/*` and no use of the prod KMS key.
- **State lives in:** the store's policy configuration.
- **Check:** test with real identities before moving on.
  - An engineer cannot read prod.
  - `orders-api-prod` can read prod but cannot write it and cannot read dev.
  - Security on-call can write prod.
- **If it fails:** stop. Nothing depends on these policies yet, so there is no customer impact.

### 2. Create the secrets

- **Starts when:** step 1 is verified.
- **What moves:**
  - Security on-call copies the three current key values from `config/app.yaml` into `orders-api/prod/{payments,email,geocoding}_api_key`. This is the first write of each secret. Record the three version ids as the baseline.
  - Sandbox keys from each provider go into `orders-api/dev/*`, so local development never needs prod keys.
- **State lives in:** the store, encrypted at rest with the per-environment KMS key.
- **Check:** security on-call tests each stored prod value with a harmless provider call (for example a read-only or "who am I" endpoint). This matters because the app's readiness check only proves a value was fetched, not that it is correct. A bad copy would pass readiness and then fail customer requests.
- **If it fails:** correct the value and write again. Each write is a new version, and nothing reads the secrets yet, so there is no customer impact. Update the recorded baseline version ids.

### 3. Build the code change (one pull request)

- **Starts when:** step 2 is done and checked, so a merge can safely deploy.
- **What moves:** the keys stop being read from the file and are read from the store instead.
  - Add `app/secrets.py` with `load()`, `refresh()` and `get(name)`. Part 2 describes its behavior.
  - Change `PaymentsClient`, `EmailClient` and `GeocodingClient` to call `secrets.get("<name>")` on every request. They must no longer store the key as an attribute.
  - `/healthz` additionally returns the loaded version ids as `secret_versions`. It never returns values.
  - Delete the three `api_key` lines from `config/app.yaml`.
  - Add a CI check that fails if `config/app.yaml` contains an `api_key` key at any depth.
  - `make run` sets `APP_ENV=dev`.
  - Make sure no log line, exception message or HTTP debug output can include the `Authorization` header or a key value.
- **State lives in:** the repo. Merging to `main` triggers the usual image build.
- **Check:**
  - Tests cover load retry, refresh and refresh failure.
  - A deliberate change that re-adds `api_key` is shown to fail CI.
  - The built image contains no keys.
- **If it fails:** CI blocks the merge. Fix and push again.

### 4. Deploy with the normal rolling deploy

- **Starts when:** the pull request is merged and the image is built.
- **What moves:** pods are replaced one at a time with `maxUnavailable: 0`. Each new pod loads the baseline key versions from the store (runtime steps R1 and R2), reports ready, and only then is an old pod stopped.
- **State lives in:** each pod's memory. Old pods still hold the keys from their baked-in `app.yaml`.
- **If it fails:** a new pod that cannot load all three keys exits non-zero and never becomes ready, so the rollout halts and the old pods keep serving. Customers are unaffected. Fix the cause (policy, secret name, store outage) and redeploy. If needed, roll back to the previous image, which still works because the old keys are still valid.

### 5. Verify the deployment

- **Starts when:** all 4 replicas have been replaced.
- **What moves:** nothing. Check each pod's `/healthz`. The check passes if every pod is ready and reports the baseline version ids from step 2. Also confirm that a log search finds no key values.
- **State lives in:** pod memory and the central logs.
- **If it fails:** do not rotate. Investigate and, if needed, roll back as in step 4. The old keys are still valid, so rollback is safe.

### 6. Rotate the keys at the providers

- **Starts when:** step 5 passes. Security on-call does the work, one key at a time.
- **What moves:**
  1. Create a new key at the provider. The old key stays active.
  2. Test the new key with a harmless provider call before it goes anywhere else.
  3. Write it to `orders-api/prod/<name>`, which creates a new version id. Running pods pick it up at their next refresh, within 5 minutes (R4).
- **State lives in:** the provider (both keys active) and the store (new version).
- **If it fails:** if the provider call fails, delete the new key and do not write to the store. If a bad value was already written, write the old value back as a newer version. Pods pick that up within 5 minutes, and the old key is still active throughout, so requests keep working.

### 7. Confirm every instance uses the new keys

- **Starts when:** at least 5 minutes plus a margin (for example 10 minutes in total) have passed since the write.
- **What moves:** nothing. Check `/healthz` on each running pod directly (for example by port-forward), not through the load balancer, which would only reach one pod at a time. The gate passes only if all of these hold.
  - Every pod reports the new version id for that key.
  - No pod has logged a refresh warning for it.
  - Provider call error rates are normal.
- **State lives in:** pod memory (version ids) and the logs.
- **If it fails:** do not revoke. A pod stuck on the old version has a refresh problem, which its warning log will show. Fix the cause. Restarting that pod also works, because a starting pod loads the latest version.

### 8. Revoke the old keys

- **Starts when:** step 7 has passed for that specific key. Re-check pod versions immediately before revoking, because pods may have restarted or been added since.
- **What moves:** revoke the old key at the provider, one provider at a time. Then watch provider call errors for about 15 minutes before the next one.
- **State lives in:** the provider.
- **If it fails:** revocation cannot be undone, so the step 7 gate is the real protection. If errors appear, find the pod still using the old key. Pre-migration images and old local checkouts still carry the revoked keys. Local runs on old checkouts will stop working, which is expected. Tell engineers to update.

### 9. Close out

- **Starts when:** all three old keys are revoked.
- **What moves:** update `deploy.md`.
  - Say that keys come from the store, and that `make run` uses dev keys.
  - Say that rollback to any image from before this migration no longer works, because its baked-in keys are revoked. Roll back only to the migration image or later.
  - Say that the CI check blocks `api_key` in `config/app.yaml`.
- **State lives in:** the repo.
- **If it fails:** nothing at runtime depends on this step.

## Part 2: How the app reads keys at runtime

The state is a map in process memory: `name -> (value, version_id)`. The source of truth is the store. Nothing is written to disk or to environment variables.

- **R1. Startup load.**
  - **Starts when:** the process starts, before the HTTP server accepts traffic.
  - **What moves:** `secrets.load()` reads the latest version of `orders-api/<env>/<name>` for all three names into the in-memory map. The store identity is the pod's service identity (`orders-api-prod` in prod, the developer's own credentials locally). A missing or empty `APP_ENV` is an error, never a default to prod.
  - **If it fails:** any failure counts as a failed load for the whole set. Retry 3 times, 2 seconds apart, so there are 4 attempts in total. Then exit with a non-zero code. The orchestrator keeps restarting the pod, and a rolling deploy halts if this happens during a rollout.
- **R2. Readiness.** `/healthz` returns 200 with `{"status": "ok", "secret_versions": {...}}` once the server is up. Because the load happens before the server accepts traffic, 200 means all three keys are held. Readiness does not depend on the store afterwards, so a store outage does not take all 4 pods out of service.
- **R3. Use.** Each client calls `secrets.get(name)` when it builds a request. This reads memory under a lock and makes no network call. A request already in flight keeps the key it started with, and the next request uses whatever is current.
- **R4. Refresh every 5 minutes.** A background thread calls `refresh()`. It fetches the latest version of each secret. If the version id changed, it swaps in the new `(value, version_id)` pair as one step and logs the old and new version ids.
- **R5. Refresh failure.** If the store is unreachable, errors, or returns an empty value, the app keeps the last good value for that secret. It logs a warning with the secret name, the error and the held version id, but never the value. It tries again at the next interval, with no extra retries, and it does not exit. A pod can therefore sit on an old key without anyone noticing, which is why step 7 checks version ids on every pod. Consider an alert on repeated refresh warnings.

Local development: `make run` sets `APP_ENV=dev`, so the app reads `orders-api/dev/*` with the developer's own credentials. Engineers have no access to prod values.

## Assumptions to confirm before starting

- Each provider allows two active keys at once. Without that, step 6 cannot avoid a window of failing requests, and the plan must change.
- Nothing else (other services, scripts, jobs) uses these three keys. If something does, it must be moved before step 8.
- Sandbox keys exist at each provider for dev.

## Open question

Security has not decided whether keys must also be rotated on a regular schedule after this migration, or how often. This plan sets no cadence. Once Security decides, the rotation procedure (steps 6 to 8) can be reused as is, because rotating needs no redeploy.