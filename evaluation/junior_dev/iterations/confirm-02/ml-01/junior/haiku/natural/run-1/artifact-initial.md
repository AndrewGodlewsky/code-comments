# Recommendations API: serving, model versions and shadow testing

## Scope and assumptions

This plan covers the path from `GET /recommendations?user_id=...` through the online feature store, model versions, shadow testing, promotion and rollback. It makes no choice on the live A/B test question. That gap is covered in its own section at the end.

Points the brief leaves open, marked **[Assumption]** where they are used. Each needs a yes or no before build:

1. **Freshness reference.** The 6-hour rule is measured from `source_as_of` (the warehouse snapshot time), not from the time the row was written. This is the stricter reading.
2. **Model deadline.** The brief sets no timeout for the model call. This plan sets an internal request deadline of 140 ms and gives the model whatever time remains.
3. **Invalid model output.** A response that is not exactly 20 unique catalog item IDs counts as a model error and triggers the fallback.
4. **Rollback needs no approval.** The previous version was already approved, so rollback is an operator action with no ML lead gate.
5. **Shadow drop limit.** At most 1% of eligible shadow samples may be dropped. Above that, the shadow window is invalid.

## Latency budget (p99, whole call: 150 ms)

| Stage | Budget | Enforcement |
|---|---|---|
| Gateway and API overhead | ~10 ms | Load balancer and API timeouts |
| Feature lookup | 30 ms | Hard deadline; timeout means fallback |
| Active model inference | Remainder of 140 ms internal deadline (gate: p99 under 80 ms) | Deadline; timeout means fallback |
| Validate, rank, serialize | ~10 ms | Code path, no I/O |
| Margin | ~20 ms | Unallocated headroom |

## Components and where state lives

| Component | Role | State |
|---|---|---|
| Recommendations API (stateless, many instances) | Orchestrates each request | In memory only: serving config cache and popular-items cache |
| Online feature store (key-value, keyed by user ID) | Serves per-user feature rows | Durable, replicated. One row per user holds all features plus `schema_version`, `source_as_of`, `materialized_at` |
| Materialization job (hourly) | Copies warehouse features into the online store | Stateless. Progress is visible in the store's per-row timestamps |
| Model registry | Immutable numbered versions, manifests, eligibility, approvals | Metadata in a relational table. Artifacts in an object store with write-once (object lock) |
| Serving config store | Active pointer and shadow configuration, with a revision number | Small strongly consistent record with revision history. Compare-and-set (CAS) writes |
| Inference pools | Active pool serves the active version. Shadow pool serves the candidate | Loaded model versions in memory. Both pools are separate deployments |
| Shadow queue and shadow worker | Runs the candidate off the request path | Bounded in-memory queue. Output written to a log |
| Popular-items job (daily) | Produces the fallback list | Versioned object. The previous day is kept |
| Warehouse (shadow and decision logs) | Comparison and gate evidence | Append-only tables |

## Part A: Request path

**1. Accept and validate the request**
- **Starts when:** `GET /recommendations?user_id=...` arrives.
- **Data moves:** `user_id` and a generated `request_id` for tracing.
- **State:** None.
- **On failure:** Missing or malformed `user_id` returns 400. If the popular-items cache is empty (only possible right after a cold start), the API returns 503 instead of an empty list.

**2. Read the serving config from the local cache**
- **Starts when:** Every request, after validation.
- **Data moves:** Active version ID, its feature manifest, shadow settings (candidate version, salt, percentage), and the config revision. All come from memory.
- **State:** Each instance polls the serving config store every 10 s and keeps the last good copy.
- **On failure:** If a poll fails, the instance keeps serving the last good config and raises an alert once the copy is older than 2 minutes. If no config has ever loaded, every request takes the popular-items fallback with reason `no_config`.

**3. Look up features with a 30 ms deadline**
- **Starts when:** Step 2 succeeds.
- **Data moves:** One key read (`user_id`). The whole row comes back, so the active model and any shadow candidate read the same snapshot.
- **State:** Online feature store.
- **On failure:** A timeout or store error sets the fallback reason `lookup_timeout` or `lookup_error`. The model is not called.

**4. Check freshness and compatibility**
- **Starts when:** A row is returned.
- **Data moves:** `source_as_of` and `schema_version` from the row, compared with the active manifest.
- **State:** Read only.
- **On failure:**
  - No row: fallback reason `no_features`. The model is not called.
  - `now - source_as_of` greater than 6 hours: the features count as missing. Fallback reason `stale_features`.
  - Row lacks a feature the active model requires: fallback reason `feature_mismatch`. This check is a safety net. Step 12 should already prevent it.

**5. Run the active model with the remaining deadline**
- **Starts when:** Step 4 passes.
- **Data moves:** The feature row to the active pool. Ranked item IDs come back.
- **State:** Active pool holds the active version in memory (see Part C).
- **On failure:** Timeout, transport error, or invalid output (not exactly 20 unique catalog IDs) gives fallback reason `model_error` or `model_timeout`.

**6. Hand off to shadow after the decision (non-blocking)**
- **Starts when:** The active response is decided. It is enqueued after the response bytes are written, so it adds no latency.
- **Data moves:** A sample: `request_id`, `user_id`, the feature row, active item IDs, and the config revision. Only if the user is in the shadow cohort (Part D, step 17) and the candidate's manifest is satisfied by the row.
- **State:** Bounded in-memory queue per instance.
- **On failure:** If the queue is full, the sample is dropped, a counter goes up, and nothing waits. Nothing in shadow can change the user's response.

**7. Return the response**
- **Starts when:** Step 5 succeeds, or any fallback condition in steps 2 to 5 fires.
- **Data moves:**
  - Normal: `{ "items": [20 IDs], "fallback": false, "model_version": "v<active>" }`
  - Fallback: `{ "items": [20 popular IDs], "fallback": true, "fallback_reason": "<reason>" }`
- **State:** The popular list comes from the in-memory cache. It does not depend on the feature store or the model.
- **On failure:** If the popular cache is empty, return 503.

## Part B: Feature freshness

**8. Hourly materialization**
- **Starts when:** The hourly schedule fires.
- **Data moves:** Warehouse feature snapshot to the online store. Each user gets one row: `{features, schema_version, source_as_of, materialized_at}`.
- **State:** Online feature store. The job holds no state of its own.
- **On failure:**
  - Writes are per key and idempotent, so re-running is safe.
  - A partial run leaves mixed freshness. This is acceptable because every row carries its own timestamp and is checked on read.
  - The job retries with backoff. An alert fires when no successful run has finished for 90 minutes.
  - Serving is unaffected by the job's failure.

**9. Enforce the 6-hour rule on read, not by TTL**
- **Starts when:** Every feature read (step 4).
- **Data moves:** None beyond step 4.
- **State:** The store keeps rows for 24 hours so storage is cleaned up. That TTL is not the freshness rule.
- **On failure:** If materialization stops, rows age. Once a row passes 6 hours it counts as missing, and users move to the fallback one by one. The fallback rate by reason is on the dashboard, and an alert fires when `stale_features` exceeds an agreed threshold.

**10. Daily popular-items list**
- **Starts when:** The daily schedule fires.
- **Data moves:** Interaction data produces 20 catalog item IDs. Written as a new versioned object.
- **State:** Object store (versioned). The API loads the newest object into memory every 5 minutes.
- **On failure:** The job keeps the previous day's list. An alert fires when the list is more than 36 hours old. The API keeps serving the last good list.

## Part C: Model versions and switching

**11. Register a trained version (immutable)**
- **Starts when:** A training run completes.
- **Data moves:** Model artifact, SHA-256 checksum, and a manifest: required feature names and types, `schema_version`, output contract (20 catalog IDs), training data reference, and metrics.
- **State:** Artifact written once to the object store with object lock. Registry row status `registered`. A version number is never reused. Changing a model means a new number.
- **On failure:** A failed registration leaves no version behind, or a version with status `incomplete` that cannot be activated or shadowed. Nothing is overwritten.

**12. Check eligibility against the online store**
- **Starts when:** Registration, and again whenever the store's feature schema changes.
- **Data moves:** The version's manifest compared with the store's current schema for the features it needs.
- **State:** `eligible` flag and reason in the registry.
- **On failure:** An ineligible version cannot be placed in shadow or made active. A candidate that needs a feature not yet in the store stays ineligible until materialization writes that feature. A request-time check in step 4 also refuses any row that lacks a required feature.

**13. Update the serving config with CAS**
- **Starts when:** An operator (or the promotion tool, Part E) writes a change.
- **Data moves:** `{active_version, shadow: {version, salt, percentage, started_at}, revision}`.
- **State:** Serving config store. Each write names the revision it expects. If the revision has changed, the write is rejected and must be re-read.
- **On failure:** Validation rejects an active version that is unregistered, ineligible, or not approved. Shadow is rejected when the candidate is ineligible. No partial state is written.

**14. Load and switch without redeploying the API**
- **Starts when:** An instance sees a new revision on its 10-second poll.
- **Data moves:** Artifact downloaded by version ID. Checksum verified. A warm-up inference runs before the swap.
- **State:** Each inference pool keeps the current version and the previous version resident. The swap is an atomic reference change.
- **On failure:** If a load or checksum fails, the instance keeps the previous version, marks the target as `failed` in the status table, and alerts. The switch is complete only when the control tool sees every active-pool instance report the new version loaded. The timeout is 2 minutes, after which the switch is reported as incomplete.

**15. Rollback in under 1 minute**
- **Starts when:** An operator writes a CAS revision that points `active` at the previous version.
- **Data moves:** The previous version ID from the history. No artifact is downloaded, because the previous version is still resident.
- **State:** Config store. Previous version resident in each pool.
- **On failure:** If the previous version is no longer resident, the load path in step 14 runs, which still fits in the budget for a small model. **[Assumption]** Budget: 10 s poll, under 5 s swap, under 30 s confirmation. Total well under 1 minute.

## Part D: Running shadow and comparing results

**16. Start shadow**
- **Starts when:** A CAS revision sets `shadow` to an eligible candidate, with a fresh salt and `percentage = 10`.
- **Data moves:** Shadow settings. `started_at` starts the 7-day clock.
- **State:** Config store and registry status `shadow`.
- **On failure:** Changing the candidate, salt, or percentage restarts the clock. Shadow never affects the request path.

**17. Assign the shadow cohort**
- **Starts when:** Every request, at step 6.
- **Data moves:** None. The cohort is a pure function: `bucket = hash(salt, user_id) mod 10000`, and the user is in the cohort when `bucket < 1000`.
- **State:** None. The salt is fixed for the whole window, so a user is always in or always out.
- **On failure:** None. Users with no usable features never get a shadow run, so the effective sample is smaller than 10%. The comparison reports this coverage.

**18. Run the candidate off the hot path**
- **Starts when:** A sample is dequeued by the shadow worker.
- **Data moves:** The feature row goes to the shadow pool, which runs the candidate with a 500 ms deadline. The output is compared with the active output.
- **State:** The shadow pool is a separate deployment with its own concurrency limit. When the active pool is busy, shadow load is shed first.
- **On failure:**
  - Timeouts, errors and invalid outputs are counted as candidate failures.
  - A crash in the shadow pool does not touch the active pool.
  - A full queue drops the sample. Drops are counted separately and are not counted as attempts.

**19. Log and compare**
- **Starts when:** Every shadow attempt, and a daily comparison job.
- **Data moves:** Per sample: `request_id`, `user_id`, active items, candidate items, candidate inference time, status (`ok`, `timeout`, `error`, `invalid`), drop reason, and `source_as_of`. Both models saw the same row, so comparisons are fair.
- **State:** Log stream, then a warehouse table.
- **On failure:** Log loss is tolerated but measured. The daily job reports overlap at 20 (active versus candidate), candidate error rate, candidate p99 inference time, drop rate, and eligible coverage. If the drop rate is above 1%, the window is marked invalid.

## Part E: Promotion and rollback

**20. Evaluate the gates**
- **Starts when:** The candidate has been in shadow for 7 full days.
- **Data moves:** Shadow aggregates from step 19. Gates:
  - At least 7 continuous days in shadow under one salt and one candidate.
  - Candidate error rate under 0.5% of attempts.
  - Candidate p99 inference time under 80 ms.
  - Drop rate at or under 1%.
  - The candidate was eligible for the whole window.
- **State:** Gate report stored in the registry with its hash.
- **On failure:** A failed gate leaves the candidate in shadow or moves it to `rejected`. Nothing is promoted automatically.

**21. ML lead approval**
- **Starts when:** The gate report passes.
- **Data moves:** Approval record: version ID, report hash, approver identity, timestamp. Approvals are tied to the immutable version.
- **State:** Registry.
- **On failure:** Without an approval record, activation (step 22) is refused.

**22. Activate**
- **Starts when:** An approved version is ready.
- **Data moves:** CAS revision: `active = candidate`, shadow cleared. The previous active version is kept as the rollback target.
- **State:** Config store, registry status `active`. The previous version becomes `retired` and stays resident and in the registry.
- **On failure:** Handled as in step 14.

**23. Watch after switching**
- **Starts when:** Each switch.
- **Data moves:** Active error rate, fallback rate by reason, and p99 latency per version.
- **State:** Dashboards and alerts.
- **On failure:** A regression leads to rollback (step 15). Automatic or manual rollback is a choice to make before launch.

**24. Retention**
- **Starts when:** A version is retired.
- **Data moves:** None.
- **State:** Artifacts and manifests are kept for the retention period. They are never deleted while they are the rollback target.
- **On failure:** Not applicable.

## Part F: The open gap (live A/B test versus straight to 100%)

Product has not chosen between a live slice (showing the candidate to a share of real users) and going straight from shadow to 100%. This plan does not choose either. It is built so that both remain possible.

- **Config shape.** The serving config is a list of serving entries, each with a version, a percentage, and a salt. Today it holds one entry at 100%. A slice adds an entry without changing the request path. Shadow stays a separate field.
- **Gate for a slice.** Step 20 covers only activation. A slice needs its own gate: guardrail metrics, minimum sample size, duration, and a stop rule. Product has not defined these.
- **Conflict with the invariant.** The brief says exactly one version is active at a time. A live slice serves two versions, so either the slice arm is a separate status (for example `experiment`) that is not `active`, or the invariant is relaxed. This must be decided before any slice is built.
- **Separate salt.** A slice would use its own salt, independent of the shadow salt, so the two cohorts are not correlated.
- **Rollback.** Removing a slice is a CAS revision that drops the entry. It meets the same 1-minute target as step 15.
- **Limit of shadow.** Shadow measures agreement and reliability, not user outcomes. Whether shadow alone is enough evidence is the question product has to answer.

## Decisions needed before build

1. Freshness reference: `source_as_of` or `materialized_at` (assumption 1).
2. Model deadline and fallback on model timeout (assumption 2).
3. Whether invalid model output counts as a fallback (assumption 3).
4. Whether rollback needs an approval (assumption 4).
5. The shadow drop limit (assumption 5).
6. The live A/B decision, and how it reconciles with "exactly one active."
