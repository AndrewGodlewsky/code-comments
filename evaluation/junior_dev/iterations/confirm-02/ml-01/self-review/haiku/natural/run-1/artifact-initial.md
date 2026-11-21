# Recommendations API: serving, model versions and shadow testing

## Scope and assumptions

- One API service, horizontally scaled. Pods hold no durable state. They keep config, popular items and loaded model weights in memory and rebuild them from the config service, the artifact store and the online store.
- One shadow candidate at a time. This is an assumption to confirm.
- "Proposed" marks a design choice made here. It is not a stated requirement.
- Not decided: whether a live A/B slice sits between shadow and the full switch. This plan does not choose. See "Where the open decision attaches".

## Components and where state lives

| Component | State | Notes |
|---|---|---|
| Recommendations API | In memory only: routing config, loaded model versions, popular list | Rebuilt on restart from the config service, artifact store and online store |
| Config service | One `routing` record: `active_version`, `previous_active`, `shadow_version`, `shadow_salt`, `shadow_percent`, `mode`, `revision` | Every write is compare-and-set on `revision` |
| Model registry | Immutable version records (artifact digest, required features, feature schema, training run, code commit). Status and approvals are separate append-only events | A version record is never edited |
| Artifact store | Model weights, keyed by digest | Read-only for the API |
| Online feature store | One value per user: features, `as_of`, `schema_version`. Also a schema manifest and the popular list | Key-value store, read by the API and the shadow fleet |
| Materialization job | Run state in the orchestrator | Runs hourly |
| Shadow queue | Bounded queue of events: user ID, request ID, feature row as read, active items, active fallback flag, active version, timestamp | Dropping events is allowed |
| Shadow fleet | Stateless workers in their own deployment | Writes results to the analytics store only |
| Analytics store | Shadow rows and daily gate reports | Retention proposed: 90 days for raw rows, longer for gate reports |

## Part A: Request path

### Step 1. Receive and validate the request
- **Starts when:** `GET /recommendations?user_id=...` reaches the gateway.
- **Data moves:** `user_id` from the query string.
- **State:** none.
- **On failure:** a missing or malformed `user_id` returns 400. The 150 ms deadline starts here.

### Step 2. Read the routing config
- **Starts when:** every request, from the in-memory copy.
- **Data moves:** none on the request path. Pods poll the config service every 10 s with jitter (proposed).
- **On failure:** if the config service is unreachable, pods keep the last good config (fail static). A cold pod with no config yet returns fallback with reason `no_routing_config` and reports itself not ready.

### Step 3. Look up features
- **Starts when:** after step 2, unless `mode` is `fallback_only`.
- **Data moves:** one key-value read per user. It returns the whole row (all features, `as_of`, `schema_version`), not only the active model's columns. The shadow candidate may need other columns, and shadow must use the same snapshot as the response.
- **Budget:** 30 ms hard timeout.
- **Row rules:** a missing key counts as missing. An `as_of` more than 6 h before the API clock counts as missing. An `as_of` more than 5 min in the future (proposed skew allowance) counts as invalid and therefore missing. A `schema_version` not in the store manifest makes the row unusable for any model that needs that schema.
- **Circuit breaker (proposed):** after 5 timeouts in 10 s, skip the lookup for 10 s and go straight to fallback. This keeps the response inside 150 ms while the store is down.
- **On failure:** timeout, missing or stale rows go to step 4's fallback path. The model is not called.

### Step 4. Decide between the model and fallback
- **Compatibility check for the active model:** every required feature must be present in the row, and its feature schema must be in the store manifest. If not, return fallback with reason `feature_contract_mismatch` and raise an alert. This should not happen in normal operation.
- **Fallback:** return the popular list, which is recomputed daily, cached in memory and refreshed hourly. The response has `fallback: true` and a reason. If the popular list cannot be read, serve the last cached copy. If none was ever loaded, serve a static list bundled with the API build (proposed).

### Step 5. Run the active model
- **Starts when:** step 4 passes.
- **Data moves:** feature row goes into the active model, which returns ranked item IDs.
- **Deadline (proposed):** the lesser of 90 ms and the remaining budget minus a 20 ms reserve for serialization and response writing.
- **Output check:** exactly 20 distinct IDs, all in the catalog. If the output is short or has duplicates, fill the missing slots from the popular list and set `fallback: true` with reason `partial_model_output`.
- **On failure:** exception, timeout or invalid output after filling gives popular fallback with reason `model_error` or `model_timeout`. Each one is counted and alerted on.

### Step 6. Return the response and enqueue the shadow event
- **Response:** `{ "items": [20 IDs], "fallback": bool, "reason": string or null, "model_version": "<active>" }`. `model_version` is for debugging. The home page does not need it.
- **Shadow enqueue:** happens after the response body is written, and only if the user is in the shadow cohort (step 14) and a shadow version is set. The event carries the feature row, the active items and the fallback flag, so shadow reuses the exact inputs of this response.
- **On failure:** if the queue is full or the enqueue does not finish within 1 ms, drop the event and increment a counter. Never block or retry on the request path.

## Part B: Feature freshness

### Step 7. Run materialization hourly
- **Starts when:** the hourly schedule in the orchestrator.
- **Data moves:** warehouse snapshot, then transformation, then one write per user to the online store. Each row carries `as_of` (the time of the warehouse snapshot, not the write time) and `schema_version`.
- **State:** run status lives in the orchestrator. The online store holds only the rows.
- **On failure:** retry with backoff, 3 attempts (proposed). Alert if no run has succeeded for 90 min (proposed).

### Step 8. Validate, then publish
- **Validation before any write (proposed):** row count within a band around the previous run, null rate per feature below a threshold, and schema matches the declared version.
- **Write atomicity:** each user's row is one key write, so each row is either old or new. Partial runs leave users with mixed freshness, which the 6 h rule handles. No cross-user consistency is needed.
- **Schema changes:** a new `schema_version` is written next to the old one during migration. The manifest lists the active schema versions. A schema is removed only after no registered model that could be active or previous_active needs it.
- **On failure:** a failed validation aborts the run before any write, so the previous rows stay in place. Raise an alert.

### Step 9. Serve through a failed materialization
- A failed run leaves the previous rows in place. Each row keeps serving until its `as_of` is 6 h old. After that it counts as missing (step 3), and the response falls back to popular items.
- Alerts (proposed): warn at 2 h since the last successful run, page at 4 h. The fallback rate on the dashboard should rise before rows expire at 6 h.

## Part C: Model versions and switching

### Step 10. Register a model version
- **Starts when:** a training run is approved for registration.
- **Data moves:** the model artifact is uploaded to the artifact store. Then one registry record is created with the digest, `required_features`, `feature_schema`, training data snapshot ID, code commit and owner.
- **State:** the registry. Records are immutable. Registering the same digest returns the existing record. A changed artifact gets a new version number.
- **Status:** starts as `registered`. Status changes are appended as events, never written into the record.
- **On failure:** if the upload fails, no record is created. The record is written only after the digest is verified in the artifact store.

### Step 11. Check compatibility before any model runs
- **Rule:** a model may run for a user only if its `feature_schema` is in the store manifest and every `required_features` name is present in that user's row.
- **Where it runs:** at registration (against the current store), at promotion (against every day of the shadow window), at pod load (step 12), per request for the active model (step 4), and per event for the candidate (step 15).

### Step 12. Load versions onto pods without a redeploy
- **Starts when:** a pod reads a routing config that names a version it does not hold.
- **Data moves:** artifact store to pod memory. The download is checked against the digest before the model is used.
- **Warm set:** a pod holds up to three versions: active, previous_active and shadow. previous_active stays loaded so that rollback needs no download.
- **On failure:** a download or digest error marks that version unloadable on that pod. The pod keeps serving what it already has, and reports its loaded set to the config service.
- **Assumption:** three model versions fit in pod memory. This needs checking against model size.

### Step 13. Switch the active version
- **Starts when:** an operator or automation calls the switch with a target version and an approval reference (step 19).
- **Data moves:** one config write sets `active_version` to the target, `previous_active` to the old active version, and increments `revision`. The write is compare-and-set: it succeeds only if the expected `revision` matches, so two concurrent switches cannot both succeed.
- **Pre-warm rule (proposed):** the write is refused unless the target version is reported loaded and verified on at least 99% of healthy pods. This keeps the pointer single and stops pods from serving a version they have not loaded.
- **Propagation:** pods pick up the new revision within one poll interval (about 10 s). For a few seconds some pods may still serve the old version. Each response carries `model_version`, so this skew can be seen. The pointer itself is still single.
- **On failure:** if the config service is down, the switch is refused and nothing changes. Pods keep serving the last good config.

## Part D: Shadow testing

### Step 14. Assign the shadow cohort
- **Starts when:** `shadow_version` is set in the routing config.
- **Rule:** a user is in the cohort when the first 4 bytes of SHA-256(`shadow_salt` + `user_id`), read as an unsigned integer, mod 10000 is below `shadow_percent` × 100. For 10%, that is below 1000. SHA-256 is used because it gives the same result on every pod and in every language, which a language's built-in string hash does not.
- **Stability:** a user's membership is fixed while the salt is fixed. Changing the salt reshuffles the cohort and restarts the shadow window.
- **On failure:** none expected, because the function is pure. Test it with fixed input vectors.

### Step 15. Run shadow off the request path
- **Starts when:** step 6 enqueues an event for a cohort user.
- **Isolation:** the shadow fleet is a separate deployment with its own CPU and memory. Shadow load cannot slow request inference.
- **Compatibility first:** before running, the worker applies step 11 to the candidate against the event's feature row. If a check fails, it records `skipped_incompatible` with the missing feature names and does not run the model.
- **Run:** the candidate runs with an 80 ms timeout (the same bound as the gate). The output is checked the same way as step 5.
- **Output boundary:** candidate output is written only to the analytics store. The response builder has no reference to it. A contract test checks this (see the test plan).
- **On failure:** an exception or timeout is recorded as an error, with no retry. If queue lag exceeds 60 s (proposed), discard the older events and count them. If the shadow fleet crashes, the queue fills and requests drop events. No user sees any change.

### Step 16. Record shadow results
- **Per event, one row:** date, request ID, user ID, active version, candidate version, active items, candidate items or error, active latency, candidate latency, active fallback flag, candidate status (`ok`, `error`, `timeout`, `invalid`, `skipped_incompatible`), feature schema version, and the row's `as_of`.
- **No join needed:** the event already holds the active output, so comparison does not need the response log.
- **Writes:** batched to the analytics store every few minutes. Lost events shrink the sample but do not bias the rates, because the gate counts candidate attempts and the sample size is checked (step 18).
- **On failure:** if batch writes keep failing, the fleet stops consuming and the queue drops events. Raise an alert.

### Step 17. Compare daily
- **Starts when:** a daily job runs over the previous UTC day's rows, for the candidate and the active version.
- **Operational metrics:** error rate, invalid output rate, timeout rate, candidate p50 and p99 latency, and count of `skipped_incompatible`.
- **Agreement metrics, excluding rows where the active output was a fallback:** overlap@20 (set overlap), rank correlation on shared items, share of candidate items outside the active top 20, and catalog coverage across users.
- **Fallback comparison:** fallback rate for the active version and for the candidate, using the same denominator (candidate attempts).
- **Output:** one gate report per day, stored in the registry against the candidate version.
- **Limit:** shadow cannot show whether users prefer the candidate's lists, because they are never displayed. Quality judgement rests on offline evaluation and these agreement metrics. The user-outcome comparison belongs to the open decision below.
- **On failure:** a failed job does not affect serving. Rerun it. A day with no report does not count toward the 7 days.

## Part E: Promotion and rollback

### Step 18. Evaluate the promotion gate
- **Starts when:** the daily job has produced reports for the most recent 7 full UTC days of shadow.
- **Pass conditions (all of them):**
  - All 7 days are present, and each day has candidate attempts. A missing or empty day fails the gate.
  - Error rate under 0.5%: (error + timeout + invalid) divided by candidate attempts over the 7 days.
  - p99 candidate inference latency under 80 ms over the 7 days.
  - `skipped_incompatible` is zero over the 7 days. Any skip means some users could not be evaluated, so investigate before passing.
  - Minimum sample of 10,000 candidate attempts (proposed), so the error rate and p99 mean something.
- **Failure:** if any condition fails, the candidate stays in shadow or is rejected (an operator decision). The gate uses a rolling window, so a clean 7-day run is needed after a failure. A failed gate has no effect on the active version.
- **Output:** a gate report with the figures, the query version and the report hash. A job generates it, not a person.

### Step 19. ML lead approval
- **Starts when:** a gate report passes.
- **Data:** an approval event in the registry with the approver, version ID, gate report hash, timestamp and comment.
- **Rules:** an approval names exactly one version and one gate report. A new report with a different hash needs a new approval. Registry permissions allow only the ML lead to approve (proposed). Approvals expire after 14 days (proposed).

### Step 20. Activate
- **Starts when:** step 13 is called with an approval reference.
- **Checks in the config service, not only in the UI:** the approval exists and matches the version and report hash; the gate passed for the full 7 days; the target is loaded on at least 99% of pods; the compatibility check passes against the current store manifest; the expected `revision` matches.
- **On success:** `active_version` becomes the candidate, `previous_active` becomes the old active version, and `shadow_version` is cleared unless another candidate is set.
- **Watch window (proposed 1 h):** compare the new active version's error rate, fallback rate and latency with its shadow figures. An alarm here can trigger rollback.
- **On failure:** any failed check refuses the switch with no change.

### Step 21. Roll back
- **Starts when:** an operator or an alarm calls rollback, or a live check fails after a switch.
- **Data moves:** one config write sets `active_version` to `previous_active`, sets `previous_active` to the version being removed, and increments `revision`. The same compare-and-set applies. Pre-warm is already satisfied, because previous_active stays loaded on pods (step 12).
- **Timing:** one poll interval (about 10 s) plus apply time, well under 1 minute. Test this in a rollback drill on staging for each release and record the time from call to first response from the old version.
- **Compatibility re-check:** the previous version is checked against the current store manifest. If the check fails, rollback is refused and the kill switch (step 22) is used. Step 8's schema-removal rule is meant to prevent this case.
- **On failure:** the config service is the single write point. It needs high availability. Pods keep serving their last config while it is down.

### Step 22. Kill switch to popular fallback
- **Starts when:** the active model is causing harm and rollback is not enough, or the feature store is widely degraded.
- **Data moves:** one config write sets `mode` to `fallback_only`. Pods stop calling any model, and responses have `fallback: true` and reason `operator_disabled`. It takes effect within one poll interval.
- **Note:** this is a separate override. It does not change the active pointer, so clearing it restores the previous state.

## Where the open decision attaches

The plan does not choose between shadow-to-full and shadow-to-A/B-to-full. It keeps the request path, routing config and registry ready for either.

- **Routing:** `routing` has an ordered list of exposure rules. Today it holds one rule: all users go to active. A slice would be another rule with its own salt and percentage. This should be a config change. Confirm it in design review.
- **Conflict to resolve:** a live slice makes two versions user-visible at once. The requirement "exactly one version is active at a time" does not allow that as written. Product and the ML lead must decide whether a slice counts as an active version or whether the requirement changes.
- **Gate:** whatever form exposure takes, the first user-visible exposure of a candidate needs the same 7-day gate and approval (steps 18–19). This plan does not relax the gate for a slice.
- **Logging:** every response and every shadow row carries an `arm` field, set to `active` for now. A later test adds values without a schema change.
- **Metrics:** user-outcome comparison is not defined here. It belongs to whichever exposure is chosen.

## Test plan

- **Contract test:** candidate output never appears in a response, and the response builder has no import path to shadow output.
- **Load test:** API p99 stays under 150 ms with shadow enabled at 10%, and with the store made to time out at 30 ms.
- **Store failures:** store timeouts (circuit breaker opens), store fully down (fallback only), materialization stopped (rows expire at 6 h and fallback takes over), shadow fleet killed (no user-visible change), config service unreachable (pods fail static).
- **Compatibility:** a candidate that requires a feature the store lacks never runs, in shadow or as active, and is recorded as `skipped_incompatible`.
- **Hash:** fixed input vectors give the same cohort on every pod and across restarts.
- **Switch and rollback drill:** time from rollback call to first response from the old version, target under 60 s, measured on the real fleet.

## Open questions

1. Live A/B slice or straight to 100%, and whether a slice counts as an active version (product and ML lead).
2. Minimum shadow sample of 10,000 attempts (proposed). Confirm with the ML lead.
3. Whether one shadow candidate at a time is enough.
4. Whether three model versions fit in pod memory.
5. Whether a model error should use the same popular fallback as a feature fallback (proposed: yes).
6. Retention of shadow rows, which contain user IDs, in the analytics store. This needs a privacy review.