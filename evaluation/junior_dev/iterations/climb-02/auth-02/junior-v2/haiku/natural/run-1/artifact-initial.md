# Migrating orders-api third-party API keys to the managed secret store

## Scope and fixed constraints

- Keys in scope: `payments.api_key`, `email.api_key`, `geocoding.api_key`. Secret names: `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- Store paths: `orders-api/prod/<name>` and `orders-api/dev/<name>`. Each write creates a new version id.
- The prod identity `orders-api-prod` has read-only access to `orders-api/prod/*`. Only the security on-call writes prod secrets. Engineers have no prod read access.
- Key values exist only in process memory. They never go to disk, environment variables or logs. Version ids may be logged.
- The leaked keys stay in git history. History is not rewritten. Every key is rotated at its provider. An old key is revoked only after every running instance is confirmed on the new key.
- No customer request may fail because of a missing or revoked key.
- After the migration, CI fails any change that puts an `api_key` back into `config/app.yaml`.
- Local development must work without reading prod secrets.

Not decided: whether and how often keys must be rotated on a schedule after this migration. This plan sets no cadence. See Open question 1.

---

## Part A: Rollout

### A0. Inventory every consumer of the current keys

- **Starts:** the plan is approved.
- **Moves:** nothing changes. List every place the live keys are used: the running `orders-api` pods, cron jobs, other services, CI jobs, and developer machines that run `make run`, which loads the live keys today.
- **State:** a migration log of consumers. It records names and locations only, never key values.
- **If it fails:** an unknown consumer is found later and breaks when a key is revoked (step A7). Treat any unknown consumer as a blocker for step A7, not for the earlier steps.

### A1. Provision the store, KMS keys and identities

- **Starts:** A0 is complete.
- **Moves:** create the `orders-api/dev/*` and `orders-api/prod/*` namespaces. Create one KMS key per environment. Set IAM policy as follows:
  - `orders-api-prod`: read on `orders-api/prod/*` only.
  - Security on-call: write on `orders-api/prod/*`. Write access should not include read of values, if the store allows that split.
  - Engineers: read and write on `orders-api/dev/*` only, with no prod read.
  - The CI deploy identity: no read on prod values.
  - Policy is defined in infrastructure-as-code.
- **State:** the store and KMS keys, in their IaC definitions. The key material stays in KMS.
- **If it fails:** the IaC apply fails and nothing changes. No app or customer impact. Verify with a policy simulation that `orders-api-prod` can read `orders-api/prod/payments_api_key` and cannot read `orders-api/dev/*` or other prod paths, and that an engineer principal gets AccessDenied on any prod path.

### A2. Put dev-only keys in the dev store and move local dev onto them

- **Starts:** A1 is complete.
- **Moves:**
  - Put non-live sandbox keys from each provider into `orders-api/dev/*`. Where a provider has no sandbox key, use the offline stub in step R6.
  - Change `make run` so it sets `APP_ENV=dev` and reads `orders-api/dev/*` using the developer's own identity (see R6).
  - Give the non-secret config a per-environment base URL, so dev uses sandbox base URLs.
- **State:** the dev store (encrypted with the dev KMS key). No live key is on any developer machine after this step.
- **If it fails:** a developer without dev access gets a clear startup error (exit non-zero) or uses the offline stub mode. Prod is unaffected. Step A5 must not merge until this step is verified, because the new `make run` must work once `api_key` is removed from the config.

### A3. Issue new live keys at each provider

- **Starts:** A2 is complete and the security on-call approves the rotation.
- **Moves:** issue a new key at the payments, email and geocoding providers. Each old key stays valid. The new keys go only to the security on-call through their approved channel. They are not pasted into chat, tickets, code or commits.
- **State:** the provider console. The new key exists only there and in the next step's store.
- **If it fails:** if the provider cannot issue a key, stop. Nothing in prod has changed and the old keys still serve traffic.

### A4. Write the new keys to the prod store

- **Starts:** A3 is complete. The security on-call performs the write.
- **Moves:** write each new key to `orders-api/prod/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key`. Each write creates a version id. The on-call records the version ids in the migration log, never the values.
- **State:** the prod store, encrypted with the prod KMS key. The running pods still hold the old keys in memory, and the old image does not read the store, so nothing changes for traffic yet.
- **If it fails:** a failed write changes nothing. Retry it. The old keys still serve traffic.

### A5. Ship the new image: read keys from the store and remove them from config

- **Starts:** A4 is complete and the code change has been reviewed and merged to `main`. CI builds the image.
- **Moves:**
  - The new image reads the three secrets from the store at startup, as described in R1–R4.
  - `config/app.yaml` drops its `api_key` lines and keeps the non-secret values.
  - The CI guard from step A9 is added in the same change, so the file cannot regress.
  - The rolling deploy keeps `maxUnavailable: 0`. Each new pod loads its keys and passes the new readiness probe before an old pod stops.
- **State:** during the rollout, old pods hold the old keys in memory and new pods hold the new keys. Both are valid, because the old keys are not revoked yet.
- **If it fails:**
  - A new pod that cannot reach the store retries, exits non-zero, never becomes ready, and the rollout halts. The old pods keep serving.
  - A new pod that loads a wrong key still becomes ready, because readiness checks loading, not validity against the provider. Watch the provider error rate during the rollout. Roll back by redeploying the previous image. That image still has valid old keys, which is why revocation waits until A7.

### A6. Confirm every instance is on the new keys

- **Starts:** the rollout is complete, with 4 pods on the new image.
- **Moves:** nothing. This is a read-only check.
  - Each pod's logged version ids for all three secrets match the version ids written in A4.
  - At least one refresh interval (5 minutes), plus a margin, has passed since the last A4 write.
  - No old-image pod remains in the cluster.
  - Provider error rates are normal for all three providers.
- **State:** the central log service, with 30-day retention. It is the only confirmation record.
- **If it fails:** if a pod still reports an old version id, wait one more refresh interval. If it is still old, investigate that pod's refresher (R2). Do not revoke. The old key still works, so customers are not affected, but revocation is blocked.

### A7. Revoke the old keys, one provider at a time

- **Starts:** A6 passes for that provider's key, and A0 shows no unknown consumer of that old key.
- **Moves:** revoke the old payments key first. Watch error rates for 15 minutes. Then do email, then geocoding, with the same gate each time.
- **State:** the provider console. Revocation cannot be undone.
- **If it fails:** if errors rise after a revocation, look first for a consumer missed in A0 that still uses the old key. The recovery path is the new key already in the store and in the running pods. Do not re-enable the old key. Pause the next provider's revocation until the cause is known.

### A8. Block rollback to pre-migration images

- **Starts:** A7 has revoked at least one key.
- **Moves:** deploy tooling refuses any image tag built before the migration commit. This keeps a rollback from restoring a revoked key. See Open question 3.
- **State:** the deploy pipeline configuration.
- **If it fails:** if this is not in place, a rollback to an old image breaks customers. This is a gate for A7 and must be done before the first revocation.

### A9. CI guard against `api_key` in config

- **Starts:** added in the same change as A5. It is verified before A5 merges.
- **Moves:** a CI job scans `config/*.yaml` and fails if any `api_key` key is present, with any value. A test change that adds one must fail the job. Optionally, a pre-commit hook gives the same check locally.
- **State:** CI configuration.
- **If it fails:** a false positive blocks a merge. Fix the rule. Do not disable it.

### A10. Final cleanup and audit

- **Starts:** A7 is complete for all three providers.
- **Moves:**
  - Scan the central logs for the old key values, for the 30-day retention window, to find any past leak. Any hit is handled as an incident.
  - Decide what to do with old container images that contain the old keys. See Open question 4.
  - Record the revocation times and version ids in the migration log.
- **State:** the migration log and the log scan results.
- **If it fails:** a log hit found after revocation is already harmless, since the old key is revoked. Record it and keep the scan as evidence.

---

## Part B: How the app reads keys at runtime

Shared behavior: one in-process `SecretCache` holds `{name: (value, version_id, fetched_at)}`. Each entry is swapped as a whole, so readers always see one consistent value. The cache is the only place values live. Config holds no secrets.

### R1. Startup load (blocking, before ready)

- **Starts:** process start, before the HTTP server reports ready. It is an explicit call in `main`, not an import-time side effect in the config loader.
- **Moves:** for each of the three names, read `orders-api/<APP_ENV>/<name>` from the store, latest version. `APP_ENV` is `prod` in the cluster and `dev` locally. Store auth uses the pod's workload identity, so no store credential is in an environment variable. Each store call has a bounded timeout.
- **Retry:** one attempt, then 3 retries, 2 seconds apart. That is 4 attempts in total. See Open question 2. A secret that is "not found" is fatal at once and is not retried.
- **State:** memory only.
- **If it fails:** after the retries, log an error that names the failing secrets and the error type (no values), then exit non-zero. The pod never becomes ready, and the rollout halts (A5).

### R2. Periodic refresh (background, every 5 minutes)

- **Starts:** a background task, every 5 minutes after the last load. Add a small random jitter so the 4 replicas do not call the store at the same moment. It is independent of request handling.
- **Moves:** read the latest version of each secret. If the version id is unchanged, do nothing. If it changed, check the value is non-empty and has no whitespace. Then swap the entry in the cache and log `secret rotated name=<name> version=<id>`.
- **State:** memory only.
- **If it fails:** a timeout, auth error, not-found error or failed check keeps the last good value. Log a WARNING with the secret name, the last good version id and the error type, never the value. The next run tries again. A separate alert fires when a secret's `fetched_at` is older than a threshold chosen by ops. The threshold is not set here.

### R3. Request path (provider calls)

- **Starts:** each customer request that calls a provider.
- **Moves:** the client reads the current value from the cache at call time, for example `cache.get('payments_api_key')`. It does not copy the key in its constructor, which is the current behavior and would ignore refreshes. The store is never called on the request path.
- **State:** memory only.
- **If it fails:** a store outage does not affect requests, because the last good key is still in memory. If the provider rejects the key (401 or 403), log a WARNING with the version id and the provider error code. Also trigger one out-of-band refresh, rate-limited to once per 60 seconds, so a rotation is picked up sooner. Do not retry with any other key.

### R4. Readiness and liveness

- **Starts:** kubelet probes.
- **Moves:** change `GET /healthz`:
  - Readiness returns 200 only after R1 has loaded all three secrets. This replaces today's "200 as soon as the server listens". It is what makes the rollout safe.
  - Liveness returns 200 while the process is running and does not depend on the store, so a store outage does not restart pods.
  - Readiness does not go false when a later refresh fails (R2). Otherwise a store outage would drop capacity across all 4 replicas.
- **State:** none.
- **If it fails:** if readiness were still "listening", a new pod with no keys would take traffic, which breaks customers. The readiness change must be deployed with A5.

### R5. Logging and redaction

- **Starts:** any log call, including HTTP client debug logs.
- **Moves:** logs carry the secret name and the version id only. The secret value type has a `__repr__` and `__str__` that return `<redacted>`. Exceptions and HTTP debug output must not include the Authorization header or the request body. Turn off header dumps in the HTTP client's logging. The log pipeline gets a pattern scrub for the live key prefixes as a backstop.
- **State:** the central log service, 30-day retention.
- **If it fails:** a key value found in logs is treated as a new leak. The key is rotated at the provider using the same A3–A7 steps.

### R6. Local development

- **Starts:** a developer runs `make run`, which sets `APP_ENV=dev`.
- **Moves:** R1 runs against `orders-api/dev/*` using the developer's own identity, which can read dev only. The values are sandbox keys. No prod path is reachable from a developer identity. Base URLs come from the non-secret per-environment config.
- **Offline mode:** if the developer has no dev access or is offline, `make run --offline` starts the provider clients against a local stub server. No key is needed and nothing is read from disk.
- **State:** memory only. No key file is written on the developer machine.
- **If it fails:** no dev access gives a clear startup error and a non-zero exit. The offline mode is the fallback. Prod is never involved.

---

## Open questions

1. **Post-migration rotation cadence.** Security has not decided whether keys must be rotated on a schedule, or how often. This plan sets no cadence. A recurring rotation would reuse steps A3–A7, and it needs its own plan and decision.
2. **Retry count.** The brief says "retry 3 times". This plan reads that as 3 retries after the first attempt (4 attempts in total). If it means 3 attempts in total, change one constant in R1 and the timing in A5.
3. **Rollback after revocation.** Once a key is revoked (A7), any pre-migration image that still contains it cannot be used. A8 blocks those rollbacks. Confirm this is acceptable, or decide how a rollback should get a working key.
4. **Old images.** Old container images contain the leaked keys. Decide whether to delete them from the registry, which would remove the rollback target, or keep them behind the A8 block.
5. **Pre-cutover key check.** If a provider offers a read-only auth check, use it in A4 to validate each new key before the write. Confirm whether one exists for each provider.
6. **How version ids are reported.** Choose log lines, a metric, or both for the A6 check. This plan assumes log lines, since the central log service is already in use.
7. **Emergency revocation.** The brief allows revocation only after confirmation. If a key is abused before the rollout finishes, the security team needs a documented exception path. This plan does not define one.
8. **Staging.** The brief names only dev and prod. If a staging environment exists, insert it before A4 with the same gates.
9. **Alert threshold for stale secrets.** Ops must choose the threshold for the R2 staleness alert.