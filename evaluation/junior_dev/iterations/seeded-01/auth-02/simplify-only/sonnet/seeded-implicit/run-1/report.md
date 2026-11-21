## Review of auth-02 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged 'Don't log secret values' and the memory-only rules into one runtime-facts list
- Merged the 'Delete api_key entries', 'CI check' and 'make run APP_ENV=dev' steps into one step (6)
- Merged the code steps (new secrets module, switch clients, /healthz change) into one step (3), with runtime behaviour in a short sub-list
- Merged the 'Deploy + verify' step and the readiness gating into a single deploy step (5)
- Split the old rotate-and-revoke step into rotate (7) and confirm-then-revoke (8) so the revoke gate is explicit
- Added a short summary of how the system works today, a terms list, and a single failure table at the front and end
- Kept the old keys in the image for one release as the rollback fallback (step 4), and moved the rollback note to after revoke
- Separated runtime behaviour from rollout steps and gave every step the same four parts: trigger, does, state, failure
- Moved the rotation-schedule open question to the end and kept it undecided

### Holes
- None.
