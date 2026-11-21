## Review of ms-01 (junior-v2, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- O1 text and chart: Order is created only after Cart answers; added Cart-unreachable edge to the cart-untouched node; new failure-table row.
- Added a 'What the customer sees' bullet: order id returned at once, page polls status, emails sent.
- D2 and rules: a RELEASED hold can never be claimed; late-claim wording changed from 'lapsed' to 'EXPIRED' for consistency.
- Rule 3 now defines available stock and the claim decrement; I6 says the stock level goes down.
- P9, D6 edge and the failed-refund row: attempt count, next retry time, retry when due, and what the customer sees meanwhile.
- New rule 7: Order checks current status before applying any event, with the allowed statuses; old rule 7 became rule 8, spelling out its scope, the direct RefundRequested and the CONFIRMED duplicate case.
- Choices: merged 'No webhook' with the outright charge failure case and stated that only final outcomes go to Order; added an Open questions line on non-final pending webhooks.
- Payment storage row: refunds are one per order.
- Merged the two outbox/inbox sub-bullets in 'How to read this' into one bullet.
- Removed the Cart column from the failure table and replaced it with one line saying the cart is untouched in every case until rule 5.
- Merged the 'Cart clearing' choice into rule 5 (removes only snapshot lines) and dropped it from Choices to confirm.
- Removed the repeated 'emptied only when it receives OrderConfirmed' from the Cart row of the stores table, since rule 5 says it.
- Shortened the declined-payment, duplicate-webhook, failed-refund and rule 2/3 wording to remove repeated explanations.
- Trimmed the Choices to confirm wording (late claim, no webhook); open questions kept together at the end. The flowchart is unchanged.

### Holes
- None.
