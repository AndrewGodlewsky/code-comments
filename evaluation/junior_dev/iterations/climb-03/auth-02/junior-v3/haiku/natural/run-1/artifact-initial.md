# Move orders-api third-party keys to the managed secret store

## Scope and assumptions

- Keys in scope: `payments.api_key`, `email.api_key`, `geocoding.api_key`. Each is rotated at its provider. Old keys are revoked only after the gate in step 7.
- Environments: `prod` and `dev`. If a staging environment exists, it follows the `dev` pattern with its own KMS key and store prefix.
- Assumption A1: each provider lets us hold two live keys at once (old and new). If a provider cannot do this, the "no customer request fails" rule cannot be met for that provider, and the rollout for that provider stops at step 3 until security decides how to proceed.
- Assumption A2: pods authenticate to the store as `orders-api-prod` through the platform's workload identity. No static credential is used to reach the store.
- Assumption A3: "retry 3 times" means one initial attempt plus three retries (up to four attempts, about 6 seconds of waiting). Confirm this with the owner.
- Rotation cadence is an open question (see the end). This plan does not set a schedule.

## Part 1: Rollout

### 1. Confirm provider capability and inventory the keys

- **Starts:** the plan is approved.
- **Moves:** nothing moves. Record each key's provider, name, and every place it is used (code paths, instances, other services).
- **State lives:** the inventory, in the migration tracking issue. It contains no key values.
- **If it fails:** if a provider does not support two live keys (A1), stop before step 3 for that provider and escalate to security. Do not revoke anything to make progress.

### 2. Create the store layout, KMS keys, and IAM

- **Starts:** step 1 is done. Changes go through infrastructure-as-code and security review.
- **Moves:** nothing moves yet. Create the secret names `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, `orders-api/prod/geocoding_api_key`, and the same three under `orders-api/dev/`. Create one KMS key per environment.
- **IAM rules:**
  - `orders-api-prod` gets read on `orders-api/prod/*` only.
  - Only the security on-call role can write `orders-api/prod/*`.
  - No engineer role can read `orders-api/prod/*`.
  - Engineers get read and write on `orders-api/dev/*` only.
  - Use the store's policy simulator to confirm that the engineer roles and CI roles cannot read prod, before any value is written.
- **State lives:** the store (encrypted per environment with KMS), plus the IaC policy files.
- **If it fails:** a wrong policy shows up as a startup failure in step 5. New pods do not become ready, so the rollout halts and the old pods keep serving. Fix the policy, re-run the simulator, and retry. No customer traffic is affected.

### 3. Create new live keys at each provider

- **Starts:** step 2 is done and the simulator check passes.
- **Moves:** provider console or admin API to a new key. Old keys stay active.
- **State lives:** the provider. The new value must not go into chat, tickets, files, or environment variables. Hold it only long enough to pass it to step 4.
- **If it fails:** nothing in production has changed. Retry or escalate. Do not revoke an old key here.

### 4. Validate and write the new values to the store

- **Starts:** step 3 is done. The security on-call performs this step.
- **Moves:** new key value → a provider test call (to confirm it authenticates) → store, as a new version of `orders-api/prod/<name>`. Do the same for dev, using dev or sandbox keys, under `orders-api/dev/`.
- **State lives:** the store. Record each returned version id in the tracking issue. Version ids are safe to log and record.
- **Why validate first:** once a version is written, running pods pick it up within 5 minutes (K3). A bad key here would reach customer traffic.
- **If it fails:**
  - Validation fails: do not write. Return to step 3.
  - Write fails: retry. The old code does not read the store yet, so nothing is affected.

### 5. Release the store-reading code and remove the keys from config

- **Starts:** merge to `main`. CI builds one image. It contains no key values.
- **Moves:**
  - The release contains the runtime changes K1 to K5 below.
  - It removes the three `api_key` lines from `config/app.yaml`.
  - It adds the CI guard (K7).
  - Local development is switched to `orders-api/dev/*` (see K8).
- **Rollout:** the usual rolling deploy with `maxUnavailable: 0`. A new pod must pass readiness (K2) before an old pod stops.
- **State lives:** the new pod's memory, loaded at startup. The old pods still hold the old keys in memory and remain valid, because the old keys are not yet revoked. The mixed fleet is safe because both key sets are valid.
- **If it fails:**
  - Store unreachable at startup: the pod retries (K1), then exits non-zero. It never becomes ready, so the rollout halts. Old pods keep serving with old keys.
  - Bad or missing secret: the same as above, because readiness requires all three keys.
  - Rollback: redeploy the pre-migration image. It still has the old keys in its config, and those keys are still valid until step 7.

### 6. Confirm that every running instance uses the new keys

- **Starts:** the rollout in step 5 completes.
- **Checks:**
  - Each of the four prod pods reports, in its startup and refresh logs, the store version ids for all three keys. These must match the ids recorded in step 4.
  - No pod runs the pre-migration image.
  - At the provider, requests using each old key have dropped to zero for at least 15 minutes. This window covers three refresh cycles of 5 minutes each, plus slack. The window is a proposed value.
- **State lives:** the logs, the provider's per-key usage data, and the tracking issue, where the security on-call records sign-off.
- **If it fails:** a pod on the old image, a version mismatch, or continued old-key traffic means the gate is not met. Hold, do not revoke, and investigate. A refresh that keeps failing shows up as warning logs (K3).

### 7. Revoke the old keys at the providers

- **Starts:** the security on-call signs off on step 6.
- **Moves:** nothing in the application. Each old key is revoked at its provider.
- **State lives:** the provider. Revocation cannot be undone, so the old keys are gone for good.
- **If it fails:** any remaining old-key traffic becomes 401 errors for customers. This is why the step 6 gate is strict.
- **Rollback effect:** after this step, the pre-migration image is no longer a safe rollback target. Rollback now means redeploying the post-migration image. See the Rollback section.

### 8. Verify the CI guard and the cleanup

- **Starts:** step 7 is done.
- **Checks:**
  - On a throwaway branch, add an `api_key` line to `config/app.yaml`. Confirm that CI fails. Do not merge.
  - Confirm that the current `main` contains no `api_key` in `config/app.yaml` and that the built image contains no key values.
  - Record in the tracking issue that the old keys remain in git history. History is not being rewritten, and the old keys are revoked.
- **State lives:** CI configuration and the tracking issue.
- **If it fails:** a guard that does not fail is a blocker for closing the migration. Fix it before closing.

### 9. Local development on dev keys

This is covered by K8 and ships in step 5. It is listed here so that the rollout is complete.

- **Starts:** the release in step 5.
- **Moves:** dev store → the developer's process memory.
- **State lives:** memory only.
- **If it fails:** `make run` stops with a clear message that names the missing secret. It never falls back to live keys.

## Part 2: How the app reads keys at runtime

### K1. Load keys at process start, before the server listens

- **Starts:** process start.
- **Moves:** the store (`orders-api/<env>/<name>` for the three names) → an in-memory secret holder. The yaml loader still reads non-secret settings from `config/app.yaml`. The loader ignores any `api_key` field, so keys never enter the `settings` object.
- **Order:** the secret load runs before any client module is imported or constructed. Module-level clients (`payments = PaymentsClient()`) must not run before this load.
- **Retry:** one attempt, then up to three retries spaced 2 seconds apart (A3). If all attempts fail, log an error that names the secret and the attempt count (no values), then exit with a non-zero code.
- **State lives:** memory only. The store SDK's on-disk cache, if it has one, must be disabled. Keys are never written to a file, an environment variable, or a log.
- **If it fails:** the process exits. The pod never becomes ready.

### K2. Readiness depends on having all three keys

- **Starts:** the HTTP server begins listening.
- **Behavior:**
  - `GET /healthz` returns 200 only when K1 has loaded all three keys.
  - Before that, it returns 503.
  - The server does not start listening before K1 completes, so this is a second guard, not the only one.
- **Liveness:** use a separate check that does not depend on the store. A refresh failure must not restart pods or mark them unready.
- **State lives:** an in-memory flag set by K1.
- **If it fails:** a 503 keeps the pod out of rotation. This is also why the change to `/healthz` ships in step 5. Today it returns ok as soon as the server listens, which would be wrong with this design.

### K3. Refresh every 5 minutes

- **Starts:** one background task per process, begun after K1 succeeds. The task is not per request.
- **Moves:** store → new value → atomic swap into the holder. Each secret is swapped independently when its read succeeds, so one secret's failure does not block the other two.
- **On success:** log the secret name and the new version id, but only if the version changed.
- **On failure** (store error, timeout, empty value, or malformed value): keep the last good value. Log a warning with the secret name, the version id attempted, and the error class. Do not log the value. Readiness does not change.
- **State lives:** memory only. The holder keeps exactly one current value per secret.
- **If it fails:** customers are not affected, because the last good value keeps working. The warning logs are the signal to investigate.

### K4. Clients read keys on each use, not at construction

- **Starts:** each outbound provider call.
- **Behavior:** the client calls `secrets.get('payments_api_key')` (or equivalent) when it builds the request. It does not copy the key into `self._key` in `__init__`. Today's code does copy it, so a refresh would never take effect. This is the main change to the provider clients (`payments.py`, `email.py`, `geocoding.py`).
- **Swap timing:** a request that already read the old value finishes with it. This is safe only while the old key is still valid at the provider. That is why every rotation, including future ones, must overlap old and new keys before the old one is revoked.
- **State lives:** memory only.
- **If it fails:** a 401 from the provider with the current key means the store version is bad. The on-call should roll the store back by writing the previous good value as a new version, and alert on the 401 rate. Proposed option, not yet decided: keep the previous value for one refresh cycle and retry once with it on a 401.

### K5. Keep keys out of logs and dumps

- **Starts:** every log call and every exception.
- **Behavior:**
  - Log secret names and version ids only.
  - Redact the `Authorization` header in HTTP client debug logging.
  - Avoid including the key in exception messages or `repr` output.
  - Disable core dumps for prod pods, or confirm that they are not collected, because a dump contains memory.
- **Test:** run the test suite with a fake key, such as `FAKE_PAYMENTS_KEY_123`, and fail the run if that string appears in captured logs.
- **If it fails:** a key found in logs is treated as an exposure incident. The value must be rotated again, which means going back to step 3.

### K6. Crash and restart

- **Starts:** process exit or pod restart.
- **Behavior:** memory is discarded. The next start repeats K1. Nothing is persisted, so there is nothing to clean up on disk.
- **If it fails:** if the store is down when a pod restarts, the pod cannot become ready (K1). Pods that are still running keep serving with their last good values.

### K7. CI guard against keys in config

- **Starts:** every pull request and every push to `main`.
- **Behavior:** fail the build if `config/app.yaml` contains an `api_key` field, or any other secret-like value. Check the file contents, not only the diff. Consider also running a general secret scanner, as a suggestion for security to decide.
- **If it fails:** the pull request cannot merge until the key is removed.

### K8. Local development uses dev keys only

- **Starts:** `make run` or a test run.
- **Moves:** the developer's identity reads `orders-api/dev/*` → process memory, using the same K1 loader.
- **Requirements:**
  - Use dev or sandbox keys from each provider. If a provider does not offer sandbox keys (open question), create a separate dev-only key.
  - Tests use an in-memory fake secret source with fake values. There are no key files and no environment variables.
  - Developers delete any local copy of an older `config/app.yaml` that still has live keys.
- **State lives:** memory only.
- **If it fails:** if the dev store is unreachable, `make run` fails fast with a clear message. It must never fall back to the prod store or to the old live keys.

## Rollback

- **Before step 7 (old keys still valid):** redeploy the pre-migration image. It works with the old keys in its config.
- **After step 7 (old keys revoked):** the pre-migration image is no longer safe. Rollback means redeploying the post-migration image.
- **A bad store version:** write the previous good value as a new version. This works only while that previous key is still valid at the provider. A compromised or revoked key needs a new provider key, which means going back to step 3.
- **Decision to record:** after step 7, whether to keep any older rollback path at all.

## Failure summary

| Situation | Customer impact | What happens |
|---|---|---|
| Store unreachable at pod start | None | Pod exits after retries, is never ready, rollout halts |
| Store unreachable during refresh | None | Last good value kept, warning logged |
| Bad new store version | Possible 401s | Caught by step 4 validation; if missed, roll the store version back |
| IAM misconfigured | None (rollout halts) | Startup fails for new pods, fix policy and retry |
| `api_key` added back to config | None | CI guard fails the change (K7) |
| Old key still in use at revoke time | 401s | Prevented by the step 6 gate |

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan does not choose one. Any future rotation must use the overlap pattern in K4.
2. **Two live keys per provider (A1).** Confirm for each of payments, email, and geocoding in step 1. This is a hard gate.
3. **Sandbox or test keys for dev.** Confirm that each provider offers them, or approve dev-only keys.
4. **Staging.** Does a staging environment exist? If so, does it get its own store prefix and KMS key?
5. **Retry count (A3).** Is it one initial attempt plus three retries, or three attempts in total?
6. **Observation window in step 6.** The 15-minute window is a proposed value. Security should confirm it.
7. **Previous-value fallback in K4.** Decide whether to keep the previous value for one cycle and retry on 401.
8. **Rollback after step 7.** Decide how long, if at all, the pre-migration image stays available as a rollback target.
9. **Store audit.** Confirm that the store logs every read and write, with the caller identity, so the on-call and security can audit prod access.
10. **Secret scanning beyond config.** Decide whether to add a general secret scanner to CI beyond the K7 guard.