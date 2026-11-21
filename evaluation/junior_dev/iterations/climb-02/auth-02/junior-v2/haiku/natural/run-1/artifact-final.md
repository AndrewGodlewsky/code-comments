# Migrating orders-api third-party API keys to the managed secret store

## Scope and constraints

- Keys: `payments.api_key`, `email.api_key`, `geocoding.api_key`. Secret names: `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- Store paths are `orders-api/<env>/<name>`, where `<env>` is `prod` or `dev`. Every write creates a new version id.
- Identity `orders-api-prod` reads `orders-api/prod/*` and nothing else. Only the security on-call writes prod secrets. Engineers cannot read prod values.
- Key values live only in process memory: never on disk, in environment variables or in logs. Version ids may be logged.
- The leaked keys stay in git history, which is not rewritten. Every key is rotated at its provider. An old key is revoked only after every running instance is confirmed on the new key.
- No customer request may fail because of a missing or revoked key.
- After the migration, CI fails any change that puts an `api_key` into `config/*.yaml`.
- Local development works without reading prod secrets.
- Not decided: scheduled rotation. This plan sets no cadence (Open question 1).

Each rollout step says what starts it, what moves, where state lives and what happens if it fails. Who runs each step is open (Open question 9).

---

## Part A: Rollout

### A0. Inventory consumers

- **Starts:** the plan is approved.
- **Moves:** nothing. List every use of a live key: running pods, cron jobs, other services, CI jobs, and developer machines that run `make run`.
- **How:** search repos, CI config and config history for the three key names and the three provider base URLs. Ask each owner. Where the provider shows usage per key, check it.
- **Unknown consumer:** any use of a live key that is not on the list.
- **Done when:** every listed consumer has an owner who has confirmed the entry. Whether an observation window is needed is Open question 11.
- **Non-pod consumers** get no prod read from this plan. Each must stop using the live key, or be confirmed on the new key by its owner, before A7.
- **State:** a migration log of consumer names and locations. No key values.
- **If it fails:** an unknown consumer found later blocks A7 for that key until it is listed and handled. It does not block A1 to A6.

### A1. Provision the store, KMS keys and identities

- **Starts:** A0 is done.
- **Moves:** create `orders-api/dev/*` and `orders-api/prod/*`, and one KMS key per environment, all in infrastructure-as-code:
  - `orders-api-prod`: read on `orders-api/prod/*` only.
  - Security on-call: write on `orders-api/prod/*`. Remove value read if the store can split write from read.
  - Engineers: read and write on `orders-api/dev/*` only.
  - CI deploy identity: no read of prod values.
- **State:** the store and KMS keys in IaC. Key material stays in KMS.
- **If it fails:** the apply fails and nothing changes. Verify with a policy simulation: `orders-api-prod` can read `orders-api/prod/payments_api_key` and no other dev or prod path. An engineer principal gets AccessDenied on every prod path.

### A2. Dev store, and local development moves onto it

- **Starts:** A1 is done.
- **Moves:**
  - Put non-live sandbox keys in `orders-api/dev/*`. Where a provider has no sandbox key, use offline mode (R6).
  - `make run` sets `APP_ENV=dev` and reads dev secrets with the developer's own identity.
  - Non-secret config gets per-environment base URLs, so dev uses sandbox URLs.
- **State:** the dev store, under the dev KMS key. After this step `make run` uses no live key. Earlier clones still hold old keys in git history; revoking them in A7 is what makes those keys useless.
- **If it fails:** a developer without dev access gets a clear startup error (non-zero exit) or uses `make run --offline`. Prod is unaffected. A5 must not merge until this step is verified.

### A3. Issue new live keys at each provider

- **Starts:** A2 is done and the security on-call approves the rotation.
- **Moves:** issue a new key at each of the payments, email and geocoding providers. Old keys stay valid. New keys go only to the security on-call through the approved channel, never into chat, tickets, code or commits.
- **State:** the provider consoles. After A4, the store.
- **If it fails:** if a provider cannot issue a key, stop. Prod is unchanged and the old keys still serve traffic.

### A4. Write the new keys to the prod store

- **Starts:** A3 is done. The security on-call performs the writes.
- **Before each write:** if the provider offers a read-only auth check, validate the new key with it. If the check fails, do not write (Open question 4).
- **Moves:** write `orders-api/prod/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key`. Each write creates a version id. Record the ids in the migration log, never the values. Record any later write too.
- **State:** the prod store, under the prod KMS key. Running pods hold the old keys in memory, and the old image does not read the store, so traffic does not change yet.
- **If it fails:** a failed write changes nothing. Retry it. The old keys still serve traffic.

### A5. Ship the new image

- **Starts:** A4 is done, the code change is reviewed and merged to `main`, and CI builds the image.
- **Moves:**
  - The new image loads the three secrets at startup (R1). Its readiness probe waits for that load (R4).
  - `config/app.yaml` drops its `api_key` lines and keeps the non-secret values.
  - The CI guard lands in the same change. A CI job scans `config/*.yaml` and fails if any `api_key` key is present, with any value. A test change that adds one must fail the job. An optional pre-commit hook runs the same check locally. The guard is verified before this change merges.
  - The rolling deploy keeps `maxUnavailable: 0`.
- **State:** during the rollout, old pods hold old keys and new pods hold new keys. Both are valid, because nothing is revoked yet.
- **Gate:** continue only while the 401/403 rate on new pods stays at or below the rate on old pods. Watch it per pod.
- **If it fails:**
  - A new pod that cannot reach the store retries (R1), exits non-zero and never becomes ready. The rollout halts and the old pods keep serving.
  - A new pod that holds a key the provider rejects still becomes ready, because readiness checks loading, not validity. The gate halts the rollout. Some requests can fail before the halt, and only the A4 pre-write check guards earlier (Open question 4). Roll back by redeploying the previous image. That image still has valid old keys, which is why revocation waits for A7.
  - A false positive in the CI guard blocks a merge. Fix the rule. Do not disable it.

### A6. Confirm every instance is on the new keys

- **Starts:** the rollout is complete, with 4 pods on the new image.
- **Moves:** nothing. This is a read-only check, run as a saved log query plus a script that looks up the latest store version ids. Do not check pod by pod by hand. Log lines carry only names and version ids (R5). The security on-call runs the store-side lookup and the comparison. Whether engineers can see version ids is Open question 10.
- **Passes only when all of these hold:**
  - For each pod and each secret, the latest `secret loaded` or `secret rotated` line shows the same version id as the latest version in the store at check time. Compare with the store, not only with the A4 ids, because a later write changes the target.
  - Every A0 consumer is confirmed on the new key or stopped by its owner (Open question 11).
  - At least one refresh interval (5 minutes) plus a margin has passed since the last store write. This lets any pod that loaded an older version run its refresher once after that write. A pod that started after the last write needs no wait.
  - No old-image pod remains in the cluster.
  - Provider error rates are normal for all three providers.
- **State:** the central log service, 30-day retention. It is the confirmation record.
- **If it fails:** if a pod still shows an old version after one more refresh interval, investigate that pod's refresher (R2). Do not revoke. The old key still works, so customers are not affected, but revocation is blocked.

### A7. Revoke the old keys, one provider at a time

- **Starts:** A6 passes for that provider's key, and A0 shows no consumer still on the old key.
- **Moves:** revoke the old payments key first. Watch error rates for 15 minutes. Then email, then geocoding, with the same gate each time.
- **State:** the provider console. Revocation cannot be undone.
- **If it fails:** if errors rise, first look for a consumer missed in A0 that still uses the old key. The recovery path is the new key, already in the store and in the running pods. Do not re-enable the old key. Pause the next provider until the cause is known.

### A8. Block rollback to pre-migration images

- **Starts:** before the first revocation (A7).
- **Moves:** the deploy pipeline refuses any image built from a commit before the migration commit. Each image must record its build commit. The deploy tool and tag format are Open question 3. This plan defines no override.
- **State:** the deploy pipeline configuration.
- **If it fails:** without this, a rollback restores a revoked key. A8 gates A7.

### A9. Cleanup and audit

- **Starts:** A7 is done for all three providers.
- **Moves:**
  - Scan the central logs for the old key values across the 30-day window. Any hit is handled as an incident.
  - Decide what to do with old images that contain the old keys (Open question 3).
  - Record revocation times and version ids in the migration log.
- **State:** the migration log and the log-scan results.
- **If it fails:** a log hit found after revocation is harmless, because the key is already revoked. Record it and keep the scan as evidence.

---

## Part B: How the app reads keys at runtime

Shared behavior: one in-process `SecretCache` maps `name -> (value, version_id, fetched_at)`. Each entry is swapped as a whole, so readers always see one consistent value. The cache is the only place values live. Config holds no secrets. A `ready` flag is set once R1 has finished, or once offline mode is on (R6).

### R1. Startup load (blocking, before ready)

- **Starts:** process start. It is an explicit call in `main`, not an import-time side effect of the config loader.
- **Moves:** for each of the three names, read the latest version of `orders-api/<APP_ENV>/<name>`. `APP_ENV` is `prod` in the cluster and `dev` locally. Store calls authenticate with the pod's service identity, which the platform provides, so no store credential sits in an environment variable (Open question 10). Each store call has a bounded timeout. On success, log `secret loaded name=<name> version=<id> pod=<pod>` once per secret.
- **Retry:** one attempt, then 3 retries, 2 seconds apart. That is 4 attempts in total (Open question 2). "Not found" is fatal at once and is not retried.
- **State:** memory only.
- **If it fails:** after the retries, log an error that names the failing secrets and the error types (no values), then exit non-zero. The pod never becomes ready and the rollout halts (A5).

### R2. Periodic refresh (background, every 5 minutes)

- **Starts:** a background task every 5 minutes after the last load. A small random jitter keeps the 4 replicas from calling the store at the same moment. It runs independently of request handling.
- **Moves:** read the latest version of each secret. If the version id is unchanged, do nothing. If it changed, check that the value is non-empty and has no whitespace, swap the cache entry, and log `secret rotated name=<name> version=<id> pod=<pod>`.
- **Role:** handles later rotations and provides the margin in A6. The A5 cutover does not need it, because new pods load the latest version at startup.
- **State:** memory only.
- **If it fails:** a timeout, auth error, not-found error or failed check keeps the last good value. Log a WARNING with the secret name, the last good version id and the error type, never the value. The next run tries again. A separate alert fires when a secret's `fetched_at` is older than the threshold (Open question 8).

### R3. Request path (provider calls)

- **Starts:** each customer request that calls a provider.
- **Moves:** the client reads the current value from the cache at call time, for example `cache.get('payments_api_key')`. It does not copy the key in its constructor, as it does today, because that would ignore refreshes. The store is never called on the request path.
- **State:** memory only.
- **If it fails:**
  - A store outage does not affect requests, because the last good key stays in memory.
  - If the provider rejects the key (401 or 403), the request fails with the provider's error, as it does today. It is not retried with another key. Log a WARNING with the version id and the provider error code. Trigger one out-of-band refresh, rate-limited to once per 60 seconds, so later requests pick up a rotation sooner. This refresh does not help the failed request.
  - After A7 has started, a 401 means a pod holds a revoked key. Treat it as an incident. During A5, 401s on new pods are handled by the A5 gate.

### R4. Readiness and liveness

- **Starts:** kubelet probes.
- **Moves:**
  - Readiness returns 200 only when the `ready` flag is set, meaning R1 has loaded all three secrets (or offline mode is on, R6). This replaces today's "200 as soon as the server listens" and is what makes the rollout safe.
  - Readiness does not go false when a later refresh fails (R2). Otherwise a store outage would drop capacity across all 4 replicas.
  - Liveness returns 200 while the process is running. It does not depend on the store, so a store outage does not restart pods.
- **State:** the `ready` flag, in memory only.
- **If it fails:** if readiness still meant "listening", a new pod with no keys would take traffic and break customers. This change deploys with A5. In A5, "passes readiness" means the probe returns 200, which happens only after R1 succeeds, so a pod that cannot load its keys never receives traffic.

### R5. Logging and redaction

- **Starts:** any log call, including HTTP client debug logs.
- **Moves:** logs carry the secret name and version id only. The secret value type's `__repr__` and `__str__` return `<redacted>`. Exceptions and HTTP debug output never include the Authorization header or the request body. Header dumps are off in the HTTP client's logging. The log pipeline scrubs live key prefixes as a backstop.
- **State:** the central log service, 30-day retention.
- **If it fails:** a key value found in logs is a new leak. Rotate the key at its provider using A3 to A7.

### R6. Local development

- **Starts:** a developer runs `make run` (which sets `APP_ENV=dev`) or `make run --offline`.
- **`make run`:** R1 runs against `orders-api/dev/*` with the developer's own identity. The A1 policy gives engineers read and write on dev only, so they reach dev without prod access. The values are sandbox keys. Base URLs come from the non-secret per-environment config.
- **`make run --offline`:** skips R1 entirely, with no store call. The flag, not the environment, selects this mode. Each provider client uses a local stub server as its base URL and a fixed dummy key held in memory. `ready` is set at once.
- **State:** memory only. No key file is written on a developer machine.
- **If it fails:** no dev access gives a clear startup error and a non-zero exit. Offline mode is the fallback. Prod is never involved.

---

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must be rotated on a schedule, or how often. This plan sets no cadence. A recurring rotation would reuse A3 to A7 and needs its own plan and decision.
2. **Retry count.** The brief says "retry 3 times". This plan reads that as 3 retries after the first attempt (4 attempts in total). If it means 3 attempts in total, change R1 and the A5 timing.
3. **Rollback and old images.** Once a key is revoked (A7), pre-migration images that contain it cannot be used, and A8 blocks them. Confirm this is acceptable, or decide how a rollback gets a working key. Also decide the deploy tool and the image-tag format that records the build commit (A8 needs both). Decide whether to delete old images from the registry (which removes the rollback target) or keep them behind A8.
4. **Pre-write key check.** Confirm whether each provider offers a read-only auth check for the A4 validation. Until this is known, the A5 gate is the only guard against a bad key.
5. **Version id reporting.** The A6 check uses log lines (R1, R2). Decide whether a metric is also wanted.
6. **Emergency revocation.** Revocation is allowed only after confirmation. If a key is abused before the rollout finishes, security needs a documented exception path. This plan does not define one.
7. **Staging.** The brief names only dev and prod. If a staging environment exists, insert it before A4 with the same gates.
8. **Stale-secret alert threshold.** Ops must choose the threshold for the R2 staleness alert.
9. **Owners.** Name owners for A0, A1, A2, A5 (merge and deploy), A6 and A7, and who approves the A5 merge, before A0 starts. The brief fixes only that the security on-call performs the A4 writes.
10. **Store product and pod identity.** Name the store product, and how a pod receives its service identity without an environment credential. Confirm pods run as `orders-api-prod` (from `deploy.md`). Also confirm whether a non-engineer can see version ids without reading values (A6). Confirm both before A1 and R1.
11. **Non-pod consumers and observation window.** A6 covers only pods. Decide how each non-pod consumer (cron jobs, other services, CI jobs, developer machines) is confirmed on the new key or stopped before A7. Decide whether any of them needs its own identity, since this plan gives them no prod read. Decide whether A0 needs a watch window on provider usage before it is final.