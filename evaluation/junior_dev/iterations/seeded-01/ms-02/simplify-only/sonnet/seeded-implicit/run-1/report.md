## Review of ms-02 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-sentence summary and a paragraph on how sending works today at the top.
- Added a short Terms section defining monolith, service, broker, MailRelay, route, retry policy and idempotency key.
- Rewrote the build list as a runtime flow of five numbered steps, each with trigger, action, state and failure handling.
- Merged the scattered notes (retries, dedupe, rollback, watching) into the steps, terms and rollout list.
- Replaced the 'retries same as today' note with a single retry policy definition.
- Added one failure table instead of failure handling spread across notes.
- Separated the runtime description from the Build and rollout order section and added the 3-day, latency and 7-day gates.
- Added an Open questions section at the end for the unsettled rollback claim and row retention.

### Holes
- None.
