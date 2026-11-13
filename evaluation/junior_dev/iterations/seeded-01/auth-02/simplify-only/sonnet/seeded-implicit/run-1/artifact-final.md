# Plan: move API keys into the secret store

## Summary

`orders-api` has three third-party API keys (payments, email, geocoding) in `config/app.yaml`. That file is committed to git and copied into every container image. Today `app/config_loader.py` reads it once at import. Each provider client copies its key at construction and never re-reads it. Changing a key means a new image and a redeploy. `/healthz` returns 200 as soon as the HTTP server listens.

The plan has two parts. The runtime part makes the app fetch keys from the secret store at startup, keep them only in memory, and re-read them every 5 minutes. The rollout part moves the keys in an order that never leaves a running instance without a valid key, then rotates them, because the current keys count as leaked.

## Terms

- **Secret store**: our managed store. It encrypts each secret with a per-environment KMS key and gives every write a new version id.
- **Secret name**: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`. The names are `payments_api_key`, `email_api_key` and `geocoding_api_key`.
- **Secrets module**: new file `app/secrets.py`. It holds the keys in memory and offers `get(name)`.
- **Rotation**: creating a new key at the provider and writing it to the store as a new version.
- **Revoking**: disabling the old key at the provider.

## How the app reads keys at runtime

Runtime facts that hold for every step below:

- Key values live only in process memory. They never go to disk, environment variables or logs. Version ids may be logged.
- Provider clients call `secrets.get(name)` on every request. They no longer copy the key at construction. This is what lets a refreshed key take effect without a restart.
- The environment comes from `APP_ENV` (`prod` or `dev`). It decides which `orders-api/<env>/*` secrets are read.

## Rollout steps

Each step gives its trigger, what it does, where the state lives, and what happens if it fails.

1. **Set up access.**
   - Trigger: a person in the security team starts the migration.
   - Does: grants the prod service identity `orders-api-prod` read-only access to `orders-api/prod/*` and nothing else. Only the security on-call may write prod secrets. Engineers get no read access to prod values. Engineers may read and write `orders-api/dev/*`.
   - State: access policies in the secret store.
   - If it fails: stop. Nothing else depends on it yet, and nothing in production has changed.

2. **Create the secrets.**
   - Trigger: step 1 is done.
   - Does: the security on-call writes `orders-api/prod/{payments,email,geocoding}_api_key` with the current live key values. Someone writes `orders-api/dev/*` with sandbox keys from each provider.
   - State: the secret store.
   - If it fails: stop and retry the write. Production still runs on the old file.

3. **Add the secrets module and switch the clients.**
   - Trigger: code change merged to `main`, and CI builds an image.
   - Does: adds `app/secrets.py` and switches the three clients to `secrets.get()`. Adds the secret version ids to `/healthz` output (ids only). Makes `/healthz` return 200 only after all three keys are loaded. The runtime behaviour is below.
   - State: in-process memory only.
   - If it fails: tests fail in CI and the change does not merge.

   Runtime behaviour of the secrets module:
   - **Startup**: `load()` reads all three keys. If the store is unreachable it retries 3 times, 2 seconds apart, then exits with a non-zero code. `/healthz` stays not-ready until all three are loaded.
   - **Refresh**: every 5 minutes `refresh()` re-reads all three keys. A new version is picked up without a restart. If a read fails, the module keeps the last good value and logs a warning.

4. **Keep the keys in the file for this release.**
   - Trigger: the same release as step 3.
   - Does: the image still contains the old `api_key` entries in `config/app.yaml`, but nothing reads them. This is the safe fallback: rollback to an earlier image works, because that image reads its own file.
   - State: the image.
   - If it fails: see the failure table.

5. **Deploy and verify.**
   - Trigger: a person starts the rolling deploy, one pod at a time, with `maxUnavailable: 0`.
   - Does: each new pod must pass `/healthz`, so it must have loaded all three keys, before an old pod stops. After the deploy, check that all 4 replicas report the expected secret version ids on `/healthz`.
   - State: the cluster. Keys are in each pod's memory.
   - If it fails: a pod that cannot load its keys never becomes ready. The rollout halts and the old pods keep serving. Fix the access or the secret, or roll back.

6. **Remove the keys from the repo file and block their return.**
   - Trigger: step 5 is verified in prod.
   - Does: deletes the `api_key` entries from `config/app.yaml`. Adds a CI check that fails any change that puts an `api_key` back into that file. Sets `make run` to use `APP_ENV=dev`, so local runs read only the dev sandbox keys.
   - State: the git repo and the CI config.
   - If it fails: the CI check blocks the merge. Fix and resubmit.

7. **Rotate the keys.**
   - Trigger: step 6 is deployed.
   - Does: for each provider, the security on-call creates a new key and writes it to the store as a new version. Running pods pick it up within 5 minutes.
   - State: the provider and the secret store.
   - If it fails: the old key is still valid, so nothing breaks. Retry.

8. **Confirm, then revoke the old keys.**
   - Trigger: step 7 is done for a key.
   - Does: waits until every running instance reports the new version id on `/healthz`. This is more than one refresh interval. Only then revokes the old key at the provider.
   - State: the provider.
   - If it fails: if any instance still reports the old version, do not revoke. Find out why, for example a failing refresh in the logs, and fix it first.

9. **Update the rollback notes in `deploy.md`.**
   - Trigger: step 8 is done.
   - Does: records that rolling back to an image from before this change no longer works once the old keys are revoked, because those images read keys from the file.
   - State: `deploy.md`.
   - If it fails: nothing breaks. Fix the doc.

## What happens when things fail

| Situation | What happens |
|---|---|
| Store unreachable at startup | 3 retries, 2 seconds apart, then the app exits non-zero. The pod is never ready and the rollout halts. |
| Store unreachable on a refresh | The app keeps the last good key and logs a warning. Requests keep working. |
| New pod cannot load keys | It never becomes ready and the old pods keep serving. |
| A key is revoked too early | Prevented by step 8, which waits for every instance to report the new version. |
| Someone adds `api_key` back to the file | CI fails the change. |

## Open questions

- Must keys be rotated on a regular schedule after this migration, and how often? Security has not decided. This plan does not pick a cadence.