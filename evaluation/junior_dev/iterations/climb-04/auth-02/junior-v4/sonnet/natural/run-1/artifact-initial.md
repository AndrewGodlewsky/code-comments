# Plan: move `orders-api` provider keys into the managed secret store

## Scope and assumptions to confirm first

- Secrets are `payments_api_key`, `email_api_key` and `geocoding_api_key`. Each lives at `orders-api/<env>/<name>`.
- Everything else in `config/app.yaml` (URLs, timeouts, from-address) stays in the file.
- **Assumption A (blocking).** Each of the three providers lets two keys be valid at the same time. The whole zero-failure rollout depends on this. Step 1 checks it.
- **Assumption B.** The prod pods get store access through the cluster's workload identity for `orders-api-prod`, not through a static credential or an environment variable.
- **Assumption C.** Nothing outside `orders-api` uses the current keys. Step 8 checks this against the provider's "last used" data.

## Open question (not decided)

**Should keys be rotated on a regular schedule after this migration, and how often?** Security has not decided. This plan sets no cadence. The runtime design (steps 12 to 17) lets a rotation reach running instances within 5 minutes without a restart. Any later schedule can therefore reuse steps 5, 7, 8 and 9 without changing the app.

---

## Part 1: Rollout

### 1. Verify provider support and prepare the store (no app change)
- **Starts it:** approval of this plan. Security on-call and the platform owner do it.
- **What moves:** nothing yet. For each provider, confirm that a second key can be created while the first stays valid (Assumption A). Create the empty secret paths for prod, staging and dev. Attach the per-environment KMS keys. Create these access policies:
  - `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else.
  - Only the security on-call group can write `orders-api/prod/*`.
  - Engineers get no read on `orders-api/prod/*`. They get read on `orders-api/dev/*`.
- **State lives in:** store policies and KMS key policies.
- **If it fails:** if any provider cannot hold two valid keys, stop. Escalate to that provider for an overlap window or a different mechanism, because a hard cutover would break customer requests. If a policy is wrong, fix it before going on. Nothing in production has changed yet.

### 2. Test the access policies
- **Starts it:** step 1 is done.
- **What moves:** a throwaway test secret is written under `orders-api/prod/` by the security on-call. It is read by `orders-api-prod` from a staging-style test pod. An engineer account then tries to read it, and `orders-api-prod` tries to read a path outside `orders-api/prod/*`. The test secret is deleted afterwards.
- **State lives in:** store audit logs.
- **If it fails:** an allowed read that is denied, or a denied read that succeeds, is a policy bug. Fix and repeat. Do not go on until all three outcomes are correct.

### 3. Build the code change (one PR, not yet deployed)
- **Starts it:** step 2 passes.
- **What moves:** keys leave `app/config_loader.py`, the clients and `config/app.yaml`.
  - Add the secret provider module and change the three clients to use it (steps 12 to 17).
  - Change `/healthz` to report readiness (step 13).
  - Delete the three `api_key` lines from `config/app.yaml`.
  - Add the local-dev backends (step 11).
  - Add the CI guard (step 10).
- **State lives in:** git and the PR. New images contain no keys.
- **If it fails:** failing CI blocks the merge. No production impact, because nothing is deployed.

### 4. Deploy to staging and exercise failure paths
- **Starts it:** the PR is merged to a branch or staging pipeline. Staging has its own `orders-api/staging/*` secrets with non-production provider keys.
- **What moves:** the image goes to staging. Test these cases:
  - a normal start;
  - an unreachable store (the pod must exit non-zero after the retries and never turn ready);
  - a new version written while running (picked up within 5 minutes);
  - a failed refresh (last good value kept, warning logged);
  - a grep of logs, environment and filesystem for key values (must find nothing).
- **State lives in:** the staging cluster and its store namespace.
- **If it fails:** fix the code and redeploy to staging. Prod is untouched.

### 5. Create new provider keys and write them to the prod store
- **Starts it:** step 4 passes.
- **What moves:** the security on-call creates a new key at each provider. The old key stays active.
  1. The on-call makes one harmless authenticated test call per new key, to prove it works.
  2. The on-call writes each new key to `orders-api/prod/<name>`. The store assigns a version id.
  3. The on-call records the version ids and not the values.
  - Engineers never see the values.
- **State lives in:** the store (encrypted by the prod KMS key) and the providers' key lists. Running prod pods still hold the old keys from their baked-in file and are unaffected.
- **If it fails:** if the test call fails, the key is not written. Create another. If a wrong value was written anyway, write the correct value as a new version. Nothing in prod reads the store yet, so there is no customer impact.

### 6. Roll out the new image to prod, with a canary pause
- **Starts it:** the store holds all three new prod keys and the image is merged to `main`. CI builds it.
- **What moves:** a normal rolling deploy (one pod at a time, `maxUnavailable: 0`), with a hold after the first new pod. The new pod starts and reads its three keys from the store (steps 12 and 13). It becomes ready only if all three load. Traffic then shifts to it while the 3 old pods keep serving with the old keys. Both old and new keys are valid, so every request succeeds either way. After a 10-minute hold with error rates normal, the rest of the pods are replaced.
- **State lives in:** pod memory (the keys) and the Kubernetes rollout state.
- **If it fails:**
  - If the store is unreachable or a secret is missing, the new pod exits non-zero and never turns ready. The rollout halts and the old pods keep serving. No customer request is affected.
  - If the canary shows provider auth errors, undo the rollout. Rollback to the previous image is safe at this point, because the old keys are still valid. Then investigate the store value.

### 7. Confirm every running instance uses the new keys
- **Starts it:** the rollout finishes (4 of 4 pods on the new image).
- **What moves:** read-only checks, with no key values involved.
  - Each pod logs, and exposes on an internal endpoint, the version id it holds for each secret. Compare all 4 pods against the version ids recorded in step 5.
  - Check that no pod is still running a pre-migration image.
  - Wait at least two refresh intervals (10 minutes). A pod that picked up a newer version would show it.
- **State lives in:** pod logs, the internal version endpoint, and the cluster's pod list.
- **If it fails:** if any pod reports a different version id or an old image, do not go on. Find out why and fix it. The old keys stay active the whole time.

### 8. Check that the old keys are idle at the providers
- **Starts it:** step 7 passes.
- **What moves:** the security on-call checks each provider's "last used" or usage data for each old key. The old keys should show no traffic for at least 30 minutes. This also finds unknown users of the old keys (Assumption C): developer machines running `make run`, scripts, and other services.
- **State lives in:** the providers' usage dashboards.
- **If it fails:** if an old key is still used, find the caller and move it to its own credentials before revoking. Do not revoke while the key is in use.

### 9. Revoke the old keys, one provider at a time
- **Starts it:** steps 7 and 8 both pass for that provider.
- **What moves:** the security on-call revokes the old key at the provider. After each one, watch the error rate and provider auth failures for 15 minutes before the next.
- **State lives in:** the providers' key lists. A revoked key cannot be restored.
- **If it fails:** a revocation cannot be undone, so the guard is steps 7 and 8. If errors do appear, create another new key (step 5 procedure) and write it to the store. Running pods pick it up within 5 minutes.
- **Rollback rule from here on:** a pre-migration image holds a revoked key and would fail every request. To stop that, remove the pre-migration images from the registry and from the deploy tooling when the first key is revoked. They also contain the leaked keys. Rollback is allowed only to images that read from the store.

### 10. Turn on the CI guard
- **Starts it:** part of the step 3 PR. It becomes a required check on `main` before step 6.
- **What moves:** a CI job parses `config/app.yaml` and fails if any key named `api_key` appears at any depth, whatever its value (empty values included). It also has a self-test: a fixture file containing an `api_key` must make the job fail.
- **State lives in:** the CI config and branch protection.
- **If it fails:** the check fails the PR, which is the intended behavior. If the job itself breaks, the self-test fails and blocks merges until it is fixed.

### 11. Local development without prod secrets
- **Starts it:** an engineer runs `make run` after step 6.
- **What moves:** the app picks its secret backend from `APP_ENV`, which defaults to `dev` and never to `prod`.
  - **`make run`** reads `orders-api/dev/*` from the store with the engineer's own identity. These hold provider sandbox keys.
  - **`make run-offline`** uses a stub backend with fake local provider servers. It needs no store and no keys. The values are dummy and are not secrets.
  - The same code path (steps 12 to 17) runs in both, and key values still stay in memory only.
- **State lives in:** the dev store namespace, or nothing at all (offline mode).
- **If it fails:** a missing dev secret gives the same startup exit as prod. There is no fallback to prod. Engineers could not read prod values anyway (step 1).

---

## Part 2: How the app reads keys at runtime

### 12. Startup: load all three keys before doing anything else
- **Starts it:** process start, before the HTTP server begins serving traffic.
- **What moves:** `app/secrets.py` asks the store for the three secrets using the workload identity. For each one it gets a value and a version id. They go into one immutable in-memory snapshot, a map of name to `(value, version_id)`. The version ids are logged, and the values are not.
- **State lives in:** process memory only. Nothing goes in environment variables, on disk or in logs. Core dumps are disabled for the container, and HTTP client debug logging redacts the `Authorization` header.
- **If it fails:** the app tries once and then retries 3 times, 2 seconds apart (4 attempts in total). If a secret is still unavailable, the process logs an error without values and exits with a non-zero code.

### 13. Readiness: ready only when the keys are loaded
- **Starts it:** the kubelet's readiness probe on `GET /healthz`.
- **What moves:** `/healthz` returns 200 only after the snapshot from step 12 holds all three keys. Before that it returns 503. After that it stays 200, even if later refreshes fail, because the last good keys are still usable.
- **State lives in:** a flag in process memory.
- **If it fails:** a pod that never loads its keys exits (step 12) and never turns ready. With `maxUnavailable: 0`, the rollout halts and the old pods keep serving. Set a rollout progress deadline so a halted rollout raises an alert.

### 14. Use the key on every call
- **Starts it:** each outbound call to a provider (`PaymentsClient.charge`, the email client and the geocoding client).
- **What moves:** the clients no longer copy the key in `__init__`. At call time they read `secrets.get('payments_api_key')` (or the email or geocoding name) from the current snapshot and build the `Authorization` header from that. Base URLs and timeouts still come from `app.yaml`.
- **State lives in:** the single current snapshot reference in memory.
- **If it fails:** a call in flight keeps the value it already read. The next call gets the newest value. If a provider rejects a key, the error is logged with the secret name and version id, never the value.

### 15. Refresh every 5 minutes
- **Starts it:** a background timer, 5 minutes after the last attempt, with a few seconds of random jitter so the 4 pods do not all hit the store at the same moment.
- **What moves:** the store is read again for each of the three secrets. For each secret that returns successfully, a new snapshot is built and swapped in atomically. If the version id changed, the change is logged ("payments_api_key: version A to version B"). A new key reaches every pod within about 5 minutes with no restart.
- **State lives in:** process memory only.
- **If it fails:** each secret is handled independently. If a read fails, or the secret is not found, the app keeps the last good value for that secret and logs a warning with the name and the error type (no values). The next cycle tries again.

### 16. Watch for stale keys
- **Starts it:** a metric published by every pod.
- **What moves:** each pod exports the age of its last successful refresh per secret, and the version id it holds, as metrics and in logs. Alert when any secret has been stale for more than 15 minutes (3 missed refreshes). The step 7 comparison uses the version ids.
- **State lives in:** the metrics and log services (version ids and ages only).
- **If it fails:** the app keeps running on the last good value. The alert tells a human that the store, the network or the permissions need attention before a rotation is attempted.

### 17. Rotation (used now in steps 5 to 9, and by any future schedule)
- **Starts it:** the security on-call, on their own decision. The cadence is the open question above.
- **What moves:** repeat steps 5, 7, 8 and 9. Create the new provider key while the old one is valid, test it, then write it to the store. Running instances pick it up through step 15. Check every instance's version id and the provider's last-used data, and only then revoke the old key.
- **State lives in:** the store (a new version id per write) and the providers.
- **If it fails:** a bad new value is replaced by writing a corrected version, and the old key is still valid until step 9. This is why the old key is never revoked before every instance is confirmed on the new one.

## Final checks before closing the migration
- Search the pipeline logs, container environment and image layers for the three old and three new key values. None should be found.
- Confirm the CI guard fails on a test change that adds `api_key` to `config/app.yaml`.
- Confirm that an engineer account cannot read `orders-api/prod/*` and that the security on-call can write it.
- Leave the rotation-cadence question open until Security decides.
