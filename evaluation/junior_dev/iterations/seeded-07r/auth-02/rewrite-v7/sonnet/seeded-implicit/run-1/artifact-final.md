# Plan: move orders-api API keys into the secret store

## Summary

Today `orders-api` reads its three live API keys (payments, email, geocoding) once, at import, from `config/app.yaml`. That file is committed to git and copied into every container image, so the keys are leaked. We will rotate each key at its provider, store the new keys in the managed secret store, and make the app load them from the store at startup and re-read them every 5 minutes. The old keys are revoked only after every running instance has moved to the new ones, so no customer request fails.

## Terms

- **Secret store**: the managed service that holds secrets. It encrypts them at rest with a per-environment KMS key. Every write creates a new version id.
- **KMS key**: the encryption key the store uses for one environment (prod or dev).
- **Service identity**: the account a workload runs as. Prod pods run as `orders-api-prod`.
- **Version id**: the store's label for one written value of a secret. It is not secret and may be logged.
- **Readiness probe**: `GET /healthz`. Kubernetes sends traffic to a pod only after it returns 200.
- **Rolling deploy**: replaces the 4 prod pods one at a time (`maxUnavailable: 0`). A new pod must be ready before an old one stops. If a new pod never becomes ready, the rollout halts and the old pods keep serving.
- **Rotate / revoke**: rotate means create a new key at the provider. Revoke means switch the old key off. Both keys work in between.

## Rules that apply to every step

- Secrets are named `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The names are `payments_api_key`, `email_api_key` and `geocoding_api_key`.
- Key values live only in process memory. They never go on disk, into environment variables or into logs. Logging version ids is fine. Logs go to the central log service and are kept 30 days, so a logged value could not be taken back.
- No customer request may fail because of a missing or revoked key at any point.

## Steps

### Rollout (how we get there)

1. **Set access (starts first, by Security and platform).** In the store:
   - `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else.
   - Only the security on-call can write prod secrets.
   - Engineers cannot read prod values. Engineers can read and write `orders-api/dev/*`.

   State lives in the store's policies. If access is wrong, the pods in step 5 fail to start and the rollout halts.
2. **Rotate at the providers (security on-call).** Create a new key at each of the three providers. The old keys keep working. Write the new values to `orders-api/prod/*`. Never copy the old, leaked values into the store. Sandbox keys go to `orders-api/dev/*`. If a provider only allows one active key, stop and see Open questions. State lives in the store and at the providers.
3. **Change the code (one change).**
   - Add `app/secrets.py` (see Runtime below).
   - Change `PaymentsClient`, `EmailClient` and `GeocodingClient` to call `secrets.get(name)` on every request. Today they copy the key once at construction, which would keep a stale key after a refresh.
   - Delete the three `api_key` lines from `config/app.yaml`.
   - Add a CI check that fails any change that puts an `api_key` back into `config/app.yaml`.
   - In the Makefile, `make run` sets `APP_ENV=dev`, so local runs read sandbox keys from the dev path with the engineer's own credentials. Nobody reads prod secrets locally.
   - Make `/healthz` return 503 until all three keys are loaded, then 200 with `secret_versions` (name to version id, no values).

   Tests and CI run before merge. If CI fails, nothing ships.
4. **Merge and build.** CI builds one image per merge to `main`. The image now has no keys. Old pods still run the old image with the old keys, which stay valid.
5. **Deploy (rolling).** Each new pod loads the new keys at startup and passes readiness only after that. If a pod cannot load them, it never becomes ready, the rollout halts and the old pods keep serving. Fix the cause and redeploy.
6. **Verify.** When the rollout finishes, check that each of the 4 pods reports, in `/healthz` `secret_versions`, the same version ids as the current versions in the store. Do this before step 7. If any pod differs, do not revoke.
7. **Revoke the old keys (security on-call).** Only after step 6 confirms every instance uses the new keys, revoke the three old keys at the providers. A pod still on an old image could otherwise fail on its next request.
8. **Update `deploy.md`.** Change "rollback = redeploy an earlier image" to say that images from before this change contain the revoked keys and will fail. Roll back only to an image that reads from the store. Also record that local runs now use `orders-api/dev/*`.

### Runtime (how the app reads keys)

`app/secrets.py` holds the keys in a dict in process memory. It has `load()`, `refresh()` and `get(name)`.

- **Startup (starts at process start).** `load()` reads all three prod secrets using the pod's service identity. If the store cannot be reached, it retries 3 times, 2 seconds apart, then the process exits with a non-zero code. `/healthz` returns 503 until `load()` succeeds. On success it logs the version ids.
- **Refresh (starts every 5 minutes, on a background thread).** `refresh()` re-reads the three secrets and replaces the dict values, so a new version is picked up without a restart. If a re-read fails, the last good value stays in use and a warning is logged, with no secret value in it.
- **Use (starts on each request).** A client calls `secrets.get(name)` and gets the value from memory. It never calls the store itself.

## What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Step 1 | Wrong access | New pods cannot read secrets, never become ready, rollout halts, old pods serve |
| Step 2 | Provider allows only one key | Stop; open question |
| Step 3 | CI check or tests fail | Change is not merged |
| Step 5 | Store unreachable at pod start | 3 retries, 2 seconds apart, then exit non-zero; rollout halts, old pods serve |
| Step 6 | A pod shows an unexpected version id | Do not revoke; investigate |
| Runtime | Refresh fails | Keep last good value, log a warning |
| Runtime | Someone puts `api_key` back in `config/app.yaml` | CI fails the change |

## Open questions

- Security has not decided whether keys must be rotated on a regular schedule, or how often. This plan does not pick a cadence.
- Do all three providers allow two active keys at once? Steps 2 and 7 assume they do. If not, the swap needs a different plan, because a revoked old key would break running pods.
