# Recs API plan

The home page calls `GET /recommendations?user_id=...`. The API reads the user's fresh features from an online store, runs the active model inside its own process, and returns 20 item IDs, or a popular-items list if anything is missing or slow. Models are immutable numbered versions in a registry, and the API switches versions by polling the registry, so a switch or rollback needs no redeploy. A candidate version first runs in shadow on a copy of 10% of traffic, and is promoted only when a daily report meets the criteria and the ML lead runs the promote command. Today, recommendations are precomputed nightly into a table. This plan replaces that with per-request computation.

## Terms

- **Online store**: a key-value store of the latest features, keyed by user ID.
- **Materialization**: the hourly job that copies features from the warehouse into the online store.
- **Feature list**: the names of the features the latest materialization run copied.
- **Model registry**: stores each trained model as an immutable, numbered version, with the list of features that version needs.
- **Alias**: a named pointer to one registry version. The aliases are `active`, `previous` and `shadow`. Exactly one version is active at a time.
- **Popular list**: the popular-items list, recomputed daily. Each API instance keeps the latest copy in memory.
- **Fallback**: a response that carries the popular list instead of model output.
- **Shadow**: running a candidate version on a copy of real traffic, with its output never shown to users.
- **Shadow queue**: the queue the API sends shadow messages to. Shadow workers read from it.
- **Prediction log**: one row per shadow run.
- **Feature check**: a load-time test that every feature a model needs is in the feature list.

## Rules that apply throughout

- Total p99 budget for `/recommendations` is 150 ms. The feature lookup gets 30 ms and the model call gets 80 ms (my choice, equal to the promotion latency limit).
- Features older than 6 hours count as missing.
- Switching the active version needs no redeploy, and a rollback takes effect within 1 minute.
- A candidate version must never run, in shadow or as active, against features the online store does not have. The feature check (step 4) enforces this. A candidate may need features the active model does not use.

## Steps

1. **Materialization (every hour).** A job copies features from the warehouse into the online store, one row per user, and stamps each row with its copy time. Each run also writes the feature list. If a run fails, requests keep using the rows already there. Rows older than 6 hours count as missing.

2. **Registry and aliases (when training finishes, or when a person acts).** Training registers a model, and the registry assigns the next number. Only three actions change aliases: shadow-start, promote and rollback. Shadow-start is a manual command that sets the shadow alias to a registered version. Nothing starts shadow automatically after training.

3. **Request path (on each `GET /recommendations?user_id=...`).**
   - The API reads that user's feature row from the online store, with a 30 ms limit. There is no cache.
   - It runs the active model, held in memory in the instance, on that row (80 ms limit), and returns 20 item IDs.
   - A normal response is `{"items": [...20 IDs], "fallback": false}`.
   - It returns the fallback instead, with the same shape, 20 popular IDs and `"fallback": true`, when any of these happens: the lookup times out, the user has no fresh features, the model call errors, or the model call passes 80 ms.
   - The fallback reads only memory, so it cannot fail at request time.
   - The popular list is recomputed daily. If a recompute fails, instances keep the last copy.

4. **Model loading (at instance startup, then every 30 seconds).**
   - At startup, an instance loads the active version and the popular list before it is marked ready. If that first load fails, it stays not ready and raises an alert.
   - After startup, each instance checks the registry every 30 seconds. If the active alias points to a new version, the instance loads it in the background and runs the feature check. The check compares feature names only, never a user's row, and runs only at load time. A user whose row lacks features is handled by step 3.
   - If the check passes, the instance swaps to the new model in one step. Requests already running finish on the old model.
   - If the check or the load fails, including when the target is a rollback target, the instance keeps the model it has and raises an alert.
   - The 30 second poll plus load time keeps a switch or rollback inside 1 minute.

5. **Shadow (after each response, for users in shadow).**
   - A user is in shadow if hash(user_id) mod 100 is below 10, so a given user is always in or always out.
   - After sending the response, the API puts a message on the shadow queue: user ID, features, the active version's number and its items. Sending is fire-and-forget. If it fails or the queue is full, the message is dropped.
   - Shadow workers load the shadow-alias version the same way instances do: they check every 30 seconds, load a changed version in the background, and run the feature check. If the check fails, that version does not run.
   - A worker takes a message, runs its loaded shadow version, and writes one prediction-log row: time, user, shadow version, shadow items, active version, active items, latency, and whether it errored.
   - If the shadow alias is unset or no version is loaded, the worker drops the message and writes no row.
   - When the alias changes, a worker keeps its current version until the new one has loaded. Each row records the version actually used.
   - A worker error is logged and not retried.
   - The user's response never waits on or uses shadow output, so nothing that goes wrong in shadow can slow or break it.

6. **Daily comparison (once a day).** A job reads the prediction log and writes a dated report for the ML lead, per shadow version. The report has:
   - days in shadow: the distinct dates of that version's rows, counting only days it held the shadow alias;
   - error rate;
   - p99 inference latency;
   - overlap between its items and the active items stored in the same row.

7. **Promote (when the ML lead decides).** The ML lead reads the report and runs the promote command for one candidate version. The command refuses unless all of these hold:
   - that version is the current shadow alias;
   - it has a report from the last 24 hours (my choice, matching the daily job);
   - that report shows at least 7 days in shadow, error rate under 0.5% and p99 inference latency under 80 ms.

   Running the command is the ML lead's approval, and it records who ran it and when. If it succeeds, it moves the active alias to the candidate, and the old active version becomes previous (the switch). Product has not decided whether a live A/B test comes between shadow and this switch, so this plan does not choose. The steps work either way.

8. **Rollback (when someone decides to).** A person moves the active alias back to previous. Instances pick it up within 1 minute through step 4.

## What happens when things fail

| What fails | What happens |
|---|---|
| Materialization run | Requests keep using existing rows until they pass 6 hours old, then count as missing. |
| Feature lookup times out, or no fresh features | Fallback response. |
| Model call errors or passes 80 ms | Fallback response. |
| Daily popular-list recompute | Instances keep the last copy. |
| First model load at startup | The instance stays not ready and alerts. |
| Later model load or feature check, including rollback target | The instance keeps its current model and alerts. |
| Shadow enqueue fails or queue full | The message is dropped. The response is unaffected. |
| Shadow worker error, or no shadow version loaded | Logged or dropped, no retry, and no row is written when no version is loaded. |
| Promote criteria not met, or report stale | The command refuses. |

## Open questions

- Does Product want a live A/B test between shadow and the full switch? The plan works either way.
- Who may run shadow-start, promote and rollback is not decided.
- What candidate pool the model ranks the 20 items from, and how it gets it, is not decided in this plan.
- Whether days in shadow must be consecutive is not decided.
- Where the prediction log is stored and where the daily job publishes the popular list is not decided.
