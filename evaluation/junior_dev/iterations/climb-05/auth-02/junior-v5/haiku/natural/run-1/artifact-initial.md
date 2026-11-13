# Plan: move orders-api third-party keys into the managed secret store

## Scope and fixed points

- Keys covered: payments, email and geocoding. Store names: `orders-api/<env>/payments_api_key`, `orders-api/<env>/email_api_key`, `orders-api/<env>/geocoding_api_key`.
- The current keys are treated as leaked. They are not rewritten out of git history. Each one is rotated at its provider, and an old key is revoked only after the gate in Step 10 passes.
- Key values never appear in this plan, tickets, chat, logs, environment variables or disk. Logging store version ids is allowed.
- Roles:
  - **Security on-call**: the only writer of `orders-api/prod/*`. Generates new provider keys and writes them to the store in one step, so no engineer sees a value. Also performs revocations.
  - **`orders-api-prod`**: read-only on `orders-api/prod/*`. No other access.
  - **Engineers (dev identity, `orders-api-dev`)**: read on `orders-api/dev/*` only. No prod read.
  - **CI identity**: no secret read. It runs the config guard only.
- Open questions are collected at the end. The secret rotation cadence is not decided and is not set in this plan.

---

## Part A: Rollout

### Step 1: Inventory every consumer of the old keys

- **Starts when:** the change ticket is approved.
- **What moves where:** nothing moves. Each team that uses the same provider accounts is asked to list where it uses the old keys: other services, scripts, jobs, dashboards, partner integrations.
- **State lives in:** the change ticket.
- **If it fails:** if a consumer cannot be found or cannot be moved, revocation in Step 10 is blocked. Its owner must move it first or accept an outage at revocation.

### Step 2: Create store layout, KMS keys and access

- **Starts when:** Step 1 is complete.
- **What moves where:** per-environment KMS keys (dev, staging, prod) are created. Paths `orders-api/dev/*`, `orders-api/staging/*` and `orders-api/prod/*` are created. Policies:
  - `orders-api-prod`: read on `orders-api/prod/*` only.
  - Security on-call group: write on `orders-api/prod/*`.
  - Engineer group: read on `orders-api/dev/*` only. No prod read.
- **State lives in:** the secret store and KMS. The app is not involved yet.
- **If it fails:** nothing has been deployed, so production is unchanged. Fix the policy and re-apply. Verify with test identities that `orders-api-prod` can read `orders-api/prod/*` and cannot read or write any other prefix. Verify that engineers cannot read prod.

### Step 3: Provision dev and staging values from provider test keys

- **Starts when:** Step 2 is verified.
- **What moves where:** provider sandbox or test keys are created and written to `orders-api/dev/*` and `orders-api/staging/*`. Live keys never enter dev or staging.
- **State lives in:** the store, dev and staging paths.
- **If it fails:** only dev and staging are affected. Retry the write. Local development is unavailable until it succeeds, but production is unaffected.

### Step 4: Generate new prod keys and write them to the store

- **Starts when:** Step 3 is complete and the app-side change in Part B is ready for release, though not yet deployed.
- **What moves where:** security on-call creates a new live key at each provider. The old keys stay valid. The new value goes straight into `orders-api/prod/<name>` as a new version. Version ids are recorded in the change ticket. The values are not.
- **State lives in:** the provider (new key) and the store (new version, encrypted under the prod KMS key).
- **If it fails:** the old keys still work and nothing customer-facing has changed. If a provider cannot issue a second active key, stop here. See open question 1.

### Step 5: Verify prod read access with the production identity

- **Starts when:** Step 4 writes complete.
- **What moves where:** a one-off check job runs as `orders-api-prod`. It reads the three latest versions and prints only version ids and value lengths, never values.
- **State lives in:** job output (ids and lengths only).
- **If it fails:** a read failure here means the policy or the identity is wrong. Fix it before any deploy. Do not proceed to Step 6.

### Step 6: Merge the code change and enforce the CI guard

- **Starts when:** Step 5 passes. The merge goes to `main` through normal review.
- **What moves where:**
  - `config/app.yaml` keeps non-secret settings (base URLs, timeouts, `from_address`, app name, port, log level) and loses all three `api_key` lines.
  - The new loader and clients from Part B are included.
  - `/healthz` changes to report ready only after keys are loaded (Part B, Step 13).
  - `deploy.md` is updated to describe the new readiness meaning.
  - CI gains a guard that fails any change adding an `api_key` line to `config/app.yaml`. It is enforced in this same change because the keys are out in this same change.
- **State lives in:** git (`main`) and the built image, which contains no keys.
- **If it fails:** if the guard fails, the merge is blocked and nothing changes in production. If the build fails, nothing is released.

### Step 7: Canary one pod on the new image

- **Starts when:** Step 6's image is built.
- **What moves where:** the rolling deploy replaces one pod with the new image. The new pod loads the three keys from the store before it reports ready (Part B, Step 12).
- **State lives in:** the new pod's memory. The store holds the keys.
- **If it fails:**
  - If the store is unreachable or the identity is denied, the new pod retries 3 times, 2 seconds apart, then exits non-zero. It never becomes ready. With `maxUnavailable: 0` the rollout halts and the old pods keep serving on the old keys, which are still valid. Customer impact is none.
  - Investigate the cause, fix it, then redeploy.

### Step 8: Roll the remaining pods

- **Starts when:** the canary pod is ready and its logs show the three version ids from Step 4.
- **What moves where:** pods are replaced one at a time. The fleet is mixed for a while: old pods use the old keys, new pods use the new keys. Both are valid, which is why revocation waits.
- **State lives in:** pod memory for each pod.
- **If it fails:** the rollout halts at the first pod that cannot become ready. Old pods keep serving. Diagnose, fix, redeploy. Do not revoke anything while the fleet is mixed.

### Step 9: Confirm every instance uses the new versions

- **Starts when:** all replicas run the new image. Wait at least 10 minutes after the last replacement, which covers one full 5-minute refresh cycle plus jitter.
- **What moves where:** nothing moves. Check three signals:
  - Each replica reports the new version ids for all three names (startup and refresh logs, and the `secret_version_info` metric from Part B, Step 16).
  - No replica runs an old image.
  - The provider dashboards show traffic on the new keys, and traffic on the old keys has dropped to zero for the agreed window. If a provider does not expose per-key usage, see open question 4.
- **State lives in:** logs, metrics and provider dashboards.
- **If it fails:** a replica still on an old version or with no version reported means the gate is not passed. Do not revoke. Find out why the replica did not refresh, for example a stuck refresh thread or a failing store read.

### Step 10: Block pre-migration images, then revoke the old keys

- **Starts when:** Step 9 passes and the soak period agreed by the on-call owner (open question 3) has elapsed.
- **What moves where:**
  - First, the deploy policy denies any image built before Step 6. This must be in place before revocation, because a rollback to a pre-migration image would restore the revoked key from the image's copy of `config/app.yaml`.
  - Then security on-call revokes each old key at its provider, one key at a time. Watch error rates after each revocation.
- **State lives in:** the registry policy and the provider consoles. The store already holds only the new versions.
- **If it fails:**
  - If errors appear after a revocation, the cause is an unmigrated consumer from Step 1, not the migrated fleet. Do not re-enable the old key, since the provider's revocation is final. Issue a new key at the provider and write it as a new store version. Running pods pick it up within 5 minutes.
  - If the registry policy cannot be applied, do not revoke. Revocation without the block creates a rollback path to revoked keys.

### Step 11: Clean up and verify

- **Starts when:** Step 10 completes.
- **What moves where:**
  - Old images that contain the old keys are removed from the registry, or kept only under the deny policy.
  - Search the central log service (30-day retention) for the new key prefixes. Any hit is a logging defect. Fix it and treat it as an exposure.
  - Update `deploy.md`: readiness semantics, the rollback rule (rollback targets are post-Step-6 images only), and the local-dev setup.
  - Record the revocation and version ids in the change ticket.
- **State lives in:** the registry, logs, docs and the ticket.
- **If it fails:** log search failures are an observability gap, not a customer outage. Re-run the search later and record the gap.

### Rollback summary

| Point in rollout | Rollback target | Why |
|---|---|---|
| Steps 4 to 9 | Previous image (pre-migration) is valid | Old keys are still active |
| Steps 6 to 9 | Post-Step-6 images are valid | They read the store |
| After Step 10 | Post-Step-6 images only | Pre-migration images hold revoked keys |

---

## Part B: How the app reads keys at runtime

### Step 12: Startup load of required secrets

- **Starts when:** the process starts. Nothing happens at import time.
- **What moves where:** the config loader reads only `config/app.yaml` (non-secret settings). A `SecretStore` then fetches the latest version of each of the three names, using the pod's `orders-api-prod` identity. No credentials appear in environment variables.
- **Retry:** up to 3 retries, 2 seconds apart, after the first attempt. This plan reads "retry 3 times" that way. See open question 2.
- **Validation:** a fetched value must be non-empty and contain no whitespace. Otherwise it counts as a failed read.
- **State lives in:** process memory only, as `{name: (value, version_id, fetched_at)}`.
- **If it fails:** if any of the three names is still missing after the retries, the process logs an error with the name and the error class (no value) and exits with a non-zero code. It never starts serving with a partial set of keys.

### Step 13: Readiness and liveness

- **Starts when:** Step 12 completes.
- **What moves where:** the HTTP server starts. `GET /healthz` returns 200 only after the startup load has set the ready flag. Before that it returns 503.
- **Readiness does not depend on refresh health.** A store outage after startup does not make pods unready.
- **Liveness, if a liveness probe exists, stays listening-only.** A store outage must not restart pods.
- **State lives in:** a process-local flag.
- **If it fails:** a pod that never becomes ready is never added to service, and with `maxUnavailable: 0` the rollout halts while old pods serve. This is the change from today's behavior, where `/healthz` returns ok as soon as the listener is up. `deploy.md` must say so.

### Step 14: Clients read through the store on each use

- **Starts when:** a request needs a provider call.
- **What moves where:** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key into `self._key` at construction. Each call fetches the current value from `SecretStore` under a lock and builds the `Authorization` header. The clients are created without network access at import time, so the key is read after startup, not during import.
- **State lives in:** `SecretStore` memory.
- **If it fails:** after Step 12 the value is always present, since startup refuses to run without all three. A missing entry at request time means a programming error. It fails that request with a clear internal error and logs it. Never substitute an empty value.

### Step 15: Background refresh every 5 minutes

- **Starts when:** the ready flag is set. A timer thread runs with about ±30 seconds of jitter so the four replicas do not read the store at the same moment.
- **What moves where:** for each name, the store is read for its latest version.
  - If the version id is unchanged, do nothing.
  - If it changed and the value validates, swap the entry atomically under the lock. Log `secret rotated name=... version=...` with no value.
  - If the read fails (store error, timeout, denied, or an invalid value), keep the last good value, log a warning with the name and the error class, and try again at the next cycle.
- **Staleness check:** if no refresh has succeeded for more than 15 minutes, emit a warning and increment a metric. A dead timer thread must not go unnoticed, because the app would keep serving stale keys silently.
- **State lives in:** `SecretStore` memory.
- **If it fails:** the app keeps serving on the last good key. Customers are unaffected unless the old key was revoked at the provider while the pod still held it. Step 10's gate exists to prevent that. A provider 401 on a migrated pod is logged with the key name and version id and counted, so it shows up quickly.

### Step 16: Logging and metrics

- **Starts when:** any load, rotation, failure or request.
- **What moves where:** logs and metrics carry names and version ids only. The `secret_version_info{name, version}` metric is exported so Step 9 can check replicas. HTTP client logging must not record request headers. A log redaction filter removes anything that matches a key prefix, as a safety net and not as the main control.
- **State lives in:** the central log service (30-day retention) and the metrics system.
- **If it fails:** if the metric is missing, Step 9 falls back to log lines. Do not treat a missing metric as a passed gate.

### Step 17: Shutdown and crash handling

- **Starts when:** SIGTERM, or a crash.
- **What moves where:** nothing is written to disk and nothing needs flushing. Core dumps are disabled for the container, since a dump would capture key values from memory.
- **State lives in:** memory, which is released on exit.
- **If it fails:** if core dumps cannot be disabled, treat that as a blocker for Step 6. A dump of a running process would expose live keys.

### Step 18: Local development

- **Starts when:** a developer runs `make run` with `APP_ENV=dev`.
- **What moves where:** the developer's SSO identity (`orders-api-dev`) reads `orders-api/dev/*`, which holds provider test keys from Step 3. No prod identity is available to engineers, so local runs cannot read prod.
- **State lives in:** `SecretStore` memory on the developer's machine.
- **If it fails:** a developer without dev access sees a clear startup error and the process exits. There is no fallback to committed keys, to a local key file or to prod. If a developer needs offline work, use recorded responses or stubs, not real keys.

---

## Open questions

1. **Provider support for overlapping keys.** The zero-failure requirement assumes each provider allows two active keys at once, so that the mixed fleet works. This must be verified per provider before Step 4. If a provider allows only one key, the plan needs a different overlap mechanism, and this plan does not cover it.
2. **Retry count.** The brief says "retry 3 times". This plan reads that as one initial attempt plus 3 retries, about 6 seconds in total. Confirm whether 3 total attempts was meant.
3. **Soak period before revocation.** The brief does not set one. Security and the service owner must agree on it. Step 10 cannot run until they do.
4. **Per-key usage visibility.** Step 9 needs each provider to show traffic per key, so the old key's traffic can be seen going to zero. If a provider cannot show this, Step 9 needs another signal.
5. **Key rotation cadence after migration.** Not decided. Security has not chosen whether keys must rotate on a schedule or how often. This plan does not pick one. The 5-minute refresh interval is a read interval, not a rotation cadence, and is not a substitute for a rotation policy.
6. **Pre-migration images in the registry.** The plan blocks them from deployment at Step 10. Whether they are also deleted from the registry, and when, is not decided.
7. **Store and provider product details.** The plan assumes the store returns a version id on each read, supports an exact "latest" read, and emits access audit logs. If any of these is missing, Steps 9 and 15 need adjustment.
8. **Whether a liveness probe exists.** Part B, Step 13 assumes one may exist and that it must not depend on the store.