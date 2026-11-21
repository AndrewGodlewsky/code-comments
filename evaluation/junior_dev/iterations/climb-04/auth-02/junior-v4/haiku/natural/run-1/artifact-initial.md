# Migrating orders-api third-party API keys to the managed secret store

Status: draft plan for review. Security decisions on key rotation cadence are open (see Open questions).

## Assumptions and gates

- **G1 (blocking).** Each provider (payments, email, geocoding) lets two keys be active at the same time. Old pods (key A) and new pods (key B) both have to succeed during the rollout. If a provider cannot do this, stop before Step 5 for that provider and agree an alternative with security.
- **A2.** Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`, under `orders-api/<env>/`. Only `payments_api_key` is given in the brief; the other two names are assumed.
- **A3.** "Retry 3 times, 2 seconds apart" is read as one initial attempt plus 3 retries (4 attempts, about 6 seconds of waiting). Confirm before implementation.
- **A4.** Prod runs 4 replicas, all on one image, under identity `orders-api-prod`.
- **A5.** Key A stays valid at its provider until Step 9. Every key value ever committed (A) is treated as leaked from the start.

## Part A: Rollout

Each step lists what starts it, what moves where, where the state lives, and what happens on failure.

### Step 1. Inventory consumers and confirm gates

- **Starts:** migration kickoff. Nothing has changed yet.
- **Moves:** list every consumer of keys A: prod pods, CI jobs, local `make run`, scripts, other services, and any provider-side integrations. Confirm G1 for each provider. List every image built from `main` that contains `config/app.yaml` with keys; those images are treated as holding leaked keys.
- **State:** a tracking issue in the issue tracker. It contains no key values.
- **On failure:** if a consumer cannot be found, it blocks Step 9 only, not the rollout. If G1 fails for a provider, stop for that provider here.

### Step 2. Set store paths and access policy

- **Starts:** Step 1 complete.
- **Moves:** create `orders-api/dev/*` and `orders-api/prod/*`. Set the policy so that:
  - `orders-api-prod` has read-only access to `orders-api/prod/*` and nothing else.
  - Only the security on-call role can write `orders-api/prod/*`.
  - Engineers can read `orders-api/dev/*` only, and cannot read or list `orders-api/prod/*`.
- **State:** the managed store's access policy. Writes get version ids from the store.
- **On failure:** if engineers can read prod, or prod identity can read another path, stop. Do not continue to Step 5 until a policy test shows the intended behavior. Automated tests should check allow and deny for each identity.

### Step 3. Set up dev and local runs

- **Starts:** Step 2 complete.
- **Moves:** create separate sandbox or test keys (C) at each provider, if the provider offers them, and write them to `orders-api/dev/*`. Change `make run` to load dev values through the same runtime loader, using the engineer's own identity. Stop using live keys locally. Add an offline mode that uses stub provider clients for work without network access.
- **State:** dev store entries. Dev values live only in the local process memory, the same as prod.
- **On failure:** if an engineer cannot read dev, they use offline mode. Nobody falls back to prod values. If a provider has no sandbox, offline mode covers that provider.

### Step 4. Build the code change on a branch (do not merge yet)

- **Starts:** Step 3 complete.
- **Moves:** implement the runtime design in Part B. Remove `api_key` from `config/app.yaml` on the branch only. Add the CI guard from B10 in the same branch. Run tests in dev. Tests cover:
  - startup retry count and non-zero exit,
  - refresh success replacing the value,
  - refresh failure keeping the last value and logging a warning,
  - clients reading the current value,
  - no secret value in logs, `repr`, or exception text.
- **State:** a feature branch and PR. No prod deploy.
- **On failure:** failing tests block the merge. Nothing customer-facing has changed.

### Step 5. Rotate at providers and write new prod values

- **Starts:** Step 4 green in dev, and the security on-call is available.
- **Moves:** for each provider, the on-call creates new key B while A stays active (G1). The on-call writes B to `orders-api/prod/<name>`. Record the version ids in the change ticket. Do not record values. Verify in the provider console that B is active. Values are not pasted into chat, tickets, or git.
- **State:** provider consoles, and store versions with version ids.
- **On failure:** if the provider cannot issue B, A is still active, so customers are unaffected. Stop and retry. If the store write fails, A is still active. Retry the write. A bad B can be replaced by writing a new version. Pods pick it up within 5 minutes on refresh, or at their next start.

### Step 6. Merge the code change and build image v2

- **Starts:** Step 5 recorded (version ids in the ticket). Do not merge before this, because a merge may build an image that is deployed.
- **Moves:** merge the PR to `main`. CI builds image v2. Its `config/app.yaml` has no `api_key`, and the CI guard (B10) is on from this merge.
- **State:** the image in the registry, identified by digest.
- **On failure:** if the guard or tests fail, fix the branch before merging. Confirm that v2 is not auto-deployed before Step 7 is approved.

### Step 7. Rolling deploy of v2 to prod

- **Starts:** an operator starts the deploy after Step 6. The rollout uses `maxUnavailable: 0`.
- **Moves:** each new pod loads the 3 keys from the store under `orders-api-prod` (B1 to B5), then binds the port and passes readiness. Old v1 pods keep serving with key A, which is still valid. The rollout therefore has mixed A and B pods, and both are valid.
- **State:** the store is the source of truth for keys. Pod memory holds the values. The image holds no keys.
- **Failure modes:**
  - Store unreachable, or access denied: the new pod retries 3 times, then exits non-zero. It never becomes ready, the rollout halts, and the old pods keep serving. Fix the identity or network problem and redeploy. Do not force the rollout.
  - Provider rejects B on a new pod: the provider returns 401 or 403 for pods on v2. Halt the rollout and roll back to v1 (valid while A is active). Investigate B in the provider console.
  - Rollback before Step 9: redeploy v1 is allowed. After Step 9, v1 is not a valid rollback target (see Step 9).

### Step 8. Verify and soak

- **Starts:** the rollout completes with all 4 pods on v2.
- **Moves:** confirm all 4 pods run the v2 digest. Confirm each pod logged the B version ids at startup. Confirm the provider 401 and 403 rate is at its baseline, with no increase from v2 pods. Hold a soak period that the owner sets. It must be longer than one 5-minute refresh cycle plus the rollback window.
- **State:** central logs (30-day retention), deploy status, provider dashboards.
- **On failure:** if any pod is still on v1, or a pod is missing version ids, do not start Step 9. Investigate first.

### Step 9. Revoke key A at each provider

- **Starts:** the Step 8 soak passed, and every consumer from Step 1 is confirmed off A. This is the gate required by the brief.
- **Moves:** the security on-call revokes A at the provider. Do this per provider, after that provider's gate passes.
- **Gate checks, all required:**
  - no pod runs the v1 digest,
  - no consumer uses A,
  - dev and CI use no live keys.
- **State:** provider consoles.
- **On failure:** revocation cannot be undone at most providers. If a missed consumer breaks after revocation, issue a new key D and write it to `orders-api/prod/<name>`. v2 pods pick it up within 5 minutes through refresh, without a restart. After this step, v1 is no longer a rollback target, so the rollback target is a v2 or later image.

### Step 10. Clean up copies and confirm no leaks remain

- **Starts:** Step 9 done for all providers.
- **Moves:** remove copies of A from working copies, CI variables, and `.env` files. Scan the repo, the built images, and the central logs for the provider prefixes `pk_live_`, `ml_live_`, and `geo_live_`. Mark v1 images as do-not-deploy in the registry, but keep them for audit. Do not rewrite git history, per the decision in the brief.
- **State:** the findings are recorded in the tracking issue, with no key values.
- **On failure:** any remaining copy is already revoked, so there is no customer impact. Record it and escalate to security.

### Step 11. Remove migration scaffolding

- **Starts:** one release after Step 9.
- **Moves:** remove any temporary compatibility code used during the migration, and close the tracking issue after the Step 1 consumer list is checked off.
- **State:** the repo and the tracking issue.
- **On failure:** if scaffolding is still needed, keep it and record why.

## Part B: How the app reads keys at runtime

### B1. Config split

`config/app.yaml` keeps only non-secret settings: `app.name`, `app.port`, `app.log_level`, each `base_url`, `timeout_seconds`, and `from_address`. The secret names are constants in code, mapped to `orders-api/<env>/<name>`. The environment is set by a deployment setting, not by the yaml file.

### B2. Startup sequence

1. Read the non-secret yaml once, as today.
2. Create the store client with the pod's workload identity. No static credentials are stored on disk.
3. Fetch the 3 secrets. Retry the whole fetch 3 times, 2 seconds apart (A3). If it still fails, log the error with no values and exit non-zero.
4. Store the values in an in-memory `SecretCache`. Each entry holds the value, the version id, and the fetch time. Each replacement is atomic.
5. Start the background refresher (B4).
6. Bind the HTTP port and start serving. The socket is not bound until step 4 succeeds, so a listening pod always has keys.

### B3. Clients read through the cache

`PaymentsClient`, `EmailClient`, and `GeocodingClient` keep a reference to the cache. They do not copy the key in `__init__`. Each call reads the current value, for example `self._secrets.get('payments_api_key')`. Module-level singletons are fine, because they hold a reference to the cache and not to the value.

### B4. Refresh every 5 minutes

- **Trigger:** a timer every 300 seconds, with a small random jitter.
- **Moves:** fetch all 3 secrets. If a version id changed, swap in the new value and log `rotated <name> to version <id>`.
- **On failure:** keep the last good value. Log a warning with the secret name, the version id still in use, and the error class. Never log the value or the raw response. Try again on the next cycle.
- **Monitoring:** expose the time since the last successful refresh as a metric. The alert threshold is an open question.

### B5. Readiness and liveness

- `/healthz` (readiness) returns 200 only after the startup load succeeded and the server is running. This makes the readiness check explicit. Today it only means the server is listening.
- A store outage after startup does not flip readiness, because the pod keeps its last good values. This prevents rolling restarts during a store outage.
- Liveness is separate and does not depend on the store.

### B6. Request-path failures

- A 401 or 403 from a provider is logged with the provider status and the version id in use. The key is not logged.
- Option, to be decided by the owner: on a 401 from a provider, trigger one rate-limited immediate refresh and retry the call once. This shortens the gap after a revocation.
- Error logs, tracebacks, and HTTP client debug output must not contain the `Authorization` header or any request body with a key. Add a redaction filter and test it.

### B7. Memory handling

- Values exist only in the `SecretCache` object.
- Do not use environment variables, temp files, or any on-disk cache for values.
- Do not pass values to subprocesses.
- Disable core dumps for the container where the platform allows it. Confirm this with the platform team.

### B8. Startup guard

If the non-secret yaml contains an `api_key` key at any depth, the loader exits non-zero. This is defense in depth behind the CI guard.

### B9. Local development

`make run` uses the same loader in dev mode, with the engineer's identity, which reads `orders-api/dev/*` only. Offline mode uses stub clients. Prod values are never reachable locally.

### B10. CI guard

On every PR and on every image build:
- parse `config/app.yaml` and fail on any `api_key` at any depth;
- scan changed files for the provider prefixes `pk_live_`, `ml_live_`, and `geo_live_`, and for `api_key:` with a literal value;
- scan the built image's config for `api_key`.

The guard is turned on in the same change that removes the keys (Step 6).

## Open questions

1. **Key rotation cadence after migration.** Security has not decided whether keys need scheduled rotation, or how often. This plan does not set an interval. The refresh mechanism in B4 works for any cadence without a restart.
2. **Provider overlap (G1).** Must be confirmed for each provider before Step 5.
3. **Soak length and rollback window (Step 8).** The owner sets these.
4. **Staleness alert threshold (B4).** The owner sets this.
5. **Immediate refresh on 401 (B6).** Decide whether to add it.
6. **Retry count (A3).** Confirm the interpretation.
7. **Secret names (A2).** Confirm `email_api_key` and `geocoding_api_key`.