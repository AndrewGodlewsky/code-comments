# Recommendations API: serving, model versions and shadow testing

## 0. Assumptions and open decisions

Items marked "assumed" are my own choices, not requirements. Please confirm or change them.

- **A/B test (open, not decided here).** Steps 1 to 15 do not depend on whether a live A/B test comes before the full switch. Step 16 holds the gap. It lists what stays the same either way and what product must supply.
- **Model failure (assumed).** The brief only defines fallback for feature problems. If the active model errors or exceeds its time limit, the API also returns the popular list marked as a fallback. The alternative is an HTTP 5xx.
- **Latency budget (assumed).**

  | Part | Budget |
  |---|---|
  | Feature lookup | 30 ms (fixed) |
  | Active model inference | up to 80 ms |
  | Everything else (parsing, hashing, response, network inside the service) | about 40 ms |
  | Total | 150 ms |

  The 80 ms inference limit is the same figure the promotion gate uses. An active model is therefore never allowed to run slower than the model that earned promotion.
- **Shadow user selection (assumed).** One fixed salt is used for every candidate: `hash(salt + user_id) mod 100 < 10`. A user is always in or always out. Different candidates see the same 10% of users. Changing the salt would reshuffle the group and break "always in or out", so it is never changed.
- **"7 days in shadow" (assumed).** This means 7 days of accumulated shadow time with traffic being processed. A day on which shadow was paused or broken does not count.
- **Feature removal (assumed).** Features needed by the active version or the previous active version are not removed from the store.

## 1. Components and where state lives

| Component | State it owns |
|---|---|
| API service (stateless, many instances) | In-memory only: loaded models, a copy of the popular list, the last-seen registry pointer |
| Online feature store (key-value, key = user ID) | One record per user: all feature values, `as_of` timestamp (the warehouse snapshot time) and a feature schema ID |
| Materialization job (hourly) | Reads the warehouse and writes whole user records to the store. No other state |
| Model registry | Immutable numbered versions with a manifest each (artifact location, required feature names and schema, status, evidence, approval), and one mutable **active pointer** |
| Popular-items job (daily) | Writes the popular list to a small store, which the API reads |
| Shadow queue and shadow workers | The queue holds shadow jobs briefly. Workers hold the loaded candidate. Neither is part of the API |
| Shadow results store | One row per shadow job, keyed by request ID |

## 2. Request path

**Step 1. Request arrives.**
- Trigger: `GET /recommendations?user_id=...`.
- Data: the user ID. A request ID is generated.
- State: none.
- Failure: a missing or invalid `user_id` gets a 400. This is not a fallback case.

**Step 2. Resolve the model.**
- Trigger: step 1.
- Data: the API reads its in-memory active pointer, which is the version number and that version's manifest. There is no network call.
- State: the in-memory pointer, refreshed by step 11.
- Failure: if the pointer has never been loaded (cold start), the instance does not become ready. It serves nothing until it has an active version loaded. If the pointer later becomes unreadable, the instance keeps the last good one.
- Note: model resolution is one function, `resolve_model(user_id)`. Today it returns the active version. See step 16.

**Step 3. Feature lookup, 30 ms budget.**
- Trigger: step 2.
- Data: one key-value get by user ID. It returns the full feature record and its `as_of`.
- State: online store.
- Failure: a timeout, a store error or no record all go to step 5 (fallback). The timeout is hard at 30 ms. There is no retry, because a retry would use the budget the model needs.

**Step 4. Freshness and compatibility checks (no I/O).**
- Trigger: step 3 returned a record.
- Data: the checks compare `now - as_of` with 6 hours. They also check that the record contains every feature the active version's manifest requires, with a matching schema.
- State: none.
- Failure: if `as_of` is older than 6 hours, treat the features as missing and go to step 5. If a required feature is absent or has the wrong schema, also treat the features as missing and go to step 5. This is the runtime guard for "never run against features the store does not have". Count these separately from timeouts so the cause is visible.

**Step 5. Fallback response.**
- Trigger: step 3 or 4 failed, or step 6 failed.
- Data: the cached popular list, 20 IDs, with `fallback: true` and the reason (`timeout`, `no_features`, `stale_features`, `missing_feature`, `model_error`).
- State: in-memory copy of the popular list. If the daily job has not refreshed it, the last copy is kept. If the instance has no copy at all, it fetches it from the store at startup and does not become ready until it has one.
- Failure: if even this fails, return a 5xx. This should not happen after a successful startup.

**Step 6. Inference.**
- Trigger: step 4 passed.
- Data: the feature vector goes in. Out come 20 item IDs, which the API returns.
- State: the model is already in memory (step 10). Nothing is persisted.
- Failure: any error or a time limit of 80 ms goes to step 5 with reason `model_error`. The time limit is a hard stop so that the 150 ms budget holds.

**Step 7. Response and shadow hand-off.**
- Trigger: step 6 succeeded, or step 5 ran.
- Data: the response body is the 20 IDs, the fallback flag, and the model version that produced them (used in logs and A/B analysis). After the response is written, if the user is in the shadow bucket, a shadow job is handed off. It contains the request ID, user ID, the feature vector from step 3, the active version and the active output. The shadow worker does not do a second feature lookup.
- State: the shadow job goes to a bounded queue. The hand-off is non-blocking.
- Failure: nothing on the shadow side can affect the user. If the queue is full or unreachable, the job is dropped and a drop counter is incremented. Any exception is caught and logged. The hand-off runs after the response is sent, and never inside a lock the response path needs. Fallback responses and requests where the candidate's required features are missing are not sent (counted as `skipped`, not as errors).

## 3. Feature freshness

**Step 8. Hourly materialization.**
- Trigger: hourly schedule.
- Data: warehouse feature values for each user go to the online store. Each user's record is written whole, with the warehouse snapshot time as `as_of`, so a record is never half old and half new.
- State: online store. The job also publishes its own last-success time as a metric.
- Failure:
  - If the job fails, the old records stay. The API keeps serving them until they are 6 hours old (step 4 enforces that), then those users fall back.
  - Alert when no success for 2 hours, and page at 4 hours. That leaves 2 hours to fix it before users start falling back.
  - A partially failed run is safe because of whole-record writes. Users it did not reach keep their previous record.
  - A new feature column needed by a candidate must be added to the job and the store schema before that candidate enters shadow (step 12). Removing a column is blocked while any version that may serve (active or the previous active) needs it.

## 4. Model versions and switching

**Step 9. Register a version.**
- Trigger: a training run finishes.
- Data: the model artifact and a manifest (required feature names and schema, training data reference). The registry assigns the next number.
- State: model registry. A version is immutable once written. It starts with status `registered`.
- Failure: a failed upload leaves no version. A version that exists is never edited. If something is wrong, register a new one.

**Step 10. Load models in the API.**
- Trigger: the API sees a new active pointer (step 11), or startup.
- Data: the API downloads the artifact for the pointed version, loads it, and runs a smoke inference on a fixed sample before switching to it. It also keeps the previous active version loaded in memory.
- State: instance memory.
- Failure: if the download, load or smoke test fails, the instance keeps serving the old version and emits an alert with the instance and version. Because the previous version stays warm, a rollback does not need a download.

**Step 11. Pointer refresh.**
- Trigger: every instance polls the registry's active pointer every 10 seconds (assumed interval). No redeploy is needed to switch.
- Data: a small pointer record (version number, change ID).
- State: the registry holds it. Each instance holds a cached copy.
- Failure: if the registry is unreachable, the instance keeps its last known pointer and alerts. Worst-case time to take effect is the poll interval plus the load time of step 10. For a rollback to the warm previous version, that is about 10 seconds, inside the 1-minute requirement. Rolling back to an older version that is not warm depends on its load time, which must be tested to be under about 45 seconds. Otherwise keep the last N versions warm.

## 5. Shadow: running and comparing

**Step 12. Start shadow for a candidate.**
- Trigger: someone starts shadow on a registered version through the registry (status `registered` to `shadow`).
- Data: the registry checks the compatibility gate, comparing the candidate's manifest to the online store: every required feature must exist in the store schema, and the materialization job must be producing it. The candidate's shadow clock starts. Shadow workers load the candidate.
- State: registry status, and a record of the start time.
- Failure: if features are missing, the version is refused for shadow with the reason. If the workers cannot load it, the status stays `registered` and the clock does not start. This is the same check as step 4, applied before any traffic is used. The per-request check in step 4 (and in the shadow workers, step 13) still guards against a user whose record lacks the feature.

**Step 13. Shadow inference.**
- Trigger: a shadow job arrives from step 7.
- Data: the worker runs the candidate on the feature vector it was given. It writes a result row: request ID, user ID, candidate version, candidate output, active output, active version, latency, and error or none.
- State: shadow results store. Workers run on separate machines from the API so they cannot take its CPU or memory. They should use the same hardware class as the API, because the 80 ms gate is judged on this latency.
- Failure:
  - A worker crash or timeout writes an error row (counts toward the error rate). If the worker cannot write at all, the job is lost and counted as `dropped`.
  - The user never notices, since the response was already sent.
  - If the candidate's feature check fails for a user, the row is `skipped` and is neither an error nor a success.

**Step 14. Compare and monitor.**
- Trigger: continuously, summarized daily.
- Data: from the shadow results the report computes:
  - **Gate metrics:** error rate (errors / attempted, with skipped and dropped shown separately), p99 inference latency, days in shadow, volume.
  - **Informational comparison:** overlap of the two 20-item lists, and where they differ. No quality threshold was specified, so none is invented here. The ML lead decides what the comparison means.
- State: a report attached to the candidate's registry record.
- Failure: if the drop rate is high (for example above 5%) or volume is low, the report says the sample is not trustworthy. Dropped jobs do not count as passing. The 10% group is fixed by user ID, so the sample cannot be biased by drops that happen at random but should be watched if they are not random.

## 6. Promotion and rollback

**Step 15. Promotion gate and switch.**
- Trigger: someone requests promotion of a candidate.
- Data: the promotion tool checks that:
  1. 7 or more days in shadow;
  2. error rate under 0.5%;
  3. p99 inference latency under 80 ms;
  4. the compatibility check passes again right now against the live store;
  5. the ML lead's approval is recorded against this version number (and the report it saw).

  If all pass, it writes the active pointer with a compare-and-set against the expected current version, and records the previous version as the rollback target.
- State: registry (pointer, approval, history of changes).
- Failure: any failing check blocks the write and says which. An approval for one version is not valid for another. A pointer write that loses a race fails and must be retried deliberately. Instances then pick up the change (steps 10 and 11). If an instance cannot load the new version, it stays on the old one, and the alert from step 10 fires. Do not stop watching the dashboard until all instances report the new version.

**Step 16. The A/B question (gap).**
This step is the only one that depends on the open decision.
- **Same in both options:** the gate in step 15 stays the same. The pointer write at 100% is the same single operation. The response and logs record which version produced each result. All model selection goes through `resolve_model(user_id)` from step 2, so a user-level rule can be added later in one place without touching the other steps.
- **If product chooses to go straight to 100%:** step 15 is the last step, and nothing is added.
- **If product chooses an A/B test:** a new stage sits between step 14 and step 15. Product has to supply: slice size, how users are assigned (stable by user ID, ideally independent of the shadow group), duration, the success metric, and who decides. The registry would need to hold a second pointer (candidate and its share). Rollback of the slice must be as fast as step 17.
- **Question to settle first:** does serving the candidate to real users in an A/B slice count as "becoming active"? If it does, the 7-day, 0.5% and 80 ms gate and the ML lead's approval must come before the A/B slice. If not, someone must say what gate applies.

**Step 17. Rollback.**
- Trigger: an operator action (or an alert-driven action, if you want automatic rollback, which is not specified), after the switch.
- Data: the pointer is written back to the recorded previous version. No approval is required for a rollback (assumed, because speed matters). The reason is recorded.
- State: registry pointer and history.
- Failure: the previous version is still warm (step 10), so instances switch at the next poll, within about 10 seconds and always within the 1-minute requirement. If the target's features have been removed from the store, step 4 will send users to fallback. That is why step 8 blocks removing features that active or previous versions still need. If the registry is down, the instances cannot pick up a rollback, so the registry's availability needs to be treated as part of the rollback requirement. A rolled-back candidate returns to `shadow` or `registered` and its 7 days start again if it is retried.

## 7. What to build first

1. Steps 1 to 8: the request path, the fallback and the freshness check. This is also the part of the 150 ms budget that is easiest to break.
2. Steps 9 to 11 and 17: versions, switching and rollback. Test that a rollback takes effect in under 1 minute.
3. Steps 12 to 15: shadow and the promotion gate.
4. Step 16 only after product decides.
