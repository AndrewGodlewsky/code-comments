# Plan: move orders-api third-party keys to the managed secret store

## Scope and assumptions

- Keys in scope: payments, email, geocoding. Each is a live key that has been in git history for two years and is treated as leaked.
- Secret names: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, `orders-api/prod/geocoding_api_key`.
- The store encrypts values at rest with a per-environment KMS key and gives each write a new version id. Version ids are non-secret and may be logged.
- Prod runs 4 replicas under `orders-api-prod`. Deploys are rolling with `maxUnavailable: 0`.
- Git history is not rewritten. Rotation at each provider is what neutralises the old values.
- Assumption to verify in step 1: each provider can keep two keys active at once. The whole plan depends on this.
- Not decided: whether keys must be rotated on a regular schedule after this migration, and how often. This is an open question (see the final section). No cadence is set in this plan.

## Target state

- `config/app.yaml` holds only non-secret settings (`base_url`, `timeout_seconds`, `from_address`, app name, port, log level). It has no `api_key` anywhere.
- At runtime the app holds the three keys in memory only, fetched from the store with the pod's workload identity.
- A background refresh re-reads the keys every 5 minutes.
- Readiness (`/healthz`) returns 200 only after all three keys are loaded.
- CI fails any change that reintroduces an `api_key` into `config/app.yaml`.
- Local development uses dev-environment keys from `orders-api/dev/*`. It never reads prod.

---

## Part A: Runtime design (how the app reads keys)

### A1. Startup load

- **Starts:** container process start (or `make run` locally, see Part C).
- **Moves:** the process loads `config/app.yaml` (non-secret settings only) and validates it against a schema. It then authenticates to the store with the pod identity and reads the current version of each of the three secrets into an in-memory secret holder.
- **State lives:** process memory only. Nothing is written to disk, to environment variables, or to logs. The only log output is the secret name and version id.
- **Changes from today:** the loader no longer reads secrets at import time. Startup is an explicit init step, so tests can inject a fake store and no module does network I/O on import.
- **Startup validation:** if `config/app.yaml` contains an `api_key` key at any depth, the process refuses to start. This is defense in depth behind the CI guard in Part D.
- **If the store cannot be reached:** one initial attempt plus 3 retries, 2 seconds apart (attempts at about 0 s, 2 s, 4 s and 6 s). If all attempts fail, the process logs the failure without any secret values and exits with a non-zero code. Kubernetes restarts it, and a rolling deploy halts (see A2).
- **If a secret is missing or the identity is denied:** treated the same as an unreachable store. The process does not become ready and exits non-zero after the same retry budget. This is a choice made here; see open questions.

### A2. Readiness and liveness

- **Starts:** kubelet probes.
- **Readiness** (`/healthz` as today, used by the rollout): returns 200 only after A1 has completed for all three keys. Before that it returns non-200.
- **Liveness** (a separate endpoint or process check): returns 200 while the process is serving. It does not depend on the store, so a store outage cannot restart healthy pods.
- **If a new pod never becomes ready:** the rollout halts because `maxUnavailable: 0`. Old pods keep serving on their existing keys. This is the main protection against a bad store, bad IAM or a missing secret reaching customers.
- **Deploy.md change:** the readiness contract changes from "HTTP listening" to "keys loaded". Update the file when this ships.

### A3. Refresh every 5 minutes

- **Starts:** a background timer in each process, with random jitter so the 4 replicas do not all call the store at the same moment.
- **Moves:** the process reads the current version of each of the three secrets. For each key whose version id changed, it swaps the value in the holder. Each key is swapped independently, and a swap is atomic.
- **State lives:** memory. The last good value per key is kept until a newer one is read successfully.
- **Logging:** each swap logs the secret name, old version id and new version id. Values are never logged.
- **If a re-read fails** (store down, throttled, or IAM error): keep the last good value for that key, log a warning with the secret name and error class, and try again at the next tick. Requests are not affected.
- **Residual risk:** a refresh cannot tell a good new version from a bad one. A version the provider rejects will be used within 5 minutes. Mitigations are the pre-validation in B3 and an alert on provider 401/403 rate per pod (see B5).

### A4. Client use of keys

- **Starts:** each provider call (`charge`, email send, geocode).
- **Moves:** clients ask the secret holder for the key on every call. They no longer copy the key into `self._key` at construction, which today would freeze it for the life of the process and defeat A3.
- **State lives:** memory.
- **Log safety:**
  - The holder's string representation is redacted, so tracebacks and debug output cannot print the key.
  - HTTP client logging of request headers is disabled or scrubbed for the `Authorization` header.
  - Error wrapping does not include request headers or the key.
- **If a provider call fails:** the failure is handled as it is today. Store availability does not affect the request path.

### A5. Shutdown and host hygiene

- **Starts:** pod termination.
- **Moves:** nothing is persisted. The holder is cleared on shutdown on a best-effort basis.
- **Host checks:** prod containers run with core dumps disabled, because a core dump would write key values to disk. Swap and memory-dump settings are confirmed with the platform team.
- **If this check fails:** the platform team must fix it before step 6 of Part B. This is a blocker for the "never on disk" requirement.

---

## Part B: Rollout

### B1. Confirm provider overlap

- **Starts:** plan approval. Security on-call and the service owner do this together.
- **Moves:** nothing in our systems. For each of payments, email and geocoding, confirm in the provider's documentation or support that two keys can be active at the same time, and that creating a new key does not revoke the old one.
- **State lives:** a decision record in the team's rollout ticket. The record holds only the provider name and the answer.
- **If a provider does not allow overlap:** stop. Do not start B3 for that provider. Rotating a key that other pods are still using causes an outage, which the brief forbids. Escalate to security for a different design, such as a provider-side maintenance window that has been approved.

### B2. Create secret entries, KMS keys and IAM

- **Starts:** security on-call, through infrastructure-as-code or the store console, after B1 passes.
- **Moves:**
  - Create `orders-api/prod/*` and `orders-api/dev/*` entries, each environment with its own KMS key.
  - `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else.
  - Only the security on-call role can write prod secrets.
  - Engineers get read access to `orders-api/dev/*` only.
- **State lives:** the store, encrypted with the per-environment KMS key. The IAM policy is in infrastructure-as-code.
- **Checks:** a test read as `orders-api-prod` succeeds on `orders-api/prod/*` and fails on any other path. A test read as an engineer fails on `orders-api/prod/*`.
- **If it fails:** nothing has changed for customers. Fix IAM before B4. Any IAM gap will surface as a non-ready pod in B5, which the rollout will catch.

### B3. Rotate each key at its provider, without revoking the old one

- **Starts:** security on-call, after B2 passes.
- **Moves:** generate a new key at each provider. Test each new key with a read-only call. The old key stays active.
- **State lives:** the provider dashboard. New key values are not written to tickets, chat, the repo or any log.
- **If the provider cannot issue a key:** nothing has changed and the old key is still valid. Stop and retry later.
- **If the test call fails:** discard that new key, generate another, and do not write it to the store.

### B4. Write the new values to the store (version 1)

- **Starts:** security on-call, after B3 passes for that key.
- **Moves:** write the new value of each key into `orders-api/prod/<name>`. The store assigns version ids. Record the version id of each write in the rollout ticket. The id is not secret.
- **State lives:** the store. Current pods are not affected, because they still read their keys from the old config file (see Part B5 for how pods change).
- **If the write fails:** nothing changes. Retry the write.

### B5. Staging proof, then the code change

- **Starts:** a PR containing the code change in Part A, the config change in Part D, and a deploy.md update. Merge to `main` starts CI and the image build.
- **Staging:** deploy the image to staging with staging keys. Verify:
  - startup and readiness behaviour;
  - a refresh that picks up a new version;
  - a re-read failure that keeps the last good value and logs a warning;
  - a store outage at startup, which should give the 3-retry, non-zero exit behaviour;
  - a denied identity, which should not become ready;
  - no key values in logs or on disk.
- **If staging fails:** do not deploy to prod. Fix and repeat.
- **Prod rollout:** the image is built from `main` and does not contain `api_key`. Pods are replaced one at a time. For each new pod:
  - It starts with the new image and reads all three keys from the store with `orders-api-prod`.
  - It becomes ready only when all three are loaded.
  - Only then is one old pod stopped.
- **Mixed fleet during the rollout:** old pods keep their file-based keys (the old, still-valid keys), and new pods use the store keys (the new keys). Both sets are valid because of B1, so customers see no failures from the mix.
- **If a new pod crashes on start** (store unreachable, identity denied, or key missing): the process retries as in A1, exits non-zero, and is restarted with backoff. The rollout halts. Old pods keep serving.
- **Recovery:** fix the cause, then continue the rollout or roll back (see Part E).

### B6. Confirm every instance is on the new keys

- **Starts:** the rollout reports complete, with all 4 replicas on the new image.
- **Moves:** nothing. This is a check.
- **Checks, all required:**
  - All 4 pods run the new image digest. No pod runs a pre-migration image.
  - Each pod's logs show the store version ids recorded in B4 for all three keys, either at startup or at a refresh within 5 minutes. Use a time window of at least one full refresh cycle after the last pod was replaced.
  - If a newer version id exists, re-check against the newest id and repeat.
- **State lives:** the pod list from the cluster, and the central log service (30-day retention).
- **If any check fails:** do not continue. Find out why the pod is not on the new key or the new image. Do not revoke anything.

### B7. Revoke the old keys at each provider

- **Starts:** B6 passes for all four replicas, and security on-call approves. This is the only point at which an old key may be revoked.
- **Moves:** revoke each old key at its provider, one provider at a time.
- **Watch:** after each revocation, check for 401/403 responses and error rate for the next 15 minutes.
- **State lives:** the provider dashboard.
- **If a revoked key was still in use:** the revocation cannot be undone. Replace it with the new key in the store only if the new key is still valid, and treat the incident as a customer-impact event. This is why B6 is strict.
- **Soak window:** the time between B6 and B7 is a decision for the owner (see open questions). This plan does not set it.

### B8. Clean up the repo and the config

- **Starts:** the PR in B5 has already removed `api_key` from `config/app.yaml`. This step is the final check.
- **Moves:** confirm the current tree contains no live key strings and no `api_key`. Do not rewrite git history.
- **Log check:** search the central logs for the three old key strings. Any hit is recorded as an incident note. The keys are already revoked, so no rotation is needed for them again.
- **If a hit is found in an active config or image:** remove it and rebuild.

---

## Part C: Local development

### C1. `make run`

- **Starts:** a developer runs `make run`.
- **Moves:** the process reads the same non-secret `config/app.yaml`. It then reads `orders-api/dev/*` with the developer's dev-only identity into memory, using the same loader as prod.
- **State lives:** memory only. No `.env` file, no shell variable and no file on disk holds key values.
- **Dev keys:** `orders-api/dev/*` holds provider sandbox keys, or the team's agreed test keys. Live keys are never used locally.
- **Prod protection:** the loader refuses to run if the environment is `prod`, and the developer identity has no read on `orders-api/prod/*`.
- **If the developer has no dev access:** the process refuses to start with a clear message. A documented fallback is to point `base_url` at a provider sandbox or local stub. The fallback is opt-in and never reads prod.
- **If the store is unreachable locally:** the same retry-then-exit behaviour as A1. A developer can use the stub mode.

---

## Part D: CI guard

### D1. Block `api_key` in config on every PR

- **Starts:** every pull request and every push to `main`.
- **Moves:** nothing. The job parses `config/app.yaml` as YAML and fails if any mapping key named `api_key` appears at any depth. It also greps the whole current tree for the known live key prefixes (`pk_live_`, `ml_live_`, `geo_live_`).
- **Also in the image build:** the build fails if the built image's `config/app.yaml` contains `api_key`.
- **Required check:** make the job a required status check on `main` branch protection, so it cannot be skipped by merging.
- **If it fails:** the PR is blocked. The author removes the key and uses the store.
- **Limit:** CI cannot stop a direct commit that bypasses branch protection. Branch protection is the control for that case.

---

## Part E: Rollback

### E1. Roll back a bad deploy

- **Starts:** an alert or a failed readiness during rollout.
- **Moves:** redeploy an earlier image.
- **Constraint:** before B7 (old keys revoked), a pre-migration image still works, because its file-based keys are valid. After B7, a pre-migration image holds revoked keys and must never be deployed. Rollback targets after B7 are migration-era images only.
- **Enforcement:** the deploy pipeline rejects any image that contains `api_key` in its config. This is the same check as D1, applied at deploy time.
- **If the store is the cause:** prefer rolling back the store version, not the image. Set the current version back to the previous version id, as recorded in B4 and later writes. The app picks up the change at the next refresh. Pods already running are not restarted.

---

## Open questions

1. **Rotation cadence (not decided):** security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan does not set one. The refresh interval in A3 is not a rotation policy.
2. **Provider overlap:** B1 must be answered for each provider before any rotation. If any provider cannot keep two keys active, this plan does not apply to that provider as written.
3. **Soak window between B6 and B7:** the owner must decide how long to wait after all pods are confirmed before revoking. The plan does not set a value.
4. **Retry count wording:** the plan reads "retry 3 times, 2 seconds apart" as one initial attempt plus 3 retries, about 6 seconds total. Confirm this reading.
5. **Missing secret with a reachable store:** the plan treats it as a startup failure with the same retry budget. Confirm that this is the desired behaviour.
6. **Bad version in the store:** a refresh cannot detect a version the provider rejects. Decide whether to add a validation call before a refresh swaps a value, or rely on pre-validation in B3 and the 401/403 alert.
7. **Refresh jitter and version-id reporting:** confirm the jitter window, and whether version ids are exposed on an internal endpoint in addition to logs. An endpoint would make the B6 check faster.
8. **Core dumps and host memory:** the platform team must confirm the A5 host settings before B5.