# Plan: move orders-api third-party keys to the managed secret store

## Summary

`orders-api` calls three outside services (payments, email, geocoding). Each call needs an API key, a secret string that tells the provider the caller is us. Today the three live keys are written in `config/app.yaml`. That file is committed to git and copied into every container image, so anyone who can read the repo or an image can read the keys.

This plan moves the keys into the managed secret store, under `orders-api/<env>/<name>`. The app loads them into memory at startup and re-reads them every 5 minutes. Each key is replaced at its provider. An old key is revoked only after every running instance is confirmed to be using the new one.

Non-secret settings (`base_url`, `timeout_seconds`, `from_address`, `port`, `log_level`) stay in `config/app.yaml`.

Git history is not rewritten. The old keys remain in past commits, so they count as leaked and must be replaced at each provider.

## Terms used in this plan

- **Provider:** the outside company whose API we call (payments, email, geocoding).
- **Secret store:** the managed service that holds secret values. It encrypts them at rest and keeps every version.
- **Secret path:** the name of one secret, in the form `orders-api/<env>/<name>`. For example, `orders-api/prod/payments_api_key` is the `payments_api_key` secret in the `prod` environment.
- **KMS key:** the encryption key the secret store uses. There is one per environment (dev and prod).
- **Store SDK:** the client library the app uses to read secrets from the secret store.
- **Identity:** the account a pod or a person uses to call the secret store. Access is granted per identity.
- **IAM policy:** the rules that say which identity may read or write which secret paths. IAM means identity and access management.
- **Version id:** every write creates a new version of a secret, with its own id. Pods log the version ids they load, so we can see which key each pod is running.
- **Holder:** the in-memory object in the app that stores the current three key values and their version ids.
- **Pod:** one running copy of the app. Production runs 4 pods, all under the identity `orders-api-prod`.
- **Readiness probe:** a check the platform runs on each pod (`GET /healthz`). A pod receives traffic only while this check returns 200.
- **Liveness probe:** a check that the process is alive. If it fails, the platform restarts the pod.
- **Rolling deploy with `maxUnavailable: 0`:** the platform starts one new pod, waits for it to pass readiness, and only then stops one old pod. If a new pod never becomes ready, the rollout stops and the old pods keep serving.
- **Revoke:** disable an old key at its provider so it no longer works. This cannot be undone.
- **Gate:** a condition that must be true before the next step may start.

## Gates

- **Gate A (blocking):** Each provider must allow the old and new keys to be active at the same time. If a provider allows only one active key, the "no customer failure" requirement cannot be met as written. Stop and escalate before step 3.
- **Gate B:** An old key is never revoked while any instance, local run, or CI job still uses it. See step 13.

## Order of steps

Run the steps in numeric order, with two exceptions:

- Steps 16 and 17 are one change that merges after step 9 and before the rollout in step 12. The deployed image therefore contains no keys.
- Step 15 is completed before step 14. It closes the rollback path before any key is revoked.

---

## Phase 0: Preparation (no customer impact)

### 1. Inventory consumers and provider capabilities

- **Starts when:** The migration is approved.
- **What moves where:** Nothing moves. Record every reader of the three keys:
  - the three provider clients (`payments.py`, `email.py`, `geocoding.py`),
  - the `make run` local path,
  - CI jobs that read `config/app.yaml`,
  - any other service that copies the file.

  For each provider, record:
  - whether two keys can be active at once (Gate A),
  - whether a sandbox or test key exists,
  - whether a non-mutating check call exists (a call that tests a key without changing any data),
  - whether the provider reports usage per key. Step 13 needs this.
- **State:** A migration checklist in a tracking issue. No code change.
- **If it fails:** If a provider cannot support two active keys, or a consumer is found that this plan does not cover, stop. Nothing has changed yet.

### 2. Create secret paths, KMS keys and IAM policies

- **Starts when:** Step 1 is complete.
- **What moves where:** Create the paths `orders-api/dev/*` and `orders-api/prod/*`, with one KMS key per environment. Set these permissions:
  - `orders-api-prod` (the production pod identity): read on `orders-api/prod/*`, plus decrypt on the prod KMS key, which a read requires. No other secret or KMS permissions.
  - Security on-call: write on `orders-api/prod/*`.
  - Engineers: no read on `orders-api/prod/*`.
  - Developer identity: read on `orders-api/dev/*` only.
- **State:** The secret store and KMS policies. No secret values exist yet.
- **If it fails:** Wrong permissions show up later as startup failures, so test them now. An engineer's read of a prod path must be denied. `orders-api-prod` must be denied on every path other than `orders-api/prod/*`.

### 3. Obtain dev and test keys

- **Starts when:** Gate A is passed.
- **What moves where:** Create non-production keys at each provider, using sandbox or test mode where the provider offers it. Write them to `orders-api/dev/<name>`.
- **State:** Dev values in the dev secret path.
- **If it fails:** Local development is blocked, but production is not affected. Never use live keys for development.

---

## Phase 1: Code change (merged, not yet promoted to production)

### 4. Add the secret loader

- **Starts when:** Step 2 is complete.
- **What moves where:** Add a new module (for example `app/secrets.py`) that:
  - At startup, fetches the three secrets from `orders-api/<env>/<name>`. The environment name comes from configuration.
  - Keeps the values in the holder. A refresh replaces the values only when all three reads succeed (see Runtime behavior).
  - Runs a background refresh every 5 minutes.
  - Logs version ids, never values.
- **State:** Process memory only. No disk cache, no environment variables, no temp files. The store SDK's debug logging is turned off. Exception messages are scrubbed so they cannot contain key material.
- **If it fails:** See the failure table in Runtime behavior.

### 5. Change the provider clients

- **Starts when:** Step 4 is written.
- **What moves where:** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in their constructors. Each call reads the current key from the holder, so a refresh takes effect without a restart. Remove the module-level singletons that read keys at import time. Keep the `base_url` and timeout reads as they are.
- **State:** Same as step 4.
- **If it fails:** A client that still copies the key keeps a stale key until restart. A test must confirm that a refreshed value is used on the next call.

### 6. Gate readiness on the keys

- **Starts when:** Step 5 is written.
- **What moves where:** `GET /healthz` returns 200 only after all three secrets are loaded. Readiness stays true when a later refresh fails.
  - The liveness check must not depend on the keys. If the platform also uses `/healthz` for liveness, add a separate liveness path. Otherwise a pod that is still waiting for keys gets restarted in a loop.
- **State:** Process memory.
- **If it fails:** Today `/healthz` returns OK as soon as the HTTP server starts listening. If that is not changed, a new pod passes readiness with no keys and customer requests fail. This change is required before any rollout.

### 7. Point local development at the dev store

- **Starts when:** Step 3 is complete.
- **What moves where:** `make run` loads the dev secret path using the developer's dev-only identity. It never reads the prod path. Local copies of `config/app.yaml` contain no keys.
- **State:** Process memory.
- **If it fails:** A developer cannot run locally until they have dev access. Local runs must not fall back to the live keys.

### 8. Tests

- **Starts when:** Steps 4 to 7 are written.
- **What moves where:** Tests must cover:
  - Startup with the store unreachable makes the retries described in Runtime behavior, then exits non-zero.
  - A refresh failure keeps the last good values and logs a warning.
  - A refreshed value is used on the next call.
  - Readiness is false before the keys load and true after.
  - No key value appears in logs, including when a request fails.
- **State:** Test code only.
- **If it fails:** Do not merge.

### 9. Merge the code, and do not promote it

- **Starts when:** Step 8 passes review.
- **What moves where:** The code merges to `main`, which builds an image. Do not deploy that image to production yet.
  - The image still contains the `api_key` lines in `config/app.yaml`. They are removed in step 17.
  - The image must not be deployed until the store holds the new values (step 10).
- **State:** A built image that is not deployed.
- **If it fails:** Nothing has reached production.

---

## Phase 2: New keys in the store

### 10. Rotate each key at its provider

- **Starts when:** Step 9 is merged and step 2 is complete.
- **What moves where:**
  1. The security on-call creates a new key at each provider. The old keys stay active.
  2. The security on-call writes each new key to `orders-api/prod/<name>`. Each write creates a new version id.
  3. Engineers do not see the values.
- **State:** The prod secret store now has a new version of each secret, encrypted with the prod KMS key. The old keys are still active at the providers.
- **If it fails:**
  - If a provider call or a store write fails, nothing uses the new key yet, so retry. Each store write gets a new version id, so a partial write is visible and can be repeated.
  - Readiness does not prove that a key works at the provider. Use the provider's check call where one exists (step 1), and confirm the key works before writing it to the store.
  - A bad new version does not stay contained. Running pods pick it up at their next refresh (within 5 minutes), and their calls then fail. Rely on the provider check call, and on the traffic checks in step 13.

---

## Phase 3: Rollout

### 11. Verify that the production identity can read

- **Starts when:** Step 10 is complete.
- **What moves where:** Check that `orders-api-prod` can read all three `orders-api/prod/<name>` paths and nothing else.
- **State:** Nothing changes.
- **If it fails:** Pods would fail at startup, and the rollout would halt at readiness. That is safe. Fix the IAM policy and retry. Do not roll out until this check passes.

### 12. Rolling deploy of the new image

- **Starts when:** Steps 10 and 11 are complete, and steps 16 and 17 have merged.
- **What moves where:** The platform replaces pods one at a time. Each new pod loads the three secrets and passes readiness. Then one old pod stops (`maxUnavailable: 0`).
  - During the rollout the fleet is mixed. Old pods use the old keys, and new pods use the new keys. Both sets work because step 10 kept the old keys active.
  - The deployed image contains no keys, because steps 16 and 17 merged before this step.
- **State:** Each pod's memory. The fleet's progress is visible in the pods' version-id logs.
- **If it fails:**
  - A new pod that cannot read the store exits non-zero. It never becomes ready, the rollout halts, and the old pods keep serving.
  - Rollback means redeploying an earlier image. Earlier images still contain the old keys in `config/app.yaml`. They work only while the old keys are active, which is until step 14. After step 14, a rollback to any earlier image fails, because its keys are revoked. Step 15 blocks that choice before revocation happens.

### 13. Confirm every instance is on the new version

- **Starts when:** The rollout (step 12) completes.
- **What moves where:** Wait at least one full refresh cycle (5 minutes) plus a margin. Then confirm both of these:
  - Every running pod's latest logged version id is the new one.
  - Old-key usage at each provider has been zero for the whole window. This catches any forgotten consumer, such as a local run or a CI job. It requires the usage reporting found in step 1.
- **State:** Logs and provider usage reports.
- **If it fails:** Do not revoke. Find out why any pod is still on an old version, or why old-key usage remains, before going on.

---

## Phase 4: Revocation and cleanup

### 14. Revoke old keys

- **Starts when:** For a given provider, step 13 passes for that provider, and step 15 is complete.
- **What moves where:** The security on-call revokes that provider's old key at the provider. Each provider's key is judged only on that provider's step 13 results.
- **State:** At the provider. Revocation cannot be undone.
- **If it fails:** If a consumer still uses an old key, customer requests to that provider fail. This is why step 13 is a hard gate. Do not revoke one provider's key based on another provider's results.

### 15. Block rollback to pre-migration images

- **Starts when:** Step 13 passes. This step must be complete before step 14.
- **What moves where:** The deploy pipeline refuses images built before the migration. This stops a rollback from putting keys back into files, and from deploying keys that have been revoked. It must be in place before revocation.
- **State:** Deploy policy.
- **If it fails:** If a rollback is needed after this point, the rollback target must be a post-migration image.

### 16. CI guard against `api_key` in the config

- **Starts when:** Merged together with step 17.
- **What moves where:** CI parses `config/app.yaml` and fails the build if a key named `api_key` appears at any depth. Add a test that puts an `api_key` into a copy of the file and confirms the check fails.
- **State:** CI configuration.
- **If it fails:** A failing guard blocks the merge. Do not turn it on before the file is clean (step 17), or it blocks the migration itself.

### 17. Remove the keys from the config file

- **Starts when:** Step 9 is merged. Merge together with step 16, before step 12.
- **What moves where:** Delete the three `api_key` lines from `config/app.yaml`. Leave the other fields in place. The git history still contains the old keys. This is accepted.
- **State:** Repo file.
- **If it is reverted:** The file holds keys again. Step 16 blocks that change from merging.

### 18. Update the deploy notes

- **Starts when:** Steps 12 to 16 are complete.
- **What moves where:** `deploy.md` gets the new read path, the secret paths, the new meaning of readiness, and the local dev setup.
- **State:** Documentation.
- **If it fails:** Documentation drifts from the code. Nothing else is affected.

### 19. Clean up local copies

- **Starts when:** Step 14 is complete.
- **What moves where:** Engineers delete any local copy of the live keys. Local runs use the dev keys from step 7.
- **State:** Developer machines.
- **If it fails:** Stale copies stop working after step 14. They cause failures only in local runs. Production is not affected.

---

## Runtime behavior of the app

### Startup

1. Load the three secrets from `orders-api/<env>/<name>`, using the pod's identity.
2. If the store cannot be reached, retry. The brief says "retry 3 times, 2 seconds apart." This plan reads that as 3 retries after the first attempt, which is 4 attempts in total and about 6 seconds of waiting. Confirm this reading before implementation (open question 6).
3. If any of the three secrets is still missing after the retries, log the error and exit non-zero. The pod never becomes ready.
4. Once all three are loaded, record their version ids in the holder and mark readiness true.

### Refresh

- Every 5 minutes, re-read all three secrets.
- If all three reads succeed, swap the new values into the holder and log the new version ids.
- If any read fails, keep the last good values for all three, log a warning, and leave readiness true.

### Key use

- Clients read the key from the holder on each call.
- A key value is never placed in an environment variable, a file, a log line, or request-logging middleware.

### Failure table

| Situation | Behavior |
|---|---|
| Store unreachable at startup | Retry, then exit non-zero. The rollout halts. |
| Store unreachable on refresh | Keep the last good values and log a warning. The pod stays ready. |
| Store returns a bad value | The loader does not detect this. The provider rejects the key and calls fail. See open question 3. |
| Provider rejects a key (401) | Log and alert. The holder keeps its current value, and the app does not switch keys on its own. The fix is a new store version, which the next refresh picks up. See open question 3. |

---

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan does not set one.
2. **Provider support for two active keys.** Gate A depends on this. It must be answered for each provider before step 3.
3. **Fallback on provider rejection.** Should the app keep the previous store version in memory and retry with it when the provider returns 401? This would cover a bad new value, but it keeps a second copy of the key in memory. Decide before step 4.
4. **Rollback window.** How long must pre-migration images stay deployable? Step 15 must be complete before step 14, so this window closes when step 15 completes, which is before revocation.
5. **Confirmation window.** Step 13 proposes one refresh cycle plus a margin. Confirm the margin.
6. **Retry count.** Confirm whether "retry 3 times" means 3 retries after the first attempt (4 attempts in total) or 3 attempts in total (see Startup, step 2).
7. **Log review.** Should the old keys be checked against provider access logs for the period they were in use, since they are treated as leaked? This is not in the brief and is out of scope unless security asks for it.