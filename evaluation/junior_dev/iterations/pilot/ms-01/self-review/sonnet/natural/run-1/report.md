## Review of ms-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Replaced 'lane' wording with 'grouped box' and said the group title lists the service's tables, and that the Customer group shows what the customer sees
- Added short definitions of idempotency key, webhook and outbox for readers new to the stack
- Noted that an unlabelled arrow means 'then' and marked the provider as external
- Fixed the contradiction in the double-click dedupe: the cart id key applies only while an earlier order for that cart is in progress, so a retry after a decline still works
- Step 2 now names the StockShort event and the REJECTED_SHORT_STOCK status; step 3 now says where AWAITING_PAYMENT is set
- Step 5 now says the status change is in the same transaction as the inbox insert and outgoing event
- Explained what 'claim' means and spelled out the late-success timing; named StockClaimed in the normal path
- Marked REFUNDED as an end state and clarified the notification-service assumption
- Chart: renamed O4b label to 'Ask Inventory to claim the stock' and changed 'HTTP GET cart' to 'HTTP get cart'; otherwise left the diagram unchanged
- Added a one-sentence summary of the whole flow at the top for readers new to the stack
- Added definitions of hold, claim and unique constraint, and clarified the outbox definition (database transaction, and which services have one)
- Explained that HTTP-request-then-event-reply pairs appear as two arrows
- Added an outbox to the Inventory service in the flowchart title and storage table, since Inventory publishes events
- Reworded the Order create node so the snapshot is saved before it is described as never changing
- Step 2 now states the success event (StockReserved) alongside StockShort
- Step 7 now says what the Inventory decision is, and the late-success wording is fixed so it refers to when the claim arrives rather than when payment succeeded
- Step 9 links an expired-hold claim back to the late-success check
- Added an assumption that events may be delivered more than once, explaining the status checks
- Added a definition of N to the terms list, since it was used in the flowchart and notes before being explained
- Stated up front that no service reads another's tables
- Clarified that Order records each decision as the order's status
- Reworded the HTTP-then-event bullet to say it more directly
- Step 1 now names the initial status PENDING_STOCK
- Step 7 wording tightened ("takes one of two paths")
- Added short plain-language glosses for PENDING_STOCK and AWAITING_PAYMENT in the statuses section
- Flowchart, tables and assumptions left unchanged

### Holes
- None.
