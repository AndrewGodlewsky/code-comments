## Review of ms-01 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Cut the bare service list and the one-line notes, and replaced them with a summary and a terms section that define Order, Cart, Inventory, Reservation, Claim, Payment, Provider, Order id, Webhook and Event in one line each.
- Replaced the five-node flowchart with one that shows every failure branch in the brief: short stock, declined payment, late success after the hold lapsed, failed refund, and duplicate webhooks. Each node names the service that acts.
- Dropped the 're-reserve' option for late payments. The brief requires a full refund and a cancelled order, so re-reserving is not part of the plan. It is now an open question.
- Replaced the vague notes ('Order statuses are tracked', 'Refunds are retried', 'Cart cleared via event', 'Idempotency keys on provider calls', 'Webhooks can be late or duplicated, so dedupe') with eight numbered steps. Each step states its trigger, its work, the service that keeps the data, and its failure handling.
- Merged the 'Reservations expire after 10 min' note into step 2, the diagram note and the failure table, so the expiry is stated where it applies.
- Decided that Order cancels and emails the customer only after the refund is confirmed, so the email is true when sent. Recorded this in step 8.
- Added a failure table covering every failure path, including a call that fails or times out, a missed OrderConfirmed event, and a failed release.
- Added open questions for the gaps the file cannot answer: a missing webhook, whether refunds confirm by webhook, the alert threshold for stuck refunds, and whether to re-reserve before refunding.
- Length: the file is well over one and a half times its first length. The brief requires the failure branches, the owner of each step and each stored record, so the added length is needed to cover them. Repeated wording was removed where the diagram and the steps overlapped.

### Holes
- None.
