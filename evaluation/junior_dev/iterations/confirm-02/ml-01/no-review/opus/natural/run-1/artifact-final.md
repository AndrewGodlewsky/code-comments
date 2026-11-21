# Recommendations API: serving, model versions and shadow testing

A numbered, end-to-end plan. Each step says what starts it, what data moves, where the state lives and what happens on failure. Section F lists the assumptions I made. Section E handles the open product decision without choosing an option.

## Components and shared state

| Component | Role | State it owns |
|---|---|---|
| **API service** | Serves `GET /recommendations`. Holds the serving config and the popular-items list in memory. | Nothing durable. All in-memory copies can be rebuilt. |
| **Online feature store** | Key-value store keyed by `user_id`. One record per user per feature group. | Feature values, plus `materialized_at` for each feature group. |
| **Feature catalog** | Lists which feature groups are materialized online, and when each last materialized successfully. | One row per feature group: `online`, `last_success_at`, `schema_version`. |
| **Model registry** | Holds immutable, numbered model versions. | One record per version: artifact URI, checksum, required feature groups and schema versions, training metadata, approval records. |
| **Serving config** | One record that says what runs. It lives in the registry database and is written by compare-and-set. | `revision`, `active_version`, `previous_version`, `preload_version`, `shadow_version`, `shadow_percent` (10), `shadow_salt`, `shadow_started_at`, `force_fallback`, plus an append-only change history. |
| **Inference service** | Runs the active model. Keeps the previous version loaded and ready. | The loaded models (in memory). Each instance reports the versions it has loaded and its config revision. |
| **Shadow queue and shadow pool** | A separate queue and separate hosts that run the candidate. | Queue messages. The shadow log. |
| **Response log and warehouse** | Logs every response, and joins active output with shadow output. | Response log, shadow log, daily shadow metrics. |

**Latency budget for the request** (p99, 150 ms in total): about 5 ms for routing and config, 30 ms hard timeout for the feature lookup, up to 100 ms for model inference (also capped by the remaining deadline), and about 15 ms margin for serialization and the network. The 80 ms p99 inference gate for promotion keeps active models inside this budget.

**Single source of truth for "active".** Version status (active, previous, shadow) comes only from the serving config. It is never stored on the version record as well. Because `active_version` is a single field, exactly one version is active at a time.

---

## A. Request path

### 1. Accept the request and fix its routing
- **Starts it:** The home page calls `GET /recommendations?user_id=...`.
- **Data:** `user_id` comes in. The API assigns a `request_id`, sets a deadline of start + 140 ms, and reads its in-memory snapshot of the serving config (step 13).
- **Shadow membership:** `in_shadow = shadow_version != null && hash(user_id, shadow_salt) mod 100 < shadow_percent`. The salt is fixed for the life of one candidate's shadow run, so a given user is always in or always out for that candidate.
- **State:** Memory only.
- **On failure:** A missing or invalid `user_id` returns 400. If `force_fallback` is set (step 23), skip to step 5 with reason `forced`.

### 2. Look up online features for the active model
- **Starts it:** Step 1.
- **Data:** One read for `user_id` that fetches only the feature groups listed in the active version's manifest. Candidate-only feature groups are never read on the user path, so the size and latency of this lookup do not depend on the candidate.
- **State:** Online feature store.
- **On failure:** The client timeout is 30 ms with no retry, because a retry cannot fit in the budget. A timeout, an error, or no record for the user goes to step 5 with reason `features_timeout`, `features_error` or `no_features`. The model is not called.

### 3. Check that features are fresh and complete
- **Starts it:** Step 2 returns.
- **Data:** Compare each feature group's `materialized_at` with now. A group older than 6 hours counts as missing. If any group the active version requires is missing, the user counts as having no features (assumption F1).
- **State:** Memory only.
- **On failure:** Go to step 5 with reason `features_stale` or `features_incomplete`. The model is not called.

### 4. Run the active model
- **Starts it:** Step 3 passes.
- **Data:** The feature vector goes to the inference service, tagged with `active_version`, and 20 or more ranked item IDs come back.
- **State:** The inference service holds the model in memory.
- **On failure:** The call timeout is `min(100 ms, deadline − now − 10 ms)`. A timeout, an error, or output that is not valid (fewer than 20 distinct known item IDs after padding is allowed, see step 5) goes to step 5 with reason `model_timeout` or `model_error`. Falling back on model failure is my addition. The brief names only feature failures, but the 150 ms budget needs some answer here (F2).

### 5. Build the response
- **Starts it:** Step 4 succeeds, or any fallback branch.
- **Data:** Model path: the first 20 distinct item IDs, with `fallback: false` and `model_version`. Fallback path: the first 20 IDs of the in-memory popular-items list (step 10), with `fallback: true` and `fallback_reason`. If the model returns fewer than 20 valid IDs, pad from the popular list and set `padded: true`. This keeps the response at 20 items without hiding that it was not purely model output.
- **State:** Memory only.
- **On failure:** If the popular list is not loaded, the instance is not ready (step 10), so the load balancer does not send it traffic.

### 6. Hand off to shadow (never blocks)
- **Starts it:** Step 5 is done and `in_shadow` is true. This runs after the response is written.
- **Data:** `{request_id, user_id, ts, active_version, active_items, fallback, fallback_reason, active feature materialized_at}` goes into a bounded in-memory buffer with a non-blocking add. A background thread serializes the buffered events and publishes them to the shadow queue.
- **State:** The API's in-memory buffer, then the shadow queue.
- **On failure:** If the buffer is full or the queue is unreachable, drop the event and count it as `shadow_dropped`. Nothing on this path can delay or fail the user's response: no awaits, no retries on the request thread, and a fixed memory cap.

### 7. Log the response
- **Starts it:** Step 5 is done, for every request.
- **Data:** Request ID, user ID, served version, items, fallback flag and reason, padded flag, latency of each stage, and the config revision. Sent through the same kind of non-blocking buffer to the log pipeline, then to the warehouse.
- **State:** Response log in the warehouse.
- **On failure:** Drop and count. Alert if more than 1% of events are dropped, because steps 16 and 21 depend on this log.

---

## B. Feature freshness

### 8. Hourly materialization
- **Starts it:** The scheduler, every hour.
- **Data:** Each feature group listed in the feature catalog is copied from the warehouse to the online store. Each user and group record is written together with its own `materialized_at`. When a group finishes, the job sets `last_success_at` for that group in the catalog.
- **State:** Online feature store and feature catalog.
- **On failure:** Records are written one at a time, so a partial run leaves some users fresh and some at the previous run's values. That is safe, because step 3 checks each record's age. The store's TTL must be well over 6 hours (for example 7 days), so old records stay available to fall back on. The 6-hour cutoff is enforced at read time in step 3, not by the TTL. One group can fail without blocking the others.

### 9. Monitor materialization failures
- **Starts it:** A group's `last_success_at` gets older than 1 h 15 m.
- **Data:** Alerts that read from the catalog.
- **State:** Feature catalog and alerting.
- **On failure:** Ticket at 2 hours behind. Page at 4 hours, which leaves 2 hours to fix it before records pass 6 hours and step 3 starts sending those users to fallback. Also alert if the fallback rate rises by reason `features_stale`, because that is the user-visible effect. Nothing is purged or rewritten. Serving continues on the stored values until they age out.

### 10. Daily popular-items list
- **Starts it:** The scheduler, daily.
- **Data:** A batch job computes the list (at least 20 IDs) and writes it as a new dated version of a single object. API instances check for a new version every 5 minutes, load it into memory, and swap it in.
- **State:** Versioned object storage, plus a copy in each API instance's memory.
- **On failure:** If the job fails, instances keep the last list they loaded, and the team gets an alert. The brief sets no maximum age for this list (F3). An instance that has never loaded a list, for example on a cold start while storage is down, does not report ready. A list with fewer than 20 IDs is rejected.

---

## C. Model versions and switching

### 11. Register a trained version
- **Starts it:** The training pipeline finishes a run.
- **Data:** The artifact is uploaded to write-once storage. The registry gives the version the next number and records its URI, checksum, required feature groups with schema versions, and training and evaluation metadata.
- **State:** Model registry and artifact storage. No field of a version record can be changed after it is written. Approvals and notes are separate records that point to the version.
- **On failure:** If the upload or checksum fails, the version is not registered. The pipeline can retry, and each retry gets a new number. Numbers are never reused.

### 12. Feature availability check
- **Starts it:** Any request to set a version as `shadow_version`, `preload_version` or `active_version`.
- **Data:** Compare the version's required feature groups with the feature catalog. Every group must have `online = true`, a matching `schema_version`, and `last_success_at` within 6 hours.
- **State:** Reads the registry and the catalog.
- **On failure:** Reject the config change and say which groups are missing. A candidate that needs new features first needs those groups added to materialization (step 8) and at least one successful run. The catalog also blocks removing or changing the schema of a group that the active, previous or shadow version requires. This keeps the warm rollback target from losing its features. This is the first of two guards. The second runs on every request (steps 3 and 15).

### 13. How instances pick up config changes
- **Starts it:** Each API and inference instance polls the serving config every 10 seconds.
- **Data:** If `revision` has changed, the instance applies the new snapshot. Inference instances load any version they do not yet hold (preload, active, previous), check its checksum, warm it up with synthetic requests, then point at the new `active_version` atomically. Each instance reports its `revision` and loaded versions in a heartbeat.
- **State:** Serving config (durable) and instance memory. Inference instances are sized to hold three models at once: active, previous and preload.
- **On failure:** If a load or checksum fails, the instance keeps the versions it already has and alerts. If the config store is unreachable, the instance keeps its last snapshot. An instance that has never loaded a config does not report ready. Any instance that falls more than 60 seconds behind the current revision raises an alert. The 1-minute rollback guarantee depends on the config store being reachable (F4).

---

## D. Running shadow and comparing results

### 14. Start shadow for a candidate
- **Starts it:** An ML engineer runs the promote tool with `shadow <version>`.
- **Data:** Step 12 runs. The tool then compare-and-sets `shadow_version`, `shadow_percent = 10`, a new `shadow_salt` and `shadow_started_at`. The shadow pool loads the candidate (as in step 13) before events are consumed.
- **State:** Serving config. Only one candidate can be in shadow at a time.
- **On failure:** If the check fails or the CAS loses a race, nothing changes. Replacing a shadow version, or changing its salt or percent, restarts its 7-day clock.

### 15. Shadow worker runs the candidate
- **Starts it:** A message on the shadow queue.
- **Data:** The worker does its own online feature lookup for every group the candidate requires, on a rate-limited client separate from the API's, preferably against a read replica. It applies the same 6-hour freshness and completeness rule as step 3. Then it calls the candidate on the shadow pool and records the inference time. It writes `{request_id, shadow_version, items, inference_ms, outcome, feature materialized_at}` to the shadow log.
- **Outcomes:** `ok`. `error`, which covers an exception, a timeout over 500 ms, or output that is not 20 distinct known item IDs. `skipped_missing_features`, which means the candidate never runs. `skipped_stale_message`, for messages older than 5 minutes.
- **State:** Shadow queue, shadow pool memory, shadow log in the warehouse. Shadow output has no route back to the API or to any cache the API reads, so it can never be shown to a user.
- **Isolation:** Separate hosts, a separate queue and a separate feature client. The online store is the shared dependency. A circuit breaker pauses shadow consumption automatically when the API's feature lookup p99 goes above 20 ms or its timeout rate rises. Paused messages expire, and shadow is the part that loses data.
- **On failure:** Worker crashes are retried at most once. A backlog is dropped by expiry, not drained late, because late runs would see different features. Drop and skip counts go into the metrics.
- **Latency fidelity:** The shadow pool uses the same instance type and model runtime as the inference service. Its load per instance is sized to match serving, so the 80 ms number predicts how the candidate would run in serving.

### 16. Daily comparison job
- **Starts it:** The scheduler, daily, while a shadow run is active.
- **Data:** Joins the response log (step 7) and the shadow log (step 15) on `request_id`. Computes for each day:
  - Gate metrics: error rate = `error / (ok + error)`, and p99 `inference_ms` over `ok`.
  - Coverage: the share of shadow-eligible requests where the candidate ran, and how often it skipped while the active model served from the model path.
  - Data quality: the drop rate (events from steps 6 and 15 that went missing), and pairs whose feature `materialized_at` differed between the two lookups.
  - Comparison only, no gate: overlap@20 with active output, rank correlation, catalog coverage, popular-item share, and the spread of items across categories.
- **State:** Shadow metrics table in the warehouse, one row per version per day.
- **On failure:** The job can be rerun for any day. A day with a drop rate over 5%, or with missing metrics, is marked `not_counted` (F5).

### 17. Evaluate the shadow gate
- **Starts it:** The daily job finishes, or someone runs the promote tool with `evaluate <version>`.
- **Data:** Passes only if all of these hold for this exact version, salt and percent: at least 7 counted days since `shadow_started_at`, an error rate under 0.5% across all counted days, and p99 inference latency under 80 ms across all counted days. It also re-runs step 12.
- **State:** The result is written to the registry as an evaluation record that points to the version, with a snapshot of the metrics.
- **On failure:** The version stays in shadow and keeps collecting data, or the engineer stops shadow. A failed check is never overridden in the tool. Shadow keeps running while promotion waits, so it keeps producing evidence.

---

## E. Promotion and rollback

### 18. ML lead approval
- **Starts it:** A passing evaluation record exists.
- **Data:** The ML lead reviews the gate metrics and the comparison metrics from step 16, then records an approval: approver identity, time, version, and the ID of the evaluation record approved.
- **State:** An approval record in the registry. The tool accepts approvals only from the people in the ML lead role.
- **On failure:** Rejection is recorded with a reason. Approval is tied to one evaluation record. If shadow is restarted, a new evaluation and a new approval are needed.

### 19. The stage between approval and full switch (not decided)
Product has not decided whether a live A/B test comes between shadow and the switch. This plan does not choose. It is built so that either answer can be added here without changing steps 1 to 18 or 20 to 23.

- **Built now, needed in either case:** steps 1 to 18 and 20 to 23. That includes user-ID hashing with a salt, serving and logging `model_version` on every response, holding several models in each inference instance, and the approval record.
- **Not built now:** any path that shows candidate output to users, and any traffic split in the active path.
- **What the state model provides:** promotion is a sequence of states: `shadow → shadow_passed → approved → [stage to be decided] → active`. Today the promote tool stops at `approved`. The move to `active` is not enabled until product decides. After that, it is either a direct step 20 or an A/B stage that ends in step 20.
- **If product chooses A/B, these questions open up, and each is a requirement change rather than a detail:**
  1. "Exactly one version is active at a time" no longer holds while two versions serve users. That requirement has to be restated, for example as one active version plus one experiment version.
  2. How the A/B users relate to the shadow 10%: the same users, separate users, or a new salt.
  3. A/B success metrics, duration, and who decides.
  4. Whether the ML lead approves before A/B, before 100%, or both.
  5. Rollback during A/B: does it mean setting the experiment share to 0, and is that also bound by the 1-minute limit?
- **If product chooses to go straight to 100%:** `approved` leads directly to step 20.
- **Deadline:** the first candidate can reach `approved` about 7 days after its shadow run starts. Until product decides, an approved candidate waits in shadow. This is a real schedule dependency. Product needs to decide before the first shadow run finishes.

### 20. Switch the active version
- **Starts it:** The promote tool with `activate <version>`, on a version in `approved` (or past the stage to be decided).
- **Phase 1, preload:** run step 12, then CAS `preload_version = candidate`. Wait until every inference instance's heartbeat says it has the version loaded and warmed up. Time out after 15 minutes.
- **Phase 2, flip:** one CAS sets `previous_version = old active`, `active_version = candidate`, `preload_version = null`, `shadow_version = null`, and writes the change history (who, when, from, to, approval ID). Instances move to the new version on their next poll (≤ 10 s), with no load on the request path and no redeploy. The version that used to be previous is unloaded.
- **State:** Serving config and its history.
- **On failure:** If phase 1 times out, clear `preload_version` and report which instances failed. Active never changed. If the phase 2 CAS loses a race, reread the config and retry or abort. During the ≤ 10 s convergence, some responses come from the old version. Every response logs its `model_version`, so this is visible.

### 21. Watch after the switch
- **Starts it:** Step 20 phase 2.
- **Data:** Dashboards and alerts from the response log and inference metrics, split by `model_version`: model error rate, fallback rate by reason, p99 of the whole call compared with 150 ms, p99 inference compared with 80 ms, and output that is not valid.
- **State:** Metrics system.
- **On failure:** Proposed automatic rollback triggers for the first 24 hours: model error rate over 1% for 5 minutes, or a rise in fallback rate (`model_*` reasons) of more than 2 points compared with before the switch (F6). An alert fires step 22 automatically and also pages on-call.

### 22. Roll back
- **Starts it:** An automatic trigger from step 21, or on-call running `rollback`.
- **Data:** One CAS swaps `active_version` with `previous_version` and writes the change history. The previous version is already loaded and warmed up on every instance, so the change takes effect on the next poll: ≤ 10 s plus a pointer swap, well inside 1 minute.
- **Check that it worked:** the tool waits until every instance reports the new revision, and checks that response-log `model_version` has changed. It alerts on any instance still behind after 60 s. Instances that do not converge are taken out of the load balancer.
- **State:** Serving config and its history.
- **On failure:** The 1-minute guarantee covers rollback to `previous_version` only. Rolling back to an older version means a cold load and is best effort. If the previous version is also bad, use step 23.

### 23. Emergency fallback for all traffic
- **Starts it:** On-call sets `force_fallback = true`.
- **Data:** On the next poll, every API instance skips steps 2 to 4 and serves the popular-items list with `fallback_reason = forced`.
- **State:** Serving config.
- **On failure:** This path depends only on the in-memory popular list. It is the last resort if the feature store, the inference service or every loaded model is unhealthy.

---

## F. Assumptions to confirm

1. **Partial features (step 3):** if any feature group the active model needs is missing or stale, the user counts as having no features and gets the fallback. The brief covers "no features" but not partial features.
2. **Model failure (step 4):** a model timeout or error also returns the popular-items fallback. The brief names only feature failures.
3. **Popular-list age (step 10):** no maximum age is given. I keep serving the last list loaded and alert.
4. **Rollback and config-store outage (step 13):** if the config store is down, instances keep serving their last config. Availability wins over the rollback guarantee for the length of the outage.
5. **What counts as "7 days" (step 16):** days with more than 5% of shadow events dropped do not count, and any change to shadow version, salt or percent restarts the clock.
6. **Thresholds for automatic rollback (step 21):** the numbers are proposals. The brief does not set them.
7. **Shadow and the feature store:** shadow adds about 10% more reads, of a wider feature set. The store needs capacity for that, and step 15's circuit breaker protects the user path if the estimate is wrong.
