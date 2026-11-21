## Review of ml-01 (junior, author haiku, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Restructured the plan into a summary, a terms list, the numbered steps by part, a failure table and open questions, as the junior-dev layout asks.
- Step 1 now starts the 140 ms deadline at request receipt (Q1).
- Step 5 now says the active pool is a separate set of model servers behind an internal load balancer, and defines transport error (Q2).
- Replaced the separate operator and promotion tool with one control tool, defined in Terms, and used it in steps 13, 15 and 20 to 22 (Q3).
- Defined the status table in the serving config store, in step 14 (Q4).
- Step 7 states that model_version comes from the active pool's reply. Step 14 states that mixed versions during the poll window are accepted (Q5).
- Step 13 defines approved as having an approval record from step 21. Step 15 states that the rollback target keeps that record (Q6).
- Step 6 now checks the candidate manifest in memory, and queues shadow only after the active model succeeds, so fallback requests are never queued (Q7).
- Step 18 now defines the shadow worker as a per-instance background task. Step 19 now defines per-instance drop counters, summed daily (Q8).
- Step 12 now says what triggers the eligibility re-check, and what an ineligible active version does (Q9).
- Step 20 now defines error rate as timeouts plus errors plus invalid outputs, over attempts, so the gate is unambiguous.
- Merged the components table into the terms list and moved its state facts into the steps that use them. Removed repeated cross-references between steps and repeated failure lines. Every requirement and number from the first version is kept.
- Step 2 and step 14: API instances only read config. Pool servers poll, download, verify and load models, and write the status rows (answers Q10).
- Step 4: added the schema_version check, with feature_mismatch on a difference (Q12).
- Step 5: a pool server that does not hold the named version returns an error, which falls back as model_error (Q11).
- Step 11: registration stores a fixed sample feature row for warm-up (Q13).
- Step 12: added an append-only eligibility history, so step 20 can check the whole window (Q15).
- Step 14: the warm-up runs on the stored sample row; an incomplete switch does not roll back automatically and leaves the servers mixed until an operator acts (Q13, Q14).
- Step 16 and 17: percentage is a whole percent, and the cohort threshold is percentage times 100 (Q17).
- Step 19: each shadow record carries candidate version and salt, and the daily job filters on them. Overlap at 20 is reported, not gated (Q16).
- Step 20: the daily comparison job decides when 7 days have passed and runs the gates. The operator then asks for approval through the control tool (Q17).
- Step 22: active pool servers load the new version from the object store, not from the shadow pool (Q13).
- Failure table: feature_mismatch and model_error rows now cover the schema_version check and the version-not-held case.
- Open questions: added whether a switch should wait for pool servers to load the new version, and whether overlap at 20 should become a gate.
- Restructured: summary and terms before the steps, with the latency budget kept. Dropped no stated requirement, limit, number or assumption.
- Step 5: the API makes one attempt and does not retry on another pool server (Q18).
- Step 5: the model receives only the feature values its manifest lists, not the row's metadata or user_id (Q24).
- Step 14: a server still loading keeps its current version and answers only requests that name it; requests naming the new version fall back as model_error (Q19).
- Step 14: each server keeps current and previous versions; a swap unloads the old previous version, which stays in the registry (Q20).
- Step 15: the rollback target is defined as the version active in the revision before the current one, taken from the config history (Q20).
- Step 16: the control tool writes shadow starts as CAS revisions that set started_at; shadow pool servers load and unload the candidate with the step 14 load path (Q21, Q23).
- Step 18: the feature values the candidate's manifest lists go to the shadow pool (Q24).
- Step 19: a change to candidate, salt or percentage resets started_at, so earlier records fall outside the window (Q23).
- Step 20: failure outcomes split into rejected (candidate's own numbers fail) and stays in shadow (window fails, or no approval yet) (Q22).
- Step 21: the approval record names the gate report hash it reviewed (Q22).
- Terms: added the gate report definition, needed by steps 20 and 21.
- Open questions: added whether the load balancer retries on its own, and whether an approval must match the latest report hash (Q18, Q22).
- Changed: The model call step now says the pool reply carries the version it served, and a different version counts as model_error, so model_version names the version that answered (Q25).
- Changed: The model call step now says the API enforces the 140 ms deadline by closing its call and ignoring late replies, and the pool server drops abandoned work (Q29).
- Changed: The activation step now says the shadow clear and the activation are one CAS write, and that samples queued for the candidate afterwards are discarded without being counted (Q26).
- Changed: The control tool term and the activation step now say it checks the stored gate report and approval record but does not run the gates (Q27).
- Changed: The no_config reason now also covers the period before the first activation, in the serving config step, the activation step and the failure table, and the first activation has no previous version (Q28).
- Changed: The switch step now says that new or restarted pool servers load the config's version and report ready before taking traffic, and that status rows from servers no longer in the pool are ignored (Q30).
- Changed: The model_error row of the failure table now includes a reply that names a different version (Q25).
- Changed: Rewrote for a newcomer: removed step-number codes such as Assumption and Q references, stated each rule once, moved the freshness rule into one place, and kept every requirement, limit and number from the brief and the first version.
- Rewrote the whole document once in the order: what this is, terms, latency budget, components, the steps, failures, decisions before build, the open gap, open questions.
- Replaced the Part A to F labels with plain phase headings and one continuous step numbering from 1 to 24. Removed cross-references that sent the reader to other answers; step numbers now appear only where a reader needs to jump to a related step.
- Summary cut to a few sentences: what the API does, the fallback rule, the shadow and approval gate, and how the system works today.
- Merged the duplicate statements of the same rule into one place: API instances only read config (step 2 only), shadow never affects the request path (step 16 and 18 kept at one place each), the popular list does not depend on the model or store (step 7 only), and the one-attempt, no-retry rule (step 5 only).
- Merged the separate assumptions list and decisions list into one 'Before build' list of seven decisions, each with its default.
- Moved the rule that queued shadow samples are discarded after activation into step 22, its only place of use, and removed the duplicate in step 18.
- Kept every number, limit and rule from the first version: 20 IDs, 150 ms p99, 30 ms lookup, 140 ms internal deadline, 6 h from source_as_of, 24 h row deletion, 90 min alert, 36 h popular alert, 2 min config alert, 10 s polls, 2 min switch timeout, 500 ms shadow deadline, 10% cohort, bucket less than 1000, 7 days, 0.5% errors, 80 ms p99, 1% drops, 1-minute rollback budget with its 10 s, 5 s and 30 s parts.
- Kept the reasons that the Q&A rounds added, in one short clause each: why the model gets only manifest features, why there is no retry, why nothing rolls back automatically, why a failed reply naming another version is an error, and why the discarded samples are not counted.
- Kept the components table, the failure table with all 11 rows and the open questions list with all ten items.
- Added plain one-line definitions for terms a newcomer would not know, including manifest, eligible, CAS, object lock, warm-up inference, shadow cohort and salt, and added a short definition of operator, which the first version left implied.
- Kept the open A/B gap section whole, including config shape, the invariant conflict, the slice gate, salt, rollback and the limit of shadow, and marked clearly that it is not decided.

### Holes
- None.
