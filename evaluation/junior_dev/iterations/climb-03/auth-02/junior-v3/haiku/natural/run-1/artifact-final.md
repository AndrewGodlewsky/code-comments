# Move orders-api third-party keys to the managed secret store

orders-api keeps three live provider keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to git and copied into every image. This plan moves the keys into the secret store, rotates all three at their providers, and changes the app to read them from the store at startup and re-read them every 5 minutes. Old keys are revoked only after every running pod is confirmed to use the new ones.

Main flow: steps 1 to 4 prepare the store and the new keys. Step 5 ships code that reads the store and removes the keys from config. Steps 6 and 7 confirm and then revoke the old keys. Steps 8 and 9 verify the CI guard and local development.

## Terms

- **Secret store**: the managed service that holds secret values. Every write creates a new version with its own id. The app reads the latest version.
- **KMS key**: the key the store uses to encrypt values at rest. There is one per environment (`prod`, `dev`).
- **Version id**: the id of one stored value. Version ids are safe to log and to record.
- **Workload identity**: how a pod proves who it is to the store. Prod pods run as `orders-api-prod`. No static credential is used.
- **Holder**: the in-memory place where the app keeps the current value of each key.
- **Refresh**: a background task in each pod that re-reads the three secrets every 5 minutes.
- **Readiness**: `GET /healthz`. The cluster uses it to decide whether a pod gets traffic and whether a rollout continues.
- **Deployer**: the person or pipeline that starts and watches a rollout. It is not the security on-call.

## Assumptions

- Each provider lets us hold two live keys at once, the old and the new. This is a hard gate. If a provider cannot, stop at step 1 and escalate to security.
- Each provider reports requests per key, so step 6 can check old-key use. This is a hard gate. If a provider cannot, stop at step 1 and escalate to security.
- Pods reach the store only through workload identity.
- "Retry 3 times" means one initial attempt plus three retries: up to four attempts, about 6 seconds of waiting. The owner must confirm this.

## Rollout

1. **Confirm provider capability and inventory the keys.**
   - Starts: the plan is approved.
   - Moves: nothing. Record each key's provider, its name, and every place it is used (code paths, instances, other services).
   - State lives: the migration tracking issue. It holds no key values.
   - If it fails: a provider that fails either assumption stops that provider's migration before step 3. Escalate to security. Revoke nothing.

2. **Create the store layout, KMS keys and IAM.**
   - Starts: step 1 is done. Changes go through infrastructure-as-code and security review.
   - Moves: nothing moves yet. Create `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, `orders-api/prod/geocoding_api_key`, and the same three under `orders-api/dev/`. Create one KMS key per environment.
   - Access rules:
     - `orders-api-prod` can read `orders-api/prod/*` and nothing else.
     - Only the security on-call role can write `orders-api/prod/*`.
     - No engineer role can read `orders-api/prod/*`.
     - Engineers can read and write `orders-api/dev/*` only.
   - Before any value is written, run the store's policy simulator to confirm that engineer and CI roles cannot read prod.
   - State lives: the encrypted store and the IaC policy files.
   - If it fails: fix the policy, re-run the simulator and retry. A wrong policy that gets past both the simulator and the step 4 read check shows up as new pods failing at startup in step 5. The rollout halts and old pods keep serving.

3. **Create new keys at each provider.**
   - Starts: step 2 is done and the simulator check passes.
   - Moves: the security on-call creates a new key in each provider's console or admin API. Old keys stay active.
   - State lives: the provider.
   - If it fails: nothing in production has changed. Retry or escalate. Do not revoke any old key.

4. **Validate and write the new values to the store.**
   - Starts: step 3 is done. The security on-call does this step.
   - Moves, for each key: the on-call copies the new value from the provider console into the store's write command, in one sitting. The value is never saved to a file, chat, ticket or environment variable. A provider test call first confirms the value authenticates. Then the value is written as a new version of `orders-api/prod/<name>`.
   - Read check: after the writes, the deployer runs a job that serves no traffic and reads the three prod secrets as `orders-api-prod`. Each must return the version id just written. This tests the real identity's access before any pod depends on it.
   - State lives: the store. The on-call records each returned version id in the tracking issue at the time of the write.
   - Why validate first: running pods pick up a new version at their next refresh, within 5 minutes. A bad key would reach customer traffic.
   - Later rewrites of a key follow the same steps, validation and read check included. Running pods pick them up at their next refresh, with no deploy.
   - If it fails:
     - Validation fails: do not write. Return to step 3.
     - Write fails: retry. Nothing is affected, because the old code does not read the store yet.
     - Read check fails: fix the policy (step 2) and run the check again. Nothing is affected yet.

5. **Release the store-reading code and remove the keys from config.**
   - Starts: merge to `main`. CI builds one image with no key values in it.
   - Startup, in each new pod, in this order:
     1. Load `config/app.yaml` for the non-secret settings. Ignore any `api_key` field.
     2. Read the three secrets into the holder. Make one attempt, then up to three retries, 2 seconds apart. If any secret still fails, log the secret names and the attempt count (never the values) and exit non-zero.
     3. Build the provider clients. Each client reads its key from the holder on every request. It does not copy the key in its constructor.
     4. Start listening.
   - Because the server listens only after step 2, `/healthz` returns 200 only once all three keys are loaded. Before that, nothing answers the probe, so the pod is not ready.
   - Config edit: remove the three `api_key` lines from `config/app.yaml`. The CI guard is added in step 8. Local development switches to dev keys in step 9.
   - Rollout: the deployer runs a rolling deploy with `maxUnavailable: 0`. A new pod must pass readiness before an old pod stops. The deployer watches until the rollout completes or halts.
   - Mixed fleet: both key sets stay valid at the providers until step 7. Old pods keep working with their old keys, and new pods work with their new keys.
   - State lives: the new pod's memory. Old pods keep their old keys until the rollout replaces them.
   - If it fails: if the store is down, or a secret is missing or bad, at startup, the pod exits. It never becomes ready, the rollout halts, and old pods keep serving.
   - Rollback: redeploy the pre-migration image. Its old keys still work until step 7.

6. **Confirm that every running pod uses the new keys (the gate).** Every check must pass before step 7.
   - Starts: step 5 is complete. Run the checks at least 5 minutes after the last write, so every pod has had a refresh.
   - Checks:
     - For each of the four prod pods, the most recent startup or refresh line for each key shows the version id recorded in the tracking issue. A pod on an unrecorded id fails.
     - The cluster's pod list shows no pod on the pre-migration image.
     - Every other consumer found in the step 1 inventory uses the new keys.
     - At the provider, requests using each old key have been zero for 15 minutes.
     - In the central log service, the prod logs contain zero matches for `secret refresh failed` over the same 15 minutes, from any pod.
     - The 15-minute window and the zero-warning rule are proposed, and security must confirm them (see open questions).
   - State lives: the logs, the provider's per-key usage, and the tracking issue, where the security on-call records sign-off.
   - If it fails: an old-image pod, a version mismatch, continued old-key traffic, or a refresh warning means the gate is not met. Hold, do not revoke, and investigate.

7. **Revoke the old keys at the providers.**
   - Starts: the security on-call signs off step 6.
   - Moves: nothing in the app. Each old key is revoked at its provider.
   - State lives: the provider. Revocation cannot be undone.
   - If it fails: any old-key traffic left behind becomes 401 errors for customers. This is why the step 6 gate is strict.
   - Effect: after this step, the pre-migration image is no longer a safe rollback.

8. **Verify the CI guard and clean up.**
   - Starts: step 7 is done.
   - Behavior: CI fails any change that puts an `api_key` field in `config/app.yaml`. It checks the file contents, not only the diff.
   - Checks:
     - On a throwaway branch, add an `api_key` line and confirm CI fails. Do not merge.
     - Confirm that `main` and the built image contain no key values.
     - Record in the tracking issue that the old keys remain in git history. History is not rewritten, and the old keys are revoked.
   - If it fails: a guard that does not fail blocks closing the migration.

9. **Local development on dev keys.**
   - Starts: the release in step 5.
   - Dev keys: an engineer creates sandbox or test keys at each provider, runs the same test call as in step 4, and writes them to `orders-api/dev/<name>`. This is done before developers switch. Dev keys never went live, so they need no step 6 gate and no step 7 revoke.
   - Moves: each developer's own engineer identity reads `orders-api/dev/*`. `make run` and the tests use the same loader.
   - Tests use an in-memory fake secret source with fake values. There are no key files and no environment variables. Developers delete any local copy of an older `config/app.yaml` that has live keys.
   - State lives: memory only.
   - If the dev store is unreachable: `make run` fails fast with a message that names the missing secret. It never falls back to the prod store or to the old live keys.

## Runtime rules (every pod, after startup)

- **Refresh**: every 5 minutes, the refresh task re-reads each secret. Each secret is swapped in independently when its read succeeds, so one failure does not block the others. The swap is atomic: a request sees either the old value or the new one, never a partial one.
- **On success**: log the secret name and the new version id, only if the version changed.
- **On failure** (store error, timeout, secret deleted or missing, empty or malformed value): keep the last good value. Log one warning line that starts with the fixed text `secret refresh failed`, followed by the secret name, the attempted version id and the error class. Never log the value. Readiness does not change, and a refresh failure never restarts a pod. Liveness is a separate check that does not depend on the store.
- **A valid-looking value that the provider rejects**: the refresh cannot test a key with the provider, so it swaps the value in. Requests then get 401s until a good value is written. Step 4's test call is the guard against this.
- **Provider returns 401 for a current key**: the request fails with the provider's error. The client logs the provider name and the status, never the key. Nothing retries with another key.
- **Memory only**: keys are never written to disk, to environment variables or to logs. The store SDK's on-disk cache, if it has one, is disabled.
- **Logs and dumps**: log secret names and version ids only. Redact the `Authorization` header in HTTP debug logs. Keep keys out of exception messages and `repr` output. Disable core dumps for prod pods, or confirm they are not collected.
- **Test**: run the test suite with a fake key such as `FAKE_PAYMENTS_KEY_123`, and fail the run if it appears in captured logs.
- **Restart**: memory is discarded, and the next start repeats the startup load. If the store is down when a pod restarts, that pod cannot become ready, but running pods keep their last good values.
- **A key found in logs**: an exposure incident. Rotate it again, starting at step 3.

## What fails and what happens (runtime)

| Situation | Customer impact | What happens |
|---|---|---|
| Store unreachable or secret missing during refresh | None | Last good value kept, warning logged |
| Bad new store version | Possible 401s | Step 4 validation should catch it. If not, the on-call writes the previous good value as a new version, and pods pick it up at their next refresh, up to 5 minutes later. That works only while the previous key is still valid at the provider, so after the step 7 revoke it works only for keys that were not revoked. A compromised key needs a new provider key (step 3). No alert for 401s is set (see open questions). |
| Rollback before the step 7 revoke | None | Redeploy the pre-migration image. Its old keys still work. |
| Rollback after the step 7 revoke | Depends on the image | The pre-migration image is no longer safe. Roll back to the post-migration image. |

## Open questions

- **Rotation cadence.** Security has not decided whether keys must be rotated on a schedule, or how often. This plan sets no schedule. Any future rotation must overlap old and new keys, as the runtime rules require.
- **Sandbox or test keys for dev.** Confirm that each provider offers them, or approve dev-only keys (step 9).
- **Staging.** Does a staging environment exist? If so, does it get its own store prefix and KMS key?
- **Observation window.** The 15-minute window and the zero-warning rule in step 6 are proposed. Security should confirm both.
- **Previous-value fallback.** Keep the previous value for one refresh cycle and retry once on a 401?
- **Rollback after the revoke.** How long, if at all, does the pre-migration image stay available?
- **Store audit.** Does the store log every read and write with the caller identity?
- **Secret scanning beyond the CI guard.** Add a general secret scanner to CI?
- **Store and KMS product names.** The brief does not name them.
- **Tooling and roles.** Which tool and machine run the test call, the write and the read check? How does the read-check job run as `orders-api-prod`? Who attaches workload identity to the pods, and how? Which team is the deployer?
- **Version id on read.** Does a store read return the version id with the value? Steps 4 and 6 depend on it.
- **Developer login.** How do engineers authenticate to the dev store for `make run`?
- **Alerts.** Does a halted rollout, or a spike in provider 401s, alert anyone, or does the deployer watch it?