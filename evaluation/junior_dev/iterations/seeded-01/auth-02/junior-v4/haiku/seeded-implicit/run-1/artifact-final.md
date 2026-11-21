# Plan: move API keys to the secret store

## What this is and how it goes

`orders-api` has three live provider keys (payments, email, geocoding) in `config/app.yaml`. That file is in git and copied into every image. The app reads it once at start-up, so changing a key means a new image and a redeploy.

This plan moves the keys into the managed secret store. The app loads them into memory at start-up and re-reads them every 5 minutes. Each key is then rotated at its provider. An old key is revoked only after every pod uses the new one.

Main flow: store the current keys, switch the app to read the store, deploy, rotate, confirm every pod, revoke.

## Terms

- **Secret store**: our managed store. It encrypts each secret with a per-environment KMS key. Every write creates a new version with its own id.
- **Version id**: the id of one stored value. It is safe to log.
- **Latest version**: the newest version of a secret. The app always reads this.
- **APP_ENV**: `prod` or `dev`. The app reads secrets from `orders-api/<APP_ENV>/<name>`.
- **Service identity**: `orders-api-prod`. All production pods run under it.
- **Pod**: one running copy of the app. Production runs 4.

## Rollout steps

Each step says what starts it, what it does, where its state lives, and what happens if it fails.

1. **Set access.**
   - Starts: the plan is approved.
   - Does: gives `orders-api-prod` read access to `orders-api/prod/*` only. Only the security on-call can write prod secrets. Engineers cannot read prod values.
   - State: store access policies.
   - If it fails: nothing has moved. Fix the policy and retry.

2. **Store the current keys.**
   - Starts: step 1 is done.
   - Does: writes the three current prod keys as version 1 under `orders-api/prod/`. Writes the sandbox keys under `orders-api/dev/`.
   - State: the store.
   - If it fails: nothing reads the store yet, so the app is unchanged. Retry.

3. **Ship the reader.**
   - Starts: the code change in `app/secrets.py` is ready.
   - Does: adds the reader described under "How the app reads keys". Each provider client calls `get(name)` on every request. `/healthz` gains `secret_versions`.
   - State: the code, then process memory at run time.
   - If it fails: the change is not merged, so nothing deploys.

4. **Remove keys from the repo.**
   - Starts: step 3 is merged.
   - Does: deletes the `api_key` lines from `config/app.yaml`. Adds a CI check that fails the build if `api_key` appears in that file. The prod deploy sets `APP_ENV=prod`. `make run` sets `APP_ENV=dev`.
   - State: git.
   - If it fails: CI blocks the merge, so nothing deploys.

5. **Write rollback notes.**
   - Starts: step 4 is ready.
   - Does: adds the rollback rules below to `deploy.md`.
   - State: git.
   - If it fails: do not deploy until the notes exist.

6. **Deploy and verify.**
   - Starts: the merge to `main`, then the CI image build.
   - Does: rolling deploy with `maxUnavailable: 0`. A new pod loads its keys before it serves, and `/healthz` returns 200 only after that. Then the operator checks that every pod shows version 1 for all three names.
   - State: pods and the log service.
   - If it fails: a new pod that cannot load its keys exits and never becomes ready. The rollout halts and old pods keep serving. Check the rollout status and that pod's logs for the load failure, then fix and redeploy.
   - A slow rollout is not a failure. The new pod becomes ready within the wait limit (see open questions).

7. **Rotate at providers.** For each provider, in turn:
   - Starts: step 6 is verified.
   - a. Create a new key at the provider. The old key stays valid.
   - b. Check the new key at the provider before it goes into the store.
   - c. The security on-call writes the new key to the store as a new version. The write returns a version id. Keep the three ids for step 8.
   - State: the store (old and new versions) and the provider.
   - If key creation or the check fails: the store is not written, no pod gets the new key, and the app keeps working.
   - If the store write fails: the store still holds version 1, nothing is revoked, and the app keeps working.

8. **Confirm every pod.**
   - Starts: step 7 writes are done.
   - Does: waits 10 minutes, so each pod refreshes at least twice. The operator lists the pods (4 expected) and reads `/healthz` on each. Every pod must show, for all three names, the version id that step 7 returned.
   - State: none kept. The check reads `/healthz` live.
   - If a pod is missing, unreachable or shows an old id: do not revoke. Investigate first. The old keys stay valid.

9. **Revoke old keys.**
   - Starts: step 8 confirms every pod.
   - Does: revokes each old key at its provider.
   - State: the provider.
   - If it fails: the old key stays valid. Retry.
   - This is the point of no return for rollback.

## How the app reads keys at runtime

This is how the running app works. It is separate from the rollout.

1. **Start-up.**
   - Starts: the process starts.
   - Does: `load()` runs before the HTTP server listens. It reads the latest version of the three keys for `APP_ENV`.
   - State: process memory.
   - If the store cannot be reached: it retries 3 times, 2 seconds apart. If it still fails, the process exits with a non-zero code. The server never starts, so the pod never becomes ready.
   - If `APP_ENV` is unset or unknown: the app refuses to start.

2. **Health check.**
   - Starts: a `/healthz` request.
   - Does: returns 200 only after `load()` has succeeded. It also returns `secret_versions`, which maps each name to the version id the pod holds. Today `/healthz` answers as soon as the server listens. That changes here.
   - State: process memory.
   - If `load()` has not succeeded: it does not return 200.

3. **Refresh.**
   - Starts: every 5 minutes.
   - Does: `refresh()` reads the latest version of each key. On success it replaces the in-memory value and logs the new version id.
   - State: process memory.
   - If it fails: it keeps the last good value and logs a warning. The warning never includes a key value.

4. **Each request.**
   - Starts: a client call.
   - Does: the client calls `get(name)`, which returns the value held in memory. A refreshed key is used by the next request, with no restart.
   - State: process memory.
   - If it fails: no store call is made on the request path, so a store outage does not reach requests.

Key values live only in process memory. They never go to disk, into environment variables or into logs.

## What happens when things fail

| Failure | What happens |
|---|---|
| Store unreachable at start-up | 3 retries, 2 seconds apart, then the process exits. The pod never becomes ready. |
| Store unreachable at refresh | The last good value stays in use. A warning is logged. |
| New pod cannot load keys during rollout | The rollout halts. Old pods keep serving. |
| Provider rejects the new key at the check (step 7) | The store is not written. The app is unchanged. |
| Store write fails (step 7) | The store keeps version 1. Nothing is revoked. |
| Pod missing or shows an old id (step 8) | Do not revoke. Investigate. |
| Revoke fails (step 9) | The old key stays valid. Retry. |
| A bad key reaches pods (step 7) | Requests that use it fail until the next refresh, within 5 minutes. See rollback. |

## Rollback rules

- **Before step 9:** redeploy the last image built before this change. Its `config/app.yaml` still has the keys, and those keys are still valid.
- **After step 9:** do not roll back to any image from before the migration. Its keys are revoked. Fix forward, or roll back to a post-migration image, which reads the store.
- **Failed rollout (step 6):** no rollback is needed. Old pods keep serving. Fix and redeploy.
- **Bad new key (step 7):** the check before the store write stops most bad keys. If one still reaches pods, the security on-call writes the previous version's value back to the store as the latest version. Pods pick it up at their next refresh, within 5 minutes. Requests that used the bad key fail until then. The old key still works until step 9.

## Open questions

- Which product is the secret store, and how does `orders-api` authenticate to it?
- Who may rotate keys, and who creates the new key at each provider? The brief does not say.
- How is a new key checked at each provider before it goes into the store? Does each provider offer a way to do that?
- Does each provider let an old key and a new key be valid at the same time? Step 7 assumes yes.
- A bad key that reaches pods makes requests fail until the next refresh. A fallback to the old key would prevent this, but it is a new mechanism. Should it be added?
- How does the operator reach `/healthz` on each pod?
- How long does the rollout wait before it counts as halted?
- Does the store return the latest version by default when the app reads a name?
- Do sandbox keys exist at each provider for dev use?
- Should keys be rotated on a schedule after this migration? Security has not decided. This plan sets no cadence.