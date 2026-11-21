# Recommendations API: serving, model versions and shadow testing

## Summary

Today, recommendations are precomputed each night into a table, and the home page reads that table. This plan replaces that with `GET /recommendations?user_id=...`, which returns 20 item IDs computed per request from the latest features, with a p99 budget of 150 ms for the whole call. A request reads one user's features from a fast key-value store, runs the active model in memory and returns the result. If features are missing or too old, or the model fails, it returns a popular-items list marked as a fallback. New model versions are registered, tried in shadow on 10% of users (the model runs on a copy of the traffic and its output is never shown), and made active only after passing a gate and getting approval. Switching the active version is a pointer change in a registry, so it needs no redeploy and can be rolled back within 1 minute.

## Decisions I made (please confirm or change)

These are my choices, not requirements.

- **Model failure.** The brief defines fallback only for feature problems. I also return the popular list, marked as a fallback, when the active model errors or exceeds its time limit. The alternative is an HTTP 5xx.
- **Latency budget.** The 30 ms lookup is fixed. The rest is my split of the 150 ms total:

  | Part | Budget |
  |---|---|
  | Feature lookup | 30 ms (fixed) |
  | Model inference | up to 80 ms |
  | Everything else (parsing, hashing, response, in-service network) | about 40 ms |

  The 80 ms inference limit equals the promotion gate's latency limit, so an active model is never allowed to be slower than the one that earned promotion.
- **Shadow user selection.** One fixed salt for every candidate: a user is in shadow if `hash(salt + user_id) mod 100 < 10`. A user is always in or always out. Every candidate sees the same 10% of users. The salt is never changed, because changing it would reshuffle the group.
- **"7 days in shadow".** Seven days of accumulated shadow time while traffic is being processed. A day when shadow was paused or broken does not count.
- **Rollback needs no approval,** because speed matters. The reason is recorded.
- **Pointer poll interval:** 10 seconds.

## Open decision: live A/B test

Product has not decided whether a live A/B test (showing the candidate to a slice of real users) comes between shadow and the full switch, or whether we go straight from shadow to 100%. This plan chooses neither. See "The A/B gap" below for what stays the same either way.

## Terms

- **Online feature store:** a key-value store, key = user ID. Each record holds all of a user's feature values, an `as_of` time (when the warehouse snapshot was taken) and a feature schema ID.
- **Materialization job:** the hourly job that copies features from the warehouse into the online store.
- **Model registry:** where every trained model is kept as an immutable, numbered version. Each version has a manifest: artifact location, required feature names and schema, status, evidence and approval.
- **Active pointer:** the one mutable value in the registry. It names the single active version.
- **Shadow:** running a candidate version on a copy of real traffic. Its output is stored and compared, never shown to a user.
- **Candidate:** a registered version being tried in shadow.
- **Fallback:** the popular-items list (recomputed daily), returned with `fallback: true` and a reason, in place of model output.
- **Warm:** already loaded in an API instance's memory.

## Where state lives

| Component | State it owns |
|---|---|
| API service (stateless, many instances) | In memory only: loaded models (active and previous), a copy of the popular list, the last-seen active pointer |
| Online feature store | One whole record per user (see terms) |
| Materialization job | Nothing except its last-success time, published as a metric |
| Model registry | Versions and manifests, the active pointer, approvals, shadow start times, reports, change history |
| Popular-items job (daily) | Writes the popular list to a small store the API reads |
| Shadow queue and workers | The queue holds shadow jobs briefly. Workers hold the loaded candidate. Both run outside the API, on separate machines of the same hardware class as the API |
| Shadow results store | One row per shadow job, keyed by request ID |

## How a request works

All model selection goes through one function, `resolve_model(user_id)`. Today it returns the active version.

1. **Request arrives.** Trigger: the HTTP call. A request ID is generated. A missing or invalid `user_id` gets a 400 (not a fallback case).
2. **Resolve the model.** The API reads its in-memory active pointer. No network call. On cold start the instance is not ready until it has loaded an active version. If the registry later becomes unreadable, the instance keeps the last good pointer.
3. **Feature lookup.** One key-value get by user ID, hard timeout 30 ms, no retry (a retry would use budget the model needs). A timeout, a store error or no record goes to fallback.
4. **Freshness and compatibility checks** (no I/O). If `now - as_of` is over 6 hours, treat features as missing. If the record lacks any feature the active manifest requires, or its schema does not match, treat features as missing. The second check is the runtime guard for "never run against features the store does not have". Each cause (`timeout`, `no_features`, `stale_features`, `missing_feature`) is counted separately.
5. **Inference.** The feature vector goes into the in-memory model, which returns 20 item IDs. A hard stop at 80 ms keeps the 150 ms budget. Any error or timeout goes to fallback with reason `model_error`.
6. **Fallback response.** The cached popular list (20 IDs) with `fallback: true` and the reason. If the daily job has not refreshed the list, the last copy is kept. At startup an instance fetches the list and is not ready until it has one. If even this fails, return a 5xx, which should not happen after a successful startup.
7. **Response and shadow hand-off.** The response holds the 20 IDs, the fallback flag and the version that produced them (for logs and later A/B analysis). After the response is sent, if the user is in the shadow group and the response was not a fallback, the API puts a shadow job on a bounded queue without blocking. The job holds the request ID, user ID, the feature vector from step 3, the active version and the active output. The shadow worker does not do its own feature lookup. Nothing on the shadow side can affect the user: if the queue is full or unreachable the job is dropped and a drop counter goes up, and any exception is caught and logged.

## How features stay fresh

8. **Hourly materialization.** Trigger: the hourly schedule. Each user's record is written whole, with the snapshot time as `as_of`, so a record is never half old and half new.
   - If the job fails, old records stay and are served until they are 6 hours old (step 4 enforces this); then those users fall back. A partly failed run is safe: users it did not reach keep their previous record.
   - Alert after 2 hours without success and page at 4 hours. That leaves 2 hours to fix it before users start falling back.
   - A feature that a candidate needs must be added to the job and the store schema before the candidate enters shadow. A feature is never removed while the active version or the previous active version needs it.

## Model versions and switching

9. **Register a version.** Trigger: a training run finishes. The registry stores the artifact and manifest and assigns the next number. The status starts as `registered`. A version is never edited; if something is wrong, register a new one. A failed upload leaves no version.
10. **Load models.** Trigger: startup, or a new active pointer seen in step 11. The instance downloads the artifact, loads it and runs a smoke inference on a fixed sample before switching to it. It also keeps the previous active version warm, so a rollback needs no download. If the download, load or smoke test fails, the instance keeps serving the old version and alerts with the instance and version.
11. **Pointer refresh.** Every instance polls the active pointer (version number, change ID) every 10 seconds. If the registry is unreachable, the instance keeps its last pointer and alerts. Time to take effect is the poll interval plus the load time. Rolling back to the warm previous version takes about 10 seconds. Rolling back to an older version that is not warm depends on its load time, which must be tested to stay under about 45 seconds; otherwise keep more past versions warm.

## Shadow: running and comparing

12. **Start shadow.** Trigger: someone moves a registered version to `shadow`. The registry runs a compatibility check: every feature in the manifest must exist in the store schema, and the materialization job must be producing it. If not, the version is refused with the reason. If the workers cannot load it, the status stays `registered`. Otherwise the 7-day shadow clock starts and the workers load the candidate.
13. **Shadow inference.** Trigger: a shadow job arrives. The worker runs the candidate on the supplied feature vector and writes a row: request ID, user ID, candidate version and output, active version and output, latency, and an error or none.
    - A worker crash or timeout writes an error row, which counts toward the error rate.
    - If the worker cannot write at all, the job is lost and counted as `dropped`.
    - If the user's record lacks a feature the candidate needs, the row is `skipped`, which is neither an error nor a success.
14. **Compare and monitor.** Continuously, summarized daily, into a report on the candidate's registry record.
    - Gate metrics: error rate (errors divided by attempted; skipped and dropped are shown separately), p99 inference latency, days in shadow and volume.
    - Informational comparison: overlap of the two 20-item lists and where they differ. No quality threshold was given, so none is invented; the ML lead decides what the comparison means.
    - If the drop rate is high (for example over 5%) or volume is low, the report says the sample is not trustworthy. Dropped jobs never count as passes. Drops should be watched in case they are not random.

## Promotion and rollback

15. **Promotion gate and switch.** Trigger: someone requests promotion. The tool checks all of these:
    1. at least 7 days in shadow;
    2. error rate under 0.5%;
    3. p99 inference latency under 80 ms;
    4. the compatibility check passes again right now against the live store;
    5. the ML lead's approval is recorded against this version number and the report they saw. An approval for one version is not valid for another.

    If all pass, it writes the active pointer with a compare-and-set against the expected current version, and records the previous version as the rollback target. Any failed check blocks the write and says which. A pointer write that loses a race fails and must be retried deliberately. Instances then pick up the change through steps 10 and 11; one that cannot load the new version stays on the old one and alerts. Keep watching until every instance reports the new version.
16. **Rollback.** Trigger: an operator action (automatic, alert-driven rollback is not specified). The pointer is written back to the recorded previous version, which is still warm, so instances switch at the next poll, within about 10 seconds and inside the 1-minute requirement. If the target's features were removed from the store, users fall back (step 4), which is why step 8 forbids that removal. If the registry is down, instances cannot see the rollback, so registry availability counts as part of the rollback requirement. A rolled-back candidate returns to `shadow` or `registered`, and its 7 days restart if retried.

## The A/B gap

Only this section depends on the open decision.

- **Same either way:** the gate in step 15 and the single pointer write at 100%. Responses and logs record which version produced each result. Because selection goes through `resolve_model(user_id)`, a per-user rule can be added later in one place.
- **If product goes straight to 100%:** step 15 is the last step and nothing is added.
- **If product chooses an A/B test:** a new stage sits between steps 14 and 15. Product must supply slice size, how users are assigned (stable by user ID, ideally independent of the shadow group), duration, success metric and who decides. The registry would need a second pointer (candidate and its share), and rolling back the slice must be as fast as step 16.
- **To settle first:** does serving the candidate to real users in an A/B slice count as "becoming active"? If so, the 7-day, 0.5%, 80 ms gate and ML lead approval must come before the slice. If not, someone must say what gate applies.

## Failure summary

| Where | What goes wrong | What happens |
|---|---|---|
| Lookup | Timeout, store error, no record | Fallback, no model call |
| Check | Record older than 6 hours, or required feature missing | Fallback, counted by reason |
| Inference | Error or over 80 ms | Fallback with `model_error` |
| Shadow hand-off | Queue full or down, any exception | Job dropped and counted; user unaffected |
| Materialization | Job fails | Old records served up to 6 hours; alerts at 2 and 4 hours |
| Model load | Download, load or smoke test fails | Instance keeps old version and alerts |
| Registry | Unreachable | Instances keep last pointer; no switch or rollback possible |
| Promotion | A gate check fails, or the write loses a race | No change; reason shown |

## What to build first

1. Steps 1 to 8: request path, fallback and freshness check (the part of the 150 ms budget easiest to break).
2. Steps 9 to 11 and 16: versions, switching and rollback. Test that rollback takes effect in under 1 minute.
3. Steps 12 to 15: shadow and the promotion gate.
4. The A/B section only after product decides.

## Open questions

- Confirm or change the decisions listed near the top.
- Product: A/B test or straight to 100%, and which gate applies to an A/B slice.
- Whether rollback should ever be automatic.
