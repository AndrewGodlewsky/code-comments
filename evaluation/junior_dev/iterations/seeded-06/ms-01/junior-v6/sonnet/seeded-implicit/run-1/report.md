## Review of ms-01 (junior-v6, author sonnet, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Redrew the diagram: Refund now only follows the late-success stock-gone branch, not every Confirm.
- Added all failure branches to the diagram: short stock, declined, duplicate webhook, lapsed hold, failed refund.
- Stated that Order drives the sequence via HTTP calls and waits for payment events.
- Added terms, per-service storage and order statuses.
- Added dedupe key (provider event id, unique in Payment DB) and the outbox-style event delivery for lost events.
- Defined refund retry as persistent PENDING record retried until success with an alert; added open questions for missing webhook and alert details.
- Added FAILED_TECHNICAL status and retry-with-same-order-id handling for failed or timed-out Inventory and Payment calls, with hold release (Q9, Q10).
- Added rule that a payment success for an order no longer AWAITING_PAYMENT triggers an automatic refund, so an uncertain charge is never kept (Q10).
- Stated that Order subscribes to payment events and acts only when AWAITING_PAYMENT, so repeats and downtime are safe (Q11).
- Made claim idempotent per order id and retried until Inventory replies, with an alert if it keeps failing (Q12).
- Defined that each Place order press makes a new order id, so a retry gets a new key and hold (Q13).
- Added one-open-order-per-cart rule so a double press returns the same order (Q14).
- Added terms for Event and Order id, an Inventory one-hold-per-order note, and open questions on whole-cart clearing and retry limits.
- Added the Order crash sweep: orders stuck in AWAITING_STOCK are resumed by repeating the reserve call, because such an order would otherwise block the cart for good.
- Stated that the screen polls Order for the status, in the opening paragraph.
- Stated that no new order can start for a cart while one is open, and tied the blocked cart to the no-webhook open question.
- Added that the charge request carries the order id and the snapshot amount (in the diagram and a note); added a Snapshot term.
- Said in the diagram that Payment consumes RefundRequested and finds the payment by order id; added a note that the order status does not change when a refund finishes or fails.
- Added open questions: how the payment method reaches the provider, the poll interval, and the crash sweep timings.
- Order crash sweep now also covers orders AWAITING_PAYMENT older than two minutes with no charge-accepted mark, and says a crash after the reserve reply is covered by the AWAITING_STOCK case (a real hole: such an order would block the cart).
- Order stores a 'charge accepted' mark on AWAITING_PAYMENT orders; the diagram sets AWAITING_PAYMENT before the charge call and marks the charge accepted after Payment replies.
- Payment saves the PENDING payment record before calling the provider, so a provider failure or crash is retried safely and a record always exists when a charge might have happened.
- Release of the hold is stated as best effort, tried once, with the 10 minute expiry as the backstop (diagram and notes).
- Event handling: a consumer acknowledges only after it finishes handling, so a crash during the claim makes the broker redeliver and Order repeat the claim; added to the Event term and the Receiving events note.
- Webhook matching: by order id, sent to the provider as the charge reference; added a diagram branch and a note for a webhook with no matching payment record (store event id, alert a person, reply OK, publish nothing).
- Open questions: added provider reference echo not verified, broker redelivery settings, and unmatched webhooks to the alert destination item.
- Reordered into: summary paragraph, terms, diagram, storage, numbered steps, failure table, open questions.
- Added a one-paragraph summary stating the flow and why Order orchestrates, plus a line on the monolith today.
- Merged the many scattered Notes bullets into 8 numbered steps, each with trigger, action, storage and failure handling.
- Merged the crash, failed-call, charge-uncertain, receiving-events and duplicates notes into the steps where they apply.
- Added a failure table.
- Added terms: Open order; defined Order id, Snapshot and Event more plainly.
- Added the outbox tables to the storage list; added Payment's unique constraint on event ids.
- Kept every stated fact: 10-min hold, 30-min webhook, order id key, snapshot, all-or-nothing, full refund, email, no partial orders, refund never dropped, cart cleared only on confirm, all open questions.
- Cut repetition (double press and one-open-order rule stated once; the 'Payment does not look the amount up' repeated lines).

### Holes
- None.
