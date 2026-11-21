# Plan: move API keys into the secret store

Today the three provider API keys (payments, email, geocoding) sit in `config/app.yaml`, which is committed to git and copied into every container image. `app/config_loader.py` reads that file once at import, and each provider client copies its key at construction, so a key change needs a new image. This plan puts the keys in the managed secret store, has the app load them at startup and re-read them every 5 minutes, and then rotates every key at its provider, because the old keys have been in git history for two years and count as leaked. We are not rewriting git history.

## Terms

- **Secret store**: our managed secret service. It holds each secret under `orders-api/<env>/<name>`, encrypts it at rest with a per-environment KMS key (KMS = key management service) and gives every write a new version id. The product is not named in the brief (see open questions).
- **Version id**: the id the store assigns to each write of a secret. It is safe to log. It tells us which value an instance holds.
- **Service identity**: the identity a workload presents to the store. Production pods run as `orders-api-prod`.
- **Replica**: one of the 4 production pods running the app.
- **Readiness probe**: `GET /healthz`. During a rolling deploy (one pod at a time, `maxUnavailable: 0`) the cluster does not stop an old pod until the new pod returns 200 here. If a new pod never becomes ready, the rollout halts and old pods keep serving.
- **`APP_ENV`**: `prod` or `dev`. It decides which store path the app reads (`orders-api/prod/*` or `orders-api/dev/*`).
- **Operator**: the engineer running the rollout.

## Rules that apply everywhere

- Key values live only in process memory. Never on disk, in environment variables or in logs. Logging version ids is fine.
- Secret names: `payments_api_key`, `email_api_key`, `geocoding_api_key`.
- Prod access: `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only the security on-call can write prod secrets. Engineers cannot read prod values.
- A missing, deleted or empty secret counts as a failed read, both at startup and on refresh.
- No customer request may fail because of a missing or revoked key at any point.
- The rotation schedule is not part of this plan (see open questions).

## How the app runs after the change

1. **Startup load.** Starts when the process starts. `app/secrets.py` reads `APP_ENV`, then reads all three secrets from `orders-api/<APP_ENV>/*` using the service identity, and keeps value and version id in memory only. If the store cannot be reached, it retries 3 times, 2 seconds apart, then the process exits with a non-zero code. If `APP_ENV` is unset it exits the same way, so a pod can never fall back to dev keys. `APP_ENV=prod` is set in the production deploy config.
2. **Readiness.** `/healthz` returns 503 until all three keys are loaded, then 200 with `{"status": "ok", "secret_versions": {"payments_api_key": "<id>", ...}}`. It holds version ids only, never values. Operators read it per replica to see which version each pod uses. A pod that cannot load never becomes ready, so the rollout halts.
3. **Refresh.** Every 5 minutes a background task re-reads all three secrets and swaps in any new value and version id. If a read fails, the app keeps the last good value and logs a warning (names and error only, no values), then tries again in 5 minutes. Each replica refreshes on its own timer, so for up to about 5 minutes after a new version is written, replicas can hold different versions. This is expected and safe, because rotation keeps the old key valid until every replica has the new one.
4. **Use in clients.** `PaymentsClient`, `EmailClient` and `GeocodingClient` no longer copy the key in their constructors. Each calls `secrets.get(name)` on every request, so a refreshed key is used by the next request. `base_url` and the timeouts still come from `config/app.yaml`, which `app/config_loader.py` keeps loading unchanged (the file just no longer contains `api_key`). `secrets.py` is separate and does not use `config_loader`. If a provider rejects a key, the client returns the error as it does today, with no re-read or retry, since the rotation order means a valid key is always in use.
5. **Local development.** `make run` sets `APP_ENV=dev` and reads `orders-api/dev/*`, which hold sandbox keys. Developers authenticate to the store with their own credentials, which can read `dev` only. Nobody reads prod values locally.

## Rollout, in order

1. **Access policies.** Security sets them: the read-only prod policy for `orders-api-prod`, prod writes for the security on-call only, no prod read for engineers, and dev read for engineers. If wrong, the startup load in step 4 fails and the rollout halts, which is safe.
2. **Create secrets.** The security on-call writes `orders-api/prod/*` with the current key values. Anyone with dev access writes `orders-api/dev/*` with sandbox keys. Running pods are unaffected.
3. **Code change, one merge.** Add `app/secrets.py` (`load()`, `refresh()`, `get(name)`), switch the three clients to `secrets.get()`, add `secret_versions` and the 503-until-loaded behaviour to `/healthz`, delete the `api_key` entries from `config/app.yaml`, and set `APP_ENV` in `make run` and the prod deploy config. `config_loader.py` is unchanged. Add a CI check that parses `config/app.yaml` and fails the build if a key named `api_key` appears anywhere in it.
4. **Deploy.** CI builds an image and the rolling deploy replaces pods one at a time. Old pods (keys from yaml) and new pods (keys from the store) serve together during the deploy. This is safe because the old keys are still valid. If a new pod stays unready, the rollout halts: fix it or roll back.
5. **Verify.** The operator checks that all 4 replicas are ready, each replica's `/healthz` shows all three version ids, the logs show no key values, and a payment, an email and a geocode request each succeed on the new pods.
6. **Rotate each key, one provider at a time.**
   1. Create a new key at the provider while the old one stays active.
   2. The security on-call writes the new value as a new version in the store.
   3. Wait at least 6 minutes (one 5-minute refresh plus margin), then check every replica's `/healthz` shows the new version id. Keep checking until all do. A replica whose refresh failed still shows the old id, so the check catches it.
   4. Only then revoke the old key at the provider. If any replica does not show the new version, do not revoke; find out why first.
7. **Update `deploy.md`.** Describe the new startup, the readiness change, the dev flow and the rollback rule below.

## Rollback

Until the old keys are revoked, redeploying the pre-change image works, because it still has its keys in the yaml. After step 6 revokes them, that image no longer works. From then on roll back only to images that include the secret-store code.

## What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Startup load | Store unreachable, identity or policy wrong, or a secret missing or empty | 3 retries 2 seconds apart, then exit non-zero. Pod never ready. Rollout halts, old pods serve. |
| Startup | `APP_ENV` unset | Exit non-zero. |
| Refresh | Read fails, or secret missing or empty | Keep last good value, log a warning, try again in 5 minutes. |
| Rotation | A replica still shows the old version | Do not revoke the old key. |
| CI | `api_key` present in `config/app.yaml` | Build fails. |

## Open questions

- Rotation schedule: whether keys must be rotated regularly after this migration, and how often. Security has not decided. This plan sets no cadence.
- Which secret store product this is, and how `orders-api-prod` authenticates to it (for example a workload identity token). Not stated in the brief.
- Whether each provider lets the old and new keys be active together. Step 6 needs this. If one does not, that key needs a separate plan.
- How operators call `/healthz` on each of the 4 pods individually (for example a port-forward or per-pod address), whether they are allowed to, and whether version ids may appear in its response.
