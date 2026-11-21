# Recommendations API: serving, model versions and shadow testing

## Scope and assumptions

Everything below follows the fixed requirements. These points go beyond them and need confirming.

- **Inference failure.** The brief only names two fallback causes: lookup timeout and no features. This plan also falls back when inference errors, exceeds its deadline, or returns something other than 20 valid item IDs. An error page on the home page is worse than a popular-items list.
- **Latency split.** The 150 ms budget is split into these proposed limits. They are hard deadlines, so a slow dependency can never push past the total.

  | Stage | Limit |
  |---|---|
  | Feature lookup | 30 ms (fixed) |
  | Inference | 90 ms |
  | Parsing, response and overhead | 30 ms |

  The 90 ms inference deadline sits above the 80 ms p99 promotion gate. A candidate that passes the gate therefore rarely hits the deadline.
- **One candidate at a time** is in shadow.
- **Rollback authority.** Rolling back to a version that was active before needs no 7-day wait and no ML lead approval.
- **Before any real-user exposure.** The brief only gates "active". I assume the shadow gate and ML lead approval are also required before any live A/B exposure (step 14). Please confirm this.

## State overview

| State | Lives in | Read by |
|---|---|---|
| Model versions and stage (`registered`, `shadow`, `active`, `retired`) | Model registry | Gate evaluator, API loader |
| Serving config: active version, shadow candidate, shadow percent and salt, with a revision number | Config store (small KV, separate from the registry's artifact storage) | Every API instance, polled |
| Per-user features, each record stamped with `source_ts` and `feature_set_version` | Online feature store | API (active features), shadow workers |
| Popular-items list, recomputed daily | Blob or table, cached in each API instance | API |
| Shadow pair records (active and candidate outputs, latency, errors) | Shadow results table | Comparison and gate jobs |

## Request path

### 1. A request arrives
- **Starts it:** `GET /recommendations?user_id=...` from the home page.
- **Data moves:** `user_id` goes into a request context carrying a 150 ms deadline. The handler reads the in-memory serving snapshot, which holds the active model, the active version's required feature list, the popular list and the shadow config. It makes no network call for any of these.
- **State:** the snapshot lives in instance memory and is refreshed by steps 5 and 9.
- **On failure:**
  - A missing or malformed `user_id` returns 400.
  - An instance with no loaded model or no popular list reports not-ready and gets no traffic. After startup, a failed refresh keeps the last good snapshot.

### 2. Online feature lookup
- **Starts it:** step 1 completes.
- **Data moves:** one key-value read by user ID for the active version's feature set, with a hard 30 ms timeout. The record comes back with `source_ts` and `feature_set_version`.
- **State:** the online feature store. The API only reads it.
- **On failure:** a timeout or store error goes to the fallback (step 5) with reason `lookup_timeout`. There is no retry, because 30 ms leaves no room for one. A not-found goes to the fallback with reason `no_features`.

### 3. Freshness and completeness check
- **Starts it:** a record came back from step 2.
- **Data moves:** the API computes `age = now - source_ts`. It also checks that every feature the active version declares is present and non-null.
- **State:** the rule is in code. The declared feature list lives in the registry entry, cached in the snapshot.
- **On failure:**
  - Age over 6 hours counts as missing and goes to the fallback with reason `stale_features`.
  - A missing required feature counts as missing and goes to the fallback with reason `partial_features`.
  - A record is never mixed with older data. Step 7 writes each user's record whole.

### 4. Inference and response
- **Starts it:** the record is fresh and complete.
- **Data moves:** features go to the loaded active model. The model returns ranked item IDs. The API checks for exactly 20 unique, non-empty IDs and returns them with `fallback: false` and the active version number.
- **State:** the model is held in instance memory (see step 9).
- **On failure:** an exception, the 90 ms inference deadline, or invalid output goes to the fallback with reason `inference_error`. The reason is logged.

### 5. Fallback response and the popular list
- **Starts it:** any failure in steps 2 to 4, or the daily refresh.
- **Data moves:**
  - The first 20 items of the cached popular list are returned with `fallback: true`. The reason is logged but is not exposed beyond that flag unless the front end wants it.
  - A daily job recomputes the list and writes it to the blob or table. Each instance reloads it on a timer.
- **State:** the list lives in the blob or table, with a per-instance cached copy.
- **On failure:**
  - A failed daily job or a failed reload keeps yesterday's list. The list's age is alerted on.
  - An instance that has never loaded a list stays not-ready (step 1).
- **Alert:** the fallback rate per reason. A rise in `stale_features` means step 7 is failing.

### 6. Hand-off to shadow, after the response
- **Starts it:** the response has been sent and a candidate is configured in the snapshot. Shadow is skipped for requests that took the fallback, because those users have no usable features.
- **Data moves:**
  - The API computes `hash(salt + user_id) mod 10000 < percent * 100`. The hash is a fixed deterministic function, so a user is always in or always out. The salt is set when the candidate enters shadow and never changes while it is there.
  - For selected users only, it puts a small message on a bounded, non-blocking queue. The message holds request ID, user ID, active version, active item IDs and the active record's `source_ts`.
- **State:** the queue is a separate service (or an in-process queue drained by a separate process) so it shares no thread pool or connection pool with the request path.
- **On failure:**
  - A full queue, a slow publish or a publish error drops the message and increments a counter. Nothing waits or retries on the request path.
  - The send runs after the response is flushed. The drop counter is part of the gate report (step 13).

## Feature freshness

### 7. Hourly materialization
- **Starts it:** an hourly schedule.
- **Data moves:**
  - The job reads a warehouse snapshot and writes one record per user to the online store. Each record contains all features, the snapshot time as `source_ts`, and a `feature_set_version`.
  - A record replaces the previous one in a single write, so an update is never half-applied for one user.
- **State:** the source is the warehouse. The destination is the online store. The job writes a run record (start, end, snapshot time, rows written, status) to the metadata table.
- **On failure:**
  - The previous records stay in place and keep being served until step 3 ages them out at 6 hours. Nothing is deleted on failure.
  - A partial run leaves some users on new data and some on old. Step 3 judges each record by its own `source_ts`, so this is safe.
  - Alert after 2 consecutive failed runs (about 2 hours). Page at 4 hours, because at 6 hours every user starts falling back.
  - When a candidate needs a new feature (step 8), the schema change is deployed to the job first. Records carry the new feature only after a run completes.

## Model versions and switching

### 8. Registering a version
- **Starts it:** training finishes.
- **Data moves:**
  - The model artifact (content-hashed) and its metadata are written to the registry as the next number. Metadata includes the **required feature list** and the feature names, types and `feature_set_version` it was trained on.
  - The registry refuses any change to a registered version. A fix is a new number.
  - The registry checks that every required feature exists in the online store's schema and is **actually materialized**, meaning at least one completed run has written it. The stage is `registered` if so. Otherwise it is `blocked_features`, and the version cannot enter shadow or become active.
- **State:** the model registry.
- **On failure:** a failed check leaves the version `blocked_features` with the missing features listed. The feature owner adds them to step 7, and the check reruns after a completed run.

### 9. Serving config, loading and switching in the API
- **Starts it:** every instance polls the config store every 15 seconds, and on startup. A change in the revision number triggers a load.
- **Data moves:**
  - The config holds `active_version`, the shadow block (`candidate_version`, `percent`, `salt`, `started_at`) and a revision.
  - For a new `active_version`, the instance downloads the artifact and checks its hash. It then re-checks the version's required features against the live schema (the same check as step 8, as a guard against later changes). It runs one smoke inference on a stored sample record, and swaps the snapshot atomically.
  - It keeps the previous active version loaded as well (the last two active versions stay warm), so a rollback needs no download.
- **State:** the pointer and shadow block are in the config store. Loaded models are in instance memory. The poll result is exported as a metric: `active_version` per instance.
- **On failure:**
  - If the config store is unreachable, the instance keeps its current snapshot.
  - If load, hash, feature check or smoke test fails, the instance keeps serving the old version, reports the failure, and retries on the next poll. It never serves a version it could not verify.
  - Alert if instances report different `active_version` values for more than 60 seconds.
- **Timing:** switching needs no redeploy. Worst case is 15 s of polling plus swap time. A warm rollback target takes effect within the next poll, well inside the 1-minute requirement.

## Shadow testing

### 10. Start shadow for a candidate
- **Starts it:** an engineer requests it for a version in stage `registered`. Only one candidate may be in shadow at a time.
- **Data moves:** a registry-controlled operation writes the shadow block to the config store (version, `percent: 10`, a fresh salt, `started_at`). It also sets the registry stage to `shadow`. The operation re-runs the step 8 feature check first.
- **State:** the config store holds the block. The registry holds the stage.
- **On failure:** if the check fails, shadow does not start. Stopping shadow is the same operation with the block cleared, and it takes effect on the next poll. Changing the percent or salt restarts the 7-day clock (step 13).

### 11. The shadow worker runs the candidate
- **Starts it:** a message from step 6 arrives. Workers are a separate deployment sized for the candidate, on the same hardware class as the API so the latency numbers are meaningful.
- **Data moves:**
  - The worker looks up the candidate's own feature set itself. The user's response used only the active version's features and was unaffected by the candidate's needs.
  - It applies the same freshness and completeness rule as step 3, using the candidate's required list.
  - It runs inference with a 90 ms deadline and writes a pair record to the shadow results table: request ID, user ID, both item lists, candidate latency, outcome, and both `source_ts` values.
- **State:** the queue, the workers' memory, and the results table. Nothing here is on the user path and the user never sees the output.
- **Outcome classes:**
  - `ok`
  - `error` (exception, timeout, invalid output)
  - `skipped_features` (record missing or lacking the candidate's features)
  - `dropped_stale` (the message was over 60 s old, which makes the pair no longer comparable)
- **On failure:**
  - Worker crashes, backlog and result-write failures affect only shadow. They show up as fewer pairs and a higher drop rate.
  - The user's latency cannot be affected, because step 6 never waits.

### 12. Comparing results
- **Starts it:** a scheduled job, hourly, over the results table.
- **Data moves:** per pair it computes overlap@20, rank correlation on shared items, share of popular items, catalogue coverage and duplicate or unknown-item counts. It aggregates by day and by user segment, and writes the aggregates to a report table.
- **State:** the report table, read by a dashboard.
- **On failure:** a failed job leaves yesterday's report stale, and the dashboard shows the report's age.
- **Limit of this evidence:** shadow shows how the candidate's lists differ from the active ones and whether it runs reliably. It cannot show whether users would click more on them. That question is what the open product decision is about (step 14).

### 13. The shadow gate
- **Starts it:** daily, and on demand when someone asks to promote.
- **Data moves:** the evaluator reads the results and writes a gate report: shadow time, pair count, drop and skip rates, error rate and p99 inference latency. Pass requires all of:
  1. At least 7 days of shadow at 10%, counting only time when the pipeline was healthy. Days with a pipeline outage or a config change (step 10) do not count.
  2. Error rate under 0.5%. This is `error / (ok + error)`.
  3. p99 inference latency under 80 ms.
  4. Skip and drop rates reported alongside, so a high skip rate cannot hide behind a good error rate. The team should set a ceiling for these.
  5. A minimum pair count large enough that the error rate's confidence interval sits under 0.5%.
- **State:** the gate report is stored against the registry entry.
- **On failure:** a failed gate keeps the candidate in shadow or sends it back for retraining. The report names the failing criterion. A fixed candidate is a new version with a new 7-day clock.

## Promotion and rollback

### 14. Decision point: live A/B test or straight to 100%
Product has not decided. Steps 1 to 13 and 15 to 16 do not depend on the answer, so nothing blocks building them. The only build-now work is a **seam**: the handler gets its model from a single `select_version(user_id, snapshot)` function that returns the active version today. If A/B is chosen, only that function and the config schema change, and it is a code change that needs a deploy. If it is not, nothing has been built that goes unused.

- **Path A, A/B test between shadow and the full switch.**
  - The config gains an `exposure` block: candidate, percent, salt. `select_version` assigns users by stable hash, independent of the shadow salt.
  - Every response and log line records which version produced it.
  - Outcome events (clicks) are joined to the version.
  - Product must define the success metric, duration and stopping rules.
  - Stopping the test means setting exposure to 0, effective within the same 15 s poll.
  - Exposed users who take the fallback get the popular list, exactly as in step 5.
  - If the test succeeds, go to step 15.
- **Path B, straight from shadow to 100%.**
  - After the gate (step 13) and approval, go to step 15. No new code is needed.
  - The risk is that the first real-user exposure is everyone. Rollback (step 16) is the safeguard.
- **Open question for either path:** does the A/B stage need its own ML lead approval? This plan assumes the approval attaches to the version and covers both.

### 15. Promotion
- **Starts it:** the gate report passes, the ML lead approves, and (Path A only) the A/B stage ends in favour of the candidate.
- **Data moves:**
  - The approval is recorded in the registry: who, when, version and the hash of the gate report.
  - A promotion operation, the only writer of `active_version`, checks that the stage is `shadow` (or `live_test` in Path A), the gate report passed and is recent, approval exists for this exact version, and the feature check from step 8 passes right now.
  - It then writes the new `active_version` to the config store, stores the previous version as `rollback_target`, clears the shadow block, and sets the stage to `active`.
  - The API instances pick the change up through step 9. Each loads the new version, so the active switch is within one poll plus load time.
- **State:** config store (pointer), registry (stage, approval, rollback target).
- **On failure:**
  - A failed check rejects the promotion with the reason. The pointer does not change.
  - Instances that fail to load stay on the old version (step 9).
  - Watch fallback rate, error rate and p99 latency for the first hours after promotion, compared with the previous version.

### 16. Rollback
- **Starts it:** an on-call engineer, on alert or judgement. This plan does not trigger rollback automatically. Whether to automate it can be decided later, by adding a rule on the alerts above.
- **Data moves:**
  - A rollback operation writes the `rollback_target` (or any previously active version) to `active_version`. It first runs the step 8 feature check against that version. It requires no 7-day wait and no approval.
  - Instances see the new revision within 15 s and swap to the already-warm model.
  - Total time is expected well inside the 1-minute requirement.
- **State:** the config store pointer. The registry records the event and marks the bad version `retired`.
- **On failure:**
  - If the target fails the feature check (for example a feature has since been retired), the rollback is refused. Rule to prevent this: no feature may be removed from the online store while the active or rollback-target version needs it.
  - If config writes fail, the on-call retries. Instances keep the last snapshot meanwhile.
  - As a last resort, an emergency switch sets `active_version` to none. Every request then takes the fallback, which keeps the home page working while the problem is fixed.

## Open items

1. Product decision on A/B versus straight to 100% (step 14), and, if A/B, the success metric and duration.
2. Confirm that the shadow gate and approval also apply before any A/B exposure.
3. Confirm falling back on inference failure and invalid output, and the 90 ms inference deadline (and that the remaining 30 ms is enough overhead).
4. Set the ceilings for skip and drop rates and the minimum pair count (step 13).
5. Decide whether rollback should ever be automatic.
