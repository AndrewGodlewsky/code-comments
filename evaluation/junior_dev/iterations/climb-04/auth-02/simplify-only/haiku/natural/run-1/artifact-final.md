# Move orders-api third-party keys into the managed secret store

## Summary

Today `orders-api` reads three live API keys (payments, email, geocoding) from `config/app.yaml`. That file is committed to git and copied into every container image. The app reads the keys once at import and copies them into each provider client.

After this change, the keys live in the managed secret store under `orders-api/<env>/<name>`. The app loads them into memory at startup and refreshes them every 5 minutes. If a refresh fails, it keeps the last good value. Each key is rotated at its provider first. During the rollout, old and new keys are both valid. Old keys are revoked last, only after every running instance is on the new key, so no customer request fails.

## Access model

| Principal | Store access | Notes |
|---|---|---|
| `orders-api-prod` (pods) | read on `orders-api/prod/*` only | No other paths, no write. |
| Security on-call role | write on `orders-api/prod/*` | The only principal that writes prod values. |
| Engineers | no read on `orders-api/prod/*` | Confirm with a policy simulation that no broader role grants read. |
| Developers | read on `orders-api/dev/*` | Dev holds sandbox provider keys only. |

Run an IAM policy simulation for each principal before step 3.

## Terms

- **Secret store**: the managed service that holds encrypted secret values. Each write gets a new version id.
- **Version id**: the store's id for one written value. Logs may show version ids.
- **Secret cache**: the in-memory holder of the three keys in the app. Each entry has a value and a version id.
- **Workload identity**: the platform identity that pods use to read the store. No credential file is on disk.
- **Revoke**: disable an old key at its provider so it stops working. This cannot be undone.
- **Grace period**: a short wait before revoking, so requests that started with an old key can finish.

## How the app reads keys at runtime

1. **Config split.** `config/app.yaml` keeps only non-secret settings: `base_url`, timeouts, `from_address`, `port`, `log_level`. The `api_key` fields are removed. The new code never reads them, so the removal ships in the same change as the new code (rollout step 4).
2. **Secret cache.** Holds three entries, one per key: `value` and `version_id`. A lock guards them. A swap replaces both fields at once, so a reader sees either the old pair or the new pair.
3. **Startup.** Before the HTTP listener starts, the app loads all three secrets in one attempt. If any read fails or returns an empty value, the whole load fails. The app then retries, up to 3 retries 2 seconds apart. That is one attempt plus 3 retries, about 6 seconds of waiting. If every attempt fails, the app logs the error without any value and exits with a non-zero code.
4. **Health checks.** `/healthz` (readiness) returns 200 only after the startup load succeeds. It stays 200 after a later refresh failure, because the app keeps serving on the last good value. A separate liveness endpoint does not check the store, so a store outage cannot kill running pods.
5. **Refresh.** A background task runs every 300 seconds. For each secret, it reads the current version. If the version id changed and the value is non-empty, it swaps the entry and logs the new version id. On any failure (network, auth, empty value), it keeps the last good entry and logs a WARN with the secret name, the kept version id and the error class.
6. **Clients.** `PaymentsClient`, `EmailClient` and `GeocodingClient` stop copying the key in their constructors. Each request reads the current value from the cache and builds the `Authorization` header then. The module-level singletons stay.
7. **Memory only.** Values never go to disk, into environment variables or into logs. Redact the `Authorization` header in HTTP client debug logs and in exception messages and reprs. A test runs a request with debug logging on and asserts that no key value appears in the captured output.
8. **Confirmation signal.** Each instance exposes the loaded `version_id` of each secret on an internal endpoint or metric. It never exposes values. The revocation gate in step 7 reads this signal.

## Rollout steps

Each step lists what starts it, what it does, where its state lives and what happens if it fails.

**Step 1. Verify overlapping keys.**
- Starts: before any other step.
- Does: confirm from provider docs or a provider test account that each provider accepts the old and new key at the same time. Nothing moves.
- State: none.
- If it fails: stop the migration for that provider and escalate. A one-key cutover would break customers.

**Step 2. Create new keys at each provider.**
- Starts: step 1 passes.
- Does: the security on-call creates three new keys in the provider consoles. Engineers never see the values. Old keys stay active.
- State: at the providers.
- If it fails: nothing changes for customers. Retry. The old keys still work.

**Step 3. Write new values to the store.**
- Starts: step 2.
- Does: the security on-call writes `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key` and `orders-api/prod/geocoding_api_key`. Dev owners write the sandbox keys to `orders-api/dev/*`. The store encrypts each value with the per-environment KMS key and returns a version id.
- State: in the store, versioned. Record the version ids in the change ticket. Never record values.
- If it fails: no running code reads these values yet, so customers see nothing. Retry the write. If a value is wrong, write a new version. Old pods are unaffected.

**Step 4. Merge the code change.**
- Starts: merge to `main`. The change includes the runtime design, the config change that removes `api_key`, the redaction and the CI guard.
- Does: CI builds one image. The image contains the new config with no keys.
- State: git and the container registry.
- If it fails: a failing test blocks the merge. Nothing is deployed.

**Step 5. CI guard against reintroducing keys.**
- Starts: every pull request.
- Does: fails any change where `config/app.yaml` contains an `api_key` key. Recommended: also scan the whole repo for live-key prefixes (`pk_live_`, `ml_live_`, `geo_live_`).
- Test: a test branch that adds `api_key` back to the config must fail CI.
- State: CI configuration.
- If it fails: a false positive blocks a merge. Fix the file or the pattern, not the guard.

**Step 6. Deploy to dev, then prod.**
- Starts: the step 4 image is built. Dev deploys first, then prod.
- Does: a rolling deploy with `maxUnavailable: 0`. Each new pod loads the three secrets at startup (runtime step 3) and becomes ready only after all three load. Old pods keep their old in-memory keys and keep serving.
- State: in memory on each pod. The fleet is mixed for a while. Both key sets are valid because of step 1.
- If it fails:
  - Store unreachable, IAM misconfigured, or an empty value: the new pod retries, then exits non-zero. The rollout halts and old pods keep serving.
  - A pod that restarts during a store outage cannot start. Capacity drops. This is accepted for now (see open question 3).

**Step 7. Confirm every pod is on the new key.**
- Starts: the rollout completes.
- Does: nothing moves. Check three things:
  - No pod runs a pre-migration image.
  - Every pod reports the new `version_id` for all three secrets.
  - Error rates for payments, email and geocoding are at baseline, with no spike in 401 or 403 responses from the providers.
- State: none.
- If it fails: a pod still on an old version is blocked. Check its refresh logs. Do not revoke while any pod is unconfirmed.

**Step 8. Grace period.**
- Starts: step 7 passes.
- Does: wait at least 60 seconds, so requests that began with an old key can finish. The payments timeout is 10 seconds. The 60-second value is the author's choice, not from the brief.
- State: none.
- If it fails: if error rates rise during the wait, stop and investigate. Do not revoke.

**Step 9. Revoke old keys at the providers.**
- Starts: step 8 passes, the deployment is accepted and the rollback decision is made (see the failure table).
- Does: the security on-call revokes the old key at each provider, one provider at a time. Watch 401 rates after each revocation.
- State: at the providers. Revocation cannot be undone.
- If it fails: a 401 spike means move forward, not back. Fix the new key or its store version. Old keys cannot be restored.

**Step 10. Retire old store versions.**
- Starts: step 9 passes.
- Does: disable or destroy the old store versions, so no read returns a dead key.
- State: in the store.
- If it fails: nothing customer-facing. Retry.

**Step 11. Close out.**
- Starts: step 10.
- Does: record the version ids and revocation times in the change ticket. Confirm the step 5 CI guard is active on `main`. Do not rewrite git history.
- State: the change ticket and `main`.
- If it fails: nothing customer-facing. Finish the record before closing the ticket. Old values remain in git history and may stay in central logs for up to 30 days. This is acceptable because the keys are revoked.

## Failures and rollback

| When | What happens | Response |
|---|---|---|
| A provider accepts only one active key (step 1) | A cutover would break customers. | Stop that provider's migration and escalate. |
| Store unreachable, IAM misconfigured or empty value at pod start | The new pod exits non-zero. | The rollout halts. Old pods keep serving. |
| Store unreachable during a refresh | The app keeps the last good value and logs a WARN. | None needed now. The next refresh retries in 5 minutes. |
| Pod restart or scale-out during a store outage | The new pod cannot start. | Capacity risk (open question 3). |
| Error rates rise during the grace period | Possible key or rollout problem. | Stop and investigate. Do not revoke. |
| 401 spike after a revocation | New key or new version is failing. | Move forward. Fix the new key or its store version. |
| Rollback before step 9 | Old keys are still valid. | Rollback to a pre-migration image is safe. |
| Rollback after step 9 | Pre-migration images use revoked keys and would fail customer requests. | Roll back only to post-migration images. Block pre-migration images in the registry or deploy policy. |

## Local development

1. Dev owners create sandbox keys at each provider and write them to `orders-api/dev/*` (step 3).
2. `make run` uses the same loader, pointed at `orders-api/dev/*`, through the developer's own store session. That identity reads dev only.
3. A non-secret config overlay points dev at the provider sandbox base URLs. The app writes no `.env` file with keys.
4. A developer without dev access gets a clear failure from `make run` and requests access. No developer needs prod access to run locally.

## Open questions

1. **Rotation cadence.** Security has not decided whether keys must rotate on a schedule after this migration, or how often. No cadence is chosen here.
2. **Overlapping keys.** Each provider must be confirmed to accept old and new keys at the same time (step 1). The plan assumes it.
3. **Store outages and capacity.** Startup needs the store, so an outage during a pod restart or scale-out blocks new pods. With four replicas this is a real capacity risk. SRE and security must accept it or define a mitigation.
4. **Staging.** Does a staging environment exist? If so, it follows the dev steps with its own keys.
5. **Sandbox base URLs.** The dev overlay needs the provider sandbox URLs, which the brief does not give.
6. **Log redaction.** Confirm that the central log service does not capture request headers by default. The plan assumes app-side redaction is enough.