## Review of ms-01 (junior-v1, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Stock counts: I2 now adds to a reserved count and leaves stock on hand unchanged; SW and D2 subtract the reserved count; K3 lowers stock on hand and the reserved count on claim. Added a Stock counts design rule (Q5).
- Added a How the services talk section: solid arrows are HTTP or synchronous; events go through each outbox and a relay onto the broker; the customer does not need to stay on the page while Pending (Q1, Q2).
- P3 no edge labelled as the synchronous HTTP reply to Order, so the path to D1 is explicit (Q3).
- Claim retries design rule added: same claim resent, idempotent 200 on repeat, not held on a lapsed hold, order stays Awaiting payment meanwhile (Q4).
- Outbox rule now says a relay publishes from the outbox table to the broker (Q2).
- Refund results: L7 and L10 publish RefundSucceeded and RefundOpen; ownership table and design rules say Order records refund status while staying Cancelled (Q7).
- K6 now says the customer sees confirmation on the order page; late-success branch says the order stays Cancelled with refund status recorded separately (Q6, Q7).
- Open question 2 reworded: removed the undefined provider lookup from the flow and asked whether to build a timeout lookup (Q8).
- Merged the O4 and O5 steps into one: Order sets status Awaiting payment before asking Payment to charge, so a lost reply leaves a visible state. Removed the Stock reserved status and the O5 node. (Q10)
- Place order (O1) returns the cart's open order when one exists, instead of creating a second order. Added the One open order per cart design rule and the open-order key in the ownership table. (Q11)
- Lost-replies failure branch added: reserve is repeated with the same order id and Inventory keeps one reservation per order id; charge is repeated with the same key. (Q9, Q10)
- Webhook label W1 now names the charge id and order id. Added the Webhook matching design rule. (Q12)
- K1 and the Consumers design rule: Order acts on ChargeSucceeded or ChargeDeclined only while Awaiting payment, and skips otherwise. (Q12)
- Ownership table: Order, Inventory and Payment rows now state one open order per cart, one reservation per order id and one charge per order id. (Q9, Q11, Q12)
- Open question 3 now sweeps orders in Placed or Awaiting payment, instead of Stock reserved, to match the merged status.

### Holes
- Q8: What is the 'provider lookup' mentioned in open question 2, and who triggers it? Is it part of the flow today or not yet built? (author: The document does not define a provider lookup. It is not in the flow, and no service or trigger is designed for it. I removed the phrase from the file's flow and reworded open question 2 to ask whether Payment should look up the provider on a timeout. I do not know whether that is wanted.)
