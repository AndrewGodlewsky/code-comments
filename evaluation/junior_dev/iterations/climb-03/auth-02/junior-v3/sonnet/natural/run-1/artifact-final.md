# Plan: move orders-api provider keys into the managed secret store

## Summary

Three provider keys (payments, email, geocoding) move out of the committed `config/app.yaml` and into the managed secret store. Every key is rotated at its provider, because the old ones are in git history for good. The old and new keys stay valid side by side for the whole rollout. The old keys are revoked only after every running instance is confirmed to be using the new ones. That overlap keeps customer requests from failing. The app reads its keys from memory on every call, loads them at startup, reports ready only when it has all three, and refreshes them every 5 minutes.

## Terms

- **Store:** the managed secret store. A secret lives at `orders-api/<env>/<name>`, is encrypted with a per-environment KMS key, and gets a new version id on every write.
- **Names:** `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- **APP_ENV:** `prod` or `dev`. The app builds each secret path from it. There is no default: if it is unset, the app refuses to start. Prod gets its value from the deploy manifest.
- **Security on-call:** the only role that can write prod secrets or touch provider keys.
- **Overlap:** the period when a provider has both the old and the new key active.
- **Version endpoint:** an internal-only endpoint on each pod, reachable only from inside the cluster, that reports the version id of each secret the pod uses. It never shows values.

## Assumptions to verify in step 1

- Each provider lets two keys be active at once.
- Each provider offers test or sandbox keys.
- "Retry 3 times" means the first attempt plus 3 retries, 4 attempts in total.
- The store's read API returns the latest value together with its version id.
- The store product, and how a pod proves it is `orders-api-prod` to it (for example a platform-issued workload identity), are not fixed by the brief.

## Steps

### Phase A: Prepare the store and the new keys (no production effect)

**1. Preflight checks**
- **Starts when:** the plan is approved.
- **What happens:** check each of the following and record the result on the tracking ticket.
  - **Overlap:** each provider confirms in writing that a second key can be active alongside the current one.
  - **Inventory:** list every consumer of the three live keys: other services, cron jobs and workers built from this image, CI, staging, and developer machines (`make run` uses the live keys today).
  - **Test keys:** each provider offers test or sandbox keys.
  - **Store facts:** the read API returns the latest value with its version id.
  - **Identity:** how a pod authenticates to the store as `orders-api-prod`, and that the cluster can issue that identity.
- **If it fails:** nothing has changed, so nothing is undone. If a provider allows only one active key, stop: simple overlap cannot meet the "no failed requests" rule, and that provider needs its own plan.

**2. Create the store layout and access rules**
- **Starts when:** step 1 passes.
- **What happens:** create the three secrets under `orders-api/prod/` and `orders-api/dev/`, with a separate KMS key for each environment. Set access, managed as code:
  - `orders-api-prod` gets read-only on `orders-api/prod/*` and decrypt on the prod KMS key, nothing else.
  - Only the security on-call can write `orders-api/prod/*`.
  - Engineers can read `orders-api/dev/*`. No engineer group gets anything on prod.
- **Check before moving on:** prod read as `orders-api-prod` succeeds. Prod write as `orders-api-prod` is denied. Prod read and write as an ordinary engineer are denied. Dev read as an engineer succeeds.
- **If it fails:** nothing depends on the store yet, so fix the policy and retry.

**3. Set up local development** (must ship before step 14)
- **Starts when:** step 2 is done.
- **What happens:** `make run` sets `APP_ENV=dev` and reads `orders-api/dev/*` with the engineer's own credentials. Those secrets hold provider test keys, never live ones. `make run-offline` replaces the provider clients with local fakes that need no key. It is also the fallback if a provider has no test keys. No key goes into a file or an environment variable.
- **If it fails:** engineers use offline mode. It must work before step 14, because revoking breaks any local run still using the old keys.

**4. Create new keys at each provider**
- **Starts when:** step 2 is done. The security on-call does this.
- **What happens:** at each provider, issue a new live key and do not revoke the old one. New keys are never pasted into chat, tickets or files.
- **If it fails:** nothing in production has changed, so retry. If a provider refuses a second active key, that contradicts step 1: stop and re-plan for that provider.

**5. Validate the new keys and write them to the prod store**
- **Starts when:** step 4 is done for a provider.
- **What happens:** for each key, the security on-call (1) proves the key works with a harmless authenticated call to the provider, (2) writes it to `orders-api/prod/<name>`, and (3) records the version id the store returns on the ticket. Validation comes first because the app takes the latest version, so a bad value would reach live traffic within 5 minutes. The old keys are never written to the store.
- **If it fails:** if the provider rejects the key, do not write it and get a new one. If a wrong value was written, write the correct value as a new version and record its id. Nothing reads the store yet, so no customer is affected.

### Phase B: Build the new runtime behavior (one code change)

**6. Keep keys in memory and have clients read them per call**
- **Starts when:** the code change is built.
- **What happens:**
  - New module `app/secrets.py` holds a map of name to (value, version id) in process memory. The map is replaced as a whole, never edited in place, so a request always sees one consistent pair. Nothing is written to disk.
  - `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in `__init__`. At each outgoing request they call `secrets.get("<name>")`. The module-level singletons stay but hold no key.
  - `config_loader.py` loads only non-secret settings (`base_url`, timeouts, `from_address`). The loader raises an error if it ever finds an `api_key` in the file.
- **If it fails:** a missing name raises an error at call time (step 7 prevents this in practice). If a provider rejects a key, the client behaves as today and returns the error to the caller with no new retry. The overlap keeps the old key valid, and a bad new version is fixed as described in step 9. Add a test that a client uses the new value after a refresh.

**7. Load all three keys at startup**
- **Starts when:** the process starts.
- **What happens:** the app builds each path from `APP_ENV` and reads the three secrets from the store: one attempt, then up to 3 retries, 2 seconds apart (about 6 seconds of waiting at worst). On success it fills the map and logs each version id.
- **If it fails:** if any secret can't be fetched, it logs the secret name and error type (never a value) and exits with a non-zero code. A partial load never counts as success. The pod is restarted. During a rollout, the new pod never becomes ready, so the rollout halts and the old pods keep serving.

**8. Make readiness depend on the keys**
- **Starts when:** each call to `GET /healthz`.
- **What happens:** it returns 503 until all three keys are loaded, then 200. Today it returns 200 as soon as the server is listening, which would let a pod take traffic without keys. A flag in memory is set once after step 7. Later refresh failures do not turn it back to 503, because the pod still has a usable last good value.
- **If it fails:** a pod that is not ready gets no traffic, and with `maxUnavailable: 0` the old pod is not stopped.

**9. Refresh every 5 minutes**
- **Starts when:** a background timer, every 5 minutes, started after step 7.
- **What happens:** for each secret independently, the app re-reads the latest value and version id. If the version id changed, it swaps in the new pair and logs "name now at version X". Each pod refreshes on its own schedule, so pods pick up a new version at different moments within 5 minutes of the write.
- **If it fails:** the app keeps the last good value and logs a warning (name, error type, current version id). A failed refresh never causes a restart or a 503. Alert if the warnings repeat, with a threshold for the team to set.
- **If a bad version was written:** write the previous good value as a new version, and pods pick it up within 5 minutes. This works because the old key is not revoked until step 14.

**10. Version endpoint and log safety**
- **Starts when:** the code change is built.
- **What happens:** add the version endpoint, which reads version ids from memory. Audit and test that no log line, exception message or crash output can contain a key. Check anywhere the old `settings` dict was logged, and anywhere an HTTP client could log request headers (the `Authorization` header holds the key). Keys are never copied into environment variables.
- **If it fails:** the pull request doesn't merge. A leaked value in logs would be kept for 30 days in the central log service, so test this before deploying.

**11. Remove the keys from the file and add the CI guard**
- **Starts when:** the same change as steps 6 to 10.
- **What happens:** delete all three `api_key` lines from `config/app.yaml`. Add a CI check that parses the file and fails if any key named `api_key` appears anywhere in it, and make it a required status check on `main`. Prove it by confirming it fails on a deliberately bad copy. Update `deploy.md` for the new startup, readiness and local-run behavior.
- **If it fails:** if the check can't be made required, the requirement isn't met, and that is blocking.
- **Limit:** this does not remove the keys from git history. That is why step 4 rotates them.

### Phase C: Roll out, confirm, revoke

**12. Deploy the new image**
- **Starts when:** step 5 is done and the code change is merged to `main`, so CI builds the image.
- **What happens:** a normal rolling deploy of the 4 replicas, one pod at a time, `maxUnavailable: 0`. New pods use the new keys from the store. Old pods keep serving with the old keys baked into their file, which are still valid. That is deliberate: it is the overlap that protects customers. The operator pauses the rollout after the first new pod is ready. That pod serves real traffic for a few minutes. The gate passes if its logs and metrics show no authentication errors from any of the three providers. Then the rollout continues.
- **If it fails:** if the store is unreachable or a secret is missing, the new pod exits (step 7), never becomes ready, and the rollout halts while old pods keep serving. If the first new pod shows provider errors, stop and roll back by redeploying the earlier image, which still works because the old keys are valid.

**13. Confirm every instance is on the new keys**
- **Starts when:** the rollout has finished.
- **What happens:** the operator collects evidence that the old keys are no longer in use:
  - Every running pod, listed from the cluster, runs the new image. No pre-migration pod is left.
  - The version endpoint of every pod, queried one by one from inside the cluster, reports for all three secrets the latest version id in the store, and that id is one the on-call validated in step 5 (or a later corrected one recorded on the ticket).
  - Where available, provider dashboards show no recent use of the old keys.
  - The other consumers found in step 1 have moved.
- **If it fails:** any mismatch means the old key stays active. Investigate that pod and do not revoke.

**14. Revoke the old keys**
- **Starts when:** step 13 passes and step 3 has shipped. The security on-call does this.
- **What happens:** revoke the old key at one provider at a time, and watch that provider's error rate after each revoke.
- **If it fails:** unexpected errors point to a consumer that was missed. A revoked key can't be restored, so move that consumer onto the new key from the store right away. Only that consumer's calls to that provider fail meanwhile. This is why the step 1 inventory must be thorough and providers are revoked one at a time. After this step, rolling back to a pre-migration image is no longer possible, because those images carry dead keys.

**15. Clean up**
- **Starts when:** step 14 is done.
- **What happens:** mark pre-migration images as non-deployable, because they carry the leaked keys and would now fail every request. Confirm the updated `deploy.md` is merged. Close the ticket with the list of recorded version ids.
- **If it fails:** an old image that stays deployable is a risk for a future rollback, so leave the ticket open until it is blocked.

## Open questions

- Security has not decided whether keys must also be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence. Steps 4, 5, 13 and 14, with the 5-minute refresh from step 9, can be reused at any frequency. A schedule would add only a trigger and an owner.
- Which store product is used, and how pods authenticate to it as `orders-api-prod`. Step 1 confirms this.
- Exactly how the operator pauses the rollout in step 12 with the current deploy tooling.
