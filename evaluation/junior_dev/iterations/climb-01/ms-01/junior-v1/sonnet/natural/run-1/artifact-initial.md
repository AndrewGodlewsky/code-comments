# Checkout across Cart, Inventory, Payment and Order

## How to read this

- There are four services. Each owns its own database, and none reads another's tables.
- **Events** (shown as `event X` on an arrow) go over the shared message broker. **HTTP** calls are labelled as such.
- Every service writes its events through a transactional outbox: the state change and the event are saved in one local transaction, and a relay then publishes the event. Every consumer records the ids of events it has handled, so a redelivered event does nothing the second time.
- In the diagram, red nodes are failure branches and green is the success end. A dotted arrow means "no event is sent, so this service does nothing".

## Flowchart

```mermaid
flowchart TD
    CUST(["Customer presses Place order"])

    subgraph CART["CART service"]
        A1["Send cart lines and prices to Order<br/>Cart is NOT changed<br/>Saves the order id on the cart"]
        A8["Cart stays exactly as it was<br/>Customer can try again"]
        A9["Empty the cart<br/>only if order id matches"]
    end

    subgraph ORDER["ORDER service"]
        O1["Create order, status PLACED<br/>Freeze lines and prices as a snapshot"]
        O2["Status AWAITING_PAYMENT"]
        O3["Status CANCELLED_SHORT_STOCK<br/>Save the short items<br/>Customer is told which items are short"]
        O4["Status CANCELLED_PAYMENT_DECLINED<br/>Customer is told"]
        O5["Status PAID_CLAIMING<br/>Ask Inventory to claim the stock"]
        O6["Status CONFIRMED<br/>Confirmation email"]
        O7["Status CANCELLED_OUT_OF_STOCK<br/>Email customer: cancelled, full refund coming"]
        O8["Record refund complete"]
    end

    subgraph INV["INVENTORY service"]
        I1{"Are ALL lines<br/>in stock?"}
        I2["Reserve every line in one transaction<br/>Hold for 10 minutes: expires_at = now + 10 min"]
        I3["Reserve nothing"]
        I4{"Claim in one transaction<br/>Hold still valid, or all lines<br/>still free to take now?"}
        I5["Reservation CLAIMED<br/>Stock removed for good"]
        I6["Claim fails<br/>Nothing is claimed"]
        I7["Release hold<br/>Stock back on sale"]
        IS["Expiry timer, runs every minute<br/>HELD and past expires_at becomes EXPIRED<br/>Stock back on sale"]
    end

    subgraph PAY["PAYMENT service"]
        P1["Save payment PENDING<br/>Charge provider, idempotency key = order id"]
        P2["Webhook arrives<br/>Verify signature"]
        P3{"Provider event id<br/>already processed?"}
        P4["Ignore duplicate<br/>Reply 200 OK"]
        P5{"Outcome?"}
        P6["Save payment DECLINED<br/>Save event id in same transaction"]
        P7["Save payment SUCCEEDED<br/>Save event id in same transaction"]
        P8["Save refund REFUND_PENDING, full amount<br/>Call provider refund<br/>idempotency key = refund + order id"]
        P9{"Refund accepted?"}
        P10["Refund REFUNDED"]
        P11["Keep refund REFUND_PENDING<br/>Retry timer retries with backoff, never gives up<br/>After 5 failures alert operations"]
    end

    PROV[("Payment provider<br/>external")]

    CUST --> A1
    A1 -->|"HTTP POST /orders, once per cart version"| O1
    O1 -->|"event OrderPlaced"| I1

    I1 -->|"no, any line short"| I3
    I3 -->|"event StockRejected, with short items"| O3
    I1 -->|"yes"| I2
    I2 -->|"event StockReserved"| O2
    O2 -->|"event PaymentRequested, order id and total"| P1
    P1 -->|"HTTPS charge request, safe to retry"| PROV

    PROV -->|"webhook: succeeded or declined<br/>seconds to 30 minutes, may repeat"| P2
    P2 --> P3
    P3 -->|"yes"| P4
    P3 -->|"no, first time"| P5
    P5 -->|"declined"| P6
    P5 -->|"succeeded"| P7

    P6 -->|"event PaymentDeclined"| O4
    O4 -->|"event OrderCancelled"| I7

    P7 -->|"event PaymentSucceeded"| O5
    O5 -->|"event ClaimStock"| I4
    I4 -->|"yes, in time"| I5
    I5 -->|"event StockClaimed"| O6
    O6 -->|"event OrderConfirmed"| A9

    I4 -->|"no, hold lapsed and stock sold to someone else"| I6
    I6 -->|"event StockClaimFailed"| O7
    O7 -->|"event RefundRequested"| P8
    P8 --> P9
    P9 -->|"yes"| P10
    P9 -->|"no, provider error"| P11
    P11 -->|"retry"| P9
    P10 -->|"event RefundSucceeded"| O8

    O3 -.->|"no OrderConfirmed event"| A8
    O4 -.->|"no OrderConfirmed event"| A8
    O7 -.->|"no OrderConfirmed event"| A8

    classDef fail fill:#fde2e2,stroke:#c0392b,color:#000
    classDef ok fill:#e1f5e1,stroke:#2e7d32,color:#000
    class I3,O3,O4,O7,I6,P4,P6,P11 fail
    class O6,A9,I5,P10 ok
```

## What each step does, in order

1. **Place order (Cart to Order).** Cart sends its lines and prices to Order over HTTP. Order creates the order and freezes the lines and prices as a snapshot, so later cart edits or price changes don't affect it. The request is keyed on the cart id and cart version, so a double-click returns the same order. Cart saves the order id on the cart but does not change the cart's lines.
2. **Reserve stock (Inventory).** Order publishes `OrderPlaced`. Inventory checks every line and reserves all of them in one transaction, or reserves none.
   - **Short stock:** Inventory publishes `StockRejected` with the short items. Order marks the order cancelled and keeps the short items, so the screen the customer is polling (`GET /orders/{id}`) shows which items are short. No payment is ever requested.
   - **All in stock:** each reservation gets `expires_at = now + 10 minutes`, and Inventory publishes `StockReserved`.
3. **Request payment.** Order moves to AWAITING_PAYMENT and publishes `PaymentRequested`. Payment saves the payment as PENDING before it calls the provider. It then sends the charge with the **order id as the idempotency key**. If the call times out, Payment resends the same request, and the provider cannot charge twice.
4. **Webhook arrives (Payment).** The provider's result arrives by webhook, between a few seconds and 30 minutes later. Payment verifies the signature, then checks the provider's event id against its table of processed events.
   - **Duplicate:** Payment replies 200 OK and does nothing else.
   - **First time:** Payment records the event id and the new payment status in **one transaction**. A crash between the two cannot lead to a double process or a lost event.
5. **Declined.** Payment publishes `PaymentDeclined`. Order cancels the order and tells the customer. Order then publishes `OrderCancelled`, and Inventory releases the hold straight away. The cart is untouched.
6. **Succeeded.** Payment publishes `PaymentSucceeded`. Order publishes `ClaimStock`, and Inventory tries to claim in one transaction:
   - **Hold still valid:** Inventory marks it CLAIMED and publishes `StockClaimed`.
   - **Hold already lapsed:** Inventory tries once to take all the lines again, all-or-nothing. If every line is still free, it claims them. This is an assumption of this design, because it avoids refunding an order we could still fulfil. If you want a lapsed hold to always fail, remove that second attempt.
   - **Anything else:** Inventory publishes `StockClaimFailed`. That is the bad case, where payment succeeded but the stock has gone.
7. **Confirmed.** On `StockClaimed`, Order sets CONFIRMED, sends the confirmation email and publishes `OrderConfirmed`. **Only now** does Cart empty the cart, and only if the order id matches the one it saved.
8. **Late success, stock gone.**
   - **Order:** sets CANCELLED_OUT_OF_STOCK, emails the customer ("cancelled, full refund on its way") and publishes `RefundRequested`. The whole order is cancelled, and nothing ships.
   - **Payment:** saves a REFUND_PENDING record for the full amount before it calls the provider. The refund call uses its own idempotency key, so a retry cannot refund twice.
   - **Success:** Payment marks the refund REFUNDED and publishes `RefundSucceeded`. Order records that the refund is complete.
9. **Refund fails at the provider.** The refund record stays REFUND_PENDING and is written to the database, so it survives a restart. A retry timer re-sends pending refunds with backoff and never stops. After 5 failures Payment also alerts operations. A refund can only leave the pending state by succeeding.
10. **Expired holds.** A timer in Inventory runs every minute and returns any hold past `expires_at` to stock. The claim step in 6 checks `expires_at` and status inside its own transaction, so the timer and a late claim cannot both win.

## What each service stores

| Service | Stores |
|---|---|
| **Cart** | Carts and their lines. The id of the order created by the last Place order, so it can match `OrderConfirmed`. Handled-event ids. |
| **Order** | Orders with the frozen snapshot of lines, prices and total. Status (PLACED, AWAITING_PAYMENT, PAID_CLAIMING, CONFIRMED, CANCELLED_SHORT_STOCK, CANCELLED_PAYMENT_DECLINED, CANCELLED_OUT_OF_STOCK). The short items. Refund status. Outbox and handled-event ids. |
| **Inventory** | Stock level per item. Reservations: order id, lines, `expires_at`, and status HELD, CLAIMED, EXPIRED or RELEASED. Outbox and handled-event ids. |
| **Payment** | Payments: order id, amount, status PENDING, SUCCEEDED or DECLINED. Refunds: order id, amount, status REFUND_PENDING or REFUNDED, attempt count. **Processed provider event ids** (unique), used to drop duplicate webhooks. Outbox. |

## Edge cases and decisions

- **Only Payment talks to the provider.** The charge and refund calls and the webhook endpoint all live in Payment. No other service sees provider credentials.
- **No double charge.** The charge key is the order id, and retries reuse it. One order can have at most one charge.
- **Failure leaves the cart alone.** Cart changes only on `OrderConfirmed`. The three failure paths (short stock, declined, out of stock) all leave the cart as it was, so the customer can press Place order again. A retry creates a new order and a new snapshot.
- **A success arriving for an order that is no longer waiting for payment** (for example, already cancelled) goes down the same path as a failed claim: refund in full.
- **Redelivered events are safe.** Because every service records the event ids it has handled, a message delivered twice has no second effect.
- **Open question for you.** I used 5 failed refund attempts as the alert point, and one minute as the expiry timer interval. Both are easy to change.
