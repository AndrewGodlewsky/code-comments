# Plan: move orders-api's API keys into the secret store

## Today
- `config/app.yaml` is committed and copied into every image. It holds three live keys: `payments.api_key`, `email.api_key` and `geocoding.api_key`.
- `app/config_loader.py` reads that file once, at import. Nothing re-reads it.
- Each provider client (`PaymentsClient`, `EmailClient`, `GeocodingClient`) copies its key into itself once, when it is built at import.
- Prod runs 4 pods under the identity `orders-api-prod`. Deploys replace one pod at a time (`maxUnavailable: 0`), and a new pod must pass `GET /healthz` before an old one is stopped. If a new pod never becomes ready, the rollout halts and the old pods keep serving. Today `/healthz` passes as soon as the server is listening.
- `make run` uses the same file, so local runs use the live keys.

## Where state lives after the change

| What | Where | Who can read / write |
|---|---|---|
| Prod key values | Secret store, `orders-api/prod/<name>` for `payments_api_key`, `email_api_key` and `geocoding_api_key`. Encrypted with the prod KMS key. Every write gets a new version id. | `orders-api-prod`: read-only, and nothing outside `orders-api/prod/*`. Security on-call: the only writer. Engineers: no access. |
| Dev (sandbox) key values | Secret store, `orders-api/dev/<name>`, encrypted with the dev KMS key. | Engineers read and write them with their own login. |
| Keys inside a running app | In-memory cache in each process: `{name: (value, version_id)}`. | Only that process. Never written to disk, environment variables or logs. |
| Non-secret settings (URLs, timeouts, port) | `config/app.yaml`, as today. | The repo. |

`config/app.yaml` is **not** a fallback source for keys. After rollout step 3 it contains no keys.

## How the app reads keys at runtime (new `app/secrets.py`)

1. **Startup load**
   - **Starts:** process start, in `main`, before the HTTP server starts listening. So `/healthz` cannot pass until this succeeds.
   - **Moves:** reads `APP_ENV` (`prod` or `dev`) and fetches the three secrets from `orders-api/<env>/*` with the process's own identity: `orders-api-prod` in prod, the developer's own login under `make run`.
   - **State:** each value and its version id go into the in-memory cache.
   - **If it fails** (store unreachable, access denied, or any one secret missing even if the other two are there): do not start with a partial set. Retry the whole load 3 times, 2 seconds apart. If it still fails, log the error (secret names only, never values) and exit with a non-zero code. The pod never becomes ready. During a deploy, the rollout halts and the old pods keep serving.
2. **Refresh every 5 minutes**
   - **Starts:** a background timer, every 5 minutes after the startup load.
   - **Moves:** re-reads all three secrets from the store. If a version id has changed, the new `(value, version_id)` pair replaces the old entry in one assignment, so a request sees either the old pair or the new one, never a mix. Logs `<name> now at version <id>`.
   - **State:** the same in-memory cache.
   - **If it fails** (whole store or one secret): keep the last good value for each secret that could not be read, update the ones that could, log a warning (name and error, no value) and try again at the next tick. The app keeps running and stays ready.
3. **Clients read the key on every request**
   - **Starts:** every outgoing call to a provider.
   - **Moves:** the client calls `secrets.get("<name>")` and puts the value in the `Authorization` header. Clients no longer copy the key when they are built, so a refreshed key is used from the next request on, with no restart.
   - **State:** none in the client. The cache is the only copy.
   - **If it fails:** `get()` cannot miss, because startup guarantees all three entries and refresh never removes one. If the provider rejects the key (for example, because it was revoked), that request fails like any provider error today, and the client logs the secret name and version id, not the value. Rollout step 5 makes sure no key is revoked while a pod still uses it.
4. **Version report**
   - **Starts:** every `GET /healthz` (the readiness probe, or an engineer checking pods during the rollout).
   - **Moves:** version ids from the cache into the response: `{"status": "ok", "secret_versions": {"payments_api_key": "<id>", ...}}`. Never values.
   - **State:** reads the cache only. It never calls the store.
   - **If it fails:** because it never calls the store, a store outage after startup does not make a pod unready. The reported versions stay at the last good ones until a refresh succeeds.

## Rollout steps

1. **Set access**
   - **Starts:** the plan is approved. Nothing is in the store yet.
   - **Moves:** access policies in the store. `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else. The security on-call gets write on `orders-api/prod/*`. Engineers get read and write on `orders-api/dev/*` and no access to `orders-api/prod/*`.
   - **State:** the store's access policies.
   - **If it fails:** test that an engineer is denied on a prod path and that `orders-api-prod` is denied on a dev path. If either is allowed, fix the policy and test again before step 2. Nothing reads the store yet, so customers are not affected.
2. **Put the current keys in the store**
   - **Starts:** step 1's tests pass.
   - **Moves:** the security on-call copies today's three prod values into `orders-api/prod/*`, which creates the first version of each. An engineer creates a sandbox key at each provider and writes it to `orders-api/dev/*`.
   - **State:** the store. The prod values are also still in `config/app.yaml` and in the running images, which keep using them.
   - **If it fails:** nothing reads the store yet, so a wrong or missing value has no effect. Write it again, which creates a new version.
3. **Ship the code change in one merge**
   - **Starts:** step 2 is done. Merging to `main` makes CI build the image and starts the rolling deploy.
   - **The merge contains:** `app/secrets.py` (runtime items 1–4) and the client change; the three `api_key` lines removed from `config/app.yaml`; `make run` setting `APP_ENV=dev`; a CI check, run on every change, that fails the build if `config/app.yaml` contains an `api_key` entry.
   - **Moves:** each new pod loads its keys from the store before it becomes ready. Old pods keep using the keys baked into their image.
   - **State:** new pods: the in-memory cache. Old pods: `config/app.yaml` in their image, until they are stopped.
   - **If it fails:** a new pod that cannot load its keys exits and never becomes ready. The rollout halts and the old pods keep serving with their baked-in keys, which are still valid. Customers see no errors. Fix the store or the access, then run the deploy again. If the CI check fails, the merge is blocked.
4. **Verify**
   - **Starts:** the rolling deploy has replaced all 4 pods.
   - **Moves:** an engineer calls `/healthz` on each pod. All 4 must show the first version id for all three secrets. Then run one payments, one email and one geocoding call.
   - **State:** nothing new.
   - **If it fails:** roll back by redeploying the previous image. Its keys in `config/app.yaml` still work, because nothing has been revoked. Fix the problem and repeat step 3.
5. **Rotate each key, one provider at a time**
   The old values are in git history, which we are not rewriting, so they count as leaked.
   - **Starts:** step 4 passes. Payments goes first, then email, then geocoding. Each provider starts only when the previous one is finished.
   - **Moves:**
     1. The security on-call creates a new key at the provider. The old key stays valid.
     2. The security on-call writes the new value to `orders-api/prod/<name>`, which creates a new version id. The value goes from the provider straight into the store, and no engineer sees it.
     3. Wait for the refresh: at most 5 minutes, but allow 10. Check `/healthz` on every pod. All 4 must show the new version id.
     4. Only then does the security on-call revoke the old key at the provider.
   - **State:** the store holds both versions. Each pod's cache switches to the new one at its next refresh.
   - **If it fails:**
     - A pod still shows the old version after 10 minutes: do not revoke. Look for refresh warnings in that pod's logs, or restart the pod, which forces a fresh startup load. The other pods keep serving.
     - Calls fail with the new key: the security on-call writes the old value back to the store as a new version. The old key still works, because it has not been revoked. Pods pick it up within 5 minutes. Fix the problem and start again at 5.1.
6. **Retire pre-migration images**
   - **Starts:** the last old key (geocoding) has been revoked.
   - **Moves:** update `deploy.md`: a rollback may only go to an image built from step 3's merge or later. Older images hold revoked keys.
   - **State:** the rollback rule in `deploy.md`.
   - **If it fails** (an older image is deployed anyway): its pods pass the old `/healthz`, which only checks that the server is listening, but every provider call fails. Redeploy the current image at once.

## Open question
- **Scheduled rotation.** Security has not decided yet whether keys must be rotated on a regular schedule after this migration, or how often. This plan covers only the one-time rotation in step 5. If a schedule is chosen, step 5 is the procedure to repeat.
