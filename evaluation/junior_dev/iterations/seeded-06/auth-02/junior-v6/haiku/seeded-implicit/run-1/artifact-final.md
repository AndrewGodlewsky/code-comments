# Plan: move API keys to the secret store

## Summary

Today `orders-api` keeps three live third-party keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to git and copied into every container image. The app reads it once, when the process starts, so changing a key means a new image and a redeploy.

This plan moves the keys into our managed secret store. The app loads all three keys at startup and does not report ready until it has them. It then re-reads them every 5 minutes, so a new key takes effect without a redeploy.

The three keys are treated as leaked, because git history keeps them. History is not rewritten. Each key is rotated at its provider, and the old key is revoked last.

The order protects customers. The current keys are copied into the store first, so the new code has valid keys from the start. The old keys stay valid until no running instance uses them, so no customer request fails.

## Terms

- **Secret store**: our managed service that holds secrets. It encrypts each secret at rest with a per-environment KMS key (a cloud service that holds encryption keys). Every write creates a new version. The product is not yet named (see open questions).
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. `<env>` is `prod` or `dev`.
- **Version id**: the id the store gives each written value. Logs may show version ids. Logs must never show secret values.
- **Service identity**: the identity a workload runs as. Prod pods run as `orders-api-prod`.
- **Security on-call**: the person on duty in security. Only this role writes prod secrets.
- **Provider**: the outside company that issues each key (payments, email, geocoding).
- **Last good value**: the most recent key the app read from the store successfully.
- **Readiness**: a new pod must return 200 from `GET /healthz` before the cluster stops an old pod.
- **maxUnavailable: 0**: a cluster setting that keeps every old pod running until its new pod is ready.
- **Revoke**: disable an old key at the provider, so it stops working.
- **Rollback**: redeploying an earlier image.
- **Local run**: `make run` on a developer machine.

## How the app reads keys at runtime

Keys live only in process memory. They never go on disk, into environment variables or into logs.

1. **Start.** Starts when a pod starts. `secrets.load()` reads the three secrets for the pod's environment into memory. `APP_ENV=prod` reads `orders-api/prod/*`. `APP_ENV=dev` reads `orders-api/dev/*`. If a read fails, the app retries 3 times, 2 seconds apart. If the store still cannot be reached, the process exits with a non-zero code. The pod never becomes ready, so the rollout stops. Old pods keep serving.
2. **Ready.** Starts when the cluster probes `GET /healthz`. The endpoint returns 200 only after all three keys have loaded. Today it returns 200 as soon as the server listens, so this changes. The response includes `secret_versions`, a map from each secret name to the version id in use. It never includes values.
3. **Serve.** Starts on every provider call. The payments, email and geocoding clients call `secrets.get(name)` each time. They do not copy the key when they are built, so a refreshed key is used at once. Serving reads memory only, so a store outage does not affect it. Base URLs, timeouts (payments 10 s, geocoding 3 s) and the email from-address stay in `config/app.yaml`. Only the keys move.
4. **Refresh.** Starts every 5 minutes on a timer. `secrets.refresh()` re-reads the three secrets. A changed value replaces the value in memory, and the new version id is logged. If the read fails, the app keeps the last good value, logs a warning and tries again at the next tick. Running pods keep serving.

## Rollout

Each step says what starts it, what it changes, where its state lives and what happens if it fails. The rollout uses one container image per merge to `main`. Production runs 4 pods under `orders-api-prod`.

1. **Access policies.** Starts before any secret is written. Changes:
   - `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else.
   - Security on-call can write prod secrets. Engineers cannot read prod values.
   - Engineers get read access to `orders-api/dev/*` only, so local work needs no prod secret.

   State: the policies live in the store. If it fails: if the prod read is missing, new pods fail at start and the rollout stops. Old pods keep serving.
2. **Create secrets.** Starts after step 1. Security on-call writes `orders-api/prod/{payments,email,geocoding}_api_key` with the current values. These are the leaked keys, and they stay valid until step 9. Sandbox keys go to `orders-api/dev/*`. State: the store, encrypted with the prod KMS key. If it fails: a missing secret makes a new pod fail at start, as in runtime step 1. Running pods are not affected, because they still read `config/app.yaml`.
3. **Add `app/secrets.py`.** Starts with the code change. It provides `load()`, `refresh()` and `get(name)`. Steps 3 to 7 ship as one release, and step 8 deploys it. Nothing changes in production before step 8.
4. **Switch clients.** Same release. PaymentsClient, EmailClient and GeocodingClient call `secrets.get()` on each call. They no longer copy the key when they are built.
5. **Change `/healthz`.** Same release. It returns 200 only after the keys load, so the rollout waits for keys. It adds `secret_versions`.
6. **Remove keys from the file.** Same release. Delete the `api_key` entries from `config/app.yaml`. Add a CI check that fails any change where `config/app.yaml` contains `api_key` on any line. No image built from this change carries keys. Images built earlier still contain the leaked keys until they are replaced.
7. **Local runs.** Same release. `make run` sets `APP_ENV=dev`, so it reads `orders-api/dev/*`, not prod. If dev secrets are missing, `make run` exits non-zero. Prod is not affected.
8. **Deploy and verify.** Starts when a merge to `main` builds the image and the rollout begins. The rollout updates prod one pod at a time, with `maxUnavailable: 0`. The deploy is verified when all of these hold:
   - every new pod passes readiness;
   - `/healthz` shows the expected version id for all three secrets on every pod;
   - no key value appears in the logs;
   - customer error rates for payments, email and geocoding stay at normal levels.

   If it fails: if a new pod never becomes ready, the rollout halts and old pods keep serving. Fix the pod or roll back.
9. **Rotate and revoke.** Do this for each of the three keys, in this order. Starts when the key is ready to rotate.
   - a. Issue a new key at the provider. Check that it works there before writing it to the store.
   - b. Security on-call writes the new value to `orders-api/prod/<name>`. The store creates a new version.
   - c. Within 5 minutes, the refresh on every pod picks up the new version. Each pod logs the new version id.
   - d. Confirm that all 4 pods show the new version id in `/healthz`.
   - e. Only then revoke the old key at the provider.

   The old key stays valid through steps a to d, so no request fails. If any pod does not show the new version, do not revoke.
10. **Update rollback notes in `deploy.md`.** Copy the rollback rules from the failure table below. Rollback is still redeploying an earlier image.

## What happens when things fail

| When | What happens | What to do |
|---|---|---|
| Store unreachable at start | Retries 3 times, 2 seconds apart, then exits non-zero. Pod never ready. Rollout stops. Old pods keep serving. | Fix store access. Old pods keep serving. |
| A prod secret is missing at start, or prod read access is missing | Same as a failed start. | Fix the secret, or the policy from step 1. |
| Store unreachable at refresh | Keeps the last good value and logs a warning. Retries at the next 5-minute tick. | Fix the store. Customers are not affected. |
| Refresh returns a changed value | Replaces the in-memory value and logs the new version id. This is the rotation path. A wrong value replaces the good one. | Check the key first (step 9a). |
| New pod never ready | Rollout halts. Old pods keep serving. | Fix the pod, or roll back. |
| Rollback before step 9 revokes | The earlier image reads keys from its own `config/app.yaml`, and works while the old keys are valid. | Allowed. |
| Rollback after step 9 revokes | The earlier image uses revoked keys, and customer requests fail. | Do not roll back to a pre-migration image. Roll back only to a release that reads the store. |
| A pod does not show the new version in `/healthz` (step 9d) | The old key must stay valid. | Do not revoke. Find the pod that is not refreshing. |
| Dev secrets missing | `make run` exits non-zero. | Fix dev secrets. Prod is not affected. |

Logs go to the central log service and are kept for 30 days. Logs show version ids only.

## Open questions

- Which product is the secret store, and how does the app authenticate to it? The brief names only the service identity `orders-api-prod`.
- Who issues the new key at each provider, and how is each new key confirmed to work?
- Where is `APP_ENV` set in prod? It is not in the files reviewed.
- Does "retry 3 times" mean 3 retries after the first failure, or 3 attempts in all? This plan assumes 3 retries after the first failure.
- Should keys be rotated on a regular schedule after this migration, and how often? Security has not decided. No cadence is chosen here.