# Move orders-api third-party keys into the managed secret store

## Summary

The payments, email, and geocoding keys leave `config/app.yaml` and move to the managed secret store under `orders-api/<env>/<name>`. Each key is rotated at its provider before the new value is stored. The app reads keys into process memory at startup, refreshes them every 5 minutes, and keeps the last good value when a refresh fails. Old keys are revoked last, only after every running instance is confirmed on the new key. Throughout, both old and new keys are valid, so no customer request should fail.

## Interpretations and assumptions

- **Retry count.** "Retry 3 times, 2 seconds apart" is read as one initial attempt plus 3 retries, so up to 4 attempts with about 6 seconds of waiting before a non-zero exit.
- **Overlapping keys.** Each provider must accept the old and new key at the same time. Step 1 verifies this. If a provider cannot do it, the rollout cannot meet the no-failure requirement for that provider and must stop.
- **Pod identity.** Pods reach the store with the platform workload identity for `orders-api-prod`. No static credential file exists on disk.
- **Environments.** `dev` and `prod` are named. If a staging environment exists, it follows the `dev` pattern with its own keys.

## Access model

| Principal | Store access | Notes |
|---|---|---|
| `orders-api-prod` (pods) | read on `orders-api/prod/*` only | No other paths, no write. |
| Security on-call role | write on `orders-api/prod/*` | The only principal that writes prod values. |
| Engineers | no read on `orders-api/prod/*` | Confirm with a policy simulation that no broader role grants read. |
| Developers | read on `orders-api/dev/*` | Dev holds sandbox provider keys only. |

Verify the access model with an IAM policy simulation for each principal before step 3.

## Runtime design: how the app reads keys

1. **Config split.** `config/app.yaml` keeps only non-secret settings (`base_url`, timeouts, `from_address`, `port`, `log_level`). The `api_key` fields are removed. Because the new code never reads them, the removal can ship in the same change as the new code (step 4).
2. **Secret cache.** A new module holds three entries, one per secret: `value`, `version_id`, and `loaded_at`. A lock protects the entries. Values are swapped atomically, so a reader sees either the old pair or the new pair.
3. **Startup.** Before the HTTP listener starts, the app loads all three secrets in one attempt. Any failure retries the whole load, with 3 retries 2 seconds apart. If every attempt fails, the process logs the error without any value and exits non-zero.
4. **Readiness and liveness.** `/healthz` returns 200 only after the initial load has succeeded. Liveness is a separate endpoint that does not check the store, so a store outage cannot kill running pods. Readiness stays green after a refresh failure, because the app keeps serving on the last good value.
5. **Refresh.** A background task runs every 300 seconds. For each secret it reads the current version. If the version id changed and the value is non-empty, it swaps the entry and logs the new version id. On any failure (network, auth, empty value), it keeps the last good entry and logs a WARN with the secret name, the retained version id, and the error class. It never logs the value.
6. **Clients.** Remove the `self._key` copy in `PaymentsClient`, `EmailClient`, and `GeocodingClient`. Each request calls the cache for the current value and builds the `Authorization` header then. The module-level singletons can stay.
7. **Memory only.** Values never go to disk, environment variables, or logs. Also redact the `Authorization` header in HTTP client debug logging and in exception messages or reprs. Add a test that runs a request with debug logging on and asserts that no key value appears in the captured output.
8. **Confirmation signal.** Each instance exposes the loaded `version_id` for each secret on an internal endpoint or metric. Values are never exposed. The revocation gate in step 7 reads this signal.
9. **Local development.** `make run` uses the same loader, pointed at `orders-api/dev/*`, with the developer's own store session. Dev base URLs point to provider sandboxes through a non-secret, env-specific config overlay. The app writes no `.env` file with keys.

## Rollout steps

**Step 1. Verify overlapping keys.**
- Starts: before any other step.
- Moves: nothing.
- State: provider documentation or a provider test account.
- Failure: if a provider accepts only one active key, stop the migration for that provider and escalate. A one-key cutover would break customers.

**Step 2. Create new keys at each provider.**
- Starts: step 1 passes. The security on-call performs this in each provider console, so engineers never see the values.
- Moves: three new keys are created at the providers. Old keys stay active.
- State: at the providers.
- Failure: nothing changes for customers. Retry the creation. The old keys still work.

**Step 3. Write new values to the store.**
- Starts: step 2. The security on-call writes `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, and `orders-api/prod/geocoding_api_key`. Dev owners write the sandbox keys to `orders-api/dev/*`.
- Moves: values go into the store, which encrypts them with the per-environment KMS key and returns a version id for each write.
- State: store, versioned. Record the version ids in the change ticket. Do not record values.
- Failure: no running code reads these values yet, so nothing customer-facing changes. Retry the write. If a value is written wrongly, write a new version. Old pods are unaffected.

**Step 4. Merge the code change.**
- Starts: merge to `main`. This includes the runtime design above, the `config/app.yaml` change that removes `api_key`, the redaction, and the CI check.
- Moves: CI builds one image. The image contains the new config with no keys.
- State: git and the container registry.
- Failure: a failing test blocks the merge. Nothing is deployed yet.

**Step 5. CI guard against reintroducing keys.**
- Starts: runs on every PR as part of step 4.
- Moves: nothing.
- Behavior: fail any change where `config/app.yaml` contains an `api_key` key. Also scan the whole repo for live-key prefixes (`pk_live_`, `ml_live_`, `geo_live_`) as a recommended addition. Confirm the guard fails on a test branch that adds `api_key` back to the config.
- Failure: a false positive blocks a merge. Fix the file or the pattern, not the guard.

**Step 6. Deploy to dev, then prod.**
- Starts: step 4 image is built. Deploy to dev first, then prod.
- Moves: rolling deploy with `maxUnavailable: 0`. Each new pod starts, loads the three secrets from the store, and becomes ready only after all three are loaded. Old pods keep their in-memory old keys and keep serving.
- State: in memory on each pod. The fleet is mixed for a time, with old pods on old keys and new pods on new keys. Both sets are valid because of step 1.
- Failure cases:
  - Store unreachable: the new pod retries, then exits non-zero. The rollout halts, and the old pods keep serving.
  - IAM misconfigured: same halt, same result.
  - Store returns an empty value: treated as a failed load, so the same halt.
  - Pod restart after a store outage: the pod cannot start, which reduces capacity. This is an accepted consequence of the startup rule (see open questions).

**Step 7. Confirm every pod is on the new key.**
- Starts: rollout completes.
- Moves: nothing.
- Check: no pod runs a pre-migration image. Every pod reports the new `version_id` for all three secrets. Error rates for payments, email, and geocoding are at baseline, with no spike in 401 or 403 responses from the providers.
- Failure: a pod still on an old version is blocked. Investigate its refresh logs. Do not proceed to revocation while any pod is unconfirmed.

**Step 8. Grace period.**
- Starts: step 7 passes.
- Moves: nothing.
- Purpose: let requests that began with an old key finish. The payments client timeout is 10 seconds, so wait at least 60 seconds. This is the author's choice, not from the brief.
- Failure: if error rates rise during the grace period, stop and investigate. Do not revoke.

**Step 9. Revoke old keys at the providers.**
- Starts: step 8 passes and the deployment is accepted. Do this only after the rollback decision is made (see the rollback section).
- Moves: the security on-call revokes the old key at each provider, one provider at a time, watching 401 rates after each revocation.
- State: at the providers. Revocation is effectively irreversible.
- Failure: if 401 rates spike, the response is forward, not back. Fix the new key or its store version. Old keys cannot be restored.

**Step 10. Retire old store versions.**
- Starts: step 9 passes.
- Moves: the old store versions are disabled or destroyed, so no read returns a dead key. This is cleanup, not a customer-facing step.
- Failure: harmless. Retry.

**Step 11. Close out.**
- Starts: step 10.
- Moves: record the version ids and the revocation times in the change ticket. Confirm the CI guard from step 5 is active on `main`.
- Note: the old values remain in git history and may remain in central logs for up to 30 days. Both are acceptable because the keys are revoked. Do not rewrite history.

## Rollback

- **Before step 9:** rollback to a pre-migration image is safe. Its keys are still valid.
- **After step 9:** pre-migration images are dead. Their keys are revoked, so a rollback to them would fail customer requests. Rollback targets must be post-migration images. Block pre-migration images from deployment in the registry or deploy policy.
- **Rollout halt:** a new pod that cannot load keys halts the rollout. This is the same as rollback: old pods keep serving.

## Local development

1. Create sandbox keys at each provider. Write them to `orders-api/dev/*` (step 3).
2. Change `make run` to use the dev store through the developer's own session. The developer's identity reads dev only.
3. Point the dev overlay at sandbox base URLs.
4. A developer without dev access sees a clear failure from `make run` and requests access. No developer needs prod access to run locally.

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must rotate on a schedule after this migration, or how often. No cadence is chosen here. This is an open question for security.
2. **Overlapping keys.** Each provider must be confirmed to accept old and new keys at the same time (step 1). The plan assumes it.
3. **Store outages and capacity.** Because startup needs the store, a store outage during a pod restart or scale-out blocks new pods. Four replicas make this a real capacity risk. Confirm with SRE and security that this is acceptable, or define a mitigation.
4. **Staging.** Does a staging environment exist? If so, it needs the same steps as dev.
5. **Sandbox base URLs.** The dev overlay needs the provider sandbox URLs, which are not in the brief.
6. **Log redaction.** Confirm that the central log service does not capture request headers by default. This plan assumes redaction in the app is sufficient.