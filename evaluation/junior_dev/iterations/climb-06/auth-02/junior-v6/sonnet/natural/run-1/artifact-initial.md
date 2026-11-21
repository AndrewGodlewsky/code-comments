# Plan: Move orders-api provider keys into the managed secret store

## Scope and assumptions

- **Providers:** payments, email and geocoding. Their secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`.
- **Store paths:** `orders-api/<env>/<name>`.
- **Two keys at once:** the plan assumes each provider lets an old and a new key be valid at the same time. Step 1 checks this, and nothing else starts until it is confirmed.
- **Config:** `base_url`, timeouts and `from_address` stay in `config/app.yaml`. Only the `api_key` entries leave it.
- **Version ids:** the store gives every write a new version id. Version ids are not secret and may be logged.
- **Phases:** steps 1-3 touch only the store and providers. Steps 4-7 are code and deploy. Steps 8-10 retire the old keys. Steps 11-15 describe how the app behaves at runtime, and the code in step 4 implements them. Step 16 is the rotation runbook for later.

## Part A: Rollout

### 1. Check that every provider supports two active keys

- **Starts it:** the plan is approved.
- **What moves:** nothing. The security on-call reads each provider's docs or console, or asks the provider.
- **State:** the result is recorded on the migration ticket.
- **If it fails:** if a provider allows only one active key, rotating it would break requests. Stop for that provider. Ask the provider for a grace window or a second key slot, and do not go on until there is one. The other two providers can proceed.

### 2. Create the store layout and access rules

- **Starts it:** step 1 is confirmed for at least one provider.
- **What moves:** nothing sensitive. Infrastructure changes only:
  - Create the per-environment KMS keys, with `prod` and `dev` kept separate.
  - Create the empty secret paths `orders-api/prod/{payments,email,geocoding}_api_key`, and the same under `orders-api/dev/`.
  - Grant identity `orders-api-prod` read-only access to `orders-api/prod/*`, plus decrypt on the prod KMS key only. Give it nothing else.
  - Allow writes to `orders-api/prod/*` only for the security on-call role.
  - Add an explicit deny so engineer roles cannot read or write `orders-api/prod/*`.
  - Let engineers read `orders-api/dev/*`, and let them write it too if they maintain the sandbox keys.
- **State:** the policies live in the store's IAM and KMS configuration, kept as code in the infrastructure repo.
- **Verify before moving on, each with a real call:**
  - `orders-api-prod` can read prod and cannot write prod.
  - `orders-api-prod` cannot read dev.
  - An engineer role is denied on prod reads.
  - The security on-call role can write prod.
- **If it fails:** a wrong grant is fixed in the policy and the tests are run again. Nothing in the app depends on the store yet, so there is no customer impact. Do not go on until the engineer-denied test passes.

### 3. Issue new keys and load them into the store

- **Starts it:** step 2 verification has passed.
- **What moves:**
  - The security on-call creates a new key at each provider. The old keys stay active.
  - They check each new key with one cheap authenticated call to that provider.
  - They write the new key to `orders-api/prod/<name>`, which creates version 1.
  - Engineers get sandbox or test keys, written to `orders-api/dev/<name>`.
- **State:** the new prod keys exist only at the provider and in the store, encrypted by the prod KMS key. They are never put in a ticket, chat message, file or CI variable. Record only the version ids on the ticket.
- **If it fails:** if the provider call fails, do not write the key. Create another one. A key that is bad but already written is overwritten by a new version, and no running instance reads the store yet.

### 4. Implement the runtime secret reader and gate readiness on it

- **Starts it:** step 3 is done for the dev path at least, so the code can be tested. It can be built in parallel with steps 2-3.
- **What moves:** code only. The behavior is specified in steps 11-15:
  - Add `app/secrets.py` with `start()` and `get(name)`.
  - Change `PaymentsClient`, `EmailClient` and `GeocodingClient` so they no longer copy the key in `__init__`. Each call to `charge()` and the other methods calls `secrets.get('<name>')` at the moment of the request. The module-level singletons stay, but constructing them must not read secrets, because construction happens at import, before the load.
  - Make `/healthz` return 200 only after the first successful load of all three keys. Before that it returns 503.
  - Add a defensive check in `config_loader.py`. If the loaded YAML contains an `api_key` key at any depth, the process refuses to start. This guards against an old config file being used.
- **State:** the secrets live in a process-memory dictionary guarded by a lock. Nothing goes to disk or to environment variables.
- **Tests required:**
  - A fake store that is down for the first 3 attempts, then up. The app should reach ready.
  - A fake store that is down for good. The app should exit non-zero after 3 retries.
  - A refresh that fails. The old value should stay in use and a warning should be logged.
  - A refresh that succeeds. The next request should use the new value.
  - A log-capture test asserting the key value never appears in logs.
- **If it fails:** the pull request does not merge.

### 5. Remove the keys from `config/app.yaml` and add the CI guard

- **Starts it:** step 4 is code-complete. Both changes ship in the same pull request as step 4. Merging the guard before the keys are removed would fail `main`, and removing the keys without the new code would break startup.
- **What moves:**
  - Delete the three `api_key` lines and their "live key" comments from `config/app.yaml`.
  - Add a CI job that parses `config/app.yaml` as YAML and fails if any key named `api_key` exists at any depth, in any letter case. It also fails if the file does not parse.
- **State:** the check lives in the CI configuration in the repo.
- **Verify:** open a throwaway branch that adds `api_key: x` to the file, and confirm CI goes red. Then close the branch.
- **If it fails:** a guard that does not trip on the test branch is fixed before merge. A false failure on a legitimate change is fixed in the check, not by weakening it to ignore `api_key`.

### 6. Local development

- **Starts it:** part of the step 4 pull request.
- **What moves:** `make run` no longer reads keys from `config/app.yaml`.
  - It starts the app with `APP_ENV=dev`. The app then reads `orders-api/dev/*` with the engineer's own store login, using the same code path as production.
  - A `make run-offline` target points the three clients at local stub servers and needs no store access and no keys.
  - `deploy.md` and the README are updated to describe both.
- **State:** the dev keys are provider sandbox or test keys, held in the dev path and in process memory. Prod pods set `APP_ENV=prod` as an ordinary, non-secret variable.
- **Safety:** an engineer cannot read prod even by setting `APP_ENV=prod`, because the deny rule from step 2 refuses the read.
- **If it fails:** if the dev store is unreachable, `make run` exits with the same startup error as production, and `make run-offline` still works.

### 7. Deploy to production

- **Starts it:** the step 4/5 pull request is merged. CI builds the image. Deploy to any non-production environment first using `orders-api/<env>`, and proceed once it is ready.
- **What moves:** the existing rolling deploy, one pod at a time with `maxUnavailable: 0`, in the existing pipeline.
  - A new pod starts and loads the three keys from the store using `orders-api-prod`. It becomes ready only after all three are loaded.
  - Only then is an old pod stopped.
  - During the rollout, old pods keep serving with the old keys from their baked-in YAML, and new pods serve with the new keys. Both are valid at the provider, so no request fails on either side.
- **State:** the keys live in each pod's process memory. The old pods' copies disappear as the pods stop.
- **If it fails:**
  - If a new pod cannot load the keys, it retries 3 times, exits non-zero and never becomes ready. The rollout halts and the old pods keep serving.
  - Fix the store access or the key and redeploy.
  - Rollback to the previous image is safe at this point, because the old keys are still active.

### 8. Confirm every running instance is on the new keys

- **Starts it:** the rollout in step 7 shows complete, and at least one full refresh cycle has passed (5 minutes).
- **What moves:** nothing. This is a check, done by the security on-call or the release engineer. All of these must hold:
  1. The cluster lists exactly the expected pods, all running the post-migration image. No pod from an older image exists.
  2. For each of those pods, the central logs contain a "secret loaded" line (`name=<name> version=<id>`) for each of the three names. The version id matches the store's current version id for that secret.
  3. A pod with no such line is treated as not confirmed. Missing evidence blocks the next step.
- **State:** the evidence is the pod list, the log lines and the store's current version ids, recorded on the ticket.
- **If it fails:** wait one more refresh cycle and check again. If a pod still lacks the version, investigate that pod. Do not revoke anything.

### 9. Close the rollback door, then revoke the old keys

- **Starts it:** step 8 passed for the provider in question, and the release owner agrees that the rollback window is closed.
- **What moves:**
  1. Mark every pre-migration image as non-deployable in the registry or the deploy pipeline. They contain old keys and would fail once those keys are revoked. Rollback from now on means redeploying an image built from step 7 or later.
  2. If the provider shows when a key was last used, check that the old key has had no traffic for a reasonable period, such as 1 hour.
  3. The security on-call revokes the old key at the provider, one provider at a time.
- **State:** the old key's state is held at the provider. The ticket records the date and time of each revocation.
- **If it fails:** if error rates for that provider rise right after revocation, the cause is an instance still using the old key. Issue a fresh key at the provider, write it to the store as a new version, and let the 5-minute refresh pick it up. Do not restore the old key, which is treated as leaked. Then work out how step 8 missed that instance.

### 10. Close out

- **Starts it:** all three old keys are revoked.
- **What moves:**
  - Watch provider authentication-failure counts and the app's error rate for 24 hours.
  - Confirm CI is green on `main` with the guard in place.
  - Record that the keys remain in git history and in old images, and that they are harmless because they are revoked. History is not being rewritten.
  - Delete the old images from the registry if policy allows.
- **State:** the ticket and the rotation record.
- **If it fails:** a failure here is handled the same way as step 9. Rotate again through the normal path (step 16).

## Part B: How the app reads keys at runtime

### 11. Process start: load all three keys

- **Starts it:** the process starts. `app.name`, ports and URLs are read from `config/app.yaml` as before.
- **What moves:** `secrets.start()` reads `orders-api/<APP_ENV>/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key` from the store, using the pod's service identity. It records each value and its version id in process memory, then logs `secret loaded name=<name> version=<id>`.
- **State:** the in-memory dictionary, holding the value and version id for each name. No key goes to disk, to an environment variable, or into a log line.
- **If it fails:**
  - Any failure to read any of the three keys counts, including an unreachable store, access denied and a missing secret.
  - The app makes 1 initial attempt and then retries 3 times, 2 seconds apart.
  - After the last retry it logs the secret name and the error class, never a value, and exits with a non-zero code.
  - In the cluster this makes the pod crash and keeps it out of rotation (see step 12).

### 12. Readiness

- **Starts it:** `secrets.start()` returns with all three keys loaded.
- **What moves:** `/healthz` changes from 503 to 200 with `{"status": "ok"}`. Until then it returns 503, even if the HTTP server is already listening.
- **State:** a single in-process ready flag, set once and never cleared. The readiness probe in the deploy configuration stays as it is.
- **Why it matters:** `maxUnavailable: 0` only protects customers if a pod without keys is never ready. Without this change a pod could report ready, take traffic and fail every call.
- **Later store problems:** a failed refresh after startup does not change `/healthz`. If it did, a store outage would make every pod unready at once, even though each pod has working keys.
- **If it fails:** a pod that never becomes ready is stopped by the rollout and does not serve. The old pods keep serving.

### 13. Using a key on each request

- **Starts it:** a request needs to call a provider.
- **What moves:** the client calls `secrets.get('payments_api_key')` (or the matching name) for each outbound call and builds the `Authorization` header from the result. It does not store the value on `self`.
- **State:** the current value in the in-memory dictionary. The read takes the lock briefly and returns a plain string.
- **If it fails:**
  - A request that has already read a key finishes with that key, even if a refresh swaps the value a moment later.
  - If `get()` is called before the first load, which should not happen because the pod is not ready, it raises a clear internal error.
  - Optional hardening, not required for this plan: on an authentication error from a provider, trigger one immediate re-read.

### 14. Refresh every 5 minutes

- **Starts it:** a background timer in each process fires every 5 minutes, beginning 5 minutes after the first load.
- **What moves:** it re-reads each of the three names. For each, if the version id differs from the one in memory and the value is non-empty, it swaps in the new value and version id together, and logs `secret loaded name=<name> version=<id>`. If the version is unchanged, it does nothing.
- **State:** the same in-memory dictionary, updated under the lock so a reader never sees a new value with an old version id.
- **If it fails:**
  - Each name is handled separately, so one failure does not affect the other two.
  - A failed re-read keeps the last good value and logs a warning with the secret name and the error class.
  - It never stores an empty or malformed value.
  - It tries again at the next tick.
  - Alert if a pod has gone more than 15 minutes (3 cycles) without a successful re-read, so a silent loss of access is noticed before it matters.
  - The one case it cannot cover is a key revoked at the provider before the instance has refreshed, which is why step 16 holds the old key until every pod is confirmed.

### 15. Logging rules

- **Starts it:** every log call in the secrets code and in the three clients.
- **What moves:** logs may contain the secret name, the version id, the error class and timestamps. They never contain the value, the `Authorization` header, or a request object that includes headers. HTTP client debug logging stays off.
- **State:** logs are kept in the central log service for 30 days, which is another reason values must not appear there.
- **If it fails:** the step 4 log-capture test catches a leak before merge. If a value is ever found in logs, treat that key as leaked and rotate it through step 16.

### 16. Later rotation (runbook)

- **Starts it:** a security decision to rotate a key, for example after a suspected leak. This plan does not set a schedule (see open questions).
- **What moves:**
  1. The security on-call creates a new key at the provider while the old key stays active.
  2. They check the new key with one cheap authenticated call.
  3. They write the new key to `orders-api/prod/<name>`, which creates a new version id.
  4. Every pod picks it up within 5 minutes, with no restart and no failed request.
  5. When step 8's check passes for every pod, they revoke the old key.
- **State:** the store holds the current version. The provider holds both keys until the last step.
- **If it fails:**
  - A bad new key written by mistake is overwritten with a corrected version, which the pods pick up within 5 minutes. Do not revoke the old key until that is sorted out.
  - If the store is down during the window, pods keep using their last good value, and the revoke waits.

## Open questions

1. **Scheduled rotation:** should keys also be rotated on a regular schedule after this migration, and how often? Security has not decided, and this plan sets no cadence. Whatever they choose, step 16 and the 5-minute refresh already allow rotation without downtime. The decision only affects how often the runbook is run and who owns the calendar.
2. **Providers with a single active key:** if step 1 finds a provider that cannot have two active keys, a safe path for that provider has to be agreed with the provider before it can be migrated.
