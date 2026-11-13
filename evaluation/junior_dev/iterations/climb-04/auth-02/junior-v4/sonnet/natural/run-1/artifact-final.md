# Plan: move `orders-api` provider keys into the managed secret store

## What this is

Today the three provider keys (payments, email, geocoding) sit in `config/app.yaml`. That file is in git and in every image. The app reads it once at start, and each client copies its key in its constructor. Changing a key means a new image.

After this plan the keys live in the managed secret store. Each pod fetches them at startup, keeps them in memory only, and re-reads them every 5 minutes. The rollout has five moves. Put new keys in the store. Replace the pods one at a time so each new pod loads the new keys. Confirm every pod uses them. Check the old keys are idle. Revoke the old keys. Old and new keys are both valid until the last move, so no customer request fails.

## Terms

- **Store:** the managed secret store. Each secret is at `orders-api/<env>/<name>`, is encrypted with a per-environment KMS key, and gets a new version id on every write.
- **Workload identity:** the cluster gives each pod a short-lived signed token for its service identity (`orders-api-prod` in prod). The app sends it to the store, and the store checks its access policy. The pod holds no stored credential. The store client uses the current token on every read, so the app never handles expiry.
- **Snapshot:** the app's in-memory map of secret name to `(value, version_id)`. It is never edited. A new one replaces it.
- **Old keys:** the leaked keys in git history and in pre-migration images. **New keys:** the keys created in rollout step 3.
- **Secrets:** `payments_api_key`, `email_api_key`, `geocoding_api_key`. URLs, timeouts and the from-address stay in `config/app.yaml`.

## Assumptions to confirm first

Rollout step 1 checks A and D. Rollout step 6 checks C.

- **A (blocking).** Each provider lets two keys be valid at once. The zero-failure rollout depends on it.
- **B.** Prod pods reach the store through workload identity, not a static credential or environment variable.
- **C.** Nothing outside `orders-api` uses the current keys.
- **D.** Each provider offers sandbox keys for staging and dev.

## Part 1: How the app reads keys at runtime

Key values exist only in process memory. They never go in environment variables, on disk or in logs. Version ids may be logged. Core dumps are disabled for the container, and HTTP client debug logging redacts the `Authorization` header.

### 1. Startup load
- **Starts it:** process start, before the HTTP server serves traffic.
- **What it does:** `app/secrets.py` presents the workload identity token to the store and reads the three secrets under `orders-api/<APP_ENV>/`. Each comes back as a value and a version id. They go into one snapshot, and the version ids are logged.
- **State lives in:** process memory.
- **If it fails:** the app tries once, then retries 3 times, 2 seconds apart (4 attempts). If a secret is still unavailable, it logs an error without values and exits non-zero.

### 2. Readiness
- **Starts it:** the readiness probe `GET /healthz`.
- **What it does:** returns 503 until the snapshot holds all three keys, then 200. It stays 200 even if later refreshes fail, because the last good keys still work.
- **State lives in:** a flag in process memory.
- **If it fails:** a pod that cannot load its keys exits (step 1) and never turns ready. With `maxUnavailable: 0` the rollout halts and the old pods keep serving. A rollout progress deadline raises an alert.

### 3. Using a key on each call
- **Starts it:** each outbound call to a provider (payments, email, geocoding).
- **What it does:** the client no longer copies the key in `__init__`. At call time it reads the key from the current snapshot (for example `secrets.get('payments_api_key')`) and builds the `Authorization` header.
- **State lives in:** the current snapshot reference.
- **If it fails:** a call in flight keeps the value it already read. If a provider rejects a key, the app logs the secret name and version id, never the value. It does not re-fetch on a rejection. It waits for the next refresh.

### 4. Refresh every 5 minutes
- **Starts it:** a background timer, 5 minutes after the last attempt, plus a few seconds of random jitter so pods do not hit the store together.
- **What it does:** reads each secret again. It copies the current snapshot, replaces each secret that was read successfully, and swaps the copy in atomically. Requests in flight keep what they read. If a version id changed, it logs the change ("payments_api_key: version A to version B").
- **State lives in:** process memory.
- **If it fails:** each secret is handled alone. On a failed read, a missing secret or a rejected token, the app keeps that secret's last good value and logs a warning with the name and error type. The next cycle tries again with a fresh token.

### 5. Stale-key alert
- **Starts it:** metrics that every pod publishes.
- **What it does:** each pod exports, per secret, the age of its last successful refresh and the version id it holds. It alerts when any secret is more than 15 minutes stale (3 missed refreshes). The rollout uses the version-id metric.
- **State lives in:** the metrics and log services (version ids and ages only).
- **If it fails:** the app keeps running on the last good value. The alert tells a human that the store, network or permissions need attention.

### Local development
`APP_ENV` picks the secret backend. It defaults to `dev` and never to `prod`. Each cluster's deploy config sets it (`prod` or `staging`). It is not a secret. The same code runs everywhere.
- **`make run`** reads `orders-api/dev/*` (sandbox keys) with the engineer's own identity.
- **`make run-offline`** uses a stub backend and fake local provider servers. It needs no store and no keys.
- **If it fails:** a missing dev secret gives the same startup exit as prod. There is no fallback to prod, and engineers cannot read prod values anyway.

## Part 2: Rollout

### 1. Check providers, prepare the store, test policies
- **Starts it:** approval of this plan. The security on-call and the platform owner do it.
- **What it does:**
  - Confirm each provider allows a second valid key (A) and offers a sandbox key (D).
  - Create the secret paths for prod, staging and dev, with the per-environment KMS keys.
  - The security on-call writes sandbox keys to `orders-api/staging/*` and `orders-api/dev/*`. Prod paths stay empty.
  - Policies: `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else. The staging identity gets read-only on `orders-api/staging/*`. Only the security on-call group writes `orders-api/prod/*`. Engineers get no read on prod and get read on `orders-api/dev/*`.
  - Test the policies. The security on-call writes a throwaway prod secret. `orders-api-prod` reads it from a test pod. An engineer account tries to read it. `orders-api-prod` tries to read a path outside `orders-api/prod/*`. Then delete the secret.
- **State lives in:** store policies, KMS key policies and store audit logs.
- **If it fails:** if a provider cannot hold two valid keys, stop and escalate, because a hard cutover would break requests. If a test result is wrong, it is a policy bug. Fix it and repeat until all three outcomes are correct. Prod is unchanged.

### 2. Build the code change and test it in staging
- **Starts it:** step 1 is done.
- **What it does:** one PR, not merged yet.
  - It adds the secret module, switches the three clients to it, makes `/healthz` report readiness, deletes the three `api_key` lines from `config/app.yaml`, adds the local-dev backends, and adds the CI guard.
  - The CI guard parses `config/app.yaml` and fails if a key named `api_key` appears at any depth, with any value (empty too). A self-test feeds it a fixture containing `api_key` and the job must fail on it.
  - Deploy the PR build to staging, which reads `orders-api/staging/*`. Test a normal start, an unreachable store (the pod must exit non-zero after the retries and never turn ready), a new version written while running (picked up within 5 minutes), a failed refresh (last good value kept, warning logged), and a search of logs, environment and filesystem for key values (must find nothing).
- **State lives in:** git, the PR, and the staging cluster.
- **If it fails:** failing CI blocks the merge. Fix the code and redeploy to staging. Prod is untouched.

### 3. Create new provider keys and write them to the prod store
- **Starts it:** step 2 passes. Make the CI guard a required check on `main` now.
- **What it does:** the security on-call creates a new key at each provider. The old key stays active. Make one harmless authenticated test call per new key. Write each new key to `orders-api/prod/<name>`. Record the version ids, not the values. Engineers never see the values.
- **State lives in:** the store (encrypted by the prod KMS key) and the providers' key lists. Running prod pods still use the old keys from their baked-in file. Nothing tells them to switch.
- **If it fails:** if the test call fails, do not write the key. Create another. If a wrong value was written, write the correct one as a new version. Nothing in prod reads the store yet.

### 4. Merge and roll out to prod with a canary pause
- **Starts it:** step 3 is done. Merge the PR. CI builds the image and the rolling deploy follows. An engineer on the deploy rota watches it, with the security on-call reachable.
- **What it does:** prod runs 4 pods. The old pods run on the old keys in their baked-in file. A new pod has no `api_key` lines, loads the new keys from the store, and turns ready only if all three load. The deploy is rolling with `maxUnavailable: 0`, and it holds after the first new pod. Old and new keys are both valid, so every request succeeds on either kind of pod. The canary is healthy if its request error rate is no higher than the old pods' and no log line shows a provider rejecting a key. Watch for 10 minutes, then replace the rest. No pod switches keys while running. Each old pod is replaced by a new pod. The 5-minute refresh is not needed here. It is for later rotations.
- **State lives in:** pod memory and the Kubernetes rollout state.
- **If it fails:** if the store is unreachable or a secret is missing, the new pod exits and never turns ready. The rollout halts and the old pods keep serving. If the canary shows provider auth errors, redeploy the previous image through the normal pipeline. This is safe because the old keys are still valid. Then investigate the store value.

### 5. Confirm every pod uses the new keys
- **Starts it:** the rollout finishes (4 of 4 pods on the new image).
- **What it does:** read-only checks, with no key values. In the metrics service, check that all 4 pods show the version ids recorded in step 3. Check in the cluster's pod list that no pod runs a pre-migration image. Wait 10 minutes (two refresh intervals). A pod that picked up a newer version would show it.
- **State lives in:** pod logs, the metrics service and the pod list.
- **If it fails:** if any pod reports a different version id or an old image, stop. Find out why and fix it. The old keys stay active.

### 6. Check that the old keys are idle
- **Starts it:** step 5 passes.
- **What it does:** the security on-call checks each provider's "last used" data for each old key. It should show no traffic for at least 30 minutes. Any traffic left comes from someone else (C): developer machines on an old checkout, scripts or other services.
- **State lives in:** the providers' usage dashboards.
- **If it fails:** if an old key is still used, find the caller from what the provider shows (such as source address or user agent) and ask the teams that could be using it. Give the caller its own credentials. Do not revoke while the key is in use.

### 7. Revoke the old keys, one provider at a time
- **Starts it:** steps 5 and 6 both pass for that provider.
- **What it does:** the security on-call revokes the old key at the provider. After each revocation, watch the error rate and provider auth failures for 15 minutes before the next.
- **State lives in:** the providers' key lists. A revoked key cannot be restored.
- **If it fails:** revocation cannot be undone, so steps 5 and 6 are the guard. If errors appear, a caller was still on the old key. Find it from the logged secret name and version id. Create another new key (step 3), write it to the store, and pods pick it up at their next refresh, within about 5 minutes. Until then calls from a pod that holds the revoked key fail.
- **Rollback from here on:** a pre-migration image holds a revoked key and the leaked keys. When the first key is revoked, the platform owner deletes all pre-migration images from the registry and removes them from the deploy pipeline's list. Rollback is then only to images that read from the store.

### 8. Final checks
- Search pipeline logs, container environment and image layers for the three old and three new key values. None should be found.
- Confirm the CI guard fails on a test change that adds `api_key` to `config/app.yaml`.
- Confirm an engineer account cannot read `orders-api/prod/*` and the security on-call can write it.

### Later rotations
The security on-call decides when. Repeat steps 3, 5, 6 and 7. Running pods pick up the new key through the refresh. The old key is never revoked before every instance is confirmed on the new one.

## Open questions

- **Rotation schedule (not decided).** Should keys be rotated on a regular schedule after this migration, and how often? Security has not decided. This plan sets no cadence.
- **Staging image source.** Can CI build an image from a PR branch for staging? Not known. Ask the platform owner.
- **Image removal commands.** The exact registry and deploy-tool commands for removing pre-migration images are not known. The platform owner owns them.
- **No sandbox keys.** If a provider has no sandbox key, what do staging and dev use? Not decided.
- **Dashboards.** Which existing dashboards show request error rate and provider auth failures? Not known. Ask the platform owner.
- **Provider usage data.** Whether a provider's "last used" data shows only time, or also the caller's source address, is not known.
