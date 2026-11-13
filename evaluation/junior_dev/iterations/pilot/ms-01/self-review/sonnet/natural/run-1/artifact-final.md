# Checkout across Cart, Inventory, Payment and Order

## How to read this

In one sentence: when the customer presses Place order, Order snapshots the cart, Inventory reserves the stock, Payment charges the customer through the external provider, and then Order confirms the order and Cart is emptied. The rest of this document covers what happens when a step fails.

- There are four services: **Cart**, **Order**, **Inventory** and **Payment**. Each owns its own database. They talk only by HTTP calls (arrows labelled `HTTP`) or by events on the shared message broker (arrows labelled `event`). No service reads another service's tables.
- Only **Payment** talks to the external payment provider.
- **Order** is the coordinator. When it receives a reply or an event, it decides what happens next and records the result as the order's status.
- In the flowchart, each service is a grouped box, and each step sits inside the group of the service that performs it. The group title also lists that service's database tables. The **Customer** group shows what the customer sees or receives.
- Arrow labels say what triggers the next step. An arrow with no label means "then".
- Red-bordered boxes are the failure branches: short stock, declined payment, late success, failed refund and duplicate webhook.
- Some steps are requested by HTTP and answered by an event. Both arrows appear (for example, Order calls Inventory over HTTP, and Inventory replies with an event).

Terms used throughout:

- **Idempotency key**: a unique value sent with a request. If the same key arrives twice, the receiver returns the first result instead of repeating the action. Here the key is the order id (or `refund-<orderId>` for refunds).
- **Webhook**: an HTTP call the payment provider makes to Payment to report a result, instead of Payment waiting on the original request.
- **Outbox**: a table in a service's own database. A service writes its state change and the event it must publish in one database transaction (all-or-nothing). A separate publisher then sends the event to the broker. A crash therefore cannot save the change without the event. Every service that publishes events (Order, Inventory, Payment) has one.
- **Hold**: a temporary reservation of stock that lasts 10 minutes. **Claim**: turning a hold into a permanent allocation once the order is paid for. Unclaimed holds expire and the stock goes back on sale.
- **Unique constraint**: a database rule that rejects a second row with the same value. It is how duplicates are detected.
- **N**: the number of failed refund attempts after which a person is alerted. Its value is not decided yet.

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
    O1["Create order PENDING_STOCK. Ask Cart for the cart. Save its lines and prices as the order's own copy. Never changes afterwards"]
    O2["Status REJECTED_SHORT_STOCK. No payment requested"]
    O3["Status AWAITING_PAYMENT"]
    O4["Status PAYMENT_DECLINED"]
    O4b["Ask Inventory to claim the stock"]
    O5["Status CONFIRMED. Publish OrderConfirmed"]
    O6["Status CANCELLED_OUT_OF_STOCK. Send email. Publish RefundRequested"]
    O7["Status REFUNDED"]
  end

  subgraph CART["Cart service - DB: carts, cart_lines"]
    K1["Return cart lines and prices as they are now"]
    K2["Empty the cart. Safe to repeat"]
  end

  subgraph INV["Inventory service - DB: stock, reservations, reservation_lines, outbox"]
    I1{"Every line in stock?"}
    I2["Reserve all lines in ONE transaction. Hold expires in 10 minutes. Publish StockReserved"]
    I3["Reserve nothing. Publish StockShort with the short items"]
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

  subgraph PROV["Payment provider (external)"]
    V1["Processes charge. Result after seconds, up to 30 min"]
  end

  C1 -->|"HTTP"| O1
  O1 -->|"HTTP get cart"| K1
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

1. **Place order.** Order creates the order in status `PENDING_STOCK`, then calls Cart over HTTP for the current lines and prices and saves them as the order's own copy. After that, cart edits and price changes cannot touch the order. Order also ignores a repeated Place order (for example a double click) while an earlier order for the same cart is still in progress, by using the cart id as a dedupe key.
2. **Reserve stock.** Order asks Inventory to reserve all the lines, using the order id as the key. Inventory checks every line and reserves all of them in one database transaction, or none. If every line is available, it publishes `StockReserved`. If any line is short, it publishes `StockShort` listing exactly which ones. Order then marks the order `REJECTED_SHORT_STOCK` and the customer sees the short items. No payment is requested and the cart is untouched.
3. **Request payment.** After `StockReserved`, Order marks the order `AWAITING_PAYMENT` and asks Payment to charge. Payment saves a `PENDING` row (one row per order id, enforced by a unique constraint). It then calls the provider with the order id as the idempotency key. If Payment or Order retries this call, the provider returns the original charge instead of making a second one.
4. **Wait for the webhook.** The result can take up to 30 minutes. Payment does not poll or block. It waits for the provider's webhook.
5. **Webhook intake.** Payment verifies the signature. It then inserts the provider's event id into `webhook_inbox`, which has a unique constraint on that id. If the id is already there, Payment replies 200 and does nothing. This is the duplicate-webhook branch. The inbox insert, the payment status change and the outgoing event are written in one transaction (using the outbox), so a crash cannot record the webhook without also recording the result and the event.
6. **Declined.** Payment publishes `PaymentDeclined`. Order marks the order `PAYMENT_DECLINED`, asks Inventory to release the hold, and tells the customer. The cart is untouched. If the customer tries again, that is a new Place order with a new order id and so a new idempotency key. A declined order id is never charged again.
7. **Succeeded.** Payment publishes `PaymentSucceeded`. Order asks Inventory to **claim** the stock for that order. Inventory then takes one of two paths.
   - **Normal path.** The hold is still valid. Inventory marks it claimed and publishes `StockClaimed`. Order marks the order `CONFIRMED`, emails the customer, and publishes `OrderConfirmed`. Cart reacts to that event by emptying the cart. This is the only point where the cart is emptied.
   - **Late success.** The claim arrives after the 10-minute hold has lapsed. Inventory checks whether every line is still free. If so, it re-takes the stock and the claim succeeds as in the normal path. Otherwise (some stock has been sold to someone else) it publishes `ClaimFailed`. Order marks the order `CANCELLED_OUT_OF_STOCK`, emails the customer, and publishes `RefundRequested`. Nothing is shipped, because we never ship partial orders. The cart stays as it was.
8. **Refund.** Payment saves a refund row for the full amount before it calls the provider, using the idempotency key `refund-<orderId>`. If the provider accepts it, Payment saves `REFUNDED` and publishes `RefundCompleted`, and Order marks the order `REFUNDED`. If the provider rejects it or times out, the row becomes `REFUND_FAILED` with an attempt count and next retry time. A timer retries every refund that is not yet `REFUNDED`. After N failed attempts it also alerts a person, but the retries continue. A refund is never deleted or given up on.
9. **Hold expiry.** A timer in Inventory expires unclaimed holds after 10 minutes and puts the stock back on sale. Expiry and claim both do a conditional update on the reservation row (from `held` to `expired` or `claimed`), so exactly one of them wins if they race. A claim on an already expired hold takes the late-success check in step 7.

## What each service stores

| Service | Stores | Key constraints |
|---|---|---|
| Cart | Carts and cart lines (product, quantity, price) | Emptied only on `OrderConfirmed`. Emptying is safe to repeat |
| Order | Order, its copy of the lines and prices, status, outbox | Unique per checkout attempt. Lines and prices are never updated |
| Inventory | Stock levels, reservations (`held`, `claimed`, `expired`, `released`), reservation lines, `expires_at`, outbox | One reservation per order id. Reserve and claim are each a single transaction |
| Payment | Payment (status, amount, provider charge id), refunds (status, attempts, next retry), `webhook_inbox`, outbox | Unique payment per order id. Unique provider event id in the inbox |

## Order statuses

`PENDING_STOCK` (created, stock not yet reserved) leads to one of:

- `REJECTED_SHORT_STOCK` (end)
- `AWAITING_PAYMENT` (stock held, waiting for the provider), which leads to one of:
  - `PAYMENT_DECLINED` (end)
  - `CONFIRMED` (end)
  - `CANCELLED_OUT_OF_STOCK`, then `REFUNDED` (end)

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
- No separate email service exists, so Order sends the emails. If there is a notification service, Order would publish an event to it instead.
- The customer gets one email when the order is cancelled, and Order records the refund later as `REFUNDED`. If you want a second email when the refund lands, trigger it from `RefundCompleted`.
- The values for N (refund attempts before alerting) and the retry backoff are not decided yet.
- The broker may deliver an event more than once, which is why every handler checks status or keys first.
- An order stuck in `AWAITING_PAYMENT` with no webhook long after 30 minutes is not covered by the stated requirements. I suggest a reconciliation job in Payment that asks the provider for the charge status once an order is older than about 35 minutes.