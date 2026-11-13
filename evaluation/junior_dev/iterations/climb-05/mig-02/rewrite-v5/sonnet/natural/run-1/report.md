## Review of mig-02 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added an opening summary paragraph covering how billing works today, the main flow and why it is shaped this way
- Added a Terms section defining usage event log, billing ledger, shadow store, payment provider, billing_mode, rollout controller, billing period, idempotency key, mismatch, Gate A and Gate B
- Moved the Gate A and Gate B lines out of the diagram notes into Terms, placed the summary and terms before the diagram and notes after it
- Merged the retention-hold, shadow, and both special cases into step 4 of Rollback steps
- Moved the reason the flag flips last into step 6 and removed its separate bullet
- Stated the rollback triggers once, at the head of Rollback steps
- Merged the Day 35 clock open question into the diagram note, since it is a stated assumption
- Cut the 'steps are idempotent' row detail into one line at the head of Rollback steps; shortened several failure table rows
- Removed the repeated mismatch definition from the shadow row of the mode table (now in Terms)
- No change to the plan's behavior or the diagram

### Holes
- None.
