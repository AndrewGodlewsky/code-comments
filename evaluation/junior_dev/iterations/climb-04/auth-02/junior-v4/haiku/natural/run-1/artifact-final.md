# Migrating orders-api third-party API keys to the managed secret store

Status: draft plan for review. Key rotation cadence is an open security decision (see Open questions).

## Summary

Today `config/app.yaml` holds three live provider keys (payments, email, geocoding). Git stores the file, every container image contains it, and the app reads it once at start and copies each key into its client. Changing a key means a new image and a redeploy.

After the migration, the keys live in the managed secret store under `orders-api/<env>/<name>`. The app reads them at startup, re-reads them every 5 minutes, and keeps the last good value if a re-read fails. The config file holds only non-secret settings. The rollout creates new keys at each provider, writes them to the store, deploys an image that reads from the store, and only then revokes the old keys.

## Terms

- **Key A**: the current key, committed to git. Treat it as leaked.
- **Key B**: the new key created at each provider.
- **Secret store**: the managed store that holds the keys. It encrypts them per environment and gives every write a new version id.
- **Version id**: the id the store returns for each write. The app logs it and uses it to detect a change.
- **Workload identity**: the identity the cluster gives a pod. The store uses it to decide what the pod may read.
- **v1 image**: today's image. It contains key A.
- **v2 image**: the new image. It contains no keys.
- **Key cache**: the in-memory holder of the three values, each with its version id and fetch time.
- **Readiness**: `GET /healthz` returns 200. A pod receives traffic only when it is ready.

## Gates and assumptions

- **Blocking gate: provider overlap.** Each provider must accept two active keys at once, so v1 pods (key A) and v2 pods (key B) can run together during the rollout. If a provider cannot, stop for that provider before Step 5 and agree an alternative with security.
- Prod runs 4 replicas, all from one image, under identity `orders-api-prod`.
- Key A stays valid at its provider until Step 9.

## Part 1: Rollout

Each step lists what starts it, what it does, where its data is kept, and what happens if it fails.

### Step 1. Inventory consumers and confirm the gate

- **Starts:** migration kickoff. Nothing has changed yet.
- **Does:** list every user of key A: prod pods, CI jobs, local runs, scripts, other services and provider-side integrations. Confirm the overlap gate for each provider. List every v1 image still in the registry.
- **Keeps data:** a tracking issue. It contains no key values.
- **On failure:** a consumer that cannot be found blocks Step 9 only. A provider that fails the overlap gate stops the migration for that provider.

### Step 2. Set store paths and access policy

- **Starts:** Step 1 done.
- **Does:** create `orders-api/dev/*` and `orders-api/prod/*`, with these rules:
  - `orders-api-prod` reads `orders-api/prod/*` and nothing else.
  - Only the security on-call role writes `orders-api/prod/*`.
  - Engineers read `orders-api/dev/*` only. They cannot read or list prod.
- **Keeps data:** the store's access policy.
- **On failure:** if engineers can read prod, or the prod identity can read another path, stop. Automated allow and deny tests for each identity must pass before Step 5.

### Step 3. Set up dev values and local runs

- **Starts:** Step 2 done.
- **Does:** create sandbox keys at each provider that offers them, and write them to `orders-api/dev/*`. Local runs load dev values through the same loader, using the engineer's identity. Local runs never use live keys. Offline mode uses stub provider clients and needs no network or store access.
- **Keeps data:** dev values in the store. Values exist only in process memory while the app runs.
- **On failure:** an engineer without dev access uses offline mode. Nobody falls back to prod. A provider with no sandbox is covered by offline mode.

### Step 4. Build the code change on a branch (no merge yet)

- **Starts:** Step 3 done.
- **Does:** implement Part 2 on a branch. Remove `api_key` from `config/app.yaml`. Add the CI guard (see CI guard below) to the same branch. Run tests in dev. The tests cover:
  - startup retries and non-zero exit,
  - a successful refresh replacing the value,
  - a failed refresh keeping the last value and logging a warning,
  - clients reading the current value,
  - no secret value in logs, `repr` or exception text.
- **Keeps data:** a feature branch and a PR. Nothing is deployed.
- **On failure:** failing tests block the merge. Customers are not affected.

### Step 5. Create key B and write it to prod

- **Starts:** Step 4 green in dev, and the security on-call is available.
- **Does:** for each provider, the on-call creates key B while key A stays active. The on-call writes B to `orders-api/prod/<name>`. Record the version ids in the change ticket, never the values. Check in the provider console that B is active.
- **Keeps data:** B at the provider, and B in the store with its version id.
- **On failure:**
  - If B cannot be created, A still works. Retry.
  - If the store write fails, A still works. Retry.
  - A bad B is replaced by writing a new version.
  - This step changes nothing for v1 pods. They keep key A in memory from their image. Only v2 pods read the store.

### Step 6. Merge and build image v2

- **Starts:** Step 5 recorded in the ticket. Do not merge earlier, because a merge builds an image that could be deployed.
- **Does:** merge the PR to `main`. CI builds v2. Its config has no `api_key`, and the CI guard is on.
- **Keeps data:** the image in the registry, identified by its digest.
- **On failure:**
  - If tests or the guard fail before the merge, fix the branch and do not merge.
  - If CI fails after the merge, do not deploy v2. Fix forward.

### Step 7. Roll out v2 to prod

- **Starts:** an operator starts the deploy after Step 6 is approved. The deploy tool and trigger are an open question.
- **Does:** the rollout replaces one pod at a time, with `maxUnavailable: 0`. Each new pod loads the three keys at startup (see Runtime: startup), and it becomes ready only after that. Old v1 pods keep serving with key A.
- **Keeps data:** the store holds the keys. Pod memory holds the values. The image holds no keys.
- **Mixed state:** A pods and B pods run together. Both must work at the provider (see the overlap gate).
- **On failure:**
  - Store unreachable, or access denied: the new pod retries, then exits non-zero. It never becomes ready, so the rollout halts and the old pods keep serving. Fix the identity or network problem and redeploy. Do not force the rollout.
  - Provider rejects B (401 or 403 from v2 pods): halt the rollout and roll back to v1. Key A is still active, so v1 works. Investigate B in the provider console.

### Step 8. Verify and soak

- **Starts:** the rollout completes with all 4 pods on v2.
- **Does:** confirm all 4 pods run the v2 digest. Confirm each pod logged its version ids at startup. Confirm the provider 401 and 403 rate stays at baseline. Hold a soak period longer than one 5-minute refresh cycle plus the rollback window. The owner sets its length.
- **Keeps data:** central logs (30-day retention), deploy status and provider dashboards.
- **On failure:** if any pod still runs v1, or a pod is missing version ids, do not start Step 9. Investigate first.

### Step 9. Revoke key A at each provider

- **Starts:** the Step 8 soak passed, and every consumer from Step 1 is confirmed off key A.
- **Does:** the security on-call revokes key A at one provider at a time, after that provider's checks pass. All checks are required:
  - no pod runs the v1 digest,
  - no consumer uses key A,
  - dev and CI use no live keys.
- **Keeps data:** the provider console.
- **On failure:** revocation usually cannot be undone. If a missed consumer breaks, issue a new key D and write it to `orders-api/prod/<name>`. v2 pods pick it up within 5 minutes, without a restart. After this step, v1 is no longer a rollback target. Roll back only to v2 or later.

### Step 10. Clean up and close

- **Starts:** Step 9 done for all providers.
- **Does:** remove copies of key A from working copies, CI variables and `.env` files. Scan the repo, the built images and the central logs for `pk_live_`, `ml_live_` and `geo_live_`. Mark v1 images do-not-deploy in the registry, but keep them for audit. Do not rewrite git history. Close the tracking issue.
- **Keeps data:** the tracking issue, with findings and no key values.
- **On failure:** any copy left behind is already revoked, so there is no customer impact. Record it and escalate to security.

## Part 2: How the app reads keys at runtime

The app keeps the three keys in the key cache, in memory only. It loads them before it serves traffic, re-reads them every 5 minutes, and keeps the last good values if a re-read fails. The config file holds only non-secret settings.

### Config and startup guard

- `config/app.yaml` keeps only non-secret settings: app name, port, log level, each `base_url`, `timeout_seconds` and `from_address`.
- Secret names are constants in code, mapped to `orders-api/<env>/<name>`.
- The environment comes from the deployment setting `APP_ENV`, not from the yaml file.
- If the yaml contains an `api_key` at any depth, the loader exits non-zero.

### Startup

- **Starts:** process start.
- **Does:**
  1. Read the non-secret yaml, as today.
  2. Create the store client with the pod's workload identity. No static credentials are stored on disk.
  3. Fetch the three secrets. If a fetch fails, retry 3 times, 2 seconds apart. If every attempt fails, log the error with no values and exit non-zero.
  4. Store each value in the key cache with its version id and fetch time. Log the version id of each loaded secret. Each swap is atomic.
  5. Start the refresh timer.
  6. Bind the HTTP port and start serving. The port is not bound until step 4 succeeds, so a listening pod always has keys.
- **Keeps data:** the key cache, in memory only.
- **On failure:** if the store cannot be reached or access is denied after the retries, the process exits non-zero. The pod never listens and never becomes ready.

### Clients

- **Starts:** each provider call.
- **Does:** `PaymentsClient`, `EmailClient` and `GeocodingClient` keep a reference to the key cache, not a copy of the key. Each call reads the current value. A call that has already read a value keeps it, even if a refresh swaps in a new one during the call.
- **Keeps data:** nothing new. The key cache is the only holder.
- **On failure:** see Provider errors below.

### Refresh

- **Starts:** a timer every 300 seconds, with a small random jitter.
- **Does:** fetch all three secrets. If a version id changed, swap in the new value and log `rotated <name> to version <id>`.
- **Keeps data:** the key cache, in memory only.
- **On failure:** keep the last good value. Log a warning with the secret name, the version id still in use and the error class. Never log the value or the raw response. Try again on the next cycle.
- **Monitoring:** expose the time since the last successful refresh as a metric. The alert threshold is an open question.

### Readiness and liveness

- Readiness (`/healthz`) returns 200 only after startup has loaded the keys and the server is running. A pod without keys is never ready.
- A store outage after startup does not change readiness. The pod keeps its last good values and keeps serving.
- Liveness is separate and does not depend on the store.

### Provider errors

- **Starts:** a provider returns 401 or 403.
- **Does:** log the status and the version id in use. Never log the key.
- **Keeps data:** nothing new.
- **On failure:** the call fails. A key revoked before the pod refreshes causes 401 or 403 until a refresh gets a newer version. Readiness stays green during this time.
- Logs, tracebacks and HTTP client debug output must never contain the `Authorization` header or a request body with a key. A redaction filter enforces this, and a test covers it.

### Memory rules

- Key values exist only in the key cache.
- No environment variables, temp files or on-disk cache hold values. Values are not passed to subprocesses.
- Core dumps are disabled where the platform allows. The platform team confirms this.
- Logging version ids is fine.

### CI guard

Added on the Step 4 branch, and live once the Step 6 merge lands. On every PR and every image build:

- parse `config/app.yaml` and fail on any `api_key` at any depth;
- scan changed files for `pk_live_`, `ml_live_`, `geo_live_`, and for `api_key:` with a literal value;
- scan the built image's config for `api_key`.

## Failure summary

| Where | What happens | Customer impact |
|---|---|---|
| Startup, store unreachable | Retries, then exits non-zero. Pod never ready. Old pods keep serving. | None |
| Refresh fails | Keeps last good value, logs a warning. | None while the value still works |
| Provider rejects B on a v2 pod | Halt and roll back to v1 while A is active. | Affected requests fail until rollback |
| Pod holds a key that is revoked before it refreshes | Calls fail with 401 or 403 until a refresh gets a newer version. Readiness stays green. | Yes, until refresh |

## Open questions

1. **Secret store product and workload identity mechanism.** The brief does not name the product or how a pod proves its identity. Confirm both before Step 2.
2. **Deploy tool and trigger.** `deploy.md` describes the rolling policy but not the tool or who starts it.
3. **On-call write tool, and how engineers authenticate for dev reads.** Not specified.
4. **Retry count at startup.** Read as one attempt plus 3 retries, about 6 seconds of waiting. Confirm.
5. **Secret names.** `payments_api_key` is given. `email_api_key` and `geocoding_api_key` are assumed. Confirm.
6. **Immediate refresh on 401.** Decide whether to add a rate-limited refresh and one retry on a 401. It shortens the window in which a revoked key causes failures.
7. **Staleness alert threshold.** The owner sets it.
8. **Soak length and rollback window.** The owner sets them.
9. **Key rotation cadence after migration.** Security has not decided whether keys need scheduled rotation, or how often. This plan sets no interval. The refresh in Part 2 works for any cadence without a restart. Any future rotation must write the new key and let pods refresh before the old key is revoked, the same rule this migration follows.