## Review of ms-01 (junior-v7, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Cart now creates the order id at Place order and sends it on every call, so a lost reply can be retried with the same id. Previously Order created the id in O1, so there was no safe retry key.
- Defined stock availability: on_hand minus HELD holds. on_hand is decremented only at commit, not at reserve.
- Payment's reply to Order means the charge was accepted or stored as pending, not the provider's outcome. Added this reply arrow and the 'payment in progress' node (CP) to Cart.
- The outbox is explained in the terms. The flowchart now routes all events through an explicit message broker node.
- PaymentDeclined is published by Payment and consumed by both Order and Cart. Previously Order forwarded the decline to Cart. This removes a hop and lets Cart show the decline without waiting for Order.
- Cart keeps a checkouts row per order id, separate from the cart lines, so it can show the checkout result without changing the cart.
- The commit in step 8 applies to all of the order's holds in one transaction, and it fails if any hold has lapsed.
- The late-success branch now says explicitly that the commit fails even when no other customer bought the stock, because the hold has lapsed.
- A retry after a decline is defined as a new order with a new hold and charge.
- Refund step now names its stored fields and its retry and alert behaviour in one place. The retry and alert rule is kept as stated.
- Restructured for a newcomer: summary, terms, flowchart, numbered steps, failure table, storage, open questions. The separate steps table was removed because it repeated the flowchart; its facts moved into the numbered steps.
- Added open questions for the points the brief does not settle: how long Payment retries an unsent charge, how long Order waits for Inventory, and whether to re-reserve stock that is still free after a lapsed hold.
- Kept every stated requirement from the brief and the first version, including the 10-minute hold, the 30-minute webhook window, duplicate webhooks, full refund on late success, no partial shipments, refunds never dropped, and the cart emptied only on OrderConfirmed.
- Step 4: the charge call now also sends the order id as the charge reference, the provider_ref is stored when the provider accepts, and a scheduled Payment job resends charges that have no provider_ref (answers Q9 and Q14).
- Step 6: the webhook names the order id, and Payment finds the charge by order id rather than provider_ref, since the webhook can arrive before provider_ref is stored (Q9).
- Step 9 and the flowchart: the refund request to Payment is an HTTP call that Payment answers once the refund row is stored as OPEN. Order retries it safely because the refund row is unique on order id (Q10).
- Step 9, the flowchart and Cart storage: Order publishes OrderCancelled on CANCELLED_OUT_OF_STOCK, and Cart marks its checkouts row CANCELLED_OUT_OF_STOCK, so the customer is not left seeing payment in progress after a late success (Q11). This adds one event to the plan.
- Step 8 and the flowchart C2 node: Cart sets its checkouts row to CONFIRMED on OrderConfirmed, and the customer sees the confirmation the next time they view the cart (Q12).
- Steps 7 and 8, and the failure table: Order acknowledges PaymentSucceeded and PaymentDeclined only after Inventory replies, so the broker resends them if the call fails. The commit-lost and release-failed rows are merged into one row (Q13 and Q15).
- Step 7, the flowchart release label and the failure table: the release to Inventory is an HTTP call, and releasing an EXPIRED hold changes no stock (Q15).
- Terms: added Provider event id, Provider reference (provider_ref) and Acknowledge, because the rewritten steps use them.
- Step 2: states that on_hand is not reduced at reserve time, which was already in the answers but missing from the steps.
- Rewrote the whole document once for a newcomer, as step 6 of the junior-dev skill asks. Every requirement, limit, number and rule from the brief and the first version was checked and kept: service-owned databases, HTTP and broker use, the frozen order snapshot, reserve-before-pay, all-or-nothing reservation, the 10-minute hold, order id as the idempotency key, the 30-minute and repeated webhook, the late-success refund and email, refund retries that are never dropped, and the cart rule.
- Added a plain summary that says how checkout works today (inside the monolith) before the new flow.
- Added terms a newcomer needs: SKU, cart snapshot, HTTP call, on_hand, hold, commit, release, provider reference, webhook, idempotency key, broker, acknowledge, outbox, scheduled job and unique constraint. Each is one line. Left out everyday terms such as transaction.
- Added the availability rule from the junior's question: on_hand minus HELD holds, with on_hand reduced only at commit.
- Added to step 2 the order fields Order stores and the Inventory tables, moved from the separate storage list. Each service's data is now named in the step that writes it, and the separate list is cut.
- Step 4 now says Payment sends the order id as the charge reference, and explains how a charge with no provider_ref is resent while one with a provider_ref is left for the webhook.
- Step 6 now says the webhook is matched to the charge by order id, not provider_ref, because the webhook can arrive first.
- Step 7 now says the release is an HTTP call, and that an already expired hold changes no stock.
- Step 8 now says a commit is sent over HTTP, and that the lapsed-hold failure happens even when no one else bought the stock.
- Step 9 now says Order waits for Payment's reply (refund stored OPEN) before waiting for RefundCompleted, and that Cart shows the cancellation so the customer is not left at payment in progress.
- Step 1 now says the checkouts row is kept apart from the cart lines, and Cart empties only on OrderConfirmed.
- Diagram: node labels now use the step numbers from the text instead of codes such as C1 or O4, so the two can be matched. Added the Payment refund call to the provider, the refund reply to Order, and the broker on every event arrow. Cart's declined and cancelled boxes now receive events through the broker.
- Cut repetition: the separate storage list, the duplicated ignore-PaymentSucceeded rule (kept only in the failure table), the acknowledge rule (kept only in the failure table), the third flowchart note about the cart (kept only in the failure table), and the separate assumptions list (merged into the open questions).
- Failure handling is now one table. Added rows for the cart rule on any failed checkout and for the consumers' processed-event tables.
- Open questions: kept all brief-derived gaps. Added the broker-redelivery assumption, the unknown charge-retry limit, and the unknown wait for Inventory, which the junior raised. The claim point is named explicitly.
- Not changed: the design itself. No mechanism was added beyond the first version, and the flow is the same apart from the reply and event edges the junior's answers already decided.

### Holes
- None.
