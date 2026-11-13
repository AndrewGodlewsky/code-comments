# Plan: move orders-api provider keys into the managed secret store

**Status:** proposed. **Scope:** the payments, email and geocoding keys for `orders-api`.

## Summary

- The new keys are minted and stored first. The old keys stay valid the whole time, so every pod, old or new, always has a working key.
- New code reads the keys from the store. The readiness probe gates on having them, and clients read the key on every request, so a later rotation needs no restart.
- The old keys are revoked only after a per-pod check proves every instance runs on the new versions.
- The CI guard lands with the code change, so it passes from the first merge.

## Assumptions to confirm

- **Two valid keys per provider.** Each provider allows two keys to be valid at once. Step 1 verifies this. If a provider cannot do it, stop: "no customer request fails" cannot be met with this plan.
- **Retry count.** "Retry 3 times, 2 seconds apart" is read as 1 initial attempt plus 3 retries, 4 attempts in all, about 6 seconds before exit.
- **Merge may deploy.** A merge to `main` may auto-deploy, because `deploy.md` does not say. Steps 2 and 3 therefore finish before the merge in step 4.
- **Readiness-only probe.** `/healthz` is used only as the readiness probe. If a liveness probe also targets it, point that probe elsewhere in step 4.

Names used below:
- Secrets: `orders-api/<env>/payments_api_key`, `orders-api/<env>/email_api_key`, `orders-api/<env>/geocoding_api_key`.
- `env` is `prod`, `dev`, and `staging` if that environment exists.
- `V1` is the set of version ids returned when the new prod keys are first written.

---

## Part A: Rollout

### Step 1. Check the providers and inventory the old keys

- **Starts when:** this plan is approved.
- **What moves:** nothing. Security on-call and the owning engineer do this by hand.
  - For each provider, confirm two keys can be valid at once.
  - Confirm how to disable a key (preferred) and how to delete it.
  - Check each provider's usage view for what is currently calling with the old key. List every consumer: the 4 prod replicas, staging if it uses the same image, scheduled jobs, CI, and developer laptops (`make run` uses the live keys today).
- **State lives in:** the provider consoles. Write the inventory in the tracking ticket.
- **If it fails:** a provider that cannot hold two keys, or an unknown consumer, blocks the plan. Stop and escalate. Nothing has changed yet.

### Step 2. Set up the store, KMS keys and access

- **Starts when:** step 1 is done.
- **What moves:** no secret values yet.
  - Create the per-environment KMS keys (prod, dev, and staging if it exists).
  - Create the `orders-api/prod/*` namespace and `orders-api/dev/*`.
  - Grant `orders-api-prod` read on `orders-api/prod/*` and decrypt on the prod KMS key only.
  - Grant write on `orders-api/prod/*` to the security on-call group only.
  - Engineers get no read on prod secrets and no decrypt on the prod KMS key. They get read on `orders-api/dev/*` through their own identities.
- **State lives in:** the store's and KMS's access policies. Keep them as code in the infrastructure repo if one exists.
- **Verify with real calls:**

  | Identity | Expected result |
  |---|---|
  | Engineer | Cannot read `orders-api/prod/*` |
  | `orders-api-prod` | Can read prod, cannot write, cannot read `dev/*` |
  | Security on-call | Can write prod |

- **If it fails:** fix the policy. The app does not depend on any of this yet, so nothing is at risk. Do not continue while any of the three checks gives the wrong answer.

### Step 3. Mint new keys and store them (old keys stay active)

- **Starts when:** step 2 verification passes. The security on-call does this.
- **What moves:**
  - Create a new key at each provider. Pipe each value straight into a store write for `orders-api/prod/<name>`, without saving it to a file or putting it on a command line or in shell history.
  - Record the returned version ids as `V1`.
  - Smoke-test each new key directly against its provider with one harmless authenticated call, for example a read-only lookup. Do not use a call that charges or sends mail.
  - Create sandbox or test keys at each provider and store them under `orders-api/dev/*`.
- **State lives in:**
  - The new keys: the provider (active) and the store (encrypted, version `V1`).
  - The old keys: still active, still in git history and in images.
- **If it fails:**
  - A new key fails its smoke test: delete that key at the provider, mint another and rewrite the secret. The store assigns a new version id, so update `V1`.
  - A write fails: nothing downstream has changed. Retry.
  - Nothing in production has changed at this point.

### Step 4. Merge the code change

- **Starts when:** steps 2 and 3 are complete. This ordering means that even an auto-deploy finds the secrets already in place.
- **What moves:** one PR that contains all of the following.
  - **Secrets module.** The new secrets module behaves as in steps 9 to 13.
  - **Clients.** The three clients stop copying the key at construction. They keep a reference to the secrets module and read the current key on each request. Provider base URLs and timeouts stay in `config/app.yaml`.
  - **Config.** `config/app.yaml` loses all three `api_key` lines. `config_loader.py` no longer touches keys.
  - **Version endpoint.** A new endpoint returns secret names and version ids only, never values. It is served on a cluster-internal path. Confirm that the ingress does not route it publicly.
  - **Local mode.** See step 5.
  - **CI guard.** A job that parses `config/*.yaml` as YAML. It fails if any mapping at any depth has a key named `api_key`, whether the value is empty or not. It parses the file rather than grepping, so a comment cannot trigger it. It is a required status check on `main`.
- **State lives in:** git and the built image. The image contains no key values.
- **Tests that must pass before merge** (use a fake store):
  - Startup retries exactly 4 attempts, spaced 2 seconds apart.
  - Startup then exits non-zero.
  - Readiness is 503 until all three keys are loaded.
  - A failed refresh keeps the last good value and logs a warning.
  - A captured-log test shows no key value in any log line, including error paths and HTTP client debug output.
  - The guard fails on a fixture containing `api_key` and passes on the new `app.yaml`.
- **If it fails:** CI is red, so the change is not merged and nothing is deployed. Fix and re-run.

### Step 5. Local development

- **Starts when:** step 4 merges and a developer pulls it.
- **What moves:**
  - `make run` sets `APP_ENV=local`. Provider base URLs point at local stub servers, which accept any key. No secret is read from anywhere.
  - Optionally, `make run-sandbox` sets `APP_ENV=dev`. The developer's own identity reads `orders-api/dev/*`, which holds sandbox keys.
  - There is no default environment. If `APP_ENV` is missing, the app exits non-zero, so a local run can never fall through to prod paths. Only the prod manifest sets `APP_ENV=prod`.
- **State lives in:** sandbox keys in the store's dev namespace, in memory only. The local stub config is committed and contains no keys.
- **If it fails:** a developer who cannot read dev secrets uses the stubs. Developers never need prod access. If an engineer's identity can read prod, that is a step 2 policy bug, so fix the policy.

### Step 6. Roll out to prod with a canary pause

- **Starts when:** the image from step 4 is deployed (automatically or by hand). Pause the rolling update after the first new pod is ready.
- **What moves:**
  - The new pod starts under `orders-api-prod`, reads the three secrets at version `V1`, and passes readiness. Only then does an old pod stop (`maxUnavailable: 0`).
  - During the rollout the fleet is mixed. Old pods use the old keys from their image and new pods use the new keys from the store. Both are valid, so no request fails for lack of a key.
  - After the first pod is ready, watch it for at least one 5-minute refresh cycle. Check for provider 401 and 403 responses, check that the version endpoint shows `V1`, and check that logs hold version ids but no values. Then resume.
- **State lives in:**
  - Keys: in each new pod's memory.
  - Version ids: in logs and on the version endpoint.
- **If it fails:**
  - A new pod cannot reach the store or never becomes ready: it exits after about 6 seconds, the rollout halts, and the old pods keep serving. Fix the cause and re-run.
  - A new pod is ready but a provider rejects its key: this is the one failure that can hit customers. Roll back at once to the previous image, whose old key is still valid. The step 3 smoke test is the main defence, and the pause limits the exposure to 1 of 4 pods.

### Step 7. Confirm every instance uses the new keys, then revoke the old ones

- **Starts when:** the rollout has finished, with 4 new pods ready and no old-image pod left.
- **What moves:**
  - **Gate (all must hold).**
    - Query the version endpoint on each pod individually, not through the load balancer. Every pod reports `V1` for all three secrets.
    - Every running pod uses the new image (check with `kubectl`).
    - Each provider's usage view shows no calls with the old key for at least one full refresh interval after the last old pod stopped.
    - Every other consumer from the step 1 inventory has been moved or retired.
  - **Revoke.** The security on-call then disables each old key at the provider, one key at a time, watching error rates after each. Delete the key later, once a quiet period has passed.
  - **Rollback.** Remove pre-migration images from the deploy list, because they carry revoked keys. After this point, "rollback" means redeploying an image from step 4 or later.
- **State lives in:**
  - The gate evidence: in the ticket.
  - The key's status: at the provider.
- **If it fails:**
  - Any pod not on `V1`, or any old-key traffic: do not revoke. Find the pod or consumer, and restart it or point it at the store.
  - Errors appear after a revoke: a consumer was missed. Re-enable the key if the provider allows it, which is why disable comes before delete. Otherwise fix forward by pointing the consumer at the store.

### Step 8. Close out

- **Starts when:** all three old keys are revoked.
- **What moves:**
  - Update `deploy.md` to say that secrets come from the store and how local runs work.
  - Open a throwaway PR that adds `api_key` to `config/app.yaml`. Confirm the guard blocks it, then close the PR.
  - Confirm no key value appears in the logs, which are kept for 30 days.
- **State lives in:** the repo and docs. The old keys stay in git history; they are revoked, so they are harmless.
- **If it fails:** if the guard does not block the throwaway PR, fix it before closing the ticket.

---

## Part B: How the app reads keys at runtime

### Step 9. Process start

- **Starts when:** the container starts.
- **What moves:**
  - Read `APP_ENV`. If it is missing or not one of the known values, exit non-zero.
  - Build the secrets module with its three paths `orders-api/<env>/<name>`. Importing modules and building the client singletons read no secrets and make no network calls.
  - Authenticate to the store with the pod's service identity. No credential file or environment variable is involved.
- **State lives in:** nothing yet.
- **If it fails:** a bad or missing `APP_ENV` is an immediate non-zero exit. The pod crash-loops and the rollout halts.

### Step 10. Initial fetch

- **Starts when:** step 9 completes, before the HTTP server listens.
- **What moves:** fetch all three secrets, each as (value, version id). Retry the whole fetch up to 3 more times, 2 seconds apart. Reject any empty or missing value as a failure.
- **State lives in:** one in-memory snapshot, a map from name to (value, version id). It is replaced whole, never edited in place. Its string form masks values.
- **If it fails:**
  - Any secret is still missing after the fourth attempt: log the error class and secret names, exit non-zero, and never start serving.
  - Error messages and logs carry names and version ids only, never values or auth headers.

### Step 11. Readiness

- **Starts when:** step 10 succeeds.
- **What moves:** start the HTTP server. `/healthz` returns 200 only when the snapshot holds all three keys. Before that it returns 503. It never reverts to 503 after the first success.
- **State lives in:** the in-memory snapshot, plus the version endpoint that exposes names and version ids.
- **If it fails:** an unready pod gets no traffic, so the old pods keep serving.

### Step 12. Serving requests

- **Starts when:** each outbound provider call.
- **What moves:** the client reads the current key from the snapshot at call time and puts it in the Authorization header. It never stores the key on `self`. HTTP client debug logging stays off for these clients.
- **State lives in:** the snapshot only. An in-flight request keeps the key it started with.
- **If it fails:** a provider error is handled as today. The key is not logged.

### Step 13. Refresh every 5 minutes

- **Starts when:** a background timer fires, 5 minutes after the previous cycle.
- **What moves:** read each secret's latest version. If the value is non-empty, swap in a new snapshot with the new value and version id. Log "secret refreshed" with the name and the old and new version ids when the version changed.
- **State lives in:** the new snapshot, replacing the old one in a single atomic reference swap.
- **If it fails:**
  - A read fails, or the value is empty: keep the last good value for that secret and log a warning with the name and error class. Try again next cycle.
  - Alert if refreshes keep failing for a long period. A silently stale instance would also hold up the step 7 gate and any later rotation.

---

## Open question: scheduled rotation

Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence. If a schedule is chosen, the design needs no changes:
- Write a new version to the store.
- Instances pick it up within about 5 minutes.
- Run the step 7 gate.
- Revoke the old key.

**Owner:** security. **Needed before:** any recurring rotation job is built.
