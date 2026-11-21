# Recommendations API: serving, model versions and shadow testing

## Summary

Today the home page reads recommendations from a table that a job precomputes each night. This plan replaces that with an API, `GET /recommendations?user_id=...`, that scores 20 items per request with the active model, using features that are at most one hour old in normal operation. New model versions are tried in shadow first. A copy of the traffic for 10% of users goes to a candidate, its output is never shown, and the results are compared against fixed gates before the ML lead may promote it. The shape comes from the brief: every failure on the user path falls back to a popular list, and everything about shadow runs off the request path so it cannot slow or break a response.

## Terms

- **Online feature store**: a key-value store keyed by user ID. It holds one record per user: `features{}` and one `materialized_at` timestamp. If the store has per-feature timestamps instead, apply the 6-hour rule to every feature the model uses.
- **Materialization**: the hourly job that copies features from a warehouse snapshot into the online store.
- **Model registry**: stores trained models as immutable, numbered versions. Each version lists the feature names it requires. A fix is a new number.
- **Routing config**: one small document in the registry that says which version is active, which is the rollback target, and which candidate is in shadow (shape below).
- **Active / previous / candidate**: the version users see / the version to roll back to / the version being tested in shadow.
- **Shadow**: running a candidate on a copy of real requests and recording its output, without showing it to anyone.
- **Shadow worker**: a separate service that consumes the shadow queue and runs the candidate.
- **Fallback**: a response that is the popular-items list (one global list, the same for every user, recomputed daily) with `fallback: true`.
- **Gate report**: an hourly report built from shadow results, stored in the registry.
- **Promotion tool, rollback command, stop-shadow command (kill switch)**: command-line tools run by people. The promotion tool is run by an ML engineer. The rollback command and the stop-shadow command (which sets `shadow` to null) may also be run by the on-call engineer. Together with the evaluation job (a scheduled job), these are the only writers of the routing config, and every write records who or what made it. The authentication method is left to the platform team.

## Fixed rules from the brief

- The p99 latency budget for the whole call is 150 ms. The online feature lookup gets 30 ms.
- Features older than 6 hours count as missing. If materialization fails, the store keeps serving what it has, up to that age.
- Exactly one version is active at a time. Switching it needs no redeploy of the API. A rollback takes effect within 1 minute.
- Shadow covers 10% of users, chosen by user ID so that a user is always in or always out. Nothing that goes wrong in shadow may slow down or break the user's response.
- A candidate may need features the active model does not use. It must never run, in shadow or as active, against features the store does not have.
- A candidate becomes active only after at least 7 days in shadow, an error rate under 0.5%, p99 inference latency under 80 ms, and the ML lead's approval.
- Open decision: Product has not decided whether a live A/B test comes between shadow and the full switch. This plan does not choose (see the decision point below).

Assumptions I added (each is repeated in the open questions):

- An active-model inference error or timeout is treated like a feature failure: return the fallback.
- One candidate is in shadow at a time. Shadow inference runs in separate workers, not in the API process.
- The API runs the active model in-process (no separate model server).
- Budget split for the 150 ms:

| Stage | Budget |
|---|---|
| Parse and route | about 5 ms |
| Feature lookup | 30 ms (fixed) |
| Inference | up to about 80 ms (hard deadline 125 ms from request start) |
| Filter and format | about 10 ms |
| Margin | about 25 ms |

## State at a glance

| State | Where it lives | Written by |
|---|---|---|
| Features | Online feature store | Hourly materialization job |
| Popular list | Daily table or object, cached in memory by each API instance | Daily job |
| Model artifacts and versions | Model registry | Training pipeline |
| Routing config | Registry | Promotion tool, rollback command, evaluation job |
| Shadow results | Results store, keyed by request ID | Shadow workers |
| Gate reports and approvals | Registry, attached to the candidate version | Evaluation job and the ML lead |

Routing config shape:

```
{ active: v, previous: v, shadow: { candidate: v, percent: 0 or 10, salt: s } | null }
```

`percent` is 0 while a candidate is only being prepared (its features are being materialized and nobody is in shadow) and 10 while shadow runs. The `salt` is new each time shadow starts and also identifies that shadow run.

## How the system runs

### 1. Receive the request and route

- **Trigger:** `GET /recommendations?user_id=...` arrives.
- **What it does:**
  - Validates `user_id` and starts a 150 ms request deadline.
  - Reads the instance's in-memory copy of the routing config and holds a reference to the active model for this request, so a pointer swap mid-request cannot change the model.
  - Computes `bucket = hash(salt + user_id) mod 100`. The user is in shadow if a candidate is set and `bucket < shadow.percent`.
  - The API never loads or runs the candidate. From `shadow` it needs only `percent` and `salt`.
- **Data kept:** the config copy lives in memory per instance. A request never waits on the registry.
- **If it goes wrong:** an invalid `user_id` returns 400. An instance is ready for traffic only after it has read the config and loaded the active and previous models. If that fails at cold start (for example, the registry is down), it takes no traffic.

### 2. Look up features (30 ms)

- **Trigger:** step 1 finishes.
- **What it does:** one key-value read by user ID returns the whole record. The record holds the features for every version in flight (active, previous, candidate), so shadow needs no second lookup.
- **Data kept:** the online feature store.
- **If it goes wrong:** the request becomes a fallback if the lookup times out at 30 ms, the user has no record, the record is older than 6 hours (`now - materialized_at > 6h`), or it lacks a feature the active version requires. The model is not called. The API checks freshness on every read and does not rely on a store TTL. If the store has a TTL, set it above 6 hours.

### 3. Run the active model

- **Trigger:** step 2 returned a complete record under 6 hours old.
- **What it does:**
  - The model reads only the features named in its registry entry and ignores the rest.
  - It returns candidate item IDs with scores, best first. The API removes duplicates, applies filters, and keeps the top 20.
  - If fewer than 20 remain, the API tops up from the popular list, skipping items already present, so the response always has 20. This is a normal response (`fallback: false`), and the topped-up count is recorded. If nothing remains, it counts as an inference failure.
  - Response: `{items: [...], fallback: false, model_version: N}`.
  - The API checks the remaining time before and after inference. Missing the 125 ms deadline is a failure.
- **Data kept:** the model is held in memory, loaded from the registry (step 8).
- **If it goes wrong:** an error or missed deadline goes to step 4, and the error is counted against the active version.

### 4. Fallback response

- **Trigger:** any failure in step 2 or 3.
- **What it does:** returns the 20-item popular list from memory: `{items: [...], fallback: true, reason: timeout | no_features | stale | missing_feature | inference_error}`. `timeout` means only the 30 ms feature lookup. An inference error and a missed inference deadline are both `inference_error`. The fallback does no network I/O, so it still fits in 150 ms.
- **Data kept:** each instance holds a copy of the popular list and refreshes it from the daily table or object on its own background thread (proposed every 10 minutes, since the list changes daily). If a refresh fails, it keeps the last good list. An instance cannot start without a list.
- **If it goes wrong:** nothing is expected to fail on this path. Alert on the fallback rate, the mix of reasons (a jump in `stale` means materialization is failing), and the age of the popular list.

### 5. Hand off to shadow, after the response

- **Trigger:** the user is in the shadow bucket and the response came from step 3. Fallback requests are never shadowed, since they have no features to give the candidate.
- **What it does:**
  - The response is written to the caller first.
  - The API then puts one message on a bounded, non-blocking in-process buffer. The message holds the request ID, request time, user ID, the feature record, the active version, and the active output (20 items and inference latency). The feature snapshot means the candidate sees exactly what the active model saw.
  - A background thread in the API ships the buffer to a message queue in small batches.
  - The API does not check the candidate's features. Some users in the bucket may lack one, and the worker records a skip.
  - Volume is 10% of non-fallback requests. The brief gives no request rate, so buffer and queue sizes are set once it is known.
- **Data kept:** a short-lived buffer in the API process, then the queue.
- **If it goes wrong:** the enqueue never waits and never retries on the request thread. A full buffer or unreachable queue drops the message and raises a counter. Everything is wrapped so no exception reaches the response, and the buffer has its own small thread budget. Drops shrink the sample and are reported apart from candidate errors. A high drop rate raises an alert, and the on-call engineer may use the kill switch. There is no automatic disable.

### 6. Hourly materialization

- **Trigger:** the schedule fires every hour.
- **What it does:**
  - Reads a warehouse snapshot and writes one record per user, with `materialized_at` set to the snapshot time, not the write time.
  - Writes the union of the features required by the active version, the previous version and the shadow candidate. It rebuilds this union from the current routing config at the start of every run, so there is no separate job config. A candidate counts as soon as it is set, even at `percent: 0`. After a promotion, features only the old previous version used drop out at the next run.
  - The union also covers a promotion in progress: the new active was already in it as the candidate, and the old active becomes `previous`, so instances on either version find their features.
- **Data kept:** the online store. Run history lives in the scheduler.
- **If it goes wrong:** nothing is rolled back and the store keeps serving what it has. Records older than 6 hours fall out through step 2 into fallback. Writes are per record, so a half-finished run leaves a mix of old and new records, which is safe because each carries its own timestamp. Alert after 2 missed runs, and page at about 4 hours since the last success, which leaves time to fix it before users fall back.

### 7. Register a version

- **Trigger:** the training pipeline finishes a model.
- **What it does:** stores the artifact as a new numbered, immutable version, with its list of required feature names.
- **Data kept:** the model registry.
- **If it goes wrong:** a version whose registration is incomplete has no `registered` status and cannot be selected.

### 8. Deliver the active pointer without a redeploy

- **Trigger:** the routing config changes. Each instance polls the registry every 10 seconds on its own background thread, so no request waits on the poll.
- **What it does:**
  - If `active` or `previous` names a version the instance does not hold, it loads that artifact on the background thread while requests keep using the current model. It swaps the in-memory pointer atomically, only after the load succeeds.
  - It keeps exactly the active and previous versions in memory and drops any other once no in-flight request holds it. Having `previous` resident is what makes rollback fast.
  - It does not preload a shadow candidate. Only shadow workers run candidates, so a newly promoted version is loaded only after the promotion write.
  - It reports its loaded version in its health metrics.
- **Data kept:** the registry holds the config. The instance holds a cached copy and the loaded models. Real load time is not yet known.
- **If it goes wrong:** if the registry is unreachable, the instance keeps its last config and keeps serving. If a load fails, it keeps the current version and raises an alert, and never serves a half-loaded model. Instances may briefly disagree on the version, by up to one poll interval plus load time. That is accepted, and each response states its `model_version`.

## How a model is tested and released

### 9. Start shadow for a candidate

Starting has two phases, so the candidate's features exist in the store before anyone is sent to it.

- **Trigger:** someone requests shadow on a registered version through the promotion tool.
- **The feature check** is used in both phases and in step 12. The tool reads a random sample of user records from the online store and reports, per required feature, the share of sampled records that have it. A feature that appears in no sampled record blocks the step. A partial share does not block, because the worker skips users who lack a feature and the skip rate is gated separately. The sample size is open.
- **Phase 1, prepare:** the tool checks that no other candidate is in shadow and writes `shadow: {candidate, percent: 0, salt}`. No user is bucketed in, but the next materialization run includes the candidate's features. After that run, the tool runs the feature check and reports.
- **Phase 2, start:** the tool runs the feature check again and stops if any feature is missing from the sample. Otherwise it writes `percent: 10` with a new salt and records the write time in the registry as the start of this shadow run. The 7-day clock starts at that time. A restart gets a new salt and start time, so the clock begins again from zero.
- **Data kept:** the routing config, and the gate report record in the registry.
- **If it goes wrong:** shadow stays at percent 0 or is switched off, and the tool names the missing feature. The per-request check in step 10 is the real guarantee. This pre-check only avoids a test that would mostly skip.

### 10. Shadow worker runs the candidate

- **Trigger:** a message arrives on the shadow queue.
- **What it does:**
  - Reads the current routing config for each message (a copy cached for a few seconds is enough). If `shadow` is null, it discards the message, which also handles leftovers after a promotion or kill switch.
  - If it does not hold the candidate, it loads it from the registry first and keeps one candidate resident at a time. Messages wait in the queue meanwhile.
  - Checks that the snapshot has every feature the candidate requires and that the record's age (the message's request time minus `materialized_at`) was under 6 hours. If not, it records a skip (`missing_feature` or `stale`) and does not run the model. This is the check that keeps the candidate from ever running against features the store lacks.
  - Otherwise it runs inference with the same inference code and hardware class as the API and the same 125 ms deadline, and measures latency.
  - Writes `{request_id, user_id, shadow_salt, candidate_version, active_version, candidate_items, active_items, candidate_latency, error?, skip_reason?, feature_age}` to the results store. `shadow_salt` marks which run produced the row. Nothing on the request path reads this output.
- **Data kept:** the results store.
- **If it goes wrong:** a model error, or a miss of the 125 ms deadline, is a candidate error, and a missed attempt is recorded with a latency of 125 ms. A result slower than 80 ms but within 125 ms is not an error. It only counts in the p99 latency, where the 80 ms gate applies. A worker crash or lost message is not a candidate error. It lowers the sample count and is reported as loss. Workers scale and fail independently of the API. The kill switch sets `shadow` to null, and API instances stop sending within one poll interval.

### 11. Compare results and build the gate report

- **Trigger:** the evaluation job runs, for example hourly, over the results store.
- **What it does, per candidate version:** counts only rows whose `shadow_salt` matches the current run, then computes:
  - **Error rate**: candidate errors divided by inference attempts, with skips excluded from both. Gate: under 0.5%.
  - **p99 inference latency** from `candidate_latency`. Gate: under 80 ms.
  - **Days in shadow**: now minus the run start time from step 9, while `shadow` still holds this run's salt. Gate: at least 7. Any switch-off or restart ends the run, so no gap detection is needed. Gaps in results show up as loss and a low sample count.
  - **Skip rate** by reason and **drop rate**, shown beside the gate numbers. A high skip rate means the gate numbers describe only part of the traffic.
  - **Comparison with the active model**: overlap@20, rank correlation, share of empty or short lists, and catalogue coverage. These show how different the candidate is, not whether it is better, because shadow has no user response to score.
  - It writes the report to the registry with a timestamp and report ID. Each run adds a new report, and reports stay attached to the version after promotion or shadow end.
- **Data kept:** the registry (reports) and the results store.
- **If it goes wrong:** if the job is down, the report goes stale and step 12 refuses a report older than 24 hours. If the results store is incomplete, the report shows the gap and the gate stays closed.

### 12. Promotion gate

- **Trigger:** someone asks the promotion tool to activate a candidate.
- **The tool refuses unless all of these hold:**
  - at least 7 days in shadow;
  - error rate under 0.5%;
  - p99 inference latency under 80 ms;
  - the latest gate report is no older than 24 hours and itself meets those three numbers;
  - the ML lead has approved this exact version against a report no older than 24 hours;
  - the feature check from step 9, run again now, passes.
- **Data kept:** the approval record in the registry: the person, the time, the version, and the report ID the approver saw.
- **If it goes wrong:** the tool lists the unmet conditions and changes nothing. Reports are replaced hourly, so the approver approves the report they saw, and that approval counts for 24 hours from that report. After that, or if the latest report fails a number, the ML lead must approve again from a fresh report. An approval is not valid for a different version.

### 13. Decision point: A/B test or direct switch (not decided)

The plan does not choose. Steps 1 to 12 and the switch in step 14 work the same under either option.

- **Option A (live A/B between shadow and the full switch):** the routing config would gain an optional `experiment` field, off by default, serving the candidate's items to a slice of users. It would need its own bucketing (a different salt from shadow), success metrics, end criteria and a sign-off decision, all owned by Product.
- **Option B (shadow straight to 100%):** nothing is added, and step 14 follows step 12.
- **What to do now:** keep the routing config small so a field can be added later without changing the API contract. Do not build experiment serving. Do not remove any gate from step 12 under either option, since an A/B test adds criteria after them. Record in the registry which path each promotion took.
- **Needed from Product:** the choice, and for option A the metrics and thresholds.

### 14. Switch the active version, and roll back

- **Trigger:** step 12 passes (and step 13, if it applies), or an on-call engineer starts a rollback.
- **Promotion:**
  - The tool writes `previous = old active, active = candidate, shadow = null`.
  - Instances load the new version only after this write, in the background (step 8), and keep using the old one until the load finishes. The switch therefore takes up to one poll interval plus load time, which is accepted. Materialization during this window is safe because of the union in step 6.
  - The tool reads each instance's loaded version from the health metrics and prints how many are on the new version. Promotion is complete when every ready instance reports it. Any instance that has not after 5 minutes is listed for a human to fix the artifact or roll back. The tool takes no automatic action.
- **Rollback:**
  - One command swaps the fields: `active = old previous, previous = old active`. Running it again rolls forward. No approval is needed, since the approval rule applies to promotion.
  - It takes effect on all instances within one poll (10 seconds) plus pointer swap time. Both versions are resident on every instance and both stay in the materialization union, so the 1-minute requirement is met. Rolling back to anything older than `previous` needs a load and must be timed in advance. If too slow, keep more versions resident or limit rollback targets to `previous`.
  - A rollback target is valid only while its required features are still materialized, which is why step 6 keeps the previous version's features.
- **Data kept:** the routing config.
- **If it goes wrong:** an instance that cannot load the new version stays on the old one, and the report shows a mix. Roll back or fix the artifact. A rollback never needs a redeploy. After promotion, watch fallback rate, error rate and latency for the new version. A guardrail alert that pages the on-call is the first automation step. Automatic rollback is optional and decided separately.

## What happens when things fail (summary)

| Failure | Result |
|---|---|
| Feature lookup over 30 ms, no record, record over 6 hours old, missing feature | Fallback, with the reason |
| Active inference error or over 125 ms | Fallback, reason `inference_error` |
| Materialization fails | Store keeps old records. Users fall back once records pass 6 hours. Alerts at 2 missed runs and about 4 hours |
| Registry down | Instances keep their last config and models. A cold start takes no traffic |
| Model load fails | Instance keeps its current version and alerts |
| Shadow buffer full or queue down | Message dropped and counted. User response unaffected |
| Shadow worker crash or lost message | Counted as loss, not a candidate error |
| Candidate lacks features, or record too old | Worker records a skip and does not run the model |
| Promotion condition unmet | Tool refuses and lists what is missing |

## Open questions

1. **A/B or direct switch.** Product decides (step 13).
2. **Active inference failure.** I assumed a fallback response. Confirm.
3. **7 days of shadow.** I assumed the days are continuous from one run start and a restart resets the clock. Confirm, and decide whether to add a minimum number of requests.
4. **Skip-rate limit.** Set how much higher the candidate's skip rate may be than the active model's fallback rate before promotion is refused.
5. **Poll interval and load time.** I proposed 10 seconds. Measure real model load time, since it decides whether rollback to a non-resident version fits in 1 minute.
6. **Shadow quality.** Shadow measures errors, latency and difference from the active model, not whether recommendations are better. If the approver needs that, it needs a separate offline evaluation or option A.
7. **Per-record versus per-feature timestamps** in the online store.
8. **Feature check sample size** in step 9.
9. **Unspecified platform choices.** The brief does not name the model artifact format, the inference runtime, the queue product, who deploys and runs the shadow workers, where instance health metrics are kept, how "popular" is scored, the exact item filter rules, where candidate item IDs come from (the whole catalogue or an earlier retrieval step), the request rate, or the authentication method for tools. Product or the platform team must fill these in.
10. **Popular list refresh interval.** I proposed 10 minutes. Confirm or set another value.
