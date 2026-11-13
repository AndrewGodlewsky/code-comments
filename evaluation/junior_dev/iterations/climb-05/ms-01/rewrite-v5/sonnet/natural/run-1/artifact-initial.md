# Checkout design: Cart, Inventory, Payment, Order

## How to read this

- **Solid arrows** are synchronous HTTP calls. **Dotted arrows** are events on the shared broker.
- **Red nodes** are failure branches. The **green nodes** are the happy ending.
- Each box sits in the lane of the one service that does it. Each service writes only to its own database.
- Order is the coordinator (an orchestrated saga). It decides the next step after each reply or event.
- Every state change that also emits an event is written in one local transaction together with an **outbox** row. A relay publishes the outbox to the broker. Delivery is at-least-once, so every consumer ignores message ids it has already processed.

```mermaid
flowchart TD
  CUST(["Customer presses Place order"])
  PROV(["Payment provider - external"])

  subgraph ORD["ORDER service"]
    O1["O1 Receive Place order<br/>ask Cart for a snapshot"]
    O2["O2 Create order PLACED<br/>store lines and prices as of now"]
    O3["O3 Mark REJECTED_OUT_OF_STOCK<br/>tell customer which items are short"]
    O4["O4 Mark AWAITING_PAYMENT<br/>tell customer: processing"]
    O5["O5 Mark PAYMENT_DECLINED<br/>email customer, cart untouched"]
    O6["O6 On PaymentSucceeded:<br/>ask Inventory to claim stock"]
    O7["O7 Mark CONFIRMED<br/>email confirmation"]
    O8["O8 Mark CANCELLED_OUT_OF_STOCK<br/>email: cancelled, full refund coming<br/>request refund"]
    O9["O9 Record refund status on order<br/>REFUNDED or REFUND_STUCK"]
  end

  subgraph CART["CART service"]
    K1["K1 Return snapshot of lines and prices<br/>cart left unchanged"]
    K2["K2 Empty the cart"]
  end

  subgraph INV["INVENTORY service"]
    I1{"I1 Every line in stock?"}
    I2["I2 Reserve ALL lines in one transaction<br/>HELD, expires_at = now + 10 min"]
    I3["I3 Reserve nothing<br/>return list of short items"]
    I4{"I4 Claim: hold still HELD,<br/>or lapsed but all lines still free?"}
    I5["I5 Mark CLAIMED<br/>stock permanently deducted"]
    I6["I6 Refuse claim<br/>stock was sold to someone else"]
    I7["I7 Release hold<br/>stock back on sale"]
    I8["I8 Timer every minute:<br/>holds past expires_at become EXPIRED<br/>stock back on sale"]
  end

  subgraph PAY["PAYMENT service"]
    P1["P1 Store payment PENDING<br/>charge provider, idempotency key = order id"]
    P2{"P2 Webhook event id<br/>already processed?"}
    P3["P3 Ignore duplicate<br/>reply 200"]
    P4{"P4 Provider outcome?"}
    P5["P5 Mark DECLINED"]
    P6["P6 Mark SUCCEEDED"]
    P7["P7 Store refund REQUESTED for full amount<br/>call provider refund<br/>key = refund + order id"]
    P8{"P8 Provider accepted refund?"}
    P9["P9 Mark REFUNDED"]
    P10["P10 Keep REFUND_PENDING<br/>schedule retry with backoff"]
    P11["P11 After N tries mark REFUND_STUCK<br/>alert on-call, keep retrying"]
  end

  CUST --> O1
  O1 -->|"HTTP get snapshot"| K1
  K1 -->|"lines and prices"| O2
  O2 -->|"HTTP reserve stock for order id"| I1
  I1 -->|"no, some line short"| I3
  I3 -->|"short items"| O3
  I1 -->|"yes"| I2
  I2 -->|"reserved"| O4
  O4 -->|"HTTP create charge"| P1
  P1 -->|"charge request"| PROV
  I2 -.->|"hold ages"| I8

  PROV -->|"webhook, may repeat, up to 30 min"| P2
  P2 -->|"yes"| P3
  P2 -->|"no, record id and continue"| P4
  P4 -->|"declined"| P5
  P4 -->|"succeeded"| P6

  P5 -.->|"event PaymentDeclined"| O5
  O5 -->|"HTTP release order id"| I7

  P6 -.->|"event PaymentSucceeded"| O6
  O6 -->|"HTTP claim order id"| I4
  I4 -->|"yes"| I5
  I5 -->|"claimed"| O7
  O7 -.->|"event OrderConfirmed"| K2

  I4 -->|"no"| I6
  I6 -->|"refused"| O8
  O8 -.->|"event RefundRequested"| P7
  P7 -->|"refund request"| PROV
  PROV -->|"refund result"| P8
  P8 -->|"yes"| P9
  P8 -->|"no or timeout"| P10
  P10 -->|"retry due"| P7
  P10 -->|"after N tries"| P11
  P11 -->|"retry due"| P7
  P9 -.->|"event RefundCompleted"| O9
  P11 -.->|"event RefundStuck"| O9

  classDef fail fill:#fde2e2,stroke:#b42318,color:#3b0a07;
  classDef ok fill:#dcf5e3,stroke:#1a7f37,color:#06260f;
  class O3,O5,O8,I3,I6,P5,P10,P11,P3 fail;
  class O7,K2,P9 ok;
```

## Step by step

| Step | Service | Triggered by | What happens |
|---|---|---|---|
| O1, K1, O2 | Order, Cart | Customer presses Place order | Order asks Cart for a read-only snapshot. Order stores the lines and prices in its own order record. From now on cart edits and price changes cannot touch this order. |
| I1 to I3 | Inventory | HTTP reserve call from Order | In one transaction, check every line and reserve all of them, or none. The reply is synchronous so the customer is told at once which items are short. No payment is requested on this branch. |
| I2 | Inventory | Same call | Reservation row is HELD with `expires_at = now + 10 min`. |
| P1 | Payment | HTTP charge call from Order | Store the payment as PENDING, then charge the provider. The idempotency key is the order id, so a retried request cannot charge twice. Payment is the only service that talks to the provider. |
| P2 to P6 | Payment | Provider webhook | Check the signature. Then, in one transaction, insert the provider event id into `processed_webhooks` (unique) and update the payment. A repeat hits the unique constraint and is acknowledged with 200 and ignored (P3). |
| O5, I7 | Order, Inventory | PaymentDeclined | The order is closed. The hold is released, and releasing is safe if the hold has already expired. The cart is untouched, so the customer can try again. |
| O6, I4, I5 | Order, Inventory | PaymentSucceeded | Order asks Inventory to claim. The check and the status change happen in one row transaction, so the claim and the expiry timer (I8) cannot both win. |
| O7, K2 | Order, Cart | Claim OK | Order is CONFIRMED and the customer is emailed. Cart empties on the OrderConfirmed event and only then. |
| I6, O8 | Inventory, Order | Claim refused | This is the late-success case. Order cancels as out of stock, emails the customer, and requests a refund. No partial shipment. |
| P7 to P11 | Payment | RefundRequested | Refund the full amount. A failed or timed-out refund is never dropped. See "Failed refund". |

## What each service stores

| Service | Tables (owned privately) |
|---|---|
| **Cart** | `carts`, `cart_lines` (sku, qty, unit price), `processed_events`. |
| **Inventory** | `stock` (sku, on_hand, reserved). `reservations` (order id unique, lines, status HELD, CLAIMED, RELEASED or EXPIRED, `expires_at`). `processed_events`. |
| **Order** | `orders` (id, customer, status, total, refund_status). `order_lines` (the snapshot: sku, qty, price at Place order). `outbox`, `processed_events`. |
| **Payment** | `payments` (order id unique, amount, status PENDING, SUCCEEDED or DECLINED, provider ref). `refunds` (order id unique, status REQUESTED, REFUND_PENDING, REFUNDED or REFUND_STUCK, attempts, next_retry_at). `processed_webhooks` (provider event id unique). `outbox`. |

## Failure branches

1. **Short stock.** I1 says no. Inventory reserves nothing. Order marks the order REJECTED_OUT_OF_STOCK and shows the short items. No payment is requested and the cart is unchanged.
2. **Declined payment.** The webhook says declined. The payment is DECLINED, and Order closes the order and releases the hold. The cart is unchanged.
   - Retrying creates a new order id, so the provider treats it as a new charge. Reusing the declined order id would return the declined result.
3. **Late success after the hold lapsed.** The webhook says succeeded but the hold is EXPIRED, and some line is no longer free.
   - I4 says no, so Order cancels as out of stock, emails the customer and requests a full refund.
   - Any PaymentSucceeded for an order that is not awaiting payment is handled the same way: refund it.
4. **Failed refund.** Payment stores the refund before calling the provider, so the intent survives a crash.
   - A failure or timeout leaves it REFUND_PENDING (P10). It is retried with backoff using the same refund key, so a retry cannot refund twice.
   - After N tries it becomes REFUND_STUCK, on-call is alerted, and it keeps retrying on a slow schedule until it succeeds or someone resolves it by hand (P11).
   - Order shows the refund status on the order record (O9).
5. **Duplicate webhooks.** P2 dedupes on the provider event id inside the same transaction as the state change. Status transitions are also guarded: only PENDING can become SUCCEEDED or DECLINED. Duplicate broker messages are dropped by `processed_events` in each consumer.

## Decisions to confirm

- **Lapsed hold, stock still free.** I4 lets a late payment claim anyway if every line can be re-reserved at that moment. This avoids refunding a customer needlessly. If you want a strict reading, where a lapsed hold always means refund, remove the second half of I4's condition.
- **No webhook after 30 minutes.** The design adds a Payment reconciler (not drawn). For payments still PENDING after about 35 minutes, it asks the provider for the status by order id and processes the answer like a webhook.
- **Email sender.** Order sends the emails, to avoid adding a fifth service. Move this to a notification service later if one appears.
- **Customer-facing status.** After Place order the page polls `GET /orders/{id}`. It shows processing, confirmed, rejected for stock, payment declined, or cancelled out of stock with refund coming.
