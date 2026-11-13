# Plan: move API keys into the secret store

## Summary

Today `orders-api` reads three live provider keys (payments, email, geocoding) from `config/app.yaml` once, when the process starts. That file is in git and copied into every image, so changing a key needs a new image and a redeploy. This plan moves the keys into the managed secret store. Each pod loads all three keys into memory before it reports ready, then re-reads them every 5 minutes, so a new key takes effect without a restart. The old keys count as leaked. Git history is not rewritten, so each key is replaced at its provider, and the old key is revoked only after every running pod uses the new one. The rollout order keeps keys present at all times, so no customer request fails.

## Terms

- **Secret store**: the managed service that holds secrets. It encrypts them at rest and gives every write a new version id. The product is not named yet (see open questions).
- **Secret path**: where one secret lives, `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`.
- **`<env>`**: `prod` or `dev`. The app sets it from `APP_ENV`.
- **APP_ENV**: the app setting that picks `<env>`. `make run` sets it to `dev`.
- **KMS key**: the encryption key the store uses. There is one per environment.
- **Version id**: the id the store gives each written value. Safe to log.
- **Service identity**: the account a pod runs as. Prod pods run as `orders-api-prod`.
- **Pod**: one running copy of the app in the cluster. Prod runs 4.
- **Rolling deploy**: replacing pods one at a time, so old pods keep serving until new ones are ready.
- **Readiness**: a pod is ready when `GET /healthz` returns 200.
- **Provider**: the third-party company that issues a key.
- **Revoke**: disable a key at its provider so it stops working.
- **Last good value**: the last key value the app read from the store successfully.

## How the app reads keys at runtime

Rules for every step:

- Key values stay in process memory. They never go on disk, into environment variables or into logs. Logging version ids is fine.
- No customer request may fail because a key is missing or revoked. The rollout order keeps this true.

1. **Load keys at startup.**
   - Starts when the process starts. It runs before `/healthz` can return 200.
   - `load()` in the new `app/secrets.py` reads `orders-api/<APP_ENV>/payments_api_key`, `email_api_key` and `geocoding_api_key` into memory.
   - State: process memory only.
   - If the store cannot be reached, it retries 3 times, 2 seconds apart. If it still fails, or a key is missing, the process exits with a non-zero code. The app never runs with partial keys, so the pod never becomes ready.

2. **Report readiness.**
   - Starts when step 1 succeeds.
   - `/healthz` returns 200 only after all three keys are in memory. Today it returns 200 as soon as the server listens, so this changes.
   - It also returns `secret_versions`: the version id of each key in memory. It never returns a value.
   - State: the memory from step 1.
   - If step 1 fails, the pod never returns 200, and the rollout halts.
   - After startup, `/healthz` stays 200 while the pod holds all three keys. A failed or slow refresh does not change it, so a running pod never goes unready. Making a running pod unready during a store outage would remove pods that still hold valid keys.

3. **Refresh every 5 minutes.**
   - Starts on a 5-minute timer in the running process. The next refresh runs 5 minutes later, whether this one succeeded or not.
   - `refresh()` re-reads all three secrets. Each one that reads successfully replaces its in-memory value in one step, so a request never sees a half-written value.
   - Keys are independent, so one failure does not block the others.
   - State: process memory. Warnings go to the central log service, which keeps them 30 days.
   - If a read fails, that secret keeps its last good value and a warning is logged. The warning names the secret and its version id, never the value. The read is retried at the next refresh. `/healthz` does not change. Nothing alerts on repeated failures (see open questions).

4. **Clients read the current value.**
   - Starts on every customer request.
   - `PaymentsClient`, `EmailClient` and `GeocodingClient` call `secrets.get(name)` on each request. Today each client copies its key once, when the module is imported, so a refreshed key would never reach it. The new code does not copy it.
   - `get` reads memory only and makes no store call. A refreshed value is used on the next request, with no restart.
   - Base URLs, timeouts and other non-secret settings stay in `config/app.yaml`.
   - State: process memory.
   - If the store is down, requests use the last good value in memory.
   - Clients do not retry or switch to another key, because there is no fallback key. If a provider rejects a key, the request fails with the provider's error, as it does today. Rollout step 7 is meant to prevent this.

## Rollout

Each step starts when the previous step is done.

1. **Set access.**
   - Starts when the plan is approved.
   - Grant `orders-api-prod` read-only access to `orders-api/prod/*` and nothing else. Only the security on-call can write prod secrets. Engineers cannot read prod values. Engineers can read `orders-api/dev/*`.
   - State: the store's access policies.
   - If a policy is wrong, fix it before any secret is written. Nothing is deployed yet.

2. **Copy secrets into the store.**
   - Starts when step 1 is done.
   - The security on-call writes the current values from `config/app.yaml` into `orders-api/prod/payments_api_key`, `email_api_key` and `geocoding_api_key`. Sandbox keys go into `orders-api/dev/*`. Each write gets a version id.
   - These prod values are the leaked keys. Step 6 replaces them.
   - State: the store now holds copies of the repo's values. Running pods still read `config/app.yaml`, so nothing changes for them yet. Until step 6, the store keys and the config keys are the same values.
   - If a write fails, retry it. Nothing else changes.

3. **Change code and config.**
   - Starts when step 2 is done.
   - Build `app/secrets.py` with `load()`, `refresh()` and `get(name)`. Switch the three clients to `secrets.get()`. Add `secret_versions` to `/healthz` and gate readiness on the load. Remove the three `api_key` lines from `config/app.yaml`.
   - Add a CI check that fails any change that puts an `api_key` back into `config/app.yaml`.
   - State: the git repo. The image built from this change has no keys. Images built before it still have them, and rollback depends on that (step 8).
   - If CI fails, fix the change before merging.

4. **Local development.**
   - Starts when a developer runs `make run`.
   - `make run` sets `APP_ENV=dev`, so the app loads `orders-api/dev/*`. Developers never need prod access. The app never falls back to prod keys.
   - State: dev secrets in the store. No prod values reach a developer's machine.
   - If a developer has no dev access, startup fails with a load error, and `make run` fails.

5. **Deploy and verify.**
   - Starts when the change merges to `main`.
   - CI builds one image per merge to `main`. The rolling deploy runs 4 pods under `orders-api-prod`, one pod at a time, with `maxUnavailable: 0`. Each new pod loads its keys at startup, and must pass readiness before an old pod is stopped.
   - Verify that all 4 pods are ready. Verify that each pod's `/healthz` shows a version id for all three keys. Verify that customer request failures do not rise and that the logs show no key-load warnings. Compare failures and warnings for the deploy window with the window before it. The person running the rollout does these checks.
   - State: the image and the pods. Logs go to the central log service and are kept 30 days.
   - If a new pod cannot load keys, it never becomes ready. The rollout halts and the old pods keep serving.
   - If a check fails after all pods are replaced, redeploy the pre-migration image. It still works until step 7.

6. **Rotate each key.**
   - Starts when step 5 is verified. Do payments, email and geocoding one at a time.
   - a. Create a new key at the provider. The old key stays valid. If this fails, the old key stays in use and nothing changes.
   - b. The security on-call writes the new value to `orders-api/prod/<name>`. The store gives it a new version id. Keep that id for step d.
   - c. Running pods pick up the new value at their next refresh, within 5 minutes. No restart is needed. Calls already in flight with the old key still succeed, because the provider accepts the old key until step 7.
   - d. The person running the rotation checks each pod directly at that pod's own address, not through the service. Each pod's `/healthz` must show the version id from step b for that key. If any pod still shows the old version, check again later. Do not go to step 7 until every pod shows the new version.
   - Pods can differ for up to 5 minutes, and different keys can be on different versions at once. A pod may hold the new payments key while another holds the old email key. This is safe: each provider accepts both keys until step 7, and each key is revoked on its own.
   - State: the store holds the new value. The provider has both keys live.
   - If a provider cannot create a new key, nothing changes. If any pod does not show the new version, do not revoke.

7. **Revoke the old key.**
   - Starts only when step 6d is confirmed for that key.
   - Revoke the old key at the provider.
   - If any pod still uses the old key, do not revoke.
   - State: the provider.
   - After revocation, no image built before this migration can run.

8. **Update rollback notes in `deploy.md`.**
   - Starts when step 7 is done.
   - Rollback means redeploying an earlier image. Until step 7, a pre-migration image works, because its config keys are still valid. After step 7 it does not. A fix must then go forward through a new image.
   - State: `deploy.md`.

## Open questions

- Which product is the secret store, and where does it run? The brief does not name it.
- How does an `orders-api-prod` pod prove its identity to the store? The brief names the identity, not the mechanism.
- Where is `APP_ENV` set in prod, and what happens if it is missing?
- Does each provider accept two live keys at once? Step 6 assumes yes. If not, the cutover needs a different plan.
- How long must old keys stay valid for rollback? Step 7 ends rollback to pre-migration images.
- Are sandbox keys available for dev, and who supplies them?
- How is each pod's `/healthz` reached directly for step 6d?
- Who runs the step 5 checks, and which failure metric do they use? The brief names neither.
- Who reads the refresh warnings, and should anyone be alerted when they repeat? Nothing alerts in this plan.
- Must keys be rotated on a regular schedule after this migration, and how often? Security has not decided. No cadence is set in this plan.