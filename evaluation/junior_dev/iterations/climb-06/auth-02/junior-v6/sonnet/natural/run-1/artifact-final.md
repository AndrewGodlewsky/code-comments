# Plan: Move orders-api provider keys into the managed secret store

## What this is

Today `orders-api` reads three live provider keys (payments, email, geocoding) from `config/app.yaml`. That file is committed to the repo and copied into every container image. `app/config_loader.py` reads it once at import, and each provider client copies its key into itself when it is built. Changing a key means a new image and a redeploy.

This plan moves the keys into our managed secret store. The app then loads them from the store when it starts and re-reads them every 5 minutes.

The flow, start to finish:
1. Security creates new keys at each provider and puts them in the store. The old keys stay valid.
2. The app is changed to load the keys at startup, refuse to report ready until it has all three, and re-read them every 5 minutes.
3. The keys are deleted from the YAML, and a CI check stops them coming back.
4. A normal rolling deploy replaces old pods (old keys, baked into their image) with new pods (new keys, from the store). Both keys are valid at the provider, so no request fails.
5. Only when every running pod is confirmed to be on the new keys are the old keys revoked.

The old keys have been in git history for two years, so they are treated as leaked. History is not being rewritten, so every key is rotated and the old ones are revoked at the end.

## Terms

- **Store:** the managed secret store. It holds each secret under `orders-api/<env>/<name>`, encrypts it at rest with a per-environment KMS key, and gives every write a new version id.
- **KMS key:** the encryption key the store uses. Prod and dev have separate ones.
- **Names:** `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- **Version id:** a label the store gives each write. It is not secret and may be logged.
- **Service identity:** the account a workload runs as. Prod pods run as `orders-api-prod`. The store checks this identity on every read.
- **`APP_ENV`:** an ordinary, non-secret environment variable (`prod` or `dev`) that tells the app which store path to read. It is set in each environment's deploy configuration. If it is missing, the app exits non-zero at startup.
- **Readiness probe:** `GET /healthz`. A rolling deploy starts a new pod, waits for the probe to return 200, then stops one old pod. `maxUnavailable: 0` means an old pod is never stopped before its replacement is ready.
- **Security on-call:** the only role that can write prod secrets and revoke keys at the providers.
- **Old key / new key:** the leaked key now in the YAML, and the replacement created at the provider. The provider must accept both at once during the migration.

## Rules that hold throughout

- Providers: payments, email, geocoding. `base_url`, timeouts and `from_address` stay in `config/app.yaml`. Only the `api_key` entries leave it.
- `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only the security on-call writes prod secrets. Engineers must not be able to read prod values.
- Key values exist only in process memory. They never go on disk, into environment variables or into logs. Version ids may be logged.
- Production runs 4 replicas. Logs go to the central log service and are kept for 30 days.
- No customer request may fail because of a missing or revoked key at any point.
- Rollback means redeploying an earlier image.

Steps 1-3 touch only the store and providers. Steps 4-7 are code and deploy. Steps 8-10 retire the old keys. Steps 11-15 describe how the running app behaves, and the code in step 4 implements them. Step 16 is the runbook for later rotations.

## Part A: Rollout

### 1. Check that every provider supports two active keys

- **Starts it:** the plan is approved.
- **What moves:** nothing. The security on-call reads each provider's docs or console, or asks the provider.
- **State:** the result is recorded on the migration ticket.
- **If it fails:** if a provider allows only one active key, rotating it would break requests. Stop for that provider and ask for a grace window or a second key slot. The other providers can proceed.

### 2. Create the store layout and access rules

- **Starts it:** step 1 is confirmed for at least one provider.
- **What moves:** infrastructure changes only, no secrets.
  - Create the KMS keys, with prod and dev kept separate.
  - Create the empty secret paths `orders-api/prod/{payments,email,geocoding}_api_key`, and the same under `orders-api/dev/`.
  - Grant `orders-api-prod` read-only access to `orders-api/prod/*`, plus decrypt on the prod KMS key only.
  - Allow writes to `orders-api/prod/*` only for the security on-call role.
  - Add an explicit deny so engineer roles cannot read or write `orders-api/prod/*`.
  - Let engineers read `orders-api/dev/*`, and write it if they maintain the sandbox keys.
  - Give any non-production deploy environment its own service identity with read-only access to `orders-api/dev/*` (used in step 7).
- **State:** the policies live in the store's IAM and KMS configuration, kept as code in the infrastructure repo.
- **Verify, each with a real call:** `orders-api-prod` can read prod and cannot write prod. `orders-api-prod` cannot read dev. An engineer role is denied on prod reads. The security on-call role can write prod. Also confirm that a real prod pod, running as `orders-api-prod`, can authenticate to the store without anyone supplying a credential at deploy time.
- **If it fails:** fix the policy and run the tests again. Nothing in the app depends on the store yet, so there is no customer impact. Do not go on until the engineer-denied test passes.

### 3. Issue new keys and load them into the store

- **Starts it:** step 2 verification has passed.
- **What moves:**
  - The security on-call creates a new key at each provider. The old keys stay active.
  - They check each new key with one cheap authenticated call to that provider.
  - They write the new key to `orders-api/prod/<name>`, which creates version 1.
  - Engineers get sandbox or test keys, written to `orders-api/dev/<name>`.
- **State:** the new prod keys exist only at the provider and in the store. They are never put in a ticket, chat message, file or CI variable. Only the version ids are recorded on the ticket.
- **If it fails:** if the provider call fails, do not write the key; create another. A bad key already written is overwritten by a new version. No running instance reads the store yet.

### 4. Implement the runtime secret reader and gate readiness on it

- **Starts it:** step 3 is done for the dev path at least, so the code can be tested. It can be built in parallel with steps 2-3.
- **What moves:** code only. The behavior is described in Part B.
  - Add `app/secrets.py` with `start()` and `get(name)`.
  - Change `PaymentsClient`, `EmailClient` and `GeocodingClient` so they no longer copy the key in `__init__`. Each outbound call runs `secrets.get('<name>')` at the moment of the request. The module-level singletons stay, but constructing them must not read secrets, because construction happens at import, before the first load.
  - Make `/healthz` return 200 only after the first successful load of all three keys. Before that it returns 503.
  - Add a defensive check in `config_loader.py`: if the loaded YAML contains an `api_key` key at any depth, the process refuses to start. This guards against an old config file.
- **State:** secrets live in a process-memory dictionary guarded by a lock.
- **Tests required:**
  - A fake store that is down for the first 3 attempts, then up: the app reaches ready.
  - A fake store that is down for good: the app exits non-zero after 3 retries.
  - A refresh that fails: the old value stays in use and a warning is logged.
  - A refresh that succeeds: the next request uses the new value.
  - A log-capture test: the key value never appears in logs.
- **If it fails:** the pull request does not merge.

### 5. Remove the keys from `config/app.yaml` and add the CI guard

- **Starts it:** step 4 is code-complete. Both changes ship in the same pull request as step 4. Merging the guard first would fail `main`; removing the keys without the new code would break startup.
- **What moves:**
  - Delete the three `api_key` lines and their "live key" comments from `config/app.yaml`. This changes only the new image. Images built earlier are immutable and keep the old YAML, which is how old pods still have their keys during the rollout.
  - Add a CI job that parses `config/app.yaml` as YAML and fails if any key named `api_key` exists at any depth, in any letter case. It also fails if the file does not parse.
- **State:** the check lives in the CI configuration in the repo.
- **Verify:** open a throwaway branch that adds `api_key: x` to the file, confirm CI goes red, then close the branch.
- **If it fails:** fix a guard that does not trip before merge. Fix a false failure in the check itself, never by ignoring `api_key`.

### 6. Local development

- **Starts it:** part of the step 4 pull request.
- **What moves:** `make run` no longer reads keys from `config/app.yaml`.
  - It starts the app with `APP_ENV=dev`. The app reads `orders-api/dev/*` with the engineer's own store login, using the same code path as production.
  - A `make run-offline` target points the three clients at local stub servers and needs no store access and no keys.
  - `deploy.md` and the README are updated to describe both, and each environment's deploy configuration sets `APP_ENV`.
- **State:** dev keys are provider sandbox or test keys, held in the dev path and in process memory. Prod pods set `APP_ENV=prod`.
- **Safety:** an engineer cannot read prod even by setting `APP_ENV=prod`, because the deny rule from step 2 refuses the read.
- **If it fails:** if the dev store is unreachable, `make run` exits with the same startup error as production, and `make run-offline` still works.

### 7. Deploy to production

- **Starts it:** the step 4/5 pull request is merged and CI has built the image. First deploy the image to a non-production environment that sets `APP_ENV=dev` and runs under its own non-prod identity (from step 2), and continue once it is ready.
- **What moves:** the existing rolling deploy, one pod at a time with `maxUnavailable: 0`.
  - A new pod starts and loads the three keys from the store as `orders-api-prod`. It becomes ready only after all three are loaded.
  - Only then is an old pod stopped.
  - During the rollout, old pods keep serving with the old keys from the YAML baked into their image, and new pods serve with the new keys. Both are valid at the provider, so no request fails on either side.
- **State:** keys live in each pod's process memory. The old pods' copies disappear as the pods stop.
- **If it fails:**
  - A new pod that cannot load the keys retries 3 times, exits non-zero and never becomes ready. The rollout halts and the old pods keep serving.
  - Fix the store access or the key and redeploy.
  - Rolling back to the previous image is safe at this point, because the old keys are still active.

### 8. Confirm every running instance is on the new keys

- **Starts it:** the rollout shows complete and at least one full refresh cycle (5 minutes) has passed.
- **What moves:** nothing. The security on-call or the release engineer checks all of the following:
  1. The cluster lists exactly the expected 4 pods, all running the post-migration image. No pod from an older image exists.
  2. For each pod and each of the three names, take the most recent log line `secret loaded name=<name> version=<id>`. The app logs this at start and again whenever a version changes, so the latest line is the version the pod is using. It must equal the store's current version id for that secret.
  3. That pod has no refresh-failure warning after that line, since a failing refresh could hide a newer version.
  4. A pod with a missing or mismatched line is not confirmed. Missing evidence blocks the next step.
- **State:** the evidence (pod list, log lines, store version ids) is recorded on the ticket.
- **If it fails:** wait one more refresh cycle and check again. If a pod still lacks the version, investigate that pod. Do not revoke anything.

### 9. Close the rollback door, then revoke the old keys

- **Starts it:** step 8 passed for the provider in question, and the release owner agrees the rollback window is closed.
- **Why the old key waited until now:** until every pod is confirmed, a pod still on an older image, a restart from an older image or a rollback would use the old key. Revoking it earlier would make those requests fail.
- **What moves:**
  1. Mark every pre-migration image as non-deployable in the registry or the pipeline. They contain old keys and would fail once those keys are revoked. Rollback from now on means redeploying an image built from step 7 or later.
  2. If the provider shows when a key was last used, check that the old key has had no traffic for a reasonable period, such as 1 hour.
  3. The security on-call revokes the old key at the provider, one provider at a time.
- **State:** the old key's state is held at the provider. The ticket records the date and time of each revocation.
- **If it fails:** if error rates for that provider rise right after revocation, an instance is still using the old key. Issue a fresh key at the provider, write it to the store as a new version, and let the 5-minute refresh pick it up. Do not restore the old key, which is treated as leaked. Then work out how the step 8 check missed that instance.

### 10. Close out

- **Starts it:** all three old keys are revoked.
- **What moves:**
  - Watch provider authentication-failure counts and the app's error rate for 24 hours.
  - Confirm CI is green on `main` with the guard in place.
  - Record that the keys remain in git history and old images and are harmless because they are revoked. History is not rewritten.
  - Delete the old images from the registry if policy allows.
- **State:** the ticket and the rotation record.
- **If it fails:** handle it as in step 9, rotating again through the runbook in step 16.

## Part B: How the app reads keys at runtime

### 11. Process start: load all three keys

- **Starts it:** the process starts. `app.name`, ports and URLs are read from `config/app.yaml` as before.
- **What moves:** `secrets.start()` reads `orders-api/<APP_ENV>/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key` from the store. The pod authenticates with its platform-provided service identity; no credential is passed in by hand. It records each value and version id in process memory and logs `secret loaded name=<name> version=<id>`.
- **State:** the in-memory dictionary, holding value and version id per name. No key goes to disk, an environment variable or a log line.
- **If it fails:**
  - Any failure to read any of the three counts: unreachable store, access denied, missing secret.
  - The app makes 1 initial attempt, then retries 3 times, 2 seconds apart.
  - After the last retry it logs the secret name and the error class, never a value, and exits non-zero.
  - In the cluster the pod crashes and stays out of rotation.

### 12. Readiness

- **Starts it:** `secrets.start()` returns with all three keys loaded.
- **What moves:** `/healthz` changes from 503 to 200 with `{"status": "ok"}`. Until then it returns 503, even if the HTTP server is already listening.
- **State:** a single in-process ready flag, set once and never cleared. The probe configuration stays as it is.
- **Why:** `maxUnavailable: 0` only protects customers if a pod without keys is never ready. Today `/healthz` returns ok as soon as the server listens, which would not be enough.
- **Later store problems:** a failed refresh after startup does not change `/healthz`. Otherwise a store outage would make every pod unready at once, though each has working keys.
- **If it fails:** a pod that never becomes ready is stopped by the rollout and does not serve. The old pods keep serving.

### 13. Using a key on each request

- **Starts it:** a request needs to call a provider.
- **What moves:** the client calls `secrets.get('<name>')` for each outbound call and builds the `Authorization` header from the result. It does not store the value on `self`.
- **State:** the current value in the in-memory dictionary. The read takes the lock briefly and returns a plain string.
- **If it fails:**
  - A request that already read a key finishes with it, even if a refresh swaps the value a moment later. During the migration both keys are valid at the provider, so this is safe.
  - If the provider rejects the key with an authentication error, the client returns it to the caller as an ordinary provider error. There is no retry. If the migration order is followed, this cannot happen.
  - If `get()` runs before the first load, which should not happen because the pod is not ready, it raises a clear internal error.
  - Optional hardening, not required: on an authentication error, trigger one immediate re-read.

### 14. Refresh every 5 minutes

- **Starts it:** a background thread in each process wakes every 5 minutes, beginning 5 minutes after the first load. It is a daemon thread that catches every exception, so one bad cycle cannot kill it. It runs separately from request handling.
- **What moves:** it re-reads each of the three names. If the version id differs from the one in memory and the value is non-empty, it swaps in the new value and version id together and logs `secret loaded name=<name> version=<id>`. If the version is unchanged, it does nothing.
- **State:** the same in-memory dictionary, updated under the lock so a reader never sees a new value with an old version id. The process also keeps a last-successful-refresh time per name and exposes it as a metric.
- **If it fails:**
  - Each name is handled separately, so one failure does not affect the others.
  - A failed re-read keeps the last good value and logs a warning with the secret name and the error class.
  - It never stores an empty or malformed value, and tries again at the next tick.
  - Alert if any name has had no successful re-read for more than 15 minutes (3 cycles). This also catches a thread that has died or stalled, because the time stops advancing.
  - The one case this cannot cover is a key revoked at the provider before the instance has refreshed. That is why the old key is held until the step 8 check passes for every pod and revoked only in step 9.

### 15. Logging rules

- **Starts it:** every log call in the secrets code and in the three clients.
- **What moves:** logs may contain the secret name, version id, error class and timestamps. They never contain the value, the `Authorization` header, or a request object that includes headers. HTTP client debug logging stays off.
- **State:** logs are kept 30 days in the central log service, which is another reason values must not appear there.
- **If it fails:** the log-capture test in step 4 catches a leak before merge. If a value is ever found in logs, treat that key as leaked and rotate it through step 16.

### 16. Later rotation (runbook)

- **Starts it:** a security decision to rotate a key, for example after a suspected leak. This plan sets no schedule (see open questions).
- **What moves:**
  1. The security on-call creates a new key at the provider while the old key stays active.
  2. They check the new key with one cheap authenticated call.
  3. They write it to `orders-api/prod/<name>`, creating a new version id.
  4. Every pod picks it up within 5 minutes, with no restart and no failed request.
  5. When the step 8 check passes for every pod, they revoke the old key.
- **State:** the store holds the current version. The provider holds both keys until the last step.
- **If it fails:**
  - A bad new key written by mistake is overwritten with a corrected version, which pods pick up within 5 minutes. Do not revoke the old key until that is sorted out.
  - If the store is down during the window, pods keep their last good value and the revoke waits.

## Open questions

1. **Scheduled rotation:** should keys also be rotated on a regular schedule after this migration, and how often? Security has not decided, and this plan sets no cadence. Step 16 and the 5-minute refresh already allow rotation without downtime. The decision only affects how often the runbook runs and who owns the calendar.
2. **Providers with a single active key:** if step 1 finds a provider that cannot have two active keys, a safe path has to be agreed with that provider before it can be migrated.
3. **How the pod proves its identity to the store:** deploy.md says pods run under `orders-api-prod` but not how the store learns that. This plan assumes the platform attaches the identity to the pod. Step 2 checks it with a real prod pod.
4. **Non-production environment:** this plan assumes one can use the dev path and a separate non-prod identity. Confirm whether such an environment exists.
