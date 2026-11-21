# Plan: move API keys to the secret store

Today `orders-api` reads three live provider keys (payments, email, geocoding) from `config/app.yaml`. That file is committed to git and copied into every image. The app loads it once at start-up, and each provider client copies its key once when it is built. This plan moves the keys to the managed secret store under `orders-api/<env>/<name>`. The app loads them at start-up, re-reads them every 5 minutes, and keeps them only in memory. Each key is rotated at its provider, and an old key is revoked only after every instance is using the new one.

## Terms

- **Secret store**: the managed service that encrypts secrets per environment and gives each write a new version id.
- **Version id**: the id of one stored value. Logs may show it. Values must never be logged.
- **Last good value**: the most recent value the store returned without error.
- **Ready**: `GET /healthz` returns 200.

## Steps

Each step says what starts it, what it does, where its data lives, and what happens if it fails.

1. **Set access rules.** Starts the migration. The prod identity `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only security on-call can write prod secrets. Engineers cannot read prod values. Data: the store's access policy. On failure, fix the rules before step 2. Customers are not affected yet.

2. **Copy the current keys into the store.** Starts after step 1. Creates `orders-api/prod/{payments,email,geocoding}_api_key` with the current values, and `orders-api/dev/*` with sandbox keys. Data: the store. On failure, retry the write. The app still reads the yaml, so customers are not affected.

3. **Add the loader (`app/secrets.py`).** It has `load()`, `refresh()` and `get(name)`.
   - `load()` runs at start-up. It reads all three keys. If the store fails, it retries 3 times, 2 seconds apart. If every try fails, the process exits with a non-zero code.
   - `refresh()` runs every 5 minutes. If it fails, the instance keeps the last good value and logs a warning.
   - Data: memory only. Never disk, environment variables or logs.

4. **Switch the provider clients to the loader.** `PaymentsClient`, `EmailClient` and `GeocodingClient` call `secrets.get(name)` on each use, instead of copying the key at construction. Otherwise a refreshed key would never be seen. Data: memory. On failure, the pod never becomes ready (step 5), so no request runs without a key.

5. **Report readiness.** `/healthz` returns 200 only after all three keys have loaded. It also returns `secret_versions` (version ids only). Starts with each probe. On failure, the pod stays not-ready, so the rollout halts and old pods keep serving.

6. **Remove the keys from the repo.** Delete the `api_key` entries from `config/app.yaml`. Add a CI check that fails any change that puts an `api_key` back. Starts with the change to `main`. On failure, CI blocks the merge.

7. **Point local runs at dev.** `make run` sets `APP_ENV=dev`, so it reads `orders-api/dev/*`. Starts when a developer runs it. Data: the dev store. Developers need dev access only, never prod.

8. **Deploy and verify.** Starts with a merge to `main`. CI builds the image. The rolling deploy replaces one pod at a time, with `maxUnavailable: 0`. Check that each new pod reports the expected `secret_versions`. On failure, the rollout halts and old pods keep serving.

9. **Rotate, then revoke.** Starts once step 8 is verified on all 4 replicas.
   1. Create a new key at each provider.
   2. Security on-call writes the new value to `orders-api/prod/*` as a new version.
   3. Wait for the 5-minute refresh.
   4. Confirm every instance reports the new version id.
   5. Only then revoke the old key at the provider.

   On failure, if any instance does not show the new version, do not revoke. An instance whose re-read fails keeps its last good (old) key, which stays valid until revoke.

10. **Update the rollback notes in `deploy.md`.** Rollback is still a redeploy of an earlier image. A pre-migration image has the old keys baked in, so after step 9 it will fail. Roll back only to post-migration images.

## What happens when things fail

| Failure | What happens | Customer impact |
|---|---|---|
| Store unreachable at start-up | 3 retries, 2 s apart, then exit non-zero; pod not ready | None; old pods serve |
| Store unreachable on refresh | Keep last good value; log a warning | None |
| New pod never ready | Rollout halts | None |
| Old key revoked before all instances switch | Requests with that key fail | Prevented by the step 9 gate |
| Rollback to pre-migration image after revoke | Old key rejected | Yes; do not roll back that far |

## Open questions

- Must keys also be rotated on a regular schedule after this migration, and how often? Security has not decided. No cadence is set in this plan.