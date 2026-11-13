# Plan: move orders-api API keys into the secret store

## What this plan does

`orders-api` calls three outside services: payments, email and geocoding. Each one needs an API key (a secret string that proves to the provider that our app is allowed to call it).

Today the three keys are written in `config/app.yaml`. That file is committed to git and copied into every container image, so the keys sit in git history and in every image. The keys have been in git for about two years, so we treat them as leaked.

This plan does four things:

1. Moves the keys into the managed secret store.
2. Changes the app to read the keys from the store when it starts, and keep them in memory.
3. Rotates every key at its provider (creates a new key and stops relying on the old one). We do not rewrite git history.
4. Revokes each old key (disables it at the provider so it no longer works), only after every running app instance uses the new key.

## Terms used in this plan

- **Secret store**: the managed cloud service that holds secret values. Each value has a name, such as `orders-api/prod/payments_api_key`. The store encrypts values at rest using a per-environment KMS key (a cloud key-management key; we have one for each environment).
- **Secret version**: every write to a secret creates a new version with its own id. Logs and `/healthz` may show version ids. They never show the key value.
- **Service identity**: the cloud identity a workload runs as, and the permissions that identity has. Production pods run as `orders-api-prod`.
- **Image**: the packaged container that CI builds from the code. Each merge to `main` produces one image.
- **Pod (replica)**: one running copy of the app. Production runs 4.
- **Readiness probe**: the cluster calls `GET /healthz` on each pod. The cluster sends traffic to a pod only while this returns 200.
- **Rolling deploy**: the cluster replaces pods one at a time. A new pod must pass its readiness probe before one old pod is stopped. If a new pod never becomes ready, the rollout stops and the old pods keep serving.
- **Provider**: the outside company whose API we call.
- **Refresh**: every 5 minutes, each running app re-reads its three keys from the store.
- **Last good value**: the most recent key value the app read from the store without error.
- **Revoke**: disable an old key at the provider so it no longer works.

## How things work today

`config/app.yaml` holds the three live provider keys. The app reads the file once, at startup. Each provider client copies its key once, when the client is built. So changing a key means building a new image and redeploying. Local runs (`make run`) load the same file, so they also use the live keys.

## How the app reads keys at runtime (target state)

A new module, `app/secrets.py`, has three functions: `load()`, `refresh()` and `get(name)`.

1. **Startup load.** When the process starts, `load()` fetches the three keys from the store and keeps them in memory. In production it runs as `orders-api-prod`. In development it uses the sandbox keys under `orders-api/dev/*`. If the store cannot be reached, `load()` makes one attempt, then retries 3 more times, waiting 2 seconds between attempts. If every attempt fails, the process exits with a non-zero code. A process that exits never becomes ready, so it gets no traffic.
2. **Readiness.** `/healthz` returns a non-200 status until `load()` has succeeded. A pod that has not loaded its keys gets no traffic.
3. **Periodic refresh.** Every 5 minutes, `refresh()` re-reads the three keys. If the store has a newer version, memory is updated. If the read fails, the app keeps its last good value, logs a warning that names the secret that failed, and keeps serving.
4. **Per-request lookup.** Each provider client calls `secrets.get(name)` on every request. It does not copy the key when it is built. This lets a refreshed value take effect without a restart.
5. **Memory only.** Key values live only in process memory. They are never written to disk, to environment variables or to logs. Logs may include version ids.
6. **Visibility.** After a successful load, `/healthz` returns `{"status": "ok"}` plus `secret_versions`, which gives the version id in use for each key. Operators use this to check which version each pod runs.

Two consequences of this design:

- A store outage does not affect pods that are already running. They keep their last good keys.
- A pod that restarts during a store outage cannot load its keys, so it never becomes ready. A long outage can therefore reduce capacity. It does not cause failures for pods already serving.

## Rollout plan

### 1. Set up access

- **Starts:** the plan is approved.
- **What moves:** nothing moves yet. Only access policies are created.
- **Where state lives:** in the secret store's access policies.
- **Policies:**
  - `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else.
  - The security on-call group can write prod secrets.
  - Engineers get read and write access to `orders-api/dev/*` only. Engineers cannot read prod values.
- **Check before continuing:** test-read each secret as each identity. Confirm that engineers are denied prod reads, and that `orders-api-prod` is denied writes.
- **If it fails:** nothing is deployed yet, so customers are not affected. Fix the policy and repeat the check.

### 2. Create the secrets

- **Starts:** step 1 is verified.
- **What moves:**
  - The security on-call creates `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key` and `orders-api/prod/geocoding_api_key`. The first version of each is the current live value, which is a leaked key. This is a temporary bridge: it keeps customers working while the rollout runs. Step 9 replaces these values.
  - Engineers create `orders-api/dev/*` with sandbox keys from the providers. No live keys go into dev.
- **Where state lives:** in the secret store, encrypted with the matching per-environment KMS key.
- **If it fails:** a failed write changes nothing. Retry the write. Confirm that each secret has a version id before continuing.

### 3. Write `app/secrets.py`

- **Starts:** step 2 is done, so the secret names are fixed.
- **What it contains:** `load()`, `refresh()` and `get(name)`, with the startup retries and the 5-minute refresh described above.
- **Where state lives:** in process memory only.
- **Testing:** unit tests run against a fake store. They cover:
  - a successful load;
  - a load that fails on every attempt, then exits non-zero;
  - a refresh failure that keeps the last good value.
- **If it fails:** do not merge. Nothing has been deployed.

### 4. Switch the provider clients to `secrets.get()`

- **Starts:** step 3 is in place.
- **What changes:** `PaymentsClient`, `EmailClient` and `GeocodingClient` call `secrets.get(name)` on each request. Today each one copies its key when it is built, so a refreshed value would be ignored.
- **Where state lives:** in process memory.
- **If it fails:** tests catch most problems before merge. If a bad image is deployed anyway, step 5 keeps its pods from receiving traffic.

### 5. Update `/healthz`

- **Starts:** steps 3 and 4 are in place.
- **What changes:**
  - `/healthz` returns a non-200 status until `load()` has succeeded.
  - After that, `/healthz` returns `{"status": "ok"}` as before, plus `secret_versions`.
- **Testing:**
  - Start the app with the store unreachable. Confirm `/healthz` is non-200.
  - Start the app with the store reachable. Confirm `/healthz` is 200 and lists the three versions.
- **If it fails:** if readiness reports ready before the keys are loaded, pods serve traffic without keys and customer requests fail. Treat this as a blocker.

### 6. Remove `api_key` from `config/app.yaml` and add a CI check

- **Starts:** steps 3, 4 and 5 are done. Steps 3 to 6 are one change set. They merge to `main` together, and step 8 deploys them together. The file loses its keys only in the same release that reads the keys from the store.
- **What changes:**
  - The three `api_key` lines are removed.
  - `base_url`, `timeout_seconds`, `from_address` and the rest of the file stay the same.
  - The loader no longer reads keys from the file.
  - CI gets a check that fails any change that puts an `api_key` entry back into `config/app.yaml`.
- **Where state lives:** in git. Old images and old git history still contain the leaked keys. This is expected. Step 9 deals with the keys themselves.
- **If it fails:** if the CI check blocks a legitimate change, fix the check. Never allow `api_key` back into the file.

### 7. Point `make run` at dev

- **Starts:** step 6 is merged.
- **What changes:** `make run` sets `APP_ENV=dev`. Locally, the app loads the sandbox keys from `orders-api/dev/*`. Engineers can read these keys through the dev access from step 1.
- **Where state lives:** the dev keys live in the store. Local processes hold them in memory only.
- **If it fails:** if a dev key is missing or an engineer lacks access, the local app fails at load with a clear error. It must never fall back to prod keys. Engineers cannot read prod keys in any case.

### 8. Deploy and verify

- **Starts:** the release from steps 3 to 6 is merged to `main`, and CI builds one image.
- **What moves:** the new image rolls out to the 4 pods, one at a time. Each new pod loads its keys as `orders-api-prod` and becomes ready. Then one old pod stops. This repeats until all 4 pods are new.
- **Where state lives:** keys are in process memory. `secret_versions` is visible on each pod's `/healthz`.
- **Verification:**
  - Check each of the 4 pods directly. All 4 must report `secret_versions` that match the store's current versions. A request to the service can reach any pod, so checking one pod is not enough.
  - Payments, email and geocoding success rates are unchanged.
  - Logs contain no key values.
- **If it fails:**
  - If a new pod cannot load its keys, it exits or stays not-ready. The rollout halts and the old pods keep serving.
  - To roll back, redeploy the previous image. That image still holds the old keys, and those keys still work because step 9 has not run.

### 9. Rotate the keys and revoke the old ones

- **Starts:** step 8 is verified on all 4 pods.
- **Pre-check:** confirm with each provider that two keys can be active at once. If a provider allows only one key, switching keys causes a gap. Security plans for that gap before starting, so no customer request fails.
- **What moves, one provider at a time:**
  1. Create a new key at the provider. The old key stays valid.
  2. The security on-call writes the new value to the store as a new version of the prod secret. Only the security on-call can write prod.
  3. Wait at least one refresh cycle (5 minutes). Then check all 4 pods. Each must report the new version id in `secret_versions`.
  4. Watch the provider's error rates for a period Security sets.
  5. Revoke the old key at the provider. Do this only after step 3 is confirmed on all 4 pods.
- **Where state lives:** the new key lives at the provider and in the store. Each pod keeps it in memory.
- **If it fails:**
  - If a pod still reports the old version about 10 minutes after the write, do not revoke. Check that the store is reachable, and read the refresh warnings in the logs.
  - If the new key fails at the provider, write the previous value back to the store as a new version. Keep the old key active, and investigate.
  - An old key is revoked only after every running pod is confirmed on the new version.

### 10. Update the rollback notes in `deploy.md`

- **Starts:** step 9 is complete.
- **What changes:** `deploy.md` gets a new rollback section that says:
  - Any image built before this change contains the old keys. Those keys are revoked after step 9. Rolling back to such an image breaks payments, email and geocoding.
  - Roll back only to images built after this change.
  - If an older image must be used, the keys must be reissued first. That is a Security decision.
  - Treat old images in the registry as holding leaked keys.
  - Readiness now waits for secrets. A rollout can halt where it previously would not have.
- **If it fails:** these notes are documentation only. A wrong note is fixed by editing the file.

## Open questions

- **Rotation schedule (Security to decide):** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan sets no cadence. A schedule must be decided before the migration is called finished.
- **Overlapping keys at providers:** step 9 assumes each provider lets two keys be active at once. This is unconfirmed. It must be checked before rotation begins.