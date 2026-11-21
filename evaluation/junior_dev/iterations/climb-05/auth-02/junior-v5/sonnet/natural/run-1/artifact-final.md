# Plan: move orders-api provider keys into the secret store

## Summary

Today the three live provider keys (payments, email, geocoding) sit in `config/app.yaml`. That file is committed to git and baked into every container image. `app/config_loader.py` reads it once at import. Each provider client copies its key at construction. Changing a key means a new image and a redeploy.

After this change the keys live only in our managed secret store. Each pod loads them into memory before it reports ready, refreshes them every 5 minutes, and clients read the current key on every request. The old keys are treated as leaked (they have been in git history for two years), so every key is rotated at its provider.

The rollout is shaped by one rule: no customer request may fail. New keys are issued while old keys stay valid. Old-image pods keep using the old keys, and new-image pods use the new ones. The old keys are revoked only after every instance is confirmed to be on the new ones.

This document has two parts. Part 1 is how the app runs. Part 2 is how we roll it out.

## Terms

- **Secret store**: our managed service that holds secrets, encrypted at rest with a per-environment KMS key. Every write gets a new version id. The product and the identity mechanism are not named in the brief. The first rollout step records them.
- **Version id**: the id the store gives each write. Logging version ids is allowed. Logging values is not.
- **Path**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. `<env>` is prod, staging or dev.
- **Identity**: who the pod is when it calls the store. In prod it is `orders-api-prod`, which the platform gives the pod with no static credential in an env var or on disk (for example workload identity). `orders-api-prod` can only read `orders-api/prod/*`.
- **`APP_ENV`**: a plain name (prod, staging or dev) that picks the path prefix. It is not a secret.
- **`Secret`**: a small wrapper around a key string. Printing it shows `<redacted>`. `reveal()` returns the real string.
- **Secrets provider**: the one object in the process that owns the current snapshot, the refresher thread and the `get(name)` call. Clients hold a reference to it. The reference carries no key value.
- **Snapshot**: the immutable map `{name: (Secret, version_id)}` the secrets provider holds now. A refresh builds a new map and swaps it in atomically.
- **Readiness probe**: the orchestrator calls `GET /healthz`. A rolling deploy stops an old pod only after a new pod returns 200. If a new pod never becomes ready, the rollout halts and the old pods keep serving.
- **Security on-call**: the only group that can write prod secrets. Engineers cannot read prod values.

## Part 1: How the app runs

### 1. Process start

- **Starts when:** the container starts.
- **What it does:** reads `config/app.yaml` for non-secret settings only (`base_url`, timeouts, `from_address`, port, log level). Reads `APP_ENV`.
- **Where data lives:** nothing secret exists yet.
- **If it goes wrong:** a missing `APP_ENV`, or an `api_key` found in the YAML, makes the process exit non-zero before it listens.

### 2. Initial load with retry

- **Starts when:** step 1 is done. The HTTP server does not start until this succeeds, so no customer request can arrive before the keys are loaded.
- **What it does:** fetches the latest version of `payments_api_key`, `email_api_key` and `geocoding_api_key` under `orders-api/$APP_ENV/`, getting value and version id. It authenticates with the platform identity. Failing to get that identity counts as a failed fetch. Each call has a timeout of about 3 seconds. If any fetch fails, wait 2 seconds and retry only the missing ones, up to 3 retries (at most 4 attempts).
- **Where data lives:** process memory only.
- **If it goes wrong:** after the last retry, log an error naming the secrets and the error class (never values) and exit non-zero. In a rollout the pod never becomes ready, so the rollout halts and old pods keep serving. Outside a rollout the orchestrator restarts the container and the other replicas keep serving. Residual risk: if the store is down while many pods restart at once, capacity drops. Store availability is the control for that.

### 3. Publish the snapshot and report ready

- **Starts when:** all three keys are loaded.
- **What it does:** puts the keys in the first snapshot. Logs one line per secret with name and version id only. Starts the refresher thread. Then starts the HTTP server. `/healthz` returns 200 `{"status":"ok"}` only while the snapshot holds all three keys. Until the server listens, the probe cannot connect, which counts as not ready. `/healthz` does not turn unhealthy when a later refresh fails, so a store outage does not pull every pod out of service. Core dumps are disabled in the container.
- **Where data lives:** process heap only. Never on disk, in env vars or in logs.
- **If it goes wrong:** if the refresher thread cannot start, exit non-zero before the server starts.

### 4. Per-request key use

- **Starts when:** any outbound call to a provider.
- **What it does:** `PaymentsClient`, `EmailClient` and `GeocodingClient` no longer copy the key at construction. Each call reads the current key from the secrets provider:

  ```python
  def charge(self, order):
      key = self._secrets.get('payments_api_key')   # current snapshot, per call
      return http.post(self._base + '/charges',
                       headers={'Authorization': 'Bearer ' + key.reveal()},
                       json=order.to_charge())
  ```

  A request already in flight keeps the value it read. On a 401 or 403 from the provider, the client tries at most one retry:
  1. If the snapshot now holds a different version than the request used, retry once with the snapshot's value. No store call.
  2. Otherwise, if no forced re-read of this secret happened in the last 30 seconds, re-read that one secret from the store (3 second timeout). If it finds a new version, put it in the shared snapshot so every request sees it, and retry once with it.
  3. Otherwise return the provider error to the caller and log a warning.

  A 401 means the provider rejected the request before processing it, so a retry cannot double-charge. This covers an instance that lags behind a rotation.
- **Where data lives:** the snapshot in memory.
- **If it goes wrong:** if the store is unreachable during the forced re-read, the request returns the provider error and the cached value stays in use. What the caller does with a provider error is existing order-code behavior (see open questions).

### 5. Periodic refresh

- **Starts when:** every 5 minutes after the initial load, on the refresher thread.
- **What it does:** fetches the latest version of each secret, each handled on its own.
  - A new version id replaces that secret in a new snapshot, swapped in atomically. Log `secret_rotated name old_version new_version`.
  - An unchanged version id does nothing.
  - An empty or malformed value counts as a failure.
  - If one secret fails, the others still update and the failed one keeps its previous value.
  - After every cycle, log one `secrets_refreshed` line with the pod name and the version id in use for all three secrets, for example `secrets_refreshed pod=orders-api-abc12 payments_api_key=v7 email_api_key=v3 geocoding_api_key=v5`. A failed secret shows its older version id. The format may change but must carry the pod name and all three ids. The rollout's confirmation gate reads this line.
- **Where data lives:** process memory. The store holds the version history.
- **If it goes wrong:** on a fetch error, keep the previous value and log a WARNING with the secret name, error class, version id still in use and time since the last good load (never values or response bodies). Readiness stays 200. Alert the on-call if no cycle has succeeded for several cycles in a row. On-call sets the threshold.

### 6. Stop or restart

- **Starts when:** SIGTERM, a crash or a reschedule.
- **What it does:** nothing is persisted. Memory is discarded. A new process repeats steps 1 to 3.
- **If it goes wrong:** see step 2.

### 7. Local development

- **Starts when:** an engineer runs `make run`.
- **What it does:** `APP_ENV` defaults to `dev`. The app reads `orders-api/dev/*` with the engineer's own login. Those paths hold provider sandbox keys, so live keys are never used locally. Engineers have no access to prod paths, and the loader also refuses `APP_ENV=prod` outside the prod identity. `make run-offline` (`SECRETS_BACKEND=fake`) uses an in-process fake backend with placeholder values and points provider `base_url`s at local stubs. Tests use the same fake backend, so no real key appears in any test run.
- **Where data lives:** process memory, as in prod.
- **If it goes wrong:** an engineer without dev access, or a provider with no sandbox, hits the step 2 failure. They use `make run-offline`.

## Part 2: Rollout

### Assumptions to verify first

- Each provider allows two keys to be valid at once. If not, stop (see step 1).
- Each provider offers sandbox keys. If not, dev uses `make run-offline`.
- The platform gives pods the `orders-api-prod` identity with no static credential.
- Prod deploys can be held by a person or pipeline gate. If a merge to `main` auto-deploys to prod, the secrets work (steps 2 to 4) must be finished before the merge, and the readiness gate is the only safety net.

### 1. Inventory callers and check providers

- **Starts when:** the plan is approved.
- **What it does:** list every caller of the three old keys: each environment running the image (prod, staging, any `APP_CONFIG` override), CI jobs and scripts, and developer laptops (`make run` uses live keys today). Use each provider's last-used and caller data to find callers nobody listed. Confirm with each provider that two keys can be valid at once and that sandbox keys exist. Record the secret store product and how a pod proves its identity. For each provider, record where the old key's last-used time is shown, how far it lags real use, and whether the provider shows rejected attempts on a suspended or revoked key with the caller.
- **Where data lives:** a checklist in the migration ticket, with no key values.
- **If it goes wrong:** if a provider allows only one active key, stop. Zero failures cannot be met without an overlap, so ask the provider for one and escalate to security. An unknown caller joins the migration scope and blocks the confirmation gate until migrated.

### 2. Create the store layout, KMS keys and access policies

- **Starts when:** step 1 is done.
- **What it does:** create one KMS key per environment. Reserve `orders-api/prod/*`, `orders-api/staging/*` and `orders-api/dev/*`, each encrypted with its own environment key. `orders-api-prod` gets read-only on prod paths and nothing else. Only the security on-call group can write prod. Engineers get no prod access and read-only on dev. Staging gets its own identity, read-only on staging paths only.
- **Where data lives:** store and IAM config as code, reviewed in the infra repo.
- **Check with a probe secret** that security writes to `orders-api/prod/_probe`: `orders-api-prod` can read it, cannot write it, and cannot read staging or dev paths; an engineer cannot read it. The probe also proves the identity mechanism works.
- **If it goes wrong:** fix the policy and re-run. No real key is in the store yet.

### 3. Issue new keys at each provider

- **Starts when:** the step 2 checks pass.
- **What it does:** the security on-call creates a new key at each provider, with the old keys still active. The value goes from the provider console straight into the store, never into a file, ticket, chat, shell history or env var. Test each new key with a harmless read-only call. Also create sandbox keys for dev and staging. Staging never uses live keys.
- **Where data lives:** the provider accounts. The ticket records only key ids or names.
- **If it goes wrong:** delete a key that does not validate and issue another. Nothing depends on it yet.

### 4. Write the new keys into the store

- **Starts when:** step 3 produced validated keys.
- **What it does:** the security on-call writes the three prod secrets interactively (prompt or stdin, no value on a command line), and the sandbox keys to staging and dev. Each write returns a version id. Record the prod ids in the ticket as the expected versions.
- **Where data lives:** the store, encrypted, with an audit trail of reads and writes.
- **If it goes wrong:** retry. A partial set is harmless because nothing reads these paths yet. A corrected value is a new version, so update the expected versions in the ticket. Running pods adopt it within 5 minutes.

### 5. Build and review the code change

- **Starts when:** any time, but it must not merge before step 4.
- **What it does:** one PR containing the runtime changes from Part 1 (secrets module, per-request clients, gated `/healthz`, dev support) and these rollout pieces:
  - The three `api_key` lines are removed from `config/app.yaml`. `base_url`, timeouts and `from_address` stay.
  - The loader fails loudly if `api_key` appears in the YAML.
  - A CI check fails any change that puts an `api_key` back into `config/app.yaml`. It parses the YAML and fails on an `api_key` key at any depth, and also scans for `pk_live_`, `ml_live_` and `geo_live_`. It has a test fixture and is a required status check in branch protection.
  - Redaction so a `Secret`'s `repr` and `str` print `<redacted>`.
  - Tests for each Part 1 behavior. One test asserts a sentinel key never appears in captured logs or `os.environ`.
- **Where data lives:** git. The PR holds no key values.
- **If it goes wrong:** CI or review fails, nothing merges, nothing deploys.

### 6. Staging deploy and failure drills

- **Starts when:** the PR is approved and the staging and dev secrets exist.
- **What it does:** preferred order is deploy the PR-branch image to staging, run the drills, merge, then prod deploy. If the pipeline cannot deploy a PR-branch image, merge first so CI builds the image, deploy it to staging, and hold the prod deploy until the drills pass. This is safe because the prod secrets already exist and rollouts halt on a pod that is not ready. Staging pods still on the old image keep using old keys from their YAML until replaced. New staging pods use the sandbox keys.

  Drills:
  - Store unreachable at startup: the pod retries, exits non-zero, and the rollout halts.
  - A new version written to staging is adopted by every pod within 5 minutes with no restart.
  - Block the store during a refresh: a warning is logged and traffic continues on the last good value.
  - Revoke a sandbox key mid-run: the 401 path re-reads and retries once.
  - Check logs and `os.environ` for key values.
- **Where data lives:** staging pod memory and the staging store.
- **If it goes wrong:** fix, rebuild, redeploy staging. Prod is untouched.

### 7. Prod rolling deploy

- **Starts when:** the drills passed, the PR is merged, and the security on-call is available.
- **What it does:** the deploy runs one pod at a time with `maxUnavailable: 0`. Each new pod fetches the prod secrets as `orders-api-prod`, reports ready, and only then is an old pod stopped. New pods use the new keys. Old pods keep the old keys, because the old image is immutable and carries its own copy of `config/app.yaml` with the old keys. Both keys are valid. Old pods never call the store, so a store outage affects only new pods.

  After the first new pod, pause. Look at that pod's outbound provider calls in the central logs or metrics and compare its error rate with the old pods. Stop and roll back on any provider 401 or 403, or a clearly higher error rate. Soak length and threshold are the team's choice.

  The engineer running the deploy decides to roll back and tells the security on-call. Rollback redeploys the previous image under the same rolling rules, so it is safe while the old keys are not revoked.
- **Where data lives:** pod memory. The store holds the versions.
- **If it goes wrong:** a new pod that cannot read the store exits, never becomes ready, and the rollout halts with old pods serving. Fix access and resume.

### 8. Confirm every instance is on the new keys (gate before revocation)

- **Starts when:** the rollout is complete.
- **What it does:** check all three and record them in the ticket:
  1. Every orders-api pod, job and script in every environment runs the new image digest. Only an old-image pod holds an old key, so this catches those.
  2. For every live pod, the latest `secrets_refreshed` line shows the expected version ids. The expected version is the latest id in the store at check time (metadata only). It must match the ticket, including any corrected write. Query the central logs and group by pod name, then compare against the current pod list so a silent pod is caught. A pod whose latest line is older than one refresh interval plus a margin fails. This catches a stuck or silent new pod.
  3. Each provider shows the old key's last-used time older than one refresh interval plus a margin, with no unknown callers. The margin must exceed the provider's recorded lag. This catches callers outside the pod list.
- **Where data lives:** central logs, the cluster pod list and provider usage data.
- **If it goes wrong:** revoke nothing. Find and migrate or stop whatever still uses an old key, then repeat.

### 9. Block rollback to pre-migration images

- **Starts when:** the gate passed, just before revocation.
- **What it does:** mark every image built before the migration PR's merge commit as non-deployable in the deploy pipeline, and remove them from the registry. A pre-migration image carries the old keys, so after revocation it would fail every provider call. The gate already showed no running pod uses one, and a rescheduled pod pulls the image named in the current deployment, which is the new one.
- **Where data lives:** deploy pipeline config.
- **If it goes wrong:** do not revoke. Without this guard a rollback would break customer requests.

### 10. Revoke old keys, one provider at a time

- **Starts when:** steps 8 and 9 are done, with sign-off from the security on-call and one engineer.
- **What it does:** revoke in order of blast radius: geocoding, email, payments. If the provider supports suspending a key, suspend first and watch for one refresh interval, then delete. Watch the provider's record of rejected attempts on the old key (it names the caller) and orders-api's own provider 401 and 403 rate against normal. A rejected attempt on the old key means a missed caller. A rise in 401s with no rejected attempt on the old key points elsewhere, such as the new key, so investigate that first. Move to the next provider only when the previous one is clean.
- **Where data lives:** the provider accounts.
- **If it goes wrong:** re-enable the suspended key at once if the provider allows, find the caller, and repeat the gate for it. Deletion is irreversible, so delete only after a clean suspension.

### 11. Prove the CI guard

- **Starts when:** the PR has merged.
- **What it does:** open a throwaway PR that re-adds an `api_key` line to `config/app.yaml`. Confirm the check fails and branch protection blocks the merge. Close it unmerged.
- **Where data lives:** CI and branch protection settings.
- **If it goes wrong:** fix the check or protection. It is off the customer path, so it can wait until after the critical steps.

### 12. Close out

- **Starts when:** steps 10 and 11 are done.
- **What it does:** search the 30-day central logs for `pk_live_`, `ml_live_` and `geo_live_`. If any appears, rotate that key and ask the log service to purge it. The old keys stay in git history but are revoked. Write a short runbook covering store layout, rotation and the confirmation gate. Hand the rotation-cadence question to security.
- **Where data lives:** repo docs and the ticket.
- **If it goes wrong:** log a follow-up ticket and do not mark the migration complete.

### Later rotations

Any later rotation repeats: issue and validate a new key (step 3), write it to the store (step 4), wait up to 5 minutes for pods to adopt it, run the confirmation gate (step 8), then revoke the old key (step 10). Never revoke before the gate passes.

## What happens when things fail

| Moment | What happens |
|---|---|
| New keys issued, old still active (3, 4) | Both valid, and nothing reads the new ones yet |
| Mixed rolling deploy (7) | Old pods use old keys, new pods use new keys, both valid |
| New pod cannot load keys (Part 1 step 2) | It exits, never becomes ready, rollout halts, old pods serve |
| Store outage while running (Part 1 step 5) | Pods keep the last good value and stay ready |
| Rollback during rollout (7) | Old keys not yet revoked, so safe |
| Revocation (10) | Only after the gate confirms no instance or caller uses the old key, and old images are blocked |

## Open questions

- **Rotation cadence (owner: security).** Security has not decided whether keys must also be rotated on a schedule, or how often. This plan picks no cadence. The mechanism supports any cadence (see Later rotations). Needed before close-out, because the answer decides whether a reminder or scheduler is added.
- **Caller behavior after a provider error (owner: orders-api team).** When a provider call still fails after the retry, the client returns the error to its caller. The files given do not show whether the order is marked failed or who retries it. That is existing order code and this plan does not change it.
- **Provider last-used data (owner: security on-call).** Where each provider shows the old key's last-used time, and how stale it can be, is not known. Rollout step 1 records it for each provider.
- **Store product and identity mechanism (owner: security).** The brief does not name them. Rollout steps 1 and 2 record and verify them.