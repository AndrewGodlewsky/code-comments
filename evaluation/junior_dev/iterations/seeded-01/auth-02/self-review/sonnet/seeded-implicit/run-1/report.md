## Review of auth-02 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the plan from a terse 10-item list into numbered steps that each state trigger, what moves, where state lives, and failure behaviour, as the brief required
- Reordered the rollout so the mechanism is deployed with unchanged key values first, then keys are rotated, then old keys are revoked; the original revoked/rotated without a safe gate
- Added an explicit adoption gate (step 7): every pod's /healthz must report the new version id before any old key is revoked
- Added a separate runtime section (R1-R5) covering startup load, retry semantics (1 attempt + 3 retries), readiness, per-request key lookup, 5-minute refresh, and last-good-on-failure
- Stated that clients must stop copying the key at construction, since this is why a refresh would otherwise have no effect
- Spelled out access policies including negative tests (engineers cannot read prod; orders-api-prod cannot write or read dev)
- Added rollback consequences: images from before the migration stop working once old keys are revoked, and local runs on old checkouts break
- Noted the rolling deploy with maxUnavailable 0 makes a failed key load halt the rollout without customer impact
- Replaced the vague 'Don't log secret values' with concrete rules (no Authorization header or exception text containing keys; log version ids only)
- Added a short overview and term definitions so a reader new to the project can follow
- Listed assumptions (two active keys per provider, no other key consumers, sandbox keys exist) and kept the rotation cadence as an open question without picking one
- Fixed a logic error in step 2: it claimed a wrong prod value would be caught in step 4 because the pod would not become ready, but readiness only proves the fetch succeeded. Added a step 2 check that tests each stored value with a harmless provider call before any deploy, and moved the failure handling accordingly.
- Step 3 now starts when step 2 is done and checked.
- Added a short deploy background paragraph (4 replicas, rolling deploy, readiness probe, rollback) so a reader without deploy.md can follow steps 4 to 8.
- Explained KMS inline and stated that APP_ENV is an environment variable and the only one involved.
- Moved the 5-minute pickup note into step 6's what-moves list and clarified why requests keep working during a bad-value rollback.
- Fixed the Part 1 reference to 'Section 2' to 'Part 2'.
- Made small wording fixes: 'no extra retries' in R5, removed redundant sentences, and dropped 'value' from the step 4 fix list.
- Reformatted the deploy background and terms paragraphs into bullet lists for easier scanning.
- Reworded step 7's timing to 'for example 10 minutes in total' so the margin is unambiguous.
- Changed 'run these tests' to 'test with real identities' in step 1, and made small wording tweaks elsewhere.
- Kept all steps, requirements, the open question and the format unchanged.

### Holes
- None.
