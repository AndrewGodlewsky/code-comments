# Recs API plan

1. **Shadow / challenger stuff.** The challenger (the candidate, which is whatever the `shadow` alias points at) runs on shadow workers, which are a separate service from the API. They get jobs off the shadow queue (bounded, 10k) that the API publishes fire-and-forget after it has already responded, but only when hash(user_id) mod 100 < 10, so it is about 10% of users and always the same users. If the queue is full or down, the API just drops the job and bumps `shadow_dropped`. The job carries request_id, user_id and the feature vector the champion already used, so no second lookup happens and both models get identical inputs. The worker writes a row (role=shadow) to the prediction log in the warehouse. Errors go in the row and there are no retries. The challenger's output never goes back to the API or the user. Also, every 30 s the workers poll the `shadow` alias, and before loading they check that the required features exist in the KV store schema, otherwise they keep whatever they have and alert.

2. Rollback: flip `active` back to `previous` in the registry; within 1 min.

3. **Request handling**: GET /recommendations?user_id=..., p99 150 ms overall, returns 20 IDs. Feature cache lookup, 30 ms timeout → if it times out, or there's no record, or updated_at is over 6 h old → popular list with fallback: true (no model). Then the prod model, held in memory, gives the top 20; if it throws, popular list again with fallback: true. Respond with items + model_version + request_id. After responding, a log row (role=active, items, latency_ms, error, fallback) goes into the prediction log asynchronously in batches; if the write fails, drop it and count it. Also see 1 for the shadow publish.

4. The promotion gate is ≥7 days in shadow, errors <0.5%, p99 inference <80 ms, plus the ML lead approving in the registry. Product hasn't decided whether there's an A/B test on a slice of real users before we go to 100%, so that's open. If yes it slots in before the switch; if no we go straight to the switch. Don't build either yet.

5. **Hourly job**: the scheduler on the hour copies features from the warehouse into the online feature store, overwriting each user's record and setting updated_at. Retried next hour, alert after 2 failed runs in a row, last good values stay put (the 6 h staleness rule is enforced in request handling, not here).

6. Registry: training pipeline finishes → artifact + required feature names stored under the next version number, immutable. Aliases are active / previous / shadow. An ML engineer sets shadow to trial a version.

7. Version pickup on API instances: they poll the active alias every 30 s, and if it changed they download, check the required features against the online store schema, load, and swap atomically. The old live model stays in memory as previous for 24 h, which is why the rollback in 2 is near-instant: no download, just the next 30 s poll. After 24 h a rollback needs a re-download, so it's slower. If the check or the load fails, keep the current model and alert, so a model missing features never runs. The popular list (object storage, daily) is also held in memory on each instance.

8. Daily comparison job: joins active and shadow rows on request_id, computes the challenger's days in shadow, error rate, p99, top-20 overlap (info only) and drop rate, and writes a report for each candidate with pass/fail against the gate in 4.

9. Switch: after approval (and whatever gets decided about A/B), set previous = current live version, active = candidate, clear shadow; instances pick it up within 30 s per 7; watch error and fallback rates for 24 h. Rollback is triggered by on-call or an alert (spike in errors or fallbacks).
