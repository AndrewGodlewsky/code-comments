## Review of ms-01 (junior-v6, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a summary of how checkout works today (inside the monolith) and the main flow from start to finish, with the reason for the order of steps.
- Added terms for saga, snapshot, release, expiry, webhook, refund row, outbox relay, broker and the hold expired flag.
- Added a browser polling node and edge to the flowchart, and step 1 says the POST returns at once and the browser polls status (Q1).
- Step 1 now takes the Cart snapshot before inserting the order, so a failed snapshot creates no order (clarifies the diagram's order of calls).
- Step 3 now says what the charge request carries (order id and the amount from stored lines) and that the HTTP call returns once the provider accepts the request (Q3).
- Step 4 now covers signature failure (rejected, nothing written), finding the charge from the order id the provider sends back, and the duplicate check (Q4).
- Step 5 now says Order saves the payment outcome before claiming, and keeps the status AWAITING_PAYMENT until the claim is answered (Q2, Q7).
- Step 6 now states that the order status does not change on expiry and what the flag is for (Q5).
- Step 7 added: release and claim are retried with the same order id until answered, and the 10-minute expiry backstops a failed release (Q7).
- Step 9 added: RefundCompleted is recorded in the status history with no customer change (Q8).
- Added step 11 for recovery after an Order crash (Q2).
- Failure table rewritten with rows for snapshot failure, reserve failure, signature failure, release and claim failures, Order crash, broker outage and double-click.
- Rule 3 now says a failed checkout leaves the cart exactly as it was, which is a stated requirement that was missing from the rules.
- Stored state: Order now also stores pending release and claim calls and unclaimed payment outcomes, so retries survive a restart.
- Open questions: added 6 (browser update method), 7 (webhook order id and provider retries), 8 (PLACING order whose hold expired before recovery) and 9 (customer message on refund completion). Open questions 1 to 5 are unchanged.
- All numbers and rules from the brief and the first version are kept: 10-minute hold, 30-minute webhook window, 45-minute poll, statuses, idempotency keys, full refund, FAILED_NEEDS_ATTENTION, daily reconciliation, outbox and the six rules.
- Step 1: added that a background worker in Order runs the reserve step after the POST returns, and that the browser shows a placing state while the order is PLACING.
- Step 2: added that the reserve result comes back in the HTTP response, and what a repeated reserve call returns (the existing reservation, or a fresh stock check after a short answer).
- Step 3: added what happens when the provider call fails before it accepts the charge (retry with the same key, order stays AWAITING_PAYMENT, hold keeps running), and pointed to Open questions for where payment details are held and how soon recovery runs.
- Step 4: added that a charge is set only once, and a later conflicting result is logged and changes nothing.
- Step 5: added that a repeat success on a CONFIRMED or CANCELLED_OUT_OF_STOCK order changes nothing, and explained the saved payment outcome and why it is written before the claim.
- Step 10: added what Payment does when a poll says the charge is still pending (change nothing, poll again), so a pending charge is not treated as failed.
- Terms: added Saved payment outcome.
- Failure table: added a row for a provider call that fails before accepting the charge, and a row for a charge still pending after a poll.
- Open questions: added 10 (where payment details are held before the charge), 11 (recovery timing and a charge the provider never accepts), and 12 (the pending wait has no end).
- Step 1: added that the browser makes a new client request id per press of Place order, and that Order generates the order id at insert (Q16).
- Step 2: added that Inventory counts only HELD reservations with expires_at in the future as holding stock, so an expired hold does not block stock before the sweep (Q17). Without this, stock stayed blocked past 10 minutes.
- Step 3: replaced 'Payment retries with the same key' with the explicit rule: Payment answers Order with an error, Payment retries the provider call in the background with the same key, and Order does not resend (Q15).
- Step 5 (declined): the retry is a new press of Place order and gets a new order id, with the reason stated (Q16).
- Terms: Reservation and Claim now say the stock counts as held and the claim is accepted only while HELD and not past expires_at (Q17).
- Failure table: the provider-call-fails row now names the error answer to Order and the background retry in Payment (Q15). The double-click row now explains that a double-click is one press with one client request id (Q16).
- Flowchart: the reserve check label counts only HELD, unexpired holds (Q17). Added a retry self-loop on Call provider charge for a failure before acceptance (Q15). The ordering of the IN2 and IN3 edges was also changed to match the reserve result.
- Added a plain opening sentence on how checkout works today (inside the monolith) and a short plain-language main-flow paragraph before the terms.
- Added terms a newcomer needs: compensating step, place order, client request id, order id, payment provider, charge, webhook signature check, webhook log, consumer, final state, background worker, recovery job, polling, backoff, ops, reconciliation. Defined the existing terms in plainer words. Kept the terms list and dropped nothing from it.
- Moved the diagram to sit right after the terms, with its notes right after it. Dropped the 'How to read it' repetition of the diagram-wide notes into a shorter list. The Mermaid source is unchanged.
- Added to the diagram notes that the reserve call runs from a background worker in Order, answering the junior's question about what triggers it.
- Reordered the steps into the order they happen: the hold expiry (now step 4) can happen while waiting, the webhook (step 5) and the charge timeout with no webhook (step 6) follow, then the payment event (step 7). Previously the payment event came before the hold expiry.
- Step 1: made the browser's request, the worker handoff and the placing and polling states explicit in one place. Stated that a resent press returns the first order.
- Step 2: stated that the worker starts it and that the reserve result comes back in the HTTP response. Put the lost-response repeat rules next to it, and the recovery backstop.
- Step 3: stated that Order never calls the provider. Put the timeout and the before-accept failure paths in sub-bullets so each reads on its own. Replaced the 'Order does not resend' wording with the same meaning and kept it.
- Step 4: stated that the claim checks expires_at, so a late sweep cannot let an expired hold be claimed. Added that the claim decides the outcome.
- Step 5: moved the signature rule and the webhook log check into plain sentences. Kept the 'a later conflicting result is logged and changes nothing' rule.
- Step 6 (charge outcome unknown): kept the 45-minute poll and the rule that a pending charge is never treated as failed, now as its own step.
- Step 7 (payment event): kept the final-state ignore rule, the decline and retry rules (new press, new order id, no old key), and both claim outcomes. Changed 'the late success case' wording to name the late-success path, and cross-referenced it by name.
- Steps 8 to 11: release and claim retries, refund, refund completed, and crash recovery kept in full. Added that Order stores pending calls so restarts do not lose them.
- Failure table: all rows kept. Rewrote the 'Refund call fails' row to add 'A refund is never silently dropped' from the brief. Shortened the double-click row wording without losing the fact.
- Rules: kept all six rules. Rule 3 keeps the brief's wording about the cart staying exactly as it was. Rule 4 now says the key is stored before the call, using plain words and no duplicated detail.
- Open questions: all twelve kept. Removed the cross-reference codes (for example 'open question 6') so each question stands alone. Each question keeps its original content.
- Not added, noticed only: the design does not say whether REJECTED_SHORT_STOCK is a final state or whether a retry after a short-stock answer creates a new order id. This is a gap in the first version, not a choice the junior asked about, so it was not added to the file or the open questions.
- Cut: nothing from the first version's facts was removed. The repeated 'Stored state per service' and 'Failure branches' wording is kept as one table each, not two.

### Holes
- Q10: The charge request carries the payment details the customer entered. Where do those details live between Place order and the charge, and where does Order get them when the recovery job repeats the charge? (author: The design does not say where the customer's payment details are held between Place order and the charge, or how recovery repeats the charge without them. The brief does not set this. Added as open question 10.)
