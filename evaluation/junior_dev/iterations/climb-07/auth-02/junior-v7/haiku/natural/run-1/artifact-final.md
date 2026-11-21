# orders-api: move the three third-party API keys into the managed secret store

## Summary

`orders-api` keeps three live provider keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to git and copied into every container image. The keys have been in git for two years, so all three are treated as leaked. This plan moves them into the managed secret store and has the app read them at startup, every 5 minutes, and on each provider call. The rollout loads new keys first, replaces prod pods one at a time, and disables the old keys only after every running pod is on the new ones, so no customer request fails.

Today the app reads `config/app.yaml` once, when the module is first imported, and each provider client copies its key into itself when it is built. `/healthz` returns `ok` as soon as the HTTP server listens. Rollback means redeploying an earlier image, which brings back that image's baked-in keys. `make run` reads the same file, so local runs use the live keys today.

## Terms

- **Provider:** a third-party company whose API the app calls.
- **Secret store:** the company's managed service that holds secret values, encrypts them and keeps every version. The product is not named (open, see Open questions).
- **Secret path:** the name of one secret in the store, in the form `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. `<env>` is `dev` or `prod`.
- **Version id:** the id the store gives each write. Every write creates a new version. The latest version is the newest id for that name.
- **KMS key:** a key-management key that encrypts data at rest. Each environment has its own.
- **Service identity:** the login a running workload uses to call the store. Prod pods run as `orders-api-prod`.
- **APP_ENV:** an environment variable that names the environment the app runs in, `dev` or `prod`. It is not a secret. `make run` sets it to `dev`. Prod pods are set to `prod` by their deployment (open, see Open questions).
- **Pod:** one running copy of the app in the cluster. Prod runs 4 pods.
- **Readiness:** whether the cluster sends traffic to a pod. `/healthz` returns 200 when the pod is ready and 503 when it is not.
- **Liveness probe:** a check that restarts a pod when it is stuck. This plan adds none.
- **Rolling deploy with `maxUnavailable: 0`:** pods are replaced one at a time. A new pod must be ready before an old pod stops.
- **Startup gate:** the code in `main()` that loads all three secrets before the app reports ready.
- **SecretCache:** the in-memory copy of the current secret values. Each entry is an immutable snapshot `{value, version_id, fetched_at}`. The cache swaps in a new snapshot by replacing one reference.
- **Sandbox key:** a provider test key that is not live. Dev uses these.
- **Soak period:** the wait between disabling an old key and deleting it. Security sets it.
- **Migration marker:** a tag or label that CI adds to each image built from the migration PR onward.
- **Core dump:** a file a crashed process writes, which can contain key values from memory.
- **Jitter:** a random delay added to a timer, so pods do not act at the same moment.

## Assumptions

Each one is checked in Step 0 or listed under Open questions.

- Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`. The brief fixes only the pattern and the payments example.
- Environments are `dev` and `prod`. Any other environment, such as staging, uses the `dev` pattern.
- Each provider can keep two keys active at once and can disable a key before deleting it. Step 0 checks this.
- Merging to `main` builds an image but deploys nothing. Deploys are a separate promotion.
- The deploy pipeline can reject images by build date or tag.

---

## Part A. How the app reads keys at runtime

**Rules for all of Part A.** Key values are never logged, printed, put in exception messages, written to disk, or put in environment variables. Only version ids are logged. Central logs are kept for 30 days.

### A1. Startup gate

- **Starts:** process start. The HTTP server starts listening first, so `/healthz` can answer. Then the gate runs.
- **Reads:** the secret store, as the pod's identity (`orders-api-prod` in prod, or the developer's dev identity locally). It fetches the latest version of all three secrets.
- **Attempt:** one attempt fetches all three secrets. The attempt fails if any one of them fails or is missing. A failed attempt keeps nothing. The next attempt fetches all three again.
- **Retry:** up to 3 retries, which is 4 attempts in total, 2 seconds apart (open, see Open questions).
- **Moves:** after a full successful attempt, each value goes into the SecretCache, in memory.
- **Success:** the app marks itself ready. `/healthz` returns 200 only from this point and 503 before it. This replaces today's behaviour, where `/healthz` returns `ok` as soon as the server listens.
- **State:** process memory only.
- **On failure:** log the secret names and error classes, never values. Exit non-zero. Kubernetes restarts the container, and the gate runs again from the start, with the usual crash-loop backoff. The pod crash-loops, the rolling deploy halts because `maxUnavailable` is 0, and the old pods keep serving.
- **No liveness probe.** A pod that returns 503 is not ready, and it is not killed for that.

### A2. Refresh loop

- **Starts:** a timer, every 5 minutes after readiness. Each pod adds up to 30 seconds of jitter, so the four pods do not read in lockstep.
- **Moves:** for each secret, fetch the latest version. If the version id changed, build a new snapshot and swap it in. Log `secret=<name> version=<old>-><new>`. A client call that starts after the swap uses the new key. A request already in flight keeps the key it read and finishes with it. The old key stays valid until Step 6, so that request succeeds.
- **State:** memory. Each successful read sets `secret_last_success_timestamp{name}`. The version id is exposed as the metric `secret_version{name,version}`. The same version change is also in the central logs, which Step 5 can use if the metric is not available.
- **On failure, per secret:** keep the last good snapshot. Log a warning with the secret name, the version id still held and the error. Increment `secret_refresh_failures_total{name}`. There is no maximum age, so the app keeps the last good value indefinitely.
- **Staleness:** staleness is now minus `secret_last_success_timestamp`. Alert on staleness, not on the warning alone. The threshold and the recipient are open (see Open questions).
- **Optional, recommended: 401 re-read.** When a provider client gets HTTP 401 on a call, it asks the cache for one extra re-read, at most once per 60 seconds. This shortens the window after a sudden revocation. The brief does not require it. Each 401 increments `provider_auth_failures_total{name}`. The request that got the 401 fails with a clear error, and this plan does not retry it. The re-read changes only calls that start after it.

### A3. Client reads

- `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying their key in `__init__`. Each HTTP call to a provider reads the current snapshot when the call is made, for example `secrets.get('payments_api_key')`, and puts the key in the `Authorization: Bearer` header.
- A retried call reads the snapshot again. One HTTP request uses one snapshot, so no request mixes two key versions. Today `PaymentsClient` makes one POST per charge, so no call spans several keys.
- `config/app.yaml` keeps only non-secret settings: `base_url`, `timeout_seconds`, `from_address`, `port` and `log_level`.
- `app/config_loader.py` no longer fetches secrets at import time. Import-time fetching would make tests and local runs hit the store, and would bypass the startup gate. Settings still load at import. Secrets load only in `main()`.
- **On failure:** if the cache is empty, the client raises a clear error and the request fails. The gate should make this impossible, so any occurrence is a bug.

### A4. Memory and logging checks

- Check the HTTP client's debug logging and exception formatting. Both can include the `Authorization: Bearer` header.
- There are no secret env vars, no mounted secret files and no Kubernetes Secret objects. The app calls the store directly with its own identity, so nothing lands on disk or in the environment.
- Core dumps are turned off in prod containers, or confirmed as not collected.

### A5. Local development

- **Local run:** `make run` sets `APP_ENV=dev` and reads `orders-api/dev/*` with the developer role. That role can read dev only. The dev values are sandbox keys, not live keys.
- **Guard:** the guard runs on every start, using `APP_ENV`.
  - When `APP_ENV` is `dev`, startup refuses to run if the identity is `orders-api-prod`.
  - On every start, startup refuses to run if the secret path does not start with `orders-api/<APP_ENV>/`.
  - Prod pods run with `APP_ENV=prod` and the identity `orders-api-prod`, so they pass the guard. Locally, `make run` sets `APP_ENV=dev`, so the prod identity is refused.
  - The guard reads the identity name from the store login for the process. If that name cannot be read, startup refuses to run. The guard fails closed. How the store reports the name is open (see Open questions).
  - There is no fallback to a file and no fallback to prod.
- Unit and integration tests inject a fake `SecretStore`, so CI never touches the store.

---

## Part B. Rollout

Each step says what starts it, what it changes, where its state lives and what happens if it fails. Steps run in order.

### Step 0. Confirm provider capabilities (blocker)

- **Starts:** plan approval.
- **Checks, for each of the three providers:** (a) two keys can be active at once; (b) a key can be disabled, which is reversible, before it is deleted; (c) the last-used time of each key is visible.
- **Moves:** nothing.
- **State:** the decision is recorded on the tracking issue.
- **On failure:** stop. Without (a), overlap cannot meet "no customer request fails". Escalate to Security and product before any later step. Without (c), Step 5 cannot be confirmed.

### Step 1. Create the store namespaces, KMS keys and access policy

- **Starts:** Step 0 passes.
- **Moves:** create `orders-api/dev/*` and `orders-api/prod/*`. Each is encrypted with its own per-environment KMS key. Policies:
  - `orders-api-prod` can read `orders-api/prod/*` only.
  - The Security on-call role can write `orders-api/prod/*`. Only it can write prod secrets.
  - Engineers can read `orders-api/dev/*` only. They cannot read prod values.
- **State:** the store. No values yet.
- **On failure:** nothing live has changed. Fix the policy, then verify with negative tests: `orders-api-prod` cannot read dev or list other paths, and an engineer role cannot read prod.

### Step 2. Issue new provider keys and load them into the prod store (version 1)

- **Starts:** Step 1 is verified.
- **Moves:** Security on-call creates a second key at each provider while the old keys stay active. They write each new value to `orders-api/prod/<name>`. The store returns version ids. Record the ids on the rollout ticket. Never record the values.
- **Dev:** separate sandbox keys go into `orders-api/dev/*`. Who creates them is open (see Open questions).
- **Later rotations** repeat this step. Security on-call writes a new value to the same path, and the store creates the next version. A later rotation follows the write freeze in Step 4.
- **Open:** the write route (see Open questions).
- **State:** old keys are live at the providers and used by the old pods. New keys are live at the providers and in the store as v1. No running code reads the store yet, so v1 is inert.
- **On failure:** if key creation fails, nothing has changed. Stop. If a store write fails, retry it. A partial load (two of three secrets) is harmless, because no running code reads the store yet.

### Step 3. Build and verify the new code in dev

- **Starts:** the PR merges to `main`. The PR contains Part A, the `config/app.yaml` cleanup, the CI guard (Step 9) and the migration marker (Step 8). The merge builds an image and deploys nothing.
- **Moves:** deploy the image to dev. It reads `orders-api/dev/*`. How the image reaches dev is open (see Open questions).
- **Verify:**
  - `/healthz` returns 503 before the keys load and 200 after.
  - Store unreachable at start: 3 retries, 2 seconds apart, then a non-zero exit.
  - Store fails mid-run: a warning is logged, the last good value keeps serving, and the next successful read swaps the version.
  - A revoked key: the failing request returns a clear error. If the optional 401 re-read is built, `provider_auth_failures_total` rises.
  - A log scan finds no key-shaped strings.
- **How each failure is produced in dev:**
  - Store unreachable: block the pod's route to the store before it starts.
  - Store fails mid-run: remove the dev read permission for the pod's identity for one refresh window, then restore it.
  - Revoked key: disable the dev sandbox key at its provider.
- **State:** dev only.
- **On failure:** fix and re-merge. Prod is untouched.

### Step 4. Promote the new image to prod with a rolling deploy

- **Starts:** Step 3 passes and the Step 2 v1 values exist in the store.
- **Moves:** a rolling deploy with `maxUnavailable: 0`, 4 replicas, one pod at a time. Start one new pod. It runs the startup gate (A1) and reads v1. When its `/healthz` returns 200, one old pod stops. Repeat until all 4 pods are new.
- **Old pods** keep the keys baked into their images. Those keys stay valid because of Step 2.
- **Write freeze:** from the start of this step until Step 5 is confirmed, no new prod secret version is written. A write in the middle of the rollout would leave pods that started before and after it on different versions. The freeze keeps all four pods on v1.
- **State:** a mixed fleet until the rollout finishes. Old pods use the old keys. New pods use the v1 keys. Each pod's secret state is in memory. Once all 4 pods are new, the old keys are still valid but unused until Step 6.
- **On failure:** if a new pod exits or never becomes ready, the rollout halts. The old pods keep serving on their still-valid old keys. Fix the cause and promote again. Who is alerted to a halted rollout is open (see Open questions).

### Step 5. Confirm every running instance is on the new version

- **Starts:** the rollout completes.
- **Checks:**
  - Each of the 4 prod pods reports the store's latest version id for all three secrets. Use the `secret_version` metric or the version-change log lines (A2). Wait at least one full refresh cycle (5 minutes) plus a margin.
  - Each old key shows zero use at its provider for a window that Security sets (suggested: 30 minutes). The window starts when the last old pod stops. Use the per-key last-used time confirmed in Step 0.
  - Zero use is expected, because no pod holds an old key after Step 4. Traffic that could still appear is: requests in flight when the last old pod stopped, a rollback to a pre-migration image (Step 8 closes this), or another workload from the inventory below.
  - Inventory every other workload that uses these keys, including jobs, workers, scripts and other services. Each one must be migrated before Step 6.
- **State:** the observations are recorded on the ticket.
- **On failure:** if any instance reports an old or missing version, investigate and do not revoke. If the last-used time is not zero after the window, do not disable the key. Find the source first. If old-key traffic comes from an unknown source, stop and find that source first.

### Step 6. Disable the old keys

- **Starts:** Step 5 is confirmed, Step 8 is in place and Security signs off.
- **Moves:** disable, not delete, each old key at its provider. Disabling is a revocation in effect, so Step 5 must be complete first.
- **State:** the old keys are disabled at the providers.
- **On failure:** if customer errors appear, re-enable the old key at once. This is the reversible path. Investigate, and go on to Step 7 only once the errors are explained.

### Step 7. Soak, then delete the old keys

- **Starts:** the soak period that Security sets has passed with no old-key use. Step 7 suggests at least 24 hours (open, see Open questions).
- **Moves:** delete the old keys at the providers.
- **State:** the keys are deleted at the providers.
- **On failure:** none expected. The keys are already disabled and no running code uses them. Deletion cannot be undone, so confirm the soak period first.

### Step 8. Close the rollback path and lock out old images

- **Starts:** Step 4 completes. This must be in place before Step 6, because after Step 6 pre-migration images would also fail.
- **Moves:** CI stamps every image built from the Step 3 PR onward with a migration marker, a tag or label. The deploy pipeline rejects any image without the marker. Rollback targets are post-migration images only.
- **Why a marker:** a CI-set marker is exact. A build-date cutoff would depend on when the merge landed. The marker needs the pipeline to support tags (assumption). Who configures the check is open (see Open questions).
- **Why at all:** pre-migration images carry the leaked keys in `config/app.yaml`. Once Step 6 disables those keys, a rollback to such an image gets 401 from all three providers.
- **Rollback for a bad secret version:** before Step 7, if the store can point back to an earlier version (open, see Open questions), move the pointer back to the previous version. After Step 7 the previous key is gone, so the fix is a newly issued key.
- **State:** the pipeline check and the markers on images.
- **On failure:** if the pipeline cannot check tags, Step 8 cannot be done, so Step 6 cannot start.

### Step 9. CI guard, history and the rotation runbook

- **Guard:** CI fails any change that adds an `api_key` entry to `config/app.yaml`. It also fails any diff that contains the provider key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) in tracked files. The guard scans the diff and the current tree, not history.
- **Timing:** the guard ships with the Step 3 PR, so it is active before any new image is promoted.
- **History:** git history is not rewritten. The old keys stay there, but they are inert after Step 7.
- **Logs:** search the central logs (30-day retention) for past key values. Anything found goes into a separate incident item.
- **Rotation runbook:** Steps 2, 5, 6 and 7 form the procedure for any future rotation. The cadence is open (see Open questions).

---

## What happens when things fail

| Failure | What happens | Where it is set |
|---|---|---|
| Store unreachable at start | Gate retries, then exits non-zero. The pod crash-loops, the rollout halts, and the old pods keep serving. | Startup gate (A1) |
| Store unreachable mid-run | The last good value keeps serving, a warning is logged, and the staleness alert fires once its threshold is set. | Refresh loop (A2) |
| Sudden revocation of the current key | Requests on that key fail until a re-read finds a newer version. That takes up to 5 minutes, or less with the optional 401 re-read. | Refresh loop (A2) |
| Empty cache | The client raises a clear error and the request fails. Any occurrence is a bug. | Client reads (A3) |
| Identity cannot be read in dev | Startup refuses to run. | Local development (A5) |

**Residual risks**

- A sudden revocation can cause failures for up to 5 minutes, the refresh interval. The 5-minute interval is fixed by the brief. A shorter interval would need a separate decision.
- A store outage during a deploy blocks new pods, which is intended. Old pods keep serving, so the impact is a stalled deploy, not an outage.
- Keys stay leaked in git history and in old images in the registry. Disabling them removes their function, but not their exposure.

---

## Open questions

1. **Scheduled rotation cadence after the migration.** Security has not decided whether keys rotate on a schedule, or how often. This plan does not pick a cadence. Steps 2, 5, 6 and 7 can serve as the rotation runbook once Security sets one.
2. **Provider overlap and disable support.** If a provider cannot keep two keys active, the "no failed requests" rule cannot be met by overlap, and Step 0 is a hard stop.
3. **Retry count.** This plan reads "retry 3 times" as one initial attempt plus 3 retries, 2 seconds apart, about 6 seconds of waiting in total. If Security means 3 total attempts, change the constant only.
4. **Soak period** between disabling and deleting old keys. Security sets it. Step 7 suggests at least 24 hours.
5. **Other consumers.** Whether any job, script or other service uses these same keys. Step 5 requires the inventory.
6. **Secret store product, write route and workload identity.** The brief names "our managed secret store" and the identity `orders-api-prod`, but not the product, how a pod proves its identity to the store, how the guard learns the identity name, or how Security on-call writes values. Steps 1 and 2, A1 and A5 depend on these.
7. **Moving back to an earlier version.** The brief says every write gets a new version id. It does not say the store keeps a current pointer that can be moved back to an older version. Step 8 depends on this.
8. **Where the `secret_version` metric is viewed.** The brief names no metrics backend or dashboard. Step 5 depends on it.
9. **Dev keys and dev deploys.** The brief names no owner for the dev sandbox keys, and does not say how an image reaches dev, by hand or automatically. Steps 2 and 3 depend on this.
10. **Stalled rollouts and staleness alerts.** The brief names no one to watch a halted rollout, and no staleness threshold or alert recipient. A2 and Step 4 depend on these.
11. **Image marker check.** The brief does not say who configures the pipeline's check for pre-migration images, or whether the pipeline can check tags (assumption). Step 8 depends on this.
12. **How prod pods get `APP_ENV=prod`.** The brief does not say how the deployment sets it. A5 assumes the prod deployment sets `APP_ENV=prod` on each pod, so the guard can tell prod pods from local runs.