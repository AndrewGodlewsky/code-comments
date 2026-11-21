# Recommendations API plan

## Goal

The home page calls `GET /recommendations?user_id=...`. The API computes 20 item IDs per request with a model, using the latest features. It replaces the nightly precomputed table. The whole call has a p99 latency budget of 150 ms (99% of calls must finish within it).

## How it fits together

- An hourly job copies features from the warehouse into a fast key-value store.
- Each request reads one user's features from that store, runs the model and returns 20 items. If the features are unavailable, it returns a fixed popular-items list instead.
- Models live in a registry as numbered versions that never change. Named pointers (aliases) say which version plays which role. Moving an alias switches or rolls back a model, with no redeploy.
- A candidate model is first tried "in shadow". For a fixed 10% of users, a copy of each request is run through the candidate in the background. The results are logged and never shown to anyone. After 7 days in shadow, passing the metric thresholds and getting the ML lead's approval, the candidate can become the live model.

## Terms

- **Online feature store**: a key-value store keyed by user ID, holding the model's input features. Each stored row carries the time it was materialized.
- **Materialization**: an hourly job that copies features from the warehouse into the online store.
- **Model registry**: stores every trained model as an immutable, numbered version (v41, v42, ...). Each version records the list of features it needs.
- **Alias**: a named, movable pointer to one version. The aliases are `active` (served to users), `previous` (the last active version, kept for rollback) and `shadow` (the candidate under test). Versions never change. Only aliases move, so a switch or a rollback means moving an alias.
- **Shadow**: running a candidate on a copy of real traffic. Its output is logged and never shown to users.
- **Fallback**: the popular-items list, recomputed daily. A response that uses it is marked `fallback: true`.
- **Stale** features: a row materialized more than 6 hours ago. Stale rows count as missing.

## Open decision

Product has not decided whether a live A/B test (showing the candidate's recommendations to a slice of real users) comes between shadow and the full switch. This plan works with either answer. Only step 12 depends on it. The other steps are the same in both cases.

## Part A: Serving a request

**1. Materialize features every hour**
- Starts: an hourly schedule.
- Data: the job reads current features from the warehouse and writes one row per user into the online store, stamped with the materialization time.
- State: the online store. Rows stay until they are overwritten.
- On failure: do nothing to the store. The API keeps serving the existing rows, and an alert fires after the first failed run. Rows older than 6 hours count as missing (step 2), so a long outage degrades to fallback and never serves very old features.

**2. Handle a request: features first**
- Starts: a call to `GET /recommendations?user_id=...`.
- Data: the API looks up the user's features in the online store, asking only for the features that the `active` version lists. The lookup gets 30 ms.
- State: none. The API instance is stateless apart from the loaded models (step 5).
- On failure: if the lookup times out, the user has no row, or the row is stale, the API does not call the model. It returns the popular-items list with `fallback: true` and counts the reason (timeout, missing or stale).

**3. Run the model and respond**
- Starts: step 2 returned fresh features.
- Data: the API runs the in-memory `active` model on the features and returns the top 20 item IDs plus the model version used.
- State: nothing is stored, except that the version number goes into the request log.
- On failure: if the model errors or runs out of the remaining time budget, return the fallback, as in step 2. This goes beyond the brief, which names only feature failures. It protects the 150 ms budget.

**4. Pick requests to copy to shadow**
- Starts: after the API has built its response, so the check adds no time to the user's call.
- Data: the API hashes the user ID. If `hash(user_id) mod 100 < 10` and a `shadow` alias exists, the request is shadow-eligible. The same user always gets the same answer, so the same 10% of users are always in. Fallback responses are skipped, because there was no model output to compare against. For an eligible request, the API puts a message on the shadow queue (step 8).
- State: the rule is code and config. It needs no per-user storage.
- On failure: the API does not wait for the queue and drops the message if the queue is full. Nothing here can touch the user's response.

## Part B: Model versions and switching

**5. Load models on API instances**
- Starts: instance startup, then a poll of the registry every 15 seconds.
- Data: the instance reads where the `active` and `previous` aliases point. If either one changed, it downloads that version in the background and loads it into memory. It keeps `previous` loaded too, so a rollback needs no download. Once a new `active` is fully loaded, the instance swaps to it atomically (in one step, so no request sees a half-loaded model).
- State: the alias pointers live in the registry. Each instance holds the loaded models in memory.
- On failure: if the registry is unreachable, the instance keeps serving what it has. If a download or load fails, or the feature check in step 6 fails, the instance keeps the old active model and raises an alert. A switch needs no redeploy. Instances can disagree for up to about a minute during a switch, and the version in each response and log line makes this visible.

**6. Check features before any alias moves**
- Starts: someone (or a tool) tries to point `shadow` or `active` at a version. Each instance repeats the check when it loads a model (step 5) as a second guard.
- Data: compare the version's feature list with the online store. Every listed feature must be defined in the store, and materialization must have succeeded within the last 6 hours.
- State: the feature list is stored with the version in the registry. The online store is the source for which features exist.
- On failure: refuse the alias change with a message naming the missing features. A candidate that uses new features can therefore run only after those features are in the materialization job. This applies to shadow and to active, with no exceptions. This check is per version. For an individual user whose row lacks one of the candidate's features, see step 8.

## Part C: Shadow

**7. Start shadow**
- Starts: someone registers the new version and sets the `shadow` alias to it.
- Data: step 6 runs first. If it passes, the alias change is recorded with a timestamp, which starts the 7-day clock.
- State: the registry holds the alias and the start time.
- On failure: if step 6 refuses, nothing starts. Moving the alias to a different version restarts the 7-day clock.

**8. Run the candidate on copied traffic**
- Starts: a message placed on the queue in step 4.
- Data: the message holds the request ID, the user ID, the active version and the 20 items that were returned. Shadow workers, a separate service, take messages from the queue. A worker loads the `shadow` version and reads that version's features from the online store itself. The API's features from step 2 are not enough, because the candidate may need features the active model does not use. The worker applies the same freshness rule as step 2. It then runs the candidate and writes one row to the prediction log. The row holds the request ID, both versions, both item lists, the candidate's inference time and any error.
- State: the queue and the prediction log. The log is the permanent record that the comparison job reads.
- On failure: shadow is isolated from users. The queue is bounded and the API never waits for it, so a full or broken queue loses shadow samples and the user is unaffected. Workers run on their own capacity. If the user's row is missing or stale for the candidate's features, the worker skips that request and counts it. If the candidate crashes or hangs, the worker logs an error row, because the error rate is a promotion criterion. Dropped messages are counted and alerted on, so a gap in the data is visible.

**9. Compare results daily**
- Starts: a daily schedule.
- Data: the job reads the prediction log and computes, for the candidate: days in shadow, error rate, p99 inference latency, number of samples, and how much its item lists overlap with the active model's. It writes a report.
- State: reports are stored by date. Nothing here changes any alias.
- On failure: a failed run is retried and alerted. A missing day delays promotion and corrupts nothing.

## Part D: Promotion and rollback

**10. Check the promotion criteria**
- Starts: the daily report (step 9).
- Data: the candidate qualifies only if all of these hold: it has been in shadow at least 7 days, its error rate is under 0.5%, and its p99 inference latency is under 80 ms. The ML lead must then approve, and the approval is recorded with a name and a time. The report and the approval are both tied to the version.
- State: the approval record sits in the registry beside the version.
- On failure: if any criterion fails, the candidate stays in shadow or is dropped. If the ML lead declines, the candidate does not become `active`.

**11. Re-check just before switching**
- Starts: the ML lead's approval.
- Data: run step 6 again, since features could have changed during the 7 days.
- State: none new.
- On failure: abort the switch and report which features are missing.

**12. (Open: A/B test between shadow and the full switch)**
- If Product chooses A/B: before step 13, the candidate is shown to a slice of users picked by user ID, and the results are compared against the active model. The traffic split would be a setting in the registry or config, and the API would need a rule for which model each user gets. The ML lead should say whether the approval in step 10 covers this phase or whether it needs its own. Product would set the slice size and the success criteria, which are not defined here.
- If Product chooses to go straight to 100%: skip this step.
- Do not build this step until Product decides.

**13. Switch**
- Starts: step 11 passed, and step 12 (if used) is complete.
- Data: in the registry, set `previous` to the current `active`, then set `active` to the candidate. Clear the `shadow` alias.
- State: the registry. Instances pick up the change at their next poll (step 5), within about 15 seconds. The new model loads in the background and then swaps in, with no redeploy.
- On failure: if an instance cannot load the new version, it keeps serving the old one and alerts. Watch the error rate and fallback rate for the first hour after a switch.

**14. Roll back**
- Starts: a person decides to roll back, or an alert fires on error rate, latency or fallback rate. Automatic rollback is not planned. A person makes this call.
- Data: set `active` back to the version in `previous`. Instances already hold it in memory, so it takes effect at the next poll (about 15 seconds), well inside the 1-minute requirement.
- State: the registry. Rollback needs neither the 7-day wait nor ML lead approval, because speed matters more than process here. This is an assumption to confirm.
- On failure: if the registry is down, the alias cannot move, and each instance keeps serving what it has. Rollback therefore depends on the registry, which must be highly available.