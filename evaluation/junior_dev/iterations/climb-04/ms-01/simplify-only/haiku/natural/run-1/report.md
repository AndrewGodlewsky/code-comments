## Review of ms-01 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the 'Rules the diagram enforces' list. Each rule now sits in the step that enforces it.
- Merged the 'Stores by service' table into a 'Stores' line in each step.
- Merged the 'Terminal states' table into one failure table. Added rows for hold lapse, commit timeout, webhook never arriving, refund failure, duplicate webhook and broker down.
- Moved the sweeper, the 35-minute reconcile, and the commit-timeout rule into the steps and failure table that use them.
- Moved the 'Claim means commit' decision into Terms, and kept it as an open question so product can accept or reject the cost.
- Moved the cart-edit decision (remove confirmed lines only) into step 7 with its reason.
- Moved the at-least-once delivery decision into Terms, since each consumer checks state before it acts.
- Replaced the 'Decisions and open points' list with five open questions that need an owner's answer. Removed the decisions that are now settled in the steps.
- Added a short summary that says how checkout works today (inside the monolith) before the new design.
- Added a Terms section with one-line definitions of the terms a newcomer needs, placed before the diagram.
- Kept the Mermaid diagram unchanged. No new mechanism was added, and the brief's behaviour is unchanged.

### Holes
- None.
