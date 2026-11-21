## Review of ms-01 (junior-v4, author sonnet, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Rewrote the flowchart so each node names the service, trigger and stored data, and added the short-stock, declined, claim-fail and refund branches.
- Fixed the arrows: Confirm no longer leads to Refund; the claim step now splits into confirm or cancel and refund.
- Added a one-paragraph summary and a terms list stating what each service stores.
- Added a step and failure table, and a note that Inventory alone owns the 10-minute timer.
- Named the dedupe key (provider event id in Payment DB) and the refund retry rule (row saved first, retried until success).
- Added open questions for webhook authentication, email sending, outbox for events and retry timing.
- Added payment token to Terms, step 1 and step 3 and the diagram, so card details never reach our services (Q10).
- Step 3 now handles provider or Payment failure by repeating the call, then PAYMENT_FAILED and release after a limit; a late success is refunded (Q11).
- Step 4 now says Payment asks the provider for status if no webhook arrives after 30 minutes; added as an open question (Q12).
- Step 5 says how Order finds the order and acts on events by status, ignoring repeats (Q13, Q15).
- Added a Claim paragraph and a Terms line explaining what claim changes and how free stock is decided (Q14).
- Step 1 row states a retry after a decline is a new order with a new id (Q16).
- Changed the refund order: Order asks Payment to refund first, then sets CANCELLED_OUT_OF_STOCK and emails, so a crash cannot drop the refund; refund requests are idempotent by order id (Q17).
- Added customer notice line and extra open questions (duplicate email, charge try count, status lookup).
- Step 3 row and diagram node 3: Place order returns after the charge is handed over, with order id and AWAITING_PAYMENT, so the customer sees a status page rather than a held request.
- Step 1 row: orders still PENDING after 10 minutes are set to FAILED by a periodic check in Order, so a crash before reserving does not leave an order stuck.
- Step 3 row: Order itself repeats the charge call from a periodic check for orders with no payment id, and counts tries.
- Step 8 row and Customer notice: Payment answers when the refund row is saved; Order sets CANCELLED_OUT_OF_STOCK then; the email says the refund is on its way.
- Terms: added Release, saying what it does to the reservation and counts and that repeats are harmless.
- Step 5 row: a late success for an order already PAYMENT_FAILED is refunded in full, the status stays PAYMENT_FAILED, and the customer is emailed.
- Step 4 diagram node: Payment now checks the signature, publishes the event, then stores the event id and replies 200; an already-stored id gets a 200 and no publish. This closes the gap where a crash between storing the id and publishing lost the event.
- Step 4 table row: added the publish, store, reply order, the crash case (provider redelivers, duplicate event is harmless because Order only acts on AWAITING_PAYMENT), and that a publish failure returns an error so the provider retries.
- Shortened Reservation, Claim and Release term definitions and removed repeated phrasing.
- Trimmed table wording in steps 1, 3, 4, 5 and 8 into shorter sentences without dropping any failure case.
- Renamed the trailing claim paragraph to 'How Inventory handles a claim' and tightened it; merged nothing that changes behaviour.
- Shortened the outbox open question and removed duplicated explanation of the Place-order response in step 3.
- Kept the diagram, terms-first layout and all failure branches unchanged.

### Holes
- Q5: What does the "Payment webhook" contain, and which service receives it? How is it checked as genuine? (author: The webhook carries the provider event id, the order id (payment reference) and the outcome, and Payment receives it. The brief does not say how it is authenticated; I assume the provider's signature with a shared secret and listed it under open questions.)
- Q12: If the webhook never arrives, what happens to the order, the reservation and the customer? Does anything check on the payment? (author: The brief does not say. My proposal is that Payment asks the provider for the payment's status once 30 minutes (the stated maximum) have passed without a webhook, and handles the answer like a webhook. The reservation lapses meanwhile and the customer sees awaiting payment. I do not know whether the provider offers a status lookup, so it is listed under open questions. Added to the step 4 row.)
