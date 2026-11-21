# Recommendations API: serving, model versions and shadow testing

## Scope and fixed decisions

- `GET /recommendations?user_id=...` returns 20 item IDs. The p99 budget for the whole call is 150 ms.
- Features come from the online feature store (key-value, keyed by user ID), filled hourly by a materialization job from the warehouse.
- Feature lookup budget is 30 ms. On timeout, or when the user has no features, the response is the daily popular-items list, marked `fallback=true`. The model is not called.
- Features older than 6 hours count as missing.
- Every trained model is an immutable, numbered registry version. Exactly one version is active at a time. Switching needs no API redeploy. Rollback takes effect within 1 minute.
- A candidate runs in shadow for the 10% of users chosen by a stable hash of user ID. Shadow output is never shown to a user and never delays or breaks a response.
- A model version never runs against features the online store does not have, in shadow or as active.
- Promotion of a candidate needs at least 7 days in shadow, error rate under 0.5%, p99 inference under 80 ms, and ML lead approval.
- **Not decided:** whether a live A/B slice sits between shadow and 100%, or whether shadow goes straight to 100%. This plan does not choose. Steps 6 and 8 keep both options open.

## Components

- **API service**: stateless instances behind the gateway. Each holds an in-memory cache of the serving config and of the loaded model versions.
- **Online feature store**: one bundle per user (all features written together), with a `materialized_at` timestamp and a `feature_schema_version`.
- **Popular-items store**: one small key holding the 20 daily popular items, rewritten by a daily job.
- **Model registry**: immutable version records. Each has an artifact URI, a required-feature list with types, the input/output contract, training data snapshot, offline metrics, and gate results.
- **Serving config store**: one record `{active_version, shadow_version, shadow_percent, shadow_salt, revision}`. Writes are compare-and-set on `revision`, so two promoters cannot both win.
- **Shadow queue and shadow workers**: a bounded queue and a separate worker pool, with their own capacity and circuit breaker.
- **Shadow results store**: append-only log, with user IDs hashed for analysis.
- **Control plane**: the only path that changes serving config. It enforces the promotion gates and records the approver.

## Request path

**Step 1. Receive and start the clock.**
- Trigger: home page calls `GET /recommendations`.
- Data: `user_id` in, no writes.
- State: none. The API records the start time for the 150 ms budget.
- Failure: malformed or missing `user_id` returns 400. It does not count against the model.

**Step 2. Read the feature bundle (30 ms deadline).**
- Trigger: step 1 completed.
- Data: one read of the user's feature bundle from the online store.
- Failure:
  - Timeout or store error: go to step 4 (fallback), reason `feature_timeout` or `feature_error`.
  - No bundle: fallback, reason `no_features`.
  - Bundle present but `now - materialized_at > 6h`: treat as missing, fallback, reason `stale_features`.
  - Bundle present and fresh: go to step 3.

**Step 3. Check feature coverage, then infer with the active version.**
- Trigger: fresh bundle found.
- Data: the active version's required-feature list (from the cached config and registry) is checked against the bundle. Only the required features are passed to the model.
- Failure:
  - Any required feature missing from the bundle: do not call the model. Go to step 4, reason `missing_feature`. This is a second line of defence behind the promotion check in step 8.
  - Inference error, or inference running past its deadline (about 90 ms, leaving room for the rest of the budget): go to step 4, reason `inference_error` or `inference_timeout`. The brief does not specify this case. This plan assumes fallback, which keeps the 150 ms p99. Confirm with product.
  - Output that is not exactly 20 unique item IDs: treat as an error and fall back.
  - Success: go to step 5.

**Step 4. Fallback.**
- Trigger: any failure in steps 2 or 3.
- Data: read the popular-items key.
- Failure: if the popular-items key is missing or unreadable, serve the last successfully read copy kept in process memory. If there is none, return an empty list with `fallback=true` and an alert. The brief does not cover this case. Flag it.
- Response: 20 popular items, `fallback=true`, `fallback_reason`, and the active version ID that was in effect.

**Step 5. Respond, then enqueue shadow.**
- Trigger: a model response is ready.
- Data: the response goes to the client. A shadow event is put on the bounded queue. The event holds `request_id`, `user_id` (hashed), the feature bundle as read in step 2 (its `materialized_at` and the values used), the active version ID, and the 20 active items.
- State: the queue lives in memory on the API instance, with a fixed size. Enqueueing is a non-blocking attempt.
- Failure: if the queue is full, drop the event and increment a counter. The user response is unchanged. Step 6 selects users for shadow. Step 6 skips the enqueue when the user is not in the shadow cohort.

## Feature freshness

**Step 6. Materialize features hourly, atomically per user.**
- Trigger: hourly schedule.
- Data: the warehouse produces a snapshot. The job writes each user's whole feature bundle as one value, with the new `materialized_at`. A bundle is never split across keys, so a user never sees features from two runs mixed together.
- State: the online store holds the latest bundle per user. Older values are overwritten only after the new value for that key is written, so a failed run leaves the old bundles in place.
- Failure:
  - Job fails partway: users already written have new bundles, the rest keep old ones. Each bundle's own timestamp decides whether it is still valid. Nothing is deleted.
  - Job fails for more than 6 hours: every bundle is stale. All requests fall back. Alert on materialization lag at 2 hours, so there is time to act before the 6-hour cutoff.
  - Store unreachable during the write: the job retries and then alerts. Serving continues on the old bundles.
- Note: a single failed run is tolerated (bundles reach about 2 hours old before the next success). Two consecutive failures put users into fallback.

**Step 7. Maintain the feature catalog.**
- Trigger: a model version is registered, or the feature schema changes.
- Data: the catalog lists each feature name, its type, and the `feature_schema_version` it appears in.
- State: the catalog lives in the registry and the feature store's metadata.
- Failure: a feature removed from materialization is flagged in the catalog. Any model version requiring it becomes ineligible for promotion and for shadow (see step 8).

## Model versions and switching

**Step 8. Register a version and check its eligibility.**
- Trigger: training finishes, or a candidate is proposed.
- Data: the registry record is written once and never edited. The control plane compares the version's required-feature list with the catalog.
- State: registry record (immutable). Eligibility is computed and stored with the record.
- Failure: any required feature missing from the catalog marks the version `ineligible`. It cannot be set as shadow or active. The record is kept for reference.

**Step 9. Publish serving config.**
- Trigger: a control-plane action that changes which version is active, which is in shadow, or the shadow percentage.
- Data: the new config is written with compare-and-set on `revision`. The control plane checks that the target version exists, is eligible, and (for promotion) has passed the gates in step 13.
- State: one config record. Exactly one `active_version` at any time, by construction.
- Failure: a revision mismatch means another change won. The action is retried after re-reading the config, and nothing is applied twice.

**Step 10. Pick up config and load versions in each API instance.**
- Trigger: the config record changes, or an instance polls it (every 15 seconds as a backstop).
- Data: the instance reads the config, loads any version it does not yet have from the artifact store, and warms it with a test inference. It loads only the versions named in the config (active, and shadow if set). The previous active version stays loaded.
- State: in-memory map of loaded versions. Pointers swap in memory. No restart.
- Failure:
  - New version fails to load or warm-up fails: the instance keeps the previous active version and reports the failure. The config is not applied on that instance.
  - Config store unreachable: the instance keeps its last known config. It does not fall back to popular items for this reason alone.
  - The instance reports its applied `revision` and `active_version`, so the control plane can confirm when the whole fleet has switched.

**Step 11. Confirm the switch across the fleet.**
- Trigger: after a config change.
- Data: each instance reports its applied revision. The control plane waits until every healthy instance reports the new revision, or until 60 seconds have passed.
- Failure: instances still on the old revision after 60 seconds raise an alert. Those instances keep serving the previous version, which is still a valid, eligible version.

## Running shadow

**Step 12. Select the shadow cohort.**
- Trigger: each request that passes step 2 with fresh, complete features.
- Data: `bucket = hash(salt + user_id) mod 100`. The user is in shadow when `bucket < shadow_percent`. Hash with SHA-256 or another stable function, never a language's built-in hash. Use a fixed `shadow_salt` for the life of an experiment. Changing the salt reshuffles users, so don't.
- Behaviour: the same user is always in or always out. Shadow runs only when the candidate's features are all present and fresh. For fallback users, no model runs, so no shadow runs. The 10% therefore applies to users with features, which is what the shadow logs will measure.
- Failure: if the candidate is `ineligible` or unloaded, skip shadow and log `shadow_skipped` with the reason.

**Step 13. Run the candidate in shadow, off the request path.**
- Trigger: a shadow event is taken from the queue by a shadow worker.
- Data: the worker runs the candidate on the feature bundle captured in step 5 (not a fresh read), so the active and candidate outputs compare the same inputs. The result is written to the shadow results store with the active items.
- State: shadow workers use their own thread or process pool, separate from the request path. They have a per-call timeout (for example 200 ms) and a circuit breaker. The shadow results store is append-only.
- Failure:
  - Candidate error, timeout, or invalid output: logged as a shadow error. Nothing is returned to any user.
  - Queue full or worker pool saturated: events are dropped and counted. The sampling rate is then reported as lower than configured.
  - Kill switch: set `shadow_percent` to 0 through step 9. Workers drain and stop. This needs no redeploy.
  - Shadow must not slow the active path: if active p99 rises while shadow runs, the shadow pool is capped further or stopped. Shadow runs on separate capacity, so this should not happen, but it is checked in step 14.

**Step 14. Compare and monitor shadow results.**
- Trigger: a scheduled daily aggregation, plus live dashboards.
- Data: per day and in total: count of shadow-eligible requests; candidate error rate (errors, timeouts and invalid outputs over candidate calls); candidate inference p99; agreement of the candidate's 20 items with the active 20 (overlap at 20, rank correlation); coverage of the item catalog; and spread of recommendations across users.
- Health checks on the active path during shadow: active p99 and error rate before and after shadow was turned on in the same window.
- State: aggregates in the results store. Raw rows kept per the retention policy.
- Failure: if the daily count of shadow-eligible requests falls below the agreed minimum, that day does not count toward the 7-day window.

## Promotion and rollback

**Step 15. Check promotion gates.**
- Trigger: a promotion request for the candidate.
- Data: the control plane reads the shadow aggregates and the registry record.
- Gates, all required:
  - At least 7 days of shadow, counted as days that met the minimum eligible-request count, with no gap that ended shadow.
  - Candidate error rate under 0.5% over the shadow window.
  - Candidate inference p99 under 80 ms over the shadow window.
  - Version eligibility (step 8) still true.
  - ML lead approval recorded in the registry: approver identity and timestamp.
- Failure: any missing gate blocks the promotion and states which one. The brief does not say what happens when shadow stops for more than a day. This plan counts that day as not qualifying and does not reset the whole count. Confirm with the ML lead.

**Step 16. Switch the active version.**
- Trigger: gates pass and approval is recorded.
- Data: the control plane writes the config (step 9) with `active_version = candidate` and clears the shadow slot.
- State: the previous active version stays in the registry and stays loaded on instances for rollback.
- Failure: the switch is confirmed fleet-wide (step 11) before the promotion is marked complete.

**Step 17. Roll back.**
- Trigger: a manual decision, or an automated alert on the active version (error rate or latency above its threshold).
- Data: the config is set back to the previous version, which is still loaded in each instance (step 10) and is still in the registry.
- State: the same config record and compare-and-set path as step 9.
- Timing: instances already hold the previous version, so no download is needed. Polling and the config watch apply the change within 1 minute, and the control plane confirms it in step 11.
- Approval: rollback does not need ML lead approval. Promotion does. This plan recommends that split. Confirm it.
- Last resort: a serving mode of `popular_only` in the config makes every request use the popular-items list, with no model call. It is also a single config write.

## Keeping room for the undecided A/B step

**Step 18. Model serving as an allocation table.**
- The config is written as a list of allocation rows: `(version, bucket range, mode)`, where mode is `serve` or `shadow`. Bucket ranges use the same stable hash as step 12.
- Shadow-to-100% is one table: a shadow row at 10%, then a serve row covering all buckets for the candidate.
- A live A/B slice would be a third layout: a serve row for the candidate on a bucket range, with the rest on the active version. Its size would be set by product.
- Either path uses the same mechanism and the same rollback (step 17). Nothing here chooses between them.
- What is undecided, and needs a decision before the live step is built: the gate for a live slice (shadow gates alone, or extra user-facing metrics), what exposure logging is needed to measure it, and the slice size.

## Open questions

1. Behaviour when inference runs past its deadline. This plan falls back to popular items, which matches the brief's rule for missing features.
2. Behaviour when the popular-items key is missing. This plan serves the last copy in memory, then an empty list.
3. Whether shadow may run for fallback users. This plan says no, since no model call happens for them.
4. How a gap in shadow days is counted toward the 7-day window.
5. Whether rollback requires approval. This plan says no.
6. The live A/B decision (see step 18).
