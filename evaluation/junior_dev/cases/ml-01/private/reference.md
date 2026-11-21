# Plan: Recommendations API with model versions and shadow testing

## Components and where state lives

| Component | What it holds |
|---|---|
| **Warehouse** | Source of truth for user features. Also holds the **prediction log** table. |
| **Online feature store** (key-value) | One record per user: feature values plus `updated_at`. |
| **Model registry** | Immutable numbered versions: model artifact plus a list of required feature names. Three aliases: `active`, `previous`, `shadow`. |
| **Popular-items list** | Object storage, recomputed daily. Each API instance keeps a copy in memory. |
| **Recommendations API** (stateless instances) | In memory: the `active` model, the `previous` model (kept for 24 h) and the popular list. |
| **Shadow queue** | Bounded message queue (capacity 10,000 jobs). |
| **Shadow workers** (separate service) | In memory: the `shadow` model. They never serve user traffic. |
| **Comparison job** | Daily batch job that writes a report for each candidate version. |

## Steps

1. **Materialize features (every hour).**
   - *Trigger:* scheduler, on the hour.
   - *Moves:* user features go from the warehouse to the online store. Each user record is overwritten, with `updated_at` set to the time of the run.
   - *On failure:* the job is retried at the next hour, and an alert fires after 2 failed runs in a row. The store keeps its last good values. Step 3 enforces the 6-hour age limit, not this job.

2. **Register a model version.**
   - *Trigger:* the training pipeline finishes.
   - *Moves:* the artifact and its list of required feature names go to the registry under the next version number. A version is never changed after it is registered.
   - To trial the version, an ML engineer points the `shadow` alias at it (see step 5).

3. **Serve a request (`GET /recommendations?user_id=...`, p99 150 ms).**
   1. Look up the user's features in the online store, with a 30 ms timeout.
   2. If the lookup times out, the user has no record, or `updated_at` is more than 6 hours old: return the popular list with `fallback: true` and skip the model.
   3. Otherwise, run the in-memory `active` model on the features and take the top 20 items. If inference throws an error, return the popular list with `fallback: true`.
   4. Respond with the items, `model_version` and `request_id`.
   5. After the response has been sent, write a prediction log row (`request_id, user_id, model_version, role=active, items, latency_ms, error, fallback`). Rows are written asynchronously in batches. If a write fails, the row is dropped and counted. The user is not affected.
   6. Also after the response: if the `shadow` alias is set and `hash(user_id) mod 100 < 10`, publish the job `{request_id, user_id, feature vector}` to the shadow queue. This is fire-and-forget. If the queue is full or unreachable, drop the job and increment `shadow_dropped`.

4. **Pick up version changes (each API instance and each shadow worker, every 30 s).**
   - *Trigger:* a poll timer. API instances read the `active` alias, and shadow workers read the `shadow` alias.
   - When the alias points to a new version: download the artifact, check that every required feature exists in the online store's schema, load the model, then swap it in atomically. The API keeps the old active model in memory for 24 h as `previous`.
   - *On failure* (missing feature, failed download or failed load): keep serving the current version and raise an alert. A version with missing features therefore never runs.

5. **Run shadow inference.**
   - *Trigger:* a job arrives on the shadow queue.
   - A shadow worker runs the `shadow` model on the **same feature vector** the active model used. It does not do a second lookup, so both models see identical inputs.
   - *Moves:* a prediction log row with `role=shadow`, the shadow version, items, latency and the error, if any.
   - *On failure:* the error is recorded in the row and the job is not retried. The output never goes back to the API or the user.

6. **Compare (daily).**
   - *Trigger:* daily schedule.
   - Join `active` and `shadow` rows on `request_id`. For the candidate version, compute days in shadow, error rate, p99 inference latency, top-20 overlap with the active model (for information only) and the shadow drop rate.
   - *Output:* a report for each candidate version, with a pass or fail result against the gate in step 7.

7. **Promotion gate.**
   - The candidate passes when it has had at least 7 days in shadow, an error rate under 0.5% and p99 inference latency under 80 ms.
   - The ML lead then approves it in the registry. Without that approval, nothing switches.
   - **OPEN QUESTION (Product):** Should a live A/B test, with the candidate shown to a slice of real users, come between this step and step 8? This has not been decided. If the answer is yes, an A/B step is inserted here. If it is no, go straight to step 8. Neither option is built until Product decides.

8. **Switch the active version.**
   - *Trigger:* approval, plus the outcome of the open question in step 7.
   - In the registry, set `previous` to the current active version, set `active` to the candidate, and clear `shadow`.
   - API instances pick up the change within 30 s (step 4). Watch the error rate and fallback rate for 24 h.

9. **Roll back.**
   - *Trigger:* on-call decision or an alert, such as a spike in errors or fallbacks.
   - Set `active` back to `previous` in the registry. Each instance sees the change at its next 30 s poll. The previous model is still in memory (for 24 h), so the swap is immediate and the rollback completes within 1 minute.
   - After 24 h, a rollback has to download the artifact again, which is slower. Plan to roll back within that window.

## Open questions
- Product: is there a live A/B test step between shadow and the full switch? (See step 7.)
