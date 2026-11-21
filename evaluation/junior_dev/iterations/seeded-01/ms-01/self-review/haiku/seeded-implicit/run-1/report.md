## Review of ms-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the five-box happy-path flowchart with a full flowchart that shows every branch the brief requires: short stock, declined payment, late success after the hold lapsed, failed refund, and duplicate webhook. The draft had none of these failure branches.
- Put the owning service, the trigger and the stored state into each flowchart node, so a reader can see who does each step without the brief.
- Replaced the vague notes (for example 'Order statuses are tracked' and 'Cart cleared via event') with named order statuses, named events, and a list of what each service stores.
- Added a plain explanation of why the stock can be released while payment is still pending: a hold lasts 10 minutes, but a provider result can take up to 30 minutes.
- Spelled out the idempotency key (order id for charges), the webhook deduplication rule, and the rule that refunds are retried and never dropped.
- Kept the draft's option to re-reserve stock after a late success, before refunding. The brief only requires refund and cancel, so the re-reserve step needs confirmation.
- Added a short section on the rules that keep the flow safe, including the cart rule and the rule against partial orders.
- Added a Terms section defining hold, snapshot, idempotency key, webhook, event id and broker, so a reader new to the stack can follow the diagram.
- Added to the Payment decision node that the event id is recorded when a new event is first handled, which the rules describe but the diagram did not show.
- Renamed the declined outcome to 'store attempt as DECLINED' to match the Payment attempt status, and made the release-hold step say it does nothing when the hold has already expired.
- Clarified the late-success branch: Inventory creates a new hold and then converts it to sold stock, instead of implying the expired hold is still there.
- Changed the refund-failure text so it says retries continue until the provider accepts, and repeated failures raise an alert for a person. Previously 'alert on repeated failure' could be read as giving up.
- Clarified the Order status AWAITING_PAYMENT: it stays in that status until the provider's outcome is known, even after the hold expires.
- Replaced the claim that every node names a service with an accurate note: steps the brief does not assign are customer emails and the short-stock message, and these are listed under Open points.
- Added an Open points section for the unassigned customer emails and for what the customer sees while a late payment is pending.
- Split the reading notes into short bullets and spelled out each failure branch in plain words, and reworded the events and rules sections for a reader without project context. Diagram structure, node meanings and statuses are unchanged.
- Added a short plain-language list of the five parties (Cart, Inventory, Payment, Order, provider) at the top, so a reader who does not know the stack sees who is involved first.
- Explained HTTP versus events, and what a broker and an event are, in the opening section.
- Defined the terms 'all or nothing', 'refund key' and the status values PENDING, DECLINED, REFUNDED and PENDING_RETRY. The refund key is my own wording for the 'same refund key' the plan already relied on; the brief does not define it, so confirm that is the intent.
- Added a 'How to read the diagram' note explaining that rectangles are steps and diamonds are decisions, and that the text before the colon names the owning service.
- Corrected the note that said steps without a service were ones 'the brief does not assign'. The provider's decisions (J and S) are provider results, and the unassigned items are the customer messages in D and P, which are listed as open points.
- Clarified the failed-refund branch in the reading notes: retries continue, and a person is alerted if they keep failing.
- Clarified that an order never moves back to an earlier status, instead of the vague 'moves forward'.
- Added an open point: the diagram never shows how Payment records a successful charge.
- Kept the Mermaid diagram, the order statuses, the events and the rules unchanged in substance.

### Holes
- None.
