# orders-api: move the three live API keys into the managed secret store

## Summary

Today `orders-api` holds three live third-party API keys (payments, email and geocoding) in `config/app.yaml`. That file is committed to git and copied into every container image. The app reads the file once, when the process starts, and each provider client copies its key once from that file. So the keys sit in git history and in every image, and changing a key means building and deploying a new image.

This plan moves the keys into the managed secret store, under `orders-api/<env>/<name>`. A pod built from the new image reads its keys from the store at startup, keeps them only in memory, and re-reads them every 5 minutes. The key values never go into the image, the config file, environment variables or logs.

The keys are treated as leaked, so every key is rotated at its provider first. The old key and the new key both work for a while, so customer requests are not affected during the change. The order of work is:

1. prepare the store and its access rules;
2. rotate each key at its provider, while the old key still works;
3. write each new key to the store;
4. ship the new image, whose pods wait for their keys before they take traffic;
5. confirm that every pod runs the new keys;
6. wait a bake period;
7. only then revoke the old keys.

This order keeps old pods serving with the keys in their own image. A rollback therefore always has working keys until the old keys are revoked.

Proposed secret names: `orders-api/prod/payments_api_key`, `orders-api/prod/email_api_key`, `orders-api/prod/geocoding_api_key`. The same names exist under `orders-api/dev/` and, if a staging environment exists, under `orders-api/staging/`. Those hold sandbox keys, not live keys.

## Terms

- **Secret store:** the managed service that holds the keys. It encrypts each value at rest. Every write creates a new version with a new version id. The brief does not name the product.
- **KMS (key management service):** the service that holds the encryption key the secret store uses. Each environment has its own KMS key, so prod has a key that dev does not use.
- **Live key:** a provider key that works with real payments and real email. **Sandbox key:** a key that works only in a provider's test environment. Only live keys go to prod.
- **Provider:** a third-party service the app calls: payments, email or geocoding.
- **Identity:** the account a pod uses to talk to the secret store. Prod pods use the identity `orders-api-prod`. How a pod proves it holds that identity is not decided yet (see open questions).
- **Version id:** the id the store gives each write. It is not secret, so it may be logged.
- **Pod:** one running copy of the app. Production runs 4 pods, all under `orders-api-prod`.
- **Image:** the packaged app. CI builds one image per merge to `main`. A pod starts from one image.
- **Pre-migration image:** any image built before this change. Its `config/app.yaml` still holds the keys.
- **Old ReplicaSet:** the group of pods made from a pre-migration image. A ReplicaSet is the cluster's group of identical pods.
- **Readiness:** the check the cluster uses to decide whether a pod may receive traffic. A ready pod returns 200 from `GET /healthz`.
- **Liveness:** the check the cluster uses to decide whether to restart a pod.
- **Rollout:** replacing old pods with new ones. Deploys roll one pod at a time with `maxUnavailable: 0`, which means the cluster does not stop an old pod until its new replacement is ready.
- **Rollback:** redeploying an earlier image tag, as `deploy.md` describes. The on-call or the service owner runs it. The tool or command is not named yet (see open questions).
- **Holder:** the in-memory object that holds one key's current value, its version id and when it was fetched.
- **Refresh:** re-reading the keys from the store on a timer.
- **Bake period:** a wait after every pod runs the new keys, before the old keys are revoked.
- **Revoke:** disable an old key at its provider so that it stops working.
- **Admission rule:** a cluster rule that blocks deploying a named image.
- **Stub client:** a fake provider client that needs no key.
- **Central log service:** where all app logs go. It keeps them for 30 days.

---

## How the app reads its keys at runtime

Today each client copies its key in its constructor, and the clients are built when their module is imported. That would keep the old key in memory forever. `/healthz` also returns a status ok as soon as the HTTP listener is up, which is unsafe here, because a new pod could take traffic before it has any keys.

After the change, the app loads the keys from the store at startup, reads the current key on each request, and refreshes the keys every 5 minutes.

The image alone decides which path a pod takes. There is no switch in config. A pod from the new image always reads the store, and its `config/app.yaml` has no keys. A pod from an old image always reads its own `config/app.yaml`, which still holds keys, and never touches the store.

`config/app.yaml` keeps the non-secret settings: app name `orders-api`, port 8080, log level `info`, the three base URLs (`https://api.payprovider.example/v2`, `https://api.mailer.example/v3`, `https://geo.example/v1`), the payments timeout of 10 seconds, the geocoding timeout of 3 seconds, and the email from address `orders@shop.example`. The file may list secret names. A name is a reference, not a value. The file path comes from the `APP_CONFIG` environment variable and defaults to `config/app.yaml`.

### Startup loading

- **Starts when:** the process starts. It runs before the server accepts traffic.
- **What it does:**
  1. Read the non-secret settings from `config/app.yaml`.
  2. Read the environment name from the non-secret environment variable `APP_ENV`. Where `APP_ENV` is set in prod is an open question.
  3. For each of the three names, fetch the current version of `orders-api/<env>/<name>`, using the pod's identity.
  4. Store each value in its own holder, with its version id and fetch time.
  5. Log each secret name and its version id. Never log the value. The rollout check reads these lines.
  6. If all three keys loaded, mark the process ready (see Readiness) and start the refresh timer (see Refresh).
- **Retries:** if the store cannot be reached, or a key is missing while the store is reachable, the app retries. The brief says retry 3 times, 2 seconds apart. This plan reads that as one first attempt plus 3 retries, with 2 seconds between attempts. This reading is an open question.
- **Where the data lives:** memory only. Nothing is written to disk, to environment variables or to crash dumps.
- **If it fails:** log an error that names the missing secret and the store error, never the value. Exit with a non-zero code. The cluster restarts the pod with its own backoff. The pod never becomes ready, and old pods keep serving.

### Readiness and liveness

- **Starts when:** the cluster probes the pod.
- **What it does:**
  - Readiness returns 200 only after startup loading has succeeded. It does not look at refresh status, so a later store outage does not take pods out of traffic.
  - Liveness only checks that the process responds. It does not depend on the store.
  - Readiness stays on `/healthz`. Liveness uses a second path. If both used `/healthz`, a pod with no keys would fail liveness and be restarted, which is the wrong response. The name of the liveness path is an open question.
  - The service owner changes the cluster probe configuration in the same change as the code. Old pods keep the old meaning, because the old image has the old code.
- **Why:** a new pod must not take customer traffic before it has its keys.
- **Where the data lives:** none. This only reports the result of startup loading.
- **If it fails:** if readiness returns OK before startup loading finishes, the rollout check fails silently. A test must confirm that a pod with no keys returns not-ready.

### Reading a key on each request

- **Starts when:** a request needs a provider.
- **What it does:** each client receives the secret provider when it is built. On each request it calls `get('payments')`, `get('email')` or `get('geocoding')`. The value comes from the holder. The holder swaps the whole record at once, so a call always sees one complete value with its version id.
- **Import rule:** importing a module never does network I/O. Startup loading is the only place keys are loaded.
- **Requests in flight:** a request takes its snapshot of the holder when it starts and keeps it. A call that already has its key finishes with that key. The old key is still valid then, because revocation happens last. The next request reads the new value.
- **Where the data lives:** the holder, in memory.
- **If it fails:** a client that copies the key at construction would keep a revoked key forever. A test must confirm that a refreshed value reaches the next request.

### Refresh every 5 minutes

- **Starts when:** startup loading succeeds. A timer in the same process runs the refresh. The timer is the only trigger. Nothing refreshes on demand, and nothing refreshes sooner than 5 minutes.
- **What it does, for each secret:**
  1. Fetch the current version, with a timeout. The timeout value is to be set.
  2. On success with a new version id: swap the holder and log the version change. Never log the value.
  3. On failure: keep the last good value. Log a warning with the secret name, the error type, the last good version id and how long the value has been unchanged. Readiness does not change.
- **Where the data lives:** memory only.
- **If it fails:**
  - A short store outage has no effect beyond the warning.
  - A long outage keeps the last good value indefinitely. Alerts fire when a value is older than a threshold. The threshold is to be set, and it depends on the rotation cadence decision, which is open.
  - Limitation: the app does not check that a new value works. If the store serves a version that a provider rejects, the app keeps using it. Provider 401 and 403 errors show the problem. Whether the app should fall back to the previous version is an open question.

### Rules for the whole runtime

- Logs contain secret names, version ids, fetch times and error types. They never contain values.
- A logging filter refuses any log line that contains a known key prefix: `pk_live_`, `ml_live_` or `geo_live_`. It is a backstop only. It catches those prefixes and nothing else. It does not replace keeping values out of logs.
- Test fixtures use fake values, never real keys.
- The process never writes secrets to disk, to environment variables or to crash dumps. Core dumps are disabled for this process.
- One refresh task writes each holder. Any number of request threads read it. Each read takes a snapshot, so a refresh never exposes a half-finished update.

---

## How the migration rolls out

Principles: the keys are treated as leaked, and git history is not rewritten. Every key is rotated at its provider. An old key is revoked only after every running pod is confirmed on a new key. No customer request should fail because of a missing or revoked key at any point.

Why old and new pods can serve at the same time: every key in use is valid at its provider. Old pods use the keys in their own image's `config/app.yaml`, which stay valid until revocation. New pods use the new keys. Each new key is checked with its provider before any pod uses it, and step 1 confirms that each provider allows two live keys at once.

### Step 1. Confirm provider capabilities and inventory

- **Starts when:** this plan is approved.
- **What it does:** list each provider, its key owner, and whether it allows two live keys at once.
- **Moves:** nothing.
- **Where the data lives:** the migration record, in the tracking issue.
- **If it fails:** if a provider allows only one live key, its rotation needs a planned cut-over window. Mark that provider in the rotation and revocation steps, and take it out of the general sequence. Change nothing else yet.

### Step 2. Prepare store access and KMS

- **Starts when:** step 1 is complete.
- **What it does:** create the three prod secret entries, which stay empty until step 5. Confirm that the prod KMS key exists.
- **Access policy:**
  - Identity `orders-api-prod`: read on `orders-api/prod/*`, and decrypt with the prod KMS key. No write access. No list access outside that prefix.
  - Security on-call role: write on `orders-api/prod/*`. This is the only write path to prod.
  - Engineers: no read access to prod values. Dev access is separate (see the local development part).
- **Where the data lives:** the access policy, managed as code in the infrastructure repo.
- **Verification:** test the policy with a non-prod identity and with an engineer identity. Both must be denied prod reads. `orders-api-prod` must be denied writes, and denied access to any other prefix.
- **If it fails:** stop. Fix the policy before any secret value is created.

### Step 3. Create dev and staging secrets with sandbox keys

- **Starts when:** step 2 is complete.
- **What it does:** copy sandbox keys from each provider's sandbox into `orders-api/dev/*`, and into `orders-api/staging/*` if staging exists. These are not live keys.
- **Where the data lives:** the dev and staging store entries.
- **If it fails:** local development uses offline mode until this works (see the local development part). Production is not affected.

### Step 4. Rotate at providers, keeping old keys valid

- **Starts when:** steps 1 and 2 are complete. The security on-call does this.
- **What it does:** create a new live key at each provider. Do not revoke the old key. Nothing uses the new key yet.
- **Where the data lives:** the provider consoles. The new value goes directly from the provider to the store (step 5). It must never be pasted into tickets, chat or files.
- **If it fails:** if creation fails or the provider rejects the key, keep the old key. Nothing in production has changed, so there is no customer impact.

### Step 5. Write the new keys to the prod store

- **Starts when:** step 4 is complete for a provider.
- **What it does:** write the new live key to `orders-api/prod/<name>`. The store assigns a new version id. Record that version id in the migration record. Never record the value.
- **Verification:** before any pod uses the new key, the security on-call makes a read-only call to the provider with it, and confirms that the provider accepts it. The read-only endpoint for each provider is an open question.
- **Who reads the store at this point:** no prod pod reads the store before step 7. Old pods read their own `config/app.yaml`, and the new code has not run yet. Dev and staging readers use other prefixes.
- **Where the data lives:** the store, encrypted with the prod KMS key.
- **If it fails:**
  - If the write fails, retry it. Old pods are not affected, because they hold the old key from their own image.
  - If the key does not work with the provider, do not write it. Go back to step 4.
  - If a bad value was written, write a corrected version. Running pods pick it up at their next refresh or on restart. No pod on the new code exists yet.

### Step 6. Build the new image and prove it in staging

- **Starts when:** the change is merged to `main`. The change contains the code from the runtime part, and the `config/app.yaml` change with every `api_key` line removed. The CI guard (see the local development part) is added in the same change. CI builds one image as usual.
- **What it does:** the image holds the new code, a `config/app.yaml` without keys, and no secrets.
- **Staging check:** deploy the image to staging with sandbox keys. Confirm that:
  - new pods do not become ready until all three keys are loaded;
  - a store outage at startup leads to a non-zero exit after the retries;
  - a store outage after startup leaves the app serving on its last good keys, with a warning.
- **Where the data lives:** the image (no secrets) and the staging store.
- **If it fails:** do not promote the image. Fix it on `main` and rebuild. Production is untouched.

### Step 7. Roll out to production

- **Starts when:** step 5 is complete for all three providers, step 6 has passed in staging, and the release is approved.
- **What it does:**
  - The cluster replaces pods one at a time, with `maxUnavailable: 0`. Production runs 4 pods.
  - A new pod loads the three prod keys at startup.
  - A new pod joins traffic only after its readiness check passes.
  - Old pods keep serving until each replacement is ready. They keep the keys in their own image's `config/app.yaml`, which stay valid until step 11.
- **Where the data lives:** each pod's memory. The rollout status lives in the cluster.
- **Watch during the rollout:**
  - the version ids each new pod logs for the three keys;
  - the per-pod provider error rate (401 or 403 from any provider);
  - pod restarts and exit codes.
- **If it fails:**
  - **Store unreachable, or a key missing.** The new pod retries, then exits non-zero. It crash-loops and never becomes ready. The cluster halts the rollout by itself, and old pods keep serving. Page the on-call. The cluster keeps restarting the pod with its own backoff. The plan sets no time limit (open question). Only a fix in the store, or a rollback, stops the loop.
  - **Keys load, but a provider rejects them** (a 401 or 403 spike on new pods). These pods are ready, so they may take traffic. The cluster does not halt on its own, because it halts only for pods that are not ready. The on-call pauses the rollout by hand, then rolls back by redeploying the previous image tag. The previous image reads its keys from its own `config/app.yaml`, so its pods use the old keys. This is safe only while the old keys are still valid, which is why revocation must not happen early. Rollback does not fix the store. Write a corrected version (step 5) before any new rollout.
  - **Rollback after revocation is not possible.** Once old keys are revoked, a pre-migration image cannot work. The revocation gate (step 10) blocks those images.

### Step 8. Confirm every pod runs the new keys

- **Starts when:** the rollout reports complete.
- **Check:**
  - every running pod logs the new version id for all three keys;
  - no pod from the old ReplicaSet remains, including any pod still draining;
  - provider error rates are at baseline for each provider;
  - the bake period has started (its length is an open question).
- **How the check is done:** the version-id lines, written at startup and on each change, go to the central log service. The security on-call queries that service for each pod's lines and records the result in the migration record. This is manual unless someone automates it.
- **Where the data lives:** the central log service and the migration record. Nothing changes in the app.
- **If it fails:** any pod still on an old version id, or any pod with a new error pattern, blocks the revocation gate. Investigate that pod. Do not revoke.

### Step 9. Bake period

- **Starts when:** step 8 passes.
- **What it does:** nothing changes. This period waits for problems that appear only under real traffic.
- **Why:** the old keys are the fallback. A fallback means rolling back to a pre-migration image. Those pods use the old keys in their own image, which work until revocation.
- **Minimum:** at least one full refresh interval (5 minutes) after the last pod changed, plus the bake window agreed with security. The window's length is an open question.
- **If it fails:** a provider error spike, or a version mismatch, restarts the check from step 8, after the cause is fixed.

### Step 10. Revocation gate

Security on-call and the service owner each sign off that:

1. Step 8 passed, and no pre-migration pod exists.
2. Step 9 passed.
3. The provider error rate matches the pre-migration baseline.
4. Deploys of pre-migration image tags are blocked. An admission rule stops any pre-migration image from being redeployed, because its embedded keys will be dead. From now on, the rollback target is a post-migration image only.

If any gate fails, the old keys stay valid. Nothing is revoked.

### Step 11. Revoke the old keys

- **Starts when:** step 10 is signed off. The security on-call does this. It needs explicit approval, because it cannot be undone.
- **What it does:** revoke each old key at its provider. Record the revocation time and key id in the migration record.
- **Where the data lives:** the provider consoles.
- **If it fails:** if customer errors appear after revocation, the only recovery is to issue another new key. Then the store and the running pods must both be updated. This is why the gate in step 10 is strict.

### Step 12. Clean up and close

- **Starts when:** step 11 is complete.
- **Checks:**
  - Search the central logs (30-day retention) for the old key values. Any hit ages out within 30 days of its last log line. Record the result.
  - Old container images still embed the old keys. They are inert after revocation. Restrict pulling them if the registry allows it.
  - Update `deploy.md` to describe the new readiness meaning, local development, and the rule that keys never go on disk.
- **Git history:** not rewritten. Old keys are treated as leaked permanently.
- **If it fails:** a log or artifact hit that cannot age out is escalated to security.

---

## Local development and the CI guard

Today `make run` loads the same `config/app.yaml`, so local runs use the live keys. After this change, no developer needs a prod key.

### Local run with dev keys

- **Starts when:** a developer runs `make run`.
- **What it does:** loads the dev keys from `orders-api/dev/*`, using the developer's own dev identity, which has no prod access. The keys are held in memory only.
- **If it fails:** if the developer has no dev access, or the store is down, use the offline run.

### Local offline run

- **Starts when:** the developer has no dev access, or the store is down.
- **What it does:** `make run-offline` starts the app with stub provider clients, so it runs without any key.

Result: no developer needs a prod key, and `config/app.yaml` no longer holds one.

### CI guard against key reintroduction

- **Starts when:** every pull request.
- **What it checks:**
  - fail if `config/app.yaml` contains an `api_key` entry;
  - fail if any tracked file contains a known live-key prefix: `pk_live_`, `ml_live_` or `geo_live_`.
- **Scope:** this stops new keys from entering the repo. It does not remove the old keys from git history.
- **When it is added:** in the same change as the `config/app.yaml` change (step 6). Added earlier, it would fail on the current file.
- **If it fails:** the PR cannot merge. The developer moves the value to the store.

---

## What happens when things fail

| When | What happens | Who acts |
|---|---|---|
| A pod starts and the store is unreachable, or a key is missing | Retries 3 times, 2 seconds apart, then exits non-zero. The pod never becomes ready. Old pods keep serving. | On-call fixes the store, or rolls back. |
| The store is unreachable after startup | The pod keeps its last good keys and logs a warning. Readiness does not change. An alert fires if the value gets too old. | On-call, if the alert fires. |
| The store serves a version the provider rejects | The pod keeps using it. Provider 401 or 403 errors rise. | On-call pauses the rollout, rolls back, and writes a corrected version. |
| A new pod never becomes ready | The rollout halts. Old pods keep serving. | On-call is paged. |
| A new key fails the provider's read-only check | Do not write it to the store. Go back to step 4. | Security on-call. |
| Staging check fails | Do not promote the image. | Developer fixes it on `main`. |
| Bake check fails | Restart the check from step 8, after the fix. | Security on-call and service owner. |
| Revocation causes customer errors | The only recovery is a new key, then store and pod updates. | Security on-call. |
| The CI guard finds an `api_key` or a live-key prefix | The PR cannot merge. | Developer moves the value to the store. |
| The dev store is down | `make run-offline` starts the app with stub clients. | Developer. |

---

## Open questions

1. **Rotation cadence (not decided).** Security has not decided whether keys must rotate on a schedule after this migration, or how often. This plan picks no cadence. The answer affects the refresh interval, the staleness alert threshold, and whether rotation becomes a repeated runbook.
2. **Two live keys per provider.** Confirm in step 1 that each provider allows an old key and a new key at once. If not, its rotation needs a planned cut-over, and the rollout and revocation steps change for that provider.
3. **Bake period.** The length beyond the 5-minute refresh is for security and the service owner to choose.
4. **Retry count.** Confirm whether retry 3 times means 3 total attempts, or 3 retries after the first attempt. This plan uses the second reading.
5. **Staging.** Confirm whether a staging environment exists. The dev and staging step and the staging check assume it does.
6. **Store version semantics.** Confirm two things. First, whether the store supports version labels or staged promotion. If it does, step 5 can write a pending version and promote it after step 8, which removes the window where a bad value is current. Second, whether a new write becomes the value every read returns at once. This plan assumes a read returns the latest version.
7. **Fallback on rejected values.** Should the app keep the previous version when a provider rejects the new one? This plan does not add that behavior.
8. **Old keys in logs.** Confirm whether old keys were ever logged. The 30-day retention bounds the exposure after revocation, but it does not undo any earlier leak.
9. **Probe paths.** Confirm that readiness stays on `/healthz`, or moves to a new path. Name the liveness path. Update the cluster probe configuration to match.
10. **Pod identity.** The brief names the identity `orders-api-prod`, but not how a running pod proves to the secret store that it holds that identity. Confirm the mechanism before the access policy in step 2 is built.
11. **Environment and store identity.** Confirm where `APP_ENV` is set in prod, and how a pod gets the identity it uses to read the store.
12. **Read-only provider endpoint.** Name the provider endpoint that step 5 uses for its read-only check of a new key, for each of the three providers.
13. **Who runs a rollback.** The brief does not name the tool or command used to redeploy the previous image. Name the tool, and the person or role who runs it.
14. **Time limit for the crash loop.** This plan sets no time limit on a pod that crash-loops on a missing key. Decide whether it should page after a set time.