## Review of auth-02 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into the skill's layout: summary (with how the system works today), terms, steps, failure table, open questions.
- Split into Part A (runtime: startup load, readiness, per-request key reads, refresh, local dev) and Part B (build and rollout), so how the system runs is separate from how we ship it.
- Added a Terms section defining secret store, version id, APP_ENV, SecretStore, SecretCache, orders-api-prod, readiness probe, rolling deploy, security on-call, platform and revoke.
- Merged old Steps 3 and 4 (create keys, prove they work) into one step B3.
- Merged the code steps (loader, readiness, clients, refresh, local dev, CI guard) into Part A plus one PR step B4, so the CI guard rule is stated once.
- Merged old Steps 12 and 13 into B6 and B7 under clearer names, and made the old Phase 0 step B1.
- Cut the Roles section (folded into the terms) and the redundant retry arithmetic (1 initial plus 3 retries, 4 attempts, about 6 seconds).
- Cut the explanation of why startup retries are sized as they are and the rollout-in-flight detail repeated across steps.
- Replaced step-number cross-references like Step 14's confirmation list with named steps and a one-line reason (for example, readiness checks presence, validity is checked in B3).
- Added a failure summary table for the runtime (A6).
- Moved the reason for the single PR into B4 and the reason readiness does not check validity into A2, where each part appears.
- Kept the rotation-cadence open question at the end and unchanged in intent (no cadence chosen, no scheduled job).

### Holes
- None.
