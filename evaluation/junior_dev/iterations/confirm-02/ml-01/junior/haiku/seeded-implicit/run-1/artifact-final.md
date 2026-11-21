# Recs API plan

## What this is

Today, recommendations are precomputed each night into a table. This plan replaces that with a live call. `GET /recommendations?user_id=...` reads the user's features from an online store, runs the active model, and returns 20 item IDs within 150 ms at p99. Each model is stored as a numbered version, and exactly one version is active at a time. A new version first runs in shadow for 10% of users. It scores their requests, but nothing it returns is shown. It can become active only after it passes the promotion checks and the ML lead approves.

Two rules shape the design. Shadow work never slows down or breaks a user's response. No model ever runs on features the store does not have.

## Terms

- **Online feature store**: a key-value store keyed by user ID. Each user's record holds that user's features and the time the record was written. It holds user features only. Item features are an open question.
- **Materialization job**: an hourly job that copies features from the warehouse into the online store.
- **Model registry**: where every trained model is kept as an immutable, numbered version (v1, v2, ...). A version is never edited. Fixes ship as new versions.
- **Feature list**: the feature names a model version needs. It is saved with the version.
- **Alias**: a name that points at one version. `active` serves users, and exactly one version holds it. `previous` is the version before it. `shadow` is the candidate under test.
- **Feature check**: before a version is used, confirm that every feature in its feature list exists in the online store with the expected type.
- **Popular-items list**: 20 items, recomputed daily, returned when personal recommendations cannot be made.
- **Shadow group**: the 10% of users chosen by `hash(user_id) mod 100 < 10`. The hash is fixed, so a user is always in or always out.
- **Shadow queue**: a buffer that holds shadow jobs until a shadow worker takes them.
- **Shadow worker**: a separate process that takes jobs from the shadow queue and runs the `shadow` candidate on them.
- **Prediction log**: a table with one row for each shadow job, recording what the candidate returned.
- **Daily report**: the output of the daily comparison, stored in the registry with the candidate version.
- **Pooled latency counts**: for each 1 ms bucket, how many calls took that long. Adding these counts across days gives a true p99. Averaging daily p99 values does not.

## How the system runs

### Request path

1. **Request in.** Trigger: the home page calls `GET /recommendations?user_id=...`. Data: the user ID. State: none kept. The 150 ms budget starts now, on arrival.
2. **Read features.** Trigger: step 1. Read the user's record from the online store with a 30 ms limit. Data: the record, read only. If the read times out, the user has no record, or the record is older than 6 hours, go to step 4.
3. **Score.** Trigger: a usable record. If the record lacks any feature in the `active` model's feature list, go to step 4. Otherwise run the `active` model on the record and take its top 20 item IDs. Return them with `fallback: false`. The model must finish within 120 ms of arrival. That leaves 30 ms for the fallback read in step 4. Step 2 takes at most 30 ms, so the model always gets at least 90 ms when it runs. If the model errors or runs past 120 ms, go to step 4. This step records which version ran and how long the model call took.
4. **Fallback.** Trigger: a failure in step 2 or 3. Read the popular-items list from the online store with a 30 ms limit, and return it with `fallback: true`. The model is not called. Data: the list, read only. Step 3 ends by 120 ms, so this read finishes inside the 150 ms budget. If this read also fails, the call returns HTTP 503 and raises an alert.
5. **Queue shadow work.** Trigger: the user is in the shadow group, a `shadow` alias exists, and the response came from step 3. Just before the response is sent, write one job to the shadow queue. The job holds: request ID, user ID, the feature record used, the active version ID, the active top 20, and the active model's latency from step 3. The write does not block, so the response never waits for a shadow result. If the queue is full or the write fails, drop the job and count the drop. The user is unaffected. Fallback responses are never shadowed, because they have no active model output to compare with.

### Feature freshness

- **Hourly load.** Trigger: the hourly schedule. The materialization job copies features from the warehouse into the online store and stamps each record with its write time. If it fails, the store keeps the last records it wrote, and an alert goes to the on-call engineer.
- **Age limit.** A record older than 6 hours counts as missing. Step 2 checks the stamp. If loads keep failing, the store keeps serving the records it has, but once they pass 6 hours old, users get fallback responses (step 4) until the next successful load.
- **Popular-items list.** Trigger: a daily job. It writes the list to the online store under one fixed key. If the job fails, the last written list stays in place.

### Model loading

- **Registration.** Trigger: a model finishes training. It is saved as the next numbered version, with its feature list. State: the registry.
- **Instance startup.** Each API instance reads the aliases and loads `active` and `previous` into memory before it serves traffic.
- **Picking up a change.** Trigger: every 15 seconds, each instance reads the aliases. When `active` points at a version the instance has not loaded, the instance:
  1. loads that version in the background;
  2. runs the feature check;
  3. swaps it in for new requests, and keeps the old version loaded as `previous`.

  Requests already in flight finish on the version they started with. Switching never needs a redeploy. Instances poll independently, so for up to 15 seconds some may serve the new version while others still serve the old one. This is accepted.
- **If loading or the feature check fails.** The instance keeps the version it has and raises an alert. A version that fails the check is never served. An instance with no version loaded serves only fallback responses. An instance that failed the check can differ from the others until the problem is fixed.
- **If the registry cannot be reached.** The instance keeps its current versions and tries again at the next poll. No request fails because of this.

### Shadow

- **Start.** Trigger: an operator points the `shadow` alias at a candidate version. Shadow workers pick it up the same way instances do. They poll every 15 seconds, load the candidate in the background, and run the feature check before use. A job that reaches a worker before the candidate is loaded gets a `skipped` row with the reason "candidate not loaded". The daily report counts these rows, so the gap stays visible.
- **Shadow worker.** Trigger: a job on the shadow queue. The worker runs in its own process, not inside the request. It:
  1. checks that every feature the candidate needs is in the job's record. If not, it writes a `skipped` row and stops. The candidate never runs on missing features;
  2. runs the candidate on that same record with a limit of 150 ms, and takes its top 20;
  3. writes a prediction log row with the candidate's output.

  If the candidate errors or runs past 150 ms, the worker writes an error row. It does not retry. The worker never calls the active model. It copies the active fields from the job. The user never sees any of this.
- **Prediction log.** One row for each shadow job. Each row holds: request ID, user ID, time, the active version and its top 20, the shadow version and its top 20 (or the skip or error reason), the write time of the feature record, the feature values used, and the latency of each model call. The active fields come from the job, and the shadow fields come from the worker. Both models see the same feature values, so the results compare fairly. There is no fallback flag, because fallback responses are never shadowed.

### Daily comparison

- **Trigger.** A scheduled job runs once a day, after the previous UTC day ends, over that day's prediction log rows.
- **What it computes for that day.**
  - Attempts: shadow jobs, with `skipped` rows left out.
  - Error rate: error rows divided by attempts. An error is a candidate exception or a run past 150 ms.
  - p99 latency: the candidate's p99 over all attempts, with timeouts counted at 150 ms, so a timeout cannot make the latency look better than it was.
  - Overlap: how many of the candidate's top 20 items are also in the active top 20.
  - Days in shadow: the number of daily reports stored with the candidate since the `shadow` alias was set to it. One day is one UTC calendar day.
- **What it stores.** The daily report, stored in the registry with the candidate version. It also keeps the counts behind the figures: attempts, errors, and the count of latencies in each 1 ms bucket. Timeouts go in the 150 ms bucket. Promotion pools these counts across days.
- **Who sees it.** The ML lead and the candidate's owner.
- **If it fails.** That day has no report. Promotion cannot pass while any day in the 7-day window lacks one.
- **What it does not measure.** It measures agreement with the active model, and errors. It does not show whether the candidate's recommendations are better. See open questions.

## How we roll out a model

### Promotion

A candidate can become `active` only when all four of these are true:

1. It has at least 7 days in shadow: a daily report exists for each of the last 7 UTC days since the `shadow` alias was set to it.
2. Its shadow error rate over those 7 days is under 0.5%: total error rows divided by total attempts across the 7 days.
3. Its shadow p99 inference latency over those 7 days is under 80 ms. It is computed from the pooled latency counts of the 7 days, not from the daily p99 values.
4. The ML lead approves it, and the approval is recorded on the candidate version in the registry.

Checks 2 and 3 cover all seven days together. A latest-day figure would let a bad earlier day pass.

Checks 1 to 3 come from the daily reports. When they pass, the ML lead reviews the candidate and records approval. The registry enforces the rule. A move of `active` to a candidate is refused until all four are recorded and pass. An operator cannot skip this by moving the alias by hand.

Product has not decided whether a live A/B test (showing the candidate's recommendations to a slice of real users) sits between approval and the full switch, or whether the switch goes straight to 100%. This plan does not choose either option. It defines no step in that gap. If a test stage is added, it needs its own rule for which users see the candidate.

### Switch

Trigger: all four promotion checks have passed. An operator moves the `active` alias to the candidate in the registry. Instances pick up the change as described under Picking up a change. No redeploy is needed.

### Rollback

- **Trigger.** An operator (the ML lead or on-call engineer) decides to roll back, for example after an alert.
- **Action.** In the registry, move `active` back to `previous`. Then point `previous` at the version that was rolled away from, so a second rollback undoes the first. The data is two alias pointers. The old version is still loaded in every instance, so nothing reloads. The promotion checks do not apply, because `previous` was already active.
- **Pickup.** Each instance sees the change at its next 15-second poll and swaps at once. New requests get the rolled-back version. In-flight requests finish on the old one. The 1-minute limit comes from the fixed requirement that a rollback must take effect within 1 minute. The 15-second poll meets it, but only while the registry is reachable.
- **If the registry cannot be reached.** Rollback waits until the registry is reachable. Instances keep serving the current version.

## Open questions

- Whether a live A/B test sits between approval and the full switch. Product has not decided.
- Whether the model scores every item or a candidate set, and where that set would come from. The requirements do not say.
- What counts as a better recommendation. There is no ground truth, so the daily job measures only agreement and errors.
- Whether the store also holds item features, or only the user features described here.
- Who may read prediction log rows, which hold user IDs and feature values.
- What the endpoint should return when the popular-items list cannot be read. The plan returns HTTP 503 and raises an alert.