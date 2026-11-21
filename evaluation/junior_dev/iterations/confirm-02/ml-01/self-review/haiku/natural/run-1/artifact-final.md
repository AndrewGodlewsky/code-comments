# Recommendations API: serving, model versions and shadow testing

## What this plan does

Today, recommendations are computed once each night and stored in a table. The home page reads from that table. This plan replaces it with a service that computes recommendations for each request, using features that are at most a few hours old.

The plan also covers three related questions:

- **Shadow:** how a new model version runs on a copy of some real traffic. It computes results, but users never see them.
- **Activation:** how a version becomes the **active** one, the version that answers users.
- **Rollback:** how we return to the previous active version if something goes wrong.

Terms are defined in "Terms used in this plan," before the steps that use them. Anything marked **Proposed** is a design choice made in this plan. It is not a requirement from the brief.

## How the pieces fit together

- A user's home page calls the API. The API reads that user's feature row from the online feature store, runs the active model, and returns 20 item IDs. If something needed is missing, it returns the popular list instead.
- Once an hour, a materialization job copies features from the warehouse into the online store.
- A config service holds one routing record. It says which model version is active and which version, if any, is in shadow. Each API pod reads this record every 10 seconds.
- Model versions are stored in two places: a registry holds their metadata, and an artifact store holds the model files.
- For users in the shadow cohort, the API copies the inputs and output of each request into a queue. A separate shadow fleet runs the candidate model on those inputs and writes the results to an analytics store. Users never see that output.

## Scope and assumptions

- **One API service, scaled horizontally.** The service runs as several pods (identical running copies). Each pod holds no durable state. When a pod starts, it rebuilds what it needs from three places: the config service, the artifact store and the online store.
- **In memory per pod:** the routing config, the popular list and the loaded model weights.
- **One shadow candidate at a time.** This is an assumption to confirm.
- **Not decided:** whether a live A/B slice sits between shadow and the full switch. A live slice means showing a candidate's recommendations to some real users. This plan does not choose. See "Where the open decision attaches."

## Terms used in this plan

- **Feature:** one input value describing a user, such as a count or a category. Models use features to make predictions.
- **Feature row:** the single record the online store holds for one user. It contains all of that user's features, an `as_of` time and a `schema_version`.
- **`as_of`:** when the warehouse snapshot behind a feature row was taken. It is not when the row was written to the store.
- **Schema and `schema_version`:** a schema is the agreed layout of a feature row: which feature names exist and what they mean. The `schema_version` is the identifier for one such layout.
- **Store manifest:** the list of schema versions the online store currently serves.
- **Catalog:** the full set of items that can be recommended. Every ID in a response must be in the catalog.
- **Popular list:** 20 popular item IDs, recomputed daily. It is the fallback answer.
- **Fallback:** a response that returns the popular list instead of model output. It is marked `fallback: true` and gives a reason.
- **Active version:** the model version that answers user requests.
- **Shadow candidate:** a second model version that runs on a copy of some requests. Its output is stored for analysis and never shown to users.
- **Shadow cohort:** the users whose requests are copied to the shadow candidate.
- **Gate:** the set of checks a shadow candidate must pass before it can become active.
- **Compare-and-set (CAS):** a write that succeeds only if the stored `revision` number still equals the value the writer read. Each successful write increments `revision`. If two writers race, only one succeeds. The other must read the new revision and try again.
- **Fail static:** when a component cannot reach its source of truth, it keeps using its last good copy. It does not guess.
- **Warm set:** the model versions a pod has already downloaded and checked, so it can use them without downloading again.
- **Digest:** a fingerprint of a file's exact bytes, such as a SHA-256 hash. If the bytes change, the digest changes.
- **Circuit breaker:** a rule that stops calls to a failing dependency for a while, so requests fail fast instead of waiting.
- **Latency budget:** the whole `GET /recommendations` call must finish within 150 ms at the 99th percentile (p99). That means 99% of calls finish within 150 ms.
- **Enqueue:** add an event to the back of a queue for a later worker to process.
- **Orchestrator:** the scheduler that runs jobs on a timetable and records whether each run succeeded.

## Components and where state lives

| Component | State | Notes |
|---|---|---|
| Recommendations API | In memory only: routing config, loaded model versions, popular list | Rebuilt on restart from the config service, artifact store and online store |
| Config service | One `routing` record: `active_version`, `previous_active`, `shadow_version`, `shadow_salt`, `shadow_percent`, `mode`, `revision`, and an ordered list of exposure rules | Today the rule list has one rule: all users go to the active version. Every write is a CAS on `revision` |
| Model registry | Immutable version records (artifact digest, required features, feature schema, training run, code commit). Status and approvals are separate append-only events | A version record is never edited |
| Artifact store | Model weight files, keyed by digest | Read-only for the API |
| Online feature store | One feature row per user. Also holds the schema manifest and the popular list | Key-value store (a store that looks up a value by its key). Read by the API and the shadow fleet |
| Materialization job | Run status in the orchestrator | Runs hourly. Copies features from the warehouse into the online store |
| Shadow queue | Bounded queue of events. Each event holds: user ID, request ID, the feature row as read, active items, active fallback flag, active version, timestamp | Dropping events is allowed |
| Shadow fleet | Stateless workers in their own deployment | Writes results to the analytics store only |
| Analytics store | Shadow rows and daily gate reports | Retention proposed: 90 days for raw rows, longer for gate reports |

## Part A: Request path

### Step 1. Receive and validate the request

- **Starts when:** `GET /recommendations?user_id=...` reaches the gateway (the front door that routes web requests to services).
- **Data moves:** `user_id` from the query string.
- **State:** none.
- **On failure:** a missing or malformed `user_id` returns 400. The 150 ms budget starts here.

### Step 2. Read the routing config

- **Starts when:** every request. It reads the copy held in memory.
- **Data moves:** none on the request path. Each pod polls the config service every 10 s. Polls are spread out with random jitter so pods do not all poll at the same moment (proposed).
- **On failure:** if the config service is unreachable, the pod keeps its last good config (fail static). A new pod with no config yet returns fallback with reason `no_routing_config` and reports itself as not ready.

### Step 3. Look up features

- **Starts when:** after step 2. Skipped if `mode` is `fallback_only`.
- **Data moves:** one key-value read per user. It returns the whole feature row: all features, `as_of` and `schema_version`. It does not return only the columns the active model uses. A shadow candidate may need other columns. Shadow must use the same row as the response, so both see identical inputs.
- **Budget:** 30 ms hard timeout.
- **What counts as missing or invalid:**
  - No row for the key: **missing**.
  - `as_of` more than 6 h before the API's clock: **missing (stale)**.
  - `as_of` more than 5 min after the API's clock: **invalid**, so treated as missing. The 5 min allowance for clock skew is proposed.
  - `schema_version` not in the store manifest: the row cannot be used by any model that needs that schema.
- **Circuit breaker (proposed):** after 5 timeouts within 10 s, the API stops calling the store for 10 s and goes straight to fallback. This keeps responses inside 150 ms while the store is down.
- **On failure:** a timeout, a missing row or a stale row sends the request to fallback (step 4). The model is not called.

### Step 4. Decide between the model and fallback

- **Compatibility check for the active model:** every required feature must be in the row, and the row's schema must be in the store manifest. If either check fails, return fallback with reason `feature_contract_mismatch` and raise an alert. This should not happen in normal operation.
- **Fallback:** return the popular list, with `fallback: true` and a reason. The popular list is recomputed daily, held in memory and refreshed hourly.
  - If it cannot be read, serve the last cached copy.
  - If none was ever loaded, serve a static list bundled with the API build (proposed).

### Step 5. Run the active model

- **Starts when:** step 4 passes.
- **Data moves:** the feature row goes into the active model. The model returns ranked item IDs.
- **Deadline (proposed):** the smaller of two values:
  - 90 ms, or
  - the time left in the 150 ms budget, minus a 20 ms reserve for writing the response.
- **Output check:** the output must be exactly 20 distinct IDs, all in the catalog. If it is short or has duplicates, fill the missing slots from the popular list and set `fallback: true` with reason `partial_model_output`.
- **On failure:** an exception, a timeout, or output that is still invalid after filling gives popular fallback with reason `model_error` or `model_timeout`. Each case is counted and alerted on.

### Step 6. Return the response and enqueue the shadow event

- **Response:** `{ "items": [20 IDs], "fallback": bool, "reason": string or null, "model_version": "<active>" }`. The `model_version` field is for debugging. The home page does not need it.
- **Shadow enqueue:** happens after the response body is written. It happens only if the user is in the shadow cohort (step 14) and a shadow version is set. The event carries the feature row, the active items and the fallback flag. Shadow therefore uses exactly the inputs this response used.
- **On failure:** if the queue is full, or the enqueue does not finish within 1 ms, drop the event and increment a counter. Never block or retry on the request path.

## Part B: Feature freshness

### Step 7. Run materialization hourly

- **Starts when:** the hourly schedule in the orchestrator.
- **Data moves:** warehouse snapshot, then transformation, then one write per user to the online store. Each row carries its `as_of` (the snapshot time) and its `schema_version`.
- **State:** run status lives in the orchestrator. The online store holds only the rows.
- **On failure:** retry with backoff (waiting longer before each retry), up to 3 attempts (proposed). Alert if no run has succeeded for 90 minutes (proposed).

### Step 8. Validate, then publish

- **Validation before any write (proposed):**
  - the row count is within a band around the previous run's count;
  - the null rate (share of missing values) for each feature is below a threshold;
  - the schema matches the declared version.
- **Write atomicity:** each user's row is written with one key write. So each user sees either the old row or the new row, never a mix. If a run stops partway, some users keep older rows than others. Step 9 handles this. No consistency across users is needed.
- **Schema changes:** during a migration, the new `schema_version` is written next to the old one. The manifest lists the active schema versions. A schema is removed only when no registered model that could still be active or previous needs it.
- **On failure:** a failed validation stops the run before any write, so the previous rows stay in place. Raise an alert.

### Step 9. Serve through a failed materialization

- A failed run leaves the previous rows in place. Each row keeps being served until its `as_of` is 6 h old. After that, it counts as missing (step 3), and responses fall back to the popular list.
- **Alerts (proposed):** warn 2 h after the last successful run, and page at 4 h. The fallback rate on the dashboard should rise before rows expire at 6 h.

## Part C: Model versions and switching

### Step 10. Register a model version

- **Starts when:** a training run is approved for registration.
- **Data moves:** the model file is uploaded to the artifact store. Then one registry record is created. The record holds the digest, `required_features`, `feature_schema`, the training data snapshot ID, the code commit and the owner.
- **State:** the registry. Records are immutable. Registering the same digest returns the existing record. A changed artifact gets a new version number.
- **Status:** a new record starts as `registered`. Later status changes are added as separate events. They are never written into the record itself.
- **On failure:** if the upload fails, no record is created. The record is written only after the digest has been checked in the artifact store.

### Step 11. Check compatibility before any model runs

- **Rule:** a model may run for a user only if:
  - its `feature_schema` is in the store manifest, and
  - every name in `required_features` is present in that user's feature row.
- **Where the rule is checked:**
  - at registration, against the current store;
  - at promotion, against every day of the shadow window;
  - at pod load (step 12);
  - per request for the active model (step 4);
  - per event for the candidate (step 15).

### Step 12. Load versions onto pods without a redeploy

- **Starts when:** a pod reads a routing config that names a version it does not hold.
- **Data moves:** the model file goes from the artifact store to pod memory. The downloaded file is checked against its digest before the model is used.
- **Warm set:** a pod holds up to three versions:
  - the active version,
  - `previous_active`,
  - the shadow candidate.

  `previous_active` stays loaded, so a rollback needs no download.
- **On failure:** a download or digest error marks that version as unloadable on that pod. The pod keeps serving what it already has. It reports its loaded set to the config service.
- **Assumption:** three model versions fit in pod memory. This must be checked against real model sizes.

### Step 13. Switch the active version

- **Starts when:** an operator or automation calls the switch with a target version and an approval reference (step 19).
- **Data moves:** one config write sets `active_version` to the target, sets `previous_active` to the old active version, and increments `revision`.
  - The write is a CAS: it succeeds only if the `revision` it expects is still current. So two switches running at the same time cannot both succeed.
- **Pre-warm rule (proposed):** the write is refused unless the target version is reported as loaded and verified on at least 99% of healthy pods. This keeps the active pointer single and stops pods from serving a version they have not loaded.
- **Propagation:** pods pick up the new revision within one poll interval (about 10 s). For a few seconds, some pods may still serve the old version. Each response carries `model_version`, so this mix can be seen in the data. The pointer itself is still single.
- **On failure:** if the config service is down, the switch is refused and nothing changes. Pods keep serving their last good config.

## Part D: Shadow testing

### Step 14. Assign the shadow cohort

- **Starts when:** `shadow_version` is set in the routing config.
- **Rule:**
  1. Take the bytes of `shadow_salt` followed directly by `user_id`, both encoded as UTF-8, with nothing between them.
  2. Compute the SHA-256 hash of those bytes.
  3. Read the first 4 bytes of the hash as an unsigned integer, big-endian (most significant byte first).
  4. Take that integer mod 10000 (the remainder after dividing by 10,000).
  5. The user is in the cohort if the result is below `shadow_percent` × 100. For 10%, that means below 1000.
- **Why this exact recipe:** SHA-256 gives the same result on every pod and in every language. Built-in string hash functions do not. Fixing the byte order and encoding means every implementation agrees.
- **Stability:** a user's membership stays fixed while the salt stays fixed. Changing the salt reshuffles the cohort and restarts the shadow window.
- **On failure:** none expected, because the function is pure (same input, same output, no side effects). Test it with fixed input vectors.

### Step 15. Run shadow off the request path

- **Starts when:** step 6 enqueues an event for a cohort user.
- **Isolation:** the shadow fleet is a separate deployment with its own CPU and memory. Shadow load cannot slow down request inference.
- **Compatibility check first:** before running, the worker applies the step 11 check to the candidate against the event's feature row. If a check fails, it records `skipped_incompatible` with the missing feature names. It does not run the model.
- **Run:** the candidate runs with an 80 ms timeout, the same bound as the gate. Its output is checked the same way as in step 5.
- **Output boundary:** candidate output is written only to the analytics store. The response builder has no reference to it. A contract test checks this (see the test plan).
- **On failure:** an exception or timeout is recorded as an error. There is no retry. If queue lag exceeds 60 s (proposed), the worker discards the older events and counts them. If the shadow fleet crashes, the queue fills and requests drop events. No user sees any change.

### Step 16. Record shadow results

- **One row per event**, with these fields:
  - date, request ID, user ID;
  - active version, candidate version;
  - active items, and candidate items or error;
  - active latency, candidate latency;
  - active fallback flag;
  - candidate status: `ok`, `error`, `timeout`, `invalid` or `skipped_incompatible`;
  - feature schema version and the row's `as_of`.
- **No join needed:** each event already holds the active output, so comparison does not need the response log.
- **Writes:** batched to the analytics store every few minutes. Lost events shrink the sample but do not bias the rates. The gate counts candidate attempts and checks the sample size (step 18).
- **On failure:** if batch writes keep failing, the fleet stops consuming and the queue drops events. Raise an alert.

### Step 17. Compare daily

- **Starts when:** a daily job runs over the previous UTC day's rows, for the candidate and the active version.
- **Operational metrics:** error rate, invalid-output rate, timeout rate, candidate p50 and p99 latency, and the count of `skipped_incompatible`.
- **Agreement metrics**, excluding rows where the active output was a fallback:
  - overlap@20 (how many of the 20 items the two lists share);
  - rank correlation on shared items (whether the shared items appear in a similar order);
  - the share of candidate items that fall outside the active top 20;
  - catalog coverage across users (how much of the catalog the candidate recommends across all users).
- **Fallback comparison:** the fallback rate for the active version and for the candidate. Both use the candidate's attempts as the denominator, so the two rates cover the same users.
- **Output:** one gate report per day, stored in the registry against the candidate version.
- **Limit:** shadow cannot show whether users prefer the candidate's lists, because users never see them. Quality judgement rests on offline evaluation and these agreement metrics. The user-outcome comparison belongs to the open decision below.
- **On failure:** a failed job does not affect serving. Rerun it. A day with no report does not count toward the 7 days.

## Part E: Promotion and rollback

### Step 18. Evaluate the promotion gate

- **Starts when:** the daily job has produced reports for the most recent 7 full UTC days of shadow.
- **Pass conditions (all must hold):**
  - All 7 days are present, and each day has candidate attempts. A missing or empty day fails the gate.
  - Error rate is under 0.5%. Errors are error + timeout + invalid, divided by candidate attempts over the 7 days.
  - p99 candidate inference latency is under 80 ms over the 7 days.
  - `skipped_incompatible` is zero over the 7 days. Any skip means some users could not be evaluated, so investigate before passing.
  - At least 10,000 candidate attempts (proposed), so that the error rate and p99 are meaningful.
- **Failure:** if any condition fails, the candidate stays in shadow or is rejected. That choice is an operator decision. The gate uses a rolling window, so a clean 7-day run is needed after any failure. A failed gate has no effect on the active version.
- **Output:** a gate report with the figures, the query version and a report hash. A job generates it, not a person.

### Step 19. ML lead approval

- **Starts when:** a gate report passes.
- **Data:** an approval event in the registry. It holds the approver, version ID, gate report hash, timestamp and comment.
- **Rules:**
  - An approval names exactly one version and one gate report. A new report with a different hash needs a new approval.
  - Only the ML lead can approve in the registry (proposed).
  - Approvals expire after 14 days (proposed).

### Step 20. Activate

- **Starts when:** step 13 is called with an approval reference.
- **Checks made by the config service itself, not only by the UI:**
  - the approval exists and matches the version and the report hash;
  - the gate passed for the full 7 days;
  - the target is loaded on at least 99% of pods;
  - the compatibility check passes against the current store manifest;
  - the expected `revision` is still current.
- **On success:**
  - `active_version` becomes the candidate;
  - `previous_active` becomes the old active version;
  - `shadow_version` is cleared, unless another candidate has been set.
- **Watch window (proposed, 1 h):** compare the new active version's error rate, fallback rate and latency with its shadow figures. An alarm in this window can trigger a rollback.
- **On failure:** any failed check refuses the switch and changes nothing.

### Step 21. Roll back

- **Starts when:** an operator or an alarm calls rollback, or a live check fails after a switch.
- **Data moves:** one config write sets `active_version` to `previous_active`, sets `previous_active` to the version being removed, and increments `revision`. The same CAS rule applies. Pre-warm is already satisfied, because `previous_active` stays loaded on pods (step 12).
- **Timing:** about one poll interval (10 s) plus apply time. This is well under the 1-minute requirement. Run a rollback drill on staging for each release. Record the time from the call to the first response from the old version.
- **Compatibility re-check:** the previous version is checked against the current store manifest. If the check fails, rollback is refused and the kill switch (step 22) is used. The schema-removal rule in step 8 is meant to prevent this case.
- **On failure:** the config service is the single write point, so it needs high availability. Pods keep serving their last config while it is down.

### Step 22. Kill switch to popular fallback

- **Starts when:** the active model is causing harm and rollback is not enough, or the feature store is widely degraded.
- **Data moves:** one config write sets `mode` to `fallback_only`. Pods stop calling any model. Responses have `fallback: true` and reason `operator_disabled`. It takes effect within one poll interval.
- **Note:** this is a separate override. It does not change the active pointer, so clearing it restores the previous state.

## Where the open decision attaches

This plan does not choose between two options:

- **Option 1:** shadow, then 100%.
- **Option 2:** shadow, then a live A/B slice (a test where some real users see the candidate's recommendations), then 100%.

The plan keeps the request path, routing config and registry ready for either.

- **Routing:** the `routing` record already has an ordered list of exposure rules. Today it holds one rule: all users go to the active version. A live slice would be another rule, with its own salt and percentage. This should be a config change. Confirm it in design review.
- **Conflict to resolve:** a live slice makes two versions visible to users at once. The requirement "exactly one version is active at a time," as written, does not allow that. Product and the ML lead must decide whether a slice counts as an active version, or whether the requirement changes.
- **Gate:** whatever form exposure takes, the first user-visible exposure of a candidate needs the same 7-day gate and approval (steps 18 to 19). This plan does not relax the gate for a slice.
- **Logging:** every response and every shadow row carries an `arm` field, set to `active` for now. A later test can add values without a schema change.
- **Metrics:** comparing user outcomes is not defined here. It belongs to whichever exposure is chosen.

## Test plan

- **Contract test:** candidate output never appears in a response. The response builder has no import path to shadow output.
- **Load test:**
  - API p99 stays under 150 ms with shadow enabled at 10%;
  - and again with the feature store made to time out at 30 ms.
- **Store failures:**
  - store timeouts: the circuit breaker opens;
  - store fully down: fallback only;
  - materialization stopped: rows expire at 6 h and fallback takes over;
  - shadow fleet killed: no user-visible change;
  - config service unreachable: pods fail static.
- **Compatibility:** a candidate that requires a feature the store lacks never runs, in shadow or as active. It is recorded as `skipped_incompatible`.
- **Hash:** fixed input vectors give the same cohort on every pod and across restarts.
- **Switch and rollback drill:** measure the time from the rollback call to the first response from the old version. Target: under 60 s, measured on the real fleet.

## Open questions

1. Live A/B slice, or straight to 100%? And does a slice count as an active version? (Product and ML lead.)
2. Is a minimum shadow sample of 10,000 attempts right? (Proposed. Confirm with the ML lead.)
3. Is one shadow candidate at a time enough?
4. Do three model versions fit in pod memory?
5. Should a model error use the same popular fallback as a feature fallback? (Proposed: yes.)
6. How long should shadow rows be kept? They contain user IDs, so this needs a privacy review.