# Checkout across Cart, Inventory, Payment and Order

## How to read this

- Solid arrows are synchronous HTTP calls or steps inside one service.
- Dotted arrows are events on the shared message broker. The label is the event name.
- Each box sits in the service that does the step. No service reads another service's tables, so data crosses only in HTTP bodies and event payloads.
- Every event is written to the sender's own database in the same transaction as its state change (a transactional outbox) and then published. A crash between "saved" and "published" therefore cannot lose an event. Consumers tolerate duplicates.

```mermaid
flowchart TD
    START(["Customer presses Place order"])

    subgraph CART["CART service - owns: carts, cart lines, current prices"]
        C1["Snapshot cart lines and prices<br/>Cart is NOT changed or locked"]
        C9["Empty the cart"]
    end

    subgraph ORDER["ORDER service - owns: orders, order lines with price snapshot, status, outbox"]
        O1["Create order PENDING<br/>store snapshot copy of lines, prices, total"]
        O2["Order REJECTED_OUT_OF_STOCK<br/>no payment requested"]
        O3["Order AWAITING_PAYMENT<br/>publish StockReserved with total and currency"]
        O4["Order PAYMENT_FAILED"]
        O5{"Order still AWAITING_PAYMENT?"}
        O6["Order CONFIRMED<br/>publish OrderConfirmed<br/>email order confirmation"]
        O7["Order CANCELLED_OUT_OF_STOCK<br/>publish RefundRequested<br/>email customer: cancelled, refund on its way"]
        O8["Record refund as done<br/>email customer: refund complete"]
    end

    subgraph INV["INVENTORY service - owns: stock levels, reservations, reservation lines"]
        I1{"Every line in stock?"}
        I3["Reserve nothing<br/>return list of short items"]
        I4["In ONE local transaction reserve all lines<br/>reservation ACTIVE, expires in 10 min<br/>keyed by order id so retries are safe"]
        I5["Release reservation<br/>stock back on sale"]
        I6{"Reservation still ACTIVE?"}
        I7{"Expired: can ALL lines be taken again now?"}
        I8["Reservation CLAIMED<br/>stock permanently deducted"]
        I9["Claim failed: stock has gone<br/>nothing deducted"]
        IT["Sweeper every minute:<br/>ACTIVE and past 10 min becomes EXPIRED<br/>stock back on sale"]
    end

    subgraph PAY["PAYMENT service - owns: payments, refunds, webhook dedupe table, outbox"]
        P1["Create payment PENDING<br/>send charge request to provider<br/>idempotency key = order id"]
        P2["Webhook received<br/>insert provider event id into dedupe table"]
        P3{"Event id already stored?"}
        P4["Reply 200 and do nothing"]
        P5{"Provider outcome?"}
        P6["Payment DECLINED<br/>publish PaymentDeclined"]
        P7["Payment SUCCEEDED<br/>publish PaymentSucceeded"]
        P8["Refund record REFUND_PENDING<br/>request full refund from provider<br/>idempotency key = refund + order id"]
        P9{"Provider accepted refund?"}
        P10["Refund REFUNDED<br/>publish RefundSucceeded"]
        P11["Keep REFUND_PENDING<br/>schedule retry with backoff"]
        P12{"Retry limit reached?"}
        P13["Refund REFUND_FAILED<br/>alert on-call, add to manual queue<br/>still retried until a human closes it"]
    end

    PROV[["Payment provider - external<br/>only Payment talks to it"]]

    END_SHORT(["Customer is told which items are short<br/>Cart unchanged"])
    END_DECL(["Customer told payment declined<br/>Cart unchanged, can try again"])
    END_OK(["Order confirmed, cart empty"])

    START --> C1
    C1 -->|"HTTP: create order with snapshot"| O1
    O1 -->|"HTTP: reserve all lines"| I1

    I1 -->|"No, any line short"| I3
    I3 -->|"HTTP reply: shortages"| O2
    O2 --> END_SHORT

    I1 -->|"Yes"| I4
    I4 -->|"HTTP reply: reserved"| O3
    O3 -.->|"event StockReserved"| P1
    P1 -->|"charge request"| PROV

    PROV -->|"webhook: succeeded or declined<br/>seconds to 30 min, may repeat"| P2
    P2 --> P3
    P3 -->|"Yes, duplicate"| P4
    P3 -->|"No, first time"| P5

    P5 -->|"Declined"| P6
    P6 -.->|"event PaymentDeclined"| O4
    O4 -->|"HTTP: release"| I5
    O4 --> END_DECL

    P5 -->|"Succeeded"| P7
    P7 -.->|"event PaymentSucceeded"| O5
    O5 -->|"No, e.g. already failed or cancelled"| O7
    O5 -->|"Yes"| I6
    I6 -->|"Yes, hold still valid"| I8
    I6 -->|"No, hold lapsed"| I7
    I7 -->|"Yes, stock still free"| I8
    I7 -->|"No, sold to someone else"| I9
    I8 -->|"HTTP reply: claimed"| O6
    I9 -->|"HTTP reply: claim failed"| O7

    O6 -.->|"event OrderConfirmed"| C9
    C9 --> END_OK

    O7 -.->|"event RefundRequested"| P8
    P8 -->|"refund request"| PROV
    PROV -->|"refund response"| P9
    P9 -->|"Yes"| P10
    P10 -.->|"event RefundSucceeded"| O8
    P9 -->|"No, error or timeout"| P11
    P11 --> P12
    P12 -->|"No"| P8
    P12 -->|"Yes"| P13

    IT -.->|"unclaimed holds lapse on their own"| I1
```

## Step by step

1. **Place order.** Cart reads its own lines and prices and sends them to Order. Cart does not change at this point. Order saves a private copy of the lines, prices and total, so later cart edits or price changes cannot touch it.
2. **Reserve stock before any payment.** Order calls Inventory over HTTP. Inventory checks every line and reserves them all in one local transaction, or reserves nothing. The call is keyed by order id, so a retry returns the same reservation. Each reservation expires 10 minutes after it is created.
3. **Short stock.** Inventory replies with the short items. Order is marked REJECTED_OUT_OF_STOCK, no payment is ever requested, and the customer sees which items are short. The cart is untouched.
4. **Request payment.** Order publishes `StockReserved` with the total. Payment creates its record and sends the charge to the provider with the order id as the idempotency key. A retried request can never double-charge.
5. **Webhook.** The provider reports the result by webhook, usually within seconds and sometimes up to 30 minutes later. Payment first inserts the provider's event id into a table with a unique constraint. If the insert finds the id already there, the webhook is a duplicate. Payment replies 200 and does nothing. The insert and the payment state change commit together, so a crash cannot leave a half-processed event.
6. **Declined.** Payment publishes `PaymentDeclined`. Order moves to PAYMENT_FAILED and tells Inventory to release the hold. The customer is told, and the cart is unchanged so they can retry.
7. **Succeeded.** Payment publishes `PaymentSucceeded`. Order asks Inventory to claim the reservation. Inventory handles three cases:
   - **Hold still valid:** it claims the stock.
   - **Hold lapsed but the stock is still free:** it takes all lines again in one transaction and claims them.
   - **Hold lapsed and the stock has gone:** the claim fails, and nothing is deducted.

   Claiming and expiring are both state changes on the same reservation row inside Inventory. Only one of them can win.
8. **Confirmed.** Order becomes CONFIRMED and emails the customer. Its `OrderConfirmed` event is what makes Cart empty the cart. This is the only place the cart is emptied.
9. **Late success after the stock is gone.** Order is marked CANCELLED_OUT_OF_STOCK and emails the customer. It publishes `RefundRequested`, and Payment refunds the full amount automatically. Nothing ships, so no partial orders are possible.
10. **Refund failure.** The refund is a stored record in REFUND_PENDING and is retried with backoff, using its own idempotency key so retries cannot refund twice. If the retry limit is reached, the record becomes REFUND_FAILED. That raises an alert and puts the refund in a manual queue. It is never deleted, and it keeps being retried until it succeeds or a person closes it. When a refund succeeds, Order emails the customer that the money is back.

## Order states

`PENDING` then one of:

- `REJECTED_OUT_OF_STOCK`
- `AWAITING_PAYMENT`, then `PAYMENT_FAILED`, `CONFIRMED` or `CANCELLED_OUT_OF_STOCK`

## What each service stores

| Service | Owns |
|---|---|
| Cart | Carts, cart lines, current prices. It changes only when the customer edits it or when `OrderConfirmed` arrives. |
| Order | Orders, the price and line snapshot, order status, outbox. |
| Inventory | Stock levels, reservations (ACTIVE, CLAIMED, EXPIRED, RELEASED) with expiry time, outbox. |
| Payment | Payments, refunds (REFUND_PENDING, REFUNDED, REFUND_FAILED), dedupe table of provider event ids, outbox. |

## Decisions I made that you may want to change

- **The hold lapsing does not cancel the order.** The order stays AWAITING_PAYMENT until the payment outcome arrives, because that can take up to 30 minutes. Only the stock is released at 10 minutes. If a payment never gets an outcome, Payment should poll the provider after about 35 minutes. I left that out of the diagram.
- **Re-taking lapsed stock.** If a hold lapsed but the stock is still free, the order is fulfilled. This avoids needlessly cancelling paid orders. If you would rather cancel and refund every late payment, remove the "can all lines be taken again" check.
- **Who sends email.** The brief names no notification service, so I assumed Order sends the emails. Move that to a separate service if you have one.
- **Success arriving for a dead order.** A `PaymentSucceeded` event can arrive for an order that is no longer AWAITING_PAYMENT, for example one already marked PAYMENT_FAILED or cancelled. Order sends it straight to the refund path.
