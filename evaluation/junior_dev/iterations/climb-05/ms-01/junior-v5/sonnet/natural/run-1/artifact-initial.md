# Checkout across Cart, Inventory, Payment and Order

## How to read this

- Each box in the diagram is one step. The coloured lane around it is the service that performs it.
- Services never touch each other's databases. They talk in two ways:
  - **HTTP**, used only for the first call, where Order asks Cart for a snapshot.
  - **Events** on the shared broker, used for everything else. In the diagram, events are written in `CamelCase` on the arrows.
- Each service writes its database change and the event it publishes in the **same local transaction** (a transactional outbox). Consumers record the id of every event they handle (an inbox) and ignore repeats. This makes event delivery at-least-once without double effects.
- Order ids are created by the Order service. They are the key that ties together the reservation, the charge, the refund and the emails.

## Flowchart

```mermaid
flowchart TD
  START(["Customer presses Place order"])

  subgraph ORD["ORDER service - stores: orders, order_lines (snapshot of lines and prices), order status, outbox, inbox"]
    O1["1. Receive Place order.<br/>Ask Cart for the current lines and prices (HTTP)"]
    O2["2. Save order with the snapshot.<br/>Status PENDING_STOCK.<br/>Publish ReserveStock"]
    O3["Status REJECTED_OUT_OF_STOCK.<br/>Tell customer which items are short.<br/>No payment was requested"]
    O4["Status AWAITING_PAYMENT.<br/>Publish ChargeRequested"]
    O5["Status PAYMENT_DECLINED.<br/>Tell customer, who can try again"]
    O6["Status PAID.<br/>Publish ClaimStock"]
    O7["Status CONFIRMED.<br/>Email order confirmation.<br/>Publish OrderConfirmed"]
    O8["Status CANCELLED_OUT_OF_STOCK.<br/>Email customer: cancelled, full refund on its way.<br/>Publish RefundRequested for the full amount"]
    O9["Record refund as done on the order.<br/>Email customer: refund issued"]
  end

  subgraph CART["CART service - stores: carts, cart lines, current prices"]
    C1["Return lines and prices as they are now.<br/>Cart is not changed"]
    C2["Empty the cart.<br/>Only ever triggered by OrderConfirmed"]
  end

  subgraph INV["INVENTORY service - stores: stock levels, reservations (order id, lines, status, expires_at), inbox"]
    I1["3. In ONE database transaction, check every line"]
    I2{"Is every line in stock?"}
    I3["Reserve nothing.<br/>Publish StockShort with the list of short items"]
    I4["Save reservation HELD for the order.<br/>expires_at = now + 10 minutes.<br/>Publish StockReserved"]
    I5["Release the hold, stock goes back on sale.<br/>Does nothing if already released"]
    I6{"Claim: is the hold still HELD,<br/>or lapsed but all lines still free?"}
    I7["Reservation CLAIMED, stock decremented.<br/>Publish StockClaimed"]
    I8["Publish ClaimFailed.<br/>Stock was sold to someone else"]
    I9["TIMER every minute:<br/>HELD reservations past expires_at become EXPIRED.<br/>Stock goes back on sale.<br/>Order is not notified, because payment may still succeed"]
  end

  subgraph PAY["PAYMENT service - stores: payments (order id unique, amount, status), refunds (status, attempts), webhook inbox of provider event ids, outbox"]
    P1["4. Save payment PENDING for the order id.<br/>Call provider to charge.<br/>Idempotency key = order id.<br/>On timeout retry with the SAME key"]
    P2["Webhook arrives.<br/>Verify signature.<br/>Insert provider event id in inbox,<br/>in the same transaction as the update"]
    P3{"Event id already in inbox?"}
    P4["Duplicate: reply 200 and do nothing"]
    P5{"Outcome reported?"}
    P6["Payment DECLINED.<br/>Publish PaymentDeclined"]
    P7["Payment SUCCEEDED.<br/>Publish PaymentSucceeded"]
    P8["Save refund REFUND_PENDING.<br/>Call provider to refund the full amount.<br/>Idempotency key = refund + order id"]
    P9{"Provider accepted the refund?"}
    P10["Refund REFUNDED.<br/>Publish Refunded"]
    P11["Keep REFUND_PENDING and record the attempt.<br/>Retry with growing delay, never give up.<br/>After 5 failures raise an alert for a person"]
    P12["TIMER: no webhook 35 minutes after the charge?<br/>Ask provider for the charge status using the order id,<br/>then handle it as if a webhook arrived"]
  end

  PROV(["Payment provider<br/>(only Payment talks to it)"])

  START --> O1
  O1 -->|"HTTP get cart"| C1
  C1 -->|"lines and prices"| O2
  O2 -->|"ReserveStock"| I1
  I1 --> I2
  I2 -->|"No, any line short"| I3
  I3 -->|"StockShort"| O3
  I2 -->|"Yes, all lines"| I4
  I4 -->|"StockReserved"| O4
  I4 -.->|"starts 10 minute hold"| I9
  O4 -->|"ChargeRequested"| P1
  P1 -->|"charge request"| PROV
  P1 -.->|"arms"| P12

  PROV -->|"webhook: succeeded or declined, 2 seconds to 30 minutes, may repeat"| P2
  P12 -.-> P2
  P2 --> P3
  P3 -->|"Yes"| P4
  P3 -->|"No"| P5
  P5 -->|"Declined"| P6
  P5 -->|"Succeeded"| P7

  P6 -->|"PaymentDeclined"| O5
  P6 -->|"PaymentDeclined"| I5
  P7 -->|"PaymentSucceeded"| O6
  O6 -->|"ClaimStock"| I6
  I6 -->|"Yes"| I7
  I7 -->|"StockClaimed"| O7
  O7 -->|"OrderConfirmed"| C2
  I6 -->|"No, late success"| I8
  I8 -->|"ClaimFailed"| O8
  O8 -->|"RefundRequested"| P8
  P8 -->|"refund request"| PROV
  P8 --> P9
  P9 -->|"Yes"| P10
  P9 -->|"No, failed"| P11
  P11 -->|"retry"| P8
  P10 -->|"Refunded"| O9

  classDef fail fill:#fde2e2,stroke:#b42318,color:#000;
  classDef ok fill:#e0f4e3,stroke:#1a7f37,color:#000;
  classDef timer fill:#fff4cc,stroke:#9a6700,color:#000;
  class O3,O5,O8,I3,I8,P4,P6,P11 fail;
  class O7,C2,I7,P10,O9 ok;
  class I9,P12 timer;
```

Colour key: red marks a failure or no-op branch, green marks a success outcome, and yellow marks a timer.

## What each service owns

| Service | Stores | Does |
|---|---|---|
| **Cart** | Carts, lines, current prices | Gives Order a snapshot on request. Empties the cart on `OrderConfirmed` and at no other time. |
| **Order** | Orders, the line and price snapshot, status history | Starts and steers checkout. Decides the final outcome. Sends the customer emails. |
| **Inventory** | Stock levels, reservations with expiry time | Reserves all-or-nothing, expires holds, claims reserved stock, releases stock. |
| **Payment** | Payments, refunds, webhook inbox | Is the only caller of the provider. Charges, refunds, and de-duplicates webhooks. |

I assumed the Order service sends the emails through the existing mailer. That avoids a fifth service.

## Order statuses

`PENDING_STOCK` then `AWAITING_PAYMENT` then `PAID` then `CONFIRMED` is the happy path.

The other end states are:
- `REJECTED_OUT_OF_STOCK`: the reservation was short.
- `PAYMENT_DECLINED`: the provider declined the charge.
- `CANCELLED_OUT_OF_STOCK`: the payment succeeded but the stock was gone.

## Failure branches

| Case | What happens | What the customer sees | Cart |
|---|---|---|---|
| **Short stock** | Inventory reserves nothing and publishes `StockShort`. Order rejects the order. No `ChargeRequested` is ever sent, so Payment is never involved. | Told which items are short. | Unchanged |
| **Declined payment** | Payment publishes `PaymentDeclined`. Order marks the order failed. Inventory releases the hold. | Told the payment was declined. | Unchanged |
| **Late success (hold lapsed, stock sold)** | The timer expires the hold but Order does nothing, because payment may still succeed. When `PaymentSucceeded` arrives, Inventory cannot claim. It publishes `ClaimFailed`. Order cancels as out of stock, and Payment refunds the full amount. | Email: cancelled, full refund. | Unchanged |
| **Failed refund** | The refund stays `REFUND_PENDING` in Payment's database and is retried with the same idempotency key. It is never deleted, and it is retried even after the alert is raised. After 5 failures a person is alerted. | Order is already cancelled. The refund-issued email goes out only when the refund succeeds. | Unchanged |
| **Duplicate webhook** | The provider event id is inserted into the inbox, which has a unique constraint, in the same transaction as the status change. A repeat hits the constraint and gets a 200 reply with no further processing. | Nothing extra. | n/a |
| **Retried charge request** | Every charge carries the order id as the idempotency key, so the provider treats a retry as the same charge. | Nothing extra. | n/a |

## Design decisions to know about

1. **Hold versus payment delay.** The hold lasts 10 minutes and the webhook can take 30. The two are deliberately not linked. A payment that succeeds after the hold lapsed first tries to claim again. The claim still succeeds if all lines are still free. Only if any line is gone does the refund path run. This keeps refunds to the cases that need them.
2. **Claim versus expiry race.** The timer and the claim both change the same reservation row in Inventory's database, inside a transaction. Exactly one of them wins, so stock is never both released and claimed.
3. **No partial orders.** A claim covers all lines or none. A refund is always for the full amount.
4. **Stuck payments.** If no webhook arrives within 35 minutes of the charge (the 30 minute maximum plus a margin), Payment asks the provider for the charge status and handles the answer as if it were a webhook.
5. **Double-press of Place order.** Order allows one open checkout per cart. A second press returns the existing order.
6. **Cart edits during checkout.** Edits after Place order do not affect the order, which uses its snapshot. Open question: `OrderConfirmed` empties the whole cart, so any items added after Place order would be lost. If that is not wanted, Cart could remove only the snapshot's lines instead.
