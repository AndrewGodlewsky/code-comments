# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

Today the three live keys (payments, email, geocoding) sit in `config/app.yaml`. That file is committed to git and copied into every container image. The app reads it once at start, and each client copies its key at import. After this plan the keys live in the secret store. The app loads them into memory at startup, refuses to report ready without them, and re-reads them every 5 minutes. The keys are first rotated at each provider, and the old keys are revoked last and only once every instance is proven to use the new ones.

Two facts about today's deploys decide the order of the steps:

- Rollback means redeploying an earlier image, and those images contain the old keys. The old keys must stay valid until rolling back to such an image is blocked.
- `/healthz` returns 200 as soon as the server listens. Deploys are rolling, one pod at a time, with `maxUnavailable: 0`, so a new pod must pass the probe before an old one stops. `/healthz` must therefore wait for the keys, so a pod without them halts the rollout instead of replacing a good pod.

## Terms

- **Secret store:** the managed service that holds the keys. It encrypts them at rest with a per-environment KMS key and gives every write a new version id.
- **KMS key:** the encryption key the store uses. There is one each for `dev`, `staging` and `prod`.
- **Secret names:** `orders-api/<env>/payments_api_key`, `orders-api/<env>/email_api_key` and `orders-api/<env>/geocoding_api_key`. `<env>` is `dev`, `staging` or `prod`.
- **Version id:** the store's label for one written value. Version ids may be logged; values never are.
- **`APP_ENV`:** `prod`, `staging`, `dev` or `dev-offline`, set in the deployment manifest or by `make run`. It is not a secret.
- **Snapshot:** the in-memory map `{name: (value, version_id)}` of the current keys. It is replaced whole, never edited in place.
- **Service identity:** the account a prod pod authenticates as to the store: `orders-api-prod`.
- **Security on-call:** the only people who can write prod secrets or revoke keys at providers.
- **Rotation:** creating a new key at a provider, storing it, then revoking the old one.

Assumptions to confirm in step 6. If one is false, stop and rework the plan for that item before touching prod.

- Each provider lets us hold two active keys at once.
- A staging environment and a dev store path exist or can be created.
- Pods authenticate to the store through their service identity, with no static credential on disk or in env vars.
- Providers offer sandbox or test keys for dev.

## Rules that apply to every step

- Key values exist only in process memory. They never go on disk, into env vars, logs, exception messages, chat, tickets or files.
- No customer request may fail because of a missing or revoked key at any point.
- The 4 prod replicas all run as `orders-api-prod`. Engineers must not be able to read prod values.

---

## Part A. How the app runs

Part A describes the behaviour. It is built in one change (step 9).

### 1. Boot

- **Starts it:** process start.
- **What it does:** `config_loader.py` reads `config/app.yaml` for non-secret settings (`base_url`, timeouts, port, log level) and keeps them in `settings`. It ignores any `api_key` it finds. The three client singletons (`payments`, `email`, `geocoding`) are still built at import, but they no longer copy a key. Each client asks `secrets.get('<name>')` on every request, which is what lets a refreshed key take effect without a restart.
- **Data lives in:** the `settings` dict.
- **If it fails:** a missing or invalid YAML file crashes the process, as today.

### 2. Startup load

- **Starts it:** boot finished.
- **What it does:** the new `app/secrets.py` reads the three secrets from `orders-api/$APP_ENV/*`. An attempt succeeds only if all three are fetched and non-empty. They go into the snapshot, and each is logged by version id only, e.g. `secret loaded name=payments_api_key version=<id>`.
- **Data lives in:** the snapshot, in memory.
- **Readiness:** the HTTP server may listen early, but `/healthz` returns 503 `{"status":"starting"}` until the snapshot holds all three keys, then 200 `{"status":"ok"}`.
- **If it fails:** wait 2 seconds and retry, up to 3 retries (4 attempts, about 6 seconds). After the last failure, log the error class (not the message body) and exit non-zero, e.g. code `70`. The pod restarts and never becomes ready. In a rolling deploy the rollout halts and the old pods keep serving, so customers see nothing.

### 3. Serving requests

- **Starts it:** every outbound provider call.
- **What it does:** the client takes the current key from the snapshot and puts it in the `Authorization` header, as today. There is no store call on the request path. A request sees the old or the new snapshot, never a mix.
- **Data lives in:** the snapshot.
- **Safeguard:** HTTP debug logging, error reporting and tracing must not capture request headers. Step 9 checks this.
- **If it fails:** the snapshot is never empty after startup, so a missing key cannot happen at request time.

### 4. Refresh every 5 minutes

- **Starts it:** a timer in each instance, every 300 seconds. It starts when that pod becomes ready, so pods are staggered naturally.
- **What it does:** read each secret. If the version id differs from the one held, check the new value (non-empty, no stray whitespace), swap in a new snapshot, and log `secret refreshed name=... version=... (was ...)`.
- **Data lives in:** the snapshot, plus two metrics that carry version ids only: `secret_version_in_use{name,version}` and `secret_last_refresh_success_timestamp{name}`.
- **If it fails** (store unreachable, access denied, empty value, timeout): keep the last good value, log a warning with the secret name and error class, and retry at the next tick. The pod stays ready, because pulling pods out during a store outage would turn it into a customer outage. Alert if the last success is older than 15 minutes (3 missed cycles).
- **Known limit:** a pod that restarts while the store is down cannot start (step 2). With 4 replicas this reduces capacity but does not break pods that are already serving. A pod can also run without refreshing indefinitely, so time alone never proves a key was adopted. Step 14 requires evidence.

### 5. Local development

- **Starts it:** `make run`, which now sets `APP_ENV=dev`.
- **What it does:** loads `config/app.yaml` plus `config/app.dev.yaml` (which points `base_url` at provider sandboxes), and reads `orders-api/dev/*` with the engineer's own identity. Those are sandbox keys, not live keys, and engineers cannot read the prod path.
- **Offline option:** `APP_ENV=dev-offline` runs against local mock providers with fixed dummy keys that are not real credentials. The app rejects this mode unless `APP_ENV` is exactly `dev-offline`, so it cannot be turned on in prod.
- **If it fails:** the run exits through the same retry-then-exit path as step 2. The engineer can fall back to `dev-offline`.

---

## Part B. Rollout

Access and new keys come first, then code, then proof of refresh, then revocation. Revocation cannot be undone, so it is last.

### 6. Confirm assumptions and inventory

- **Starts it:** plan approved.
- **What it does:** nothing changes. The security on-call confirms the four assumptions above with each provider, including what the provider dashboard shows for last-used time or traffic. Engineering lists everything that uses the current keys: the 4 prod replicas, workers or cron jobs built from the same image, CI integration tests, developer laptops running `make run`, and any other service or doc holding a copy.
- **Data lives in:** a checklist in the tracking ticket, with no key values.
- **If it fails:** if a provider allows only one active key, stop for that provider, because zero-failure rotation is impossible as written. Raise it with security. An unknown consumer goes on the list and is handled in step 13.

### 7. Create store paths, encryption and access

- **Starts it:** step 6 complete.
- **What it does:** platform and security create the three KMS keys and the `orders-api/<env>/` namespaces, with no values yet. The access policy:

| Identity | Access |
|---|---|
| `orders-api-prod` | Read-only on `orders-api/prod/*`, nothing else |
| Security on-call | Write on `orders-api/prod/*` |
| Engineers | No access to prod values |
| Engineers | Read on `orders-api/dev/*` |

- **Verify before continuing:** as security on-call, write a throwaway to `orders-api/prod/_check`. Confirm `orders-api-prod` can read it, cannot write it, and cannot read outside `orders-api/prod/*`. Confirm an engineer identity is denied. Delete the throwaway.
- **Data lives in:** store policy and KMS configuration, kept as code or an exported policy in the ticket.
- **If it fails:** fix the policy and re-verify. Nothing uses the store yet, so there is no impact.

### 8. Create new keys and load the store

- **Starts it:** step 7 verified.
- **What it does:**
  1. The on-call creates a new live key at each provider. The old key stays active.
  2. The on-call tests each new key with a harmless authenticated call (read-only or zero-amount).
  3. The on-call pastes each tested key from the provider console straight into `orders-api/prod/<name>`, giving version 1.
  4. The same is done for `staging` (provider test keys) and `dev` (sandbox keys).
- **Data lives in:** the store, encrypted by the environment's KMS key.
- **Why now:** nobody uses the new keys yet and the old ones keep serving, so this is risk-free.
- **If it fails:** if creation or the test call fails, stop. A key that fails its test is never written, because a bad stored key would reach every instance within 5 minutes. A failed write is retried.

### 9. Build the app change and the CI guard

- **Starts it:** step 8 complete.
- **What it does:** one PR contains the Part A behaviour (`app/secrets.py`, per-request key reads in the three clients, the readiness gate, the refresh thread, the metrics, `config/app.dev.yaml`). It also removes every `api_key` line from `config/app.yaml`, adds the CI check, and checks that no logging or tracing path emits request headers.
- **CI check:** runs on every PR and is a required status check on `main`. It parses `config/*.yaml` and fails if an `api_key` key exists at any depth, whatever its value, even empty. As a second net it scans those files for the prefixes `pk_live_`, `ml_live_` and `geo_live_`.
- **Tests:**
  - Startup retries 3 times, 2 seconds apart, then exits non-zero.
  - `/healthz` is 503 until all three keys load.
  - A failed refresh keeps the last good value and logs a warning.
  - A new version is picked up without a restart.
  - Captured logs hold version ids and no key values.
  - The CI check fails on a deliberate PR that re-adds `api_key`.
- **Data lives in:** git. The PR does not merge until step 10 passes.
- **If it fails:** fix in review. Nothing has shipped. The previous image still has the old yaml keys, which stay valid, so redeploying it stays a safe rollback until step 13.

### 10. Staging soak

- **Starts it:** the PR image is built.
- **What it does:** deploy to staging and watch each failure path:
  - Block store access: the pod exits non-zero after 4 attempts and never becomes ready.
  - Write a new version of a staging secret: the pod logs the new version id within 5 minutes and the next request uses it.
  - Block the store after startup: warnings appear, the old value is kept, the pod stays ready.
- **Data lives in:** the staging store and pods.
- **If it fails:** fix the code and repeat. Do not go to prod until all three behaviours are seen.

### 11. Production rolling deploy

- **Starts it:** PR approved and merged to `main`. CI builds the image and the rolling deploy begins.
- **What it does:** each new pod reads the prod keys (v1) and becomes ready. Old pods keep using the old yaml keys. Both sets are valid at the providers, so a mixed fleet is fine. Pause after the first new pod is ready. Watch its provider calls for 401 or 403 responses and its payment, email and geocoding error rates. Resume only if they match the old pods.
- **Data lives in:** pod memory and the version-id metrics.
- **If it fails:**
  - A pod that cannot load keys never becomes ready, so the rollout halts with old pods serving. Fix the cause (usually IAM or a store path) and resume.
  - If the first pod shows provider auth errors, stop and redeploy the earlier image. Its old keys are still valid.
  - If a new key is bad, the on-call writes the previous good value as a new version. Instances adopt it within 5 minutes.

### 12. Prove runtime refresh in prod

- **Starts it:** all 4 replicas run the new image and no old-image pod remains, including workers and cron jobs found in step 6.
- **What it does:** the on-call writes the same value of one prod secret as a new version, which gets a new version id.
- **Data lives in:** the store holds the version. Each pod's metrics show the version in use.
- **Success:** within about 10 minutes `secret_version_in_use` shows the new id on every pod, and requests are unaffected.
- **If it fails:** investigate (IAM, refresh thread, store errors) and do not go on to revocation, which assumes refresh works. Customers are unaffected because pods keep the last good value.

### 13. Close the paths that still hold or run old keys

- **Starts it:** step 12 succeeded.
- **What it does:**
  - Pin the deploy tooling so no image built before the migration can be deployed or rolled back to.
  - Give each unknown consumer from step 6 its own migration or its own key, or explicitly accept that it breaks at revocation.
  - Tell engineers that old checkouts using the live keys will stop working at revocation. Current `make run` uses the dev store.
- **Why:** after revocation, rolling back to an old image would put a dead key into service and fail every request through it. Rollback must be impossible, not just discouraged.
- **Data lives in:** deploy tooling configuration and the ticket.
- **If it fails:** if rollback cannot be blocked, delay revocation.

### 14. Confirm adoption, then revoke the old keys

- **Starts it:** steps 12 and 13 complete.
- **Gate.** All must hold, from evidence rather than elapsed time:
  - Every running pod shows the new version id for all three keys in `secret_version_in_use`.
  - Every pod's last refresh success is newer than the last store write.
  - No pod reports a refresh warning.
  - No old-image pod exists in any deployment, worker or cron job.
  - The provider dashboard shows no recent traffic on the old key from sources we cannot account for, after a quiet period of at least 24 hours or as the on-call decides.
- **What it does:** the on-call revokes each old key at its provider, one provider at a time, with a second person present. After each, watch error rates and 401 and 403 responses for a few minutes before the next.
- **Data lives in:** provider consoles. The old values now remain only in git history and old images.
- **If it fails:** if a gate item cannot be confirmed, do not revoke. If requests fail after a revocation, create another new key, test it and write it to the store. Instances adopt it within 5 minutes. Revocation itself cannot be undone, which is why the gate comes first.

### 15. Clean up and close

- **Starts it:** all three old keys revoked.
- **What it does:**
  - Delete pre-migration images from the registry, since they embed the old keys.
  - Remove the `_check` secret and any temporary access granted during migration.
  - Run the planted-key test again: a PR that re-adds `api_key` to `config/app.yaml` must fail CI.
  - Record the migration in the runbook, including how the on-call writes a new version and how to confirm adoption from the metrics.
- **Data lives in:** git, the registry, the runbook.
- **Note:** git history is not rewritten, so the old keys stay visible there. They are dead after step 14, so the exposure is closed.
- **If it fails:** customers are unaffected. Re-run the cleanup and track it in the ticket.

---

## Open question

**Regular rotation schedule.** Security has not decided whether keys must also be rotated on a schedule after this migration, or how often. No cadence is chosen here. Rotation is now cheap: the on-call writes a new version and instances adopt it within 5 minutes with no deploy. Whatever cadence security picks can reuse steps 12 and 14 as its procedure. Security owns the decision.
