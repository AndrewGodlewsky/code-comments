# Plan: move `orders-api` provider keys into the secret store

## Assumptions to confirm before step 1

- Each provider (payments, email, geocoding) lets two API keys be active at once. The plan relies on this: the old and new key must work side by side until the last instance has switched. If any provider allows only one active key, stop and escalate to security. The "no failed customer request" requirement can't be met without provider support.
- Each provider can issue a sandbox or test key for non-prod use.
- Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`, stored at `orders-api/<env>/<name>`.
- "Retry 3 times" means 1 initial attempt plus 3 retries, so 4 attempts in total.

## Phase A: Prepare the store (no app change, no customer effect)

### 1. Create the paths and access rules

- **Starts when:** this plan is approved.
- **What moves where:** the platform or security team creates the `orders-api/prod/*` and `orders-api/dev/*` paths. Each environment gets its own KMS key.
  - Prod: the identity `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else. The security on-call group gets write on prod. Engineers get no access to prod values.
  - Dev: engineers get read on `orders-api/dev/*`.
  - Store audit logging is turned on for reads and writes.
- **Where state lives:** in the store's access policies and the KMS key configuration.
- **If it fails:** check each rule with a negative test before any secret is written. The tests are:
  - An engineer identity reads prod and is denied.
  - `orders-api-prod` writes and is denied.
  - `orders-api-prod` reads `orders-api/dev/*` and is denied.
  - `orders-api-prod` reads `orders-api/prod/*` and succeeds.

  If any test gives the wrong answer, fix the policy and re-test. Nothing in the app has changed yet, so nothing is at risk.

### 2. Rotate: issue new keys and store them, leaving the old keys active

- **Starts when:** step 1 passes.
- **What moves where:**
  - A security on-call engineer creates a new key at each provider. The old key stays active.
  - They make one test call per new key.
  - They write each new value directly into `orders-api/prod/<name>` with the store CLI, never through chat, a ticket or a file.
  - The store returns a version id for each write. Record the ids, not the values, in the rollout ticket.
  - Sandbox keys go into `orders-api/dev/<name>`.
- **Where state lives:** the provider holds old and new keys. The store holds the new values, encrypted at rest. The ticket holds only version ids.
- **If it fails:**
  - If a new key fails its test call, delete it at the provider and issue another. Nothing has used it.
  - If a store write fails, retry it. Nothing reads these paths yet.
  - If a provider can't hold two active keys, stop here (see the assumptions).

## Phase B: How the new app reads keys at runtime

These steps describe the behaviour that step 9 builds.

### 3. Startup load

- **Starts when:** the process starts, before the app is allowed to take traffic.
- **What moves where:**
  - The app reads the three prod secrets from the store using its platform-issued service identity. No store credential is in the image or in environment variables.
  - The path is built from `APP_ENV`, so a prod process only asks for `orders-api/prod/*`.
  - Non-secret settings (`base_url`, timeouts, `from_address`) still come from `config/app.yaml` through `config_loader.py`.
  - The loader now refuses to start if `config/app.yaml` contains any `api_key`. This stops a stale file from silently shadowing the store.
  - Each attempt reads all three secrets with a per-call timeout of about 3 s. Attempts are at t=0, 2, 4 and 6 s.
- **Where state lives:** in a process-memory holder. It stores the current value and version id per secret, swapped under a lock. The holder masks its value in `repr`/`str`.
- **If it fails:** after the 4th failed attempt the process logs the error (no values) and exits with a non-zero code (for example 3). The platform restarts it. A secret that is denied or not found is treated the same way: retry, then exit.

### 4. Readiness

- **Starts when:** the HTTP server is up.
- **What moves where:**
  - `/healthz` returns 503 until all three secrets are loaded, then 200 `{"status": "ok"}`. Today it returns 200 as soon as the server listens, which would let a pod without keys replace a working one.
  - Other routes also return 503 while the holder is empty.
- **Where state lives:** the holder's "all three loaded" flag.
- **If it fails:** a pod that can't load keys exits (step 3) and never turns ready. With `maxUnavailable: 0`, the rollout halts and the old pods keep serving.
- **Later refresh failures never flip readiness.** The pod keeps its last good values (step 7).

### 5. Using a key on each request

- **Starts when:** a request needs a provider call.
- **What moves where:**
  - Clients no longer copy the key into `self._key` at construction. They call the holder (`secrets.get("payments_api_key")`) when building each request's `Authorization` header.
  - The module-level singletons can stay, because they no longer hold a key.
  - A new value therefore applies to the next call, with no rebuild or restart.
- **Where state lives:** the value stays in the holder. A request keeps its header only for its own lifetime.
- **If it fails:** if the holder is somehow empty, return 503 and log the secret name. This shouldn't happen after readiness.

### 6. Refresh every 5 minutes

- **Starts when:** a timer fires every 5 minutes after startup, in a background thread.
- **What moves where:**
  - The thread reads the latest version of each of the three secrets.
  - For each secret whose version id changed, it swaps in the new value and keeps the previous one in memory for step 7.
  - It logs one info line per cycle with the version ids only, for example `secrets refreshed payments=v7 email=v3 geocoding=v4`.
- **Where state lives:** the holder in process memory, plus the version ids in the central logs (kept 30 days).
- **If it fails:** see step 7.

### 7. Failure handling after startup

- **Starts when:** a refresh read fails, or a provider rejects a freshly changed key.
- **What moves where:**
  - **Refresh read fails.** Keep using the last good value and log a warning with the secret name and error (no values). Retry at the next 5-minute tick.
  - **Repeated failure.** Three failed cycles in a row (15 minutes) raises an alert. A pod stuck on an old value is dangerous when an old key is about to be revoked.
  - **Bad new value.** If a provider answers 401 or 403 to a key that changed in the last refresh, the client retries that call once with the previous value and logs a warning. A 401 means the call was not processed, so the retry can't double-charge. This keeps a mistyped rotation from failing customers while it is being fixed.
- **Where state lives:** the holder (current and previous value), the logs and the alert rule.
- **If it fails:** if both values are rejected, the call returns the provider error as today. The fix is a corrected store write, which every instance picks up within 5 minutes.

### 8. Keeping values out of disk, environment and logs

- **Starts when:** always.
- **What moves where:**
  - Secrets are fetched over the store API into memory only. Don't use environment injection or a mounted secrets file.
  - Don't log headers or request objects. Turn off HTTP-client debug logging. Strip `Authorization` from exception output.
  - Disable core dumps in the container.
  - Only version ids are logged.
- **Where state lives:** process memory.
- **If it fails:** a unit test sets a random canary secret, exercises startup, refresh and failure paths, and fails the build if the canary appears in captured logs, in `os.environ` or in files under the working directory.

## Phase C: Build the change, guard the file, fix local runs

### 9. Code change (one PR)

- **Starts when:** steps 3–8 are agreed.
- **What moves where:**
  - Add a `secrets` module (holder, startup load, refresh thread).
  - Change the three clients as in step 5.
  - Change `/healthz` as in step 4.
  - Delete the three `api_key` lines from `config/app.yaml`.
  - Add the loader guard from step 3.
  - Update `deploy.md`.
- **Where state lives:** git, on a branch.
- **If it fails:** tests must pass before merge. The tests cover:
  - 4 attempts, 2 seconds apart, then a non-zero exit.
  - Last-good retention on a refresh error.
  - `/healthz` returns 503 until loaded.
  - A new value is used without a restart.
  - The 401 fallback.
  - The canary test from step 8.

### 10. CI guard, in the same PR as step 9

- **Starts when:** any change touches `config/` (run it on every PR).
- **What moves where:**
  - A CI job parses every YAML file under `config/` and fails if a key named `api_key` appears at any depth.
  - It also fails on strings that look like live keys (`pk_live_`, `ml_live_`, `geo_live_`).
  - The job is a required status check on `main`.
  - A test fixture with an `api_key` proves the job fails when it should.
- **Where state lives:** the CI config and branch protection.
- **If it fails:** a red check blocks the merge. Don't add the job after the removal, because the order would leave a gap where keys can return.

### 11. Local development

- **Starts when:** a developer runs `make run`.
- **What moves where:**
  - With `APP_ENV=local`, `make run` uses `config/app.local.yaml`. It points `base_url` at local stub servers, started by `make stubs`, and uses fixed fake keys.
  - No store call is made and no real key is needed.
  - Optionally, `make run-sandbox` reads `orders-api/dev/*` with the developer's own identity and talks to the providers' sandboxes.
  - Neither mode can name a prod path, and engineers have no prod access anyway.
- **Where state lives:** the local files and the dev store paths.
- **If it fails:** if the sandbox read is denied, fall back to the stubs. The live keys are no longer available locally.

## Phase D: Roll out, confirm, revoke

### 12. Merge and deploy

- **Starts when:** steps 2, 9 and 10 are done and the PR is approved.
- **What moves where:**
  - Merge to `main`, then CI builds an image without keys.
  - The rolling deploy replaces one pod at a time. Each new pod runs steps 3–4 and must turn ready before an old pod stops.
  - During the rollout, old pods use the old key from their yaml and new pods use the new key from the store. Both keys are active, so every call succeeds.
- **Where state lives:** the image registry, the cluster and the store.
- **If it fails:**
  - A pod that can't reach the store or lacks access exits after about 6 s and never turns ready. The rollout halts and the old pods keep serving.
  - Fix the policy, or roll back by redeploying the earlier image. That image still works because the old key is still active.

### 13. Verify and soak

- **Starts when:** all 4 pods are on the new image.
- **What moves where:**
  - Check that every pod has a startup line and a refresh line with the expected version ids.
  - Check that error and latency rates for payments, email and geocoding calls match the pre-deploy baseline.
  - Soak for at least 1 hour and at least 3 clean refresh cycles. Security can lengthen this. Rollback stays available during the soak.
- **Where state lives:** the central logs and metrics.
- **If it fails:** roll back to the earlier image (old key still valid), or correct the store value if the store value is wrong (step 7).

### 14. Close the rollback hole and find other users of the old keys

- **Starts when:** step 13 passes.
- **What moves where:**
  - Configure deploy tooling to refuse any image built before the migration image. Those images hold the old keys and would fail once the keys are revoked.
  - Use each provider's usage or audit view to list who still calls with the old keys. Expected callers are developers' `make run` and the old pods, which are gone by now. Investigate anything else.
  - Tell engineers that old local checkouts will stop working.
- **Where state lives:** the deploy tooling config and the provider usage views.
- **If it fails:** an unknown caller, or no way to see usage, holds the revocation until security has accepted the risk in writing.

### 15. Confirm every instance, then revoke the old keys

- **Starts when:** step 14 is done and the security on-call explicitly signs off.
- **Evidence required, per key:**
  - The cluster lists exactly the expected pods, all on the migration image or later.
  - Each pod's latest refresh line shows the same version ids as the store's current versions.
  - No refresh alert is open.
  - Where the provider shows last use, the old key hasn't been used since the final pod switched.
- **What moves where:**
  - Revoke one provider at a time (geocoding, then email, then payments).
  - Use a reversible "disable" first if the provider offers one. Watch error rates for 15 minutes, then delete.
- **Where state lives:** the providers, and the ticket that records the evidence.
- **If it fails:** if errors appear after a disable, re-enable the old key. If it can't be re-enabled, issue another key, write it to the store and let the 5-minute refresh deliver it. After this step a pre-migration image is no longer a rollback option, which is why step 14 blocks those images.

### 16. Close out

- **Starts when:** all three old keys are revoked.
- **What moves where:**
  - The keys in git history are dead, so rewriting history isn't needed.
  - Confirm the step 10 check is required on `main`.
  - Confirm `deploy.md` describes the store, the 5-minute refresh and the local modes.
  - Record the final version ids and the dates of revocation.
- **Where state lives:** the repo docs and the ticket.
- **If it fails:** keep the ticket open until each item is done.

## Rotating later (same mechanism)

Any future rotation follows the pattern of steps 2, 6 and 15:

1. Issue a new key at the provider while the old one stays active.
2. Test the new key, then write it to the store.
3. Wait at least 2 refresh cycles (10 minutes).
4. Confirm every pod shows the new version id.
5. Revoke the old key.

## Open question

**Scheduled rotation: not decided.** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan does not choose a cadence. The runtime design supports any cadence without code changes, so the decision doesn't block this work. Security needs to decide whether there is a schedule and who owns it.
