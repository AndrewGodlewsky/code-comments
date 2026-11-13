## Review of mig-02 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a plain-language opening describing how billing works today, then the rollout in two short paragraphs, replacing the abstract summary.
- Added a short Terms section defining shadow store, ledger, mismatch, idempotency key, rollback record and gate in one line each.
- Removed the Rules the diagram implies header and merged those bullets with the gate-is-not-a-trigger note into Notes on the diagram, placed just after the diagram.
- Merged the double-charge section into a separate Rollback steps section, and split forward steps (Running the rollout) from rollback steps so the two flows are apart.
- Dropped the extra step-1 label from old_only to shadow and the redundant description of mode entry time as its own bullet by folding it into the billing_mode bullet.
- Removed 'Who charges' wording duplication and the stray comparison detail from the mode table (mismatch definition now lives in Terms).
- Merged the manual and automatic rollback triggers into one sentence in Rollback steps, and shortened the rollback-from-shadow note to avoid RB1 mention.
- Removed codes-pointing language such as 'RB1 and the flip' for shadow rollback; shadow rollback is now described in plain words.

### Holes
- None.
