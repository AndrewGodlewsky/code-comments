## Review of ms-01 (junior-v7, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Defined the outbox relay (background loop, marks sent after broker confirms, keeps retrying if the broker is down).
- Added a line on what the customer sees while awaiting payment.
- Step table now sets PAID before the claim call (new step 5), and notes that reserve and claim are keyed by order id so they can be repeated.
- Added the webhook explanation (HTTP endpoint on Payment, provider reference maps to order id, processed list is a unique table of event ids).
- Added failure rows for reserve timeout (retry, then FAILED), charge timeout (retry with same key, then FAILED payment and PaymentDeclined) and claim timeout (stay PAID, retry until expiry).
- Declined row now says PAYMENT_DECLINED is final and a retry is a new order from the intact cart.
- Refund failure row now says Order stays CANCELLED_OUT_OF_STOCK until RefundCompleted, then marks REFUNDED and emails.
- Added FAILED to the Order statuses, and statuses to Payment's stored data.
- Added an Open questions section (provider webhook redelivery, how the status page refreshes) and added retry counts to the decisions to check.
- Added a failure row for an Order crash mid-retry: a minute-by-minute recovery loop resumes stuck PLACED or PAID orders (needed so paid orders are not stranded).
- Added status CANCELLED_LATE_PAYMENT to Order's stored statuses and defined the out-of-order success path (refund, emails, REFUNDED) in the decisions list.
- Mentioned CANCELLED_LATE_PAYMENT in the refund-failure row so it matches.
- Step 3 now says the charge carries order id, amount and a payment-method reference.
- Added an open question on where card details come from.
- Step 1 and the Order storage row: the order now saves the cart id, so Cart knows which cart to empty (Q19).
- Step 7: OrderConfirmed carries the order id and cart id (Q19).
- Open questions: added the question of cart edits after Place order, which currently get emptied too (Q19).
- Intro: stated that every 'tell the customer' means the page status plus an email from Order (Q16).
- Step 3: AWAITING_PAYMENT and ChargeRequested are saved together in one transaction (Q13).
- Step 2: a repeated reserve returns the hold already made (Q13).
- Crash row: covers a crash between the reserve reply and saving AWAITING_PAYMENT (Q13).
- Step 4: a success webhook for a payment saved as FAILED is stored as SUCCEEDED and published (Q14).
- Step 6 and the late-payment decision: nothing extends the hold, and any payment after 10 minutes is refunded even if stock is unsold (Q15).
- Declined row: Inventory releases only a HELD hold and ignores CLAIMED, EXPIRED or missing (Q17).
- Late success row: Order does not touch the already lapsed hold (Q18).
- Merged the intro and the two event rules into a three-sentence summary plus a terms list; the outbox relay, idempotent consumers, hold, webhook, idempotency key and 'tell the customer' are now defined once in one line each.
- Moved 'what the customer sees' into the terms (tell the customer) instead of a separate paragraph.
- Kept the flowchart unchanged; shortened the note after it to one line.
- Step table now carries only happy-path steps plus a 'data it keeps' column; this replaced the separate 'what each service stores' table. Failure handling moved out of the steps into one failure table, so nothing is told twice.
- Merged the 'Cart' column of the failure table into one sentence above it (cart unchanged), noting no exceptions.
- Merged the separate late-success and out-of-order text: out-of-order success is now its own failure row; the decisions section no longer repeats it.
- Folded the order, hold and payment status lists into one short line after the failure table.
- Cut the repeated explanations of the retry-safe keys from several places; they appear in the steps and the terms once.
- Merged the retry-count notes into one 'numbers and owners needed' bullet.
- Left out details nothing needed yet: exact retry counts and intervals, polling versus push (kept as open question).
- Kept all brief facts: 10 minute hold, 30 minute webhook delay, all-or-nothing reserve, order id idempotency key, duplicate webhook handling, full automatic refund, no partial orders, refunds never dropped, cart emptied only on confirmation, each service owns its database.

### Holes
- Q5: What exactly is the 'processed list' and the 'webhook' endpoint? Who calls it, how does Payment know which order a webhook belongs to, and what happens if our service is down when the provider sends it? (author: The webhook is an HTTP endpoint on Payment that the provider calls. The provider's message carries its payment reference, which Payment maps to the order id stored in the payment row. The processed list is a table of provider event ids with a unique constraint. What happens if Payment is down depends on the provider's redelivery policy, which I do not know; I listed it under open questions.)
- Q12: Does the Payment service charge the provider with only the order id and amount from the event, or does it need anything else, such as payment details from the customer? Where do the customer's card details come from? (author: Not known. The brief does not say how card details are collected. I assume the provider collects them (hosted form or token) and Payment sends only the order id, amount and a payment-method reference, so card data never touches our services. I added this to the charge step and to the open questions for confirmation.)
