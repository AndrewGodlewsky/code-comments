# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

- Today the three live keys sit in `config/app.yaml` and in every image. `app/config_loader.py` reads them once at import. Each provider client copies its key into a module-level singleton at construction. `/healthz` returns 200 as soon as the server is listening.
- The change has two halves:
  1. A rollout that rotates every key and moves the new values into the store.
  2. A runtime change: keys are read from the store into memory only, re-read every 5 minutes, and gate readiness.
- The rollout works without customer errors because the old and new keys are valid at the same time. The old keys are revoked only after every running instance is confirmed on the new ones.
- Rotation cadence is not decided. It is listed under Open questions.

## Assumptions to check before starting

These are facts the brief does not state. Step 1 owns checking them.

- **A1.** Each of the three providers allows two API keys to be valid at the same time. The zero-failure requirement cannot be met without this. If any provider allows only one live key, stop and ask Security for a provider-specific plan. Do not improvise.
- **A2.** The store authenticates `orders-api-prod` through the cluster's workload identity, so no credential is stored anywhere. If a static credential is needed, it is a new secret and must follow the same rules.
- **A3.** Each provider offers sandbox or test keys for development. If one does not, local runs for that provider use the offline fakes in step 14.
- **A4.** The store's audit log can show which identity read which secret. This is how we prove engineers cannot read prod.

## Part A: Rollout

### 1. Prepare the store and access

- **Starts when:** the plan is approved. Done by the platform team, with Security reviewing.
- **What moves:**
  - Nothing sensitive yet.
  - Create the paths `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key` and `orders-api/prod/geocoding_api_key`.
  - Create the matching `orders-api/dev/*` paths.
  - Prod secrets use the prod KMS key. Dev secrets use the dev KMS key.
  - Policies:
    - `orders-api-prod` gets read-only on `orders-api/prod/*`. If the store needs a separate KMS decrypt grant, that grant covers the prod KMS key only.
    - Only the security on-call group gets write on `orders-api/prod/*`.
    - Engineers get no prod access. They get read on `orders-api/dev/*`, and write there only if the team wants it.
  - Run these checks and attach the results to the tracking ticket:
    - An engineer identity is denied reading and writing prod.
    - `orders-api-prod` is denied reading `orders-api/dev/*` and any other path, and is denied all writes.
    - A non-security identity is denied writing prod.
- **State lives in:** the store, its policies and its audit log.
- **If it fails:** nothing in production has changed, so there is no customer impact. Fix the policy and rerun the checks. Do not go on until every negative test is denied. Also confirm A1 and A3 with each provider at this step.

### 2. Create new keys and write them to the store

- **Starts when:** step 1's checks pass. Done by the security on-call, who is the only writer.
- **What moves:**
  - For each provider, the on-call creates a **new** key in the provider console while the old key stays active.
  - The on-call validates the new key with a harmless provider call, then writes it straight into the store as `orders-api/prod/<name>` (version 1).
  - The value is never put in a ticket, chat, shell history, CI variable, environment variable or file.
  - Sandbox keys go into `orders-api/dev/*` the same way.
  - Record the **old key IDs** (not values) and the new version ids. Version ids are safe to share.
- **State lives in:** the store (new keys) and the provider (both old and new keys active). The old keys are still used by all 4 running pods.
- **If it fails:**
  - If the provider rejects the validation call, do not write the key. Create a new one.
  - If the write fails, retry. Nothing depends on it yet.
  - A bad value that did get written is superseded by writing a corrected value, which creates a new version id.
  - Customers are unaffected because the pods still use the old keys.

### 3. Ship the code change as one PR

- **Starts when:** step 2 is complete. The PR is reviewed by someone who is not the author.
- **What moves:** the changes described in Part B.
  - Remove all three `api_key` lines from `config/app.yaml`. Keep `base_url`, timeouts and `from_address`.
  - Add the `SecretProvider`.
  - Change the clients to read the key per request.
  - Gate `/healthz` on the three keys being loaded.
  - Add `config/app.dev.yaml` and the `make run` changes.
  - Add the CI check (step 15).
  - Merging to `main` triggers an image build (`deploy.md`). That image contains no keys.
- **State lives in:** git and the image registry. The old images, which still contain the old keys, remain in the registry. Step 9 deals with them.
- **If it fails:**
  - If tests or the CI check fail, the PR does not merge.
  - Required tests:
    - Startup retry count and spacing, and the non-zero exit.
    - Refresh keeps the last good value on failure.
    - Readiness is false until all three keys are loaded.
    - A log-capture test showing no key value appears in logs, including error paths.
  - Merging to `main` does not by itself change production if deploys are manual. If deploys are automatic, step 5 starts at merge, so step 4 must already be done.

### 4. Preflight in production, before any rollout

- **Starts when:** the image from step 3 exists. Done by the platform team.
- **What moves:**
  - Run a one-off job as `orders-api-prod` that reads the three prod secrets.
  - The job logs only the secret names and version ids. It never logs values.
  - The job exits 0 only if all three reads succeed.
- **State lives in:** the store and the job's logs (version ids only).
- **If it fails:**
  - Fix access or the secret path, then rerun. Nothing is deployed, so there is no customer impact.
  - Do not start step 5 until the job passes.
  - This prevents the most likely failure, which is a missing grant that would leave new pods never becoming ready.

### 5. Rolling deploy with a canary hold

- **Starts when:** step 4 passes. Done by whoever runs deploys.
- **What moves:**
  - Use the normal rolling deploy: one pod at a time, `maxUnavailable: 0`.
  - Each new pod loads its keys from the store before `/healthz` returns 200, so an old pod stops only after a new one is ready.
  - **Pause the rollout after the first new pod is ready.** Check that this pod's calls to each provider succeed with the new key. Use the provider success metric and the version id the pod reports.
  - Then resume the rollout.
  - For a short time the fleet is mixed: old pods use the old keys and new pods use the new keys. Both are valid at the same time, so this is safe.
- **State lives in:** the pods (keys in memory only) and the store.
- **If it fails:**
  - If a new pod cannot reach the store, it exits non-zero after its retries (step 10). It never becomes ready, the rollout halts, and the old pods keep serving.
  - If the canary shows provider errors, roll back by redeploying the previous image. This is safe because the old keys are still valid, so no customer request fails. Then investigate the new key (step 2).
  - Rollback to any pre-migration image is allowed only before step 8.

### 6. Confirm every instance is on the new keys

- **Starts when:** the rollout is complete and no old-image pods remain. Done by the platform team.
- **What moves:**
  - Query each of the 4 pods directly for the version ids it reports for each secret. Version ids are not secret and are exposed as in step 13.
  - Compare them with the version ids from step 2.
  - Check the provider consoles for the last-used time of each old key. Wait at least 10 minutes (two refresh intervals) after the last old pod stopped. Require no use of the old keys.
  - Look for any other consumer of the old keys, such as scripts or developer machines. Developers' `make run` used the live keys, so expect some use from laptops. Laptop use does not affect customers, but any unexplained service-side use blocks step 8.
- **State lives in:** the pods' reported versions, the provider usage data and the ticket.
- **If it fails:**
  - If any pod reports a different version, or an old key is still used by something unidentified, do not revoke. Find the cause first.
  - A pod that cannot show the right version is restarted. It will read the current store value on startup.
  - Confirmation is by reported version id, never by "enough time has passed".

### 7. Cut local development over to dev secrets

- **Starts when:** the PR from step 3 is merged. This can run in parallel with steps 5 and 6.
- **What moves:** engineers pull the new `main` and use the new `make run` (step 14). Local runs now read `orders-api/dev/*` or use offline fakes. They never touch prod secrets.
- **State lives in:** the dev store paths, plus the engineers' own identities.
- **If it fails:** an engineer whose local run breaks can use the offline mode. There is no production impact. The old live keys stop working at step 8, so there is no fallback to them.

### 8. Revoke the old keys

- **Starts when:** step 6 is fully confirmed and the Security on-call approves. This is the point of no return for any pre-migration image.
- **What moves:**
  - Revoke one provider's old key at a time, in the provider console, and watch that provider's error rate for a few minutes before the next.
  - Record the time and key ID in the ticket.
- **State lives in:** the providers.
- **If it fails:**
  - If errors appear after a revoke, find out which instance still uses the old key. It should not exist after step 6, so this is an incident.
  - The fix is to restart that instance, which loads the current store value.
  - Do not re-enable the leaked key. If the provider cannot undelete it, a new key is created and written to the store (the same path as step 2), and instances pick it up within 5 minutes.

### 9. Clean up what still holds old keys

- **Starts when:** step 8 is complete.
- **What moves:**
  - Mark every pre-migration image as do-not-deploy, or delete it from the registry. From now on, "rollback = redeploy an earlier image" is valid only for images built after step 3. A pre-migration image would start with revoked keys and fail every provider call.
  - Update `deploy.md` to say this, and to describe the new startup, readiness and local-run behavior.
  - Git history is not rewritten, so the old keys remain visible there. They are now revoked and harmless.
- **State lives in:** the registry and the docs.
- **If it fails:** if an old image is redeployed by mistake, the pod's calls fail with auth errors. Redeploy a post-migration image. This is why marking the old images matters.

## Part B: Runtime behavior

### 10. Startup: load all three keys before ready

- **Starts when:** the process starts. Read non-secret settings from the yaml first. Then, before the HTTP server accepts requests, call `SecretProvider.start()`.
- **What moves:**
  - Read `orders-api/<env>/payments_api_key`, `email_api_key` and `geocoding_api_key` from the store. `<env>` comes from `APP_ENV`, which is not secret.
  - The values go into one in-memory object, together with their version ids.
  - Allow a bounded timeout per call (an implementation choice).
  - If any read fails, retry. The brief gives 3 retries, 2 seconds apart, so there are up to 4 attempts and about 6 seconds of waiting.
  - If all three are loaded, log the version ids only, then start the server.
- **State lives in:** process memory only. No disk cache, no environment variable, no log. Disable core dumps in the container.
- **If it fails:**
  - After the last retry, log the secret names and the error class, never values, then exit non-zero.
  - Kubernetes restarts the pod. In a rolling deploy, the rollout halts and the old pods keep serving because `maxUnavailable` is 0.
  - There is no fallback to the yaml, because the keys are no longer in it.

### 11. Readiness

- **Starts when:** the kubelet probes `GET /healthz`.
- **What moves:**
  - Return 200 only if all three keys are loaded. Otherwise return 503.
  - The body includes the three version ids, for step 6.
  - After startup, readiness does **not** turn off when a refresh fails. The pod keeps its last good keys and should keep serving.
- **State lives in:** the in-memory key object.
- **If it fails:** a 503 keeps the pod out of rotation and, during a deploy, halts the rollout. The probe never calls the store itself, so a store outage cannot take down healthy pods.

### 12. Using a key on each request

- **Starts when:** a provider client makes a call (`charge`, send email, geocode).
- **What moves:**
  - Clients no longer copy the key in `__init__`. They call `secrets.get("payments_api_key")` each time.
  - `get()` returns the current value from memory and never touches the network.
  - A request that already started keeps the key it read, so a swap never changes a request half way.
  - The singletons built at import are fine, because they now hold no key.
  - If `get()` is called before the keys are loaded, it raises an error. It never returns an empty value.
- **State lives in:** process memory.
- **If it fails:** an unexpected `get()` error is a code bug caught by the tests in step 3.

### 13. Refresh every 5 minutes

- **Starts when:** a timer fires every 5 minutes after startup. Add a small random jitter so the 4 pods do not all read at once.
- **What moves:**
  - Read each secret from the store.
  - If the version id changed, swap the new value into the in-memory object in one step (replace the object reference under a lock). Log the secret name and the old and new version ids.
  - Expose the current version ids on `/healthz` (step 11) and a "seconds since last successful read" metric. The alert threshold is the team's to set.
- **State lives in:** process memory.
- **If it fails:**
  - If a read fails, or returns an empty or malformed value, keep using the last good value and log a **warning**. The warning carries the secret name, the error class and the current version id, never a value.
  - Try again at the next interval. There is no retry loop.
  - Each of the three secrets is handled separately, so one failure does not block the others.
  - A pod that keeps failing keeps working on its old value. That is why revocation in step 8 depends on reported versions.

### 14. Local development

- **Starts when:** an engineer runs `make run`.
- **What moves:**
  - `make run` sets `APP_ENV=dev` and `APP_CONFIG=config/app.dev.yaml`. The dev yaml holds sandbox `base_url`s and no keys.
  - The engineer's own identity reads `orders-api/dev/*`. The prefix is built from `APP_ENV`, so the code has no prod fallback.
  - `make run-offline` uses fake provider stubs with fake keys held in memory. This is allowed only when `APP_ENV=local`, and the app refuses to start in any other environment with the fake source.
  - Prod read access is denied to engineers anyway (step 1), so a mistake would fail rather than leak.
- **State lives in:** the dev store, or process memory for the fakes.
- **If it fails:** if the dev store is unreachable, the same retry-then-exit behavior applies. Use `make run-offline` instead.

### 15. CI guard against keys returning

- **Starts when:** every pull request and every push to `main`. Make the check **required** in branch protection.
- **What moves:**
  - A CI job parses `config/app.yaml`, and any other `config/*.yaml`, as YAML.
  - It fails the build if a key named `api_key` appears at any depth. Compare case-insensitively.
  - It also fails if the file cannot be parsed, so a parse error cannot hide a key.
  - Use a parser instead of a plain text search, so quoting or indentation changes cannot bypass the check.
  - As a second line of defense, `config_loader` refuses to start if it sees an `api_key` in the loaded settings.
- **State lives in:** CI and branch protection.
- **If it fails:** a failing check blocks the merge. The author moves the key to the store and removes it from the yaml.

## Failure summary

| Where | Failure | What happens |
|---|---|---|
| Step 5 / 10 | Store unreachable at startup | Pod exits non-zero after 3 retries. Rollout halts. Old pods keep serving. |
| Step 5 | New key bad at the provider | Caught by the canary hold. Redeploy the previous image while the old keys are still valid. |
| Step 13 | Store unreachable during refresh | Last good value kept. Warning logged. Retry in 5 minutes. |
| Step 8 | An instance still on an old key | Blocked by step 6. If it happens anyway, it is an incident. Restart the instance. |
| Step 9 | Pre-migration image redeployed | Fails on revoked keys. Prevented by marking the images. |

## Open questions

1. **Scheduled rotation: not decided.** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan does not pick a cadence. The runtime refresh and the rotate-then-confirm-then-revoke procedure (steps 2, 6 and 8) work for any cadence, so nothing here needs to change when a decision is made. The decision depends on the providers (A1).
2. **A1:** does each provider allow two live keys at once? This must be answered before step 2.
3. **A3:** do all three providers offer sandbox keys? If not, which should run on fakes locally?
4. **Alerting:** what threshold should alert on "seconds since last successful read"?
5. **Automatic deploys:** if merging to `main` auto-deploys, step 4 and step 2 must be finished before the merge in step 3.
