# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

Today `config/app.yaml` holds three live keys (payments, email, geocoding). The file is committed to git and copied into every container image. `app/config_loader.py` reads it once at import. Each provider client copies its key into itself when it is built, so a changed key needs a new image and a redeploy.

After this change the keys live only in the secret store, under `orders-api/<env>/<name>`. At startup the app loads them into memory and reports ready only when it has all three. Every 5 minutes it re-reads them, so a new version is picked up without a restart. Clients ask memory for the key on every call.

The old keys have been in git history for two years, so we treat them as leaked. Each one is replaced with a new key at its provider. The old key stays valid until every running instance is confirmed to use the new one, and only then is it revoked. That ordering is how no customer request ever hits a missing or revoked key.

This plan has two parts. Part A is how the system runs after the change. Part B is how we build it and roll it out.

## Terms

- **Secret store**: the managed service that holds secrets, encrypted at rest with a per-environment KMS key. Every write creates a new version id.
- **Secret names**: `payments_api_key`, `email_api_key`, `geocoding_api_key`. The full path is `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`.
- **Version id**: the id the store gives each write. It is safe to log. It tells us which key value a pod holds without showing the value.
- **`APP_ENV`**: the one environment variable the app needs (`prod` or `local`). It names the environment and carries no secret.
- **`SecretStore`**: new code that reads secrets from the store.
- **`SecretCache`**: an in-memory object holding the three current key values and their version ids.
- **Service identity `orders-api-prod`**: the identity all 4 production pods run as.
- **Readiness probe**: `GET /healthz`. Kubernetes sends traffic to a pod only after it returns 200. Deploys are rolling, one pod at a time, with `maxUnavailable: 0`. A new pod must be ready before an old one stops.
- **Security on-call**: the only role that writes prod secrets or works in provider consoles.
- **Platform**: the engineers who create store paths and policies, ship the code and run the rollout.
- **Revoke**: disable or delete the old key at the provider. A delete cannot be undone. A suspend can.

---

# Part A. How the system runs

### A1. Startup load

- **Starts when:** the process starts, before the server reports ready.
- **What it does:** `SecretStore` reads the latest version of the three secrets from `orders-api/<APP_ENV>/<name>`. `APP_ENV` has no default. If it is unset the app exits, so it can never load another environment's keys. All three must load and be non-empty. The values go into `SecretCache`. The app logs only the secret names and version ids.
- **Where data lives:** process memory only. Keys never go to disk, environment variables or logs. `config/app.yaml` still supplies non-secret settings (`base_url`, timeouts) through `config_loader.py`, which no longer needs any key.
- **If it fails:** if the store is unreachable or returns an error, the app retries 3 times, 2 seconds apart. If it is still failing, it logs the secret name and error class (never a value) and exits non-zero. In production that pod never becomes ready, so a rolling deploy halts and the old pods keep serving.

### A2. Readiness

- **Starts when:** Kubernetes calls `GET /healthz`.
- **What it does:** returns 503 until A1 has loaded all three keys, then 200 `{"status": "ok"}`. It keeps returning 200 even if later refreshes fail, so a store outage does not pull healthy pods out of service. Readiness checks that keys are present, not that they are valid. Validity is checked in B3.
- **Where data lives:** one in-memory "keys loaded" flag.
- **Also:** a cluster-internal endpoint, not exposed to customers, returns the three current version ids (never values). The rollout gate in B8 uses it.
- **If it fails:** a pod without keys gets no traffic.

### A3. Clients read the key per request

- **Starts when:** `PaymentsClient`, `EmailClient` or `GeocodingClient` makes an outbound call.
- **What it does:** the client no longer copies the key at construction, because a copied key would never see a refresh. It keeps only `base_url` and similar settings. On each call it asks `SecretCache` for the current key and builds the `Authorization` header. A request already in flight finishes with the key it started with.
- **Where data lives:** `SecretCache`.
- **If it fails:** after A2 the cache always holds a value, so a missing key cannot happen on the request path. A provider rejecting a key appears as a normal provider error.

### A4. Five-minute refresh

- **Starts when:** a background timer fires, every 5 minutes after startup.
- **What it does:** re-reads the latest version of each secret. If the value is non-empty and the version id is new, it replaces the cached entry in one atomic swap and logs the name and new version id. A new version written by security reaches every pod within about 5 minutes.
- **Where data lives:** process memory.
- **If it fails:** a failed or empty read keeps the last good value and logs a warning with the secret name and error class. The next tick tries again. One secret failing does not block the others. A pod that restarts during a store outage cannot start (A1). This is accepted, and the other pods keep serving from cache. Optional: alert when one secret warns on several ticks in a row. The threshold is the team's choice.

### A5. Local development

- **Starts when:** a developer runs `make run`.
- **What it does:** `make run` sets `APP_ENV=local`. The same `SecretStore` code reads `orders-api/dev/*` as the developer's own identity. Those paths hold sandbox or test keys, never live keys. For a provider with no sandbox, `make run` uses a local fake client.
- **Where data lives:** the dev store and process memory. No key file is created.
- **If it fails:** with `APP_ENV=prod` on a laptop, the store denies the read (B2), so the app exits and prod values stay out of reach. A developer without dev access is added to the dev group or uses the fakes.

### A6. Failure summary

| Situation | Result |
|---|---|
| Store down at startup | 3 retries, then non-zero exit. The pod is never ready. Old pods keep serving. |
| Store down while running | Last good keys are used. Warning logged. `/healthz` stays 200. |
| Pod restarts during an outage | It cannot start. The rest of the fleet serves from cache. |
| `APP_ENV` unset | App exits. |
| Provider rejects a key | Normal provider error on that request. |

---

# Part B. Build and rollout

### Assumptions to confirm in B1

- Each provider allows two active keys at once. If one does not, stop and escalate, because that key cannot be rotated with zero failed requests.
- Each provider has a harmless authenticated call that validates a key (no charge, no email sent).
- No other environment or tool (staging, scripts, cron) uses these keys. If one does, it is added to the B8 checklist.

### B1. Check providers and find every consumer

- **Starts when:** the plan is approved.
- **What it does:** read-only. Security confirms the two assumptions about providers and whether a key can be suspended before deletion. Platform searches for other consumers. Platform also searches the 30-day central logs for the key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) to see whether a key ever reached the logs.
- **Where data lives:** the migration ticket (findings only, never key values).
- **If it fails:** a provider without overlap, or an unknown consumer, blocks the plan until resolved. A log hit does not block. It is recorded as extra exposure, and revocation is the remedy.

### B2. Create store paths, KMS keys and policies

- **Starts when:** B1 is complete.
- **What it does:** platform creates `orders-api/prod/*` (prod KMS key) and `orders-api/dev/*` (separate dev KMS key).
  - `orders-api-prod`: read-only on `orders-api/prod/*`, nothing else.
  - Prod write: security on-call only.
  - Engineers: no access to prod paths. Read access to dev paths.
- **Where data lives:** store and IAM configuration, as reviewed infrastructure code.
- **Verify and record in the ticket:** an engineer is denied a prod read. `orders-api-prod` is denied a write and denied a read of dev paths. Security on-call can write.
- **If it fails:** a failed denial test means the policy is too broad. Fix and re-test. Nothing depends on this yet.

### B3. Create the new keys and prove they work

- **Starts when:** B2's checks pass.
- **What it does:**
  1. For each provider, security creates a new key and leaves the old key active. The value goes from the provider console straight into the store as `orders-api/prod/<name>`. It never goes into a ticket, chat, file or environment variable. Security records only the version ids.
  2. Platform runs a one-off job as `orders-api-prod`. It reads the three secrets, calls each provider's validation call, and prints only pass or fail plus the version id. This proves the keys are valid and that the prod identity can read exactly what it needs.
- **Where data lives:** the new key is at the provider and in the store. The old key is still in git history and the running images. The job holds keys in memory only. The ticket holds version ids and results.
- **If it fails:** a store write error or a rejected key means security re-enters or re-creates the key (a new version) and the job runs again. A permission denial is a policy bug, so return to B2. No customer is affected, because nothing live uses the new keys yet.

### B4. Code change (one PR)

- **Starts when:** B3 is underway. It can be developed in parallel, but it must not deploy before B3 passes.
- **What it does:** one PR holds everything, because the pieces depend on each other (removing `api_key` from the YAML while the old loader still reads it would crash on start).
  - Add `SecretStore` and `SecretCache`, the readiness gate and version endpoint, per-request client reads, the refresh timer and the `make run` change (A1 to A5).
  - Remove the three `api_key:` lines from `config/app.yaml`.
  - Add a CI check that fails the build if an `api_key` key appears at any depth in `config/app.yaml`, or if the text `api_key` appears anywhere in it (this catches commented-out copies). It runs on every PR and every push to `main`, and is a required status check on `main`. It lands in this same PR because it would fail on the current file if added earlier.
- **Where data lives:** the repo and branch protection settings.
- **If it fails:** the check fails with a message naming the line. The fix is to move the key to the store.

### B5. Merge and build

- **Starts when:** the PR is reviewed, CI is green, and B2 and B3 are complete.
- **What it does:** merge to `main` triggers the normal image build. The new image holds no keys.
- **Where data lives:** the image registry.
- **If it fails:** production is unchanged. Fix and rebuild.

### B6. Deploy the first pod and pause

- **Starts when:** the image is built and the rolling deploy begins.
- **What it does:** the first new pod loads keys (A1), passes `/healthz` (A2) and takes traffic. Platform pauses the rollout and checks: the pod reports the version ids recorded in B3, its provider error rate is normal, and its logs show no warnings and no key values. Three old pods serve on the old keys and one new pod serves on the new keys. Both keys are valid, so both work.
- **Where data lives:** the cluster.
- **If it fails:** if the new pod cannot reach the store or crashes, it never becomes ready, the rollout halts and old pods keep serving. If it serves but shows provider errors, redeploy the previous image. That is safe now, because the old keys are still valid.

### B7. Finish the rollout

- **Starts when:** the B6 check passes.
- **What it does:** the rollout resumes and replaces the other 3 pods one at a time. Each must pass `/healthz` before an old pod stops.
- **Where data lives:** the cluster.
- **If it fails:** a pod that never becomes ready halts the rollout with old pods still serving. Fix the cause and continue, or roll back as in B6.

### B8. Confirm every instance uses the new keys (gate for revoking)

- **Starts when:** the rollout is complete.
- **What it does:** nothing changes. Platform checks that:
  - every pod runs the new image, and the pod list matches the current pod count, so an unresponsive pod is not skipped;
  - each pod's version endpoint reports exactly the B3 version ids for all three keys;
  - any other consumer found in B1 has been moved;
  - where the provider shows "last used" for the old key, there is no recent use.
- **Where data lives:** the ticket, one line per key per pod (version id only).
- **If it fails:** any mismatch or unconfirmed consumer means no revoke. Wait one refresh cycle (5 minutes) and check again. Investigate if it persists. The old keys stay valid meanwhile, so no customer is affected.

### B9. Revoke the old keys

- **Starts when:** B8 is recorded for a key and security on-call approves.
- **What it does:** security revokes one provider's old key at a time and watches that provider's error rate before the next. Where the provider allows it, suspend first and delete after a quiet period.
- **Where data lives:** the provider and the ticket (date, who, which key).
- **If it fails:** if 401 errors appear, check whether the source is a pod (it should not be) or a forgotten consumer. If the key was suspended, restore it, fix the consumer and repeat B8. A deleted key cannot be restored, which is why B8 is the gate.

### B10. Block old images

- **Starts when:** all three old keys are revoked.
- **What it does:** rollback means redeploying an earlier image, and images built before this change hold the revoked keys and would fail every request. Platform removes them from the registry or blocks them from deploy. Platform also updates `deploy.md` so that rollback is only to images from this change or later.
- **Where data lives:** the image registry and the docs.
- **If it fails:** a stray old image is a rollback hazard, not a leak, since its keys are dead. The step is done when no pre-migration image can be deployed.

### B11. Standing procedure for any future rotation

- **Starts when:** security decides to rotate a key, for example after an incident.
- **What it does:** repeat the B3 to B9 path with no code change. Create the new key with the old one still active, validate it, write it to the store, let pods pick it up within about 5 minutes, confirm every pod reports the new version id (B8), then revoke the old key (B9).
- **Where data lives:** the store (versions), the providers and the ticket.
- **If it fails:** a pod that fails to refresh keeps its last good key, so the old key must stay active until every pod is confirmed. Validate the new key before writing it, as in B3.

## Open questions

- **Regular rotation schedule.** Security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan sets no cadence and adds no rotation job. The runtime (Part A) and the procedure in B11 already support any cadence, so this does not block the work. Owner: security. Needed: yes or no, and if yes, an interval.

## Done when

- All three old keys are revoked, with B8 evidence for each.
- `config/app.yaml` and the image hold no keys, and the CI guard is required on `main`.
- `/healthz` reports ready only after the keys are loaded.
- Engineers are confirmed unable to read prod values, and `make run` works from dev secrets or fakes.
- The rotation-cadence question is still recorded as open with security.
