# Recs API plan

Today a nightly job writes each user's recommendations into a table, and the home page reads from that table. This plan replaces it with a call made for each request. `GET /recommendations?user_id=...` reads the user's features from an online feature store, runs the active model version on them and returns 20 item IDs. If the features are missing or slow, the API returns a daily popular-items list and marks the response as a fallback. New model versions run in shadow on 10% of users, where their output is logged and never shown. Switching or rolling back a version means moving a pointer in the model registry, so the API is not redeployed.

## Terms

- **Warehouse**: the main data store, where features are computed in full.
- **Online feature store**: a key-value store keyed by user ID. The API reads features from it. It holds a copy made every hour.
- **Materialization**: the hourly job that copies features from the warehouse into the online feature store.
- **Model registry**: the list of trained models. Each trained model is one numbered version, and a version is never edited after it is registered.
- **Alias**: a named pointer to one registry version. This plan uses three: `active`, `previous` and `shadow`.
- **Active version**: the one version whose output users see. Exactly one at a time.
- **Shadow version**: the candidate version that runs on a copy of traffic. Its output is logged and never shown.
- **Shadow queue**: a queue where the API leaves shadow jobs, so the API does not wait for them.
- **Shadow workers**: processes that take jobs off the shadow queue and run the shadow version.
- **Prediction log**: the store where shadow results and served results are written, so they can be compared.
- **Popular-items list**: 20 item IDs, recomputed daily, used as the fallback.
- **Feature check**: before a model runs, confirm that every feature it needs is present for this user and no older than 6 hours.
- **Fallback**: a response built from the popular-items list. It is marked as a fallback.

## How it runs

### Request path

Trigger: the home page calls `GET /recommendations?user_id=...`. The whole call must finish within 150 ms at p99.

1. **Look up features.** The API reads the user's features from the online feature store. The lookup has a 30 ms limit. The store keeps the features. If the lookup times out, or the user has no features, go to step 4.
2. **Feature check.** The API checks the features the active model needs. Any feature that is missing or older than 6 hours sends the request to step 4. If all are present, go to step 3. The model never runs on features the store does not have.
3. **Run the active model.** The API runs the version that the `active` alias names, and keeps the top 20 item IDs. The model is loaded into each API instance (see Model versions and switching). If the model errors, go to step 4. The brief does not say this; see Open questions.
4. **Fallback.** The API returns the popular-items list and marks the response as a fallback.
5. **Respond.** The API returns 20 item IDs, with the fallback mark when step 4 ran. If this user is in the shadow group, the API also queues a shadow job without waiting for it (see Shadow runs and comparison).

### Feature freshness

Trigger: the hourly schedule. The materialization job copies each user's features from the warehouse into the online feature store, replacing the previous copy. If the job fails, the store keeps its last copy. The API keeps serving those features for up to 6 hours. After that they count as missing, so requests go to the fallback.

The popular-items list is recomputed once a day by a separate job. If that job fails, the previous day's list stays in use. This is our choice; the brief does not say.

### Model versions and switching

- Each trained model is registered as a new numbered version. Versions are never edited.
- Three aliases point to versions. `active` is the version users see. `previous` is the version that was active before the last switch. `shadow` is the candidate in shadow, if there is one.
- Each API instance checks the `active` alias every 30 seconds. When the alias has moved, the instance loads that version and reads which features it needs, so step 2 can check them. The instance keeps using the old version until the new one has loaded. If loading fails, it keeps the old version and logs the error. Our choice: a 30-second check keeps a switch or rollback under one minute, with room for loading.
- Because each instance checks on its own timer, instances can run different versions for up to about 30 seconds after a switch.
- A switch is allowed only through the promotion check below.

### Shadow runs and comparison

Trigger: a request from a user in the shadow group, while the `shadow` alias is set. The shadow group is 10% of users, picked by a fixed function of the user ID, so a user is always in the group or always out of it.

1. **Queue.** The API puts a shadow job (user ID and shadow version) on the shadow queue and does not wait. If the queue cannot take the job, the API logs that and carries on. Our choice: the job is dropped.
2. **Check.** A shadow worker takes the job, reads the user's features from the online feature store, and runs the feature check for the shadow version. If the check fails, the worker writes a "skipped" row to the prediction log and runs no model.
3. **Predict.** Otherwise the worker runs the shadow version and writes its 20 item IDs and its inference time to the prediction log.
4. **Served result.** For shadow-group users, the API also writes the 20 items the user was served to the prediction log. Our choice: the brief does not say where the served result comes from, and the comparison needs it.

If a worker errors or times out, it writes the error to the prediction log. Shadow output is never shown to a user, and no user response waits on shadow work.

Daily comparison job. Trigger: once a day. It reads the day's prediction log for the shadow version. For each user it compares the candidate's 20 IDs with the 20 that were served. It writes a daily summary with the days in shadow so far, the error rate, the p99 inference latency and the overlap between the two lists. Our choice: overlap is reported; the brief does not name a comparison metric. If the job fails, that day has no summary, and that day cannot count toward approval.

### Promotion

Trigger: someone asks to make the candidate active. The switch goes ahead only when the latest daily summary shows all of these:

- at least 7 days in shadow;
- an error rate under 0.5%;
- a p99 inference latency under 80 ms;
- the ML lead has approved the switch.

If all four hold, `active` moves to the candidate, the old `active` version becomes `previous`, and `shadow` is cleared. Instances pick the change up within 30 seconds. If any check fails, do not move the alias. The candidate stays in shadow, or `shadow` is cleared to stop it.

The step between shadow and this switch is open. Product has not decided on a live A/B test. See Open questions.

### Rollback

Trigger: an operator decides to roll back. The operator moves `active` back to `previous`, and the version that was rolled back from becomes `previous`. Instances pick the change up within about 30 seconds, plus loading time. This meets the 1-minute limit as long as loading takes under 30 seconds.

## Build and rollout order

1. Build the online feature store and the hourly materialization job.
2. Build the model registry, with immutable versions and the three aliases.
3. Build the endpoint: feature lookup, feature check, fallback and the daily popular-items job.
4. Add model loading on each API instance, with the 30-second alias check.
5. Add the shadow queue, shadow workers, prediction log and daily comparison job.
6. Use the aliases for promotion and rollback.

## Open questions

- Product has not decided whether a live A/B test (showing the candidate to a slice of real users) comes between shadow and the full switch, or whether the switch goes straight to 100%. This plan leaves that step open.
- The brief does not say what happens if the whole call goes over 150 ms.
- The brief does not say what happens if the active model errors. This plan returns the fallback.
- Does the 6-hour limit count from when the warehouse computed a feature, or from when it was copied into the online store?
- For the 0.5% error rule, does an error mean only a failed shadow run, or also a run skipped for missing features?
- Where do the popular-items list, the prediction log and the daily summary live? The brief does not say.
- How is the ML lead's approval recorded, and who may trigger a rollback?