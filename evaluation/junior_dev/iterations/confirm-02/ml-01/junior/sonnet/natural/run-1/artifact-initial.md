# Recommendations API: serving, model versions and shadow testing

## Scope and assumptions

The brief fixes most of the design. These are the places where I filled a gap, and each is also listed under "Open items" at the end:

- The brief only defines fallback for feature lookup failures. I treat an active-model inference error or timeout the same way: return the popular list, marked as a fallback.
- The 150 ms budget is split as follows.

| Stage | Budget |
|---|---|
| Parse and route | about 5 ms |
| Feature lookup | 30 ms (fixed) |
| Inference | up to about 80 ms |
| Filter and format | about 10 ms |
| Margin | about 25 ms |

- The online store keeps one record per user, with one `materialized_at` timestamp per record. If the store keeps per-feature timestamps instead, apply the same 6-hour rule to every feature the model uses.
- One candidate is in shadow at a time.
- Shadow inference runs in separate workers, not inside the API process.

## State at a glance

| State | Where it lives | Written by |
|---|---|---|
| Features | Online feature store, one record per user: `features{}`, `materialized_at` | Hourly materialization job |
| Popular list | Daily table or object, cached in memory by each API instance | Daily job |
| Model artifacts and versions | Model registry: immutable, numbered, with a required-feature list per version | Training pipeline |
| Routing config | Registry, one small document (see step 6) | Promotion tool and rollback tool only |
| Shadow results | Results store, keyed by request ID | Shadow workers |
| Gate reports and approvals | Registry, attached to the candidate version | Evaluation job and the ML lead |

Routing config shape:

```
{ active: v, previous: v, shadow: { candidate: v, percent: 10, salt: s } | null }
```

## Part A: the request path

### 1. Receive the request and route

- **Starts when:** `GET /recommendations?user_id=...` arrives.
- **Data moves:**
  - The API validates `user_id` and starts a request deadline of 150 ms.
  - It reads the in-memory copy of the routing config and takes a reference to the active model for the rest of this request. A pointer swap mid-request therefore cannot change the model.
  - It computes `bucket = hash(salt + user_id) mod 100`. The user is in shadow if `bucket < shadow.percent` and a candidate is set.
- **State:** the routing config is cached in memory per instance (see step 8).
- **On failure:**
  - An invalid `user_id` returns 400.
  - If the routing config cannot be read at all, for example at cold start with the registry down, the instance is not ready and takes no traffic.

### 2. Look up features (30 ms)

- **Starts when:** step 1 finishes.
- **Data moves:**
  - One key-value read by user ID returns the whole record.
  - The record carries every feature any in-flight model needs: the active model and the shadow candidate.
  - There is no second lookup for shadow.
- **State:** the online feature store.
- **On failure, the request becomes a fallback (step 4) when:**
  - the lookup times out at 30 ms;
  - there is no record for the user;
  - the record is older than 6 hours (`now - materialized_at > 6h`);
  - the record lacks any feature the active version requires.
- **Freshness is checked by the API on every read.** It does not rely on a store TTL. If the store has a TTL, set it above 6 hours so that records are never evicted while they are still valid.

### 3. Run the active model

- **Starts when:** step 2 returned a complete record under 6 hours old.
- **Data moves:**
  - The record's features go into the active model.
  - The model returns scored items. The API removes duplicates and filters, then keeps the top 20 item IDs.
  - The response is `{items: [...], fallback: false, model_version: N}`.
- **State:** the model is held in memory, loaded from the registry (see step 8).
- **Inference deadline:** about 125 ms from request start.
- **On failure:** an inference error or a missed deadline goes to step 4. The error is counted against the active version.

### 4. Fallback response

- **Starts when:** any failure in step 2 or step 3.
- **Data moves:**
  - The API returns the popular list, 20 items, from the in-memory copy.
  - The response is `{items: [...], fallback: true, reason: timeout | no_features | stale | missing_feature | inference_error}`.
  - The model is not called when features are the problem.
- **State:**
  - The popular list is recomputed daily and refreshed into each instance periodically.
  - If a refresh fails, the instance keeps the last good list.
  - An instance cannot start without a list.
- **On failure:** none expected, because this path does no network I/O.
- **Alert on:**
  - the fallback rate;
  - the fallback reason mix, because a jump in `stale` means materialization is failing;
  - the age of the popular list.

### 5. Hand off to shadow, after the response

- **Starts when:** the user is in the shadow bucket and the response came from step 3. Fallback requests are never shadowed, because there are no features to give the candidate.
- **Data moves:**
  - The response is written to the caller first.
  - The API then places one message on a bounded, in-process, non-blocking buffer. The message holds the request ID, user ID, the feature record, the active version, and the active output (the 20 items and the inference latency).
  - A background sender ships the buffer to a message queue.
  - The message carries the feature snapshot, so the candidate sees exactly what the active model saw.
- **State:** a short-lived buffer in the API process. After that, the queue.
- **Failure rules (nothing in shadow may touch the user's response):**
  - The enqueue never waits and never retries on the request thread.
  - A full buffer or an unreachable queue means the message is dropped and a counter goes up.
  - Everything is wrapped so that an exception cannot reach the response.
  - The shadow buffer has its own small thread or event-loop budget.
- **Dropped messages** shrink the sample. They are reported separately and are not counted as candidate errors.

## Part B: feature freshness

### 6. Hourly materialization

- **Starts when:** the schedule fires every hour.
- **Data moves:**
  - The job reads a warehouse snapshot.
  - It writes one record per user to the online store, with `materialized_at` set to the snapshot time, not the write time.
  - The set of features it writes is the union of the features required by the active version, the previous version (the rollback target), and the shadow candidate.
- **State:** the online store. The job's run history lives in the scheduler.
- **On failure:**
  - Nothing is rolled back. The store keeps serving what it has. This is the "keep serving up to 6 hours old" rule.
  - Users whose records are older than 6 hours fall out through step 2 and get the fallback.
  - Writes are per record, so a half-finished run leaves a mix of old and new records. This is safe, because each record carries its own timestamp.
  - Alert after 2 missed runs, and page at about 4 hours since the last successful run, so there is time to fix it before users start falling back.
  - Features are never removed from the job while any version that uses them is active, previous, or in shadow.

## Part C: model versions and switching

### 7. Register a version

- **Starts when:** the training pipeline finishes a model.
- **Data moves:**
  - The artifact is stored as a new, numbered, immutable version.
  - The registry entry lists the version's required feature names.
  - No process may edit a registered version. A fix is a new number.
- **State:** the model registry.
- **On failure:** if registration is incomplete, the version has no `registered` status and cannot be selected.

### 8. Deliver the active pointer without a redeploy

- **Starts when:** the routing config changes in the registry. Each instance also polls every 10 seconds.
- **Data moves:**
  - An instance reads the config. If `active` or `previous` points at a version it does not hold, it loads that artifact.
  - It swaps the in-memory pointer atomically, after the load has succeeded.
  - It reports its loaded version in its health metrics.
  - Each instance keeps the active and previous versions resident in memory at all times. This is what makes rollback fast (step 14).
- **State:** the registry holds the config. The instance holds a cached copy and the loaded models.
- **On failure:**
  - If the registry is unreachable, the instance keeps its last known config and keeps serving.
  - If a load fails, the instance keeps the current version and raises an alert. It does not serve a half-loaded model.
  - Instances can briefly disagree on the version (up to about one poll interval, plus load time). That is accepted. Each response states its `model_version`.

## Part D: running shadow and comparing results

### 9. Start shadow for a candidate

- **Starts when:** someone requests shadow on a registered version, through the promotion tool.
- **Pre-checks, all enforced by the tool:**
  - Every feature the candidate requires exists in the online store. The materialization job config has been updated and has run at least once, and the share of users whose records contain all required features is reported.
  - Only one candidate is in shadow.
- **Data moves:**
  - The tool writes `shadow: {candidate, percent: 10, salt}` to the routing config.
  - The same pre-check is repeated per request in step 10. The per-request check is the real guarantee. The pre-check is there to avoid starting a test that would mostly skip.
  - The 7-day clock starts at the first shadow result.
- **State:** the routing config and the gate report record in the registry.
- **On failure:** if a check fails, shadow does not start and the tool says which feature is missing.

### 10. Shadow worker runs the candidate

- **Starts when:** a message arrives on the shadow queue.
- **Data moves:**
  - The worker checks that the snapshot has every feature the candidate requires and that the record is under 6 hours old at the time of the original request. If not, it records a skip (`missing_feature` or `stale`) and does not run the model. This is the check that prevents the candidate from ever running against features the store lacks.
  - Otherwise it runs inference, using the same inference code and the same hardware class as the API, and measures inference latency.
  - It writes `{request_id, user_id, candidate_version, active_version, candidate_items, active_items, candidate_latency, error?, skip_reason?, feature_age}` to the results store.
  - Shadow output goes only to the results store. Nothing reads it on the request path.
- **State:** the results store.
- **On failure:**
  - A model error or timeout is recorded as a candidate error.
  - A worker crash or a lost message is not a candidate error. It lowers the sample count and is reported as loss.
  - Shadow workers scale and fail independently of the API.
  - A kill switch sets `shadow` to null in the routing config. API instances stop sending within one poll interval.
  - Shadow is disabled automatically if the drop rate stays high, so that the buffer cannot become a load problem.

### 11. Compare results and build the gate report

- **Starts when:** an evaluation job runs, for example hourly, over the results store.
- **Data moves, per candidate version:**
  - **Error rate:** candidate errors divided by candidate inference attempts. Skips are excluded from both counts. The gate is under 0.5%.
  - **p99 inference latency:** from `candidate_latency`. The gate is under 80 ms.
  - **Days in shadow:** the gate is at least 7.
  - **Skip rate** by reason, and **drop rate**. These are shown next to the gate numbers. A high skip rate means the gate numbers describe only part of the traffic.
  - **Comparison with the active model:** overlap@20, rank correlation, share of empty or short lists, and the item catalogue coverage. These describe how different the candidate is. They do not say whether it is better, because shadow has no user response to score.
  - The job writes the report to the registry, with a timestamp.
- **State:** the registry (gate report) and the results store.
- **On failure:**
  - If the job is down, the report goes stale. The approval step refuses a report older than 24 hours.
  - If the results store is incomplete, the report shows the gap and the gate stays closed.

## Part E: promotion and rollback

### 12. Promotion gate

- **Starts when:** someone asks the promotion tool to activate a candidate.
- **The tool refuses unless all of these hold:**
  - at least 7 days in shadow;
  - error rate under 0.5%;
  - p99 inference latency under 80 ms;
  - a gate report no older than 24 hours;
  - the ML lead's approval, recorded against this exact version and this exact report;
  - the required features are still present in the store (re-checked now).
- **State:** the approval record in the registry. The approval names the person and the time.
- **On failure:** the tool returns the list of unmet conditions. Nothing changes.
- **Approval is not valid for a different version, and not valid for a report other than the one shown to the approver.**

### 13. Decision point: A/B test or direct switch (not decided)

This is the gap. The plan does not choose. Everything before this step (steps 1 to 12) and the switch itself (step 14) work the same under either option.

- **Option A (live A/B between shadow and full switch):** the routing config would gain an optional `experiment` field, off by default, which serves the candidate's items to a slice of users. It would need its own user bucketing (a different salt from shadow), its own success metrics, its own end criteria, and a decision on who signs off. Those belong to Product.
- **Option B (shadow straight to 100%):** nothing is added. The promotion in step 14 follows step 12 directly.
- **What to do now:**
  - Keep the routing config a small document, so a field can be added later without changing the API contract.
  - Do not build experiment serving yet.
  - Do not remove any gate from step 12 under either option. The A/B option adds criteria after them and does not replace them.
  - Record in the registry which path a given promotion took.
- **Needed from Product:** the choice, and for option A the metrics and thresholds.

### 14. Switch the active version, and roll back

- **Starts when:** step 12 passes (and step 13 is done, if it applies), or an on-call engineer starts a rollback.
- **Data moves, for promotion:**
  - The tool writes `previous = old active, active = candidate, shadow = null`.
  - Instances load the version if needed (step 8). The tool reports how many instances are on the new version.
  - The promotion counts as complete when nearly all instances report the new version.
- **Data moves, for rollback:**
  - A single command sets `active` back to `previous`. No approval is needed, since the approval rule applies to promotion. The command takes effect on all instances within one poll (10 seconds) plus pointer swap time.
  - Because `previous` is already resident, the 1-minute requirement is met. Rolling back to a version older than `previous` needs a load and must be timed in advance. If it takes too long, either keep more versions resident or limit rollback targets to `previous`.
- **State:** the routing config.
- **On failure:**
  - If an instance cannot load the new version, it stays on the old one, and the report shows a mix. Roll back or fix the artifact.
  - A rollback never needs a redeploy.
  - A rollback target is valid only if its required features are still materialized, which is why step 6 keeps the previous version's features in the job.
  - After promotion, watch the fallback rate, error rate and latency for the new active version. If you want automation here, a guardrail alert that pages the on-call is the first step. An automatic rollback is optional and should be decided separately.

## Open items

1. **A/B or direct switch.** Product decides. See step 13.
2. **Active inference failure.** I assumed a fallback response. Confirm.
3. **7 days of shadow.** Decide whether the 7 days must be continuous (an interruption resets the clock), and whether to add a minimum number of requests.
4. **Skip-rate limit.** Set a threshold for how much higher the candidate's skip rate may be than the active model's fallback rate before promotion is refused.
5. **Poll interval and load time.** I proposed 10 seconds. Measure the real model load time, since it decides whether rollback to a non-resident version fits in 1 minute.
6. **Shadow quality.** Shadow measures error, latency and difference from the active model. It does not measure whether recommendations are better. If the approver needs that, it needs a separate offline evaluation or option A.
7. **Per-record versus per-feature timestamps** in the online store.
