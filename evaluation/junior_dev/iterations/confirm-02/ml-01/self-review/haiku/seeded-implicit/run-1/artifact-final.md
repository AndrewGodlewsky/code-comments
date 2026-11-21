# Recs API plan

The home page calls a recommendation API to get 20 item IDs for a user. Today those items are computed once each night and stored. The new API computes them on each request, using features at most 6 hours old and the active model version from a model registry. A new model version first runs in **shadow**: it runs beside the live model on a share of real requests, and its output is logged for comparison but never shown to anyone.

## How the parts fit

- Every hour, a job copies user features from the warehouse into a fast key-value store, the online feature store.
- A model registry stores each trained model as a numbered version. Named pointers (aliases) say which version is live, which was live before, and which is under shadow test.
- API instances load the versions the aliases point to into memory and run the live model on each request.
- A fixed share of requests also gets a copy queued for a shadow run. Shadow results go only to a log.
- A daily job summarizes the shadow log. A person approves promotion, and then an operator moves the alias.

## Terms used

- **Warehouse:** the analytics database where user activity is stored.
- **Online feature store:** a key-value store keyed by user ID. Each entry is a **feature row**: one user's features plus the time the row was written. The model reads these during a request.
- **Materialization:** the hourly job that copies features from the warehouse into the online feature store. It also publishes a **feature manifest**, the list of feature names and versions it wrote.
- **Model registry:** the catalogue of trained model versions (v1, v2, and so on). A version is never edited after it is registered. A fix is a new version. Each version records the features it needs, its training date, and its evaluation results.
- **Aliases:** named pointers to versions. `active` is the one version serving users. `previous` is the version that was active before it. `shadow` is the candidate under test, or nothing.
- **Atomic write:** an update that either fully happens or does not happen at all, so no reader sees a half-finished change. Moving an alias is one atomic write. This means there are never zero or two active versions.
- **Feature check:** a test that every feature a version needs appears in the feature manifest. It runs before a version is loaded and again whenever an alias moves.
- **Shadow:** running a candidate on a copy of real requests. Results are logged for comparison and never shown to users.
- **Shadow share:** the 10% of users whose requests are copied to shadow. Each user ID is hashed with a fixed salt into one of 100 buckets. Buckets 0 to 9 are the shadow share. A user is always in or always out, as long as the salt does not change.
- **Fallback:** the popular-items list, returned instead of model output. It is recomputed daily and held in memory on each API instance.
- **Message queue:** a managed buffer between the API and the shadow workers. It has a fixed maximum size.
- **p99:** the response time that 99% of calls beat. The slowest 1% are the ones that count.

## Steps

### 1. Feature store: hourly materialization

- **Starts:** an hourly scheduled run.
- **Data moves:** feature rows are read from the warehouse and written to the online feature store. Each row is stamped with its write time. The job then publishes the feature manifest, which step 4 uses.
- **State:** the online feature store holds the latest rows and the manifest.
- **On failure:** the store keeps the rows it already has. A failed run never deletes rows. The run is retried and the team is alerted. Readers treat any row older than 6 hours as missing, so stale data stops being used 6 hours after the last good write.

### 2. Model registry: numbered versions and aliases

- **Starts:** a training run finishes and registers its model.
- **Data moves:** the model file and its metadata are stored under a new version number. The metadata includes the features the model needs, the training date, and the evaluation results.
- **Aliases:**
  - `active` points to the one version that serves users. Exactly one version holds it at any time.
  - `previous` points to the version that was active before. It is kept so rollback is quick.
  - `shadow` points to the candidate under test, or to nothing.
  - An alias move is the only way a version changes role. Each move is one atomic write.
- **State:** the registry service, backed by a database with one row per version and one row per alias. Approval records (step 7) are stored here too.
- **On failure:** if the registry is unreachable, API instances keep serving the versions they already loaded. A version that fails to register is never used.

### 3. Request path: `GET /recommendations?user_id=...`

- **Starts:** the home page calls the endpoint with a user ID.
- **Budget:** the whole call must finish within 150 ms at p99.
- **Steps inside one request.** These are numbered within this step, so "item 5" means item 5 below.
  1. Read the user's feature row from the online feature store, with a 30 ms timeout. Ask for every feature needed by the active model and by the shadow model, so no second lookup is needed later.
  2. If the read timed out, the row is missing, or the row is older than 6 hours, go to item 5. No model runs.
  3. Check that every feature the active model needs is present in the row. If one is missing, go to item 5.
  4. Run the active model. It returns ranked item IDs. Keep the top 20. Respond with the 20 IDs, the active version number, and `fallback: false`.
  5. Fallback: respond with the popular-items list, `fallback: true`, and the version label `fallback`.
  6. After responding, if the user is in the shadow share, add a job to the message queue. Adding the job does not wait for the queue, so it adds no time to the response. This applies to fallback responses too. The shadow worker in step 5 records a skip if the features are missing.
- **Data moves:**
  - In: the user ID.
  - Read: the feature row.
  - Out: 20 item IDs, a version label, and the fallback flag.
  - The shadow job from item 6 carries the feature row, the active version number, and the 20 IDs the active model returned (empty for a fallback).
  - The request keeps no state after it returns.
- **On failure:** if the model raises an error or passes its time limit, the endpoint returns the fallback and flags it. The time limit must keep the whole call under 150 ms. Its value is open (see Open items).

### 4. Loading versions on API instances, with the feature check

- **Starts:** each API instance checks the registry when it starts and then every 15 seconds. The short interval is what lets a rollback take effect within 1 minute (step 9).
- **Data moves:** when an alias points to a version the instance has not loaded, the instance downloads it and loads it into memory in the background. The current version keeps serving during the load.
- **Feature check:** before a version is used, every feature in its required list must appear in the current feature manifest. A version that fails the check is never run, whether it is `active` or `shadow`. This is the version-level check. The per-user check in step 3, item 3, is separate.
- **Switching on the instance:** once a version is loaded and has passed the check, the instance swaps its in-memory pointer to it in one step. The previous version stays in memory, so rolling back needs no download. No restart or redeploy is involved.
- **State:** loaded models live in each instance's memory. The registry records which version holds which alias.
- **On failure:** if a download, load, or check fails, the instance keeps serving its current `active` version, retries, and alerts. An instance never serves a version it has not loaded and checked. Between a switch and the moment the last instance picks it up, instances may briefly serve different versions. Each response carries its version number, so this stays visible.

### 5. Shadow: 10% of users, message queue, shadow workers, prediction log

- **Starts:** step 3, item 6, for each request from a user in the shadow share.
- **Data moves:**
  - The queued job holds the user ID, the request time, the feature row from step 3, the active version number, and the 20 IDs the active model returned.
  - A shadow worker takes the job. It checks that every feature the `shadow` version needs is present in the feature row. If one is missing, it writes a "skipped" record and the model does not run. Otherwise it runs the candidate.
  - The worker writes one record to the prediction log. The record holds the user ID, request time, candidate version, the candidate's 20 IDs, inference time, any error, the skip reason if skipped, and the active version's 20 IDs copied from the job.
- **Keeping shadow away from users:** shadow results never reach a response or a cache. The request path only adds jobs to the queue. Workers run in their own pool, so a slow or crashing candidate cannot hold up an API instance.
- **State:** the queue is a managed message queue with a fixed maximum size. The prediction log is an append-only table, meaning rows are only added, never changed.
- **On failure:**
  - If the candidate errors, the error is logged and counted in the error rate.
  - If the queue is full, new jobs are dropped and the drop is counted. The user's response is unaffected.
  - If the workers stop, the queue fills, drops start, and an alert fires. Dropped jobs are counted, so the daily comparison can report how much of the share was covered.
  - If the candidate needs a feature the store lacks, the job is logged as skipped. The model never runs.

### 6. Daily comparison job

- **Starts:** once a day, for the previous day's prediction log.
- **Data moves:** the job reads that day's records and writes one summary row per candidate version.
- **What it computes:**
  - Error rate: failed runs divided by attempted runs. Skipped and dropped jobs are not in this rate. They are counted separately.
  - p99 inference time for the candidate.
  - Skip rate and drop rate.
  - Overlap: how many of the candidate's 20 IDs also appear in the active model's 20 for the same request.
- **Counting days:** the 7-day clock starts when a version gets the `shadow` alias. It restarts if the alias moves. The error rate and p99 are measured across the whole shadow period, not one day.
- **State:** a daily summary table. Step 7 reads it.
- **On failure:** if a day's job fails, it is re-run. A day with missing data never counts toward the 7 days or toward any criterion.

### 7. Promotion

- **Starts:** the candidate's summary shows at least 7 days in shadow, an error rate under 0.5%, and a p99 under 80 ms. The ML lead then reviews the summary.
- **Process:** the ML lead approves the candidate in the registry. The approval records the version number, the approver, and the time. Step 8 cannot run without it.
- **Live test (not decided):** Product has not decided whether a live A/B test goes between shadow and the full switch. A live test would show the candidate's recommendations to a slice of real users. This step is where such a test would sit. The rest of the plan works either way and does not assume either option. Any live test would also need the ML lead's approval.
- **State:** the approval record in the registry.
- **On failure:** if any criterion is not met, the candidate stays in shadow or is retired. Nothing moves. If an approval is withdrawn before step 8, the switch does not run.

### 8. Switching the active version

- **Starts:** an approved candidate, and an operator running the registry's switch action.
- **Steps:**
  1. The registry refuses the switch unless the candidate is approved.
  2. The registry runs the feature check against the current feature manifest. If any required feature is missing, the switch is refused.
  3. In one atomic write: `previous` is set to the old `active` version, `active` is set to the candidate, and `shadow` is cleared or set to the next candidate.
- **Data moves:** only alias pointers change. The switch copies no model file.
- **Effect:** instances pick up the change within their 15-second poll interval (step 4). No redeploy is needed.
- **On failure:** if the registry write fails, nothing changes. If instances fail to load the new version, they keep the old one and alert. If many instances fail, roll back (step 9).

### 9. Rollback

- **Starts:** an operator decides to roll back, usually after an alert or a bad metric.
- **Steps:** one atomic registry write sets `active` back to `previous`, and sets `previous` to the version being rolled back from, so the change can be reversed.
- **Going back further:** versions are immutable and stay in the registry, so rolling back to an older version uses the same kind of write. Instances that do not hold that older version in memory must download it first, which is slower.
- **Speed:** rolling back to `previous` is a pointer change, because instances already hold it in memory. The target is under 1 minute from the write.
- **Feature check:** the rollback write is an alias move, so the feature check runs again (step 4). If the current manifest no longer has a feature the old version needs, the rollback is refused. See Open items.
- **Data moves:** pointers only.
- **On failure:** if the registry cannot be reached, the rollback cannot be written. Instances keep serving the bad version until the registry returns. This is the main risk in the design. The registry must be highly available, and an on-call runbook should cover this case.

## Open items

- **Live A/B test:** Product has not decided (step 7). The plan does not assume either option.
- **Model time limit:** not set. It must keep the whole call under 150 ms, including the 30 ms feature read.
- **Fewer than 20 items:** the brief does not say whether to fill the list from the popular items or return fewer.
- **Rollback approval:** the brief does not say whether rollback needs the ML lead's approval. This needs a decision before launch.
- **Rollback and the feature check:** if the manifest drops a feature the old version needs, the check refuses the rollback. That is the worst moment to be refused. Decide whether rollback skips the check, or whether the manifest must keep features that a retained version still uses.
- **Popular-items list:** the brief does not say what computes the daily list or what happens if that job fails. Assumption to confirm: each instance keeps the last list it loaded.