## Review of ms-01 (junior, author sonnet, natural)

Rounds: 4. Ended: cap.

### What changed
- Added the outbox relay definition (in-service loop, polls unpublished rows, marks published_at, may duplicate) because Q2 showed it was undefined; removed Inventory's outbox since it publishes no events.
- Added a 'Why 10 and 30 minutes' note and a 'What the customer sees' section (202 plus polling plus email) for Q1 and Q6; O4 now says it replies 202.
- Added a 'When a step fails or a service crashes' table with an Order sweeper and idempotent reserve and claim, to cover crashes and timeouts at O2 to I1 and O6 to I6 (Q3, Q4).
- Added the PAID_CLAIMING Order status and set it at O6 so a stalled claim is recoverable.
- Specified the PaymentRequested payload (order id, customer, total, currency, payment method reference) and added currency to payments; flagged payment-details capture as open (Q5).
- Added Inventory stock counters (on_hand, reserved) and a claim rules table covering RESERVED, CLAIMED, EXPIRED and RELEASED (Q7).
- Replaced OrderCancelledOutOfStock with a general RefundRequested event, updated the flowchart, events table and text, and rewrote the not-AWAITING_PAYMENT assumption by status (Q8). Made refunds unique per order id.
- Added the checkout token column to orders, and listed the placeholder timing values as open.
- Added a note that all jobs, relays, sweepers and schedulers are timer loops inside the owning service, because several questions asked what runs them and where.
- Added a section on what the Place order request carries (customer id, cart id, checkout token, payment method reference) so Cart read and K1 know which cart.
- Added a section on the charge call and webhook: order id as reference, HMAC signature check, charge reply is acknowledgement only, retry and reconciliation when the provider never accepts (Q9, Q14, Q15); updated P1, P1a and P2 nodes and the PROV to P1R arrow label.
- Added expiry and release rules and the expiry job description, and made I3 and I4 act only when RESERVED, to prevent subtracting reserved twice (Q10, Q11).
- Fixed the refund inconsistency: provider answer to a refund is the HTTPS reply (diagram arrow now solid and labelled, RD label covers no answer); defined the refund scheduler; moved refund-by-webhook to an open question (Q12).
- Changed K1 to remove only the ordered lines, with OrderConfirmed carrying cart id and lines and a Cart applied_orders table for idempotency; flagged as a decision to confirm (Q13).
- Extended the payments table with payment method reference, attempt count, next attempt time and acknowledged flag; added Cart applied_orders; updated the events table.
- Added an open item about the provider's exact API, and listed the new interval and retry placeholders.
- Added a poll table to 'What the customer sees' and made Place order always return the order id, including the 'checking stock' 202 when Inventory is slow or unreachable (Q22).
- Added Inventory reserve rules table and the new REJECTED_TIMEOUT status (node O3T, edge, storage list, poll table, assumption) for a repeat reserve that finds an EXPIRED/RELEASED hold (Q16).
- Added 'PaymentFailed arriving when Order is not AWAITING_PAYMENT' handling to the assumptions (Q17).
- Added P7 node, edges and a payment status rules table covering success after DECLINED (refund row, alert ops), decline after SUCCEEDED and same-outcome repeats; P4 now updates status only if still REQUESTED (Q18, Q20).
- Stated that reconciliation writes no event id and relies on the P4 conditional status update (Q20).
- Added the case of a valid webhook with no payment row: no event id saved, reply 503, alert ops; added provider-retries-on-5xx to the open provider assumptions (Q19).
- K1 now inserts into applied_orders and subtracts in one transaction; OrderConfirmed carries the order id; storage table updated (Q21).
- Order storage now includes short items and REJECTED_TIMEOUT; PaymentSucceeded assumption list includes REJECTED_TIMEOUT; added the Place order wait for Inventory to the placeholder list.
- Added Place order failure case O1F (cart read fails, times out, or cart missing or empty): no order stored, reply 503 or 422, token not consumed, cart untouched. Updated the customer-sees list, flowchart (new node O1F, dotted edge from K0, edge to K2), happy path step 1, failure table, and assumptions. Fixes the previously wrong claim that Place order always returns an order id.
- Replaced the 'always returns the order id' wording with 'Only the last three replies come with an order id, because an order exists only after O2'.
- Added a 'The broker and event delivery' bullet explaining consumer handling: one local transaction, acknowledge only after commit, redeliver on failure, parked events alert ops.
- Added an open question for the broker product, push versus pull, redelivery limit and dead-letter handling, and added the Cart wait to the placeholder values list.
- Added an assumption note recording the O1F design decision and its alternative.

### Holes
- None.
