# Plan: move orders-api third-party keys into the managed secret store

## Approach in brief

- Old and new keys are both valid at the provider from step 3 until step 10. Old pods keep using the old yaml keys and new pods use the new store keys. Nothing is revoked until every consumer is confirmed on the new keys. This is what keeps customer requests from failing.
- Old pods run the old image unchanged and never read the store, so nothing about them changes before step 10, even if one restarts.
- The store holds only the new, rotated keys. The leaked keys are never copied into it.
- The new image has no key in any file. If it can't read the store it never becomes ready, and `maxUnavailable: 0` keeps the old pods serving with the old keys, which are still valid.
- Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`, stored at `orders-api/<env>/<name>`.
- "Retry 3 times, 2 seconds apart" means 1 initial attempt plus 3 retries, 4 attempts in total.

---

## Part A: Rollout

### 1. Create the store layout, KMS key and access policy

- **Starts when:** the plan is approved. Can run alongside step 2.
- **What moves:** no secret values. Create the paths `orders-api/prod/*` and `orders-api/dev/*`, each environment with its own KMS key.
- **Access:**
  - `orders-api-prod` gets read on `orders-api/prod/*` and decrypt on the prod KMS key, nothing else.
  - Only the security on-call group can write `orders-api/prod/*`.
  - Engineers get no read or decrypt on anything prod, and read on `orders-api/dev/*`.
- **State lives in:** the access policy, kept as infrastructure code in review.
- **If it fails:** nothing consumes it yet, so fix the policy and re-run. The step is done only when these tests pass:
  - An engineer identity is denied a prod read.
  - `orders-api-prod` can read prod but is denied any write.
  - `orders-api-prod` is denied reads on `orders-api/dev/*` and on other apps' paths.

### 2. Inventory every consumer and confirm the providers allow two active keys

- **Starts when:** plan approved. This is a gate for step 3.
- **What moves:** nothing. Record every user of the three live keys: the 4 prod pods, non-prod deployments of the same image, developer laptops running `make run`, CI jobs, and any other service. For each provider, confirm a second key can be active while the old one works, and note whether the provider shows a "last used" time for a key (needed in step 10).
- **State lives in:** the migration ticket.
- **If it fails:**
  - If a provider allows only one active key, zero-downtime rotation is impossible. Stop and escalate for a provider-specific overlap. Do not start step 3 for that provider.
  - An unknown consumer found now is added to the plan. Found at step 10, it would break.

### 3. Issue new keys and write them to the prod store

- **Starts when:** steps 1 and 2 are done.
- **What moves:**
  - The security on-call creates a new key at each provider. The old keys stay active.
  - They write each new key directly into `orders-api/prod/<name>`. The value never goes through chat, tickets, CI variables, shell history or an environment variable.
  - The store returns a version id per write. Record the ids in the ticket, never the values. Step 8 uses them as the expected ids.
  - They check each new key with one authenticated read-only call to its provider.
- **State lives in:** the provider (old and new keys valid) and the store (KMS-encrypted).
- **If it fails:** nothing reads these yet, so retry a failed write. For a wrong value, write a corrected one (new version id, the app reads the latest) and update the ticket. If a new key is exposed anywhere, revoke it and issue another.

### 4. Set up dev, so local runs never touch prod

- **Starts when:** step 1 is done. Must finish before the merge in step 7.
- **What moves:**
  - Put provider sandbox or test keys (not live keys) in `orders-api/dev/*`.
  - `make run` sets `APP_ENV=dev`. The app uses the engineer's own identity to read `orders-api/dev/*`, through the same code path as prod.
  - Add `make run-offline`, which sets `APP_ENV=local` and uses an in-process fake secret source with dummy values and stub provider base URLs. The fake source is refused at startup unless `APP_ENV=local`.
- **State lives in:** the dev store paths and the `make` targets in git.
- **If it fails:** if a provider has no sandbox, dev uses the offline stubs for it. Never fall back to a live key.

### 5. Code change

- **Starts when:** steps 1 and 4 are done. Can be developed in parallel with step 3.
- **What moves:**
  - `config/app.yaml` loses all three `api_key` lines. Base URLs, timeouts and `from_address` stay.
  - Add a secrets module (Part B) that holds the keys in process memory. Only its startup load and refresh talk to the store.
  - `app/clients/*` stop copying the key in `__init__`. On every call they ask the secrets module for the current key, a memory read. The module-level singletons are built at import and would otherwise hold a stale value forever.
  - Importing `config_loader` must no longer need secrets.
  - `/healthz` returns 200 only after startup loading succeeds.
- **State lives in:** git, on a feature branch.
- **If it fails:** these tests must pass before merge, using a fake store and a log-capture fixture:
  - Startup makes 4 attempts, then exits non-zero.
  - Readiness is withheld until all three keys are loaded.
  - A failed refresh keeps the last good value and logs a warning.
  - A search of captured logs, the environment and the temp directory finds no key value.

### 6. CI guard

- **Starts when:** it ships in the same PR as step 5, because it would fail on the current file.
- **What moves:** a CI job parses `config/app.yaml` as YAML and fails if any mapping key named `api_key` appears at any depth, or if the file doesn't parse. It is a required status check on `main`.
- **State lives in:** the CI config in git and branch protection.
- **If it fails:** if the job is flaky or wrong, the PR can't merge, so fix the job. A negative test (a fixture with an `api_key` must fail the job) is part of the PR.

### 7. Merge, then roll out to prod

- **Starts when:** steps 3, 4, 5 and 6 are done, plus a review. **Do not merge before step 3 is finished:** the new image can't become ready without the store keys.
- **What moves:** the new image rolls out one pod at a time with `maxUnavailable: 0`. Each new pod loads its keys (step 12) and becomes ready only when it has all three. Only then is an old pod stopped. Record the new image's digest in the ticket.
- **Check after the first new pod:** the person running the deploy pauses the rollout once the first new pod is ready and makes one authenticated read-only call per provider through that pod. They continue only if all three succeed and the pod's logs show no 401 or 403 from any provider. Otherwise they stop and roll back.
- **State lives in:** pod memory (the keys) and the logs (one `secret_loaded name=… version=…` line per secret).
- **If it fails:** if the first new pod never becomes ready, the rollout halts and the old pods keep serving. Check its error log for a store outage, an access-policy bug or a wrong secret name. Rollback means redeploying the earlier image, which works until step 10 because the old keys are still valid.

### 8. Confirm every instance is on the new keys

- **Starts when:** the rollout has finished.
- **What moves:** nothing. For each of the 4 pods (listed from the cluster at check time), confirm:
  - It runs the image digest recorded in step 7.
  - For each secret, its latest `secret_loaded` or `secret_rotated` log line shows the version id recorded in step 3. A different id means a stuck refresh or a pod that did not restart.

  Also check non-prod deployments and any other consumer found in step 2.
- **State lives in:** the logs (30-day retention), the cluster and the ticket.
- **If it fails:** step 10 does not start. Investigate the instance, and restart it if that is the only fix.

### 9. Bake, then block the old images

- **Starts when:** step 8 passes and a bake period has elapsed (team's choice, at least one business day suggested).
- **What moves:**
  - Mark the pre-migration image tags do-not-deploy, or delete them. After step 10 their keys are revoked, so redeploying one would fail every provider call, and they still contain the leaked keys.
  - Tell developers to use the new `make run`. Their old local config stops working at step 10, which affects only dev.
- **State lives in:** the image registry and deploy tooling.
- **If it fails:** if a rollback is needed during the bake, roll back to the old image and repeat steps 7 to 9 later. Re-run the step 8 check before any revocation.

### 10. Revoke the old keys, one provider at a time

- **Starts when:** the security on-call decides, after re-running the step 8 check just before each revocation.
- **What moves:** revoke the old key at each provider in this order: geocoding, email, payments (lowest impact first, so any surprise shows up there).
- **Gate for each key:** the provider's "last used" for the old key must have stopped advancing for at least 15 minutes (three refresh cycles). If it is still used, find the consumer first. If the provider shows no "last used", use the disable-first method and watch its error rate for a day.
- **Method:** if the provider supports it, disable the key first and delete it after a day with no errors.
- **State lives in:** the provider.
- **If it fails:** if errors appear after a disable, re-enable the old key and find the consumer. A hard delete has no undo, so the gate must pass first.

### 11. Close out

- **Starts when:** all three old keys are revoked.
- **What moves:** update `deploy.md` and the runbook, record the final version ids, and confirm the CI guard is required on `main` and the do-not-deploy marks are in place. Git history is not rewritten, and the leaked keys in it are now dead.
- **If it fails:** leave the ticket open.

---

## Part B: How the app reads keys at runtime (code shipped in step 5)

### 12. Startup load

- **Starts when:** the process starts, before it reports ready.
- **What moves:** the app fetches the latest version of the three secrets from `orders-api/<APP_ENV>/<name>` into process memory. It never pins a version id, so a corrected rewrite from step 3 is picked up. It authenticates as the pod's service identity (`orders-api-prod` in prod), which the platform provides, so no credential is in the image.
- **Retry and exit:** each fetch has its own timeout. If the store can't be reached or a secret is missing, retry up to 3 times, 2 seconds apart. After the fourth failed attempt, log an error naming the secret (never a value) and exit with code 1.
- **Readiness:** `/healthz` returns 503 until all three keys are held, then 200. It makes no provider call, so a provider outage can't block a rollout.
- **State lives in:** process memory.
- **If it fails:** the pod exits and Kubernetes restarts it. During a rollout it never becomes ready, so the old pods keep serving.

### 13. Holding secrets in memory

- Each key is held in a small object that is swapped as a whole, so a request never sees half an update. The object redacts itself when printed.
- Keys go nowhere else: not environment variables, not disk, not logs (including HTTP debug logs and request headers). Only version ids are logged. The pod's environment holds only non-secret settings such as `APP_ENV`.
- Only the startup load and the refresh (step 14) write memory. Requests only read it.
- **State lives in:** process memory. A restart reloads from the store.

### 14. Refresh every 5 minutes

- **Starts when:** a timer fires every 5 minutes after startup.
- **What moves:** for each secret, fetch the latest. If the version id differs from the held one, swap in the new value, keep the old one as "previous" (only one, replaced on the next swap), and log `secret_rotated name=… old_version=… new_version=…`. If it is the same, log `secret_refresh_ok`.
- **State lives in:** process memory.
- **If a re-read fails:** keep using the last good value, log a warning with the secret name and error class, and retry at the next tick. A failed refresh never changes readiness.
- **Alert (added, not in the brief):** the log service alerts the team if a pod logs no `secret_refresh_ok` for 15 minutes, because a pod that can't refresh fails once its old key is revoked.

### 15. Use on each request, and the fallback on a rejected key

- **Starts when:** a client sends a request to a provider.
- **What moves:** the client reads the current key from memory and sends it as today.
- **If the provider rejects the request (401 or 403):** an auth rejection means the provider did not process it, so a retry can't double-charge. The client:
  1. Re-reads that secret from the store, at most once a minute per secret.
  2. If the version changed, retries once with the new value.
  3. Otherwise retries once with the previous value, if held.
  4. Otherwise, or if the retry also fails, returns the original failure.
- The customer request waits during this, for at most one store read and one retry, each within its timeout.
- **Why it exists:** a safety net for the requirement that no request fail because of a missing or revoked key. It is my addition, so confirm it is wanted.

### 16. Later rotations use the same mechanism

A rotation is steps 3, 8 and 10 again. The security on-call writes a new key to the store, every instance swaps within 5 minutes, the logged version ids confirm it, then the old key is revoked. No restart or redeploy is needed.

---

## Open questions

- **Scheduled rotation (not decided, not planned here).** Security has not decided whether keys must also be rotated on a schedule, or how often. This plan sets no cadence. If they decide yes, step 16 is the mechanism, and a cadence and an owner need to be added.

Assumptions to confirm:

- Each provider allows two active keys at once (gate in step 2) and shows a "last used" time (otherwise step 10 relies on disable-first).
- How a pod proves its identity to the store (for example platform workload identity) is not specified in the brief.
- The bake length in step 9.
- Authenticated read-only calls exist for the smoke checks in steps 3 and 7.
- Each provider offers a sandbox key, or the offline stubs are acceptable for dev.
- The retry-on-rejection behaviour in step 15 is wanted.
- The log service can raise the missing-refresh alert in step 14.
- The deploy tooling or registry can enforce do-not-deploy on image tags in step 9.
