# Plan: move orders-api third-party keys to the managed secret store

## Summary

The three live keys (payments, email, geocoding) move out of `config/app.yaml` into the secret store at `orders-api/<env>/<name>`. The app reads them into process memory at startup and refreshes them every 5 minutes. Every key is rotated at its provider. The old keys are revoked only after every running instance confirms it is on the new version. Non-secret config (`base_url`, `timeout_seconds`, `from_address`, `port`, `log_level`) stays in `config/app.yaml`.

Assumptions and gates:

- **Gate A (blocking):** Each provider must allow the old and new key to be active at the same time. If a provider allows only one active key, the "no customer failure" requirement cannot be met as written. Stop and escalate before step 3.
- **Gate B:** The old key is never revoked while any instance, local run, or CI job still uses it (see step 13).

---

## Phase 0: Preparation (no customer impact)

### 1. Inventory consumers and provider capabilities

- **Starts when:** The migration is approved.
- **What moves where:** Nothing moves. Record every reader of the three keys: the three clients (`payments.py`, `email.py`, `geocoding.py`), the `make run` local path, CI jobs that read `config/app.yaml`, and any other service that copies the file. For each provider, record whether two keys can be active at once, whether a sandbox or test key exists, and whether a non-mutating check call exists.
- **State:** A migration checklist (a tracking issue, not a code change).
- **If it fails:** If a provider cannot support two active keys, or a consumer is found that this plan does not cover, stop here. No state has changed.

### 2. Create store paths, KMS keys and IAM

- **Starts when:** Step 1 is complete.
- **What moves where:** Create `orders-api/dev/*` and `orders-api/prod/*` with one KMS key per environment.
  - `orders-api-prod`: read-only on `orders-api/prod/*`, and no other secret or KMS permissions.
  - Security on-call: write on `orders-api/prod/*`.
  - Engineers: no read on `orders-api/prod/*`.
  - Developer identity: read on `orders-api/dev/*` only.
- **State:** The store and KMS policy. Secret values are not yet present.
- **If it fails:** Missing or wrong permissions show up later as startup failures. Test them now: an engineer's read of a prod path must be denied, and `orders-api-prod` must be denied on any other path.

### 3. Obtain dev and test keys

- **Starts when:** Gate A is passed.
- **What moves where:** Create non-production keys at each provider (sandbox or test mode where available) and write them to `orders-api/dev/<name>`.
- **State:** Dev values in the dev store path.
- **If it fails:** Local development is blocked, but production is not affected. Do not use live keys for development.

---

## Phase 1: Code change (merged, not yet promoted to production)

### 4. Add the secret loader

- **Starts when:** Step 2 is complete.
- **What moves where:** A new module (for example `app/secrets.py`) does the following:
  - At startup, it fetches the three secrets from `orders-api/<env>/<name>`. The environment comes from configuration.
  - It holds the values in a process-memory holder. Replacement is atomic: a refresh swaps in the new value only when the full read succeeds.
  - It runs a background refresh every 5 minutes.
  - It logs version ids, never values.
- **State:** Process memory only. No disk cache, no environment variables, no temp files. Store SDK debug logging is disabled, and exception messages are scrubbed of key material.
- **If it fails:** Covered in the runtime section below.

### 5. Change the provider clients

- **Starts when:** Step 4 is written.
- **What moves where:** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in `__init__`. Each call reads the current key from the holder, so a refresh takes effect without a restart. Remove the module-level singletons that read keys at import time. Keep the `base_url` and timeout reads as they are.
- **State:** Same as step 4.
- **If it fails:** If a client is left copying the key, it keeps a stale key until restart. A test must confirm that a refreshed value is used on the next call.

### 6. Gate readiness on the keys

- **Starts when:** Step 5 is written.
- **What moves where:** `GET /healthz` returns 200 only after all three secrets are loaded. Liveness stays a plain "process is up" check. Readiness does not turn false when a later refresh fails.
- **State:** Process memory.
- **If it fails:** Today `/healthz` returns OK as soon as the server listens. If that is not changed, a new pod passes readiness with no keys and customer requests fail. This change is required before any rollout.

### 7. Point local development at the dev store

- **Starts when:** Step 3 is complete.
- **What moves where:** `make run` loads the dev path through the developer's dev-only identity. It does not read the prod path.
- **State:** Process memory. Local copies of `config/app.yaml` contain no keys.
- **If it fails:** A developer cannot run locally until they have dev access. Local runs must not fall back to the live keys.

### 8. Tests

- **Starts when:** Steps 4 to 7 are written.
- **What moves where:** Tests cover:
  - Startup with the store unreachable makes three retries, 2 seconds apart, and then exits non-zero.
  - A refresh failure keeps the last good value and logs a warning.
  - A refreshed value is used on the next call.
  - Readiness is false before load and true after.
  - No key value appears in logs, including when a request fails.
- **State:** Test code only.
- **If it fails:** Do not merge.

### 9. Merge the code, and do not promote it

- **Starts when:** Step 8 passes review.
- **What moves where:** The code merges to `main`, which builds an image. Do not promote that image to production yet. The image still contains `api_key` lines in `config/app.yaml` until step 10, and it must not be promoted before the store holds values (step 11).
- **State:** A built image that is not deployed.
- **If it fails:** Nothing has reached production.

---

## Phase 2: New keys in the store

### 10. Rotate each key at its provider

- **Starts when:** Step 9 is merged.
- **What moves where:** The security on-call creates a new key at each provider. Old keys stay active. The security on-call writes each new key to `orders-api/prod/<name>`, which creates a new version id. Engineers do not see the values.
- **State:** Prod store (new version of each secret), encrypted with the prod KMS key. Old keys are still active at the providers.
- **If it fails:** If a provider call or a store write fails, nothing is in use yet. Retry. Store writes give new version ids, so a partial write is visible and can be repeated. Readiness does not prove the key is valid at the provider. Use a provider check call where one exists (step 1), or rely on the traffic checks in step 13.

---

## Phase 3: Rollout

### 11. Verify that the production identity can read

- **Starts when:** Step 10 is complete.
- **What moves where:** Check that `orders-api-prod` can read all three `orders-api/prod/<name>` paths and nothing else.
- **State:** None changed.
- **If it fails:** Pods would fail at startup and the rollout would halt on readiness, which is safe. Fix the IAM policy and retry. Do not roll out until this passes.

### 12. Rolling deploy of the new image

- **Starts when:** Steps 10 and 11 are complete.
- **What moves where:** Each new pod loads the three secrets, passes readiness, and then an old pod stops (`maxUnavailable: 0`). During the rollout the fleet is mixed: old pods use old keys, new pods use new keys. Both sets are valid because step 10 kept them active.
- **State:** Each pod's memory. The fleet's version state is visible in the pods' version-id logs.
- **If it fails:**
  - A new pod that cannot read the store exits non-zero. It never becomes ready, the rollout halts, and the old pods keep serving.
  - Rollback means redeploying an earlier image. Earlier images still contain the old keys in `config/app.yaml`. They keep working only while the old keys are valid, so rollback is safe until step 15.

### 13. Confirm every instance is on the new version

- **Starts when:** The rollout (step 12) completes.
- **What moves where:** Wait at least one full refresh cycle (5 minutes) plus a margin. Confirm all of the following:
  - Every running pod's latest logged version id is the new one.
  - Old-key usage at each provider has dropped to zero for the whole window. This covers any forgotten consumer, including a local run or a CI job.
- **State:** Logs and provider usage reports.
- **If it fails:** Do not revoke. Investigate any pod still on the old version, or any remaining old-key usage, before continuing.

---

## Phase 4: Revocation and cleanup

### 14. Revoke old keys

- **Starts when:** Step 13 passes for all three providers.
- **What moves where:** The security on-call revokes each old key at its provider.
- **State:** Provider. Revocation cannot be undone.
- **If it fails:** If a consumer still uses the old key, customer requests for that provider fail. This is why step 13 is a hard gate. Do not revoke one provider's key on the basis of another provider's results.

### 15. Block rollback to pre-migration images

- **Starts when:** Step 14 is complete, or the new image has been stable for the agreed window, whichever is first.
- **What moves where:** The deploy pipeline refuses images built before the migration. This keeps a rollback from reintroducing keys in files.
- **State:** Deploy policy.
- **If it fails:** If a rollback is needed after this point, the rollback target must be a post-migration image. Pre-migration images will fail because their keys are revoked.

### 16. CI guard against `api_key` in the config

- **Starts when:** Step 9 is merged. Turn on the guard in the same change that removes `api_key` from `config/app.yaml`.
- **What moves where:** CI parses `config/app.yaml` and fails the build if any key named `api_key` appears at any depth. Add a test that puts an `api_key` into a copy of the file and confirms the check fails.
- **State:** CI configuration.
- **If it fails:** A failing guard blocks the merge. It must not be turned on before the file has been cleaned, or it blocks the migration itself.

### 17. Remove the keys from the config file

- **Starts when:** Step 9 is merged.
- **What moves where:** Delete the three `api_key` lines from `config/app.yaml`. Leave the other fields in place. The commit history still contains the old keys, and that is accepted.
- **State:** Repo file.
- **If it fails:** If the change is reverted, the file again holds keys. Step 16 blocks that from merging.

### 18. Update the deploy notes

- **Starts when:** Steps 12 to 16 are complete.
- **What moves where:** `deploy.md` gets the new read path, the store paths, the readiness meaning, and the local dev setup.
- **State:** Docs.
- **If it fails:** Documentation drift only.

### 19. Clean up local copies

- **Starts when:** Step 14 is complete.
- **What moves where:** Engineers delete any local copy of the live keys. Local runs now use dev keys (step 7).
- **State:** Developer machines.
- **If it fails:** Stale copies are dead after step 14, so they cause failures only in local runs. They do not affect production.

---

## Runtime behavior of the app

### Startup

1. Load the three secrets from `orders-api/<env>/<name>` using the pod's identity.
2. If the store is unreachable, retry 3 times, 2 seconds apart. This plan reads that as three retries after the first attempt, which is four attempts in total. Confirm the intent before implementation.
3. If all three secrets are still not loaded after the retries, log the error and exit non-zero. The pod never becomes ready.
4. Once all three are loaded, record their version ids and mark readiness true.

### Refresh

- Every 5 minutes, re-read all three secrets.
- If all reads succeed, swap the new values into the holder and log the new version ids.
- If any read fails, keep the last good values for all three, and log a warning. Readiness stays true.

### Key use

- Clients read the key from the holder on each call.
- A value is never placed in an environment variable, a file, a log line, or a request-logging middleware.

### Failure table

| Situation | Behavior |
|---|---|
| Store unreachable at startup | Retry, then exit non-zero. Rollout halts. |
| Store unreachable on refresh | Keep last good value, warn. Pod stays ready. |
| Store returns a bad value | Not detected by the loader. The provider rejects it and calls fail. See open question 3. |
| Provider rejects a key (401) | Log and alert. Do not change the holder without a new store version. |

---

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan does not set one.
2. **Provider support for two active keys.** Gate A depends on this. It must be answered per provider before step 3.
3. **Fallback on provider rejection.** Should the app keep the previous store version in memory and retry with it when the provider returns 401? This would cover a bad new value, but it adds a second copy of the key in memory. Decide before step 4.
4. **Rollback window.** How long must pre-migration images stay deployable (step 15)?
5. **Confirmation window.** Step 13 proposes one refresh cycle plus a margin. Confirm the margin.
6. **Log review.** Should the old keys be checked against provider access logs for the period they were in use, given that they are treated as leaked? This is not in the brief and is out of scope unless security asks for it.