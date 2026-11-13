# orders-api: move the three third-party API keys into the managed secret store

## 0. Scope, assumptions and open questions

**Scope.** This plan covers (A) how the app reads the payments, email and geocoding keys at runtime and (B) the ordered rollout that moves them out of `config/app.yaml` without failing customer requests.

**Assumptions** (each one is checked in Step 0 or listed under Open questions):

- Secret names are `payments_api_key`, `email_api_key` and `geocoding_api_key`. The brief fixes only the pattern and the payments example.
- Environments are `dev` and `prod`. Any other environment, such as staging, follows the `dev` pattern.
- The three providers can keep two keys active at the same time, and can disable a key before deleting it. Step 0 verifies this.
- Merging to `main` builds an image but does not deploy it. Deploys are a separate promotion.
- The deploy pipeline can reject images by build date or tag.

**Open questions (not decided here)**

1. **Scheduled rotation cadence after the migration.** Security has not decided whether keys rotate on a schedule or how often. This plan does not pick a cadence. Steps 2, 5, 6 and 7 are written so they can serve as the rotation runbook once Security sets one.
2. **Provider overlap and disable support.** If a provider cannot keep two keys active, the "no failed requests" rule cannot be met by overlap. Step 0 is then a hard stop.
3. **Retry count.** This plan reads "retry 3 times" as one initial attempt plus 3 retries, 2 seconds apart, about 6 seconds in total. If Security means 3 total attempts, change the constant only.
4. **Soak period** between disabling and deleting old keys. Security sets it. Step 7 suggests at least 24 hours.
5. **Other consumers.** Whether any job, script or other service uses these same keys. Step 5 requires an inventory.

---

## Part A. How the app reads keys at runtime

**A1. Startup gate (runs in `main()`, before the HTTP server listens)**

- **Starts:** process start.
- **Reads:** the secret store, as the pod's identity `orders-api-prod` in prod, or as the developer's dev identity locally. It fetches the latest version of all three secrets.
- **Moves:** each value goes into an in-memory `SecretCache`. Each entry is an immutable snapshot `{value, version_id, fetched_at}`.
- **Retry:** up to 3 retries, 2 seconds apart. A partial result, meaning fewer than three secrets, counts as a failure.
- **Success:** the app marks itself ready and starts the HTTP server. `/healthz` returns 200 only after this point and 503 before it. This replaces today's behaviour, where `/healthz` returns `ok` as soon as the server listens. Liveness stays separate, so a process that is alive but not ready is not killed.
- **State:** process memory only.
- **On failure:** log the secret names and error classes, never values. Exit non-zero. The pod crash-loops, the rolling deploy halts because `maxUnavailable: 0`, and the old pods keep serving.

**A2. Refresh loop**

- **Starts:** a timer, every 5 minutes after readiness, with up to 30 seconds of jitter so the four pods do not read in lockstep.
- **Moves:** for each secret, fetch the latest version. If the version id changed, build a new snapshot and swap the reference atomically. Log `secret=<name> version=<old>-><new>`. Never log the value.
- **On failure, per secret:** keep the last good snapshot and log a warning with the secret name, the version id still held, and the error. Increment a metric. There is no maximum age, so the app keeps the last good value indefinitely. Alert on staleness (time since the last successful read), not on the warning alone.
- **Optional, recommended:** on a provider 401, trigger one extra re-read, rate-limited to once per 60 seconds. This shortens the window if a key is revoked suddenly.
- **State:** memory. The version id is also exposed as a metric (`secret_version{name,version}`) so Step 5 can be checked without reading logs.

**A3. Client reads**

- `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in `__init__`. Each call reads the current snapshot, for example `secrets.get('payments_api_key')`.
- `config/app.yaml` keeps only non-secret settings: `base_url`, `timeout_seconds`, `from_address`, `port`, `log_level`.
- `app/config_loader.py` no longer fetches secrets at import time. Import-time fetching would make tests and local runs hit the store, and it would bypass the startup gate. Settings load at import as before. Secrets load only in `main()`.
- **On failure:** if the cache is empty, which the gate should make impossible, the client raises a clear error and the request fails. Treat any occurrence as a bug.

**A4. Memory and logging rules**

- Values are never logged, printed or put in exception messages. Log only version ids.
- Check the HTTP client's debug logging and exception formatting, which can include the `Authorization: Bearer` header.
- No secret env vars, no mounted secret files and no Kubernetes Secret objects. The app calls the store directly with its own identity, so nothing lands on disk or in the environment.
- Turn off core dumps in prod containers, or confirm they are not collected.

**A5. Local development**

- `make run` sets `APP_ENV=dev` and reads `orders-api/dev/*` with the developer role. That role has read access to dev only. The dev values are provider sandbox keys, not live keys.
- **Guard:** startup refuses to run if the identity is `orders-api-prod`, or if the secret path does not match `APP_ENV`. There is no fallback to a file and no fallback to prod.
- Unit and integration tests inject a fake `SecretStore`, so CI never touches the store.

---

## Part B. Rollout

**Step 0. Confirm provider capabilities (blocker)**

- **Starts:** plan approval.
- **Checks, for each of the three providers:** (a) two keys can be active at once; (b) a key can be disabled, which is reversible, before it is deleted; (c) per-key last-used time is visible.
- **Moves:** nothing.
- **State:** decision recorded on the tracking issue.
- **On failure:** stop. Without (a), rotation cannot meet "no customer request fails". Escalate to Security and product before any later step. Without (c), Step 5 cannot be confirmed.

**Step 1. Create the store namespaces, KMS keys and access policy**

- **Starts:** Step 0 passes.
- **Moves:** create `orders-api/dev/*` and `orders-api/prod/*`, each encrypted with its own per-environment KMS key. Policies:
  - `orders-api-prod`: read on `orders-api/prod/*` only.
  - Security on-call: write on `orders-api/prod/*`.
  - Engineers: read on `orders-api/dev/*` only, with no prod read.
- **State:** the store. No values yet.
- **On failure:** nothing live has changed. Fix the policy. Verify with negative tests: `orders-api-prod` cannot read dev or list other paths, and an engineer role cannot read prod.

**Step 2. Issue new provider keys and load them into the prod store (version 1)**

- **Starts:** Step 1 verified.
- **Moves:** Security on-call creates a second key at each provider while the old keys stay active. They write the new values to `orders-api/prod/<name>`. The store returns version ids. Record the ids on the rollout ticket. Never record the values.
- **Dev:** separate sandbox keys go into `orders-api/dev/*`.
- **State:** old keys are live at the providers and used by the old pods. New keys are live at the providers and in the store as v1. No code reads the store yet, so v1 is inert.
- **On failure:** if key creation fails, nothing has changed; stop. If a store write fails, retry it. A partial load (two of three secrets) is harmless because no running code reads the store yet.

**Step 3. Build and verify the new code in dev**

- **Starts:** the PR merges to `main`. It contains Part A, the `config/app.yaml` cleanup and the CI guard (Step 9). The merge builds an image and deploys nothing.
- **Moves:** deploy the image to dev. It reads `orders-api/dev/*`.
- **Verify:**
  - `/healthz` returns 503 before keys load and 200 after.
  - Store unreachable at start: 3 retries, 2 seconds apart, then a non-zero exit.
  - Store fails mid-run: a warning is logged, the last good value keeps serving, and the next successful read swaps the version.
  - A revoked key: the 401 path raises the metric.
  - A log scan finds no key-shaped strings.
- **On failure:** fix and re-merge. Prod is untouched.

**Step 4. Promote the new image to prod with a rolling deploy**

- **Starts:** Step 3 passes and Step 2 v1 exists in the store.
- **Moves:** rolling deploy, `maxUnavailable: 0`, 4 replicas. Each new pod reads v1 at startup and must pass readiness before an old pod stops. Old pods keep their baked-in keys, which are still valid because of Step 2.
- **State:** a mixed fleet until the rollout finishes. Each pod's secret state is in memory.
- **On failure:** if a new pod exits or never becomes ready, the rollout halts and the old pods keep serving on still-valid old keys. Fix the cause and re-promote. From this point on, the pipeline also blocks pre-migration images (Step 8).

**Step 5. Confirm every running instance is on the new version**

- **Starts:** the rollout completes.
- **Checks:**
  - Each of the 4 prod pods reports the store's latest version id for all three secrets. Wait at least one full refresh cycle (5 minutes) plus margin.
  - Each old key shows zero use at its provider for a window that Security sets (suggested: 30 minutes).
  - Inventory every other workload that uses these keys, including jobs, workers, scripts and other services. Each must be migrated before Step 6.
- **State:** observations recorded on the ticket.
- **On failure:** if any instance reports an old or missing version, investigate and do not revoke. If old-key traffic comes from an unknown source, stop and find it first.

**Step 6. Disable the old keys**

- **Starts:** Step 5 confirmed and Security signs off.
- **Moves:** disable, not delete, each old key at its provider. Disabling is a revocation in effect, so Step 5 must be complete first.
- **On failure:** if customer errors appear, re-enable the old key at once, which is the reversible path, and investigate. Only proceed to Step 7 once the errors are explained.

**Step 7. Soak, then delete the old keys**

- **Starts:** the soak period set by Security has passed with no old-key use.
- **Moves:** delete the old keys at the providers.
- **On failure:** none expected, because the keys are already disabled and no running code uses them. Deletion is irreversible, so confirm the soak period first.

**Step 8. Close the rollback path and lock out old images**

- **Starts:** Step 4 completes. After Step 6, pre-migration images would also fail.
- **Moves:** the deploy pipeline rejects images built before the migration. Rollback targets are post-migration images only.
- **Why:** pre-migration images carry the leaked keys in `config/app.yaml`. Once Step 6 disables those keys, a rollback to such an image gets 401 from all three providers.
- **Rollback for a bad secret version:** before Step 7, move the store's current pointer back to the previous version, which the store keeps. After Step 7, the previous key is gone, so the fix is a newly issued key.

**Step 9. CI guard, history and the rotation runbook**

- **Guard:** CI fails any change that adds an `api_key` entry to `config/app.yaml`. It also fails any diff that contains the provider key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) in tracked files. The guard scans the diff and the current tree, not history.
- **Guard ships with the Step 3 PR,** so it is active before any new image is promoted.
- **History:** git history is not rewritten. The old keys remain there but are inert after Step 7.
- **Logs:** search the central logs (30-day retention) for past key values. Anything found goes into a separate incident item.
- **Rotation runbook:** Steps 2, 5, 6 and 7 form the procedure for any future rotation. The cadence is an open question.

---

## Residual risks

- **Sudden revocation of the current key** causes failures for up to 5 minutes, the refresh interval, unless the 401-triggered re-read (A2) finds a newer version. The 5-minute interval is fixed by the brief. A shorter interval would need a separate decision.
- **Start-time dependency on the store.** A store outage during a deploy blocks new pods, which is intended. Old pods keep serving, so the impact is a stalled deploy, not an outage.
- **Keys stay leaked in git history and in old images** in the registry. Disabling them removes their function, but not their exposure.