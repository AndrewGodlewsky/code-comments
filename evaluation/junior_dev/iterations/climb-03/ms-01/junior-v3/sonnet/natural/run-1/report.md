## Review of ms-01 (junior-v3, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a rule that events are stored with the status change and published by a relay, so a crash cannot strand an order
- Made Place order return immediately with the order id, with the page polling order status
- Added the FAILED status and the retry handling for a failing reserve call
- Added a one-open-order-per-cart rule so a double press returns the existing order
- Added retry-until-answered handling for a failing claim call, with the order staying PAID
- Added the REFUNDED final status set when RefundSucceeded arrives
- Spelled out the charge-call failure handling: retry timeouts and 5xx, treat outright rejection as declined, otherwise leave PENDING and alert
- Added an Open questions section for the source of payment details and unset retry limits
- Added one row to the failure table for reserve failure and one for claim failure
- How to read: listed the final statuses and said the page keeps polling, more slowly, while PENDING, RESERVED or PAID (Q15).
- Step 1: Order takes customer id and email from the login session, no cart data in the request; Cart failure sets FAILED; a 5-minute timer fails stale PENDING orders so they never block a new checkout (Q10, Q11, Q12).
- Diagram: added the customer email to the saved order, a Cart-call-fails edge to FAILED, a PENDING timer node, the release-once note, the provider reference in the charge, and the Payment timer that re-sends PENDING payments (Q11, Q12, Q13, Q14, Q16).
- Step 4: charge retries run from the stored PENDING row via a timer, and the order id is sent as the provider's reference (Q14, Q16).
- Step 5: said the webhook carries the order id reference that links it to the payment (Q14).
- Step 7: PAYMENT_FAILED is final, and release is tried once with the expiry timer as the fallback (Q13).
- Storage table and failure table: added customer id and email to Order, and rows for Cart failure or PENDING crash and for Payment crash mid-retry.
- Assumptions: added logged-in customer with email available, and provider reference support. Open questions: added the polling interval and the 5-minute PENDING limit.
- Added CANCELLED_OUT_OF_STOCK to the keep-polling statuses with its own page message (Q17).
- Added currency to the order snapshot and Payment's payment row, and made OrderReserved carry order id, total and currency (Q18).
- Moved the 35-minute status check from Assumptions into step 5, added a Payment timer node to the diagram, a failure-table row, and a note that the customer is blocked from a new checkout until then (Q19).
- Added handling for PaymentSucceeded arriving on a FAILED or PAYMENT_FAILED order: no claim, full refund, email; new diagram node, step 8 bullet and failure-table row (Q20).
- Replaced Cart-only idempotency wording with one general rule in How to read: act on an event only if the record is in the expected status; also reworded the matching assumption (Q21).
- Added an open question for the case where the 35-minute status check gives no result.
- Reordered into the newcomer layout: summary, terms, diagram, numbered steps, one failure table, open questions.
- Merged the 'How to read this' bullets into a single terms list, and merged the two event rules (never lost, repeats harmless) next to each other.
- Merged the Assumptions section into Open questions.
- Cut repeated explanations from the steps that the diagram and failure table already carried (stored-event note, retry detail in steps 2 and 4, the sentence about the status check in step 4).
- Folded the old step 9 and 10 wording and the cart-unchanged column into a single note above the failure table and trimmed the table to four columns.
- Removed cross-references such as 'see step 3' and 'see How to read this' where possible so steps stand alone; kept short step pointers only for the refusal and declined paths.
- Left the diagram unchanged.

### Holes
- Q5: Where do the card or payment method details come from when Payment sends the charge to the provider? The document never shows the customer supplying them. (author: The brief does not say how payment details reach Payment. A provider-issued token sent with Place order is likely but not decided. Added to Open questions.)
