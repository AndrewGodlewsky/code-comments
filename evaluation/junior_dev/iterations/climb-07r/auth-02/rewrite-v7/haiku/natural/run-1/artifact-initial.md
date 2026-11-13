# Migration plan: orders-api third-party API keys into the managed secret store

## Scope and assumptions

- Three live keys move out of `config/app.yaml`: payments, email, geocoding. Each gets a new key at its provider and a new value in the store.
- The store is assumed to hold each secret as a named item with immutable versions and a way to read the latest version. Each write returns a version id.
- Prod runs 4 replicas under `orders-api-prod`. Rollouts are rolling with `maxUnavailable: 0`. Readiness is `GET /healthz`.
- "Retry 3 times, 2 seconds apart" is read as 1 initial attempt plus 3 retries, so at most about 6 seconds of waiting before exit. This needs confirmation (see Open questions).
- The store encrypts with a per-environment KMS key. The service identity needs decrypt permission on the prod key as well as read on `orders-api/prod/*`.
- Old keys are treated as leaked. Git history is not rewritten. Old container images that embed the keys are treated as sensitive.
- No rotation cadence is chosen here. See Open questions.

## Part A: How the app reads keys at runtime

Each step gives the trigger, what moves where, where the state lives, and what happens on failure.

**R1. Startup load (before ready).**
- Trigger: process start.
- Moves: the app reads `orders-api/<env>/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key` from the store, using the workload identity of the environment. `<env>` comes from a non-secret setting such as `APP_ENV`, which defaults to `dev`.
- State: an in-memory map of name to (value, version id, loaded-at). Nothing is written to disk, to environment variables or to logs. Only version ids are logged.
- Retries: 1 attempt plus 3 retries, 2 seconds apart. All three secrets must load. If any still fails after the last retry, the app logs the error class and secret name (never the value) and exits non-zero.
- Guard: if `APP_ENV=prod` and the identity is not the prod workload identity, the app refuses to start.
- On failure: the pod never becomes ready. During a rollout, `maxUnavailable: 0` keeps the old pods serving, and the rollout halts.

**R2. Readiness gate.**
- Trigger: HTTP server start.
- Moves: the server may listen early, but `/healthz` returns 503 until R1 succeeds, then 200 with `{"status": "ok"}`.
- State: the in-memory "keys loaded" flag.
- On failure: no traffic reaches the pod. Readiness does not depend on the store after startup. If it did, a store outage would make every pod unready and drop customer traffic.
- Liveness: if the liveness probe also uses `/healthz`, give it its own endpoint (for example `/livez`) that does not depend on the store. Otherwise a store outage could restart pods.

**R3. Client access pattern.**
- Trigger: each provider call.
- Moves: the clients (`PaymentsClient`, `EmailClient`, `GeocodingClient`) stop copying the key in `__init__`. Each request reads the current value through a secret accessor.
- State: the current value sits behind a single atomic reference, so a request sees either the old or the new value, never a mix.
- On failure: not applicable. The accessor only returns values already loaded.

**R4. Periodic refresh (every 5 minutes).**
- Trigger: a background timer. A small jitter avoids all replicas reading at the same moment.
- Moves: for each secret, the app reads the latest version. If the version id has changed, it validates that the value is non-empty and well-formed, then swaps the atomic reference and logs `rotated <name> version=<id>`.
- State: in memory. Each secret is handled independently, so one failure does not block the others.
- On failure: the app keeps the last good value for that secret and logs a warning with the error class. It tries again on the next tick. The app does not exit and does not fail readiness.

**R5. Bad new key.**
- Trigger: the provider rejects a request with 401 or 403 after a refresh has swapped in a new value.
- Moves: the client logs the secret name and version id, and the request fails as it would today.
- Mitigation: the rotation steps (P2 and P6) validate each new key before it is written and before any old key is revoked. Keeping the previous version as a one-cycle fallback on 401 during the migration is an option for the team to decide (see Open questions).

**R6. Logging and redaction.**
- Values are wrapped in a `SecretValue` type whose `repr` and `str` print `***`.
- Exception handlers and HTTP client debug logging must not print request headers. The `Authorization` header is the most likely leak path.
- An integration test runs the app against a fake store and provider with known key values, then fails if those values appear in stdout, stderr or the log output.

**R7. Shutdown.**
- Nothing is persisted. Values are dropped from memory on exit, on a best-effort basis.

## Part B: Rollout

**P1. Create the store layout and access rules.**
- Trigger: the migration issue is approved.
- Moves: create `orders-api/dev/*` and `orders-api/prod/*`, each with its KMS key.
- Access rules: `orders-api-prod` gets read on `orders-api/prod/*` and decrypt on the prod KMS key only. Security on-call gets write on `orders-api/prod/*`. Engineers get no prod read or write. Engineers get read and write on `orders-api/dev/*`.
- State: store policy and KMS key policy, under version control in the infrastructure repo.
- On failure: if the prod identity cannot read, R1 fails at startup and the rollout halts before any customer impact. If engineers can read prod, stop and fix the policy before continuing.

**P2. Issue new keys at each provider, validate, and store them.**
- Trigger: P1 is complete and verified.
- Moves: security on-call creates a new key at each provider. The old keys stay valid. Security checks each new key with a read-only provider call made outside the app, then writes it to `orders-api/prod/<name>`. The store returns a version id, which is recorded in the migration log.
- State: each provider holds two valid keys. The store holds the new values. Running pods still use the old keys from their images.
- On failure: if a provider will not issue a second key, or the validation call fails, do not write to the store. Re-plan. Do not revoke anything. Engineers never see the key values.

**P3. Move local development off live keys.**
- Trigger: can run in parallel with P2.
- Moves: create sandbox or test keys at each provider and store them under `orders-api/dev/*`. Change `make run` to set `APP_ENV=dev` and load these keys through the developer's own identity. Remove the live keys from any local copy of the config.
- State: dev keys live in the dev store only, in memory during a run.
- On failure: if a provider has no sandbox, the developer can use a local stub for the provider. Do not put prod keys on laptops, and do not put dev keys on disk.

**P4. Ship the code change and clean the config, in one merge.**
- Trigger: P2 is complete and P3 is merged.
- Moves: merge the R1 to R7 code. Remove every `api_key` line from `config/app.yaml`, keeping only non-secret settings. Add the CI gate (below). CI builds one image.
- CI gate: a required check on `main` that fails any change which adds an `api_key` key to `config/app.yaml`, and also fails on common secret patterns in the file. The check also runs on the built image's copy of the config.
- State: the image contains no keys in its config. It reads keys from the store at runtime.
- On failure: a failing CI check means no image is built. Nothing reaches production.

**P5. Roll out the new image.**
- Trigger: the image from P4 is available.
- Moves: the rolling deploy replaces pods one at a time. Each new pod runs R1 and passes R2 before an old pod is stopped.
- State: each new pod logs the version id of each of the three keys. Old pods still hold the old keys.
- On failure: a new pod that cannot read the store retries, exits and never becomes ready. The rollout halts and the old pods keep serving. Fix the cause and redeploy. Customers are not affected, because the old keys are still valid.

**P6. Confirm every instance uses the new keys.**
- Trigger: all 4 replicas run the new image.
- Gate: every running pod (including any leftover pods from the old ReplicaSet) logs the new version id for all three keys. The central log service (30-day retention) is queried for these log lines. A full 5-minute refresh cycle passes after the last store write. Where the provider offers per-key usage data, it shows no requests with the old keys.
- State: the evidence (version ids, pod names, timestamps) is recorded in the migration log.
- On failure: if any pod still shows an old version id, or refresh warnings persist, do not revoke. Investigate and repeat the gate.

**P7. Revoke the old keys, one provider at a time.**
- Trigger: the P6 gate has passed and security has signed off.
- Moves: if the provider supports disabling a key, disable first and watch error rates for an agreed period. Then delete the old key. Start with the provider that has the lowest traffic.
- State: at the provider only.
- On failure: a revoked key cannot be restored. This is why P6 and the disable step come first. If error rates rise after disabling, re-enable the old key, if the provider allows it, and return to P6. If it does not, the team must write a new key and repeat P2 to P6 for that provider.

**P8. Lock down rollback.**
- Trigger: immediately after P7 for each provider.
- Moves: deploy tooling must block any image built before P4. Those images contain revoked keys and would fail. Rollback targets are limited to images built after the migration.
- State: the deploy tooling allow-list.
- On failure: if a pre-migration image is deployed by mistake, the new pods fail at startup or at the first request. Because `maxUnavailable: 0` keeps the other pods running, the impact is limited to the failing rollout.

**P9. Clean up and close out.**
- Trigger: P7 and P8 are complete.
- Moves: ask each provider to confirm deletion of old keys. Remove old local copies. Update `deploy.md` (local development, readiness semantics, rotation procedure). Record what changed in the migration log.
- State: the docs and the migration log.
- On failure: if a stale local copy is found, treat it as a new exposure and repeat P2 to P7 for that key.

**Rotation procedure for later (reuses P2, P6, P7).**
- Write the new key to the store as a new version. The running pods pick it up within 5 minutes through R4, so no restart is needed. Confirm with the P6 gate. Then revoke the old key. The cadence is an open question.

## Open questions

1. **Rotation cadence.** Not decided. Security must decide whether keys rotate on a schedule after the migration, and how often. This plan does not choose one.
2. **Provider capabilities.** Do the three providers support two active keys at once, a disable state before delete, and per-key usage data? P2, P6 and P7 depend on all three.
3. **Retry count.** Does "retry 3 times" mean 3 total attempts or 1 plus 3 retries? This plan assumes 1 plus 3.
4. **Staging.** `deploy.md` mentions only prod and local. Is there a staging environment that should go through P5 first?
5. **Liveness probe.** Which endpoint does the liveness probe use? If it is `/healthz`, R2 needs a separate liveness endpoint.
6. **Bad-key fallback.** Should the app keep the previous version as a one-cycle fallback on 401 or 403 during the migration (R5), or rely only on validation at P2?
7. **Rollback window.** How long must the old keys stay valid for rollback, given that a pre-migration image cannot be deployed after P7?
8. **Cluster access.** Can engineers `exec` into prod pods or read their memory? If so, they could read keys in memory despite the store policy. Security must decide.
9. **Store labels.** Does the store support a "current" label? This plan reads the latest version. If the store offers a label, R4 may use it instead.
10. **Image registry.** Who can pull old images that contain the keys? Access should be restricted until P8 is complete.