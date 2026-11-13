## Review of ms-01 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary at the top that says what checkout does and how the main flow goes.
- Replaced the 'How to read this' section with a short Terms list defining service, event, outbox, reservation, claim, idempotency key and webhook in one line each.
- Removed the O1, C1, I3, P4 style codes from the diagram labels, so each box stands alone. Node ids and structure are unchanged.
- Rewrote the step list so every step has the same four parts: what starts it, what it does, what it stores, and what happens when it fails.
- Merged the 'What each service stores' table into the steps and deleted it, which removes duplicated status lists and field lists.
- Merged the separate declined, succeeded and confirmed notes into steps 5 to 8, and moved the sweeper and watchdog into the steps where they apply.
- Folded the customer-facing result and mailer notes into one short paragraph after the diagram and one open question.
- Replaced 'Decisions I made that you should check' with a closing Open questions section covering late claim, tunable numbers, cart emptying and the mailer.
- Renamed 'Every failure branch' to 'What happens when things fail' and kept it as a single table.
- Cut the 'Place order returns at once' and similar prose that repeated the diagram, and shortened repeated wording about idempotency and repeat deliveries.
- No separate build or rollout section was added, because the brief and document contain no rollout content.

### Holes
- None.
