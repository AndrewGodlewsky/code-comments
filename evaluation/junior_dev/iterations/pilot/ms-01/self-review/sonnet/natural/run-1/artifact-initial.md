# Checkout across Cart, Inventory, Payment and Order

## How to read this

- There are four services: **Cart**, **Order**, **Inventory** and **Payment**. Each owns its own database. They talk only by HTTP calls (arrows labelled `HTTP`) or by events on the shared broker (labelled `event`).
- Only **Payment** talks to the payment provider.
- Order is the coordinator. It decides what happens next after each reply or event.
- Each box sits in the lane of the service that performs the step. Arrow labels say what triggers the step.
- The red-bordered boxes are the failure branches asked for: short stock, declined payment, late success, failed refund and duplicate webhook.

## Flowchart

```mermaid
flowchart TD
  subgraph CUST["Customer"]
    C1(["Presses Place order"])
    C2["Told which items are short. Cart unchanged"]
    C3["Told payment was declined. Cart unchanged, can retry"]
    C4["Email: order confirmed"]
    C5["Email: out of stock, full refund on its way"]
  end

  subgraph ORD["Order service - DB: orders, order_lines, outbox"]
    O1["Create order PENDING_STOCK. Copy lines and prices from the snapshot. Never changes afterwards"]
    O2["Status REJECTED_SHORT_STOCK. No payment requested"]
    O3["Status AWAITING_PAYMENT"]
    O4["Status PAYMENT_DECLINED"]
    O4b["Order asks Inventory to claim the stock"]
    O5["Status CONFIRMED. Publish OrderConfirmed"]
    O6["Status CANCELLED_OUT_OF_STOCK. Send email. Publish RefundRequested"]
    O7["Status REFUNDED"]
  end

  subgraph CART["Cart service - DB: carts, cart_lines"]
    K1["Return cart lines and prices as they are now"]
    K2["Empty the cart. Safe to repeat"]
  end

  subgraph INV["Inventory service - DB: stock, reservations, reservation_lines"]
    I1{"Every line in stock?"}
    I2["Reserve all lines in ONE transaction. Hold expires in 10 minutes. Publish StockReserved"]
    I3["Reserve nothing. Publish StockShort with short items"]
    I4["Release hold, stock back on sale. Safe to repeat"]
    I5{"Claim: hold still valid, OR lapsed but all lines still free?"}
    I6["Mark claimed, take stock off sale. Publish StockClaimed"]
    I7["Publish ClaimFailed. Stock was sold to someone else"]
    IT["Timer, every minute: unclaimed holds older than 10 min are expired, stock back on sale"]
  end

  subgraph PAY["Payment service - DB: payments, refunds, webhook_inbox, outbox"]
    P1["Save payment PENDING. Charge provider with Idempotency-Key = orderId"]
    P2["Webhook endpoint: verify signature"]
    P3{"Provider event id already in webhook_inbox?"}
    P4["Duplicate webhook: reply 200, do nothing"]
    P5{"Outcome?"}
    P6["Save SUCCEEDED. Publish PaymentSucceeded"]
    P7["Save DECLINED. Publish PaymentDeclined"]
    P8["Save refund REFUND_PENDING for the full amount. Call provider with Idempotency-Key = refund-orderId"]
    P9{"Provider accepts refund?"}
    P10["Save REFUND_FAILED with attempt count and next retry time. Alert ops after N attempts. Never delete"]
    P11["Save REFUNDED. Publish RefundCompleted"]
    PR["Timer, every minute: retry every refund in REFUND_PENDING or REFUND_FAILED that is due"]
  end

  subgraph PROV["Payment provider"]
    V1["Processes charge. Result after seconds, up to 30 min"]
  end

  C1 -->|"HTTP"| O1
  O1 -->|"HTTP GET cart"| K1
  K1 -->|"snapshot"| O1
  O1 -->|"HTTP reserve, key = orderId"| I1
  I1 -->|"no"| I3
  I1 -->|"yes"| I2
  I3 -->|"event StockShort"| O2
  O2 --> C2
  I2 -->|"event StockReserved"| O3
  O3 -->|"HTTP charge, key = orderId"| P1
  P1 -->|"HTTP"| V1
  V1 -->|"webhook, may repeat"| P2
  P2 --> P3
  P3 -->|"yes"| P4
  P3 -->|"no: insert id, then continue"| P5
  P5 -->|"declined"| P7
  P5 -->|"succeeded"| P6
  P7 -->|"event PaymentDeclined"| O4
  O4 --> C3
  O4 -->|"HTTP release"| I4
  P6 -->|"event PaymentSucceeded"| O4b
  O4b -->|"HTTP claim, key = orderId"| I5
  I5 -->|"yes"| I6
  I5 -->|"no: LATE SUCCESS"| I7
  I6 -->|"event StockClaimed"| O5
  O5 --> C4
  O5 -->|"event OrderConfirmed"| K2
  I7 -->|"event ClaimFailed"| O6
  O6 --> C5
  O6 -->|"event RefundRequested"| P8
  P8 --> P9
  P9 -->|"yes"| P11
  P9 -->|"no: error or timeout"| P10
  P10 --> PR
  PR --> P8
  P11 -->|"event RefundCompleted"| O7
  IT -.->|"same effect as release"| I4

  classDef fail stroke:#c62828,stroke-width:3px;
  class C2,C3,C5,O2,O4,O6,I3,I7,P4,P7,P10 fail;
```

## What the flow does, step by step

1. **Place order.** Order calls Cart over HTTP for the current lines and prices. It saves them as the order's own copy. After that, cart edits and price changes cannot touch the order. Order also drops a repeated Place order (double click) by using the cart id as a dedupe key.
2. **Reserve stock.** Order asks Inventory to reserve all the lines, using the order id as the key. Inventory checks every line and reserves all of them in one database transaction, or none. If any line is short, Inventory reports exactly which ones. Order marks the order rejected, and the customer sees the short items. No payment is requested and the cart is untouched.
3. **Request payment.** After `StockReserved`, Order asks Payment to charge. Payment saves a PENDING row (one row per order id, enforced by a unique constraint). It then calls the provider with the order id as the idempotency key. If Payment or Order retries this call, the provider returns the original charge instead of making a second one.
4. **Wait for the webhook.** The result can take up to 30 minutes. Payment does not poll or block. It waits for the provider's webhook.
5. **Webhook intake.** Payment verifies the signature. It then inserts the provider's event id into `webhook_inbox`, which has a unique constraint on that id. If the insert finds the id already there, Payment replies 200 and does nothing. This is the duplicate-webhook branch. The inbox insert and the outgoing event are written in one transaction (an outbox), so a crash cannot record the webhook without the event.
6. **Declined.** Payment publishes `PaymentDeclined`. Order marks the order `PAYMENT_DECLINED`, asks Inventory to release the hold, and tells the customer. The cart is untouched. A retry from the customer is a new Place order with a new order id and so a new idempotency key. A declined order id is never charged again.
7. **Succeeded.** Payment publishes `PaymentSucceeded`. Order asks Inventory to **claim** the stock for that order.
   - **Normal path.** The hold is still valid. Inventory marks it claimed. Order marks the order `CONFIRMED`, emails the customer, and publishes `OrderConfirmed`. Cart reacts to that event by emptying the cart. This is the only point where the cart is emptied.
   - **Late success.** The hold has lapsed. Inventory first checks whether every line is still free and, if so, re-takes it and the claim succeeds. Otherwise it answers `ClaimFailed`. Order marks the order `CANCELLED_OUT_OF_STOCK`, emails the customer, and publishes `RefundRequested`. Nothing is shipped, since we never ship partial orders. The cart stays as it was.
8. **Refund.** Payment saves a refund row for the full amount before it calls the provider, using the key `refund-<orderId>`. If the provider accepts it, Payment saves `REFUNDED` and publishes `RefundCompleted`, and Order marks the order `REFUNDED`. If the provider rejects it or times out, the row becomes `REFUND_FAILED` with an attempt count and next retry time. A timer retries every refund that is not `REFUNDED`. After N failed attempts it also alerts a person, but the retries continue. A refund is never deleted or given up on.
9. **Hold expiry.** A timer in Inventory expires unclaimed holds after 10 minutes and puts the stock back on sale. Expiry and claim both do a conditional update on the reservation row (`held` to `expired` or `claimed`), so exactly one of them wins when they race.

## What each service stores

| Service | Stores | Key constraints |
|---|---|---|
| Cart | Carts and cart lines (product, quantity, price) | Emptied only on `OrderConfirmed`. Emptying is safe to repeat |
| Order | Order, its copy of the lines and prices, status, outbox | Unique per checkout attempt. Lines and prices are never updated |
| Inventory | Stock levels, reservations (`held`, `claimed`, `expired`, `released`), reservation lines, `expires_at` | One reservation per order id. Reserve and claim are each a single transaction |
| Payment | Payment (status, amount, provider charge id), refunds (status, attempts, next retry), `webhook_inbox`, outbox | Unique payment per order id. Unique provider event id in the inbox |

## Order statuses

`PENDING_STOCK` leads to one of:

- `REJECTED_SHORT_STOCK` (end)
- `AWAITING_PAYMENT`, which leads to one of:
  - `PAYMENT_DECLINED` (end)
  - `CONFIRMED` (end)
  - `CANCELLED_OUT_OF_STOCK`, then `REFUNDED`

Every status change checks the current status first. A repeated or out-of-order event therefore changes nothing.

## Failure branches at a glance

| Case | Where it is caught | Result |
|---|---|---|
| Any line short | Inventory reserve | Nothing reserved, no payment, customer sees the short items, cart unchanged |
| Payment declined | Payment webhook, then Order | Hold released, customer told, cart unchanged, retry makes a new order |
| Success after hold lapsed and stock gone | Inventory claim | Full automatic refund, order cancelled as out of stock, customer emailed, cart unchanged |
| Refund fails at the provider | Payment refund row and retry timer | Status `REFUND_FAILED`, retried until it succeeds, ops alerted after N tries |
| Duplicate webhook | Payment `webhook_inbox` unique event id | Acknowledged, not processed again |
| Retried charge request | Provider idempotency key = order id | No second charge |
| Duplicate event or HTTP call between services | Status checks and keys on order id | No repeated effect |

## Assumptions to confirm

- Cart is the source of line prices. If a separate catalogue owns prices, the snapshot call changes but the design does not.
- No separate email service exists, so Order sends the emails. If there is a notification service, it would sit behind an event instead.
- The customer gets one email when the order is cancelled, and Order records the refund later as `REFUNDED`. If you want a second email when the refund lands, trigger it from `RefundCompleted`.
- The values for N (refund attempts before alerting) and the retry backoff are not decided yet.
- An order stuck in `AWAITING_PAYMENT` with no webhook long after 30 minutes is not covered by the stated requirements. I suggest a reconciliation job in Payment that asks the provider for the charge status once an order is older than about 35 minutes.
