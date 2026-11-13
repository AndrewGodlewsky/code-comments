## Review of ms-01 (junior-v5, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a terms section that defines service, snapshot, checkout attempt id, reservation, claim, sweeper, idempotency key, webhook, broker, event, outbox, unique key and conditional update in plain words.
- Replaced the ten notes and the separate step list with nine numbered steps. Each step says what starts it, what it does, which data it keeps, and what happens when it fails.
- Stated that Place order's request stays open until the reservation answer and the charge's 202 arrive, not the webhook (Q1).
- Added a node and edge showing the customer's status poll after 202, and a step explaining how the customer learns the result (Q2).
- Stated what Order and Cart store on a short-stock rejection, and that the cart is unchanged (Q4).
- Stated that a failed release call is retried, and that the hold expires after 10 minutes anyway (Q5).
- Added a section stating which calls are synchronous HTTP and which are broker events (Q6).
- Added failure-table rows for a webhook that never arrives and a charge that is never accepted (Q7, Q8).
- Moved the unanswered questions into the open questions list: charge retry count and final order state, missing-webhook handling, late-success frequency, customer notification, and release retry length.
- Kept the plan's intent. No new locks, states, or mechanisms were added. The missing-webhook and charge-never-accepted paths are documented as open, not designed.
- Summary: reworded the main flow in plain steps. Fixed a contradiction: it said every failure is retried until it succeeds, but step 8 says ops is alerted when attempts run out. It now says a failed refund is retried, and if the retries run out ops is alerted and the refund stays open until it succeeds.
- Terms: added saga, on hand, reserved, available stock and refund key. Merged 'reservation' into 'hold' (one name for one thing). Removed the unclear 'refund suffix'. Defined conditional update and unique key in one plain line each.
- Summary and step 4: stated that Cart's Place order request stays open until Order gets the reservation answer and the provider's 202, or a short-stock answer, and does not wait for the webhook (answer to Q1). Added the open question that this depends on the charge retry count.
- Step 2 and step 3: stated that Order makes the reservation call right after creating the PLACING order (Q1). Added in step 3 what the customer sees on a short-stock answer, that the cart is unchanged, and that a new attempt creates a new order (Q4).
- Step 4: stated that the customer polls Order for status after the 202 (Q2). Stated what happens when the charge is never accepted (order stays PLACING, hold not released, lapses after 10 minutes) (Q8).
- Step 5: put the webhook rules in order, with the duplicate check first and the three writes in one transaction (Q7 context). Kept the webhook-never-arrives gap visible as open.
- Step 6: stated that the release is retried, that the hold expires on its own after 10 minutes, and that stock is therefore never lost for good (Q5).
- Step 8: stated why the order is cancelled (we do not keep money for an order we cannot fulfil; no partial orders), and that the refund row is never deleted. Kept the sequence of retries and ops alert.
- Step 9: added that a claim checks expires_at itself, so a lapsed hold cannot be claimed before the sweeper runs. This follows from the claim rule in step 7, and it was not stated before. Also stated the stock returns to sale at most about a minute after expiry.
- How the services talk: now states that HTTP is for calls that need an answer and broker events are for facts other services act on (answer to Q6). Merged the delivery rules into one bullet.
- Failure table: merged the two release rows and the two refund rows. Added the claim-call-failure row, marked open, because the brief and original did not say what happens. Added the outcome for short stock (REJECTED record kept).
- Open questions: added the claim-call failure and the Place order request duration. Rewrote the late-success frequency question to say why it matters (Q3, the answer is unknown). Merged the refund reconciliation questions. Removed the step codes (none used).
- Flowchart: reduced the node count and renamed the labels to match the text (hold, not reservation). Merged the sweeper step and the stock-freed label. Added the customer's status poll node (Q2) and the 'customer can retry' end node for the declined branch. Kept every failure branch the brief names: short stock, declined payment, late success after the hold lapsed, failed refund and duplicate webhooks. Added a note after the diagram listing the branches it does not draw.
- Length: the rewrite is roughly the same length as the original, not longer. Cut the repeated explanation of the refund and sweeper steps, and the repeated statements of the same rule across steps and the table.

### Holes
- Q3: The reservation holds for 10 minutes but the webhook can take up to 30. How often does the late-success refund path actually happen, and is that the normal outcome for slow payments rather than a rare edge case? (author: The document has no measure of how often webhooks run past the 10-minute hold. The brief says they usually take seconds. Late success is a designed path for any payment whose webhook arrives after the hold lapses, so it is not rare if slow webhooks are common. We do not know the frequency. Added to open questions.)
- Q8: The charge retry loop on timeout or 5xx: how many times, and what happens to the order if retries never succeed? Does the reservation get released? (author: The retry count is not set. Retries use the same key, so the provider cannot charge twice. The document does not say what the order becomes if the retries never succeed. The order stays PLACING, because no 202 arrives. This path does not release the reservation. The reservation lapses after 10 minutes and the sweeper frees the stock. The final order state is open.)
