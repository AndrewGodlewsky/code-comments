# Checkout across Cart, Inventory, Payment and Order

This flowchart shows checkout from **Place order** to a confirmed order, a rejected order, a declined payment, or a refunded order. Each box is labelled with the service that owns it. The stores are listed under the diagram. Services talk over HTTP (request and reply) or through events on the message broker (fire and forget). Each service writes its state and its outgoing event in one database transaction (the outbox pattern), so a state change and its event cannot get out of step.

```mermaid
flowchart TD
  start(["Customer presses Place order"]) --> O1

  subgraph CART["Cart service (stores: cart lines)"]
    C1["C1 Return current lines and prices as a snapshot"]
    C2["C2 On OrderConfirmed, empty cart<br/>idempotent per order id"]
  end

  subgraph ORDER["Order service (stores: orders, price snapshot, status, outbox)"]
    O1["O1 Ask Cart for snapshot over HTTP"]
    O2["O2 Save order PENDING_STOCK with lines and prices"]
    O3["O3 Ask Inventory to reserve, key = order id"]
    O4["O4 Set REJECTED_SHORT_STOCK and tell customer which items are short"]
    O5["O5 Save AWAITING_PAYMENT and ask Payment to charge, key = order id"]
    O6["O6 On PaymentSucceeded, ask Inventory to claim the hold"]
    O7["O7 Set CONFIRMED, publish OrderConfirmed, email receipt"]
    O8["O8 Set CANCELLED_OUT_OF_STOCK, ask Payment for full refund, email customer"]
    O9["O9 Set PAYMENT_DECLINED and ask Inventory to release"]
  end

  subgraph INV["Inventory service (stores: stock on hand, reservations with status and expires_at)"]
    I1["I1 Reserve every line in one transaction<br/>hold = HELD, expires in 10 min"]
    I1d{"Every line in stock?"}
    I1n["Write nothing, return 409 with short items"]
    I2d{"Hold still HELD and not past expires_at?"}
    I2y["Mark CLAIMED, stock sold"]
    I2n["Refuse claim, hold has lapsed"]
    I3["Mark RELEASED, stock back on sale"]
    I4["Sweeper every minute: HELD and past expiry becomes RELEASED"]
  end

  subgraph PAY["Payment service (stores: charges keyed by order id, processed webhook event ids, refunds, outbox)"]
    P1["P1 Save charge PENDING, call provider with order id as idempotency key"]
    P2["P2 Webhook: verify signature, insert event id if new"]
    P2d{"Event id already processed?"}
    P3["Ack 200, change nothing"]
    P4d{"Provider outcome"}
    P5["Save SUCCEEDED only if still PENDING, publish PaymentSucceeded"]
    P6["Save DECLINED only if still PENDING, publish PaymentDeclined"]
    P7["Save refund row, call provider refund, key = refund plus order id"]
    P8d{"Provider accepted refund?"}
    P9["Save REFUNDED, publish RefundSucceeded"]
    P10["Retry with backoff; after limit mark REFUND_FAILED"]
  end

  subgraph EXT["Outside our services"]
    PROV["Payment provider: charge and refund APIs, sends webhooks"]
    OPS(["Ops team: REFUND_FAILED stays open until refunded"])
  end

  O1 --> C1 --> O2 --> O3 --> I1 --> I1d
  I1d -- "no" --> I1n --> O4 --> EndShort(["End: nothing reserved, nothing charged, cart unchanged"])
  I1d -- "yes" --> O5
  I1 -. "starts 10 min clock" .-> I4
  I4 --> I3
  O5 --> P1 --> PROV
  PROV -- "webhook, seconds to 30 min" --> P2
  PROV -. "same webhook delivered again" .-> P2
  P2 --> P2d
  P2d -- "yes" --> P3 --> EndDup(["End: duplicate ignored"])
  P2d -- "no" --> P4d
  P4d -- "declined" --> P6 --> O9 --> I3 --> EndDecl(["End: customer told declined, cart unchanged"])
  P4d -- "succeeded" --> P5 --> O6 --> I2d
  I2d -- "yes, stock still held" --> I2y --> O7 --> C2 --> EndOK(["End: order confirmed, cart emptied, receipt sent"])
  I2d -- "no, hold lapsed" --> I2n --> O8 --> P7 --> P8d
  P8d -- "yes" --> P9 --> EndRef(["End: full refund done, order cancelled, customer emailed"])
  P8d -- "no, provider error" --> P10
  P10 -- "retry" --> P7
  P10 -- "retry limit reached" --> OPS
```

## Stores by service

| Service | What it stores | Notes |
|---|---|---|
| Cart | Cart lines | Writes only when the cart is emptied after confirmation. Checkout never writes to it otherwise. |
| Order | Order header, status, the lines and prices as they were at Place order, outbox | The price snapshot is never updated after creation. |
| Inventory | Stock on hand, reservations (id, order id, lines, status HELD / CLAIMED / RELEASED, expires_at) | A reservation is one transaction across all its lines, so it is all-or-nothing. |
| Payment | Charges keyed by order id (status PENDING / SUCCEEDED / DECLINED), processed webhook event ids (unique), refunds (status, attempts), outbox | Only Payment talks to the provider. |

## Failure branches

| Branch | What happens | Cart | Money | Stock |
|---|---|---|---|---|
| Short stock | Inventory writes nothing and returns the short items. No payment is requested. Order records REJECTED_SHORT_STOCK. | Unchanged | None taken | Unchanged |
| Declined payment | Payment stores DECLINED. Order sets PAYMENT_DECLINED and asks Inventory to release the hold now, rather than waiting for the sweeper. | Unchanged | None taken | Released to sale |
| Late success after the hold lapsed | The hold claim is refused because the hold is no longer HELD or unexpired. Payment refunds the full amount. Order sets CANCELLED_OUT_OF_STOCK and emails the customer. We never ship a partial order. | Unchanged | Refunded in full | Not sold to this order |
| Failed refund | Each attempt is recorded and retried with the same idempotency key, so a retry cannot refund twice. After the retry limit, Payment sets REFUND_FAILED and the refund stays on the ops queue until it succeeds. It is never dropped. | Unchanged | Still held until refunded, and flagged | Not sold to this order |
| Duplicate webhook | The event id is already in processed_webhooks, so Payment acks and changes nothing. A repeat outcome also cannot flip a charge, because status changes only from PENDING. | Unchanged | Unaffected | Unaffected |
| Hold lapses while payment is pending | The sweeper releases the stock after 10 minutes. If the success webhook arrives later, the claim is refused and the late-success branch runs. | Unchanged | Refunded if it succeeded | Back on sale |

## Why the flow is safe

- **No payment without stock.** The payment request (O5) is made only after Inventory has created the hold (I1 yes).
- **No double charge.** Each charge uses the order id as the provider idempotency key. Payment stores one charge row per order id.
- **No double processing of webhooks.** Each webhook's event id is stored once. Each state change is conditional on PENDING, so a repeat cannot move a charge to a second outcome.
- **The claim checks the clock.** The hold claim checks expires_at at the moment of the claim, so a sweeper that runs late cannot let an expired hold be sold.
- **Cart changes only on confirmation.** Cart is read at Place order and written only when OrderConfirmed is consumed. Every failure branch leaves it untouched.

## Assumptions and open decisions

1. **Late success with stock still free.** The brief says to refund. This design refunds in every late-success case, even when nobody else bought the stock. An alternative is to try a fresh reservation first and confirm if it succeeds. Decide before build.
2. **Email sender.** The brief names no notification service, so this design has Order send the customer emails.
3. **Missing webhook.** The brief says a webhook can take up to 30 minutes. It does not say what happens if none arrives. Adding a provider status poll for charges still PENDING after about 35 minutes is recommended. It is not in the brief.
4. **Cart edits during checkout.** If the customer edits the cart while the order is pending, the confirmed order still uses the snapshot. Decide whether OrderConfirmed empties the whole cart or only the snapshot lines.
5. **Refund failure ownership.** The ops queue needs an owner and an alert threshold, and the customer needs an agreed message while a refund is stuck.