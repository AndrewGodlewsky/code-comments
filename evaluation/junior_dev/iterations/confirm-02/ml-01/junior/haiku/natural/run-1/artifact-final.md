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