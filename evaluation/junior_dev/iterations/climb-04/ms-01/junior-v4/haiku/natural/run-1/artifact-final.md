# Checkout across Cart, Inventory, Payment and Order

Checkout moves out of the monolith into four services. Order drives the flow. Inventory holds and sells stock. Payment is the only service that talks to the payment provider. Each service keeps its own database and talks to the others over HTTP or the message broker.

The main flow: Place order snapshots the cart, reserves stock, charges the customer and waits for the provider's webhook. On success, Order claims the stock and confirms the order. Checkout ends in one of three places: a confirmed order, a cancelled order with a full refund, or a stopped checkout with the cart unchanged.

## Terms

- **Hold:** stock set aside for one order for 10 minutes. It is not sold yet.
- **Claim:** turns a hold into sold stock.
- **Idempotency key:** a value sent with a request. The receiver does the work once per key, so a repeat is safe. Every call in this flow uses the order id as its key.
- **Outbox:** a table in a service's own database. A service writes an event row in the same transaction as its state change. A background relay publishes it to the broker. An event is never published without its state change, and never lost after it.
- **Retry job:** a job in Order that runs every minute and resends each reserve, charge or claim call that has no answer yet, with the same key.
- **Webhook:** the provider's HTTP call to Payment that reports a charge result.
- **Open order:** an order with status PENDING_STOCK or AWAITING_PAYMENT. Any other status is closed. A cart has at most one open order.

## Flowchart

Dashed arrows are timers or background jobs, not customer actions.

```mermaid
flowchart TD
    CUST(["Customer presses Place order"])

    subgraph CART ["Cart service"]
        C1["Send cart id, lines and prices to Order<br/>stores: carts, cart_lines (read only)"]
        C2["On OrderConfirmed: remove ordered lines still unchanged<br/>idempotent on order id<br/>stores: cart_lines"]
    end

    subgraph ORDER ["Order service"]
        O1{"Open order on this cart?"}
        O2["Create order PENDING_STOCK<br/>snapshot lines and prices<br/>stores: orders, order_lines, order_status_history"]
        O3["Ask Inventory to reserve all lines, key = order id<br/>save reservation id on the order"]
        O4["Status FAILED_SHORT_STOCK<br/>short items shown to customer"]
        O5["Status AWAITING_PAYMENT<br/>ask Payment to charge, key = order id"]
        O6["Status FAILED_PAYMENT<br/>one call to Inventory to release hold, not retried"]
        O7["Ask Inventory to claim the reservation"]
        O8["Status CONFIRMED<br/>outbox: OrderConfirmed and confirmation email"]
        O9["Status CANCELLED_OUT_OF_STOCK<br/>outbox: OrderCancelledOutOfStock and cancellation email"]
        RETRY["Retry job, every minute<br/>resends unanswered reserve, charge or claim, same key"]
    end

    subgraph INV ["Inventory service"]
        I0{"Order already has a HELD or CLAIMED reservation?"}
        I1{"Every line has enough free stock?"}
        I2["Write nothing, return short items (409)"]
        I3["Create reservation HELD, expires in 10 min<br/>stores: reservations, reservation_lines, held counts"]
        I4["Claim: HELD becomes CLAIMED, held stock becomes sold<br/>stores: reservations, stock"]
        I5{"Reservation still HELD?"}
        I6{"Same lines free now? Re-reserve and claim in one transaction"}
        I7["Claim refused, write nothing, return short items"]
        I8["Release: HELD becomes RELEASED, stock back on sale"]
        I9["Sweeper every minute: HELD past expiry becomes EXPIRED, stock back on sale"]
    end

    subgraph PAY ["Payment service (only service that talks to the provider)"]
        P0{"Signature valid?"}
        P1["Insert payment row PENDING, unique on order id<br/>stores: payments"]
        P2["Charge provider with Idempotency-Key = order id"]
        P3{"Event id already in webhook_events?"}
        P4["Record event id, unique, so a racing repeat counts as a repeat<br/>stores: webhook_events"]
        P5{"Payment status when event arrives"}
        P6["Guarded update to SUCCEEDED or DECLINED<br/>outbox row in same transaction<br/>stores: payments, outbox"]
        P6N["Treat as DECLINED, outbox publishes PaymentDeclined<br/>stores: payments, outbox"]
        P7["Set LATE_SUCCESS<br/>stores: payments"]
        P8["Watchdog: poll provider for charge status"]
        P9["Save refund row REFUND_PENDING, key = order id<br/>stores: refunds"]
        P10["Refund full amount on the charge id in this order's payment row"]
        P11{"Refund succeeded?"}
        P12["Refund SUCCEEDED"]
        P13["Retry with backoff, same key<br/>after last attempt: REFUND_FAILED, ops alert"]
    end

    PROV(["Payment provider"])
    WAIT(["Order waits in AWAITING_PAYMENT"])
    EXIST(["Return existing order, no new hold or charge"])
    STOP_SHORT(["Stop: cart unchanged, customer sees short items, can retry"])
    STOP_NOOP(["Return 200, change nothing"])
    PX(["Reject with 401, nothing stored"])
    STOP_DEC(["Stop: customer told payment declined, cart unchanged, can retry"])
    STOP_OK(["Success: order CONFIRMED, cart lines removed"])
    STOP_REF(["Stop: refund done, order stays cancelled, customer emailed"])
    OPS(["Ops alert: refund REFUND_FAILED, row stays open until resolved"])

    CUST --> C1
    C1 -->|"POST /orders with cart id, lines and prices"| O1
    O1 -->|"AWAITING_PAYMENT"| EXIST
    O1 -->|"PENDING_STOCK: resend reserve now"| O3
    O1 -->|"none open"| O2
    O2 -->|"racing duplicate rejected by unique rule"| O1
    O2 --> O3
    O3 -->|"POST /reservations, all or nothing"| I0

    I0 -->|"yes: return existing reservation id"| O5
    I0 -->|"no"| I1
    I1 -->|"no, a line is short"| I2
    I2 -->|"409 with short items"| O4
    O4 --> STOP_SHORT
    I1 -->|"yes"| I3
    I3 -->|"reservation id returned"| O5
    I3 -.->|"no claim within 10 min"| I9

    O5 -->|"POST /charges, Idempotency-Key = order id"| P1
    P1 --> P2
    P2 --> PROV
    P2 -->|"202 PENDING"| WAIT
    P2 -.->|"no webhook after 35 min"| P8
    P8 -->|"poll"| PROV
    PROV -.->|"still pending: poll again in 5 min"| P8
    PROV -.->|"poll has a status: synthetic event id"| P3
    PROV -.->|"poll: no record of charge"| P6N
    PROV -->|"webhook: succeeded or declined, up to 30 min, may repeat"| P0

    P0 -->|"no"| PX
    P0 -->|"yes"| P3
    P3 -->|"yes, duplicate"| STOP_NOOP
    P3 -->|"no, new event"| P4
    P4 --> P5
    P5 -->|"PENDING"| P6
    P5 -->|"DECLINED, event says succeeded"| P7
    P5 -->|"SUCCEEDED, or event says declined"| STOP_NOOP

    P6 -->|"DECLINED: outbox publishes PaymentDeclined"| O6
    P6 -->|"SUCCEEDED: outbox publishes PaymentSucceeded"| O7
    P6N -->|"outbox publishes PaymentDeclined"| O6
    O6 -->|"POST /reservations/id/release, one call"| I8
    I8 --> STOP_DEC

    O7 -->|"POST /reservations/id/claim"| I5
    I5 -->|"yes, on time"| I4
    I5 -->|"no, expired or swept"| I6
    I6 -->|"yes"| I4
    I6 -->|"no"| I7
    I7 -->|"claim refused, with short items"| O9
    I4 -->|"CLAIMED"| O8
    O8 -->|"OrderConfirmed event"| C2
    O8 --> STOP_OK

    P7 --> P9
    O9 -->|"OrderCancelledOutOfStock event"| P9
    P9 --> P10
    P10 --> PROV
    PROV -->|"refund result, sync or webhook"| P11
    P11 -->|"yes"| P12
    P12 --> STOP_REF
    P11 -->|"no or error"| P13
    P13 -->|"retry, same key"| P10
    P13 -->|"after last attempt"| OPS

    RETRY -.->|"unanswered reserve"| I0
    RETRY -.->|"unanswered charge"| P1
    RETRY -.->|"unanswered claim"| I5

    classDef stop fill:#f4f4f4,stroke:#777,color:#222
    classDef bad fill:#fde8e8,stroke:#b42318,color:#4a0d0d
    class STOP_SHORT,STOP_NOOP,STOP_DEC,STOP_OK,STOP_REF,EXIST,PX,WAIT stop
    class OPS,P13 bad
```

## Steps

Each step lists what starts it, what it does, which service keeps its data, and what happens when it goes wrong.

1. **Place order.**
   - Starts: the customer presses Place order.
   - Does: Cart sends its id, lines and prices to Order. Order looks for an open order on this cart. If one is AWAITING_PAYMENT, Order returns it and makes no new hold or charge. If one is PENDING_STOCK, Order resends the reserve call now. If none is open, Order creates an order with status PENDING_STOCK and a snapshot of the lines and prices. Later cart edits and price changes do not change this snapshot.
   - Keeps data: Order (orders, order_lines, order_status_history).
   - If it goes wrong: a second Place order that races the first hits the unique rule on cart id and follows the same open-order check.

2. **Reserve stock.**
   - Starts: step 1 creates an order, or the retry job finds an unanswered reserve.
   - Does: Order asks Inventory to reserve all lines, keyed on the order id. If the order already has a HELD or CLAIMED reservation, Inventory returns it and makes no new hold. Otherwise Inventory checks every line in one transaction. If any line is short, it writes nothing and returns the short items. If every line is free, it creates a HELD reservation that expires in 10 minutes. Order saves the reservation id on the order.
   - Keeps data: Inventory (reservations, reservation_lines, stock). Order (the reservation id).
   - If it goes wrong: if a line is short, Order sets FAILED_SHORT_STOCK and shows the short items. Nothing is held or charged, and the cart is unchanged. A lost reply is resent by the retry job with the same key.

3. **Charge the customer.**
   - Starts: Order has saved the reservation id.
   - Does: Order sets AWAITING_PAYMENT and asks Payment to charge, keyed on the order id. Payment inserts a PENDING payment row, unique on order id, and charges the provider with the order id as the idempotency key. Payment replies 202 PENDING, and Order waits for the webhook. The customer sees "Awaiting payment".
   - Keeps data: Payment (payments).
   - If it goes wrong: if the provider refuses before it accepts the charge, Payment returns an error and the retry job resends with the same key. If the reply is lost, the unique payment row returns the same payment.

4. **Receive the outcome.**
   - Starts: the provider's webhook. If no webhook arrives 35 minutes after the charge, the watchdog starts and polls the provider.
   - Does: Payment checks the signature first. If the event id is already recorded, Payment changes nothing. Otherwise it records the event id and applies the change only if the payment is in the state the event expects. A PENDING payment becomes SUCCEEDED or DECLINED. A DECLINED payment that receives a success event becomes LATE_SUCCESS. Any other case changes nothing. Each applied change writes one outbox row in the same transaction.
   - Watchdog: if the charge is still pending, the watchdog polls again in 5 minutes, and Order keeps waiting. If the provider returns a status, Payment treats it like a webhook, using a synthetic event id made of the charge id and the status. If the provider has no record of the charge, Payment treats the charge as DECLINED and publishes PaymentDeclined.
   - Keeps data: Payment (webhook_events, payments, outbox).
   - If it goes wrong: an invalid signature is rejected with 401 and nothing is stored. A repeated event is acknowledged and changes nothing. Two copies that race are handled by the unique constraint on the event id, so only one is processed.

5. **Payment declined.**
   - Starts: the PaymentDeclined event from Payment's outbox.
   - Does: Order acts only while the order is AWAITING_PAYMENT. It sets FAILED_PAYMENT and makes one call to Inventory to release the hold. The customer sees "Payment declined" and the cart is unchanged. The customer can press Place order again, which starts a new order with a new key.
   - Keeps data: Order (orders, order_status_history). Inventory (reservations).
   - If it goes wrong: if the release gets no answer, it is not retried. The sweeper frees the hold within 10 minutes.

6. **Payment succeeded: claim the stock.**
   - Starts: the PaymentSucceeded event from Payment's outbox. Order acts only while the order is AWAITING_PAYMENT.
   - Does: Order asks Inventory to claim the reservation. If the reservation is still HELD, Inventory marks it CLAIMED and the held stock becomes sold. If the hold has expired or been swept, Inventory tries once to re-reserve and claim the same lines in one transaction. If the lines are still free, the claim succeeds. If not, Inventory writes nothing and returns the short items.
     - On success, Order sets CONFIRMED and writes an OrderConfirmed event and a confirmation email row in the same transaction. Cart then removes each ordered line that still matches the snapshot. Lines added or changed after Place order stay in the cart.
     - On short stock, Order sets CANCELLED_OUT_OF_STOCK and writes an OrderCancelledOutOfStock event and a cancellation email row in the same transaction. This starts step 7.
   - Keeps data: Inventory (reservations, stock). Order (orders, outbox).
   - If it goes wrong: a lost claim reply is resent by the retry job. A claim on a CLAIMED reservation returns CLAIMED.

7. **Refund a cancelled order.**
   - Starts: the OrderCancelledOutOfStock event, or LATE_SUCCESS from step 4.
   - Does: Payment saves a refund row (REFUND_PENDING, keyed on the order id) before it calls the provider. It refunds the full amount on the charge id stored in this order's own payment row. On success the refund row becomes SUCCEEDED. Order is not told, and the order stays CANCELLED_OUT_OF_STOCK.
   - Keeps data: Payment (refunds, payments).
   - If it goes wrong: a failed refund is retried with backoff, using the same key. After the last attempt the row becomes REFUND_FAILED and an ops alert is raised. The row stays open until someone resolves it. A repeated event finds the same row and starts nothing new.

## Notes

- **Retry job.** It runs every minute in Order. For each call, it stops once that call gets an answer. Each call is safe to repeat. Order never cancels or refunds because a call timed out. While the job retries, the status does not change: "Checking stock" during reserve, and "Awaiting payment" during charge and claim.
- **Customer page.** The page asks Order for the status every 10 seconds while the order is open, then stops. Order pushes nothing. The page never calls Payment.
- **Emails.** Order writes each email to its outbox in the same transaction as the status change. A mailer job sends it and retries until the send succeeds. If Order crashes after sending but before marking the row sent, the customer may get one duplicate email.
- **Slow broker.** The cart can still show ordered items for a short time after confirmation. The order id makes this safe.

## What happens when things fail

| Failure | What happens | Customer sees |
|---|---|---|
| A line is short | Nothing reserved or charged. Order sets FAILED_SHORT_STOCK. | Short items listed, cart unchanged |
| Payment declined | Hold released, or swept within 10 minutes | "Payment declined", cart unchanged, can retry |
| Success after hold lapsed, same lines still free | Inventory re-reserves and claims, order confirmed | Confirmation email |
| Success after hold lapsed, lines gone | Claim refused, order cancelled, full refund | Cancellation and refund email |
| Success after a no-record decline | Payment sets LATE_SUCCESS, full refund | Nothing yet (see open questions) |
| Refund fails at provider | Retry with backoff, then REFUND_FAILED and ops alert | Cancellation email; refund still open |
| Duplicate or racing webhook | Acknowledged, nothing changed | Nothing |
| Invalid webhook signature | Rejected with 401, nothing stored | Nothing |
| Charge fails before provider accepts it | Payment returns an error; retry job resends with same key | "Awaiting payment" |
| Reserve, charge or claim reply lost | Retry job resends with the same key | "Checking stock" or "Awaiting payment" |
| Charged, but Order never got the reply | Webhook still reaches Payment, which publishes the outcome | Same as the outcome |
| No webhook 35 min after charge | Watchdog polls the provider | Same as the outcome found |
| Provider has no record of the charge | Treated as declined | "Payment declined", cart unchanged |
| Broker slow | Events arrive late | Cart may show ordered items briefly |

## What each service stores

| Service | Owns | Notes |
|---|---|---|
| Cart | carts, cart_lines | Written only by customer edits and the OrderConfirmed consumer. Never read by other services. |
| Order | orders (including reservation id), order_lines (price snapshot), order_status_history, outbox | Holds checkout state, the open-order check and the email rows. |
| Inventory | stock, reservations, reservation_lines | Hold, claim, release and expiry are all state changes on reservations. |
| Payment | payments (PENDING, SUCCEEDED, DECLINED or LATE_SUCCESS), webhook_events, refunds, outbox | webhook_events gives duplicate protection. refunds gives refund durability. |

## Open questions

- **Claim at payment success, not at reservation.** Stock is held only while payment is pending. The cost is that a payment finishing after the hold lapses can be cancelled even when the stock is still free. Extending the hold to about 35 minutes would avoid most of these cancellations, but locks stock longer after declines. The brief fixes the hold at 10 minutes, so this design does not extend it. Confirm the business accepts this.
- **Late success retries the reservation once.** If the same lines are still free, the order is fulfilled. Otherwise the customer is refunded. Confirm the business wants this, not an immediate refund.
- **Refund outcome channel.** The brief covers charge webhooks only. This design assumes refunds return a synchronous result or a webhook handled by the same dedupe path. Confirm with the provider.
- **No record means declined.** At the watchdog poll, no record means no money was taken under that key, so the charge is treated as declined. Confirm with the provider that no charge will follow a missing record. A charge still in flight could succeed later, and step 7 covers that refund.
- **Email ownership.** Order sends the confirmation and cancellation emails. Confirm that no separate notifications service is planned.
- **Cart keeps later edits.** On success, Cart removes only the ordered lines that are still unchanged. Confirm the business wants this rather than emptying the whole cart.
- **Retry job limit.** The brief sets no limit on how long the retry job keeps resending a call with no answer before it alerts ops.
- **Pending charge limit.** The brief sets no limit on how long a charge may stay pending before ops is alerted. The order waits until the provider answers.
- **Email after a no-record decline.** If a charge succeeds after a no-record decline, the customer is refunded but this design sends no email. Confirm whether they should be emailed.
- **Refund after the last attempt.** The row stays open until someone resolves it. Confirm whether ops should also retry automatically after the last attempt.
- **Payment details.** The brief does not say how the customer's payment details are captured and passed to the provider.