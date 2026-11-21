## Review of ms-01 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Replaced the bare 6-box flowchart with a full flowchart naming the service, trigger and database at each step, and added all failure branches (short stock, declined, late success, failed refund, duplicate webhook).
- Folded the six loose notes (expiry, idempotency, dedupe, late payment, refunds retried, order statuses, cart via event) into the numbered steps and a single failure table, so each rule is stated once.
- Added the opening summary and a short terms list in plain words, placed before the diagram, with the steps after it.
- Gave every step the same four parts: what starts it, what it does, where its data is kept, and what happens on failure.
- Dropped the vague 'Order statuses are tracked' note and named the actual statuses (PENDING, CONFIRMED, cancelled with a reason) where they are set.
- Kept refund handling to one simple mechanism (stay PENDING, retry on a timer, alert a person) with no lease or takeover rules, and moved the unsettled numbers to Open questions.

### Holes
- None.
