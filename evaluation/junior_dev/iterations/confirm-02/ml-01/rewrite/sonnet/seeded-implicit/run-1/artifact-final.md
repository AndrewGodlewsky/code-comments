# Recs API plan

Today the home page reads recommendations from a table that a nightly job fills. This plan replaces that with an API that computes 20 recommendations per request from fresh features. Each request reads the user's features from an online store, runs the active model version, and returns the result, or a popular-items list if anything is missing. Model versions live in a registry. The active version is switched by moving an alias, and a candidate version is first tested in shadow, on a copy of traffic, where users never see its output.

## Terms

- **Online feature store**: a key-value store, keyed by user ID, that holds each user's features for fast lookup.
- **Materialization job**: the hourly job that copies features from the warehouse into the online store.
- **Model registry**: where every trained model is stored as an immutable, numbered version.
- **Alias**: a named pointer in the registry to one version. We use `active`, `previous` and `shadow`. Exactly one version is `active` at a time.
- **Shadow**: running a candidate version on a copy of real traffic and logging its output, without showing it to anyone.
- **Fallback**: the popular-items list, recomputed daily, returned when we cannot call the model. The response is marked as a fallback.
- **Required features**: the feature names a model version needs. They are recorded on the version when it is registered.
- **Prediction log**: a store of shadow results: user ID, version, items, latency, and error if any.

## Fixed requirements

- `GET /recommendations?user_id=...` returns 20 item IDs. The p99 latency budget for the whole call is 150 ms.
- The online feature lookup gets 30 ms.
- Features older than 6 hours count as missing.
- Switching the active version needs no redeploy of the API. A rollback takes effect within 1 minute.
- Shadow runs for 10% of users, chosen by user ID. Shadow output is never shown to a user. Nothing that goes wrong in shadow may slow down or break the user's response.
- No version may run, in shadow or as active, against features the online store lacks.
- A candidate becomes active only after at least 7 days in shadow, with an error rate under 0.5% and p99 inference latency under 80 ms, and only after the ML lead approves.

## How it runs

1. **Materialization (every hour).** The job copies features from the warehouse into the online store and stamps each user's record with the time it was written. State lives in the online store. If the job fails, the store keeps serving what it has. Requests treat a record older than 6 hours as missing (see step 3), and the job's failure raises an alert.

2. **Registering a model.** When training finishes, the version is added to the registry as an immutable, numbered version, together with its required features. Nothing changes for users. State lives in the registry. If registration fails, the version does not exist and nothing else is affected.

3. **Request path (every call to the endpoint).**
   1. Look up the user's features, with a 30 ms limit.
   2. If the lookup times out, the user has no record, or the record is older than 6 hours, do not call the model. Return the fallback, marked as such.
   3. Otherwise run the loaded `active` version. If the model errors or runs past its time limit, return the fallback as well. The model limit is set so the whole call stays within 150 ms (decided: 100 ms, to be tuned from measurements).
   4. Return 20 item IDs.
   5. After responding, if the user is in the shadow group (step 5), put a copy of the request on the shadow queue.

   The API keeps no state of its own. Features come from the online store, the model comes from memory (step 4), and the fallback list is a daily-recomputed file or table that each API instance reads. If the fallback list cannot be read, the instance keeps its last copy.

4. **Loading models on API instances.** Each instance checks the registry every 15 seconds (decided; this is what makes rollback fit in 1 minute). When `active` points to a different version, the instance loads that version in the background and swaps to it only when the load succeeded. Before swapping, it runs the feature check: every required feature of the new version must exist in the online store. If the load or the check fails, the instance keeps serving its current version and raises an alert. If the registry cannot be reached, the instance keeps its current version. State lives in the registry (the alias) and in instance memory (the loaded model).

5. **Shadow.**
   - **Who:** a user is in the shadow group if a stable hash of the user ID, modulo 100, is under 10. The same user is therefore always in or always out.
   - **Starting:** an operator points the `shadow` alias at a candidate version. Shadow workers run the same feature check as step 4 before they start. If any required feature is missing from the online store, the candidate does not run in shadow at all.
   - **Running:** the API puts the user ID and the features it already fetched on a shadow queue, without waiting. If the queue is full or unavailable, the copy is dropped silently. Shadow workers, which are separate from the API, read the queue, run the candidate and write the result to the prediction log. A failed or slow shadow run is recorded as an error in the log and never touches the user's response.
   - **State:** the queue holds copies until a worker takes them. The prediction log holds the results.

6. **Daily comparison.** A daily job reads the prediction log and, for the candidate, reports: the number of days in shadow, the error rate, the p99 inference latency, and how much its items overlap with what the active model returned for the same users. It writes the report where the ML lead can read it. If the job fails, no report is made for that day, and the candidate's days in shadow still count from the log.

7. **Promotion.** A candidate may be promoted only when all of these hold: at least 7 days in shadow, error rate under 0.5%, p99 inference latency under 80 ms, and the ML lead has approved. A person checks the report and records the approval. Product has not decided whether a live A/B test (showing the candidate to a slice of real users) comes between shadow and full switch, or whether we go straight from shadow to 100%. This plan does not choose. Both options use the same two parts: a promotion check (this step) and a switch (step 8). If Product adds an A/B test, it goes between them, and its pass criteria are Product's to define. Until then, this step ends with an approved candidate and no switch.

8. **Switch.** The `active` alias is moved to the approved version, and `previous` is set to the version it replaced. The registry records the change. API instances pick it up through step 4, with no redeploy. The switch is refused if the feature check for that version fails.

9. **Rollback.** The `active` alias is moved back to `previous`. Instances pick this up within one polling interval (15 seconds), which is inside the 1-minute limit. Rollback needs no approval (decided: speed matters more than sign-off). If an instance cannot load `previous`, it keeps serving its current version and alerts.

## What happens when things fail

| Failure | Result |
| --- | --- |
| Feature lookup times out, or user has no features | Fallback, marked |
| Features older than 6 hours (materialization failing) | Treated as missing: fallback, marked |
| Model errors or is too slow | Fallback, marked |
| New version fails to load or fails the feature check | Instance keeps its current version, alert |
| Registry unreachable | Instances keep their current version |
| Shadow queue full or down, or shadow worker fails | Copy dropped or error logged, user unaffected |
| Comparison job fails | No report for that day, retry next day |

## Open questions

- Does a live A/B test sit between shadow and the full switch? Product has not decided. If yes, who defines its pass criteria and its length?
- Inference timeout (100 ms) and registry polling interval (15 seconds) are chosen to fit the budgets and should be tuned from measurements.
- Is the ML lead's approval recorded in the registry, or somewhere else? Not decided.

## Build and rollout order

Build the registry and aliases, then model loading with the feature check, then the request path, then shadow and the comparison job. Promotion and rollback use the registry and need no separate build.
