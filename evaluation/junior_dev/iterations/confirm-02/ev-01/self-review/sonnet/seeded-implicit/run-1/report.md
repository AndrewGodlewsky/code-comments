## Review of ev-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the thin original into a self-contained document: added an overview defining each participant and the single topic keyed by order ID.
- Stated the three cross-cutting rules once (outbox plus relay, dedupe by eventId in a processed_events table, retry 1s/10s/60s then DLQ) instead of repeating 'via outbox' or leaving them as vague phrases.
- Redrew the diagram to cover the happy path and both cancellation paths (StockUnavailable, PaymentDeclined) using alt/else, adding the card provider and notes showing where state is written in each transaction.
- Resolved the decisions left open in the brief: Inventory releases stock on PaymentDeclined, Order learns outcomes by consuming result events and only moves from PENDING, Payment uses orderId as the idempotency key, and email is triggered by OrderConfirmed/OrderCancelled.
- Spelled out duplicate handling, the crash-after-charge case, provider timeout/5xx behaviour (order stays PENDING), and best-effort email.
- Replaced jargon and shorthand (such as 'usual retries', 'idempotent') with explicit descriptions and defined DLQ on first use.
- Added that every event carries eventId, orderId and a type, and defined consumer group inline, so the doc stands alone.
- Reordered decisions so 'card never charged without stock' comes before the Payment idempotency detail.
- Rewrote the Payment idempotency paragraph: replaced 'This matters in one case' with a plain statement of the crash scenario and made the outcomes a clear list.
- Clarified the relay and DLQ wording ('consumer moves on to the next message', 'finds the eventId already there').
- Explained why duplicate emails can still occur (the send happens outside the transaction), rather than just citing at-least-once delivery.
- Minor wording tightening and consistent use of 'Order Service'; the diagram is unchanged.
- Defined jargon on first use: outbox, at-least-once, consumer group, card provider as external service, and the four-attempts-in-total count for retries.
- Added why the outbox pattern works (event exists if and only if its state change does).
- Scoped rule 1 to services that publish, so it no longer implies Notification has an outbox.
- Stated that a failing handler's transaction rolls back.
- Added a line before the diagram saying retries and duplicates are not drawn and rules 2 and 3 apply to every consuming arrow.
- Diagram notes: replaced '(or none)' with 'only if stock is available'; added eventId to Order Service notes and a transaction note for Inventory's release, for consistency with rule 2.
- Clarified the email duplicate scenario (send succeeds, crash before recording eventId, redelivery).
- Minor wording tightening, such as 'only in' for where state lives.

### Holes
- None.
