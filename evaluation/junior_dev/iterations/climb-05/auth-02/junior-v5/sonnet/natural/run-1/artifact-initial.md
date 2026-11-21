# Plan: move orders-api provider keys into the secret store

## Summary

The three live keys (payments, email, geocoding) move out of `config/app.yaml` into the managed secret store. The app then reads them from the store at runtime.

- **Rollout order.** New keys are issued at each provider while the old keys stay valid. A new image reads the new keys from the store. Only after every instance is confirmed on the new keys are the old keys revoked.
- **Runtime change.** The app loads the keys before it reports ready, and clients read the key on every request instead of copying it at construction. A background refresh picks up new versions every 5 minutes.
- **Why no customer request fails.** Old pods use old keys and new pods use new keys. Both are valid until the confirmation gate in step 8 passes.

### Assumptions to verify in step 1

- Each provider allows two API keys to be valid at the same time. If one does not, stop (see step 1).
- Each provider offers sandbox or test keys for dev. If not, local dev uses the offline mode in step 19.
- The platform gives pods their `orders-api-prod` identity without a static credential in an env var or on disk, for example workload identity.
- Prod deploys can be held back by a person or pipeline gate. If a merge to `main` auto-deploys to prod, steps 2 to 4 must be finished before the merge, and the readiness gate is the only safety net. Step 6 says what to do in each case.

### Open question: not decided

Security has not decided whether keys must also be rotated on a regular schedule after this migration, or how often. This plan picks no cadence.

- The mechanism supports any cadence. See "Later rotations" after step 19.
- Owner: security. Needed before the migration is closed out. The answer decides whether a reminder or scheduler is added.

---

## Part 1: Rollout

### 1. Inventory consumers and check provider capabilities

- **Starts when:** the plan is approved.
- **What moves where:** nothing moves. Produce a list of every caller of the three old keys:
  - every environment that runs the image (prod, staging, and anything using an `APP_CONFIG` override);
  - CI jobs and scripts;
  - developer laptops, which use the live keys through `make run`.

  Use each provider's "last used" and caller data to find callers nobody listed. Confirm with each provider that two keys can be valid at once, and that sandbox keys exist.
- **State lives in:** a checklist in the migration ticket. It contains no key values.
- **If it fails:** if a provider allows only one active key, stop. The zero-failure requirement cannot be met without a provider-side overlap window, so ask the provider for one and escalate to security. If an unknown caller shows up, add it to the migration scope. Step 8 must not pass until it is migrated.

### 2. Create the store layout, KMS keys and access policies

- **Starts when:** step 1 is done.
- **What moves where:**
  - Create one KMS key per environment.
  - Reserve the paths `orders-api/prod/*`, `orders-api/staging/*` and `orders-api/dev/*`, each encrypted with its own environment's KMS key.
  - Identity `orders-api-prod` gets read-only on `orders-api/prod/*` and nothing else.
  - Write on prod goes to the security on-call group only.
  - Engineers get no access to prod. They get read-only on `dev/*`.
  - Staging gets its own identity with the same shape.
- **State lives in:** store and IAM configuration kept as code, reviewed in the infra repo.
- **Verify with a non-sensitive probe secret** that security writes to `orders-api/prod/_probe`. All of these checks must pass:
  - `orders-api-prod` can read the probe.
  - `orders-api-prod` cannot write it.
  - `orders-api-prod` cannot read `staging/*` or `dev/*`.
  - An engineer cannot read the probe.
- **If it fails:** fix the policy and re-run the checks. No real key exists in the store yet, so nothing is exposed.

### 3. Security on-call issues new keys at each provider

- **Starts when:** the step 2 checks pass.
- **What moves where:**
  - Provider console to the on-call's session, then straight into the store (step 4). The value never goes into a file, ticket, chat, shell history or env var.
  - Old keys stay active.
  - Test each new key with a harmless read-only provider call.
  - Create sandbox keys for dev, and for staging if it should not use live keys.
- **State lives in:** the provider accounts (new key active alongside the old one). The ticket records only key ids or names.
- **If it fails:** if a new key does not validate, delete it at the provider and issue another. Nothing downstream depends on it yet.

### 4. Write the new keys into the store

- **Starts when:** step 3 produced validated keys.
- **What moves where:**
  - Security on-call writes `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key` and `orders-api/prod/geocoding_api_key`. The write is interactive, from a prompt or stdin, with no value on a command line.
  - Each write returns a version id. Record these in the ticket as the "expected versions" for step 8.
  - Write the sandbox keys to `staging/*` and `dev/*` the same way.
- **State lives in:** the store, encrypted with the per-environment KMS key. The store keeps an audit trail of who wrote and read.
- **If it fails:** retry the write. A partial set is harmless because nothing reads these paths yet. If a write was wrong, write a corrected value. This creates a new version id, so update the expected versions in the ticket.

### 5. Build and review the code change

- **Starts when:** it can begin any time. It must not merge before step 4.
- **What moves where:** one PR containing:
  - A secrets module implementing steps 13 to 17.
  - Clients changed to read the key per request (step 16).
  - `/healthz` gated on loaded keys (step 15).
  - The three `api_key` lines removed from `config/app.yaml`. `base_url`, timeouts and `from_address` stay.
  - The loader fails loudly if `api_key` appears in the YAML.
  - A CI check that fails any change putting an `api_key` back into `config/app.yaml`. It parses the YAML and fails on an `api_key` key at any depth. A secondary pattern scan covers `pk_live_`, `ml_live_` and `geo_live_`. It has its own test fixture, and it is a required status check in branch protection.
  - A log redaction wrapper, so a secret's `repr` and `str` print `<redacted>`.
  - Dev support (step 19).
  - Tests for each behavior in Part 2. One test asserts that a sentinel key value never appears in captured logs or in `os.environ`.
- **State lives in:** git. The PR contains no key values.
- **If it fails:** CI or review fails, so the PR is not merged. Nothing is deployed.

### 6. Staging deploy and failure drills

- **Starts when:** the PR is approved and the step 4 staging and dev secrets exist.
- **What moves where:** deploy to staging. If the pipeline can deploy a PR-branch image, use that. Otherwise merge, relying on the fact that prod secrets already exist (step 4) and that rollouts halt on a non-ready pod. Hold the prod deploy until this step passes. If merge auto-deploys prod, accept that the readiness gate in step 15 and the still-valid old keys are the safety net. Drills in staging:
  - Store unreachable at startup. The pod retries and exits non-zero, and the rollout halts.
  - A new version written to `staging/*` is adopted by every pod within 5 minutes, with no restart.
  - Block the store during a refresh. A warning is logged and traffic is still served with the last good value.
  - Revoke a sandbox key mid-run. The 401 path (step 16) re-reads and retries once.
  - Check logs and `os.environ` for key values.
- **State lives in:** staging pods' memory and the staging store.
- **If it fails:** fix, rebuild and redeploy staging. Prod is untouched.

### 7. Prod rolling deploy

- **Starts when:** step 6 has passed and the security on-call is available.
- **What moves where:**
  - The deploy runs one pod at a time with `maxUnavailable: 0`.
  - Each new pod fetches the three prod secrets as `orders-api-prod`, reports ready, and only then is an old pod stopped.
  - New pods use the new keys. Old pods keep using the old keys from their image. Both are valid.
  - **Pause after the first new pod.** Confirm that real traffic to payments, email and geocoding succeeds from it before continuing. A short soak is enough, and the length is the team's choice.
- **State lives in:** each pod's memory. The store holds the versions.
- **If it fails:**
  - A new pod that cannot read the store exits, never becomes ready, and the rollout halts with the old pods still serving. No customer impact.
  - Fix the access problem and resume.
  - A rollback to the earlier image is still safe at this point because the old keys are not revoked.

### 8. Confirm every instance is on the new keys (gate before revocation)

- **Starts when:** the rollout is complete.
- **What moves where:** nothing moves. Check all of the following and record them in the ticket:
  1. Every orders-api pod in every environment runs the new image digest. No old-image pod, job or script is left.
  2. For each live pod, the latest `secrets_refreshed` log line (step 17) shows the expected version ids from step 4 for all three secrets. Compare against the current pod list, so a silent pod is caught.
  3. Each provider shows the old key's last-used time older than at least one full refresh interval plus a margin, with no unknown callers.
- **State lives in:** central logs, the cluster pod list and provider usage data.
- **If it fails:** do not revoke anything. Find the pod or caller still using an old key and migrate or stop it. Repeat the check.

### 9. Block rollback to pre-migration images

- **Starts when:** step 8 has passed, immediately before step 10.
- **What moves where:** mark every image built before the migration image as non-deployable in the deploy pipeline (deny list or minimum build), and remove them from the registry. Rollback means redeploying an earlier image. A pre-migration image carries the old keys, which step 10 revokes, so it would fail every provider call. Rolling back to the migration image or later is still fine, because those read from the store.
- **State lives in:** deploy pipeline config.
- **If it fails:** do not proceed to step 10. Revocation without this guard leaves a rollback that breaks customer requests.

### 10. Revoke old keys, one provider at a time

- **Starts when:** steps 8 and 9 are done, with the sign-off of the security on-call and one engineer.
- **What moves where:** revoke in order of blast radius: geocoding, then email, then payments.
  - If the provider supports suspending a key before deleting it, suspend first and watch error rates for one refresh interval. Then delete.
  - Do the next provider only when the previous one is clean.
- **State lives in:** the provider accounts.
- **If it fails:** errors after suspension mean a caller was missed. Re-enable the key at once if the provider allows, find the caller, and repeat step 8 for it. Deletion is not reversible, so do not delete until the suspension period is clean.

### 11. Prove the CI guard

- **Starts when:** the PR from step 5 has merged.
- **What moves where:** open a throwaway PR that re-adds an `api_key` line to `config/app.yaml`. Confirm that the check fails and that branch protection blocks the merge. Close the PR without merging.
- **State lives in:** CI and branch protection settings.
- **If it fails:** fix the check or the branch protection. The guard is not on the customer path, so this can be done after the traffic-critical steps.

### 12. Close out

- **Starts when:** steps 10 and 11 are done.
- **What moves where:**
  - Search the 30-day central logs for the key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) to confirm no key shape was logged. If any appears, rotate that key via "Later rotations" and ask the log service to purge it.
  - The old keys stay in git history. They are revoked, so they are harmless.
  - Write a short runbook covering the store layout, the rotation procedure and the confirmation check.
  - Hand the open question about rotation cadence to security.
- **State lives in:** the repo docs and the ticket.
- **If it fails:** a leftover problem is logged as a follow-up ticket, and the migration is not marked complete.

---

## Part 2: How the app reads keys at runtime

### 13. Process start

- **Starts when:** the container starts.
- **What moves where:** the loader reads `config/app.yaml` for non-secret settings only (`base_url`, timeouts, `from_address`, port, log level). `APP_ENV` (prod, staging or dev) selects the store path prefix. It is a name, not a secret. The identity comes from the platform, with no static credential in env or on disk.
- **State lives in:** nothing secret exists yet.
- **If it fails:** a missing `APP_ENV`, or an `api_key` found in the YAML, makes the process exit non-zero before it listens.

### 14. Initial load with retry

- **Starts when:** step 13 is done. The HTTP server is not started until this succeeds, so no customer request can arrive before the keys are loaded.
- **What moves where:** fetch `orders-api/$APP_ENV/payments_api_key`, `email_api_key` and `geocoding_api_key` from the store, getting the value and version id for each. Use a per-call timeout of about 3 seconds, a choice that can be tuned. If any fetch fails, wait 2 seconds and retry only the missing ones, up to 3 retries. That is at most 4 attempts and about 6 seconds of waiting.
- **State lives in:** process memory only.
- **If it fails:** after the last retry, log an error naming the secrets and the error class, never values. Then exit with a non-zero code.
  - In a rollout, that pod never becomes ready, so the rollout halts and the old pods keep serving.
  - Outside a rollout, the orchestrator restarts the container and the loop repeats. The other replicas keep serving.
  - Residual risk: if the store is down while several pods restart at once, capacity drops. Store availability is the control for this.

### 15. Publish the snapshot and report ready

- **Starts when:** all three keys are loaded.
- **What moves where:** the keys go into an immutable in-memory snapshot, `{name: (Secret(value), version_id)}`, replaced by a single atomic reference swap. The log gets one line per secret with the name and version id only. The refresher thread starts. Then the HTTP server starts. `/healthz` returns 200 `{"status":"ok"}` only while the snapshot has all three keys. The server-start ordering and the check together guard against a future reorder. `/healthz` does not turn unhealthy when a refresh fails later (step 17), so a store outage does not pull every pod out of service. Core dumps are disabled in the container.
- **State lives in:** process heap only. Never on disk, in env vars or in logs.
- **If it fails:** if the refresher thread cannot start, exit non-zero before the server starts.

### 16. Per-request key use

- **Starts when:** any outbound call to a provider.
- **What moves where:** the three clients (`PaymentsClient`, `EmailClient`, `GeocodingClient`) no longer copy the key at construction. At import they hold only a reference to the secrets provider, which is safe because that reference carries no value. Each call reads the current key:

  ```python
  def charge(self, order):
      key = self._secrets.get('payments_api_key')   # current snapshot, per call
      return http.post(self._base + '/charges',
                       headers={'Authorization': 'Bearer ' + key.reveal()},
                       json=order.to_charge())
  ```

  A request already in flight keeps the value it read. On a 401 or 403 from the provider:
  1. Force an immediate re-read of that one secret from the store (3 second timeout, at most once per 30 seconds per secret).
  2. If the version changed, retry the request once with the new value.
  3. Otherwise return the error and log a warning.

  A 401 means the provider rejected the request before processing it, so a retry cannot double-charge. This handles an instance that lags behind a rotation.
- **State lives in:** the snapshot in memory.
- **If it fails:** if the store is unreachable during the forced re-read, the request returns the provider error and the cached value stays in use.

### 17. Periodic refresh

- **Starts when:** every 5 minutes after the initial load, on a timer in the refresher thread.
- **What moves where:** fetch the latest version of each secret. For each secret:
  - A new version id replaces the value in a new snapshot, which is then swapped in atomically. Log `secret_rotated name old_version new_version`.
  - An unchanged version id does nothing.
  - An empty or malformed value is treated as a failure.
  - After every cycle, log one `secrets_refreshed` line with the version id of each secret now in use. This line is the evidence step 8 reads.
- **State lives in:** process memory. The store holds the history of versions.
- **If it fails:**
  - On any fetch error, keep the previous value for that secret and log a WARNING containing the secret name, error class, version id still in use and time since the last good load. Never log values or response bodies.
  - Readiness stays 200.
  - Alert on-call if no cycle has succeeded for several cycles in a row. The threshold is for on-call to set.

### 18. Instance stop or restart

- **Starts when:** SIGTERM, a crash, or a reschedule.
- **What moves where:** nothing is persisted. The process memory is discarded. A new process repeats steps 13 to 15.
- **State lives in:** nothing is left behind.
- **If it fails:** see the restart note in step 14.

### 19. Local development

- **Starts when:** an engineer runs `make run`.
- **What moves where:**
  - `APP_ENV` defaults to `dev`.
  - The app reads `orders-api/dev/*` from the store using the engineer's own login.
  - Those paths hold provider sandbox keys, so the live keys are never used locally.
  - Engineers have no access to `orders-api/prod/*`, and the store denies it. The loader also refuses `APP_ENV=prod` unless it is running under the prod identity.
  - Add `make run-offline` (`SECRETS_BACKEND=fake`). It uses an in-process fake backend with placeholder values and points the provider `base_url`s at local stubs. Tests use the same fake backend, so no real key exists anywhere in the test run.
- **State lives in:** process memory, same as in prod.
- **If it fails:** an engineer without dev access, or a provider with no sandbox, hits the step 14 failure path. They use `make run-offline` instead.

---

## Later rotations

Any later rotation, scheduled or emergency, repeats the same loop:

1. Step 3: issue and validate a new key at the provider.
2. Step 4: write it to the store as a new version.
3. Wait for adoption. Instances pick it up within 5 minutes with no restart (step 17).
4. Step 8: confirm every instance shows the new version id.
5. Step 10: revoke the old key.

The old key must never be revoked before step 8 passes. Whether this loop runs on a schedule is the open question above.

## Why no customer request fails

| Moment | Why it is safe |
|---|---|
| New keys issued, old still active (3, 4) | Both keys are valid, and nothing reads the new ones yet |
| Mixed rolling deploy (7) | Old pods use old keys and new pods use new keys. Both are valid |
| New pod cannot load keys (14) | It never becomes ready, so the rollout halts and old pods keep serving |
| Store outage during runtime (17) | Pods keep the last good value and stay ready |
| Rollback during rollout (7) | Old keys are not revoked yet |
| Revocation (10) | Only after step 8 confirms no instance or caller uses the old key, and step 9 blocks rollback to pre-migration images |
