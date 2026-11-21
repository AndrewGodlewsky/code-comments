# Pair 09

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

# Recommendations API: serving, model versions and shadow testing

## What this is

The recommendations API answers `GET /recommendations?user_id=...` with 20 item IDs. For each request, the active model version runs on the user's latest features from an online feature store, so the list is computed per request. If the features are missing, stale or incompatible, or the model fails or runs out of time, the API returns a popular-items list and marks the response as a fallback. New versions run in shadow on 10% of users first: their output is logged, never shown, and never allowed to slow a response. A version becomes active only after 7 days in shadow, passing gates and ML lead approval, and switching is a config change, not a redeploy.

Today the lists are precomputed each night into a table. Per-request computation lets each response use features as fresh as the hourly copy allows.

## Terms

- **Online feature store**: a key-value store keyed by user ID. Each user has one row holding all their features plus `schema_version`, `source_as_of` and `materialized_at`.
- **Feature row**: that one user row.
- **`source_as_of`**: when the warehouse snapshot behind the features was taken.
- **`materialized_at`**: when the row was written to the online store.
- **`schema_version`**: the version number of the feature layout. A row and a model must agree on it.
- **Warehouse**: the analytics database where features are built.
- **Materialization**: the hourly copy of features from the warehouse into the online store.
- **Model version**: one trained model with a number. Once registered, it never changes. A changed model gets a new number.
- **Artifact**: the model file of one version, stored in the object store (file storage).
- **Manifest**: a version's required features and their types, its `schema_version`, and its output rule (exactly 20 unique catalog item IDs).
- **Registry**: the record of every model version, its status, eligibility and approvals.
- **Eligible**: every feature in the version's manifest exists in the online store's current schema.
- **Active version**: the one version that serves users. There is exactly one at a time, except before the first activation, when there is none.
- **Candidate**: a version running in shadow.
- **Serving config**: a small, strongly consistent record holding the active version, the shadow settings and a revision number.
- **Revision**: a counter that goes up with every serving config write.
- **CAS (compare-and-set)**: a write that names the revision it expects. If the revision has changed, the write is rejected, so two writers cannot silently overwrite each other.
- **Active pool**: model servers that hold model versions in memory and answer live requests. They sit behind an internal load balancer, and the API calls them over the network.
- **Shadow pool**: a separate set of model servers that runs candidates, with its own concurrency limit.
- **Control tool**: the command-line tool operators use to change the serving config. It reads the gate report and approval records, records approvals and writes CAS revisions. It does not run the gates.
- **Operator**: an on-call ML platform engineer with write access to the serving config store. Operators act through the control tool.
- **Gate report**: the daily summary of shadow results, checked against the promotion gates.
- **Approval record**: the ML lead's sign-off on one version, tied to one gate report.
- **Popular list**: 20 catalog item IDs, recomputed daily. It is the fallback.
- **Checksum (SHA-256)**: a fingerprint of an artifact file. A download with a different fingerprint is rejected.
- **Object lock**: a storage setting that stops an object from being changed or deleted.
- **Warm-up inference**: one test prediction, run on a fixed sample row after a model loads and before it takes traffic.
- **Shadow cohort**: the 10% of users who get shadow runs. Membership is fixed by a salt, a random string set per shadow window.
- **p99**: the response time that 99% of calls beat.

## Latency budget (p99, whole call: 150 ms)

| Stage | Budget | Enforcement |
|---|---|---|
| Gateway and API overhead | about 10 ms | Load balancer and API timeouts |
| Feature lookup | 30 ms | Hard deadline; timeout means fallback |
| Active model inference | the rest of a 140 ms internal deadline (gate: p99 under 80 ms) | Deadline; timeout means fallback |
| Validate, rank, serialize | about 10 ms | Code path, no I/O |
| Margin | about 20 ms | Unallocated headroom |

The 140 ms internal deadline starts when the API receives the request. It leaves room for the gateway and serialization inside the 150 ms budget.

## Components and where state lives

| Component | Role | State |
|---|---|---|
| Recommendations API (stateless, many instances) | Runs each request | In memory only: serving config copy and popular list |
| Online feature store | Serves one row per user | Durable and replicated |
| Materialization job (hourly) | Copies warehouse features into the store | None of its own. Progress shows in the rows' timestamps |
| Model registry | Versions, manifests, eligibility, approvals | Metadata in a relational table. Artifacts in an object store with object lock |
| Serving config store | Active pointer, shadow settings, revision history, pool status rows | Small, strongly consistent record. Writes are CAS |
| Active and shadow pools | Hold loaded model versions and run them | In memory. The two pools are separate deployments |
| Shadow queue and worker | Runs candidates off the request path | Bounded in-memory queue per instance. Output goes to a log |
| Popular-items job (daily) | Produces the fallback list | Versioned object. The previous day is kept |
| Warehouse | Shadow and decision logs for comparison and gates | Append-only tables |

## How a request is served

Every request goes through steps 1 to 7. The first failure that applies sets the fallback reason, and the response is the popular list.

**1. Accept and validate the request**
- **Starts when:** `GET /recommendations?user_id=...` arrives.
- **Does:** Checks `user_id`, generates a `request_id` for tracing and starts the 140 ms internal deadline.
- **Data:** `user_id`, `request_id`.
- **State:** None.
- **On failure:** A missing or malformed `user_id` returns 400.

**2. Read the serving config from memory**
- **Starts when:** Every request, after step 1.
- **Does:** Reads the active version ID and its manifest, the shadow candidate with its manifest, salt and percentage, and the revision.
- **State:** Each API instance polls the serving config every 10 s and keeps the last good copy in memory. API instances only read config. They never load models. Pool servers poll too, to load models (step 14).
- **On failure:** If a poll fails, the instance keeps its last good copy and raises an alert once that copy is older than 2 minutes. If no config has ever loaded, every request takes the popular list with reason `no_config`.

**3. Look up features, with a 30 ms deadline**
- **Starts when:** Step 2 has a config.
- **Does:** Reads one key, the `user_id`. The whole row comes back, so the active model and any candidate read the same snapshot.
- **State:** Online feature store.
- **On failure:** A timeout gives `lookup_timeout`. A store error gives `lookup_error`. The model is not called.

**4. Check the row for freshness and compatibility**
- **Starts when:** Step 3 returns.
- **Does:** Reads `source_as_of` and `schema_version` from the row and compares them with the active manifest. Read only. Checks run in this order:
  - No row: `no_features`.
  - `now - source_as_of` greater than 6 hours: `stale_features`. The 6 hours count from `source_as_of`, not `materialized_at`, because that is the stricter reading (assumed).
  - The row's `schema_version` differs from the manifest's: `feature_mismatch`.
  - The row lacks a feature the manifest requires, by name or type: `feature_mismatch`. This is a safety net. The eligibility check (step 12) should prevent it.
- **On failure:** In every case the model is not called.

**5. Run the active model, with the remaining deadline**
- **Starts when:** Step 4 passes.
- **Does:** Sends the active version ID and only the feature values the active manifest lists. It does not send `schema_version`, `source_as_of`, `materialized_at` or `user_id`. The manifest is the model's input contract, so extra inputs would change the model without a version change. The API keeps the metadata for the step 4 checks and the shadow logs.
- **Reply:** The pool server returns the version it served and the ranked item IDs together. The API checks that the returned version matches the one it asked for. A mismatch is `model_error`, so `model_version` always names the version that answered.
- **Output check:** The output must be exactly 20 unique catalog item IDs. Anything else is invalid, and counts as a model error (assumed).
- **Deadline:** The model gets the 140 ms deadline minus the time already used. The brief sets no separate model timeout (assumed). If no time is left, the result is `model_timeout` and the model is not called. The API enforces the deadline. It closes its call when time runs out and ignores any later reply, so a valid 200 that arrives late is still `model_timeout`. The pool server stops work when the caller disconnects and discards the result.
- **Attempts:** One. The API does not retry on another server. The deadline leaves no room for a second call, the brief sets no retry rule, and the fallback is the stated rule for `model_error`.
- **Pool rule:** A pool server answers only with a version it holds in memory. If the named version is not held (for example during a switch), it returns an error.
- **On failure:** A timeout gives `model_timeout`. A refused or reset connection, a 5xx response, invalid output, a reply naming another version, or a version not held gives `model_error`. Both fall back.

**6. Queue a shadow sample, after the response**
- **Starts when:** Step 5 succeeds. Shadow never runs after a fallback, because there is nothing to compare against.
- **Rule:** The sample is queued only if the user is in the shadow cohort (step 17) and the feature row satisfies the candidate's manifest. The API checks the manifest in memory, using the candidate manifest from its config. It does not ask the shadow pool. A candidate is eligible only when the store already has its features (step 12), so a candidate never runs on features the store does not have.
- **Data:** `request_id`, `user_id`, the feature row, the active item IDs and the config revision.
- **Timing:** Queued after the response bytes are written, so it adds no latency.
- **State:** A bounded in-memory queue on each instance.
- **On failure:** If the queue is full, the sample is dropped, a counter goes up, and nothing waits.

**7. Return the response**
- **Starts when:** Step 5 succeeds, or any fallback fires in steps 2 to 5.
- **Normal response:** `{ "items": [20 IDs], "fallback": false, "model_version": "v<active>" }`. `model_version` is the version the active pool reports it served, so during a switch it shows which version answered.
- **Fallback response:** `{ "items": [20 popular IDs], "fallback": true, "fallback_reason": "<reason>" }`.
- **State:** The popular list comes from an in-memory cache, so it does not depend on the feature store or the model.
- **On failure:** If the popular cache is empty (possible only right after a cold start), return 503.

## Feature freshness

**8. Hourly materialization**
- **Starts when:** The hourly schedule fires.
- **Data:** The warehouse feature snapshot is copied to the online store. Each user gets one row: features, `schema_version`, `source_as_of`, `materialized_at`.
- **State:** Online feature store. The job keeps no state of its own.
- **On failure:**
  - Writes are per key and idempotent, so a re-run is safe.
  - A partial run leaves mixed freshness. This is acceptable, because each row carries its own timestamp and is checked on read.
  - The job retries with backoff. An alert fires when no successful run has finished for 90 minutes.
  - Serving is not affected.

**9. Freshness is enforced on read, not by TTL**
- Step 4 checks every row on every read.
- The store deletes rows after 24 hours to save storage. That deletion is not the freshness rule.
- If materialization stops, rows already in the store keep serving, up to 6 hours old. After that they count as missing, and users move to the fallback one by one.
- The dashboard shows the fallback rate by reason. An alert fires when `stale_features` passes an agreed threshold.

**10. Daily popular list**
- **Starts when:** The daily schedule fires.
- **Data:** Interaction data produces 20 catalog item IDs, written as a new versioned object in the object store.
- **State:** Each API instance loads the newest object into memory every 5 minutes. The previous day's object is kept.
- **On failure:** The job keeps the previous day's list. An alert fires when the list is more than 36 hours old. The API keeps serving the last good list.

## Model versions and switching

**11. Register a trained version**
- **Starts when:** A training run completes.
- **Data:** The artifact, its SHA-256 checksum, and a manifest: required features and types, `schema_version`, the output contract (20 catalog IDs), the training data reference and metrics. The registration also stores a fixed sample feature row, used for warm-up.
- **State:** The artifact is written once to the object store with object lock. The registry row has status `registered`. A version number is never reused.
- **On failure:** A failed registration leaves no version, or an `incomplete` row that cannot be activated or shadowed. Nothing is overwritten.

**12. Check eligibility against the online store**
- **Starts when:** A version is registered, and whenever the store's feature schema changes. The store publishes each schema change, and the registry re-checks every version that is not yet retired.
- **Data:** The manifest compared with the store's current schema.
- **State:** The `eligible` flag and its reason are kept in the registry. The registry also keeps an append-only eligibility history: one row each time a version's flag or reason changes, with the time. The history lets the gates check the whole window later.
- **On failure:**
  - An ineligible version cannot be shadowed or activated.
  - A candidate that needs a feature not yet in the store stays ineligible until materialization writes that feature.
  - If the active version becomes ineligible, it keeps its pointer and an alert fires. Step 4 refuses rows that lack its features, so those users get the fallback. An operator must switch or roll back. Nothing switches automatically, because an automatic switch to an unknown model is riskier than a fallback.

**13. Write the serving config with CAS**
- **Starts when:** An operator writes a change through the control tool.
- **Data:** `{active_version, shadow: {version, salt, percentage, started_at}, revision}`. `percentage` is a whole percent: 10 means 10%.
- **State:** Serving config store. Each write names the revision it expects. If the revision has changed, the write is rejected, and the writer re-reads and retries.
- **Checks before each write (the control tool does them):**
  - The active version must be registered, eligible and approved. Approved means it has an approval record from step 21.
  - The shadow candidate must be registered and eligible.
  - A rollback target passes without a new approval, because it was approved when first promoted. The very first active version still needs approval.
- **On failure:** A rejected write changes nothing. No partial state is written.

**14. Load and switch, without redeploying the API**
- **Starts when:** A pool server sees a new revision on its 10 s poll. Only pool servers download and load models. API instances only read the active version ID.
- **Data:** The artifact is downloaded by version ID and its checksum is verified. A warm-up inference then runs on the fixed sample row stored with the version (step 11). Only after that does the server swap. The active pool loads from the object store. It never reuses the shadow pool's copy, and it never holds a candidate before activation.
- **State:** Each active pool server keeps the current and the previous version in memory. The swap is an atomic reference change. When a swap makes a new version current, the old previous version is unloaded from memory. It stays in the registry.
- **Status table:** Each pool server writes one row to a status table in the serving config store: server, version, status (`ready` or `failed`), revision and time. The control tool reads these rows. Rows from servers no longer in the active pool are ignored.
- **Completion:** The switch is complete when the control tool sees every active pool server report `ready` on the new revision. The timeout is 2 minutes. After that the switch is reported as incomplete and an alert fires.
- **New or restarted servers:** A server that starts later, from a restart or autoscaling, loads the version the config names through the same path and reports `ready` before it takes traffic. Otherwise it would answer with errors after every switch.
- **During the poll window:** Pool servers may run different versions for up to about 10 seconds. This is accepted, because both versions are valid and `model_version` shows which one answered. A server that is still loading keeps its old version. A request that names the new version gets `model_error` and falls back.
- **On failure:** If a download, checksum or warm-up fails, the server keeps its previous version, marks the target `failed` and raises an alert.
- **Incomplete switch:** Nothing rolls back automatically, because the brief says nothing switches automatically and a rollback would be a second switch it does not ask for. The config still names the new version. Servers that never loaded it answer with errors, and their requests fall back until an operator rolls back or fixes the failed servers. The servers stay mixed until then.

**15. Roll back in under 1 minute**
- **Starts when:** An operator writes a CAS revision that points `active` at the rollback target.
- **Rollback target:** The version that was active in the revision just before the current one. The config history records each revision's active version, so the target ID comes from there.
- **Data:** No artifact is downloaded when the target is still in memory. Each active pool server keeps the current and previous version, so rolling back to the previous version needs no download. If the target is no longer resident, the load path in step 14 runs.
- **Budget (assumed for a small model):** a 10 s poll, under 5 s swap and under 30 s confirmation. The total is well under 1 minute.
- **Approval:** None needed. The target was approved when it was first promoted.

## Shadow testing

**16. Start shadow**
- **Starts when:** An operator writes a CAS revision through the control tool that sets `shadow` to an eligible candidate, with a fresh salt and `percentage = 10`.
- **Data:** The shadow settings. `started_at` is the time of the write, and it starts the 7-day clock. Changing the candidate, the salt or the percentage sets a new `started_at` and restarts the clock.
- **Shadow pool:** Shadow pool servers poll the config too. When the shadow version is new to them, they load it through the step 14 path: download, checksum, warm-up, swap. When shadow is cleared, they unload it. A failed load counts as candidate failures (step 18).
- **State:** Serving config store, and registry status `shadow`.
- **On failure:** Shadow never affects the request path.

**17. Assign the shadow cohort**
- **Starts when:** Every request, at the check in step 6.
- **Rule:** `bucket = hash(salt, user_id) mod 10000`. The user is in the cohort when `bucket < percentage × 100`. At 10%, that is `bucket < 1000`.
- **Why it is stable:** The cohort is a pure function of the salt and the user ID. The salt is fixed for the whole window, so a user is always in or always out.
- **Coverage:** Users with no usable features never get a shadow run, so the effective sample is below 10%. The comparison reports this coverage.

**18. Run the candidate off the hot path**
- **Starts when:** The shadow worker dequeues a sample. The shadow worker is a background task in each API instance that drains that instance's queue.
- **Data:** The feature values the candidate's manifest lists go to the shadow pool, with a 500 ms deadline. The worker logs the candidate's output next to the active output, and step 19 compares them.
- **State:** The shadow pool has its own concurrency limit. When the active pool is busy, shadow load is shed first.
- **On failure:**
  - Timeouts, errors and invalid outputs are counted as candidate failures.
  - A crash in the shadow pool does not touch the active pool.
  - Samples dropped from a full queue are counted separately and are not counted as attempts.
  - Nothing in shadow reaches the user or slows the response.

**19. Log and compare**
- **Starts when:** Every shadow attempt writes a record. A daily comparison job also runs.
- **Data per attempt:** `request_id`, `user_id`, candidate version, salt, active items, candidate items, candidate inference time, status (`ok`, `timeout`, `error` or `invalid`), `source_as_of` and the config revision. Both models saw the same feature values, so the comparison is fair.
- **Drop counters:** Each instance writes a summary every minute: samples eligible, queued and dropped. The daily job sums them across instances.
- **Window selection:** The daily job keeps only records whose candidate version and salt match the current shadow settings and whose time is on or after `started_at`. Other records are excluded. The config revision is kept for audit.
- **State:** Log stream, then an append-only warehouse table of shadow and decision logs.
- **Reported figures:**
  - Overlap at 20 (active versus candidate). Reported, not gated, because the brief sets no threshold.
  - Candidate error rate.
  - Candidate p99 inference time.
  - Drop rate: dropped divided by eligible samples (queued plus dropped), summed across instances. A drop rate above 1% marks the window invalid (assumed limit).
  - Eligible coverage.
- **On failure:** Log loss is tolerated but measured, through the drop rate and the counters.

## Promotion and rollback

**20. Evaluate the gates**
- **Starts when:** The daily comparison job sees that the candidate's `started_at` is at least 7 full days old. The job runs the gates and stores the report, with its hash, in the registry. The control tool does not decide timing.
- **Gates (all must pass):**
  - At least 7 continuous days under one salt and one candidate.
  - The candidate was eligible for the whole window, checked against the eligibility history (step 12).
  - Error rate under 0.5% of attempts. Errors are timeouts, errors and invalid outputs.
  - Candidate p99 inference time under 80 ms.
  - Drop rate at or under 1%.
- **On failure:** The kind of failure decides the outcome. Nothing is promoted automatically.
  - If the candidate's own numbers fail (error rate or p99), it moves to `rejected`. That status is final for this version number, because more shadow time will not make it faster or more reliable.
  - If the window fails (an eligibility gap, or drop rate above 1%), it stays in shadow. To try again, the operator restarts shadow with a fresh salt, which resets the clock.
  - If every gate passes but nobody approves, it stays in shadow. The daily job keeps running and storing reports. Nothing times out or promotes.

**21. ML lead approval**
- **Starts when:** The gate report passes. The operator then asks the ML lead for approval through the control tool.
- **Data:** An approval record: version ID, the gate report hash it reviewed, the approver and a timestamp. Approvals are tied to the immutable version.
- **State:** Registry.
- **On failure:** Without an approval record, activation is refused.

**22. Activate**
- **Starts when:** An approved version is ready.
- **Checks before the write (the control tool does them):** The checks in step 13, plus two more: the stored gate report passed, and an approval record exists for this version and names a passing report. The control tool does not run the gates itself.
- **Data:** The control tool writes one CAS revision with `active = candidate` and `shadow` cleared. The previous active version is kept as the rollback target. This one write does two things. Shadow pool servers unload the candidate (step 16). Active pool servers load it from the object store (step 14).
- **Samples already queued for the candidate:** The shadow worker discards them when it dequeues them. It makes no call to the shadow pool and counts them neither as attempts nor as drops. The gate report was already stored and reviewed, so later attempts would add nothing and would only produce errors.
- **State:** Config store. The new version's registry status becomes `active`. The previous version becomes `retired`, but it stays in memory on each active pool server (step 14) and stays in the registry.
- **First activation:** There is no previous version. Until then the serving config has no active version, and every request takes the popular list with reason `no_config`. The first version still needs approval.
- **On failure:** Handled as in the switch step (step 14).

**23. Watch after switching**
- **Starts when:** Each switch.
- **Data:** Active error rate, fallback rate by reason, and p99 latency per version.
- **State:** Dashboards and alerts.
- **On failure:** A regression leads to rollback (step 15). Whether rollback is automatic or manual is to be decided before launch.

**24. Retention**
- **Starts when:** A version is retired.
- **Data:** None.
- **State:** Artifacts and manifests are kept for the retention period, which is not yet set.
- **Rule:** A version is never deleted while it is the rollback target.

## When things fail

| Reason or response | Cause | What the user gets |
|---|---|---|
| (none) | Features fresh and compatible; model returns 20 valid IDs for the version it names | Normal response |
| `no_config` | Serving config never loaded, or no version activated yet | Popular list, fallback |
| `lookup_timeout` | Feature store misses the 30 ms deadline | Popular list, fallback |
| `lookup_error` | Feature store returns an error | Popular list, fallback |
| `no_features` | No row for this user | Popular list, fallback |
| `stale_features` | Row older than 6 hours (from `source_as_of`) | Popular list, fallback |
| `feature_mismatch` | Row's `schema_version` differs, or the row lacks a feature the active model requires | Popular list, fallback |
| `model_timeout` | Model misses the remaining deadline, including a late reply | Popular list, fallback |
| `model_error` | Transport error, 5xx, invalid output, a reply naming another version, or the named version not held by the pool server | Popular list, fallback |
| 400 | Missing or malformed `user_id` | Error, no list |
| 503 | Popular cache empty (cold start only) | Error, no list |

Shadow failures never reach the user. Their handling is in steps 18 and 19.

## Before build: decisions

Each has a default the plan uses. Confirm yes or no before build.

1. **Freshness reference.** Rows are aged from `source_as_of`, not `materialized_at`. This is the stricter reading.
2. **Model deadline.** The internal request deadline is 140 ms from request receipt. There is no separate model timeout.
3. **Invalid output.** A response that is not exactly 20 unique catalog IDs counts as a model error and triggers the fallback.
4. **Rollback approval.** Rollback needs no approval, because the target was approved when first promoted.
5. **Shadow drop limit.** At most 1% of eligible shadow samples may be dropped. Above that, the shadow window is invalid.
6. **Rollback budget.** The 1-minute rollback target holds for a small model.
7. **Live A/B test (not decided).** Product must decide whether a live slice comes between shadow and the full switch, and how a slice fits with "exactly one active" (see the next section). Do not build any slice until this is decided.

## The open gap: live A/B test or straight to 100%

Product has not chosen between a live slice (showing the candidate to a share of real users) and going straight from shadow to 100%. This plan does not choose. It is built so that both stay possible.

- **Config shape (future):** The serving config would hold a list of serving entries, each with a version, a percentage and a salt. Today it holds one entry at 100%. A slice adds an entry without changing the request path. Shadow stays a separate field.
- **Conflict with "exactly one active":** A slice serves two versions at once. Either the slice arm gets a status other than `active` (for example `experiment`), or the invariant is relaxed. This must be decided before any slice is built.
- **Gate for a slice:** Step 20 covers only activation. A slice needs its own gate with guardrail metrics, a minimum sample size, a duration and a stop rule. Product has not defined these.
- **Salt:** A slice would use its own salt, independent of the shadow salt, so the two cohorts are not correlated.
- **Rollback:** Removing a slice is a CAS revision that drops its entry. It meets the same 1-minute target as step 15.
- **Limit of shadow:** Shadow measures agreement and reliability, not user outcomes. Whether shadow alone is enough evidence is a question for product.

## Open questions

- How the control tool gets the list of active pool servers, so it knows which status rows to wait for.
- Whether a config switch should wait until pool servers have loaded the new version. Today a switch can cause brief fallbacks on servers that have not loaded it yet.
- Whether the internal load balancer retries a failed call on its own, and whether it sends traffic to a new server only after that server reports `ready`. The plan says the API does not retry, but not what the load balancer does.
- Whether an approval must match the latest gate report. The daily report changes each day, so an approval of one report may not match the report at activation.
- Whether the activation check must name the latest report, or any passing report.
- Whether overlap at 20 should become a gate. The brief sets no threshold, so it is only reported.
- The retention period for artifacts and manifests.
- Whether rollback is automatic or manual.
- Whether removing a feature from the store schema should be blocked while an active or candidate version still needs it. The plan currently handles it after the fact.
- The first active version has no rollback target, and the plan has no way to clear the active version. Whether that should be possible is open.

---

# Document B

# Recommendations API: serving, model versions and shadow testing

## What this plan does

Today, recommendations are computed once each night and stored in a table. The home page reads from that table. This plan replaces it with a service that computes recommendations for each request, using features that are at most a few hours old.

The plan also covers three related questions:

- **Shadow:** how a new model version runs on a copy of some real traffic. It computes results, but users never see them.
- **Activation:** how a version becomes the **active** one, the version that answers users.
- **Rollback:** how we return to the previous active version if something goes wrong.

Terms are defined in "Terms used in this plan," before the steps that use them. Anything marked **Proposed** is a design choice made in this plan. It is not a requirement from the brief.

## How the pieces fit together

- A user's home page calls the API. The API reads that user's feature row from the online feature store, runs the active model, and returns 20 item IDs. If something needed is missing, it returns the popular list instead.
- Once an hour, a materialization job copies features from the warehouse into the online store.
- A config service holds one routing record. It says which model version is active and which version, if any, is in shadow. Each API pod reads this record every 10 seconds.
- Model versions are stored in two places: a registry holds their metadata, and an artifact store holds the model files.
- For users in the shadow cohort, the API copies the inputs and output of each request into a queue. A separate shadow fleet runs the candidate model on those inputs and writes the results to an analytics store. Users never see that output.

## Scope and assumptions

- **One API service, scaled horizontally.** The service runs as several pods (identical running copies). Each pod holds no durable state. When a pod starts, it rebuilds what it needs from three places: the config service, the artifact store and the online store.
- **In memory per pod:** the routing config, the popular list and the loaded model weights.
- **One shadow candidate at a time.** This is an assumption to confirm.
- **Not decided:** whether a live A/B slice sits between shadow and the full switch. A live slice means showing a candidate's recommendations to some real users. This plan does not choose. See "Where the open decision attaches."

## Terms used in this plan

- **Feature:** one input value describing a user, such as a count or a category. Models use features to make predictions.
- **Feature row:** the single record the online store holds for one user. It contains all of that user's features, an `as_of` time and a `schema_version`.
- **`as_of`:** when the warehouse snapshot behind a feature row was taken. It is not when the row was written to the store.
- **Schema and `schema_version`:** a schema is the agreed layout of a feature row: which feature names exist and what they mean. The `schema_version` is the identifier for one such layout.
- **Store manifest:** the list of schema versions the online store currently serves.
- **Catalog:** the full set of items that can be recommended. Every ID in a response must be in the catalog.
- **Popular list:** 20 popular item IDs, recomputed daily. It is the fallback answer.
- **Fallback:** a response that returns the popular list instead of model output. It is marked `fallback: true` and gives a reason.
- **Active version:** the model version that answers user requests.
- **Shadow candidate:** a second model version that runs on a copy of some requests. Its output is stored for analysis and never shown to users.
- **Shadow cohort:** the users whose requests are copied to the shadow candidate.
- **Gate:** the set of checks a shadow candidate must pass before it can become active.
- **Compare-and-set (CAS):** a write that succeeds only if the stored `revision` number still equals the value the writer read. Each successful write increments `revision`. If two writers race, only one succeeds. The other must read the new revision and try again.
- **Fail static:** when a component cannot reach its source of truth, it keeps using its last good copy. It does not guess.
- **Warm set:** the model versions a pod has already downloaded and checked, so it can use them without downloading again.
- **Digest:** a fingerprint of a file's exact bytes, such as a SHA-256 hash. If the bytes change, the digest changes.
- **Circuit breaker:** a rule that stops calls to a failing dependency for a while, so requests fail fast instead of waiting.
- **Latency budget:** the whole `GET /recommendations` call must finish within 150 ms at the 99th percentile (p99). That means 99% of calls finish within 150 ms.
- **Enqueue:** add an event to the back of a queue for a later worker to process.
- **Orchestrator:** the scheduler that runs jobs on a timetable and records whether each run succeeded.

## Components and where state lives

| Component | State | Notes |
|---|---|---|
| Recommendations API | In memory only: routing config, loaded model versions, popular list | Rebuilt on restart from the config service, artifact store and online store |
| Config service | One `routing` record: `active_version`, `previous_active`, `shadow_version`, `shadow_salt`, `shadow_percent`, `mode`, `revision`, and an ordered list of exposure rules | Today the rule list has one rule: all users go to the active version. Every write is a CAS on `revision` |
| Model registry | Immutable version records (artifact digest, required features, feature schema, training run, code commit). Status and approvals are separate append-only events | A version record is never edited |
| Artifact store | Model weight files, keyed by digest | Read-only for the API |
| Online feature store | One feature row per user. Also holds the schema manifest and the popular list | Key-value store (a store that looks up a value by its key). Read by the API and the shadow fleet |
| Materialization job | Run status in the orchestrator | Runs hourly. Copies features from the warehouse into the online store |
| Shadow queue | Bounded queue of events. Each event holds: user ID, request ID, the feature row as read, active items, active fallback flag, active version, timestamp | Dropping events is allowed |
| Shadow fleet | Stateless workers in their own deployment | Writes results to the analytics store only |
| Analytics store | Shadow rows and daily gate reports | Retention proposed: 90 days for raw rows, longer for gate reports |

## Part A: Request path

### Step 1. Receive and validate the request

- **Starts when:** `GET /recommendations?user_id=...` reaches the gateway (the front door that routes web requests to services).
- **Data moves:** `user_id` from the query string.
- **State:** none.
- **On failure:** a missing or malformed `user_id` returns 400. The 150 ms budget starts here.

### Step 2. Read the routing config

- **Starts when:** every request. It reads the copy held in memory.
- **Data moves:** none on the request path. Each pod polls the config service every 10 s. Polls are spread out with random jitter so pods do not all poll at the same moment (proposed).
- **On failure:** if the config service is unreachable, the pod keeps its last good config (fail static). A new pod with no config yet returns fallback with reason `no_routing_config` and reports itself as not ready.

### Step 3. Look up features

- **Starts when:** after step 2. Skipped if `mode` is `fallback_only`.
- **Data moves:** one key-value read per user. It returns the whole feature row: all features, `as_of` and `schema_version`. It does not return only the columns the active model uses. A shadow candidate may need other columns. Shadow must use the same row as the response, so both see identical inputs.
- **Budget:** 30 ms hard timeout.
- **What counts as missing or invalid:**
  - No row for the key: **missing**.
  - `as_of` more than 6 h before the API's clock: **missing (stale)**.
  - `as_of` more than 5 min after the API's clock: **invalid**, so treated as missing. The 5 min allowance for clock skew is proposed.
  - `schema_version` not in the store manifest: the row cannot be used by any model that needs that schema.
- **Circuit breaker (proposed):** after 5 timeouts within 10 s, the API stops calling the store for 10 s and goes straight to fallback. This keeps responses inside 150 ms while the store is down.
- **On failure:** a timeout, a missing row or a stale row sends the request to fallback (step 4). The model is not called.

### Step 4. Decide between the model and fallback

- **Compatibility check for the active model:** every required feature must be in the row, and the row's schema must be in the store manifest. If either check fails, return fallback with reason `feature_contract_mismatch` and raise an alert. This should not happen in normal operation.
- **Fallback:** return the popular list, with `fallback: true` and a reason. The popular list is recomputed daily, held in memory and refreshed hourly.
  - If it cannot be read, serve the last cached copy.
  - If none was ever loaded, serve a static list bundled with the API build (proposed).

### Step 5. Run the active model

- **Starts when:** step 4 passes.
- **Data moves:** the feature row goes into the active model. The model returns ranked item IDs.
- **Deadline (proposed):** the smaller of two values:
  - 90 ms, or
  - the time left in the 150 ms budget, minus a 20 ms reserve for writing the response.
- **Output check:** the output must be exactly 20 distinct IDs, all in the catalog. If it is short or has duplicates, fill the missing slots from the popular list and set `fallback: true` with reason `partial_model_output`.
- **On failure:** an exception, a timeout, or output that is still invalid after filling gives popular fallback with reason `model_error` or `model_timeout`. Each case is counted and alerted on.

### Step 6. Return the response and enqueue the shadow event

- **Response:** `{ "items": [20 IDs], "fallback": bool, "reason": string or null, "model_version": "<active>" }`. The `model_version` field is for debugging. The home page does not need it.
- **Shadow enqueue:** happens after the response body is written. It happens only if the user is in the shadow cohort (step 14) and a shadow version is set. The event carries the feature row, the active items and the fallback flag. Shadow therefore uses exactly the inputs this response used.
- **On failure:** if the queue is full, or the enqueue does not finish within 1 ms, drop the event and increment a counter. Never block or retry on the request path.

## Part B: Feature freshness

### Step 7. Run materialization hourly

- **Starts when:** the hourly schedule in the orchestrator.
- **Data moves:** warehouse snapshot, then transformation, then one write per user to the online store. Each row carries its `as_of` (the snapshot time) and its `schema_version`.
- **State:** run status lives in the orchestrator. The online store holds only the rows.
- **On failure:** retry with backoff (waiting longer before each retry), up to 3 attempts (proposed). Alert if no run has succeeded for 90 minutes (proposed).

### Step 8. Validate, then publish

- **Validation before any write (proposed):**
  - the row count is within a band around the previous run's count;
  - the null rate (share of missing values) for each feature is below a threshold;
  - the schema matches the declared version.
- **Write atomicity:** each user's row is written with one key write. So each user sees either the old row or the new row, never a mix. If a run stops partway, some users keep older rows than others. Step 9 handles this. No consistency across users is needed.
- **Schema changes:** during a migration, the new `schema_version` is written next to the old one. The manifest lists the active schema versions. A schema is removed only when no registered model that could still be active or previous needs it.
- **On failure:** a failed validation stops the run before any write, so the previous rows stay in place. Raise an alert.

### Step 9. Serve through a failed materialization

- A failed run leaves the previous rows in place. Each row keeps being served until its `as_of` is 6 h old. After that, it counts as missing (step 3), and responses fall back to the popular list.
- **Alerts (proposed):** warn 2 h after the last successful run, and page at 4 h. The fallback rate on the dashboard should rise before rows expire at 6 h.

## Part C: Model versions and switching

### Step 10. Register a model version

- **Starts when:** a training run is approved for registration.
- **Data moves:** the model file is uploaded to the artifact store. Then one registry record is created. The record holds the digest, `required_features`, `feature_schema`, the training data snapshot ID, the code commit and the owner.
- **State:** the registry. Records are immutable. Registering the same digest returns the existing record. A changed artifact gets a new version number.
- **Status:** a new record starts as `registered`. Later status changes are added as separate events. They are never written into the record itself.
- **On failure:** if the upload fails, no record is created. The record is written only after the digest has been checked in the artifact store.

### Step 11. Check compatibility before any model runs

- **Rule:** a model may run for a user only if:
  - its `feature_schema` is in the store manifest, and
  - every name in `required_features` is present in that user's feature row.
- **Where the rule is checked:**
  - at registration, against the current store;
  - at promotion, against every day of the shadow window;
  - at pod load (step 12);
  - per request for the active model (step 4);
  - per event for the candidate (step 15).

### Step 12. Load versions onto pods without a redeploy

- **Starts when:** a pod reads a routing config that names a version it does not hold.
- **Data moves:** the model file goes from the artifact store to pod memory. The downloaded file is checked against its digest before the model is used.
- **Warm set:** a pod holds up to three versions:
  - the active version,
  - `previous_active`,
  - the shadow candidate.

  `previous_active` stays loaded, so a rollback needs no download.
- **On failure:** a download or digest error marks that version as unloadable on that pod. The pod keeps serving what it already has. It reports its loaded set to the config service.
- **Assumption:** three model versions fit in pod memory. This must be checked against real model sizes.

### Step 13. Switch the active version

- **Starts when:** an operator or automation calls the switch with a target version and an approval reference (step 19).
- **Data moves:** one config write sets `active_version` to the target, sets `previous_active` to the old active version, and increments `revision`.
  - The write is a CAS: it succeeds only if the `revision` it expects is still current. So two switches running at the same time cannot both succeed.
- **Pre-warm rule (proposed):** the write is refused unless the target version is reported as loaded and verified on at least 99% of healthy pods. This keeps the active pointer single and stops pods from serving a version they have not loaded.
- **Propagation:** pods pick up the new revision within one poll interval (about 10 s). For a few seconds, some pods may still serve the old version. Each response carries `model_version`, so this mix can be seen in the data. The pointer itself is still single.
- **On failure:** if the config service is down, the switch is refused and nothing changes. Pods keep serving their last good config.

## Part D: Shadow testing

### Step 14. Assign the shadow cohort

- **Starts when:** `shadow_version` is set in the routing config.
- **Rule:**
  1. Take the bytes of `shadow_salt` followed directly by `user_id`, both encoded as UTF-8, with nothing between them.
  2. Compute the SHA-256 hash of those bytes.
  3. Read the first 4 bytes of the hash as an unsigned integer, big-endian (most significant byte first).
  4. Take that integer mod 10000 (the remainder after dividing by 10,000).
  5. The user is in the cohort if the result is below `shadow_percent` × 100. For 10%, that means below 1000.
- **Why this exact recipe:** SHA-256 gives the same result on every pod and in every language. Built-in string hash functions do not. Fixing the byte order and encoding means every implementation agrees.
- **Stability:** a user's membership stays fixed while the salt stays fixed. Changing the salt reshuffles the cohort and restarts the shadow window.
- **On failure:** none expected, because the function is pure (same input, same output, no side effects). Test it with fixed input vectors.

### Step 15. Run shadow off the request path

- **Starts when:** step 6 enqueues an event for a cohort user.
- **Isolation:** the shadow fleet is a separate deployment with its own CPU and memory. Shadow load cannot slow down request inference.
- **Compatibility check first:** before running, the worker applies the step 11 check to the candidate against the event's feature row. If a check fails, it records `skipped_incompatible` with the missing feature names. It does not run the model.
- **Run:** the candidate runs with an 80 ms timeout, the same bound as the gate. Its output is checked the same way as in step 5.
- **Output boundary:** candidate output is written only to the analytics store. The response builder has no reference to it. A contract test checks this (see the test plan).
- **On failure:** an exception or timeout is recorded as an error. There is no retry. If queue lag exceeds 60 s (proposed), the worker discards the older events and counts them. If the shadow fleet crashes, the queue fills and requests drop events. No user sees any change.

### Step 16. Record shadow results

- **One row per event**, with these fields:
  - date, request ID, user ID;
  - active version, candidate version;
  - active items, and candidate items or error;
  - active latency, candidate latency;
  - active fallback flag;
  - candidate status: `ok`, `error`, `timeout`, `invalid` or `skipped_incompatible`;
  - feature schema version and the row's `as_of`.
- **No join needed:** each event already holds the active output, so comparison does not need the response log.
- **Writes:** batched to the analytics store every few minutes. Lost events shrink the sample but do not bias the rates. The gate counts candidate attempts and checks the sample size (step 18).
- **On failure:** if batch writes keep failing, the fleet stops consuming and the queue drops events. Raise an alert.

### Step 17. Compare daily

- **Starts when:** a daily job runs over the previous UTC day's rows, for the candidate and the active version.
- **Operational metrics:** error rate, invalid-output rate, timeout rate, candidate p50 and p99 latency, and the count of `skipped_incompatible`.
- **Agreement metrics**, excluding rows where the active output was a fallback:
  - overlap@20 (how many of the 20 items the two lists share);
  - rank correlation on shared items (whether the shared items appear in a similar order);
  - the share of candidate items that fall outside the active top 20;
  - catalog coverage across users (how much of the catalog the candidate recommends across all users).
- **Fallback comparison:** the fallback rate for the active version and for the candidate. Both use the candidate's attempts as the denominator, so the two rates cover the same users.
- **Output:** one gate report per day, stored in the registry against the candidate version.
- **Limit:** shadow cannot show whether users prefer the candidate's lists, because users never see them. Quality judgement rests on offline evaluation and these agreement metrics. The user-outcome comparison belongs to the open decision below.
- **On failure:** a failed job does not affect serving. Rerun it. A day with no report does not count toward the 7 days.

## Part E: Promotion and rollback

### Step 18. Evaluate the promotion gate

- **Starts when:** the daily job has produced reports for the most recent 7 full UTC days of shadow.
- **Pass conditions (all must hold):**
  - All 7 days are present, and each day has candidate attempts. A missing or empty day fails the gate.
  - Error rate is under 0.5%. Errors are error + timeout + invalid, divided by candidate attempts over the 7 days.
  - p99 candidate inference latency is under 80 ms over the 7 days.
  - `skipped_incompatible` is zero over the 7 days. Any skip means some users could not be evaluated, so investigate before passing.
  - At least 10,000 candidate attempts (proposed), so that the error rate and p99 are meaningful.
- **Failure:** if any condition fails, the candidate stays in shadow or is rejected. That choice is an operator decision. The gate uses a rolling window, so a clean 7-day run is needed after any failure. A failed gate has no effect on the active version.
- **Output:** a gate report with the figures, the query version and a report hash. A job generates it, not a person.

### Step 19. ML lead approval

- **Starts when:** a gate report passes.
- **Data:** an approval event in the registry. It holds the approver, version ID, gate report hash, timestamp and comment.
- **Rules:**
  - An approval names exactly one version and one gate report. A new report with a different hash needs a new approval.
  - Only the ML lead can approve in the registry (proposed).
  - Approvals expire after 14 days (proposed).

### Step 20. Activate

- **Starts when:** step 13 is called with an approval reference.
- **Checks made by the config service itself, not only by the UI:**
  - the approval exists and matches the version and the report hash;
  - the gate passed for the full 7 days;
  - the target is loaded on at least 99% of pods;
  - the compatibility check passes against the current store manifest;
  - the expected `revision` is still current.
- **On success:**
  - `active_version` becomes the candidate;
  - `previous_active` becomes the old active version;
  - `shadow_version` is cleared, unless another candidate has been set.
- **Watch window (proposed, 1 h):** compare the new active version's error rate, fallback rate and latency with its shadow figures. An alarm in this window can trigger a rollback.
- **On failure:** any failed check refuses the switch and changes nothing.

### Step 21. Roll back

- **Starts when:** an operator or an alarm calls rollback, or a live check fails after a switch.
- **Data moves:** one config write sets `active_version` to `previous_active`, sets `previous_active` to the version being removed, and increments `revision`. The same CAS rule applies. Pre-warm is already satisfied, because `previous_active` stays loaded on pods (step 12).
- **Timing:** about one poll interval (10 s) plus apply time. This is well under the 1-minute requirement. Run a rollback drill on staging for each release. Record the time from the call to the first response from the old version.
- **Compatibility re-check:** the previous version is checked against the current store manifest. If the check fails, rollback is refused and the kill switch (step 22) is used. The schema-removal rule in step 8 is meant to prevent this case.
- **On failure:** the config service is the single write point, so it needs high availability. Pods keep serving their last config while it is down.

### Step 22. Kill switch to popular fallback

- **Starts when:** the active model is causing harm and rollback is not enough, or the feature store is widely degraded.
- **Data moves:** one config write sets `mode` to `fallback_only`. Pods stop calling any model. Responses have `fallback: true` and reason `operator_disabled`. It takes effect within one poll interval.
- **Note:** this is a separate override. It does not change the active pointer, so clearing it restores the previous state.

## Where the open decision attaches

This plan does not choose between two options:

- **Option 1:** shadow, then 100%.
- **Option 2:** shadow, then a live A/B slice (a test where some real users see the candidate's recommendations), then 100%.

The plan keeps the request path, routing config and registry ready for either.

- **Routing:** the `routing` record already has an ordered list of exposure rules. Today it holds one rule: all users go to the active version. A live slice would be another rule, with its own salt and percentage. This should be a config change. Confirm it in design review.
- **Conflict to resolve:** a live slice makes two versions visible to users at once. The requirement "exactly one version is active at a time," as written, does not allow that. Product and the ML lead must decide whether a slice counts as an active version, or whether the requirement changes.
- **Gate:** whatever form exposure takes, the first user-visible exposure of a candidate needs the same 7-day gate and approval (steps 18 to 19). This plan does not relax the gate for a slice.
- **Logging:** every response and every shadow row carries an `arm` field, set to `active` for now. A later test can add values without a schema change.
- **Metrics:** comparing user outcomes is not defined here. It belongs to whichever exposure is chosen.

## Test plan

- **Contract test:** candidate output never appears in a response. The response builder has no import path to shadow output.
- **Load test:**
  - API p99 stays under 150 ms with shadow enabled at 10%;
  - and again with the feature store made to time out at 30 ms.
- **Store failures:**
  - store timeouts: the circuit breaker opens;
  - store fully down: fallback only;
  - materialization stopped: rows expire at 6 h and fallback takes over;
  - shadow fleet killed: no user-visible change;
  - config service unreachable: pods fail static.
- **Compatibility:** a candidate that requires a feature the store lacks never runs, in shadow or as active. It is recorded as `skipped_incompatible`.
- **Hash:** fixed input vectors give the same cohort on every pod and across restarts.
- **Switch and rollback drill:** measure the time from the rollback call to the first response from the old version. Target: under 60 s, measured on the real fleet.

## Open questions

1. Live A/B slice, or straight to 100%? And does a slice count as an active version? (Product and ML lead.)
2. Is a minimum shadow sample of 10,000 attempts right? (Proposed. Confirm with the ML lead.)
3. Is one shadow candidate at a time enough?
4. Do three model versions fit in pod memory?
5. Should a model error use the same popular fallback as a feature fallback? (Proposed: yes.)
6. How long should shadow rows be kept? They contain user IDs, so this needs a privacy review.
