## Review of mig-02 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short terms list (usage event log, ledger, payment provider, shadow store, config service) and a one-line goal in the Summary so a reader new to the project can follow.
- Explained in the diagram intro that rollback is four numbered steps and that rollback from shadow needs none.
- Removed references to 'the brief', which the reader has not seen; reworded as 'stated requirements' or dropped them.
- Clarified the comparison bullet: which invoices are compared in shadow versus both.
- Rewrote the shadow rollback path to remove the ambiguous 'keep or discard' phrasing in the main sequence.
- Explained what the idempotency key does (repeat of the same key is the same charge).
- Clarified the nightly-job failure row, which previously said both 'does not count' and 'breaks the streak'.
- Added '(days 0 to 34)' to the automatic rollback failure row to match the locked-state row.
- Minor wording tightening throughout, without changing the diagram, rules, or format.
- Added definitions for billing period and mismatch to the terms list so the document is self-contained.
- Rewrote rule 1 from 'exactly one engine' to 'at most one engine', since during rollback steps 1 to 3 nobody charges.
- Clarified rule 2: it applies to rollbacks from both/new_only, and says neither engine starts new charges until handoff (the old wording implied the new engine kept charging).
- Explained that new_only_locked is not a fifth flag value but new_only after day 35, and defined 'day N' as counted from entering new_only.
- Described rollback from shadow as a single action rather than a single step, avoiding confusion with the four numbered steps.
- Made the worker charge rule in section 5 explicit per step (steps 1-3 no new charges; step 4 old engine charges only queued periods) instead of the vague 'unless this step allows it'.
- Moved the post-rollback gate reset and the day-35 lock into labelled paragraphs ('After a rollback', 'No way back') and trimmed duplicated mismatch definition from the gate text.
- Added definitions for 'Rollout controller' and 'Gate' to the terms list, since both are used before being explained.
- Rewrote summary rule 2, whose sentence about which engine charges during rollback was confusing and omitted the step-4 exception.
- Added a short reading guide above the diagram covering rollback steps, the locked state, and self-loops.
- Broke the comparison bullet in section 3 into two sub-bullets, one per mode.
- Spelled out what the idempotency key and the ledger uniqueness constraint each do.
- Glossed 'fix forward' in the failure table as repairing the new engine in place.
- Left the diagram logic, rules, and open questions unchanged.

### Holes
- None.
