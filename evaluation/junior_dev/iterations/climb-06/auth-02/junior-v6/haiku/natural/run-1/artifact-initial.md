# orders-api: move the three live API keys into the managed secret store

## Summary

The payments, email, and geocoding keys leave `config/app.yaml` and move to the managed secret store under `orders-api/<env>/<name>`. Each key is rotated at its provider first. The app reads keys from the store at startup, holds them only in process memory, and refreshes them every 5 minutes. Old keys are revoked only after every running instance is confirmed on the new key and a bake period has passed. No customer request should fail at any point, so the sequence is: prepare the store, rotate at providers while the old keys still work, ship the new code behind a readiness gate, verify, and only then revoke.

Secret names (proposed): `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, `orders-api/prod/geocoding_api_key`. The same names exist under `orders-api/dev/` and `orders-api/staging/` (if staging exists) with sandbox keys.

Each step lists: **Starts when**, **Moves**, **State lives**, **If it fails**.

---

## Part A: Rollout

### A1. Confirm provider capabilities and inventory

- **Starts when:** this plan is approved.
- **Moves:** nothing.
- **State lives:** a migration record (in the tracking issue) listing each provider, its key owner, and whether it allows two live keys at once.
- **If it fails:** if a provider allows only one live key, its rotation needs a planned cut-over window. Mark that provider in A4 and A11 and take it out of the general sequence. Do not change anything else yet.

### A2. Prepare store access and KMS

- **Starts when:** A1 is complete.
- **Moves:** creates the three prod secret entries (empty until A5). Confirms the per-environment KMS key exists for prod.
- **Access policy:**
  - Identity `orders-api-prod`: read on `orders-api/prod/*` and decrypt on the prod KMS key. No write, no list outside that prefix.
  - Security on-call role: write on `orders-api/prod/*`. This is the only write path to prod.
  - Engineers: no read on prod. Dev access is separate (see C1).
- **State lives:** the store's access policy, managed as code in the infra repo.
- **Verification:** test the policy with a non-prod identity and with an engineer identity. Both must be denied on prod reads. `orders-api-prod` must be denied on writes and on any other prefix.
- **If it fails:** if access is broader than the policy, stop here. Fix the policy before creating any secret values.

### A3. Create dev and staging secrets (sandbox keys)

- **Starts when:** A2 is complete.
- **Moves:** sandbox keys from each provider's sandbox into `orders-api/dev/*` (and `orders-api/staging/*` if staging exists). These are not live keys.
- **State lives:** the dev and staging store entries.
- **If it fails:** local development uses the offline mode in C1 until this succeeds. Production is not affected.

### A4. Rotate at providers, keeping old keys valid

- **Starts when:** A1 and A2 are complete. Security on-call performs this.
- **Moves:** a new live key is created at each provider. The old key is not revoked. Nothing uses the new key yet.
- **State lives:** the provider consoles. The new key value should go directly from the provider to the store (A5) and must not be pasted into tickets, chat, or files.
- **If it fails:** if creation fails or the provider rejects it, keep the old key. Nothing in production has changed, so there is no customer impact.

### A5. Write new versions to the prod store

- **Starts when:** A4 is complete for a provider.
- **Moves:** the new live key goes into `orders-api/prod/<name>`. The store assigns a new version id. Record the version id in the migration record (the id is not secret; the value is never recorded).
- **Verification:** confirm the key works with a read-only provider call made by security on-call before any pod uses it.
- **State lives:** the store, encrypted with the prod KMS key.
- **If it fails:**
  - If the write fails, retry it. Old pods are unaffected because they still hold the old key from the old image.
  - If the key does not work with the provider, do not write it. Go back to A4.
  - If a bad value was written, write a corrected version. Running pods will not pick it up until the next refresh (B4) or restart, and no pod on the new code exists yet.

### A6. Build the new code and image; prove it in staging

- **Starts when:** the PR with the code changes in Part B and the `config/app.yaml` change (all `api_key` lines removed) is merged to `main`. CI builds one image as usual.
- **Moves:** the image contains the new code, a `config/app.yaml` without keys, and no secrets.
- **Staging check:** deploy the image to staging with sandbox keys. Check that:
  - the new pods do not become ready until all three keys are loaded;
  - a store outage at startup leads to a non-zero exit after the retries;
  - a store outage after startup leaves the app serving on the last good keys with a warning.
- **If it fails:** do not promote the image. Fix it on `main` and rebuild. Production is untouched.

### A7. Roll out to production

- **Starts when:** A5 is complete for all three providers, A6 has passed in staging, and the release is approved.
- **Moves:** pods are replaced one at a time (`maxUnavailable: 0`). A new pod loads the three prod keys at startup (B1). It joins traffic only after readiness (B2) passes. Old pods keep serving until each replacement is ready.
- **State lives:** each pod's memory only. The rollout status lives in the cluster.
- **Watch during rollout:**
  - each new pod's logged version ids for the three keys;
  - per-pod provider error rate (401/403 from any provider);
  - pod restarts and exit codes.
- **If it fails:**
  - Store unreachable or key missing: the new pod retries, then exits non-zero. It crash-loops and never becomes ready, so the rollout halts and old pods keep serving. Page the on-call.
  - Keys load, but a provider rejects them (401/403 spike on the new pods): the pod is ready, so it may take traffic. Halt the rollout and roll back to the previous image. This is safe only while the old keys are still valid, which is why A10 must not happen early.
  - A rollback must not happen after A11. Once old keys are revoked, a pre-migration image cannot work (see A10).

### A8. Verify every instance is on the new keys

- **Starts when:** the rollout reports complete.
- **Moves:** nothing.
- **Check:**
  - every running pod logs the new version id for all three keys;
  - no pod from the old ReplicaSet remains (including any pod that is still draining);
  - provider error rates are at baseline for each provider;
  - the bake period has started (length in open questions).
- **If it fails:** any pod still on an old version id, or any pod with a new error pattern, blocks A10. Investigate that pod; do not revoke.

### A9. Bake period

- **Starts when:** A8 passes.
- **Moves:** nothing.
- **Why:** if a problem appears only under real traffic, the old keys are the fallback. They are revoked only after the period passes.
- **Minimum:** at least one full refresh interval (5 minutes) after the last pod changed, plus the bake window agreed with security (open question).
- **If it fails:** a provider error spike or a version mismatch restarts the check from A8, after the cause is fixed.

### A10. Revocation gate (checklist)

Security on-call and the service owner each sign off that:

1. A8 passed and no pre-migration pod exists.
2. A9 passed.
3. The provider error rate matches the pre-migration baseline.
4. Deploys of pre-migration image tags are blocked. Add an admission rule so that a pre-migration image cannot be redeployed, since its embedded keys will be dead. The rollback target is now a post-migration image only.

Gate failures keep the old keys valid. Nothing is revoked.

### A11. Revoke the old keys at providers

- **Starts when:** A10 is signed off. Security on-call performs this. It requires explicit approval because it cannot be undone.
- **Moves:** each old key is revoked at its provider. The revocation time and key id go into the migration record.
- **State lives:** the provider consoles.
- **If it fails:** if customer errors appear after revocation, the only recovery is issuing another new key, and the store and running pods must be updated. This is why A10 is strict.

### A12. Clean up and close

- **Starts when:** A11 is complete.
- **Moves:** nothing in git history (it is not rewritten). Old keys are treated as leaked permanently.
- **Checks:**
  - search the central logs (30-day retention) for the old key values. Any hits age out within 30 days of their last log line. Record the result.
  - note that old container images still embed the old keys. They are inert after revocation, but restrict pulling them if the registry allows it.
  - update `deploy.md` to describe the new readiness meaning, local dev, and the rule that keys never go on disk.
- **If it fails:** a log or artifact hit that cannot age out is escalated to security.

---

## Part B: How the app reads keys at runtime

### B1. Startup load (before the server accepts traffic)

- **Starts when:** process start.
- **Process:**
  1. Read non-secret settings from `config/app.yaml` (names, base URLs, timeouts). Secret names are references, not values.
  2. Read the environment name from a non-secret environment variable (for example `APP_ENV`).
  3. For each of the three names, fetch the current version from `orders-api/<env>/<name>`.
  4. Store each value in one in-memory holder with its version id and fetch time. Nothing is written to disk or to the environment.
- **Retry policy:** the brief says "retry 3 times, 2 seconds apart." This plan reads it as 1 initial attempt plus 3 retries, with 2 seconds between attempts (open question). A key that is missing while the store is reachable uses the same policy.
- **Success:** all three keys are present. Mark the process ready (B2) and start the refresh timer (B4).
- **If it fails:** log an error naming the missing secret and the store error (never the value), then exit non-zero. The orchestrator restarts the process with backoff, and old pods keep serving.

### B2. Readiness and liveness

- **Today:** `/healthz` returns OK as soon as the listener is up. That is unsafe with this design, because a new pod would receive traffic before it has keys.
- **Change:**
  - Readiness returns 200 only after B1 has succeeded. It does not depend on refresh status, so a later store outage does not drain pods.
  - Liveness only checks that the process responds. It does not depend on the store.
- **Failure of this change:** if readiness still returns OK early, the rollout gate fails silently. Add a test that a pod with no keys returns not-ready.

### B3. How clients read a key

- **Today:** clients copy the key once in the constructor, and the module-level singletons are built at import. That would freeze the old key in memory forever.
- **Change:** each client takes a secret provider and calls `get('payments')` (and the others) when it makes a request. The value comes from the in-memory holder. The holder swaps the whole record atomically, so a call always sees a complete value and version id.
- **Import rule:** importing the modules must not do network I/O. The explicit startup step (B1) runs once and is the only place keys are loaded.
- **If it fails:** a client that caches a key at construction would keep using a revoked key. Test that a refreshed value reaches the next request.

### B4. Background refresh every 5 minutes

- **Starts when:** B1 succeeds. Runs on a timer in the same process.
- **Per cycle, for each secret:**
  1. Fetch the current version, with a timeout (value to set).
  2. On success with a new version id: swap the holder and log the version id change (the value is not logged).
  3. On failure: keep the last good value, log a warning with the secret name, the error type, the last good version id, and how long it has been unchanged. Do not change readiness.
- **State lives:** memory only.
- **If it fails:**
  - a short store outage has no effect beyond the warning;
  - a long outage keeps the last good value indefinitely, and alerts fire when the value is older than a threshold (value to set; it depends on the cadence decision, which is open).
- **Limitation:** the app does not check that a new value works. If the store serves a version the provider rejects, the app keeps using it. Detection is by provider error rate (A7, A8). Whether the app should fall back to the previous version is an open question.

### B5. Logging and memory hygiene

- Logs include secret names, version ids, fetch times, and error types. They never include values.
- Add a logging filter that refuses to emit anything matching a known key prefix, as a backstop.
- Test fixtures use fake values, never real keys.
- The process does not write secrets to disk, to environment variables, or to crash dumps (disable core dumps for this process).

### B6. Concurrency

- One refresh task writes the holder. Any number of request threads read it. Each read takes a snapshot of the record, so refresh never exposes a partial update.

---

## Part C: Local development

### C1. `make run` without prod access

- **Starts when:** a developer runs `make run`.
- **Moves:** `make run` loads the dev keys from `orders-api/dev/*` using the developer's own dev identity, which has no prod access. The keys are held in memory only.
- **If the developer has no dev access, or the store is down:** an offline mode (`make run-offline`) uses stub provider clients so the app starts and runs without any key.
- **Result:** no developer needs a prod key, and the repo's `config/app.yaml` no longer holds one.

### C2. CI guard against key reintroduction

- **Starts when:** every PR.
- **Rule:** fail if `config/app.yaml` contains an `api_key` entry. Also fail if any tracked file contains the known live-key prefixes (`pk_live_`, `ml_live_`, `geo_live_`).
- **Scope:** this stops new keys from entering the repo. It does not remove the old keys from history, which remains as it is.
- **Add the guard in the same PR as the yaml change (A6).** Adding it earlier would fail on the current file.
- **If it fails:** the PR cannot merge. The developer moves the value to the store.

---

## Open questions

1. **Rotation cadence (not decided).** Security has not decided whether keys must rotate on a schedule after this migration, or how often. This plan picks no cadence. The answer affects the refresh interval, the staleness alert threshold, and whether rotation becomes a repeated runbook.
2. **Two live keys per provider.** Confirm in A1 that each provider allows an old and a new key at once. If not, its rotation needs a planned cut-over, and A7 and A11 change for that provider.
3. **Bake period.** The length beyond the 5-minute refresh is a choice for security and the service owner.
4. **Retry count.** Confirm whether "retry 3 times" means 3 total attempts or 3 retries after the first attempt. This plan uses the second reading.
5. **Staging.** Confirm whether a staging environment exists. A6 assumes it does.
6. **Store version semantics.** Confirm whether the store supports version labels or staged promotion. If it does, A5 can write a "pending" version and promote it after A8, which removes the window where a bad value is current.
7. **Fallback on rejected values.** Should the app keep the previous version when a provider rejects the new one? This plan does not add that behavior.
8. **Old keys in logs.** Confirm whether old keys were ever logged. The 30-day retention bounds the exposure after revocation, but it does not undo any earlier leak.
9. **Probe path.** Confirm that the readiness path stays `/healthz` or changes to a new path, and update the cluster probe config to match.