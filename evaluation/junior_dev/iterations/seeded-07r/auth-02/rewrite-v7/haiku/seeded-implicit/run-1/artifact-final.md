# Plan: move API keys to the secret store

Today `orders-api` keeps three live third-party keys (payments, email, geocoding) in `config/app.yaml`. The app reads that file once at startup and copies each key into its provider client. The file is committed to git and copied into every container image, so the keys are treated as leaked. This plan moves the keys into the managed secret store. The app loads them at startup, re-reads them every 5 minutes, and keeps them only in memory. Every key is rotated at its provider. Old keys are revoked last, and only after every running pod reports the new version. Git history is not rewritten.

## Terms

- **Secret store**: the managed service that holds secret values. It encrypts them at rest with a per-environment KMS key. KMS is the cloud key-management service that holds the encryption key. Each write gets a new version id.
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`.
- **Service identity**: the login a running app uses to read the store. In prod it is `orders-api-prod`.
- **Version id**: the id the store gives each write. The app logs it and shows it in `/healthz`. It is not the secret value.
- **Replica (pod)**: one running copy of the app. Prod runs 4.
- **Readiness probe**: the check the cluster runs on `GET /healthz`. The cluster sends traffic to a pod only after it returns 200.
- **Rolling deploy with maxUnavailable 0**: the cluster starts one new pod, waits until it is ready, then stops one old pod.
- **APP_ENV**: the setting that tells the app which environment's secrets to read.
- **Rotate**: create a new key at the provider.
- **Revoke**: the provider stops accepting the old key. Any instance still using it then fails.

## How the app runs

### Startup

1. The app reads `config/app.yaml`. After this change the file holds no keys. It keeps the port (8080), the log level (info), each provider's base URL, the payments timeout (10 seconds), the geocoding timeout (3 seconds) and the email from address (`orders@shop.example`).
2. The app loads the three keys from the store under its service identity. It reads `orders-api/<env>/payments_api_key`, `email_api_key` and `geocoding_api_key`. Values go into process memory only.
   - If the store cannot be reached, the app retries 3 times, 2 seconds apart. If every retry fails, it exits with a non-zero code. The new pod never becomes ready, so the rollout halts and old pods keep serving.
3. `GET /healthz` returns 200 only after all three keys are loaded. Until then it does not return 200. Once ready, it returns `{"status": "ok"}` plus `secret_versions`, which holds the version id of each key. Today `/healthz` returns ok as soon as the server is listening.
4. Each provider client calls `secrets.get(name)` on every request. It does not copy the key once at construction. This way a refresh reaches the clients without a restart.

### Refresh (while running)

5. Every 5 minutes the app re-reads the three keys. If a version has changed, the new value replaces the old one in memory and the new version id is logged.
   - If a re-read fails, the app keeps the last good value, logs a warning and tries again at the next 5-minute tick. It keeps serving customers.

### Rules everywhere

- Key values exist only in process memory. They never go to disk, into environment variables or into logs. Logging version ids is fine.
- Logs go to the central log service and are kept for 30 days.

## How we build and roll out

1. **Set access.** `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only the security on-call can write prod secrets. Engineers cannot read prod values. Engineers get read access to `orders-api/dev/*` for local runs (step 5).
   - If access is wrong, steps 2 and 6 fail with access errors. Fix the policy first. Nothing is deployed yet.
2. **Load the current values into the store.** The security on-call writes the current prod values to `orders-api/prod/payments_api_key`, `email_api_key` and `geocoding_api_key`. These are the leaked keys. They are copied in so the app can read from the store before any key changes. Sandbox keys go to `orders-api/dev/*`. Each write creates a version id. Record them.
   - If a write fails, nothing else has changed. Retry the write.
3. **Write the code.** Add `app/secrets.py` with `load()` (startup, with the retry rule above), `refresh()` (every 5 minutes) and `get(name)` (returns the value in memory). Switch `PaymentsClient`, `EmailClient` and `GeocodingClient` to `secrets.get()`. Add `secret_versions` to `/healthz`.
4. **Remove the keys from config.** Delete the three `api_key` lines from `config/app.yaml`. Add a CI check that fails any change that puts `api_key` back into that file. Steps 3 and 4 ship in the same merge, so the image that drops the keys is also the one that reads the store.
   - If the CI check fails, the change does not merge.
5. **Point local runs at dev.** `make run` sets `APP_ENV=dev`, so it reads `orders-api/dev/*` sandbox keys. Local runs no longer use live keys, and no one needs prod access to run locally.
   - A developer without dev access fails at startup. They never get a prod key.
6. **Deploy and verify.** CI builds one image per merge to `main`. The image includes `config/app.yaml`. Production runs 4 replicas under `orders-api-prod`. Rollout is one pod at a time with `maxUnavailable: 0`. A new pod must pass its readiness probe before an old pod stops.
   - Verify that each new pod's `/healthz` shows the version ids from step 2 and that the logs show no load errors.
   - If a new pod never becomes ready, the rollout halts and the old pods keep serving. Fix the cause and redeploy.
7. **Rotate and revoke, one key at a time.**
   1. Rotate the key at its provider and get the new key.
   2. The security on-call writes the new key to `orders-api/prod/<name>`. The store gives it a new version id.
   3. Wait until all 4 replicas show the new version id in `/healthz`. This can take up to one 5-minute refresh.
   4. Only then revoke the old key at the provider.
   - If any replica does not show the new version, do not revoke. The old key stays valid, so customers are not affected.
8. **Update the rollback notes in `deploy.md`.** Rollback means redeploying an earlier image. An image built before this migration has the old keys baked in. Once step 7 revokes them, that image's provider calls fail. Roll back only to images built after step 4.

## What happens when things fail

| Situation | What happens | Why customers are safe |
|---|---|---|
| Store unreachable at startup | Retry 3 times, then exit non-zero | Rollout halts; old pods keep serving |
| Store unreachable during refresh | Keep last good value, log warning | Keys stay valid in memory |
| Key revoked before every replica switched | Replicas on the old key fail provider calls | Prevented: step 7 waits for every replica |
| Rollback to a pre-migration image after revoke | That image's provider calls fail | Prevented: step 8 forbids it |

## Open questions

- **Rotation schedule.** Security has not decided whether keys must rotate on a regular schedule after this migration, or how often. This plan sets no cadence.
- **Missing key.** The rule for an unreachable store is retry then exit. It is not decided whether a key that is missing from the store uses the same rule.
- **Checking a new key.** Step 7 checks only that replicas load the new version. It does not check that the new key works at the provider before the old key is revoked.
- **Who rotates.** It is not decided who performs the rotation at each provider.