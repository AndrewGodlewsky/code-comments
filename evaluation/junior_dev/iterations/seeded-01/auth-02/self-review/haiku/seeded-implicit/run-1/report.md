## Review of auth-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a Terms section defining secret store, service identity, pod, readiness probe, rolling deploy and provider, for a reader who does not know the project.
- Added a 'How the app reads keys at runtime' section covering startup load, readiness, refresh, per-request lookup, memory-only storage and the secret_versions field, so the runtime behavior is explained in one place.
- Stated that provider clients must call secrets.get() per request, because the current code copies the key once at construction and would ignore refreshed values.
- Clarified in step 2 that the prod values written to the store are the leaked live keys, stored only as a bridge until step 9 replaces them.
- Made each step state what starts it, what moves, where state lives, and what happens on failure, following the brief's format.
- Added a pre-check in step 9 that providers allow two active keys at once, and a plan for the gap if they do not.
- Changed step 8 verification to check each of the 4 pods directly, because one request can reach any single pod.
- Added the rollback warning in step 10: images built before the change hold keys that are revoked in step 9, so rolling back to them breaks customer requests.
- Clarified step 9 so the old key is revoked only after every pod reports the new version id.
- Added an open question for the rotation schedule, left undecided as the brief requires, and an open question about provider overlap.
- Added a short opening section that says what the plan does and why the keys are treated as leaked.
- Expanded the terms list with secret version, refresh cycle, last good value and revoke, and explained each term in plain words.
- Explained what happens when startup load fails: the process exits, so it never becomes ready and gets no traffic.
- Step 2: named the security on-call as the person who creates the prod secrets, since engineers cannot write prod.
- Step 6: rewrote the 'Starts' line so it says that steps 3 to 5 and step 6 ship in one release, and why that ordering matters.
- Step 8: stated that every pod must be checked directly, because one request may reach any pod.
- Step 9: made the timing explicit, with a minimum wait of 5 minutes, a check on all 4 pods, and a 10-minute threshold for investigating a pod that is still on the old version. Left the length of the error-watch period to Security.
- Kept the rotation cadence as an open question and did not choose one. Kept the overlapping-keys question open as well.
- Kept the step format (starts, what moves, where state lives, if it fails) and the runtime section, with only wording changes.
- Replaced the startup retry wording with the brief's rule: one attempt plus 3 retries, 2 seconds apart. The old text said 3 tries in total, which does not match the brief.
- Added a short 'How things work today' section so a reader new to the project sees the current problem before the target design.
- Defined more plain terms (image, pod, rolling deploy, refresh, provider) and removed jargon such as 'bridge' without explanation.
- Stated in the runtime section that a store outage does not affect running pods, but a pod that restarts during an outage cannot become ready, which can reduce capacity.
- Step 6 now says steps 3 to 6 are one change set that merges together and deploys together in step 8, so the ordering with steps 7 and 8 is clear.
- Step 2 now explains that the leaked live values are a temporary bridge and that step 9 replaces them.
- Step 4 failure text now says step 5 keeps pods without keys from receiving traffic, which is the actual mechanism.
- Sentences shortened throughout; the step structure (starts, what moves, state, failure) and all requirements are unchanged. The rotation cadence remains an open question and no cadence was chosen.

### Holes
- None.
