## Review of ms-01 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged the fixed requirements into a short rules list plus a terms list (order snapshot, reservation, claim, idempotency key, webhook, event), since the first version used these without defining them.
- Expanded the diagram into service subgraphs showing what each service stores, with every failure branch: short stock, declined, duplicate webhook, late success with and without stock, failed refund retry loop.
- Replaced the one-line notes with numbered steps stating trigger, action, who stores data and failure handling; replaced 'Order statuses are tracked' with named statuses (PENDING, CONFIRMED, CANCELLED variants).
- Added the 10 minute hold, 30 minute webhook delay, order snapshot, all-or-nothing reservation, order id idempotency key, no partial orders, and cart-unchanged-on-failure rules that the first version lacked or left vague.
- Made 'cart cleared via event' concrete: Cart clears only on OrderConfirmed.
- Made refunds concrete: stored before sending, order id as key, marked DONE only on provider confirmation, retried with backoff, alert after repeated failures. This is a simple single mechanism with no lease or takeover rule.
- Kept the first version's 're-reserve, otherwise refund and cancel' rule, now with the all-or-nothing detail.
- Added a failure table and a separate Build order section.
- Added open questions for the missing-webhook-after-30-minutes case, who sends email, and the refund alert threshold. These are undecided and not invented.

### Holes
- None.
