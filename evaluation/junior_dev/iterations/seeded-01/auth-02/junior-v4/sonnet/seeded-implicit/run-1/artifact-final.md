# Plan: move orders-api keys into the secret store

Today orders-api keeps three live provider keys (payments, email, geocoding) in `config/app.yaml`. That file is committed, copied into every image, and read once at startup. This plan moves the keys into our managed secret store. The app reads them from the store at startup and every 5 minutes. Then we rotate the keys at the providers, because the old ones are leaked in git history.

## Terms

- **Store**: our managed secret store. It encrypts with a per-environment KMS key. Every write creates a new version id.
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The names are `payments_api_key`, `email_api_key` and `geocoding_api_key`.
- **APP_ENV**: `prod` or `dev`. It picks `<env>` in the secret name. It is set in the deployment config and by `make run`. If it is unset, the app exits at startup. It never defaults to prod.
- **Version id**: the store's id for one value of a secret. It is safe to log. Values are not.

## How the app reads keys at runtime

Key values live only in process memory. They never go to disk, env vars or logs.

1. **Startup.** `app/secrets.py` `load()` runs before the HTTP server reports ready. It reads the three secrets for `APP_ENV`. It tries once, then retries 3 times, 2 seconds apart. If it still fails, the process exits non-zero.
2. **Ready.** `/healthz` returns 503 until `load()` succeeds. Then it returns 200 with the version id of each secret, for example `{"status":"ok","secret_versions":{"payments_api_key":"v7",...}}`. It never shows values. Rollout and rotation read it to see which version each pod uses.
3. **Use.** The three clients call `secrets.get("<name>")` on every outgoing request. They no longer copy the key in `__init__`, because a copy would stop a new key reaching a running pod.
4. **Refresh.** A background thread re-reads all three secrets every 5 minutes. If a read fails, `get()` keeps returning the last good value and a warning is logged, with no values. The next cycle tries again.

## Rollout steps

Each step lists what starts it, what moves, where state lives, and what happens on failure.

1. **Set access.** Starts: us, first. `orders-api-prod` gets read-only access to `orders-api/prod/*` and nothing else. Only security on-call can write prod secrets. Engineers get read and write on `orders-api/dev/*` and no access to prod. State: store policies. If wrong: fix the policy. Nothing else has changed yet.
2. **Fill the store.** Starts: security on-call. Copy the current three key values into `orders-api/prod/*`. Put sandbox provider keys in `orders-api/dev/*`. State: the store. If a copy is wrong: write a corrected version. Old pods are unaffected.
3. **Change the code.** Starts: a pull request. Add `app/secrets.py`. Switch the three clients to `secrets.get()`. Change `/healthz` as above. Delete the `api_key` lines from `config/app.yaml`. Add a CI check that fails the build if that file contains any `api_key`. Set `APP_ENV=dev` in `make run` and `APP_ENV=prod` in the production deployment config. State: git. If the check fails, the merge is blocked until the key is removed.
4. **Deploy.** Starts: merge to `main`, then the normal rolling deploy. Each new pod loads the keys from the store and becomes ready only if `load()` succeeds. If it does not, the pod exits, the rollout halts, and old pods keep serving with their yaml keys, so no request fails. State: pod memory. Verify: all 4 pods report all three version ids on `/healthz`.
5. **Rotate, one key at a time.** Starts: security on-call, after step 4 is verified.
   1. Create a new key at the provider. The old key stays valid.
   2. Write the new key to the store as a new version.
   3. Wait at least 5 minutes, then check that every pod's `/healthz` shows the new version id.
   4. Only then revoke the old key at the provider.

   State: the store, and pod memory. If any pod still shows the old version, do not revoke. Fix the pod or the store and check again. Both keys stay valid until then, so no request fails.
6. **Update rollback notes in `deploy.md`.** Starts: a pull request, after step 4. Rollback means redeploying an earlier image. Before step 5.4, an image from before the migration still works, because its yaml key is still valid. After the old keys are revoked, roll back only to images that include `secrets.py`. For a bad key value, write the previous version back to the store. No redeploy is needed. State: git.

## What happens when things fail

| Where | What happens |
|---|---|
| Store unreachable at startup | 3 retries, then the process exits non-zero. The new pod never becomes ready and the rollout halts. |
| Store unreachable during refresh | The last good value is kept, a warning is logged, and the next cycle retries. |
| A new key does not reach every pod | The old key is not revoked. |
| Local development | `make run` uses `APP_ENV=dev` and sandbox keys. Engineers cannot read prod values. |

## Open questions

- Which store product is it, and how does the pod authenticate as `orders-api-prod`? Not known yet. It affects step 1 and `load()`.
- Does each provider allow two live keys at once? Step 5 needs this. If a provider allows only one, zero-failure rotation is not possible for it.
- Should keys be rotated on a regular schedule, and how often? Security has not decided. This plan does not pick a cadence.
