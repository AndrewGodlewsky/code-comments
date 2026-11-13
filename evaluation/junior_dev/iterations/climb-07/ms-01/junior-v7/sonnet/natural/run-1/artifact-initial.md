# Checkout across Cart, Inventory, Payment and Order

## How to read this

Order is the coordinator. It is the only service that tells the others what to do next, and it keeps the order's status. Each service writes to its own database only. Between services, "HTTP" means a direct call and "event" means a message on the shared broker.

Two rules apply to every event:
- **Outbox.** A service saves its state change and the event it wants to publish in one local transaction. A relay then sends the event. A crash cannot leave a state change without its event.
- **Idempotent consumers.** Every event carries the order id, and a repeat must have no extra effect. Each handler checks the current status before acting.

## Flowchart

```mermaid
flowchart TD
  CUST(["Customer presses Place order"])
  PROV(["Payment provider<br/>external"])
  OPS(["Ops alert and manual queue"])

  subgraph CART["Cart service"]
    K1["Return cart lines and prices<br/>read only, cart unchanged"]
    K2["Empty the cart<br/>only on OrderConfirmed"]
  end

  subgraph ORDER["Order service"]
    O1["Ask Cart for lines and prices"]
    O2["Save order PLACED<br/>with a frozen copy of lines and prices"]
    O3["Mark REJECTED_OUT_OF_STOCK<br/>tell customer which items are short<br/>cart untouched, no payment"]
    O4["Mark AWAITING_PAYMENT<br/>request charge"]
    O5["Mark PAYMENT_DECLINED<br/>tell customer, cart untouched"]
    O6["Mark PAID<br/>ask Inventory to claim the hold"]
    O7["Mark CONFIRMED"]
    O8["Mark CANCELLED_OUT_OF_STOCK<br/>email customer<br/>request full refund"]
    O9["Mark REFUNDED<br/>email refund confirmation"]
  end

  subgraph INV["Inventory service"]
    I1{"Every line<br/>in stock?"}
    I2["Hold all lines in one transaction<br/>status HELD, expires in 10 minutes"]
    I3["Reserve nothing<br/>return the list of short items"]
    I4["Release hold<br/>status RELEASED, stock back on sale"]
    I5{"Hold still HELD<br/>and not expired?"}
    I6["Mark hold CLAIMED<br/>stock is sold to this order"]
    I7["Expiry sweeper every minute<br/>unclaimed holds past 10 min become EXPIRED<br/>stock back on sale"]
  end

  subgraph PAY["Payment service"]
    P1["Save payment PENDING<br/>charge provider with idempotency key = order id<br/>retry uses the same key"]
    P2{"Webhook event id<br/>already processed?"}
    P3["Reply 200, do nothing"]
    P4{"Outcome"}
    P5["Save DECLINED and event id<br/>publish PaymentDeclined"]
    P6["Save SUCCEEDED and event id<br/>publish PaymentSucceeded"]
    P7["Save refund REQUESTED before calling provider<br/>refund full amount, key = refund-order id"]
    P8{"Provider accepted<br/>refund?"}
    P9["Save refund DONE<br/>publish RefundCompleted"]
    P10["Save refund RETRYING<br/>retry job with backoff<br/>never deleted"]
    P11["After N tries: REFUND_FAILED<br/>stays open, retried daily"]
  end

  CUST --> O1
  O1 -->|"HTTP"| K1
  K1 -->|"lines and prices"| O2
  O2 -->|"HTTP reserve<br/>order id and lines"| I1
  I1 -->|"no"| I3
  I3 -->|"HTTP reply: short items"| O3
  I1 -->|"yes"| I2
  I2 -->|"HTTP reply: reserved"| O4
  O4 -->|"event ChargeRequested<br/>order id and amount"| P1
  P1 -->|"charge request"| PROV
  PROV -->|"webhook, seconds to 30 min<br/>may arrive more than once"| P2
  P2 -->|"yes, duplicate"| P3
  P2 -->|"no, first time"| P4
  P4 -->|"declined"| P5
  P4 -->|"succeeded"| P6
  P5 -->|"event PaymentDeclined"| O5
  O5 -->|"event ReleaseHold"| I4
  P6 -->|"event PaymentSucceeded"| O6
  O6 -->|"HTTP claim by order id"| I5
  I5 -->|"yes"| I6
  I6 -->|"HTTP reply: claimed"| O7
  O7 -->|"event OrderConfirmed"| K2
  I5 -->|"no, hold lapsed"| O8
  I7 -.->|"sets EXPIRED"| I5
  O8 -->|"event RefundRequested"| P7
  P7 -->|"refund request"| PROV
  PROV -->|"response"| P8
  P8 -->|"yes"| P9
  P8 -->|"no or timeout"| P10
  P10 -->|"retry"| P7
  P10 -->|"retries used up"| P11
  P11 --> OPS
  P9 -->|"event RefundCompleted"| O9
```

Reading the picture: the solid path down the middle is the happy path. Each failure branch ends in a status that the customer can see and that leaves the cart as it was.

## Step by step

| Step | Service | Trigger | What happens |
|---|---|---|---|
| 1 | Order | Customer presses Place order | Fetches cart lines and prices from Cart, saves the order with a frozen copy. Later cart edits or price changes do not touch it. |
| 2 | Inventory | HTTP reserve from Order | Checks all lines and holds all of them in one transaction, or none. The hold expires 10 minutes later. |
| 3 | Payment | ChargeRequested event | Saves the payment, then asks the provider to charge. The idempotency key is the order id, so a retry cannot charge twice. |
| 4 | Payment | Provider webhook | Checks the provider's event id against its processed list. A duplicate gets a 200 reply and nothing else. Otherwise it stores the outcome and the event id in one transaction, then publishes the result. |
| 5 | Order | PaymentSucceeded | Asks Inventory to claim the hold. |
| 6 | Inventory | HTTP claim | Succeeds only if the hold is HELD and its expiry time has not passed. Claim and expiry both use a conditional status update, so exactly one of them wins. |
| 7 | Order, Cart | Claim succeeded | Order becomes CONFIRMED and publishes OrderConfirmed. Cart empties on that event, and only then. |

## Failure branches

| Case | What happens | Cart | Money |
|---|---|---|---|
| **Short stock** | Inventory reserves nothing and replies with the short items. Order marks REJECTED_OUT_OF_STOCK and tells the customer which items. Payment is never contacted. | Unchanged | None taken |
| **Declined payment** | Payment publishes PaymentDeclined. Order marks PAYMENT_DECLINED, tells the customer, and sends ReleaseHold so the stock returns at once rather than after 10 minutes. | Unchanged | None taken |
| **Late success** (hold lapsed and stock sold on) | The sweeper has set the hold to EXPIRED, or the claim arrives after the expiry time. The claim is refused. Order marks CANCELLED_OUT_OF_STOCK, emails the customer and publishes RefundRequested for the full amount. | Unchanged | Full refund |
| **Refund fails at the provider** | The refund row is saved as REQUESTED before the provider is called, so it exists even if we crash. A failure or timeout moves it to RETRYING, and a retry job repeats the call with backoff. The refund key is stable (refund-order id), so a retry cannot refund twice. After N attempts it becomes REFUND_FAILED, raises an ops alert and stays in the retry job's list. A refund is never deleted or skipped. | Unchanged | Refund pending until it succeeds |
| **Duplicate webhook** | The provider's event id is stored with the outcome in one transaction. A second delivery finds the id, replies 200 and does nothing. A unique constraint on the id also covers two deliveries arriving at the same moment. | n/a | n/a |

## What each service stores

| Service | Data it owns |
|---|---|
| **Cart** | Cart lines for each customer. It is changed by the customer's edits and by OrderConfirmed. It keeps no copy of order data. |
| **Order** | Orders with status (PLACED, REJECTED_OUT_OF_STOCK, AWAITING_PAYMENT, PAYMENT_DECLINED, PAID, CONFIRMED, CANCELLED_OUT_OF_STOCK, REFUNDED), the frozen lines and prices, the total, and an outbox. |
| **Inventory** | Stock levels. Reservations keyed by order id with lines, status (HELD, CLAIMED, RELEASED, EXPIRED) and expiry time. An outbox. |
| **Payment** | Payments by order id (unique), with status and provider reference. Processed webhook event ids (unique). Refunds with status and attempt count. An outbox. |

## Decisions and assumptions to check

- **Late-arriving payment is normal, not rare.** The hold lasts 10 minutes and the provider can take 30, so any payment slower than 10 minutes risks this path. If it is common, consider a longer hold or a re-reserve attempt before refunding. As specified, we refund and cancel.
- **Expiry is strict.** A claim at or after the expiry time is refused even if the sweeper has not run yet. This keeps the outcome the same whether or not the sweeper is late.
- **Out-of-order events.** If PaymentSucceeded reaches an order that is not AWAITING_PAYMENT, for example already cancelled, Order requests a refund rather than ignoring the money.
- **Email.** The brief does not name an email service. I assume Order sends the emails through the company's existing mailer. Retrying an email must not block the refund.
- **One open checkout per cart** is assumed. A second press of Place order while an order is awaiting payment should be rejected or should reuse the open order. This is not specified, so confirm it.
- **Retry limit N and alerting** for failed refunds need numbers and an owner.
