# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

The three live keys (payments, email, geocoding) leave `config/app.yaml` and live in the secret store under `orders-api/<env>/<name>`. The app loads them into memory at startup and re-reads them every 5 minutes. The keys are rotated at each provider, and the old keys are revoked only after every instance is confirmed to use the new ones.

Two properties from the existing setup shape the order of steps:

- **Rollback.** Rollback means redeploying an earlier image, and those images contain the old keys. The old keys therefore have to stay valid until rollback to a pre-migration image is no longer possible.
- **Readiness.** `/healthz` currently returns 200 as soon as the server listens. It has to wait for the keys, so that a pod without them never takes traffic and the rolling deploy (`maxUnavailable: 0`) halts instead of replacing good pods.

**Secret names** (same in every environment):

- `orders-api/<env>/payments_api_key`
- `orders-api/<env>/email_api_key`
- `orders-api/<env>/geocoding_api_key`

**Assumptions to confirm in step 6.** If any of these is false, stop and rework the plan for that item before touching prod.

- Each provider lets us hold two active keys at once. This is needed for zero-failure rotation.
- A staging environment and a dev store path exist or can be created.
- Pods authenticate to the store through their service identity, with no static credential on disk or in env vars.
- Providers offer sandbox or test keys for dev.

---

## Part A. How the app reads keys at runtime

This part is built in one change (step 9). Steps 1-5 describe the behaviour that change must have.

### 1. Boot: load non-secret config, build clients without keys

- **Starts it:** process start.
- **What moves:** `config_loader.py` still reads `config/app.yaml` for `base_url`, timeouts, port and so on. `APP_ENV` (`prod`, `staging` or `dev`) comes from the deployment manifest. It is not a secret.
- **Where state lives:** non-secret settings are in the `settings` dict as today.
- **Code changes in this step:**
  - The loader ignores any `api_key` it finds.
  - The three client singletons (`payments`, `email`, `geocoding`) are still built at import, but they no longer copy a key in `__init__`.
  - Each client calls `secrets.get('<name>')` on every request. This is what lets a refreshed key take effect with no restart.
- **If it fails:** a missing or invalid YAML file crashes the process, as today.

### 2. Startup load: all three keys before ready

- **Starts it:** step 1 finished.
- **What moves:** a new `app/secrets.py` module reads the three secrets from `orders-api/$APP_ENV/*`. Each read returns a value and a version id. The module stores them as one immutable snapshot, `{name: (value, version_id)}`, in process memory.
- **Where state lives:** only in process memory. Nothing goes to disk, an env var, a log line or an exception message. Only version ids are logged, for example `secret loaded name=payments_api_key version=<id>`.
- **Retry behaviour:**
  - An attempt succeeds only if all three secrets are fetched and non-empty.
  - On failure, wait 2 seconds and try again, for up to 3 retries (4 attempts, about 6 seconds in total).
  - After the last failure, log the error class (not the message body) and exit with a non-zero code, for example `70`.
- **Readiness:** the HTTP server may listen early, but `/healthz` returns 503 `{"status":"starting"}` until the snapshot holds all three keys. Then it returns 200 `{"status":"ok"}`.
- **If it fails:**
  - The pod exits and Kubernetes restarts it, so it never becomes ready.
  - In a rolling deploy the new pod never passes readiness, the rollout halts, and the old pods keep serving.
  - Customers see no impact.

### 3. Steady state: serve requests from memory

- **Starts it:** every outbound provider call.
- **What moves:** the client reads the current key from the snapshot and puts it in the `Authorization` header, as today. There is no store call on the request path.
- **Where state lives:** the snapshot reference in memory. It is swapped atomically, so a request sees either the old or the new value, never a mix.
- **Safeguard:** HTTP debug logging, error reporting and tracing must not capture request headers. Check this in step 9.
- **If it fails:** the snapshot is never empty after startup, so there is no "missing key" case at request time.

### 4. Refresh every 5 minutes

- **Starts it:** a background timer in each instance, every 300 seconds. Each pod's timer starts when that pod becomes ready, so pods are naturally staggered.
- **What moves:** read each secret. If the version id differs from the one held, validate the new value (non-empty, no stray whitespace) and swap it in. Log `secret refreshed name=... version=... (was ...)`.
- **Where state lives:** the in-memory snapshot, plus metrics that carry version ids only:
  - `secret_version_in_use{name,version}`
  - `secret_last_refresh_success_timestamp{name}`
- **If it fails** (store unreachable, access denied, empty value, timeout):
  - Keep using the last good value and log a warning with the secret name and error class.
  - Retry at the next tick.
  - The pod stays ready. Taking pods out of service because the store is down would turn a store outage into a customer outage.
  - Alert if `last_refresh_success` is older than 15 minutes (3 missed cycles).
- **Known limit:** a pod that restarts while the store is down cannot start (step 2). With 4 replicas this reduces capacity but does not break serving pods. A pod can run without a refresh indefinitely, so rotation must never assume that time alone means "adopted". Step 14 requires evidence instead.

### 5. Local development

- **Starts it:** `make run`, which now sets `APP_ENV=dev`.
- **What moves:**
  - It loads `config/app.yaml` plus `config/app.dev.yaml`, which points `base_url` at provider sandboxes.
  - It reads `orders-api/dev/*` from the store with the engineer's own identity.
  - Those values are sandbox keys, not live keys.
  - The prod path is not readable by engineers (step 7).
- **Offline option:** `APP_ENV=dev-offline` runs against local mock providers with fixed dummy keys that are not real credentials. This backend is rejected unless `APP_ENV` is exactly `dev-offline`, so it cannot be enabled in prod.
- **If it fails:** the dev run exits through the same retry-then-exit path as step 2. The engineer can fall back to `dev-offline`.

---

## Part B. Rollout

Order matters: access and new keys come first, then code, then rotation proof, then revocation. Revocation is the only irreversible step, so it comes last.

### 6. Confirm assumptions and inventory key usage

- **Starts it:** plan approved.
- **What moves:** nothing is changed.
- **Who and what:**
  - The security on-call confirms with each provider that two keys can be active at once. They also confirm what the provider's dashboard shows for key last-used time or traffic.
  - Engineering lists everything that uses the current keys: the 4 prod replicas, any workers or cron jobs built from the same image, CI integration tests, developer laptops via `make run`, and any other service or doc that holds a copy.
- **Where state lives:** a checklist in the tracking ticket, with no key values in it.
- **If it fails:**
  - If a provider allows only one active key, stop for that provider. Zero-failure rotation as written is not possible for it. Raise it with security for an alternative.
  - If an unknown consumer is found, add it to the list and handle it in step 13.

### 7. Create store paths, encryption and access

- **Starts it:** step 6 complete.
- **What moves:** the platform and security teams create the following, with no values yet:
  - a per-environment KMS key for each of `dev`, `staging` and `prod`
  - the `orders-api/<env>/` namespaces
- **Access policy:**

| Identity | Access |
|---|---|
| `orders-api-prod` | Read-only on `orders-api/prod/*`, nothing else |
| Security on-call | Write on `orders-api/prod/*` |
| Engineers | No access to prod values |
| Engineers | Read on `orders-api/dev/*` (sandbox keys) |

- **Where state lives:** store policy and KMS configuration, kept as code or an exported policy in the ticket.
- **Verification:** run these before continuing.
  - Write a throwaway value to `orders-api/prod/_check` as security on-call.
  - Confirm `orders-api-prod` can read it.
  - Confirm `orders-api-prod` cannot write it.
  - Confirm `orders-api-prod` cannot read a path outside `orders-api/prod/*`.
  - Confirm an engineer identity is denied.
  - Delete the throwaway.
- **If it fails:** fix the policy and re-verify. Nothing depends on the store yet, so there is no impact.

### 8. Create new keys at the providers and load the store

- **Starts it:** step 7 verified.
- **What moves:**
  1. The security on-call creates a new live key at each provider. The old key stays active.
  2. The on-call tests each new key with a harmless authenticated call, such as a read-only or zero-amount call.
  3. The on-call writes each tested key to `orders-api/prod/<name>`, giving version 1.
  4. The same is done for `staging` with the provider's test keys, and for `dev` with sandbox keys.
- **Where state lives:** the store, encrypted with the per-environment KMS key. Values never go in chat, tickets or files. The on-call pastes them directly from the provider console into the store write.
- **Why now:** the new keys are used by nobody yet, so this is risk-free. The old keys keep serving all traffic.
- **If it fails:**
  - If key creation or the test call fails, stop. Prod is unaffected.
  - If a write fails, retry.
  - A key that fails its test call is not written. A bad key written to the store would reach every instance within 5 minutes.

### 9. Build the app change, with the CI guard

- **Starts it:** step 8 complete, so the store has values for every environment.
- **What moves:** one PR contains the following.
  - The Part A behaviour: `app/secrets.py`, per-request key reads in the three clients, the readiness gate, the refresh thread, the metrics, and `config/app.dev.yaml`.
  - Removal of every `api_key` line from `config/app.yaml`.
  - The CI check described below.
  - A check that no logging or tracing path emits request headers.
- **The CI check:**
  - It runs on every PR and is a required status check on `main`.
  - It parses `config/*.yaml` and fails if any `api_key` key exists at any depth, whatever its value, including empty.
  - It also scans those files for known key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) as a second net.
- **Tests:**
  - Startup retries 3 times, 2 seconds apart, then exits non-zero.
  - `/healthz` is 503 until all three keys are loaded.
  - A failed refresh keeps the last good value and logs a warning.
  - A new version is picked up without a restart.
  - Log capture contains version ids and no key values.
  - The CI check fails on a deliberate PR that re-adds `api_key`.
- **Where state lives:** git. This PR does not merge until step 10 passes (step 8 is already done).
- **If it fails:** fix in review. Nothing has shipped.
- **Rollback property:** the previous image still contains the old yaml keys, which stay valid, so redeploying it remains a safe rollback until step 14.

### 10. Staging soak

- **Starts it:** PR image built from the branch.
- **What moves:** deploy to staging and exercise each failure path:
  - Block store access: the pod exits non-zero after 4 attempts and never becomes ready.
  - Write a new version of a staging secret: the pod logs the new version id within 5 minutes and the next request uses it.
  - Block the store after startup: warnings appear, the old value is kept, and the pod stays ready.
- **Where state lives:** staging store and pods.
- **If it fails:** fix the code and repeat. Do not proceed to prod until all three behaviours are seen.

### 11. Production rolling deploy

- **Starts it:** PR approved and merged to `main`. CI builds the image and the rolling deploy starts, one pod at a time with `maxUnavailable: 0`.
- **What moves:**
  - Each new pod reads the new prod keys (v1) and becomes ready.
  - Old pods still use the old yaml keys. Both key sets are valid at the providers, so a mixed fleet is fine.
- **Pause point:** pause the rollout after the first new pod becomes ready. Watch that pod's provider calls for 401 or 403 responses and for payment, email and geocoding error rates. Resume only if the rate matches the old pods.
- **Where state lives:** pod memory plus the version-id metrics.
- **If it fails:**
  - If a pod cannot load the keys, it never becomes ready and the rollout halts, with the old pods still serving. Fix the cause (usually IAM or a store path) and resume.
  - If the first pod shows provider auth errors, stop the rollout and redeploy the earlier image. Its old keys are still valid.
  - If a new key is bad, the on-call writes the previous good value as a new version. Instances pick it up in 5 minutes or less.

### 12. Prove runtime refresh in prod

- **Starts it:** all 4 replicas run the new image, with no old-image pods left. This includes any workers or cron jobs from step 6.
- **What moves:** the security on-call writes the same value of one prod secret as a new version. The store gives it a new version id.
- **Where state lives:** the store holds the new version. Each pod's metrics show the version in use.
- **Success:** within about 10 minutes, `secret_version_in_use` shows the new id on every pod, and requests are unaffected.
- **If it fails:**
  - If any pod does not pick up the version, investigate (IAM, refresh thread, store errors). Do not continue to revocation. The rest of the plan assumes this works.
  - Customers are unaffected, because the pod simply keeps the last good value.

### 13. Remove the paths that still hold or run old keys

- **Starts it:** step 12 succeeded.
- **What moves:**
  - Pin the deploy tooling so any image built before the migration cannot be deployed or rolled back to. After this, rollback targets are post-migration images only.
  - Any unknown consumer from step 6 gets its own migration to the store or its own key, or is explicitly accepted as breaking at revocation.
  - Announce to engineers that old checkouts using the live keys will stop working at revocation. Current `make run` uses the dev store.
- **Where state lives:** deploy tooling configuration and the tracking ticket.
- **Why:** after revocation, rolling back to an old image would put the revoked key into service, and every customer request through it would fail. Rollback must be impossible, not merely discouraged.
- **If it fails:** if rollback cannot be blocked, delay revocation. Do not revoke.

### 14. Confirm every instance uses the new keys, then revoke the old ones

- **Starts it:** steps 12 and 13 complete.
- **Gate:** all of the following must hold, from evidence rather than elapsed time:
  - Every running pod's `secret_version_in_use` shows the new version id for all three keys.
  - Every pod's `last_refresh_success` is newer than the last store write.
  - No pod reports a refresh warning.
  - No old-image pod exists in any deployment, worker or cron job.
  - The provider dashboard shows no recent traffic on the old key from sources we cannot account for. Leave a quiet period of at least 24 hours, or as the on-call decides.
- **What moves:** the security on-call revokes each old key at its provider, one provider at a time, with a second person present. After each revocation, watch error rates and provider 401 and 403 responses for a few minutes before the next.
- **Where state lives:** provider consoles. The old key values now live only in git history and old images.
- **If it fails:**
  - Revocation cannot be undone. If requests fail after revoking, create another new key, test it, and write it to the store. Instances adopt it in 5 minutes or less. This is why the gate above must pass before revoking.
  - If a gate item cannot be confirmed, do not revoke.

### 15. Clean up and close

- **Starts it:** all three old keys revoked.
- **What moves:**
  - Delete pre-migration images from the registry, since they embed the old keys.
  - Remove the throwaway `_check` secret and any temporary access granted during migration.
  - Run the planted-key test one more time: a PR that re-adds `api_key` to `config/app.yaml` must fail CI.
  - Record the migration in the runbook, including how the security on-call writes a new version and how to confirm adoption from the metrics.
- **Where state lives:** git, registry, runbook.
- **Note:** git history is not rewritten, so the old keys remain visible there. They are dead after step 14, so the exposure is closed.
- **If it fails:** a failed cleanup does not affect customers. Re-run it and track it in the ticket.

---

## Open question (not decided)

**Regular rotation schedule.** Security has not decided whether keys must also be rotated on a schedule after this migration, or how often. No cadence is chosen here. This plan makes rotation operationally cheap: the on-call writes a new version, and instances adopt it within 5 minutes with no deploy. Whatever cadence security picks can reuse steps 12 and 14 as the procedure. Security owns the decision.
