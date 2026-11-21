## Review of ms-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a Terms section that defines service, HTTP call, event, outbox, snapshot, hold, claim, sweeper, idempotency key, webhook and ops queue, so a reader new to the stack can follow the document.
- Added a short Flow overview above the diagram that gives the main path in plain sentences.
- Shortened and clarified node labels in the flowchart (for example, 'Ask Inventory to reserve all lines (HTTP)' and 'Set hold to CLAIMED (stock is sold to this order)'), and wrote each decision as a question.
- Stated in the Payment refund node that a retry reuses the one refund row for the order, instead of saving a new row on every attempt, and that retries use the same key.
- Stated the Cart step as idempotent: C2 does nothing if this order already emptied the cart, which matches the 'idempotent per order id' requirement.
- Labelled the HTTP and event calls in the text so the reader can tell request-and-reply from fire-and-forget.
- Kept the diagram's structure, node IDs, service subgraphs, stores table, failure branch table, safety section and open decisions unchanged in substance.
- Added a short summary of the four possible endings at the top, so a reader knows what the diagram covers before reading it.
- Expanded the terms list: explained what a service, outbox, snapshot, claim, sweeper, idempotency key and webhook mean in plain words, and what a status word is.
- Added a step-by-step 'Flow in plain words' section that walks through the diagram in order, with each branch described once.
- Clarified the diagram's cart note (C2) so it says the cart is left alone when the order already emptied it.
- Moved the list of order statuses into the stores table so each status name is visible where the store is described.
- Reworded the table cells for failed refunds and the Cart and Payment store notes to say plainly what is kept and what changes.
- Reworded the 'Why the flow is safe' bullets to name the exact step or field each guarantee relies on.
- Kept the Mermaid flowchart, the failure branch table, and the open decisions list unchanged in substance.
- Added a plain-language opening that says what the document covers and lists the four possible endings with one line each.
- Added a 'Stock on hand', 'Release', 'Charge', 'Refund' and 'Webhook event id' to the terms list, and expanded 'Outbox', 'Claim' and 'Idempotency key' so a reader new to the stack can follow them without outside knowledge.
- Reworded the outbox definition to say what happens when the transaction fails, so the guarantee is explicit.
- Step 7 of the plain-words flow now says plainly that a repeat is acknowledged and ignored, and that a new event id is recorded before processing.
- Step 8 now says the refund retry uses the same key, matching the failed-refund row.
- The diagram now has an explicit node for recording a new webhook event id (P2a), which the text described but the diagram did not show. Its signature check is also a separate step (P2).
- Shortened several diagram labels (for example the subgraph titles and the I1 hold description) and removed the extra wording from the diagram nodes, keeping the step IDs that the tables refer to.
- Clarified the declined ending label to say the payment was declined and the stock released, instead of telling the customer, which the diagram does not model as a separate step.
- Kept the four endings, the stores table, the failure branches, the safety section and the open decisions unchanged in substance.

### Holes
- None.
