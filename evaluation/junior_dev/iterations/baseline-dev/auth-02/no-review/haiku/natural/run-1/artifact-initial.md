# orders-api: move third-party API keys into the managed secret store

## Scope and decisions taken from the brief

- Keys: `payments_api_key`, `email_api_key`, `geocoding_api_key`. Store names: `orders-api/<env>/<name>`, for example `orders-api/prod/payments_api_key`.
- Every key is treated as leaked. Each one is rotated at its provider. Old keys are revoked only after every running instance is confirmed on the new key. Git history is not rewritten.
- Key values live only in process memory. They never go to disk, environment variables or logs. Version ids may be logged.
- The app fails closed. The new code has no fallback to `config/app.yaml` for keys, so a pod that cannot load all three keys does not become ready.
- Only the security on-call can write prod secrets. `orders-api-prod` has read-only access to `orders-api/prod/*`. Engineers have no read access to prod values.

## Assumptions to verify before Step 1

- A: Each provider can have two active keys at once (old and new), so both can be valid during overlap. If a provider allows only one active key, this plan does not work as written. Stop and return to security for a different cutover design.
- B: The store can answer "current version" reads, so a refresh picks up the newest write without a deploy.
- C: The provider returns 401 or 403 (before any side effect) when it rejects a key. This matters for the retry rule in R4.

## Open questions (not decided)

- **Q1 (security): Must keys be rotated on a regular schedule after this migration, and how often?** Not decided. Do not pick a cadence. The procedure in Steps 3 to 12 is also the rotation procedure, and the runtime design in R1 to R4 supports any cadence without a code change.
- **Q2: Rollback after revocation.** Once old keys are revoked, a pre-migration image cannot work. Step 11 closes that path on purpose. Confirm the team accepts this.
- **Q3: Dev keys.** Confirm each provider issues sandbox keys for the `dev` environment. Local development depends on them.

---

## Part A: Runtime behavior (how the app reads keys)

### R1. Process start, load and gate

- **Starts:** Container start.
- **Moves:** The store to process memory. The app reads the current version of all three secrets. Non-secret settings (`base_url`, timeouts, from-address) still come from `config/app.yaml`. `APP_ENV` picks the store path. It is a name, not a key.
- **State:** Process memory only. Each holder records its version id.
- **Ordering change:** Nothing reads secrets at import time. `settings` still loads from YAML. Client singletons such as `payments = PaymentsClient()` no longer copy the key in their constructor. Import builds no network calls.
- **Retry:** Make 1 attempt plus 3 retries, 2 seconds apart, for any secret that has not loaded yet. Only the failed reads are retried.
- **On failure:** If any secret is still missing after the retries, log an error that names the secret and the error class, with no value. Exit with a non-zero code. The orchestrator restarts the pod with backoff. A 403 from the store is treated the same way and logged as a permissions error.

### R2. Readiness and liveness

- **Starts:** Kubelet probes.
- **Moves:** Nothing.
- **State:** A `secrets_loaded` flag, set when R1 finishes.
- **Rule:** `GET /healthz` returns 200 only when `secrets_loaded` is true. Today it returns 200 as soon as the HTTP server listens. That would let a new pod pass readiness with no keys, so it must change.
- **Liveness:** Keep passing while the process runs. A store outage must not cause restarts of pods that already hold good keys.
- **On failure:** A pod that never loads its keys never becomes ready. `maxUnavailable: 0` then halts the rollout and the old pods keep serving.

### R3. Background refresh

- **Starts:** A timer every 300 seconds, with jitter so the four pods do not all call the store at once.
- **Moves:** The store to memory. If the version id changed, the holder swaps in the new value with one reference assignment. In-flight calls keep the value they already read. The app logs the old and new version ids, not the values.
- **State:** Memory only. Each refresh records the time of the last success.
- **Validation:** Reject an empty or malformed value. Keep the last good value.
- **On failure:** On a store error, timeout or invalid value, keep the last good value and log a warning. The warning names the secret, the version id still in use and the error class. Increment a failure counter. Readiness does not change. Alert when a secret has had no successful refresh for a set period, for example 15 minutes.

### R4. Each provider call

- **Starts:** A request that calls payments, email or geocoding.
- **Moves:** The key is read from the holder when the call is built, not cached in the client. The `Authorization` header is set per call.
- **State:** Memory.
- **On a 401 or 403 from the provider:** Trigger one refresh now, at most once per minute per secret. If a newer version id is found, retry the call once. A 401 or 403 means the provider rejected the request before doing any work, so the retry is safe for payments. If no newer version exists, return the provider error as today.
- **Why this matters:** It lets a pod recover from a key revoked early without waiting for the 5-minute timer. Customers do not see the failure.

### R5. Logging and error handling

- **Starts:** Any log line, exception or HTTP client debug event.
- **Moves:** Nothing.
- **Rules:** Log secret names and version ids only. The holder's `repr` is redacted. Configure the HTTP client so it never logs headers. Exception messages must not contain key text.
- **Verification:** A test runs the request and failure paths with a known fake key and asserts that the fake key does not appear in captured logs.
- **On failure:** If a key value is found in logs, treat that key as exposed and rotate it again using Steps 3 to 12.

### R6. Restart

- **Starts:** Pod restart, node drain or deploy.
- **Moves:** The new process repeats R1 from the store.
- **State:** Memory is lost on exit, which is intended.
- **On failure:** During a store outage, a restarted pod cannot start (R1 exits). Capacity drops by one pod per restart. Monitor this with the store's health. It is a known risk that the migration introduces.

---

## Part B: Rollout

### Phase 0: Prepare the store and the keys (no code change, no customer impact)

**Step 1: Verify assumptions A to C.**
- **Starts:** Migration kickoff.
- **Moves:** Nothing. Read provider documentation and test overlap on a sandbox key.
- **State:** Recorded in the migration ticket.
- **On failure:** If overlap is not supported, stop. Do not continue to Step 3.

**Step 2: Create the store entries, KMS keys and IAM policy.**
- **Starts:** Step 1 passes. Security on-call performs the change.
- **Moves:** Creates the `orders-api/prod/*` and `orders-api/dev/*` paths, with one KMS key per environment. Grants `orders-api-prod` read on `orders-api/prod/*` only. Grants developers read on `orders-api/dev/*` only. No engineer gets read on prod.
- **State:** Store policy and KMS keys. No values yet.
- **On failure:** If the policy is wrong, the new pods cannot start (R1). The rollout halts and the old pods keep serving, so customers are not affected. Check the policy with a policy simulator before Step 9.

**Step 3: Issue new keys at each provider.**
- **Starts:** Step 2 done. Security on-call performs the change.
- **Moves:** Creates a new key at payments, email and geocoding. The old keys stay valid.
- **State:** Provider consoles. New values are held only in the write path.
- **On failure:** Nothing has changed for customers. Retry issuance.

**Step 4: Write the new prod keys to the store.**
- **Starts:** Step 3 done. Only the security on-call can write.
- **Moves:** Writes `orders-api/prod/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key`. The store encrypts each one with the prod KMS key and creates a new version id for each write.
- **State:** Store, encrypted at rest. The version ids are recorded in the ticket. The values are not.
- **Effect on running pods:** None. Old pods read their keys from the old image and do not read the store.
- **On failure:** Partial writes are safe. Pods built from the new code need all three keys, so an incomplete set stops them at R1. Finish the writes before Step 9.

**Step 5: Write the dev keys to the store.**
- **Starts:** Step 3 done (sandbox keys).
- **Moves:** Writes `orders-api/dev/*`. Developers read these through their own identity.
- **State:** Store. Dev keys are not prod keys.
- **On failure:** Local development stops working until this is fixed. No customer impact.

### Phase 1: Code and config (merge without deploying to prod)

**Step 6: Merge the runtime secret layer.**
- **Starts:** Pull request merged to `main`. CI builds a new image.
- **Moves:** Adds the secret holder and the R1 to R5 behavior. Replaces the copied keys in the clients with per-call reads (R4). Changes `/healthz` (R2). The YAML keys are still present and ignored by the code.
- **State:** Code only.
- **Tests:** Unit tests for startup retry and exit code, refresh swap, refresh failure keeping the last good value, readiness gating, provider 401 retry (R4), and log redaction (R5).
- **On failure:** The pull request does not merge. Nothing is deployed.

**Step 7: Validate in dev.**
- **Starts:** Image from Step 6 deployed to a non-prod environment that uses the dev store.
- **Moves:** Runs the same startup, refresh and failure cases against the dev store. Also tests with the store unreachable, to confirm the exit code after about 6 seconds.
- **State:** Dev store. No prod values.
- **On failure:** Fix before continuing. Prod is not touched.

**Step 8: Remove the keys from `config/app.yaml` and add the CI gate.**
- **Starts:** Step 6 merged and Step 7 passed.
- **Moves:** Deletes the three `api_key` lines from `config/app.yaml`. Non-secret values stay. Adds a CI check that fails any change that puts an `api_key` key into `config/app.yaml` (or any file under `config/`).
- **State:** Repository. The removed values remain in git history, which is accepted.
- **Effect on running pods:** None. Running pods already hold their keys in memory. Pods built from this commit read keys only from the store.
- **On failure:** If the CI gate blocks this pull request, fix the gate. Do not add the key back to get the change through.
- **Note:** Old images in the registry still contain the old keys. They are inert after Step 12.

### Phase 2: Rollout (old keys still valid)

**Step 9: Roll out the new image to prod.**
- **Starts:** Image from Step 8 is promoted to prod.
- **Moves:** Each new pod runs R1 with the `orders-api-prod` identity and loads the new keys from the store. The rollout is one pod at a time with `maxUnavailable: 0`. Old and new pods both serve, and both key sets are valid (overlap from Step 1).
- **State:** Memory in each new pod. The store is the source of truth.
- **On failure:**
  - A pod that cannot load keys exits (R1) and never becomes ready. The rollout halts and the old pods keep serving.
  - Roll back by redeploying the previous image. This is allowed until Step 11.
  - Alert on repeated pod exits.

**Step 10: Confirm every instance uses the new keys.**
- **Starts:** Rollout is complete (no pre-migration pods remain).
- **Check:** Every pod reports the new version id for all three secrets (metric or structured log, no values). Provider dashboards show zero requests on the old keys. Wait at least one full refresh cycle (5 minutes), plus the 10-second payment timeout, then observe for 15 minutes with error rates at baseline.
- **State:** Metrics and logs. Version ids are recorded in the ticket.
- **On failure:** Any pod still on an old version id is a blocker. Find out why (usually a refresh failing, or a pre-migration pod still running). Do not revoke. This is the gate for Step 12.

### Phase 3: Revoke (after the gate)

**Step 11: Close the rollback path to pre-migration images.**
- **Starts:** Step 10 passed.
- **Moves:** Deploy policy blocks any image built before Step 8. Rollback targets become post-migration images only.
- **State:** Deploy policy.
- **On failure:** If a pre-migration image is needed after this, it cannot be deployed because its keys are about to be revoked. This is accepted (Q2).

**Step 12: Revoke the old keys, one provider at a time.**
- **Starts:** Steps 10 and 11 passed. Security on-call approves each provider separately.
- **Moves:** Revokes the old payments key, then email, then geocoding. Watch error rates for that provider for at least 15 minutes before the next one.
- **State:** Provider consoles. The old keys are dead, and the values in git history and old images are now useless.
- **On failure:** Providers may not allow revoked keys to be re-enabled. The recovery path is forward: issue a new key, write it to the store (new version id) and let R3 or R4 pick it up. Mitigation is the R4 immediate refresh, so recovery takes seconds, not 5 minutes. Stop further revocations until the error rate is back at baseline.

**Step 13: Revoke local copies and confirm local development.**
- **Starts:** Step 12 done.
- **Moves:** Developers who cloned the old `config/app.yaml` must pull the new one and run `make run` against the dev store. Confirm that `make run` reads only `orders-api/dev/*`.
- **State:** Developer machines. Nothing secret is on disk because `make run` uses R1 with the developer's identity.
- **On failure:** Developers who cannot read dev keys cannot run locally. This is a request for access to `orders-api/dev/*`, not a reason to read prod.

### Phase 4: Close out

**Step 14: Update the runbooks.**
- **Starts:** Step 13 done.
- **Moves:** Update `deploy.md`: readiness now means keys are loaded; local development uses the dev store; the rollback rule from Step 11. Document the rotation procedure (Steps 3 to 12) as the runbook for later rotations, with the cadence left open (Q1).
- **State:** Repository documentation.
- **On failure:** Not customer-facing. Fix the document.

**Step 15: Final check.**
- **Starts:** Step 14 done.
- **Check:** The CI gate from Step 8 fails on a test change that adds an `api_key` to `config/app.yaml`. Logs for the window contain no key value. Store read logs show only `orders-api-prod` reading `orders-api/prod/*`.
- **State:** Ticket and dashboards.
- **On failure:** Reopen the affected step.

---

## Where state lives

| Item | Location | Lifetime |
|---|---|---|
| Key values at rest | Secret store, encrypted with the per-environment KMS key | Until replaced |
| Key values in use | Process memory in each pod | Until the pod exits |
| Non-secret config | `config/app.yaml` in the repo and image | Until the next change |
| Version ids | Logs and metrics, and the migration ticket | Logs kept 30 days |
| Old keys | Provider (until revoked), git history, old images | Revoked keys are dead; history is not rewritten |

## Failure summary

- Store unreachable at start: the pod exits, the rollout halts, the old pods serve. No customer impact.
- Store unreachable at runtime: the pod keeps its last good keys and logs a warning. Alert on staleness.
- Provider rejects a key: the pod refreshes once and retries (R4). If that does not help, the error goes to the customer as it does today.
- A revoked key is still in use: this is why Step 10 must pass before Step 12.