# Plan: move orders-api API keys into the secret store

Today `orders-api` has three live third-party keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to git and copied into every container image. `app/config_loader.py` reads it once at import, and each provider client copies its key at construction, so a changed key needs a new image and a redeploy. This plan moves the keys into our managed secret store. At startup the app fetches the keys from the store, and it will not report ready until it has all three. Every 5 minutes it re-reads them, and every outgoing provider call uses the current value. The keys have been in git history for two years, so we treat them as leaked and rotate every one. We rotate only after the new code is live on every instance. We test each new key at the provider before the store holds it. We revoke an old key only after every instance is confirmed to use the new one. That order means no customer request fails because of a missing or revoked key.

## Terms

- **Secret store**: our managed secret service. It encrypts each secret at rest with a per-environment KMS key and gives every write a new version id. The product name is not recorded here (see open questions).
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The three names are `payments_api_key`, `email_api_key` and `geocoding_api_key`.
- **Version id**: the id the store gives each write of a secret. It is safe to log. It is not the value.
- **Service identity**: the account a pod runs as. In prod it is `orders-api-prod`. The app calls the store as this identity.
- **Security on-call**: the only people who can write prod secrets.
- **APP_ENV**: an environment variable naming the environment (`prod` or `dev`). It selects which secret names the app reads. It is not a secret.
- **Readiness probe**: `GET /healthz`. A new pod must return 200 before the rolling deploy stops an old pod. Deploys are rolling, one pod at a time, with `maxUnavailable: 0`. Production runs 4 replicas.
- **Old key / new key**: the leaked key currently in `app.yaml`, and its replacement created at the provider.

## Rules that hold throughout

- Key values live only in process memory. They never go on disk, into environment variables or into logs. Logging version ids is fine. Logs are kept for 30 days, so a leaked value in a log would persist.
- `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only security on-call can write prod secrets. Engineers cannot read prod values.
- Git history is not rewritten. Rotation is what removes the risk.
- No customer request may fail because of a missing or revoked key at any point in the migration.
- Local development must keep working without anyone reading prod secrets.
- CI must fail any change that puts an `api_key` back into `config/app.yaml`.

## How the app reads keys at runtime

1. **Startup.** The app starts with `APP_ENV` set. If `APP_ENV` is missing, it exits non-zero, so it can never read the wrong environment. `app/secrets.py` `load()` fetches the three secrets for that environment by name, with no version pinned (so it gets the latest). It gets back each value and its version id, and keeps both in a module-level dict in process memory. If any fetch fails for any reason (store unreachable, permission denied, secret missing), `load()` retries 3 times, 2 seconds apart, then the app exits non-zero. A pod that cannot get its keys never serves, and the rolling deploy halts with the old pods still serving.
2. **Ready.** `/healthz` returns 200 only after all three keys are loaded. It returns `{"status": "ok", "secret_versions": {...}}`, which maps each secret name to its current version id and never includes a value. Operators and the rotation check read it. Readiness is decided at startup only. Once a pod is ready, `/healthz` stays 200 even if the store later becomes unreachable. The pod keeps serving with its last good keys, because failing readiness would cause the outage this plan avoids.
3. **Using a key.** Each client (`PaymentsClient`, `EmailClient`, `GeocodingClient`) no longer copies the key at construction. It calls `secrets.get(name)` on every provider call, so a refreshed key takes effect without a restart. A call already in flight finishes with the key it started with. During rotation both old and new keys are valid, so this is safe.
4. **Refresh.** Every 5 minutes a background timer in each instance calls `refresh()`. It re-reads each of the three secrets (latest version) and swaps in any new value and version id. Each secret is handled on its own. If two reads succeed and one fails, the two new values are swapped in and the third keeps its last good value. This is safe because the keys are independent. A failed re-read logs a warning with the secret name but no value, and the next tick tries again. The timer starts when the instance starts. Instances do not coordinate, so their ticks are not aligned. Nothing alerts on a stuck refresh. The rotation check in rollout step 5(e) catches it: a stuck instance shows an old version id, so the old key is not revoked.
5. **Local development.** `make run` sets `APP_ENV=dev`. The app then reads `orders-api/dev/*`, which hold sandbox keys. Engineers can read dev secrets only, so nobody needs a prod secret to work locally.

## How we roll it out

Each step says what starts it and what happens if it goes wrong.

1. **Set up access (security).** Create the access policies for `orders-api-prod`, security on-call and engineers, as in the rules above. Also let engineers read `orders-api/dev/*`. Nothing is live yet, so a wrong policy is fixed before going on.
2. **Create the secrets.** Security on-call writes `orders-api/prod/{payments,email,geocoding}_api_key` with the current (leaked) values, so behaviour is unchanged. Engineers write `orders-api/dev/*` with sandbox keys. The store keeps these. If a write fails, retry it. Nothing depends on the secrets yet.
3. **Ship the code.** One change adds `app/secrets.py` (`load()`, `refresh()`, `get(name)`), switches the three clients to `secrets.get()`, adds `secret_versions` to `/healthz`, sets `APP_ENV=prod` in the prod deploy config, and sets `APP_ENV=dev` in `make run`. CI builds the image. Merging does not change which keys are valid.
4. **Deploy and verify.** The rolling deploy replaces pods one at a time. A new pod becomes ready only after loading all three keys. After the deploy, query `/healthz` on each of the 4 replicas directly, not through the load balancer, and check that all report the same `secret_versions`. If a pod never becomes ready, the rollout halts, the old pods keep serving, and we fix the cause. Rollback is redeploying the earlier image, which still works because the old keys are still valid.
5. **Rotate each key.** Security on-call does this for each provider in turn.
   - (a) Create a new key at the provider while the old one stays valid.
   - (b) Test the new key at the provider with one harmless authenticated call, before it goes near the store. If the test fails, discard the key and go back to (a). Nothing has changed for the app, so no request is affected.
   - (c) Write the tested key to the store as a new version of the same secret.
   - (d) Within 5 minutes every instance refreshes and starts using it (up to one full tick, since timers are not aligned).
   - (e) Query each of the 4 replicas directly and check that every one reports the new version id in `/healthz`.
   - (f) Only then revoke the old key at the provider. If any instance still shows the old version, do not revoke. Wait one more refresh (another 5 minutes), check again, and investigate if it is still old.
   - If a key that passed (b) still proves bad in use, the old key is still valid, so write the previous value again as a newer version. Instances recover on their next refresh.
6. **Remove the keys from the repo.** After rotation, delete the `api_key` entries from `config/app.yaml`. Add a CI check that fails any change where `config/app.yaml` contains an `api_key` key. The check only reads the file and never needs a secret. If it fails, the change is blocked until the key is removed.
7. **Update the rollback notes in `deploy.md`.** Once old keys are revoked, an image built before this migration cannot work, because its keys are dead. Rollback must target an image from step 3 or later, which reads the store.

## What happens when things fail

| Where | Failure | What happens |
|---|---|---|
| Startup | Store unreachable, permission denied or secret missing | 3 retries, 2 seconds apart, then exit non-zero. The pod is not ready. The rollout halts. Old pods keep serving. |
| Startup | `APP_ENV` missing | Exit non-zero. |
| Running | Store becomes unreachable after the pod is ready | `/healthz` stays 200. The pod keeps serving with its last good keys. |
| Refresh | Store unreachable or one read fails | That secret keeps its last good value, a warning is logged, and the next tick retries. Secrets read fine are still swapped in. |
| Rotation | New key fails the test at the provider (5b) | It is never written to the store. The old key is untouched. Make another new key. |
| Rotation | An instance still shows the old version | Do not revoke the old key. |
| Rotation | New key passed the test but is rejected in use | The old key is still valid. Write the previous value again. Instances recover on their next refresh (up to 5 minutes). |
| CI | `api_key` found in `config/app.yaml` | The CI check fails the change. |
| Rollback after revoke | Pre-migration image deployed | Not allowed. Use an image from step 3 or later. |

## Open questions

- Rotation schedule: whether keys must be rotated regularly after this migration, and how often. Security has not decided. This plan does not pick a cadence.
- Which secret store product this is, and how a pod proves it is `orders-api-prod` when calling it. This does not affect the flow above.
- Whether the store returns the newest version by default when a read names no version, or whether a version must be marked current. The plan assumes the newest. Confirm before step 5.
- How operators reach each replica's `/healthz` individually (for example by pod address or port-forward). The plan requires per-replica checks but does not name the cluster tooling.
- Who can reach `/healthz` from outside the cluster. It shows only version ids, but the exposure is not confirmed.
- Whether a stuck refresh should alert someone. The brief only requires a warning log, so none is planned.
- Which harmless call tests each new key in step 5(b), per provider. Security on-call picks one.
- A key can pass the 5(b) test and still fail in real use (for example a limit or scope the test does not touch). Requests could then fail for up to 5 minutes until the previous value is written back and refreshed. The plan cannot rule this out.