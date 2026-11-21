# Checkout design: Cart, Inventory, Payment, Order

## How to read this

- Each box in the diagram sits inside the service that does the work.
- Solid arrows are HTTP calls or broker events. The label says which.
- Red boxes are failure branches. Green is the happy path ending.
- Every step that changes state also writes its outgoing event to an **outbox table** in the same database transaction. A separate relay publishes outbox rows to the broker. Brokers deliver at least once, so every consumer ignores repeats by event id or order id. This is what keeps "state changed" and "event sent" from drifting apart.

## Flowchart

```mermaid
flowchart TD
    START(["Customer presses Place order"])

    subgraph ORDER["ORDER service (owns orders)"]
        O1["O1. Create order PENDING.<br/>Call Cart for lines and prices and save them as a frozen snapshot.<br/>Order id is created here."]
        O2["O2. Call Inventory: reserve all lines for this order id (HTTP)"]
        O3["O3. Status AWAITING_PAYMENT.<br/>Emit PaymentRequested with order id and total (event)"]
        OREJ["Status REJECTED_SHORT_STOCK.<br/>Reply to customer listing the short items"]
        ODEC["Status PAYMENT_DECLINED.<br/>Tell customer the payment failed.<br/>Emit ReleaseStock (event)"]
        O5["O5. Payment succeeded.<br/>Call Inventory: claim the reservation (HTTP)"]
        OOK["Status CONFIRMED.<br/>Emit OrderConfirmed (event).<br/>Email order confirmation"]
        OCAN["Status CANCELLED_OUT_OF_STOCK.<br/>Emit RefundRequested for the full amount (event).<br/>Email customer: out of stock, full refund on its way"]
        OREF["Record refund completed.<br/>Email customer: refund issued"]
    end

    subgraph CART["CART service (owns carts)"]
        C1["C1. Return current cart lines and prices (HTTP reply)"]
        C2["C2. On OrderConfirmed: empty the cart.<br/>Repeat deliveries do nothing"]
        CKEEP["Cart is not touched.<br/>Customer can edit it and press Place order again"]
    end

    subgraph INV["INVENTORY service (owns stock)"]
        I1{"I1. Every line in stock?"}
        ISHORT["Reserve nothing.<br/>Reply with the list of short items"]
        I2["I2. Hold all lines for this order.<br/>Reservation HELD, expires in 10 minutes"]
        IREL["Release the hold.<br/>Stock goes back on sale"]
        ISWEEP["Expiry sweeper, runs every minute:<br/>HELD reservations past 10 minutes become EXPIRED<br/>and their stock goes back on sale"]
        I3{"I3. Claim request.<br/>Is the hold still HELD?"}
        I4{"I4. Hold lapsed.<br/>Is every line still free right now?"}
        I5["Claim: stock deducted for good.<br/>Reservation CLAIMED.<br/>Reply claimed"]
        IGONE["Reply STOCK_GONE.<br/>Nothing is changed"]
    end

    subgraph PAY["PAYMENT service (owns payments, refunds, webhook log)"]
        P1["P1. Save payment REQUESTED.<br/>One row per order id.<br/>Charge the provider with idempotency key = order id"]
        P2{"P2. Webhook received.<br/>Signature valid and provider event id new?"}
        PDUP["Duplicate event.<br/>Reply 200 OK and do nothing"]
        P3{"P3. Provider outcome?"}
        PDEC["Save payment DECLINED.<br/>Emit PaymentDeclined (event)"]
        PSUC["Save payment SUCCEEDED.<br/>Emit PaymentSucceeded (event)"]
        P4["P4. Save refund PENDING first.<br/>Ask provider for a full refund,<br/>idempotency key = refund + order id"]
        P5{"P5. Provider accepted the refund?"}
        PRETRY["Save refund RETRYING with attempt count and next try time.<br/>A retry job picks it up with growing delays"]
        PALERT["After N failed attempts: raise an ops alert.<br/>Refund stays open and keeps retrying.<br/>It is never dropped"]
        PDONE["Save refund COMPLETED.<br/>Emit RefundCompleted (event)"]
        PWATCH["Watchdog: no webhook 45 minutes after the charge?<br/>Ask provider for the charge status by order id<br/>and treat the answer like a webhook"]
    end

    PROV(["Payment provider (external, only Payment talks to it)"])

    START --> O1
    O1 -->|"GET cart"| C1
    C1 -->|"lines and prices"| O1
    O1 --> O2
    O2 -->|"reserve"| I1
    I1 -->|"no"| ISHORT
    ISHORT -->|"short items"| OREJ
    OREJ --> CKEEP
    I1 -->|"yes"| I2
    I2 -->|"reserved"| O3
    I2 -.->|"after 10 min if never claimed"| ISWEEP

    O3 -->|"PaymentRequested"| P1
    P1 -->|"charge request"| PROV
    PROV -.->|"webhook: seconds to 30 min, may repeat"| P2
    PWATCH -.-> P2
    P2 -->|"already seen"| PDUP
    P2 -->|"new"| P3
    P3 -->|"declined"| PDEC
    P3 -->|"succeeded"| PSUC

    PDEC -->|"PaymentDeclined"| ODEC
    ODEC -->|"ReleaseStock"| IREL
    ODEC --> CKEEP

    PSUC -->|"PaymentSucceeded"| O5
    O5 -->|"claim"| I3
    I3 -->|"yes"| I5
    I3 -->|"no, expired or released"| I4
    I4 -->|"yes, claim it now"| I5
    I4 -->|"no, sold to someone else"| IGONE
    I5 -->|"claimed"| OOK
    OOK -->|"OrderConfirmed"| C2
    IGONE -->|"STOCK_GONE"| OCAN
    OCAN -->|"RefundRequested"| P4
    OCAN --> CKEEP

    P4 -->|"refund request"| PROV
    PROV --> P5
    P5 -->|"yes"| PDONE
    P5 -->|"no, error or timeout"| PRETRY
    PRETRY -->|"retry"| P4
    PRETRY --> PALERT
    PDONE -->|"RefundCompleted"| OREF

    classDef fail fill:#fde2e2,stroke:#b42318,color:#401010
    classDef good fill:#dcf5e3,stroke:#1a7f37,color:#10331a
    classDef ext fill:#eee,stroke:#666,color:#222
    class OREJ,ISHORT,ODEC,PDEC,IGONE,OCAN,PRETRY,PALERT,PDUP,CKEEP fail
    class OOK,C2,I5,PDONE,OREF good
    class PROV,START ext
```

## Step by step

1. **Place order (Order).** Order creates the order with a new id, asks Cart for its lines and prices, and stores them as the order's own snapshot. From here on, Order never looks at Cart again, so cart edits and price changes cannot affect this order.
2. **Reserve (Inventory).** Order sends all lines in one request. Inventory checks every line and holds all of them or none.
   - Any line short: nothing is held, and Inventory returns the short items. Order marks the order `REJECTED_SHORT_STOCK` and replies to the customer with those items. Payment is never contacted.
   - All lines available: Inventory records a reservation for this order id that expires in 10 minutes.
3. **Request payment (Order to Payment).** Order moves to `AWAITING_PAYMENT` and emits `PaymentRequested`. Payment saves a payment row keyed by order id, then calls the provider with the order id as idempotency key. A retried call, or a re-delivered `PaymentRequested`, cannot charge twice.
4. **Webhook (Payment).** The provider reports the result in a few seconds, or up to 30 minutes later. Payment checks the signature and looks up the provider's event id in its webhook log. The log has a unique constraint on that id.
   - Already seen: reply 200 and do nothing.
   - New: record the event and update the payment in one transaction, then emit the result event.
5. **Declined.** Payment emits `PaymentDeclined`. Order marks `PAYMENT_DECLINED` and tells the customer. It also emits `ReleaseStock`, so Inventory frees the hold early. The cart is unchanged. A retry is a new Place order with a new order id. The old id stays tied to the declined charge.
6. **Succeeded.** Payment emits `PaymentSucceeded`. Order asks Inventory to **claim** the reservation.
   - Hold still active: Inventory marks it `CLAIMED` and deducts the stock for good.
   - Hold lapsed: Inventory tries once to take the same quantities again, all lines together. If they are still free, the claim succeeds. If any line was sold, it replies `STOCK_GONE`.
7. **Confirmed.** On a successful claim, Order marks `CONFIRMED`, emails the confirmation and emits `OrderConfirmed`. Cart reacts to that event by emptying the cart. This is the only place the cart is emptied.
8. **Late success, stock gone.** Order marks `CANCELLED_OUT_OF_STOCK` and emits `RefundRequested`. It emails the customer that the item is out of stock and the full amount is being refunded. The whole order is cancelled. Nothing ships in part. The cart stays as it was.
9. **Refund (Payment).** Payment saves the refund as `PENDING` before calling the provider, so a crash cannot lose it. The refund uses its own idempotency key (refund plus order id), so retries cannot refund twice.
   - Accepted: `COMPLETED`. Payment emits `RefundCompleted` and Order emails the customer that the refund is issued.
   - Failed or timed out: `RETRYING`, with an attempt count and next-try time. A retry job repeats it with growing delays. After N attempts it raises an ops alert but keeps retrying. Nothing deletes a refund row until it is `COMPLETED`.

## What each service stores

| Service | Stores | Key fields and rules |
|---|---|---|
| **Cart** | Carts and cart lines. List of order ids already used to clear a cart. | Current items and prices only. Emptied on `OrderConfirmed`, and a repeat of the same event does nothing. |
| **Order** | Orders with frozen line and price snapshot. Outbox. Processed-event ids. | Status: `PENDING`, `AWAITING_PAYMENT`, `CONFIRMED`, `REJECTED_SHORT_STOCK`, `PAYMENT_DECLINED`, `CANCELLED_OUT_OF_STOCK`. Total and customer contact. |
| **Inventory** | Stock levels. Reservations and their lines. | Reservation: order id (unique), lines, `expires_at` (now + 10 min), status `HELD`, `CLAIMED`, `RELEASED` or `EXPIRED`. Reserving or claiming checks and changes all lines in one transaction. |
| **Payment** | Payments. Refunds. Webhook log. Outbox. | Payment: unique order id, amount, provider charge id, status. Refund: order id, amount, status `PENDING`, `RETRYING` or `COMPLETED`, attempts, next try time. Webhook log: unique provider event id. |

## Every failure branch

| Situation | Who detects it | What happens | Cart |
|---|---|---|---|
| Any line short | Inventory | Nothing reserved. No payment requested. Customer sees the short items. Order is `REJECTED_SHORT_STOCK`. | Unchanged |
| Payment declined | Payment, from the webhook | Order is `PAYMENT_DECLINED`. Hold is released. Customer is told. | Unchanged |
| Payment succeeds after the hold lapsed, stock gone | Inventory, on the claim | Full refund. Order is `CANCELLED_OUT_OF_STOCK`. Customer is emailed. | Unchanged |
| Payment succeeds after the hold lapsed, stock still free | Inventory, on the claim | Claimed late. Order is confirmed normally. | Emptied |
| Refund fails at the provider | Payment | Kept as `RETRYING` and retried with backoff. Ops alert after N attempts. Never dropped. | Unchanged |
| Same webhook delivered again | Payment | Found in the webhook log. Replied 200 and ignored. | No effect |
| Charge request retried, or `PaymentRequested` redelivered | Provider and Payment | Same order id as idempotency key, so one charge only. | No effect |
| Webhook never arrives | Payment watchdog | After 45 minutes, Payment asks the provider for the charge status and handles the answer like a webhook. | Unchanged until confirmed |

## Decisions I made that you should check

- **Late claim retries the stock.** The brief says the hold lapses and the stock goes back on sale. It does not say what to do if a late payment arrives and the stock is still free. I chose to claim it if every line is still available, because refunding a fulfillable order is worse for everyone. If you would rather always refund after a lapse, drop the "I4" check and send every lapsed hold straight to `STOCK_GONE`.
- **The email comes from an existing mailer.** Order publishes the event, and whatever sends your emails today consumes it. The brief names only four services, so I did not add a fifth.
- **The 45-minute watchdog and the "N attempts" for refund alerts are my numbers.** The 30-minute webhook limit is from the brief. The rest are placeholders for you to tune.
- **Emptying the cart.** I assumed `OrderConfirmed` empties the whole cart. If customers can add items while payment is pending, you may want Cart to remove only the lines in the order's snapshot. The brief does not say.
- **Customer-facing result.** Place order returns at once with the order id. Short stock is answered in that same response. Payment and refund outcomes are shown by the customer's order page reading the order's status, plus the emails.
