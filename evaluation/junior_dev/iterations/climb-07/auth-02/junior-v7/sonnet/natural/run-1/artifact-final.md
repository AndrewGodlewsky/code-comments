# Plan: move `orders-api` provider keys into the secret store

`orders-api` today reads three live provider keys (payments, email, geocoding) from `config/app.yaml`. That file is committed to git and baked into every container image, and nothing re-reads it after start. After this change the keys live in our managed secret store. Each pod loads them into memory at startup, refreshes them every 5 minutes, and uses them per request. We first issue new keys and keep the old ones active, so old and new pods both work during the rollout. We revoke the old keys only after every pod is confirmed on the new ones, because the old keys have been in git history for two years and are treated as leaked.

## Terms

- **The store:** our managed secret store. The brief does not name the product. Secrets live at `orders-api/<env>/<name>`, are encrypted at rest with a per-environment KMS key (the cloud's key-management service), and every write creates a new **version id**. Reading with no version id returns the newest version. The **store CLI** is that product's command-line tool.
- **Secret names:** `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- **Holder:** an in-memory object in the new `secrets` module. For each secret it keeps the current value, its version id and a **previous** value (empty at startup). Updates are swapped under a lock, so a reader never sees a new value with an old version id. It masks values in `repr`/`str`.
- **Service identity:** the platform identity a pod runs as. All 4 prod pods use `orders-api-prod`. How the platform attaches it to a pod is not covered here.
- **`APP_ENV`:** `prod`, `dev` or `local`. Each environment's deployment manifest sets it. It selects the store path, or the local file.
- **Readiness probe:** the platform calls `GET /healthz`. A rolling deploy with `maxUnavailable: 0` (set in the deployment's config) stops an old pod only after a new pod's probe returns 200.
- **Security on-call group:** holds the prod write right. Members run the store CLI under their own identity. How membership is granted is up to security.
- **Deploy tooling:** whatever system performs the redeploys and rollbacks in `deploy.md`. The files do not name it.

## Assumptions to confirm before building

- Each provider lets two API keys be active at once. The old and new key must work side by side until the last pod has switched. If any provider allows only one, stop and escalate to security: "no failed customer request" can't be met without it.
- Each provider can issue a sandbox or test key for non-prod use.
- "Retry 3 times" means 1 initial attempt plus 3 retries, 4 attempts in total.
- The store product and its read call are confirmed (see open questions).

## Rules that apply everywhere

- Key values exist only in process memory. They never go on disk, into environment variables or into logs. Logging version ids is fine.
- Fetch secrets over the store API only. Do not use environment injection or a mounted secrets file.
- Do not log headers or request objects. Turn off HTTP-client debug logging. Strip `Authorization` from exception output. Disable core dumps in the container.
- No customer request may fail because of a missing or revoked key at any point.
- Engineers must not be able to read prod values.

# Part 1: How the app runs

### 1. Startup load
- **Starts when:** the process starts, before it takes traffic.
- **What it does:**
  - Reads the three secrets from `orders-api/<APP_ENV>/<name>` using the pod's service identity. No store credential is in the image or environment.
  - If a prod pod got a wrong `APP_ENV`, the read of a non-prod path is denied, so the pod exits and never gets a wrong key.
  - With `APP_ENV=local` there is no store call. The module fills the holder from the `local_secrets` section of `config/app.local.yaml` (see Local development). Everything after loading works the same.
  - Non-secret settings (`base_url`, timeouts, `from_address`) still come from `config/app.yaml` via `config_loader.py`. The loader now refuses to start if the file it loads contains any `api_key`, so a stale file cannot shadow the store. The local fake keys sit under `local_secrets`, so they pass.
  - One attempt reads all three secrets and has a timeout of about 3 s. If any read fails, the attempt fails and the next one re-reads all three. After a failed attempt it waits 2 s. Worst case: 4 x 3 s + 3 x 2 s = 18 s.
- **State:** the holder.
- **On failure:** after the 4th failed attempt, log the error (no values) and exit with a non-zero code (for example 3). The platform is expected to restart the container, and the restart repeats the whole sequence. "Denied" and "not found" are handled the same way.
  - Only a starting pod needs the store. Running pods keep their values in memory, so a store outage does not stop them. A pod that crashes during an outage cannot return until the store does. During a rolling deploy, the new pod never turns ready and the old pods keep serving.

### 2. Readiness
- **Starts when:** the HTTP server is up.
- **What it does:** `/healthz` returns 503 until all three secrets are loaded, then 200 `{"status": "ok"}`. Today it returns 200 as soon as the server listens, which would let a pod without keys replace a working one. Other routes also return 503 while the holder is empty. Readiness proves only that the keys loaded. It makes no provider call.
- **State:** the holder's "all loaded" flag.
- **On failure:** a pod that can't load keys exits (step 1) and never turns ready, so the rollout halts. Later refresh failures never change readiness.

### 3. Using a key on a request
- **Starts when:** a request needs a provider call.
- **What it does:** the clients no longer copy the key at construction. They call `secrets.get("payments_api_key")` (and the like) when building each call's `Authorization` header. The module-level singletons stay, since they hold no key. A call reads the value once, so a swap mid-call does not affect it. Either value is valid during a rotation.
- **State:** the holder. A request keeps its header only for its own lifetime.
- **On failure:** if the holder is somehow empty, return 503 and log the secret name.

### 4. Refresh every 5 minutes
- **Starts when:** startup load succeeded. A background timer then fires every 5 minutes. Every pod has its own timer, so pods swap at different moments within 5 minutes of a new write.
- **What it does:**
  - Reads the latest version of each secret. A secret counts as changed when the returned version id differs from the holder's.
  - For each changed secret it swaps in the new value and keeps the replaced value as that secret's previous value, until that secret's next swap. There is no timer on it. A restart empties it.
  - It does not check the new value before accepting it. The protections are the test call made before the write (rollout step 2) and the fallback below.
  - It logs one info line per cycle with version ids only, for example `secrets refreshed payments=v7 email=v3 geocoding=v4`. Logs are kept 30 days.
- **State:** the holder, plus the version ids in the central logs.
- **On failure:** see step 5.

### 5. Failures after startup
- **Refresh read fails:** keep the last good value, log a warning with the secret name and error (no values), and retry at the next tick.
- **Three failed cycles in a row (15 minutes):** raise an alert, because a pod stuck on an old value is dangerous when an old key is about to be revoked. The alert is assumed to be a rule on the central logs (see open questions).
- **Provider rejects the current key (401 or 403):** each call tries the current value first. If that secret has a previous value, the client retries that call once with it and logs a warning. It does not switch permanently. The retry can't double-charge, because a refused call was not processed. The client can't tell a key-related 403 from an unrelated one, so it retries in both cases, costing one extra call. If the retry is also rejected, the call returns the provider's answer to the current value, as today.
- **Not covered by the fallback:** a freshly started pod has no previous value. That includes every new pod in the first migration, because the old key lives only in the old image's yaml. The test call in rollout step 2 protects that case.
- **Bad write:** noticed by the test call, the error-rate check in rollout step 5 and the fallback warnings. The security on-call engineer makes a corrected write, and every pod picks it up within 5 minutes.
- **State:** the holder, the logs and the alert rule.

### 6. Local development
- **Starts when:** a developer runs `make run`.
- **What it does:** with `APP_ENV=local` it uses `config/app.local.yaml`. This points `base_url` at local stub servers (started by `make stubs`) and has a `local_secrets` section with fixed fake keys, which the secrets module reads instead of calling the store. No real key is needed, and the section is not named `api_key`, so neither guard flags it.
  - Optionally, `make run-sandbox` sets `APP_ENV=dev`. It reads `orders-api/dev/*` under the developer's own identity and talks to provider sandboxes. Dev uses exactly the same secrets code as prod, including retries, readiness and refresh. Only `local` skips the store.
  - Neither mode can name a prod path, and engineers have no prod access anyway.
- **State:** the local files and the dev store paths.
- **On failure:** if the sandbox read is denied, fall back to the stubs. The live keys are no longer available locally.

# Part 2: How we build and roll it out

### 1. Create the paths and access rules
- **Starts when:** this plan is approved.
- **What it does:** the platform or security team creates `orders-api/prod/*` and `orders-api/dev/*`, each with its own KMS key, and turns on store audit logging for reads and writes.
  - Prod: `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else. The security on-call group gets write. Engineers get no access to prod values.
  - Dev: engineers get read on `orders-api/dev/*`.
- **State:** the store's access policies and KMS configuration.
- **On failure:** before any secret is written, run these tests: an engineer reads prod and is denied; `orders-api-prod` writes and is denied; `orders-api-prod` reads `orders-api/dev/*` and is denied; `orders-api-prod` reads `orders-api/prod/*` and succeeds. If any result is wrong, fix the policy and re-test. Nothing in the app has changed, so nothing is at risk.

### 2. Issue new keys and store them
- **Starts when:** step 1 passes.
- **What it does:**
  - A security on-call engineer creates a new key at each provider. The old key stays active.
  - They make one test call per new key, to catch a mistyped or dead key before any pod reads it.
  - They write each new value into `orders-api/prod/<name>` with the store CLI under their own identity, never through chat, a ticket or a file. They record the version ids, not the values, in the rollout ticket.
  - Sandbox keys go into `orders-api/dev/<name>`.
  - Today's pods never read the store, so these writes change nothing for them.
- **State:** the provider holds old and new keys; the store holds the new values; the ticket holds only version ids.
- **On failure:** a new key that fails its test call is deleted at the provider and replaced. A failed store write is retried. If a provider can't hold two active keys, stop (see assumptions).

### 3. Code change, one PR
- **Starts when:** the Part 1 behaviour is agreed.
- **What it does:**
  - Add the `secrets` module (holder, startup load, refresh thread, local source).
  - Change the three clients and `/healthz` as in Part 1.
  - Delete the three `api_key` lines from `config/app.yaml`, add the loader guard, and update `deploy.md`.
  - Add the CI guard in the same PR. Adding it after the removal would leave a gap where keys can return. It runs on every PR that touches `config/`. It parses every YAML file under `config/` and fails on a key named `api_key` at any depth, or on strings like `pk_live_`, `ml_live_`, `geo_live_`. It is a required status check on `main`, and a test fixture containing an `api_key` proves it fails when it should.
- **State:** git, on a branch. The guard lives in the CI config and branch protection.
- **On failure:** tests must pass before merge, and a red check blocks it. They cover:
  - 4 attempts, 2 s apart, then a non-zero exit.
  - Last-good retention on a refresh error.
  - `/healthz` returns 503 until loaded.
  - A new value is used without a restart.
  - The 401 fallback.
  - A canary test: set a random canary secret, exercise startup, refresh and failure paths, and fail the build if the canary appears in captured logs, in `os.environ` or in files under the working directory.

### 4. Merge and deploy
- **Starts when:** steps 2 and 3 are done and the PR is approved.
- **What it does:**
  - Merge to `main`. CI builds an image without keys. The rolling deploy replaces one pod at a time, and each new pod runs startup and readiness before an old pod stops.
  - Old and new pods run different images. An old pod has old code and the old yaml baked in, so it uses the old key and ignores the store. A new pod has the new yaml (no `api_key`) and uses the new key from the store. The loader guard checks only its own image's yaml, so they never conflict. Both keys are active, so every call succeeds.
  - A new pod first uses its key on the first customer request after turning ready. Nothing checks it before then. What protects customers is the test call in step 2 and the check in step 5. Because of `maxUnavailable: 0` and the active old key, a bad key can only hit the share of traffic the new pods serve, and rollback is available.
  - The person running the deploy watches rollout status. No separate stuck-rollout alert is set up (see open questions).
- **State:** the image registry, the cluster and the store.
- **On failure:** a pod that can't reach the store or lacks access exits after up to about 18 s and never turns ready, so the rollout halts and old pods keep serving. Fix the policy, or roll back by redeploying the earlier image. It still works because the old key is active.

### 5. Verify and soak
- **Starts when:** all 4 pods are on the new image.
- **What it does:** check that every pod has a startup line and a refresh line with the expected version ids. Check that error and latency rates for payments, email and geocoding calls match the pre-deploy baseline. Soak for at least 1 hour and at least 3 clean refresh cycles. Security can lengthen this. Rollback stays available.
- **State:** the central logs and metrics.
- **On failure:** roll back to the earlier image (old key still valid), or correct the store value if that is what is wrong.

### 6. Close the rollback hole and find other users of the old keys
- **Starts when:** step 5 passes.
- **What it does:**
  - Configure deploy tooling to refuse any image built before the migration image. Those images hold the old keys and would fail once the keys are revoked.
  - Use each provider's usage or audit view to list who still calls with the old keys. Expected callers are developers' `make run` and old pods, which are gone by now. Investigate anything else.
  - Tell engineers that old local checkouts will stop working.
- **State:** the deploy tooling config and the provider usage views.
- **On failure:** an unknown caller, or no way to see usage, holds the revocation until security accepts the risk in writing.

### 7. Confirm every instance, then revoke the old keys
- **Starts when:** step 6 is done and the security on-call engineer explicitly signs off.
- **Evidence, per key, collected by hand and recorded in the ticket:** list the pods from the cluster, read each pod's latest refresh line in the central logs, and compare the version ids with the store's current versions (the store CLI lists them).
  - The cluster lists exactly the expected pods, all on the migration image or later.
  - Each pod's latest refresh line matches the store's current versions.
  - No refresh alert is open.
  - Where the provider shows last use, the old key has not been used since the final pod switched.
- **What it does:** revoke one provider at a time (geocoding, then email, then payments). Use a reversible "disable" first if offered. Watch error rates for 15 minutes, then delete.
- **State:** the providers and the ticket.
- **On failure:** if errors appear after a disable, re-enable the old key. If it can't be re-enabled, issue another key, write it to the store and let the refresh deliver it. After this step a pre-migration image is no longer a rollback option, which is why step 6 blocks those images.

### 8. Close out
- **Starts when:** all three old keys are revoked.
- **What it does:** the keys in git history are dead, so history is not rewritten. Confirm the CI guard is required on `main`. Confirm `deploy.md` describes the store, the 5-minute refresh and the local modes. Record the final version ids and the revocation dates.
- **State:** the repo docs and the ticket.
- **On failure:** keep the ticket open until each item is done.

## Rotating later (same mechanism)

1. Issue a new key at the provider while the old one stays active.
2. Test it, then write it to the store.
3. Wait at least 2 refresh cycles (10 minutes).
4. Confirm every pod shows the new version id.
5. Revoke the old key.

## Open questions

- **Scheduled rotation: not decided.** Security has not decided whether keys must be rotated on a schedule after this migration, or how often. This plan picks no cadence. The runtime supports any cadence without code changes, so this does not block the work. Security must decide whether there is a schedule and who owns it.
- **Store product and pod identity: not known.** The brief does not name the store product or say how the platform gives a pod the `orders-api-prod` identity. Confirm both before the code change (step 3).
- **Alerting: not known.** Which system raises the refresh-failure alert, and who receives it. Confirm before deploy (step 4).
- **Stuck rollout and restart behaviour: not known.** `deploy.md` says a rollout halts when a new pod never turns ready, but not how soon anyone notices, who is told, or how the platform backs off between restarts. Confirm before deploy (step 4).
- **Deploy tooling: not known.** Where the "refuse old images" rule can be configured is unconfirmed. Confirm before step 6.
