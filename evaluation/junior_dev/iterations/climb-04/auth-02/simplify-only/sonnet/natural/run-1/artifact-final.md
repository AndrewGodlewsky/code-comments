# Plan: move orders-api provider keys into the managed secret store

**Status:** proposed. **Scope:** the payments, email and geocoding keys for `orders-api`.

## What this is

Today the three provider keys sit in `config/app.yaml`. That file is committed to git, copied into every container image, and read once at process start. Each client copies its key at construction, so changing a key means a new image and a redeploy.

This plan moves the keys into the managed secret store. New keys are minted and stored first, while the old keys stay valid, so every pod always has a working key. New code fetches the keys at startup, refreshes them every 5 minutes, and reads the current key on every request. The old keys are revoked only after every pod is confirmed to use the new ones.

## Terms

- **Store:** the managed secret store. It encrypts each secret with a per-environment KMS key and gives every write a new version id.
- **Secret names:** `orders-api/<env>/payments_api_key`, `orders-api/<env>/email_api_key`, `orders-api/<env>/geocoding_api_key`. `env` is `prod`, `dev`, or `staging` if that environment exists.
- **Snapshot:** the in-memory map from secret name to (value, version id). It is replaced whole, never edited in place.
- **V1:** the version ids returned when the new prod keys are first written.
- **Version endpoint:** a cluster-internal endpoint that returns secret names and version ids, never values.
- **Security on-call:** the only group that can write prod secrets.

## Assumptions to confirm

- **Two valid keys per provider.** Step 1 verifies this. If a provider cannot do it, stop: "no customer request fails" cannot be met.
- **Retry count.** "Retry 3 times, 2 seconds apart" means 1 attempt plus 3 retries, 4 attempts, about 6 seconds before exit.
- **Merge may deploy.** `deploy.md` does not say whether a merge auto-deploys, so steps 2 and 3 finish before the merge in step 4.
- **Readiness-only probe.** `/healthz` is only the readiness probe. If a liveness probe also uses it, point that probe elsewhere in step 4.

---

## Part A: Rollout (how we get there)

### Step 1. Check the providers and inventory the old keys

- **Starts when:** this plan is approved.
- **What it does:** security on-call and the owning engineer, by hand:
  - Confirm each provider allows two valid keys, and how to disable a key (preferred) and delete it.
  - Use each provider's usage view to list every consumer of the old key: the 4 prod replicas, staging, scheduled jobs, CI, and developer laptops (`make run` uses the live keys today).
- **Data lives in:** the provider consoles. The inventory goes in the tracking ticket.
- **If it goes wrong:** a provider with only one key slot, or an unknown consumer, blocks the plan. Stop and escalate. Nothing has changed yet.

### Step 2. Set up the store, KMS keys and access

- **Starts when:** step 1 is done.
- **What it does:** no secret values yet.
  - Create the per-environment KMS keys and the `orders-api/prod/*` and `orders-api/dev/*` namespaces.
  - Grant `orders-api-prod` read on `orders-api/prod/*` and decrypt on the prod KMS key only.
  - Grant write on `orders-api/prod/*` to the security on-call group only.
  - Engineers get no read on prod and no decrypt on the prod KMS key. They get read on `orders-api/dev/*` through their own identities.
- **Data lives in:** the store and KMS access policies, kept as code in the infrastructure repo if one exists.
- **Verify with real calls:** an engineer cannot read prod; `orders-api-prod` can read prod, cannot write, and cannot read `dev/*`; security on-call can write prod.
- **If it goes wrong:** fix the policy. The app does not use any of this yet, so nothing is at risk. Do not continue until all three checks give the right answer.

### Step 3. Mint new keys and store them (old keys stay active)

- **Starts when:** step 2 verification passes. Security on-call does this.
- **What it does:**
  - Create a new key at each provider. Pipe each value straight into a store write for `orders-api/prod/<name>`, never to a file, command line or shell history. Record the returned version ids as `V1`.
  - Smoke-test each new key against its provider with one harmless authenticated call, such as a read-only lookup. Never use a call that charges or sends mail.
  - Create sandbox keys at each provider and store them under `orders-api/dev/*`.
- **Data lives in:** the new keys are active at the provider and encrypted in the store (version `V1`). The old keys are still active, and still in git history and images.
- **If it goes wrong:** if a new key fails its smoke test, delete it, mint another and rewrite the secret. The store gives a new version id, so update `V1`. If a write fails, retry. Production is unchanged either way.

### Step 4. Merge the code change

- **Starts when:** steps 2 and 3 are complete, so even an auto-deploy finds the secrets in place.
- **What it does:** one PR containing:
  - **Secrets module** that behaves as in steps 9 to 13.
  - **Clients** that stop copying the key at construction and read the current key from the secrets module on each request. Base URLs and timeouts stay in `config/app.yaml`.
  - **Config:** `config/app.yaml` loses all three `api_key` lines, and `config_loader.py` no longer touches keys.
  - **Version endpoint**, served on a cluster-internal path. Confirm the ingress does not route it publicly.
  - **Local mode**, described in step 5.
  - **CI guard:** a job that parses `config/*.yaml` and fails if any mapping at any depth has a key named `api_key`, empty or not. It parses rather than greps, so comments cannot trigger it. It is a required status check on `main`.
- **Data lives in:** git and the built image. The image holds no key values.
- **Tests that must pass before merge** (with a fake store):
  - Startup makes exactly 4 attempts, 2 seconds apart, then exits non-zero.
  - Readiness is 503 until all three keys are loaded.
  - A failed refresh keeps the last good value and logs a warning.
  - A captured-log test finds no key value in any log line, including error paths and HTTP client debug output.
  - The guard fails on a fixture containing `api_key` and passes on the new `app.yaml`.
- **If it goes wrong:** CI is red, so nothing merges or deploys. Fix and re-run.

### Step 5. Local development

- **Starts when:** step 4 merges and a developer pulls it.
- **What it does:**
  - `make run` sets `APP_ENV=local`. Provider base URLs point at local stub servers that accept any key. No secret is read.
  - Optionally, `make run-sandbox` sets `APP_ENV=dev`. The developer's own identity reads the sandbox keys in `orders-api/dev/*`.
  - There is no default `APP_ENV`. If it is missing, the app exits non-zero, so a local run can never fall through to prod. Only the prod manifest sets `APP_ENV=prod`.
- **Data lives in:** sandbox keys in the store's dev namespace, held in memory only. The stub config is committed and has no keys.
- **If it goes wrong:** a developer who cannot read dev secrets uses the stubs. Developers never need prod access. If an engineer can read prod, that is a step 2 policy bug.

### Step 6. Roll out to prod with a canary pause

- **Starts when:** the step 4 image is deployed, automatically or by hand. Pause the rolling update after the first new pod is ready.
- **What it does:**
  - The new pod starts under `orders-api-prod`, reads the three secrets at `V1`, and passes readiness. Only then does an old pod stop.
  - During the rollout, old pods use the old keys from their image and new pods use the new keys from the store. Both are valid, so no request fails for lack of a key.
  - After the first pod is ready, watch it for at least one 5-minute refresh cycle. Check for provider 401 and 403 responses, that the version endpoint shows `V1`, and that logs hold version ids but no values. Then resume.
- **Data lives in:** keys in each new pod's memory. Version ids in logs and on the version endpoint.
- **If it goes wrong:**
  - A new pod cannot reach the store or never becomes ready: it exits after about 6 seconds, the rollout halts, and old pods keep serving. Fix the cause and re-run.
  - A new pod is ready but a provider rejects its key: this is the one failure that can hit customers. Roll back at once to the previous image, whose old key is still valid. The step 3 smoke test is the main defence, and the pause limits exposure to 1 of 4 pods.

### Step 7. Confirm every instance uses the new keys, then revoke the old ones

- **Starts when:** the rollout has finished, with 4 new pods ready and no old-image pod left.
- **What it does:**
  - **Gate (all must hold):**
    - Querying the version endpoint on each pod individually, not through the load balancer, shows `V1` for all three secrets.
    - `kubectl` shows every running pod on the new image.
    - Each provider's usage view shows no old-key calls for at least one full refresh interval after the last old pod stopped.
    - Every other consumer from the step 1 inventory has been moved or retired.
  - **Revoke:** security on-call disables each old key at the provider, one at a time, watching error rates after each. Delete a key later, after a quiet period.
  - **Rollback list:** remove pre-migration images from the deploy list, since they carry revoked keys. From now on, rollback means redeploying an image from step 4 or later.
- **Data lives in:** the gate evidence in the ticket. The key status at the provider.
- **If it goes wrong:**
  - Any pod not on `V1`, or any old-key traffic: do not revoke. Find the pod or consumer and restart it or point it at the store.
  - Errors after a revoke mean a consumer was missed. Re-enable the key if the provider allows it (which is why disable comes before delete). Otherwise point the consumer at the store.

### Step 8. Close out

- **Starts when:** all three old keys are revoked.
- **What it does:**
  - Update `deploy.md` to say secrets come from the store and how local runs work.
  - Open a throwaway PR that adds `api_key` to `config/app.yaml`. Confirm the guard blocks it, then close it.
  - Confirm no key value appears in the logs, which are kept for 30 days.
- **Data lives in:** the repo and docs. The old keys stay in git history but are revoked, so they are harmless.
- **If it goes wrong:** if the guard does not block the throwaway PR, fix it before closing the ticket.

---

## Part B: How the app reads keys at runtime

### Step 9. Process start

- **Starts when:** the container starts.
- **What it does:**
  - Read `APP_ENV`. If it is missing or not a known value, exit non-zero.
  - Build the secrets module with its three paths. Importing modules and building client singletons read no secrets and make no network calls.
  - Authenticate to the store with the pod's service identity. No credential file or environment variable is involved.
- **Data lives in:** nothing yet.
- **If it goes wrong:** a bad `APP_ENV` is an immediate non-zero exit. The pod crash-loops and the rollout halts.

### Step 10. Initial fetch

- **Starts when:** step 9 completes, before the HTTP server listens.
- **What it does:** fetch all three secrets as (value, version id). If any fetch fails, or a value is empty, retry the whole fetch up to 3 more times, 2 seconds apart.
- **Data lives in:** the snapshot. Its string form masks values.
- **If it goes wrong:** if any secret is still missing after the fourth attempt, log the error class and secret names, exit non-zero, and never serve. Errors and logs carry names and version ids only, never values or auth headers.

### Step 11. Readiness

- **Starts when:** step 10 succeeds.
- **What it does:** start the HTTP server. `/healthz` returns 200 only when the snapshot holds all three keys, and 503 before that. It never goes back to 503 after the first success.
- **Data lives in:** the snapshot, and the version endpoint that exposes names and version ids.
- **If it goes wrong:** an unready pod gets no traffic, so old pods keep serving.

### Step 12. Serving requests

- **Starts when:** the app makes an outbound provider call.
- **What it does:** the client reads the current key from the snapshot at call time and puts it in the Authorization header. It never stores the key on `self`. HTTP client debug logging stays off for these clients.
- **Data lives in:** the snapshot only. An in-flight request keeps the key it started with.
- **If it goes wrong:** a provider error is handled as today. The key is never logged.

### Step 13. Refresh every 5 minutes

- **Starts when:** a background timer fires, 5 minutes after the previous cycle.
- **What it does:** read each secret's latest version. If the value is non-empty, swap in a new snapshot with the new value and version id, in one atomic reference swap. When a version changed, log "secret refreshed" with the name and the old and new version ids.
- **Data lives in:** the new snapshot, which replaces the old one.
- **If it goes wrong:** if a read fails or the value is empty, keep the last good value for that secret, log a warning with the name and error class, and try again next cycle. Alert if refreshes keep failing for a long time, because a stale instance would also hold up the step 7 gate and any later rotation.

---

## Open question: scheduled rotation

Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence. If a schedule is chosen, the design needs no changes: write a new version to the store, wait about 5 minutes for instances to pick it up, run the step 7 gate, then revoke the old key.

**Owner:** security. **Needed before:** any recurring rotation job is built.
