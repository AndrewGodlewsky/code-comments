# Checkout across Cart, Inventory, Payment and Order

## How to read this

Four services. Each owns its own database and never reads another's tables. They talk in two ways:

- **Solid arrows** are synchronous HTTP calls.
- **Dotted arrows** are events on the shared message broker.
- **Diamonds** are decisions.
- Each box sits in the lane of the service that does the work.
- The payment provider is outside our system. It talks only to Payment.

The **Order** service is the coordinator. It decides what happens next at each step. The other three services do one job each and report back.

## Flowchart

```mermaid
flowchart TD
  START(["Customer presses Place order"])

  subgraph CART["CART service"]
    C1["Snapshot cart lines and prices<br/>as they are right now<br/>(cart is NOT changed)"]
    C2["Empty the cart"]
    C3(["Cart left exactly as it was<br/>customer can try again"])
  end

  subgraph ORDER["ORDER service"]
    O1["Create order, status PENDING<br/>store the snapshot of lines and prices<br/>this fixes the order id"]
    O2["Ask Inventory to reserve all lines"]
    O3{"All lines reserved?"}
    O4["Status REJECTED_OUT_OF_STOCK<br/>tell customer which items are short<br/>no payment is requested"]
    O5["Status AWAITING_PAYMENT<br/>ask Payment to charge the snapshot total<br/>customer sees Processing and the page polls order status"]
    O6["Status PAYMENT_FAILED<br/>tell customer the payment was declined<br/>publish OrderFailed"]
    O7["Ask Inventory to claim the stock"]
    O8{"Claim accepted?"}
    O9["Status CONFIRMED<br/>publish OrderConfirmed"]
    O10["Status CANCELLED_OUT_OF_STOCK<br/>publish RefundRequested<br/>email customer: out of stock, full refund on the way"]
    O11["Record refund done<br/>email customer: refund issued"]
  end

  subgraph INV["INVENTORY service"]
    I1["Reserve in ONE database transaction<br/>every line or none<br/>hold lasts 10 min, record expires_at"]
    I2["Some line is short<br/>nothing reserved<br/>return the list of short items"]
    I3{"Claim: is the hold still HELD<br/>and not past expires_at?<br/>checked in one transaction"}
    I4["Hold becomes CLAIMED<br/>stock is sold for good"]
    I5["Refuse claim: hold lapsed<br/>the stock was already back on sale<br/>and may be sold to someone else"]
    I6["Timer runs every minute<br/>HELD holds past 10 min become EXPIRED<br/>stock goes back on sale"]
    I7["Release the hold<br/>stock goes back on sale<br/>safe to repeat, does nothing if already released"]
  end

  subgraph PAY["PAYMENT service"]
    P1["Store payment PENDING<br/>request charge from provider<br/>idempotency key = order id"]
    P2["Receive provider webhook<br/>seconds to 30 min later<br/>may arrive more than once"]
    P3{"Provider event id<br/>already processed?"}
    P4["Reply 200 and do nothing<br/>duplicate is ignored"]
    P5{"Outcome?"}
    P6["Store DECLINED and the event id<br/>in one transaction<br/>publish PaymentDeclined"]
    P7["Store SUCCEEDED and the event id<br/>in one transaction<br/>publish PaymentSucceeded"]
    P8["Create refund record REQUESTED<br/>one per order id, so a repeat is a no-op"]
    P9["Ask provider to refund the full amount<br/>idempotency key = order id"]
    P10{"Provider accepted refund?"}
    P11["Refund record REFUNDED<br/>publish RefundCompleted"]
    P12["Refund record stays open<br/>record attempt and error<br/>retry with backoff, never give up<br/>after N tries alert a person"]
  end

  subgraph EXT["PAYMENT PROVIDER (external)"]
    X1["Takes the charge and refund requests<br/>later reports the outcome by webhook"]
  end

  START --> C1
  C1 -->|"HTTP: snapshot"| O1
  O1 --> O2
  O2 -->|"HTTP: reserve"| I1
  I1 --> O3
  I1 -.->|"any line short"| I2
  I2 --> O3
  O3 -->|"no"| O4
  O3 -->|"yes"| O5
  O4 --> C3

  O5 -->|"HTTP: charge"| P1
  P1 -->|"HTTP: charge, key = order id"| X1
  X1 -.->|"webhook"| P2
  P2 --> P3
  P3 -->|"yes"| P4
  P3 -->|"no"| P5
  P5 -->|"declined"| P6
  P5 -->|"succeeded"| P7

  P6 -.->|"event: PaymentDeclined"| O6
  O6 -.->|"event: OrderFailed"| I7
  O6 --> C3

  P7 -.->|"event: PaymentSucceeded"| O7
  O7 -->|"HTTP: claim"| I3
  I3 -->|"yes"| I4
  I3 -->|"no"| I5
  I4 --> O8
  I5 --> O8
  O8 -->|"yes"| O9
  O9 -.->|"event: OrderConfirmed"| C2

  O8 -->|"no: late success"| O10
  O10 -.->|"event: RefundRequested"| P8
  O10 --> C3
  P8 --> P9
  P9 -->|"HTTP: refund, key = order id"| X1
  P9 --> P10
  P10 -->|"yes"| P11
  P10 -->|"no or timeout"| P12
  P12 -->|"retry"| P9
  P11 -.->|"event: RefundCompleted"| O11

  I6 -.->|"hold unclaimed after 10 min"| I5
```

The timer box (`I6`) feeds the lapsed-hold path. After a hold expires, the next claim for that order finds it EXPIRED and refuses.

## What triggers each step

| Step | Triggered by |
|---|---|
| Cart snapshots and sends to Order | Customer presses **Place order** |
| Order asks Inventory to reserve | Order created |
| Order asks Payment to charge | Inventory says every line is reserved |
| Payment starts processing an outcome | Provider webhook |
| Order marks the order failed | `PaymentDeclined` event |
| Order asks Inventory to claim | `PaymentSucceeded` event |
| Cart empties | `OrderConfirmed` event, and nothing else |
| Payment starts a refund | `RefundRequested` event |
| Inventory releases a hold | `OrderFailed` event, or the 10-minute timer |
| Order emails the customer | Out-of-stock cancellation, and again when `RefundCompleted` arrives |

## What each service stores

| Service | Its own database holds |
|---|---|
| **Cart** | Carts and their lines and prices. It is edited only by the customer, and emptied only on `OrderConfirmed`. |
| **Order** | Orders with a frozen copy of the lines and prices from the moment of **Place order**, the total, and the status: `PENDING`, `AWAITING_PAYMENT`, `CONFIRMED`, `REJECTED_OUT_OF_STOCK`, `PAYMENT_FAILED`, `CANCELLED_OUT_OF_STOCK`. It also holds an outbox of events waiting to be published. |
| **Inventory** | Stock levels per item. Reservations: order id, lines, `expires_at`, and status `HELD`, `CLAIMED`, `EXPIRED` or `RELEASED`. |
| **Payment** | Payments: order id, amount, provider reference, and status `PENDING`, `SUCCEEDED` or `DECLINED`. Refunds: order id, status `REQUESTED`, `REFUNDED` or a stuck-and-retrying state, attempt count, last error. Processed provider event ids, with a unique constraint. |

## The failure branches

1. **Short stock.** Inventory reserves all-or-nothing in one transaction. If any line is short, it reserves nothing and returns the short items. Order marks the order `REJECTED_OUT_OF_STOCK` and tells the customer which items are short. Payment is never called. The cart is untouched.
2. **Declined payment.** The provider's webhook says declined. Payment stores it and publishes `PaymentDeclined`. Order marks the order `PAYMENT_FAILED` and publishes `OrderFailed`, and Inventory releases the hold straight away. The cart is untouched. The customer can press **Place order** again. That creates a new order with a new id, so it gets a fresh idempotency key.
3. **Late success after the hold lapsed.** This is the bad case.
   - Payment succeeds, for example 20 minutes after Place order.
   - Order asks Inventory to claim the stock.
   - The hold expired at 10 minutes, so Inventory refuses.
   - Order marks the order `CANCELLED_OUT_OF_STOCK`, publishes `RefundRequested`, and emails the customer.
   - Payment refunds the full amount automatically.
   - No partial order is ever shipped. The cart is untouched.
4. **Failed refund.** The refund record is written to Payment's database before the provider is called, so the obligation exists even if the call fails. A failed or timed-out refund leaves the record open. A retry job re-attempts it with backoff and never gives up. After N failures it also alerts a person. Because the key is the order id, a retry cannot refund twice. The record becomes `REFUNDED` only when the provider confirms.
5. **Duplicate webhooks.** The provider's event id is inserted into the processed-events table in the same database transaction that updates the payment. A unique constraint means a repeat delivery fails the insert. Payment replies 200 and does nothing. No second event is published and no second refund is created.

## Design rules that make this safe

- **Idempotency key is the order id.** Every charge request carries it, so a retried request cannot charge twice. The refund request uses the same key.
- **The hold and the claim race is closed.** Inventory checks `expires_at` inside the claim transaction itself, so the claim does not depend on the timer having run. A hold is either claimed in time or lost, never both.
- **Events are published through an outbox.** Each service writes the event to its own database in the same transaction as the state change. A relay then publishes it. This avoids a state change with no event, or the reverse.
- **Every consumer is safe to run twice.** Brokers deliver at least once. Order only moves an order forward from the status it expects, Inventory release and claim are idempotent per order id, and Payment dedupes as above.
- **Cart is emptied in exactly one place.** That is the `OrderConfirmed` handler. Every failure path ends with the cart unchanged.

## Assumptions to confirm

- **Email.** Order sends the customer emails through whatever mail service you already use. This is not one of the four services.
- **Lapsed hold, stock still free.** If a hold has lapsed but nobody has bought the stock yet, the claim still fails and the customer is refunded. This is simpler and predictable. The alternative is to re-reserve at claim time.
- **Silent provider.** If no webhook arrives about 35 minutes after the charge, Payment should ask the provider for the status by order id. Otherwise the order would wait forever. This is not in the diagram.
- **Cart edits during checkout.** The cart is emptied on confirmation even if the customer added items after pressing Place order. Say if you would rather remove only the lines that were ordered.
