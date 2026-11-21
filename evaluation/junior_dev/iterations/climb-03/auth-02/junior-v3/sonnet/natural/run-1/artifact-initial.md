# Plan: move orders-api provider keys into the managed secret store

## Summary

- **Keys:** three secrets (`payments_api_key`, `email_api_key`, `geocoding_api_key`) move from `config/app.yaml` into the store at `orders-api/<env>/<name>`.
- **Rotation:** every key is rotated at its provider, because the old ones are in git history for good.
- **Overlap:** old and new keys are both valid for the whole rollout. The old keys are revoked only after every running instance is confirmed to be on the new ones. This overlap is what keeps customer requests from failing.
- **App changes:** the app reads keys from memory on every call, not once at construction. It loads them at startup, reports ready only when it has all three, and refreshes them every 5 minutes.
- **Local runs:** local development reads separate dev secrets (or runs fully offline), never prod.

**Assumptions to verify in step 1:**
- Each provider lets two keys be active at once.
- Providers offer test or sandbox keys.
- "Retry 3 times" means the first attempt plus 3 retries, so 4 attempts in total.

## Phase A: Prepare the store and the new keys (no production effect)

### 1. Preflight gates
- **Starts it:** the plan is approved.
- **What moves:** nothing moves yet. Four checks are made.
  - **Overlap:** for each of the three providers, confirm in writing that a second key can be active alongside the current one. If any provider allows only one active key, stop. The "no failed requests" rule can't be met by simple overlap, and that provider needs its own plan.
  - **Inventory:** find every consumer of the three live keys. Check other services, cron jobs and workers built from this image, CI, staging, and developer machines (`make run` uses the live keys today). The old keys can't be revoked until all of these have moved.
  - **Test keys:** confirm each provider offers test or sandbox keys for dev.
  - **Store facts:** confirm the store's read API returns the latest value together with its version id.
- **State lives in:** the checklist on the tracking ticket.
- **If it fails:** the migration doesn't start. Nothing has changed, so there is nothing to undo.

### 2. Create the store layout and access rules
- **Starts it:** step 1 passes.
- **What moves:** nothing moves yet. This step creates the structure.
  - **Paths:** create the three secrets under `orders-api/prod/` and under `orders-api/dev/`.
  - **Encryption:** each environment gets its own KMS key.
  - **Read access:** identity `orders-api-prod` gets read-only on `orders-api/prod/*` and decrypt on the prod KMS key, with no other permission. The `dev` path is readable by engineers, and no engineer group is granted anything on prod.
  - **Write access:** only the security on-call role can write `orders-api/prod/*`.
- **State lives in:** the store's access policies and the KMS key policies, which should be managed as code.
- **If it fails:** nothing depends on the store yet, so fix the policy and retry.
- **Check before moving on:**
  - Reading prod as `orders-api-prod` succeeds.
  - Writing prod as `orders-api-prod` is denied.
  - Reading and writing prod as an ordinary engineer is denied.
  - Reading dev as an engineer succeeds.

### 3. Set up local development
- **Starts it:** step 2 is done. This must ship before step 14.
- **What moves:** `make run` gets two modes.
  - **Default mode:** `make run` sets `APP_ENV=dev` and reads `orders-api/dev/*` using the engineer's own credentials. Those secrets hold provider test keys, never live ones.
  - **Offline mode:** `make run-offline` swaps the provider clients for local fakes that need no key. This is also the fallback if a provider has no test keys.
  - **No default env:** the app has no default environment. If `APP_ENV` is unset it refuses to start. Prod's value comes from the deploy manifest.
- **State lives in:** the dev store path, and in process memory. No key goes into a file or an environment variable.
- **If it fails:** engineers fall back to the offline mode. It must be working before the old keys are revoked, because revoking breaks any local run that still uses them.

### 4. Create new keys at each provider
- **Starts it:** step 2 is done. The security on-call does this step.
- **What moves:** at each of the three providers, issue a new live key. Do **not** revoke the old one. The new keys are handled only by the security on-call and are never pasted into chat, tickets or files.
- **State lives in:** the provider accounts. Each provider now has the old key active and the new key active.
- **If it fails:** nothing in production has changed, so retry. If a provider refuses a second active key, that contradicts step 1. Stop and re-plan for that provider.

### 5. Validate and write the new keys to the prod store
- **Starts it:** step 4 is done for a given provider.
- **What moves:** for each key, the security on-call does three things.
  1. Prove the new key works with a harmless authenticated call to the provider.
  2. Write it to `orders-api/prod/<name>`. The store assigns a version id.
  3. Record the version ids for step 13.
- **State lives in:** the store (encrypted by the prod KMS key). The old keys are never written to the store.
- **If it fails:**
  - **Key rejected by the provider:** don't write it, and get a new one.
  - **Wrong value written:** write the correct value as a new version. Nothing reads the store yet, so no customer is affected.
- **Why this order matters:** the validation happens before the write. After migration the app takes whatever is the latest version, so a bad value would reach live traffic within 5 minutes.

## Phase B: Build the new runtime behavior

All of Phase B ships in one code change. The numbered steps below are the design.

### 6. Add an in-memory secret provider and make clients read it per call
- **Starts it:** the code change is being built.
- **What moves:**
  - **New module:** `app/secrets.py` holds a map of name to (value, version id) in process memory.
  - **Client change:** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in `__init__`. At the point of each outgoing request they call `secrets.get("payments_api_key")` and so on. The module-level singletons stay, but they hold no key.
  - **Config split:** `config_loader.py` keeps loading only the non-secret settings (`base_url`, timeouts, `from_address`). `settings` no longer contains any key.
- **State lives in:** the map is replaced as a whole and never edited in place, so a request always sees one consistent (value, version) pair. Nothing is written to disk.
- **If it fails:** a missing name raises an error at call time. Startup (step 7) prevents this in practice. Tests cover that the client uses the current value after a refresh.

### 7. Load all three keys at startup, with retries
- **Starts it:** the process starts.
- **What moves:** the app reads the three secrets for its environment from the store. It makes one attempt, then up to 3 retries, 2 seconds apart.
  - **Success:** the map from step 6 is filled and each version id is logged.
  - **Failure:** if any of the three secrets can't be fetched, it logs the failure (secret name and error type, never a value) and exits with a non-zero code. That is a worst case of about 6 seconds of waiting.
- **State lives in:** process memory.
- **If it fails:** the pod exits and Kubernetes restarts it. During a rollout this halts the rollout, and the old pods keep serving (see step 12). A partial load never counts as success.

### 8. Make readiness depend on the keys
- **Starts it:** every call to `GET /healthz`.
- **What moves:** `/healthz` returns 503 until all three keys are loaded, and 200 after. Today it returns 200 as soon as the server is listening, which would let a pod take traffic without keys.
  - **After startup:** later refresh failures do not flip it back to 503. The pod has a usable last good value, so it should keep serving.
- **State lives in:** a flag in memory, set once after step 7.
- **If it fails:** a pod that never becomes ready is never given traffic, and with `maxUnavailable: 0` the old pod is not stopped.

### 9. Refresh every 5 minutes
- **Starts it:** a background timer, every 5 minutes, started after step 7.
- **What moves:** for each secret, the app re-reads the latest value and version id from the store. If the version id changed, it swaps in the new (value, version) pair and logs "name now at version X". Each secret is refreshed independently, so one failure doesn't block the others.
- **State lives in:** process memory. Each pod refreshes on its own schedule, so pods pick up a new version at different moments within 5 minutes of the write.
- **If it fails:** the app keeps the last good value and logs a warning (name, error type, current version id). A failed refresh never causes a restart or a 503. Raise an alert if the warnings repeat. The threshold is for the team to set.
- **Why a pod can't be stuck on a bad value:** if a bad version is ever written, restore service by writing the previous good value as a new version. Pods pick it up within 5 minutes. This works because the old key is not revoked until step 14.

### 10. Report non-secret state and keep values out of logs
- **Starts it:** the code change is built.
- **What moves:**
  - **Version ids:** an internal-only endpoint (or a metric) reports the version id each pod is using for each secret. Values are never exposed.
  - **Log audit:** audit and test that no log line, exception message or crash output can contain a key. Check anywhere the old `settings` dict was logged, and anywhere an HTTP client could log request headers (the `Authorization` header holds the key).
  - **Environment:** the keys are never copied into environment variables.
- **State lives in:** the version ids come from memory.
- **If it fails:** the pull request doesn't merge. A leaked value in logs would be kept for 30 days in the central log service, so test this before deploying.

### 11. Remove the keys from the file and add the CI guard
- **Starts it:** the same change as steps 6 to 10.
- **What moves:**
  - **Config file:** delete all three `api_key` lines from `config/app.yaml`.
  - **Loader:** make the loader raise an error if it ever finds an `api_key` in the file.
  - **CI check:** add a CI check that parses `config/app.yaml` and fails if any key named `api_key` appears anywhere in it. Make it a required status check on `main`.
  - **Test:** prove the check works by confirming it fails on a deliberately bad copy of the file.
  - **Docs:** update `deploy.md` for the new startup, readiness and local-run behavior.
- **State lives in:** the repo and the CI configuration.
- **If it fails:** if the check can't be made required, the requirement isn't met. Treat that as blocking.
- **Limit:** removing the keys from the file doesn't remove them from git history. That is why step 4 rotates them.

## Phase C: Roll out, confirm, revoke

### 12. Deploy the new image
- **Starts it:** steps 5 and 11 are done, and the code change is merged to `main`. CI builds the image.
- **What moves:** a normal rolling deploy of the 4 replicas, one pod at a time, with `maxUnavailable: 0`.
  - **New pods:** these use the new keys from the store.
  - **Old pods:** these still serve with the old keys from their baked-in file, which are still valid.
  - **Gate:** pause the rollout after the first new pod is ready. Check that its calls to all three providers succeed, then continue.
- **State lives in:** the cluster for pod state, and in memory for the keys.
- **If it fails:**
  - **Store unreachable or secret missing:** the new pod exits (step 7), never becomes ready, and the rollout halts. The old pods keep serving, and customers see nothing.
  - **Provider errors on the first new pod:** stop the rollout and roll back. A rollback is a redeploy of the earlier image, which still works because the old keys are valid.

### 13. Confirm every instance is on the new keys
- **Starts it:** the rollout from step 12 has finished.
- **What moves:** nothing moves. The operator collects evidence that the old keys are no longer in use.
  - **Pod list:** every running pod uses the new image, and no pre-migration pod is left.
  - **Version ids:** every pod reports the version ids recorded in step 5 for all three secrets.
  - **Provider dashboards:** where available, the old key shows no recent use.
  - **Other consumers:** the other consumers found in step 1 have moved.
- **State lives in:** the version-id reports and the pod list.
- **If it fails:** any pod that doesn't match means the old key stays active. Investigate that pod. Do not revoke.

### 14. Revoke the old keys at the providers
- **Starts it:** step 13 passes and step 3 has shipped. The security on-call does this step.
- **What moves:** revoke the old key at one provider at a time, and watch error rates for that provider after each revoke.
- **State lives in:** the provider accounts.
- **If it fails:**
  - **Unexpected errors:** they point to a consumer that was missed. Treat the new key as the one to keep and find the missed consumer.
  - **Rollback to old images:** after this step it is no longer possible, because pre-migration images carry dead keys. Every redeploy must now use a post-migration image.

### 15. Clean up
- **Starts it:** step 14 is done.
- **What moves:**
  - **Old images:** mark pre-migration images as non-deployable. They carry the leaked keys and would now fail every request.
  - **Docs:** confirm the updated `deploy.md` is merged.
  - **Ticket:** close the migration ticket with the list of recorded version ids.
- **State lives in:** the image registry and the repo.
- **If it fails:** an old image that stays deployable is a risk for a future rollback. Leave the ticket open until it is blocked.

## Open question

Security has not decided whether keys must also be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence.

The rotation procedure itself is already in place and can be reused at any frequency: steps 4, 5, 13 and 14, with the 5-minute refresh from step 9 carrying the new value to running pods. A schedule would add only a trigger and an owner.
