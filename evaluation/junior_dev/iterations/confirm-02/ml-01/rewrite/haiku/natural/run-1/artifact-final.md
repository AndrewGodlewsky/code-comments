# Recommendations API: serving, model versions and shadow testing

## What this is

The home page calls `GET /recommendations?user_id=...` and gets back 20 item IDs. Today these are precomputed each night into a table. This plan computes them for each request, from the latest features, using a trained model. A new model version first runs in shadow on 10% of users. Shadow means it does its work and logs the result, but no user sees it. A version can become active only after 7 days in shadow, passing an error-rate gate and a latency gate, and with approval from the ML lead. If anything fails on the request path, the response falls back to a daily popular-items list. The fallback keeps the whole call inside its 150 ms budget, and shadow runs off the request path so it cannot slow a user.

Rules that hold everywhere:

- The whole call has a p99 budget of 150 ms.
- Exactly one model version is active at a time. Switching or rolling back changes config, not code, so the API is not redeployed.
- A version never runs, in shadow or as active, on features the online store does not have.
- Shadow output is never shown to a user, and shadow never slows or breaks a response.

## Parts and terms

- **API service**: stateless instances behind the gateway (the front door that routes requests to them). Each instance keeps an in-memory copy of the serving config and of the model versions it has loaded.
- **Online feature store**: a key-value store keyed by user ID. It holds one feature bundle per user.
- **Feature bundle**: all of one user's features, written together as one value. It carries `materialized_at` (when it was written) and `feature_schema_version` (which feature list it follows).
- **Materialization job**: copies features from the warehouse (the large analytics store) into the online store, every hour.
- **Popular-items store**: one small key holding the 20 popular items, rewritten by a daily job.
- **Model registry**: stores each trained model version as an immutable, numbered record. The record holds the artifact location, the required-feature list with types, the input/output contract, the training data snapshot, offline metrics, gate results and the approver.
- **Required-feature list**: the features one model version needs in order to run.
- **Serving config store**: one record, `{active_version, shadow_version, shadow_percent, shadow_salt, revision}`.
- **Revision and compare-and-set**: every config write names the revision it was based on. If the stored revision has moved on, the write is refused. So two promoters cannot both win.
- **Shadow salt**: a fixed string mixed into the user hash, so shadow membership is stable. Keep it fixed for an experiment, because changing it reshuffles users.
- **Bucket**: a number from 0 to 99 for each user, computed from the salt and the user ID. The same user always gets the same bucket.
- **Control plane**: the only path that changes serving config. It enforces the promotion gates and records who approved.
- **Shadow queue and shadow workers**: a bounded in-memory queue, and a separate pool of workers that drain it. They have their own capacity and a circuit breaker (a switch that stops calls to a failing component for a while).
- **Shadow results store**: an append-only log. User IDs are hashed in it.

The request path and the shadow path:

```
GET /recommendations
  -> read feature bundle (30 ms limit)
       -> fresh and complete -> active model -> 20 items ----+
       -> anything else      -> popular items (fallback)  ---+--> response to user
  -> if user is in shadow cohort: copy to shadow queue (never blocks)
       -> shadow worker -> candidate model -> shadow results store
```

## Request path

**1. Receive the request and start the clock.**
- Trigger: the home page calls `GET /recommendations?user_id=...`.
- Data: `user_id` comes in. Nothing is written.
- State: none. The API records the start time for the 150 ms budget.
- Failure: a missing or malformed `user_id` returns 400. This is not a model failure.

**2. Read the feature bundle (30 ms limit).**
- Trigger: step 1 is done.
- Data: one read of the user's bundle from the online store.
- Failure, each one goes to fallback (step 4) with the reason shown:
  - Timeout or store error: `feature_timeout` or `feature_error`.
  - No bundle: `no_features`.
  - `now - materialized_at` is over 6 hours: `stale_features`. Features older than 6 hours count as missing.
  - Bundle present and fresh: go to step 3.

**3. Check features, then infer with the active version.**
- Trigger: a fresh bundle was found.
- Data: the active version's required-feature list is read from the cached config and the registry. Each required feature is checked against the bundle. Only the required features are passed to the model.
- Failure:
  - A required feature is missing from the bundle: do not call the model. Fallback, reason `missing_feature`. This is a second check. The first check is at registration (step 8).
  - Inference error, or inference running past about 90 ms (this leaves room for the rest of the 150 ms budget): fallback, reason `inference_error` or `inference_timeout`. The brief does not cover this case. The plan assumes fallback, which keeps the 150 ms p99. Confirm with product.
  - Output is not exactly 20 unique item IDs: treat as an error and fall back.
  - Success: go to step 5.

**4. Fallback.**
- Trigger: any failure in steps 2 or 3.
- Data: read the popular-items key.
- Response: 20 popular items, `fallback=true`, `fallback_reason`, and the active version ID that was in effect.
- Failure: if the popular-items key is missing or unreadable, serve the last copy this instance read successfully, which it keeps in memory. If there is no such copy, return an empty list with `fallback=true` and raise an alert. The brief does not cover this case. It is flagged.

**5. Respond, then queue the shadow event.**
- Trigger: a model response is ready.
- Data: the response goes to the client first. Then, only if the user is in the shadow cohort (see step 12), an event goes on the queue. The event holds `request_id`, the hashed `user_id`, the feature bundle exactly as read in step 2 (its `materialized_at` and the values used), the active version ID, and the 20 active items.
- State: the queue lives in memory on the API instance and has a fixed size. Adding to it is a non-blocking attempt.
- Failure: if the queue is full, drop the event and increment a counter. The user's response does not change.

## Feature freshness

**6. Materialize features every hour, one user at a time.**
- Trigger: the hourly schedule.
- Data: the warehouse produces a snapshot. The job writes each user's whole bundle as one value, with a new `materialized_at`. A bundle is never split across keys, so a user never sees features from two runs mixed together.
- State: the online store holds the latest bundle per user. An old value is overwritten only after the new value for that key is written. A failed run therefore leaves the old bundles in place.
- Failure:
  - The job fails partway: users already written have new bundles, and the rest keep old ones. Each bundle's own timestamp decides whether it is still valid. Nothing is deleted.
  - The job fails for more than 6 hours: every bundle is stale, so all requests fall back. Alert on materialization lag at 2 hours, so there is time to act before the 6-hour cutoff.
  - The store is unreachable during a write: the job retries, then alerts. Serving continues on the old bundles.
  - A single failed run is tolerated, because bundles reach about 2 hours old before the next success. Two consecutive failures put users into fallback, as first drafted. This conflicts with the 6-hour rule. See open questions.

**7. Keep the feature catalog.**
- Trigger: a model version is registered, or the feature schema changes.
- Data: the catalog lists each feature's name, its type, and the `feature_schema_version` it appears in.
- State: the catalog lives in the registry and in the online store's metadata.
- Failure: a feature removed from materialization is flagged in the catalog. Any version that requires it becomes ineligible for promotion and for shadow (see step 8).

## Model versions and switching

**8. Register a version and check eligibility.**
- Trigger: training finishes, or a candidate is proposed.
- Data: the registry record is written once and never edited. The control plane compares the version's required-feature list with the catalog.
- State: the record is immutable. Eligibility is computed and stored with it.
- Failure: any required feature missing from the catalog marks the version `ineligible`. An ineligible version cannot be set as shadow or active. Its record is kept for reference.

**9. Write the serving config.**
- Trigger: a control-plane action changes which version is active, which is in shadow, or the shadow percentage.
- Data: the new config is written with compare-and-set on `revision`. The control plane checks that the target version exists and is eligible. For a promotion, it also checks the gates below.
- State: one config record. It has exactly one `active_version` at any time, by construction.
- Failure: a revision mismatch means another change won. The action re-reads the config and retries. Nothing is applied twice.

**10. Each API instance loads config and versions.**
- Trigger: the config record changes, or the instance polls it every 15 seconds as a backup.
- Data: the instance reads the config. It loads any named version it does not yet have from the artifact store, and warms it with a test inference. It loads only the versions named in the config: the active one, and the shadow one if set. The previous active version stays loaded.
- State: an in-memory map of loaded versions. Pointers swap in memory. No restart.
- Failure:
  - A new version fails to load or to warm up: the instance keeps the previous active version and reports the failure. The config is not applied on that instance.
  - The config store is unreachable: the instance keeps its last known config. It does not fall back to popular items for this reason alone.
  - The instance reports its applied `revision` and `active_version`, so the control plane can confirm the switch.

**11. Confirm the switch across the fleet.**
- Trigger: after a config change.
- Data: each instance reports its applied revision. The control plane waits until every healthy instance reports the new revision, or until 60 seconds have passed.
- Failure: instances still on the old revision after 60 seconds raise an alert. They keep serving the previous version, which is still valid and eligible.

## Running shadow

**12. Choose the shadow cohort.**
- Trigger: each request that passes step 2 with fresh, complete features.
- Data: `bucket = hash(shadow_salt + user_id) mod 100`. The user is in shadow when `bucket < shadow_percent`. Use SHA-256 or another stable hash. Never use a language's built-in hash, which can change between runs. Keep `shadow_salt` fixed for the life of an experiment.
- Behaviour: a user is always in or always out. Shadow runs only when all the candidate's features are present and fresh. Fallback users run no model, so they get no shadow. The 10% therefore means 10% of users who have features, which is what the shadow logs measure.
- Failure: if the candidate is `ineligible` or not loaded, skip shadow and log `shadow_skipped` with the reason.

**13. Run the candidate in shadow, off the request path.**
- Trigger: a shadow worker takes an event from the queue.
- Data: the worker runs the candidate on the feature bundle captured in step 5, not on a fresh read. Both models then see the same inputs. The result, with the active items, is written to the shadow results store.
- State: shadow workers use their own thread or process pool, separate from the request path. Each call has a timeout, for example 200 ms, and a circuit breaker. The results store is append-only.
- Failure:
  - Candidate error, timeout or invalid output: logged as a shadow error. Nothing is returned to any user.
  - Queue full or worker pool saturated: events are dropped and counted. The sampling rate then reads lower than configured.
  - Kill switch: set `shadow_percent` to 0 through step 9. Workers drain and stop. No redeploy is needed.
  - If active p99 rises while shadow runs, cap or stop the shadow pool. Shadow has separate capacity, so this should not happen. Step 14 checks it.

**14. Compare and monitor shadow results.**
- Trigger: a daily scheduled aggregation, plus live dashboards.
- Data, per day and in total:
  - the count of shadow-eligible requests;
  - the candidate's error rate (errors, timeouts and invalid outputs, over candidate calls);
  - the candidate's inference p99;
  - agreement between the candidate's 20 items and the active 20 (overlap at 20, and rank correlation);
  - coverage of the item catalog;
  - spread of recommendations across users.
- Health check on the active path during shadow: active p99 and error rate, before and after shadow was turned on, in the same window.
- State: aggregates are kept in the results store. Raw rows are kept per the retention policy.
- Failure: a day whose count of shadow-eligible requests falls below the agreed minimum does not count toward the 7-day window.

## Promotion and rollback

**15. Check the promotion gates.**
- Trigger: a promotion request for the candidate.
- Data: the control plane reads the shadow aggregates and the registry record.
- All of these must pass:
  - At least 7 days in shadow, counting only days that met the minimum eligible-request count, with no gap that ended shadow.
  - Candidate error rate under 0.5% over the shadow window.
  - Candidate inference p99 under 80 ms over the shadow window.
  - The version is still eligible (step 8).
  - ML lead approval is recorded in the registry, with the approver's identity and a timestamp.
- Failure: any missing gate blocks the promotion, and the result names the gate. The brief does not say what happens when shadow stops for more than a day. This plan counts that day as not qualifying, and does not reset the whole count. Confirm with the ML lead.

**16. Switch the active version.**
- Trigger: the gates pass and approval is recorded.
- Data: the control plane writes the config (step 9) with `active_version` set to the candidate, and clears the shadow slot.
- State: the previous active version stays in the registry and stays loaded on instances, ready for rollback.
- Failure: the promotion is marked complete only after the switch is confirmed across the fleet (step 11).

**17. Roll back.**
- Trigger: a manual decision, or an automated alert on the active version (error rate or latency above its threshold).
- Data: the config is set back to the previous version. That version is still loaded on each instance and still in the registry, so no download is needed.
- State: the same config record and compare-and-set path as step 9.
- Timing: polling and the config watch apply the change within 1 minute. The control plane confirms it (step 11).
- Approval: rollback does not need ML lead approval. Promotion does. The plan recommends this split. Confirm it.
- Last resort: a serving mode of `popular_only` in the config makes every request use the popular-items list, with no model call. It is also a single config write.

## Keeping room for the undecided live A/B step

Product has not decided whether a live A/B test comes between shadow and the full switch. In a live A/B test, the candidate's recommendations are shown to a slice of real users. The other option is to go straight from shadow to 100%. This plan does not choose either one. It keeps both open.

**18. Serve from an allocation table.**
- The config is a list of rows: `(version, bucket range, mode)`. Mode is `serve` or `shadow`. Bucket ranges use the same hash as step 12.
- Shadow to 100% is one table: a shadow row at 10%, then a serve row for the candidate covering all buckets.
- A live A/B slice is a third layout: a serve row for the candidate on a bucket range, with the rest of the buckets on the active version. Product sets its size.
- Both layouts use the same mechanism and the same rollback (step 17). Nothing here chooses between them.
- Still undecided, and needed before the live step is built: the gate for a live slice (shadow gates alone, or extra user-facing metrics), the exposure logging needed to measure it, and the slice size.

## Open questions

1. Behaviour when inference runs past its deadline. The plan falls back to popular items, which matches the brief's rule for missing features. The brief does not cover this. Confirm with product.
2. Behaviour when the popular-items key is missing. The plan serves the last in-memory copy, then an empty list. The brief does not cover this.
3. Whether shadow may run for fallback users. The plan says no, since no model call happens for them.
4. How a gap in shadow days counts toward the 7-day window.
5. Whether rollback needs approval. The plan says no.
6. Two consecutive failed materialization runs are said to put users into fallback. The 6-hour staleness rule would allow about six hours of failed runs before that happens. Which rule should decide?
7. The live A/B decision (step 18).