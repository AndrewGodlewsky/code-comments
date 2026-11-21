## Review of ev-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short "Why" paragraph that states the problem in plain words before the design.
- Added a "Parts" list that says what each service owns, and a "Terms used below" list defining transaction, outbox, consumer group, idempotent, DLQ and idempotency key for a reader new to the stack.
- Wrote out the happy path as numbered steps, and described both cancellation paths in their own short sections.
- Added the two cancellation branches to the Mermaid sequenceDiagram (stock unavailable and card declined), since the draft only named them and the brief asks for them in the diagram. Each branch ends in OrderCancelled and a cancellation email.
- Added notes in the diagram showing which writes happen in one transaction, and the "(relay)" label on each publish.
- Added a "Where state is written" table covering each service's writes and when they happen.
- Replaced the one-line "Consumers are idempotent" with how duplicates are handled: the processed-eventId record, Payment's idempotency key taken from the StockReserved eventId, and the email record.
- Replaced "usual retries and a DLQ" with the exact retry schedule (1 s, 10 s, 60 s), what happens after the fourth failure, and that nothing else is undone.
- Stated that email is best-effort and that only Order Service changes order status.
- Added a plain-language opening to the 'Parts' list: what the broker is, what a 'topic' and 'keyed by order ID' mean, and what 'an external card provider' is.
- Added a 'Relay' term and explained that the relay marks a row sent only after broker confirmation.
- Stated the delivery guarantee (at-least-once) in its own short paragraph before the duplicate rules.
- Added a 'Who reads which event' table so the reader can see each service's inputs and outputs, and a sentence explaining how Order Service learns the outcome.
- Explained why the request handler never calls the broker (a slow service cannot slow the customer's request).
- Added the rule behind both cancellations: no charge without a stock reservation.
- Clarified in the diagram that the Payment idempotency key is the StockReserved eventId.
- Added a note that every consumer logs handled eventIds in the same transaction as its change, and that the log and change succeed or fail together.
- Expanded the duplicate section: how Order Service ignores repeated PaymentCaptured events, and how Payment avoids a second charge after a crash, step by step.
- Clarified that the four attempts are the first attempt plus three retries.
- Stated that a card decline is not an error, and that email is never an input to an order decision.
- Added that on-call decides what to do with a dead-lettered message and its order.
- Notification row in the state table now says the record is keyed by eventId, and a sentence says every consumer logs eventIds.
- Not stated in the brief and left out of the document: whether a failed email send is retried. Confirm this before implementation.
- Added a plain-language opening that says what changes and why, before the parts list.
- Added a Terms section that defines event, publish, consumer, handler and the relay's acknowledgement step, so a reader outside the project can follow the rest.
- Stated that the relay publishes oldest row first, which the brief specifies and the original omitted.
- Clarified the Happy path so each step names the outbox write and the relay publish separately.
- Added a short 'How to read the diagram' note before the Mermaid block. The diagram itself is unchanged.
- Reworded the retry failure to say the consumer stays on the failing message until the fourth attempt. This is inferred from the brief's 'moves on' wording, not stated outright, and it is what keeps per-order ordering intact.
- Reworded the 'who reads which event' note to say Order Service learns outcomes from events that Inventory and Payment publish.
- Turned the state table's Order Service row into a clearer timeline by status, and removed repeated wording in the Failures bullets.

### Holes
- None.
