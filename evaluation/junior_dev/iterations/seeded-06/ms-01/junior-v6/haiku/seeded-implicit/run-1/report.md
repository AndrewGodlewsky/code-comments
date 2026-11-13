## Review of ms-01 (junior-v6, author haiku, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Rewrote the diagram. Confirm order no longer leads to Refund. Refund now sits only on the late-success path, after the re-reserve fails. Added the short-stock, declined, late-success, failed-refund and duplicate-webhook branches, plus the 10-minute hold timer.
- Added a terms section that defines order id, snapshot, hold, claim, idempotency key, webhook, event id, broker, refund and the order statuses, because the junior had to be told what each one means.
- Added the brief's fixed facts that the first version dropped: per-service databases, HTTP and broker rules, the snapshot at Place order, all-or-nothing holds, the 10-minute hold, the 30-minute webhook delay, the order id as idempotency key, the full automatic refund with cancel and email, no partial orders, retried refunds, and the cart staying unchanged on any failure.
- Replaced the note 'Reservations expire after 10 min' with step 8, which says who releases the stock and that the order is not cancelled at expiry.
- Replaced the note 'Idempotency keys on provider calls' with the statement that the key is the order id and what it prevents, and added the refund key.
- Replaced the note 'Webhooks can be late or duplicated, so dedupe' with step 4: the event id is stored in Payment DB in the same transaction as the status change, and a repeat is ignored.
- Replaced 'Late payment when the stock is gone: re-reserve, otherwise refund and cancel' with step 7. It keeps the one re-reserve from the first version. The open questions flag that the brief only says refund and cancel.
- Replaced 'Cart cleared via event' with step 6: Order publishes OrderConfirmed after confirmation, and Cart empties itself only then.
- Added the 'When things fail' table covering every failure path the junior asked about and the brief names.
- Added open questions for the points the brief leaves undecided: webhook fields, broker durability, no-webhook timeout, charge cancel at lapse, the re-reserve rule, cart edits during checkout, and who owns open refunds.
- Length is well over 1.5 times the first version. This was needed so that no stated fact from the brief was cut, and the added length is terms, numbered steps and the failure table that the junior's questions asked for.
- Terms: added Valid hold and Payment outcome event; the Failed status now also covers a Payment that cannot be reached (Q10, Q13).
- Diagram: added the Payment unreachable branch to Failed, the Inventory unreachable retry at claim, the PaymentDeclined and PaymentSucceeded events, and the valid-hold check (Q9, Q10, Q12, Q13).
- Step 3: Order calls Payment over HTTP, the customer sees a still-waiting message, and a Payment that cannot be reached releases the holds and sets Failed (Q13).
- Step 4: Payment tells Order by broker events PaymentDeclined and PaymentSucceeded. The outcome is stored with the event id, and Payment publishes again from the stored outcome if the broker does not accept it (Q9).
- Step 5: a hold counts as valid only if it is Held and not past its expiry time. An expired hold that the timer has not yet marked goes to step 7 (Q10).
- Step 5: if Inventory cannot be reached at claim, Order keeps asking and makes no refund or cancel until Inventory answers (Q12).
- Step 7: now starts when a hold is not valid, matching step 5 (Q10).
- Step 8: if the release after a decline fails, nobody retries and the timer releases the hold within 10 minutes (Q14).
- Failure table: added rows for Payment unreachable, release after decline failing, outcome publish not accepted, and Inventory unreachable at claim. Updated the hold-expires row (Q9, Q12, Q13, Q14).
- Open questions: added the Payment charge retry limit and the Order claim retry limit, and widened the event-loss question to cover payment outcome events (Q9, Q11, Q12).
- Step 5: Order ignores a repeat PaymentSucceeded once the order is Confirmed or Cancelled, and a hold already Claimed for the order id counts as valid so a repeated claim changes nothing (Q16).
- Step 7: the refund is an HTTP call; Order acts once Payment stores the refund as Open and does not wait for the provider; if Payment is unreachable Order resends the same request and stays Awaiting payment until accepted; a repeated re-reserve for lines already held writes nothing (Q15, Q16).
- Step 9: Payment answers Order as soon as the Open refund record is stored, without waiting for the provider (Q15).
- Added step 10: retry after Rejected, Failed or Payment declined starts a new order id, snapshot, holds and charge key; the old order stays as a record (Q17).
- Diagram notes: added that an unaccepted refund request is resent with the order in Awaiting payment, and that a retry starts again at the first box with a new order id (Q15, Q17).
- Steps 2 and 3: the Failed paths now point to the retry in step 10 (Q17).
- Failure table: added a row for a refund request Payment does not accept, and a row for duplicate PaymentSucceeded or repeated claim or re-reserve. Changed the late-success refund row to say the order is cancelled once Payment accepts the refund (Q15, Q16).
- Open questions: the retry-limit question now also covers Order asking Payment to accept a refund (Q15).
- Step 3: added how the customer learns the outcome. The checkout page asks Order for the status by order id, because the brief names no push channel (answers Q18).
- Step 10: added that the customer sees Rejected, Failed or Payment declined on the checkout page and starts the retry by pressing Place order again, and that this plan sends no email for a decline (answers Q19).
- Open questions: added how often the page asks Order for status and when it stops, and whether a retry after Cancelled is allowed, since step 10 does not list Cancelled (answers Q18 and Q19).
- Reordered the document as the skill lays it out: one summary paragraph, the terms, the diagram with its notes, the numbered steps, the failure table, then the open questions.
- Rewrote the summary to say how checkout works today (inside the monolith) and to walk the main flow from start to finish, with the three rules that shape it.
- Added one-line definitions for the terms a newcomer needs: hold states (Held, Claimed, Released), charge and refund states, idempotency key (charge key and refund key), event id, broker, payment outcome events, OrderConfirmed, and each order status including Cancelled (out of stock).
- Rebuilt the Mermaid flowchart. It now shows the short-stock, declined, late-success, failed-refund and duplicate-webhook branches, plus the Payment-unreachable branch, the Inventory-unreachable branch at hold and claim, the repeated PaymentSucceeded check and the refund retry loop. Removed the old Confirm-to-Refund edge, so refund is reached only from the late-success path.
- Rewrote each step with its trigger, what it does, which database keeps its data, and what happens when it goes wrong. Steps refer to each other by name rather than by number.
- Merged duplicate text: the two Inventory-unreachable cases at claim and re-reserve share one failure row and one explanation, and the repeated-webhook and repeated-event rules are stated once each.
- Kept every requirement, limit, number and rule from the brief and the first version: the 10-minute hold, the 30-minute webhook delay, the order id as idempotency key, all-or-nothing holds, no partial orders, refunds never silently dropped, and the cart emptied only after confirmation. Kept all 18 failure rows and all 10 open questions. No design decision was changed.

### Holes
- Q4: What does the webhook contain, and how do you dedupe it? What identifier is stored, and where? (author: The brief does not give the webhook's fields, so the exact payload is unknown until the provider's API is read. Decided: Payment dedupes on the provider's event id, stored in Payment DB in the same transaction as the charge status change. A webhook whose event id is already stored is ignored and acknowledged.)
- Q11: How many times or for how long does Payment resend the charge? What happens to the order if it never gets through to the provider? (author: The brief and the plan do not say how many times, or for how long, Payment resends a charge request that fails or times out. If the charge never reaches the provider, no money moves and no webhook comes, so the order would wait in Awaiting payment as in the no-webhook case. This is now listed as an open question.)
