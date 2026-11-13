# Plan: move orders-api third-party keys into the managed secret store

## Approach in brief

- Old and new keys are both valid at the provider from step 3 until step 10. Nothing is revoked until every consumer is confirmed on the new keys. This is what keeps customer requests from failing.
- The store only ever holds the new, rotated keys. The leaked keys are never copied into it.
- The new image has no key in any file, so it cannot start without the store. If it can't read the store, it never becomes ready. `maxUnavailable: 0` then keeps the old pods serving with the old keys, which are still valid at that point.
- Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`, stored at `orders-api/<env>/<name>`.
- "Retry 3 times, 2 seconds apart" is read as 1 initial attempt plus 3 retries, so 4 attempts in total.

---

## Part A: Rollout

### 1. Create the store layout, KMS key and access policy

- **Starts when:** the plan is approved. Nothing depends on this yet, so it can run alongside step 2.
- **What moves:** no secret values move yet. Create the paths `orders-api/prod/*` and `orders-api/dev/*`, each environment with its own KMS key. The store encrypts at rest and assigns a new version id on every write.
- **Access:**
  - `orders-api-prod` gets read on `orders-api/prod/*` and decrypt on the prod KMS key. It gets nothing else.
  - Only the security on-call group gets write on `orders-api/prod/*`.
  - Engineers get no read or decrypt on anything prod.
  - Engineers get read on `orders-api/dev/*`.
- **State lives in:** the access policy, kept as infrastructure code in review.
- **If it fails:** nothing consumes it yet, so fix the policy and re-run. The step is done only when these tests pass:
  - An engineer identity is denied a prod read.
  - `orders-api-prod` can read prod but is denied any write.
  - `orders-api-prod` is denied reads on `orders-api/dev/*` and on other apps' paths.

### 2. Inventory every consumer of the current keys and confirm the providers allow two active keys

- **Starts when:** plan approved. This is a gate for step 3.
- **What moves:** nothing. Record every place that uses the three live keys:
  - the 4 prod pods
  - any non-prod deployment of the same image
  - developer laptops running `make run`
  - CI jobs
  - any other service
  Then confirm for each provider (payments, email, geocoding) that a second key can be active while the old one still works.
- **State lives in:** the migration ticket.
- **If it fails:**
  - If a provider allows only one active key, zero-downtime rotation is impossible. Stop and escalate for a provider-specific overlap, such as a support-granted second slot. Do not proceed to step 3 for that provider.
  - An unknown consumer found now is added to the plan. Found at step 10, it would break when the old key is revoked.

### 3. Issue new keys and write them to the prod store

- **Starts when:** steps 1 and 2 are done.
- **What moves:**
  - The security on-call creates a new key at each provider. The old keys stay active.
  - They write each new key directly into `orders-api/prod/<name>`. The value never goes through chat, tickets, CI variables, shell history or an environment variable.
  - The store returns a version id for each write. Record the ids, never the values.
  - The security on-call also checks each new key against its provider with one authenticated read-only call.
- **State lives in:** the provider (old and new keys both valid) and the store (version 1 of each secret, KMS-encrypted).
- **If it fails:**
  - If a write fails, retry it. Nothing reads these yet.
  - If a wrong value was written, write a corrected value. That creates a new version id, and the app reads the latest.
  - If a new key is exposed anywhere, revoke that new key at the provider and issue another. Nothing uses it yet, so this costs nothing.

### 4. Set up dev, so local runs never touch prod

- **Starts when:** step 1 is done. This must be finished before the code merges in step 6.
- **What moves:**
  - Put provider sandbox or test keys in `orders-api/dev/*`. These must not be live keys.
  - `make run` sets `APP_ENV=dev`. The app uses the engineer's own identity to read `orders-api/dev/*`, through the same code path as prod.
  - Add `make run-offline`, which sets `APP_ENV=local` and uses an in-process fake secret source with dummy values, plus stub provider base URLs.
  - The fake source is refused at startup unless `APP_ENV=local`.
- **State lives in:** the dev store paths, plus the `make` targets in git.
- **If it fails:** if a provider has no sandbox, dev uses the offline stubs for that provider. Do not fall back to a live key.

### 5. Code change

- **Starts when:** steps 1 and 4 are done. It can be developed in parallel with step 3.
- **What moves:**
  - `config/app.yaml` loses all three `api_key` lines. Base URLs, timeouts and `from_address` stay.
  - Add a secrets module whose behaviour is described in Part B.
  - `app/clients/*` stop copying the key in `__init__`. They fetch the current key from the secrets module on every call, since the module-level singletons are built at import and would otherwise hold a stale value forever.
  - Importing `config_loader` must no longer need secrets.
  - `/healthz` returns 200 only after startup loading succeeds.
- **State lives in:** git, on a feature branch.
- **If it fails:** the tests below must pass before merge. They use a fake store and a log-capture fixture.
  - Startup makes 4 attempts, then exits non-zero.
  - Readiness is withheld until all three keys are loaded.
  - A failed refresh keeps the last good value and logs a warning.
  - A search of captured logs, the environment and the temp directory finds no key value.

### 6. CI guard

- **Starts when:** it ships in the same PR as step 5. The guard would fail on the current file, so it must land together with the key removal.
- **What moves:** a CI job parses `config/app.yaml` as YAML and fails if any mapping key named `api_key` appears at any depth, or if the file doesn't parse. Parsing is used instead of grep so quoting and nesting don't hide a key. It is a required status check on `main`, so it can't be merged around.
- **State lives in:** the CI config in git, and branch protection.
- **If it fails:**
  - If the job is flaky or wrong, the PR can't merge. Fix the job.
  - Include a negative test: a fixture with an `api_key` must make the job fail. Then open a throwaway PR that re-adds a key and confirm it is blocked.

### 7. Merge, then roll out to prod

- **Starts when:** steps 3, 4, 5 and 6 are done, plus a review. **Do not merge before step 3 is finished.** A merge builds an image, and that image can't become ready without the store keys.
- **What moves:** the new image rolls out one pod at a time with `maxUnavailable: 0`. Each new pod reads its three keys from the store (Part B, step 12) and becomes ready only when it has all of them. Only then is an old pod stopped. Old pods keep using the old yaml keys, which are still valid.
- **State lives in:** pod memory (the keys) and the logs (one `secret_loaded name=… version=…` line per secret, with the version id only).
- **If it fails:**
  - If the first new pod never becomes ready, the rollout halts and the old pods keep serving. That is the safe outcome. Check the pod's error log: a store outage, an access-policy bug or a wrong secret name.
  - Hold after the first new pod. Run one authenticated read-only call per provider through it and check the error rate before letting the rollout continue.
  - Rolling back means redeploying the earlier image. Until step 10 this still works, because the old keys are still valid.

### 8. Confirm every instance is on the new keys

- **Starts when:** the rollout has finished.
- **What moves:** nothing. The check for each of the 4 pods (list them from the cluster at check time) has three parts:
  - The pod runs the post-migration image.
  - Its logs show the expected version id for all three secrets.
  - No `secret_loaded` or refresh line shows an older version afterwards.
  Also check for non-prod deployments and any other consumer found in step 2.
- **State lives in:** the logs (30-day retention), the cluster and the ticket.
- **If it fails:** if any instance can't be shown to be on the new key, step 10 does not start. Investigate that instance, and restart it if it is the only way to fix it.

### 9. Bake, then block the old images

- **Starts when:** step 8 passes and a bake period has elapsed. The team chooses the length, and at least one business day is suggested.
- **What moves:**
  - Mark the pre-migration image tags do-not-deploy, or delete them. They contain the leaked keys, and they would fail after revocation.
  - Tell developers to pull and use the new `make run`. Their old local config copies stop working at step 10. That affects only dev, not customers.
- **State lives in:** the image registry and the deploy tooling.
- **If it fails:**
  - If a rollback is needed during the bake, roll back to the old image and repeat steps 7 to 9 later. Re-run the step 8 check before any revocation.

### 10. Revoke the old keys, one provider at a time

- **Starts when:** the security on-call decides, after re-running the step 8 check immediately before each revocation.
- **What moves:** at each provider, the old key is revoked. Go in this order: geocoding, then email, then payments. The lowest-impact provider goes first, so any surprise shows up there.
- **Gate for each key:** the provider's "last used" for the old key must have stopped advancing for at least 15 minutes. That is three refresh cycles, and it catches consumers the inventory missed. If the old key is still being used, find the consumer first.
- **Method:** if the provider supports disabling a key before deleting it, disable it first and delete after a day with no errors. That makes the step reversible.
- **State lives in:** the provider.
- **If it fails:**
  - If errors appear after a disable, re-enable the old key and find the consumer.
  - After a hard delete there is no undo, so the gate before it must pass.

### 11. Close out

- **Starts when:** all three old keys are revoked.
- **What moves:** update `deploy.md` and the runbook, record the final version ids, and confirm the CI guard is required on `main`. Git history is not rewritten, and the leaked keys in it are now dead.
- **If it fails:** leave the ticket open until the CI guard and the do-not-deploy marks are verified.

---

## Part B: How the app reads keys at runtime (code shipped in step 5)

### 12. Startup load

- **Starts when:** the process starts, before it reports ready.
- **What moves:** the app fetches the latest version of the three secrets from `orders-api/<APP_ENV>/<name>`, using the pod's identity (`orders-api-prod` in prod). The values go from the store into process memory.
- **Retry and exit:** each fetch has its own timeout. If the store can't be reached or a secret is missing, retry up to 3 times, 2 seconds apart. After the fourth failed attempt, log an error naming the secret (never a value) and exit with code 1.
- **Readiness:** `/healthz` returns 503 until all three keys are held, then 200.
- **State lives in:** process memory.
- **If it fails:** the pod exits and Kubernetes restarts it. During a rollout, the pod never becomes ready, so the rollout halts and the old pods serve.

### 13. Holding secrets in memory

- Each key is held in a small object that is swapped as a whole, so a request never sees half an update.
- The object redacts itself when printed, so an accidental `repr` or traceback can't leak it.
- Keys go nowhere else:
  - not into environment variables
  - not onto disk
  - not into logs, including HTTP debug logs and request headers
- Only version ids are logged.
- The pod's environment holds only non-secret settings such as `APP_ENV`. So `kubectl describe pod` and a process listing show nothing sensitive.
- **State lives in:** process memory. A restart reloads from the store.

### 14. Refresh every 5 minutes

- **Starts when:** a timer fires every 5 minutes after startup.
- **What moves:** for each secret, fetch the latest. If the version id differs from the one held, swap in the new value and log `secret_rotated name=… old_version=… new_version=…`. If it is the same, do nothing.
- **State lives in:** process memory. The previous value is also kept for one generation, for step 15.
- **If a re-read fails:** keep using the last good value, log a warning with the secret name and error class, and try again at the next tick. A failed refresh never changes readiness.
- **Added alert (not in the brief):** warn the team if no refresh has succeeded for 15 minutes. A pod that can't refresh will fail once its old key is revoked.

### 15. Use on each request, and the fallback on a rejected key

- **Starts when:** a client sends a request to a provider.
- **What moves:** the client reads the current key from memory and sends it as it does today.
- **If the provider rejects the key (401 or 403):**
  - Do one out-of-cycle re-read of that secret, at most once a minute per secret.
  - If the version changed, retry once with the new value.
  - Otherwise retry once with the previous value, if one is held.
  - Otherwise return the failure.
- **Why this is safe:** an auth rejection means the provider did not process the request, so the retry can't double-charge.
- **Why it exists:** it is a safety net for the requirement that no customer request fail because of a missing or revoked key. It is my addition, so confirm it is wanted.

### 16. Later rotations use the same mechanism

- A rotation is steps 3, 8 and 10 again: the security on-call issues a new key and writes it to the store. Within 5 minutes every instance swaps. The version ids in the logs are used to confirm. Then the old key is revoked.
- No restart or redeploy is needed.

---

## Open question (not decided, not planned here)

**Scheduled rotation.** Security has not decided whether keys must also be rotated on a regular schedule after this migration, or how often. This plan sets no cadence. If they decide yes, step 16 is the mechanism, and the cadence and an owner need to be added.

## Assumptions to confirm

- Each provider allows two active keys at once. This is the gate in step 2.
- The bake length in step 9.
- The authenticated read-only calls used for the smoke checks in steps 3 and 7.
- Each provider offers a sandbox key, or the offline stubs are acceptable for dev.
- The retry-on-rejection behaviour in step 15.
