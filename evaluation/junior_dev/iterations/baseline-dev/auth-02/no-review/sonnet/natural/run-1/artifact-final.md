# Plan: move `orders-api` third-party keys into the managed secret store

## Summary

- The three live keys (payments, email, geocoding) leave `config/app.yaml` and live in the secret store under `orders-api/<env>/<name>`.
- Because the keys have been in git history for two years, they are treated as leaked. Each key is replaced by a new one issued at its provider, and the old one is revoked only after every instance is confirmed to be using the new one.
- Old and new keys are valid at the same time during the migration. That overlap is what lets us avoid failed customer requests.
- The app holds the keys only in memory and re-reads them from the store every 5 minutes.

Names used below:

| Provider | Store path |
|---|---|
| payments | `orders-api/prod/payments_api_key` |
| email | `orders-api/prod/email_api_key` |
| geocoding | `orders-api/prod/geocoding_api_key` |

`<env>` comes from a non-secret setting, `APP_ENV` (`prod`, `staging` or `dev`).

**Assumptions to verify in step 2, not decisions:**

- Each provider lets two keys be active at once.
- Each provider issues sandbox or test keys for dev.
- The store grants decrypt through the per-environment KMS key as part of a normal read.
- Pods authenticate to the store through their workload identity, so no store credential sits in an environment variable.

## Open question (not decided here)

**Scheduled rotation.** Security has not decided whether keys must be rotated on a regular schedule after this migration, or how often. This plan picks no cadence. Step 17 gives a rotation procedure that works at any cadence without restarts, so the decision can be made later without changing the design.

---

## Part A: Rollout

### 1. Create the store paths and access rules

- **Starts when:** the plan is approved and a rollout ticket exists.
- **What moves where:** nothing sensitive yet. Platform and security create the paths and policies.
  - `orders-api/prod/*`:
    - Read for the service identity `orders-api-prod` only.
    - Write for the security on-call group only.
    - Engineers get no access.
  - `orders-api/dev/*` (and `staging` if it exists): engineers can read, and a separate group can write.
  - Each environment is encrypted with its own KMS key.
- **Where state lives:** store and IAM policy, kept as reviewed config (infrastructure code or the store's policy export), not click-ops.
- **If it fails:** nothing in production has changed.
- **Verification (tests recorded in the ticket):**
  - An engineer identity reading `orders-api/prod/*` is denied.
  - `orders-api-prod` reading `orders-api/prod/*` succeeds.
  - `orders-api-prod` writing, or reading any other prefix, is denied.
  - A non-on-call identity writing is denied.
  - If any test fails, fix the policy and do not continue.

### 2. Issue new keys at each provider (old keys stay active)

- **Starts when:** step 1 verification passes.
- **What moves where:** the security on-call creates one new live key per provider. The old keys stay active. They are not revoked yet.
- **Where state lives:** the provider account. The new values exist only in the on-call's session until step 3. They do not go into tickets, chat, shell history or files.
- **If it fails:** if a provider cannot hold two active keys, stop. That provider needs its own cutover plan, because a single-key swap would make live requests fail during the window. Raise it as a blocker. The other providers can proceed.

### 3. Write the new keys to the prod store

- **Starts when:** step 2 is done.
- **What moves where:** the security on-call writes each new value to its `orders-api/prod/<name>` path, through stdin or the store UI. Each write returns a version id. The on-call records only the version ids in the rollout ticket.
- **Where state lives:** the store, encrypted at rest. The ticket holds version ids only.
- **If it fails:** a failed write leaves the path as it was. Retry the write. Nothing consumes these paths yet, so there is no customer impact.

### 4. Pre-flight check of the new keys

- **Starts when:** step 3 is done.
- **What moves where:** the on-call makes one harmless authenticated call per provider (a read-only or no-side-effect endpoint) using the new key.
- **Where state lives:** the result goes in the ticket (pass or fail, no values).
- **If it fails:** a bad key is caught here, not in a pod. Fix it at the provider or re-issue, write a new store version (step 3), and repeat. Do not deploy until all three pass.

### 5. Prepare dev and staging

- **Starts when:** in parallel with steps 2 to 4.
- **What moves where:**
  - Provider sandbox or test keys are written to `orders-api/dev/<name>` (and `staging`).
  - `make run` is changed to set `APP_ENV=dev`. The app fetches its keys at startup with the engineer's own credentials.
  - A non-secret override file points `base_url` at sandbox endpoints.
  - `make run-offline` is added. It starts local stub providers, needs no keys and makes no store call.
- **Where state lives:** the dev paths in the store, and the override file in the repo (URLs only).
- **If it fails:** if a provider has no sandbox keys, use `make run-offline` for that provider. Local development never gets prod access. A developer who tries `APP_ENV=prod` is denied by step 1 policy and the app exits.

### 6. Ship the code change in one PR

- **Starts when:** review of the PR starts. It can be written alongside steps 2 to 5 but is not deployed until step 4 passes.
- **What moves where:**
  - **Secret holder.** Add a module `app/secrets.py` (design in Part B).
  - **Clients.** Change the three clients so they no longer copy a key at construction. Each call asks the holder for the current key.
  - **Config file.** Remove the three `api_key` lines from `config/app.yaml`. `config_loader.py` keeps loading the non-secret settings.
  - **Readiness.** `/healthz` returns 503 until all three keys are loaded.
  - **Startup.** Add the startup sequence in step 13.
  - **CI guard.** A required check on `main` that fails if `config/app.yaml` contains an `api_key` key at any depth, even with an empty value. As a backstop, it also fails if any repo file matches the provider key prefixes (`pk_live_`, `ml_live_`, `geo_live_`). The check is in the same PR, so it is enforced from merge onward.
- **Where state lives:** git, then the container image. The image no longer contains any key.
- **If it fails:**
  - CI red: fix and re-push.
  - Guard test: include a deliberate test PR (or unit test) that adds `api_key` and confirm the check fails.
  - Do not merge to `main` until tests pass, including the failure drills in step 7.

### 7. Drill the failure paths in staging

- **Starts when:** the PR build is deployed to staging (using staging store paths).
- **What moves where:** run the drills below and record each result in the ticket.
  - **Store unreachable at startup.**
    - The pod retries 3 times, 2 seconds apart, then exits non-zero.
    - It never reports ready.
  - **Store reachable but one key missing.** Same result as above.
  - **Rotation without restart.** Write a new version in staging. Within 5 minutes the instance reports the new version id and uses it.
  - **Failed re-read.** Block the store while the instance runs. It keeps serving with the last good value and logs a warning. Unblock it and the next re-read succeeds.
  - **Secrets stay out of logs and environment.** Inspect logs, the environment and the filesystem for the key values. None should appear.
- **Where state lives:** the staging environment and the ticket.
- **If it fails:** fix in the PR and redo the drill. Do not proceed to production with a failed drill.

### 8. Roll out to production

- **Starts when:** steps 4 and 7 are done and the PR is merged to `main`. CI builds the image, and the normal rolling deploy runs (one pod at a time, `maxUnavailable: 0`).
- **What moves where:**
  - Each new pod loads the three keys from the store using the `orders-api-prod` identity.
  - It becomes ready only after all three load.
  - Only then is an old pod stopped.
  - **Mixed fleet during the rollout:** old pods keep using the old keys from the old image, which are still valid. New pods use the new keys from the store.
- **Where state lives:** keys in each pod's memory. Store version ids appear in the pods' startup logs.
- **If it fails:**
  - A new pod that cannot load its keys exits non-zero and never becomes ready, so the rollout halts and the old pods keep serving.
  - If new pods are ready but the new key misbehaves, roll back by redeploying the earlier image. This is safe at this point because the old keys are still active and in that image.
  - Watch customer error rates on the new pods during the rollout.

### 9. Confirm every instance is on the new keys

- **Starts when:** the rollout finishes (all 4 replicas on the new image).
- **What moves where:** the on-call or release engineer checks, for each replica, that:
  - it is running the new image (no pod from a pre-migration image remains), and
  - it reports, through an internal-only endpoint or metric, the version id it currently holds for each of the three secrets, and those ids match the ids recorded in step 3.
  - The report contains version ids only, never values.
  - Also confirm that error rates are normal, and scan the central logs for the key prefixes to confirm no value leaked.
- **Where state lives:** pod memory, and the recorded checklist in the ticket.
- **If it fails:** any replica on a different version id or an old image blocks step 11. Wait for the 5-minute refresh and re-check. If it still differs, restart that pod (safe, because the store holds the new value). Do not revoke anything while any replica is unconfirmed.

### 10. Hold for a soak window

- **Starts when:** step 9 passes.
- **What moves where:** nothing moves. Both old and new keys remain valid for an agreed soak period (suggest at least one full business day, to be agreed with security). Rolling back to a pre-migration image remains possible during this time.
- **Where state lives:** the ticket records the window end.
- **If it fails:** if problems appear, roll back as in step 8. The old keys are still valid.

### 11. Inventory other users of the old keys, then revoke them one at a time

- **Starts when:** step 10 ends and the security on-call approves.
- **What moves where:**
  - **Inventory first.** Look for other users of the old keys: scripts, other services, developers' local runs (`make run` used live keys), and the provider's usage logs showing recent calls with the old key.
  - Repoint or retire anything still using them.
  - **Then revoke.** Revoke each old key at its provider, one at a time. Watch error rates for a while before revoking the next.
- **Where state lives:** the provider account. The ticket records each revocation.
- **If it fails:**
  - A revoked key cannot be restored, so the gating in steps 9 and 10 matters.
  - If errors appear after a revocation, the cause is a client still holding the old key. The new key is already in the store, so a rolling restart of the affected pods fixes it. Any such errors are a gating failure to review.
  - **Rollback rule from this point:** never roll back to a pre-migration image. Those images contain only revoked keys. Roll back only to images that read from the store.

### 12. Close out

- **Starts when:** all three old keys are revoked.
- **What moves where:**
  - Confirm the CI guard is a required check on `main`.
  - Delete the old `api_key` values from any docs, and mark pre-migration images as non-deployable (retention policy or tag).
  - Update `deploy.md` for the new rollback rule, the new `make run` and `make run-offline`, and the new `/healthz` meaning.
- **Where state lives:** repo, registry, ticket.
- **If it fails:** closeout items are tracked in the ticket until done. The old keys are already dead, so there is no urgency from a security view.

---

## Part B: How the app reads keys at runtime

### 13. Startup

- **Starts when:** the process starts.
- **What moves where:**
  - The app reads `APP_ENV` (non-secret) and builds the paths `orders-api/<env>/payments_api_key`, `.../email_api_key` and `.../geocoding_api_key`.
  - It reads all three from the store using its workload identity.
  - Each attempt has a bounded timeout (suggest 5 seconds).
  - Allow the first attempt plus 3 retries, with 2 seconds between attempts, so 4 attempts in all.
  - On success, the values go into an in-memory snapshot, together with each version id.
  - The values are wrapped in a `Secret` type. Its `str`/`repr` print `<redacted>`, and only the HTTP-header code can unwrap it.
  - Nothing is written to disk. Nothing is placed in environment variables.
  - Core dumps are disabled in the container.
- **Where state lives:** one immutable snapshot in process memory.
- **If it fails:** after the last failed attempt the process logs the error class and the secret names (never values) and exits with a non-zero code. In production, the pod does not become ready and the rollout halts, as in step 8.

### 14. Readiness

- **Starts when:** the startup snapshot is complete.
- **What moves where:** `/healthz` returns 200 only once all three keys are loaded. Before that it returns 503. After the first success it stays 200 for the life of the process, even if later re-reads fail. This is deliberate. If it dropped to 503 on a store outage, every pod would go unready at once, and an outage in the store would become an outage of the whole service.
- **Where state lives:** a boolean set once, in memory.
- **If it fails:** the pod stays out of the load balancer and the deploy gate in step 8 holds.

### 15. Serving a request

- **Starts when:** a request needs a provider call.
- **What moves where:** the client calls `secrets.get('<name>')` for each outbound call, instead of using a copy made at construction. The `Authorization` header is built from the current snapshot. The Authorization header is excluded from HTTP debug logging. The module-level client singletons stay, because they no longer hold a key.
- **Where state lives:** reads from the in-memory snapshot, with no network call. A call that has started finishes with the key it started with.
- **If it fails:** if `get` is called before the first load (which should not happen once ready), it raises and the request returns 503.

### 16. Refresh every 5 minutes

- **Starts when:** a timer on a background thread fires 5 minutes after the last attempt.
- **What moves where:**
  - It reads the latest version of each of the three secrets from the store.
  - If a version id differs from the current one, it builds a new snapshot and swaps it in atomically.
  - No lock is held during the network call.
  - On a swap it logs an info line with the secret name and the new version id.
  - A new store version is therefore used by every instance within about 5 minutes, without a restart.
- **Where state lives:** the in-memory snapshot, plus the version ids reported on the internal endpoint used in step 9.
- **If it fails:**
  - On any error, keep the last good value for that secret and log a warning (secret name, error class, the version id still in use, never a value).
  - The next attempt is made at the next tick.
  - The thread catches all exceptions, so it cannot die.
  - Suggested addition: alert if no refresh has succeeded for 15 minutes. Without it, a long store outage could go unnoticed until a rotation depends on it.

### 17. Later key rotation (works for any cadence)

- **Starts when:** a rotation is needed, whether ad hoc or on whatever schedule security eventually decides (see Open question).
- **What moves where:**
  1. The on-call creates a new key at the provider while the old one stays active.
  2. They write it as a new store version.
  3. They run the step 4 pre-flight check.
  4. Within 5 minutes every instance swaps to it.
  5. Confirm per step 9 that every replica reports the new version id.
  6. Revoke the old key only after that, with the inventory check from step 11.
- **Where state lives:** store versions and the instances' memory.
- **If it fails:** if a replica does not confirm, do not revoke. Restart that pod if needed. A bad new key is replaced by writing a new store version containing the previous (still active) value.

---

## Failure summary

| Situation | Behaviour |
|---|---|
| Store down at startup | 4 attempts, then non-zero exit. In prod the rollout halts and old pods keep serving. |
| Store down while running | Last good keys kept, warning logged, `/healthz` stays 200. |
| New key bad | Caught by the step 4 pre-flight. If missed, roll back while old keys are still active. |
| Old key revoked too early | Prevented by the gates in steps 9, 10 and 11. Recover by restarting affected pods. |
| `api_key` added back to `config/app.yaml` | CI fails the change. |
| Engineer wants prod values | Denied by policy. Local runs use dev sandbox keys or stub providers. |
