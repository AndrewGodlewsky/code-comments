# Checkout across Cart, Inventory, Payment and Order

## How to read this

- Each box is one step. Boxes sit inside the service that does the step. Customers and the payment provider are outside the services.
- Arrows say what triggers the next step. "HTTP" is a direct call. Names in `code font` are events on the shared message broker.
- Every service writes its events through a **transactional outbox**. The state change and the event are saved in one database transaction, and a relay publishes the event afterwards. Every consumer is idempotent, so a redelivered event does nothing.
- `orderId` is created when Place order is pressed. It ties together the reservation, the charge, the refund and the idempotency keys.

## Flowchart

```mermaid
flowchart TD
    %% ---------- Customer and provider ----------
    subgraph EXT["Outside the services"]
        U0(["Customer presses Place order"])
        PROV["Payment provider<br/>charges the card and sends the result by webhook<br/>takes seconds, up to 30 min, may send the same webhook twice"]
        U1(["Customer told: these items are short<br/>cart unchanged, nothing charged"])
        U2(["Customer told: payment declined<br/>cart unchanged, can try again"])
        U3(["Customer emailed: order confirmed"])
        U4(["Customer emailed: cancelled as out of stock<br/>full refund on its way"])
        U5(["Customer emailed: refund issued"])
    end

    %% ---------- Cart ----------
    subgraph CART["CART service - stores: cart lines, current prices"]
        C1["Return the cart's lines and prices<br/>cart is not changed"]
        C2["Empty the cart<br/>only ever happens here, after confirmation"]
    end

    %% ---------- Order ----------
    subgraph ORDER["ORDER service - stores: orders with a frozen copy of lines and prices, status, event ids already handled"]
        O1["Create order, status PENDING_RESERVATION<br/>save snapshot of lines and prices as they are now<br/>later cart or price changes never touch it"]
        O2["Status REJECTED_SHORT_STOCK"]
        O3["Status AWAITING_PAYMENT"]
        O4["Status PAYMENT_DECLINED"]
        O5{"Is the order still<br/>AWAITING_PAYMENT?"}
        O6["Status CONFIRMED"]
        O7["Status CANCELLED_OUT_OF_STOCK"]
        O8["Record refund as done"]
    end

    %% ---------- Inventory ----------
    subgraph INV["INVENTORY service - stores: stock levels, reservations per order id with status HELD / CLAIMED / RELEASED and expiry time"]
        I1{"Is every line<br/>in stock?"}
        I2["Reserve nothing<br/>reply with the list of short items"]
        I3["Reserve ALL lines in one transaction<br/>status HELD, expires in 10 minutes"]
        I4["Release the reservation<br/>stock back on sale<br/>does nothing if already lapsed"]
        I5{"Is the reservation still HELD<br/>and not past its expiry?"}
        I6["Status CLAIMED<br/>stock is now sold, permanent"]
        I7["Reply: cannot claim<br/>hold lapsed and stock is gone"]
        IX["Expiry sweep, runs every minute<br/>HELD and past expiry becomes RELEASED<br/>stock back on sale"]
    end

    %% ---------- Payment ----------
    subgraph PAY["PAYMENT service - stores: one payment record per order id, refund records and their retry state, inbox of provider event ids already processed"]
        P1["Save payment record PENDING<br/>ask provider to charge<br/>idempotency key = order id<br/>a retry can never double-charge"]
        P2["Webhook received<br/>verify its signature"]
        P3{"Provider event id<br/>already in inbox?"}
        P4["Duplicate: do nothing<br/>reply 200 OK"]
        P5["Save event id in inbox and update<br/>the payment record in ONE transaction"]
        P6{"Outcome?"}
        P7["Ask provider for a FULL refund<br/>idempotency key = refund + order id"]
        P8{"Provider accepted<br/>the refund?"}
        P9["Refund record DONE"]
        P10["Refund record RETRYING<br/>retry with growing delay<br/>a sweeper re-picks any unfinished refund"]
        P11["After N failed attempts: REFUND_FAILED<br/>alert the operations team<br/>record stays open and keeps being retried<br/>never dropped"]
    end

    %% ---------- Main flow ----------
    U0 -->|"HTTP"| O1
    O1 -->|"HTTP get cart"| C1
    C1 -->|"lines and prices"| O1
    O1 -->|"event ReserveStock<br/>order id, lines"| I1

    %% Short stock
    I1 -->|"no"| I2
    I2 -->|"event StockShort<br/>short items"| O2
    O2 --> U1

    %% Reserved
    I1 -->|"yes"| I3
    I3 -->|"event StockReserved"| O3
    O3 -->|"event ChargeRequested<br/>order id, total from snapshot"| P1
    P1 -->|"charge request"| PROV
    PROV -->|"webhook: succeeded or declined"| P2
    P2 --> P3
    P3 -->|"yes"| P4
    P3 -->|"no"| P5
    P5 --> P6

    %% Declined
    P6 -->|"declined"| O4
    P6 -.->|"event PaymentDeclined"| O4
    O4 --> U2
    O4 -->|"event ReleaseStock"| I4

    %% Succeeded
    P6 -->|"succeeded:<br/>event PaymentSucceeded"| O5
    O5 -->|"yes<br/>event ClaimStock"| I5
    I5 -->|"yes"| I6
    I6 -->|"event StockClaimed"| O6
    O6 --> U3
    O6 -->|"event OrderConfirmed"| C2

    %% Late success
    I5 -->|"no: late success"| I7
    I7 -->|"event StockClaimFailed"| O7
    O7 --> U4

    %% Success for an order that is no longer waiting for payment
    O5 -->|"no: order already cancelled<br/>or rejected"| P7

    %% Refund
    O7 -->|"event RefundRequested<br/>order id, full amount"| P7
    P7 --> P8
    P8 -->|"yes"| P9
    P9 -->|"event RefundCompleted"| O8
    O8 --> U5
    P8 -->|"no, error or timeout"| P10
    P10 -->|"try again"| P7
    P10 -->|"attempts used up"| P11
    P11 -.->|"operations fixes cause,<br/>retry resumes"| P7

    %% Expiry runs on its own
    IX -.->|"touches only HELD rows<br/>a claimed row is never released"| I3
```

## What each service stores

| Service | Stores | Never touches |
|---|---|---|
| Cart | Cart lines and current prices | Orders, stock, payments |
| Order | Orders, each with a frozen copy of the lines and prices, plus status and handled event ids | The cart's tables, stock tables |
| Inventory | Stock levels, plus one reservation per order id (HELD, CLAIMED or RELEASED, with an expiry time) | Orders, payments |
| Payment | One payment record per order id, refund records with retry state, and an inbox of provider event ids already processed | Orders, the cart |

Services only exchange data through the HTTP call and the events in the diagram.

## Order statuses

`PENDING_RESERVATION` goes to one of:
- `REJECTED_SHORT_STOCK` (end).
- `AWAITING_PAYMENT`, which goes to one of:
  - `PAYMENT_DECLINED` (end).
  - `CONFIRMED` (end).
  - `CANCELLED_OUT_OF_STOCK` (end, refund follows).

## Notes on each failure branch

**Short stock.**
- Inventory checks all lines and takes stock only if every line is available, in one transaction. If any line is short it reserves nothing and returns the list of short items.
- No payment is requested. The customer is told which items are short. The cart is untouched.

**Declined payment.**
- Payment reports `PaymentDeclined`. Order marks `PAYMENT_DECLINED` and asks Inventory to release the hold. If the hold has already lapsed, the release does nothing.
- The customer is told and can try again. The cart is unchanged. A new attempt creates a new order id, so it gets a new idempotency key.

**Late success after the hold lapsed.**
- The 10-minute hold can lapse while the provider is still working. The expiry sweep releases stock only from rows still `HELD`, and stock then goes back on sale.
- When `PaymentSucceeded` arrives, Order sends `ClaimStock`. Inventory claims only if the reservation is still `HELD` and not past its expiry. The check and the status change happen in one transaction.
- Expiry and claim are therefore mutually exclusive. A reservation is either claimed or released, never both.
- If the claim fails, Order marks `CANCELLED_OUT_OF_STOCK`, emails the customer, and sends `RefundRequested` for the full amount. The order is never shipped in part.
- This design does not try to re-reserve stock after a lapse, even if some happens to be free. That keeps the rule simple: no valid hold means no fulfilment. It could be added later as a deliberate change.

**Failed refund.**
- Refund requests use `refund + order id` as the idempotency key, so retries cannot refund twice. The refund record is saved before the provider is called.
- On error or timeout, the record goes to `RETRYING` and is retried with growing delays. A sweeper re-picks any unfinished refund, which also covers a crash between the save and the call.
- After N failed attempts, the record becomes `REFUND_FAILED` and the operations team is alerted. The record stays open and retries continue after the cause is fixed. Nothing is deleted or ignored until the provider confirms the refund.
- If the provider reports refund results by webhook, they go through the same inbox and duplicate check.

**Duplicate webhooks.**
- Payment verifies the signature, then, in one transaction, inserts the provider's event id into the inbox (unique key) and updates the payment record.
- If the insert finds the id already there, nothing happens and the reply is still `200 OK` so the provider stops resending.
- State changes are also one-way. A payment already `SUCCEEDED` cannot go to `DECLINED`.

**Success for an order that is no longer waiting.**
- If `PaymentSucceeded` arrives and the order is not `AWAITING_PAYMENT`, the money is refunded in full. This covers any order that was cancelled or rejected while the charge was in flight.

**Cart emptied only on confirmation.**
- Only `OrderConfirmed` makes Cart empty the cart. Every other end state leaves it exactly as it was.
- Emptying the cart is idempotent, so a redelivered event does nothing more.

## Other protections

- **Double click on Place order.** Order creation is keyed on the cart's checkout attempt, so a repeat returns the same order id instead of creating a second order.
- **Retried charge requests.** The idempotency key is always the order id, so a timeout followed by a retry cannot charge twice.
- **Lost webhook.** If no webhook has arrived after about 35 minutes, Payment asks the provider for the charge's status. It processes the answer through the same inbox path as a webhook.
- **Order of events.** Every handler checks the current status before acting. An out-of-order or repeated event is ignored or leads to a refund. It never causes a double charge or a lost refund.

## Open points to confirm

- The number of refund attempts (N) and the retry delays.
- Who receives the operations alert for `REFUND_FAILED`.
- Whether to re-reserve stock when a payment succeeds just after a lapse. This design says no.
