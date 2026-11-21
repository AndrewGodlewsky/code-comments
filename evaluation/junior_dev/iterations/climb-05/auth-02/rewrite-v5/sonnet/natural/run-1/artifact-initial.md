# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

The three live keys (payments, email, geocoding) leave `config/app.yaml` and the container image. They live in the secret store as `orders-api/<env>/<name>`. The app loads them into memory at startup, reports ready only once it has all three, and re-reads them every 5 minutes.

Because the old keys are treated as leaked, each one is replaced with a new key at its provider. The old key is revoked only after every running instance is confirmed to be using the new one.

Customer requests never see a missing or revoked key, because of this ordering:

1. New keys are created and verified while the old keys stay valid.
2. The new image rolls out. Old and new pods work side by side.
3. Revocation happens last.

Today `/healthz` is "ok" as soon as the server is listening. After this change it is ready only once the keys are loaded.

Secret names: `payments_api_key`, `email_api_key`, `geocoding_api_key`.

## Assumptions to confirm in Step 1

- Each provider allows two active keys at once. If one does not, stop at Step 1 and escalate. Without overlap, there is no way to rotate that key with zero failed requests.
- Each provider offers some harmless authenticated call that validates a key without side effects (no charge, no email sent).
- No other environment or tool (staging, scripts, cron jobs) uses these three keys. If one does, it goes into Step 14's confirmation list before any revoke.

## Open question (not decided, do not implement)

**Regular rotation schedule.** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan sets no cadence and adds no scheduled rotation job. The runtime design (Steps 5 to 8) and the manual procedure (Step 17) already support rotation at any cadence, so the decision does not block this work. Owner: security. Needed: a yes or no, and if yes, an interval.

## Roles

- **Platform engineer** (platform): creates store paths and policies, and ships the code and rollout.
- **Security on-call** (security): the only role that writes prod secrets or touches provider consoles.
- **Engineers** (eng): cannot read prod values.

---

## Phase 0: Preconditions

### Step 1. Check provider capabilities and find every consumer of the keys

- **Starts when:** this plan is approved.
- **What moves:** nothing. This is read-only checking.
  - For each provider, security confirms that two keys can be active at once and that a harmless validation call exists. They also note whether a key can be suspended before it is deleted.
  - Platform searches for other consumers of the three keys: other environments, scripts, CI jobs.
  - Platform also searches the 30-day central logs for the key formats (`pk_live_`, `ml_live_`, `geo_live_`), to learn whether any key ever reached logs.
- **State lives in:** the migration ticket (findings only, never key values).
- **If it fails:** any provider without key overlap, or any unknown consumer, blocks the plan. Later steps do not start until it is resolved or the plan is changed. A log hit does not block the plan. It is recorded as extra exposure, and the revoke in Step 15 is the remedy.

## Phase 1: Store and access

### Step 2. Create the store paths, KMS keys and policies

- **Starts when:** Step 1 is complete.
- **What moves:** platform creates, in the secret store:
  - A prod namespace `orders-api/prod/*`, encrypted with the prod KMS key.
  - A dev namespace `orders-api/dev/*`, encrypted with a separate dev KMS key.
- **Policies:**
  - `orders-api-prod`: read-only on `orders-api/prod/*`, nothing else, including no list or read access to other paths.
  - Prod write: the security on-call group only.
  - Engineers: no access to `orders-api/prod/*` at all. They get read access to `orders-api/dev/*` only.
- **State lives in:** store and IAM configuration, kept as infrastructure code and reviewed.
- **Verify before moving on** (record the results in the ticket):
  - An engineer identity is denied a read of `orders-api/prod/*`.
  - The `orders-api-prod` identity is denied a write, and denied a read of `orders-api/dev/*`.
  - The security on-call identity can write.
- **If it fails:** a failed negative test means the policy is too broad. Fix it and re-test. Nothing depends on this step yet, so the cost of a failure is only delay.

## Phase 2: Create and verify the new keys (old keys stay valid)

### Step 3. Security creates new keys and writes them to the store

- **Starts when:** Step 2's checks pass.
- **What moves:** for each of the three providers, the security on-call creates a new key at the provider. The old key is left active. The new value goes straight from the provider console into the store as `orders-api/prod/<name>`. It never goes into a ticket, chat message, file or environment variable. Each write returns a version id, and security records only the version ids in the ticket.
- **State lives in:**
  - New key: at the provider and in the store (encrypted).
  - Old key: still in git history, `config/app.yaml`, and the running images.
  - The ticket holds version ids only.
- **If it fails:**
  - A store write error: nothing depends on the new key. Retry the write, or revoke that new key at the provider and start over.
  - A mistyped value is caught in Step 4.

### Step 4. Prove each new key works, using the prod identity

- **Starts when:** Step 3 is complete for a key.
- **Why this step exists:** readiness (Step 6) only checks that a key is present, not that it is valid. A bad key would still pass readiness and then fail real requests, so it must be caught before the rollout.
- **What moves:** platform runs a one-off job under the `orders-api-prod` identity. The job reads the three secrets from the store, makes the provider's harmless validation call with each one, and prints only pass or fail plus the version id. It never prints a value, and the key stays in the job's memory. This also proves the prod identity can read exactly what it needs.
- **State lives in:** the job's memory, which is discarded when it exits. The result goes in the ticket.
- **If it fails:**
  - A provider rejects the key: security re-enters or re-creates that key (a new store version) and the job runs again.
  - A permission denied: this is a policy bug. Return to Step 2.
  - No customer is affected, because nothing live uses the new keys yet.

## Phase 3: Code change (one PR, merged as one unit)

The PR needs one change set because the loader, the clients and the YAML edit depend on each other. For example, removing `api_key` from the YAML while the old loader still reads it would crash on start.

### Step 5. Startup load of secrets

- **Starts when:** the process starts, before the HTTP server begins reporting ready.
- **What moves:** a new `SecretStore` module reads the latest version of the three secrets from `orders-api/<APP_ENV>/<name>`.
  - **Environment name:** `APP_ENV` is required, with no default. The app exits if it is unset, so a missing setting can never load the wrong environment's keys. This is the only environment variable involved, and it carries no secret.
  - **Retries:** if the store is unreachable or returns an error, the app tries again 3 times, 2 seconds apart (1 initial attempt plus 3 retries, 4 attempts, about 6 seconds of waiting).
  - **All or nothing:** all three must load. Non-empty values are checked.
  - **Success:** the values go into an in-memory `SecretCache`, a single object holding the three current values. The app logs the secret names and version ids only.
  - `app/config_loader.py` keeps loading the non-secret settings (`base_url`, timeouts, and so on) from `config/app.yaml`. Importing it no longer needs any key.
- **State lives in:** process memory only. Nothing is written to disk, environment variables or logs.
- **If it fails:** after the retries the app logs an error naming the secret and the error class (never a value) and exits with a non-zero code. In production the pod never becomes ready, so the rolling deploy halts and the old pods keep serving (see Step 12).

### Step 6. Readiness gate

- **Starts when:** Kubernetes calls `GET /healthz`.
- **What moves:** `/healthz` returns 503 until Step 5 has loaded all three keys, then returns 200 `{"status": "ok"}`. After that it keeps returning 200 even if later refreshes fail (Step 8). A secret-store outage must not take healthy pods out of service.
- **State lives in:** one in-memory "keys loaded" flag.
- **If it fails:** a pod that never gets its keys never gets traffic.
- **Also added:** a cluster-internal endpoint, not exposed to customers, returns the three current version ids (never values). Step 14 uses it.

### Step 7. Clients read the key per request

- **Starts when:** any outbound call by `PaymentsClient`, `EmailClient` or `GeocodingClient`.
- **What moves:** today each client copies its key into `self._key` at construction, so a refreshed key would never be seen. After the change, the clients keep only `base_url` and similar settings from `settings`. On every call they ask `SecretCache` for the current key (for example `secrets.get('payments_api_key')`) and build the `Authorization` header from it. The module-level singletons can stay, because they no longer hold a key.
- **State lives in:** `SecretCache` (memory) only. A request already in flight when a swap happens finishes with the key it started with.
- **If it fails:** after Step 6, the cache always holds a value, so a missing key cannot happen on the request path. A provider rejecting a key shows up as a normal provider error, not a startup failure.

### Step 8. Five-minute refresh

- **Starts when:** a background timer fires every 5 minutes after startup.
- **What moves:** the timer re-reads the latest version of each secret from the store. If a value is non-empty and has a new version id, it replaces the cached value (an atomic swap of the cache entry). The app logs the secret name and new version id when it changes, never the value. A new version written by security is therefore used by every running pod within about 5 minutes, with no restart.
- **State lives in:** process memory.
- **If it fails:**
  - A failed or empty read for a secret leaves the last good value in place and logs a warning with the secret name and error class. The next timer tick tries again.
  - A failure for one secret does not block the others.
  - Suggested addition (not a requirement): alert if the same secret has warned on several consecutive ticks, so a long outage does not go unnoticed. The threshold is a team choice.
  - A pod that restarts during a store outage cannot start (Step 5). This is accepted. The rest of the fleet keeps serving on cached values.

### Step 9. Local development without prod access

- **Starts when:** a developer runs `make run`.
- **What moves:** `make run` sets `APP_ENV=local`, and the same `SecretStore` code reads `orders-api/dev/*` using the developer's own identity. The dev paths hold the providers' sandbox or test keys, created by security in the same way as Step 3, but never live keys. For a provider with no sandbox, `make run` uses a local fake client for that provider instead.
- **State lives in:** the dev store, plus developer process memory. No key file is created, and nothing is stored on a laptop.
- **If it fails:** with `APP_ENV=prod` on a laptop, the store denies the read (Step 2), so the app exits and prod values stay unreachable. A developer without dev access either gets added to the dev group or uses the fakes.

### Step 10. Remove the keys from the repo and add the CI guard

- **Starts when:** the PR is opened (the CI job runs on every PR and every push to `main`).
- **What moves:**
  - The three `api_key:` lines come out of `config/app.yaml`, so the committed file and the image hold no keys.
  - A CI check parses `config/app.yaml` and fails the build if any `api_key` key appears at any depth. It also fails on any text match of `api_key` in that file, so a commented-out copy is caught too. It is marked a required status check on `main`, so it blocks merges.
  - The check is added in this same PR, because it would fail on the current file if added earlier.
- **State lives in:** the repo and branch protection settings.
- **If it fails:** the check fails the PR with a message naming the line. The fix is to move the key to the store.

## Phase 4: Rollout

### Step 11. Merge and build

- **Starts when:** the PR is reviewed, CI is green, and Steps 2 to 4 are complete.
- **What moves:** merge to `main` triggers the normal image build. The new image has no keys in it.
- **State lives in:** the image registry.
- **If it fails:** a failed build leaves production unchanged. Fix and rebuild.

### Step 12. Deploy with a canary pause

- **Starts when:** the new image is built and the deploy begins (rolling, one pod at a time, `maxUnavailable: 0`).
- **What moves:** the first new pod starts, loads keys from the store (Step 5), passes `/healthz` (Step 6), and takes traffic. Platform pauses the rollout here for a short check:
  - The pod reports the version ids recorded in Step 3.
  - Provider error rates for that pod are normal.
  - Logs show no warnings, and no key values appear in them.
- **State lives in:** the cluster. 3 old pods are serving on the old keys and 1 new pod on the new keys. Both sets of keys are valid at the provider, so both work.
- **If it fails:**
  - The new pod cannot reach the store, or its pod crashes (Step 5): it never becomes ready, the rollout halts, and the old pods keep serving.
  - A new pod serves but shows provider errors: roll back by redeploying the previous image. This is safe at this stage because the old keys are still valid.

### Step 13. Finish the rollout

- **Starts when:** the canary check in Step 12 passes.
- **What moves:** the rollout resumes and replaces the remaining 3 pods one at a time, each passing `/healthz` before an old pod stops.
- **State lives in:** the cluster, until all 4 pods run the new image.
- **If it fails:** a pod that never becomes ready halts the rollout with old pods still serving. Fix the cause and continue, or roll back as in Step 12.

### Step 14. Confirm every instance uses the new keys (gate for revoking)

- **Starts when:** the rollout is complete.
- **What moves:** nothing. Platform checks, for every running pod:
  - The pod runs the post-migration image.
  - Its internal version endpoint (Step 6) reports exactly the version ids recorded in Step 3, for all three keys.
  - The startup or change log lines for that pod show the same ids.
  - The pod list is compared against the current pod count, so a pod that is not responding is not skipped.
  - Any other consumer found in Step 1 has also been moved.
  - Where the provider shows "last used" for the old key, it confirms no recent use.
- **State lives in:** the ticket, with one line per key per pod (version id only).
- **If it fails:** any pod on a different version id, or any unconfirmed consumer, means no revoke. Wait one refresh cycle (5 minutes) and check again. Investigate if it persists. Old keys stay valid meanwhile, so no customer is affected.

## Phase 5: Revoke and clean up

### Step 15. Revoke the old keys

- **Starts when:** Step 14 is complete and recorded for a key, and security on-call approves.
- **What moves:** security revokes the old key at its provider, one provider at a time, then watches that provider's error rate before moving to the next. If the provider can suspend rather than delete, suspend first and delete after a quiet period. A suspension can be undone, and a delete cannot.
- **State lives in:** the provider and the ticket (the date, who revoked, which key).
- **If it fails:**
  - Provider 401 errors appear after a revoke: first check whether the source is a pod (it should not be) or a forgotten consumer. If the key was suspended, restore it, fix the consumer, and repeat Step 14.
  - A deleted key cannot be restored. This is why the confirmation in Step 14 is the gate.

### Step 16. Stop the old images being redeployed

- **Starts when:** Step 15 is complete for all three keys.
- **What moves:** rollback means redeploying an earlier image. Images built before this change contain the old (now revoked) keys and would fail every request. Platform removes them from the registry or blocks them from deploy, and updates `deploy.md` to say that rollback is only to images built from this change or later. This also removes the old keys from images, though they remain in git history and are already revoked.
- **State lives in:** the image registry and `docs`.
- **If it fails:** the keys are already dead, so a stray old image is a rollback hazard rather than a leak. The step is complete when no pre-migration image can be deployed.

### Step 17. Standing procedure for any future rotation

- **Starts when:** security decides to rotate a key (for example after an incident). Any schedule is the open question above.
- **What moves:** the same path as Steps 3 to 15, minus the code change:
  1. Create the new key at the provider, with the old one still active.
  2. Write it to the store, which creates a new version id.
  3. Pods pick it up within about 5 minutes (Step 8).
  4. Confirm every pod reports the new version id (Step 14).
  5. Revoke the old key (Step 15).
- **State lives in:** the store (versions), providers and the ticket.
- **If it fails:**
  - A pod keeps the last good key if a refresh fails (Step 8), so the old key must stay active until every pod is confirmed.
  - A bad new key shows up as provider errors, so validate it before writing (as in Step 4).

## Done when

- All three old keys are revoked at their providers, with Step 14 evidence for each.
- `config/app.yaml` and the image hold no keys, and the CI guard is required on `main`.
- `/healthz` reports ready only after the keys are loaded.
- Engineers are confirmed unable to read prod values, and `make run` works from dev secrets or fakes.
- The rotation-cadence question is still recorded as open with security.
