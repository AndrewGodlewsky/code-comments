# Checkout across Cart, Inventory, Payment and Order

## How to read this

- Order is the coordinator. It starts each step and records the order's state. The other three services each do one job and report back.
- Solid arrows are calls or events between services. Dotted arrows come from outside, either the payment provider's webhook or a timer.
- Each service has its own database. A service never reads another service's tables.
- Every state change that has to tell another service is written in the same database transaction as an outbox row. A relay then publishes it to the broker. This means a crash can't leave a state change without its event.
- Consumers of events and webhooks are idempotent. A repeated message changes nothing.

## Flowchart

```mermaid
flowchart TD
  subgraph CUS["Customer"]
    C1["Presses Place order"]
    C2["Told which items are short. Nothing reserved, no payment asked for"]
    C3["Told payment declined. Cart unchanged, can retry"]
    C4["Told order confirmed"]
    C5["Email: cancelled as out of stock, full refund on its way"]
  end

  subgraph CART["Cart service - DB: carts, cart_lines"]
    K1["Return current lines and prices"]
    K2["Empty the cart. Runs only on OrderConfirmed. Safe to repeat"]
  end

  subgraph ORD["Order service - DB: orders, order_lines snapshot, status history, outbox"]
    O1["Receive Place order with cart id. A second press returns the existing open order"]
    O2["Save order PENDING with a snapshot of lines and prices. Later cart or price changes do not touch it"]
    O3["Mark REJECTED_OUT_OF_STOCK"]
    O4["Mark AWAITING_PAYMENT. No timer cancels it, because the provider can take 30 minutes"]
    O5["Mark CANCELLED_PAYMENT_DECLINED"]
    O6{"PaymentSucceeded arrives. Is the order still AWAITING_PAYMENT?"}
    O7["Ask Inventory to claim the stock"]
    O8["Mark CONFIRMED"]
    O9["Mark CANCELLED_OUT_OF_STOCK and send the customer email"]
    O10["Request a full refund"]
    O11["Record refund completed"]
  end

  subgraph INV["Inventory service - DB: stock levels, reservations, reservation_lines"]
    I1{"Reserve all lines in one transaction. Is every line in stock?"}
    I2["Create reservation HELD with expires_at = now + 10 min. Stock set aside"]
    I3["Reserve nothing. Return the list of short items"]
    I4["Timer, every minute: HELD past expires_at becomes EXPIRED. Stock goes back on sale"]
    I5["Release reservation. Stock back on sale"]
    I6{"Claim in one transaction. Is the hold still valid, or lapsed with every line still in stock?"}
    I8["Reservation CLAIMED. Stock deducted for good"]
    I9["Claim refused. Stock was sold to someone else"]
  end

  subgraph PAY["Payment service - DB: payments, processed_webhooks, refunds, outbox"]
    P1["Save payment PENDING. Unique on order id, so a repeat request finds the same row"]
    P2["Send charge request. Idempotency key = order id. On timeout, resend with the same key"]
    P3["Webhook endpoint. Verify provider signature"]
    P4{"Provider event id already in processed_webhooks?"}
    P5["Ignore. Reply 200 so the provider stops resending"]
    P6["One transaction: insert event id, update payment to SUCCEEDED or DECLINED, write outbox row"]
    P7{"Outcome?"}
    P8["Publish PaymentSucceeded"]
    P9["Publish PaymentDeclined"]
    P10["Save refund REQUESTED for the full amount. Unique on order id"]
    P11["Send refund request. Idempotency key = refund + order id"]
    P12{"Provider accepted the refund?"}
    P13["Refund REFUNDED. Publish RefundCompleted"]
    P14["Refund stays open as FAILED_RETRYING. attempts + 1. Retry with growing delay"]
    P15["Attempts exhausted: raise an alert. Refund stays open in the ops queue. Never dropped"]
  end

  subgraph PRV["Payment provider - external"]
    V1["Charge"]
    V2["Refund"]
  end

  C1 -->|"HTTP"| O1
  O1 -->|"HTTP: get cart"| K1
  K1 --> O2
  O2 -->|"HTTP: reserve, key = order id"| I1

  I1 -->|"no, any line short"| I3
  I3 --> O3
  O3 --> C2
  I1 -->|"yes"| I2
  I2 --> O4

  O4 -->|"event PaymentRequested: order id, amount"| P1
  P1 --> P2
  P2 -->|"HTTPS"| V1
  V1 -.->|"webhook. Seconds to 30 min. May be delivered more than once"| P3
  P3 --> P4
  P4 -->|"yes, duplicate"| P5
  P4 -->|"no, new"| P6
  P6 --> P7

  P7 -->|"declined"| P9
  P9 -->|"event"| O5
  O5 --> C3
  O5 -->|"event OrderCancelled"| I5

  P7 -->|"succeeded"| P8
  P8 -->|"event"| O6
  O6 -->|"yes"| O7
  O6 -->|"no, order already closed. Never keep the money"| O10
  O7 -->|"HTTP: claim, key = order id"| I6
  I4 -.-> I6

  I6 -->|"yes"| I8
  I8 --> O8
  O8 --> C4
  O8 -->|"event OrderConfirmed"| K2

  I6 -->|"no, late success"| I9
  I9 --> O9
  O9 --> C5
  O9 --> O10
  O10 -->|"event RefundRequested"| P10
  P10 --> P11
  P11 -->|"HTTPS"| V2
  V2 --> P12
  P12 -->|"yes"| P13
  P13 -->|"event"| O11
  P12 -->|"no, or timeout"| P14
  P14 -->|"retry"| P11
  P14 -->|"limit reached"| P15
  P15 -.->|"ops retries manually"| P11
```

## Triggers and what each service stores

| Service | Triggered by | Stores | Never does |
|---|---|---|---|
| Cart | Order's HTTP request for the cart. `OrderConfirmed` event. | Cart lines, current prices | Empties the cart on anything except `OrderConfirmed` |
| Order | Place order. Inventory's reply. `PaymentSucceeded`, `PaymentDeclined` and `RefundCompleted` events. | Order, snapshot of lines and prices, status history, outbox | Touches stock or the provider |
| Inventory | Order's reserve and claim calls. `OrderCancelled` event. The expiry timer. | Stock levels, reservations with state `HELD`, `EXPIRED`, `RELEASED` or `CLAIMED` | Reads orders or payments |
| Payment | `PaymentRequested` and `RefundRequested` events. Provider webhooks. Retry worker. | Payments, processed webhook ids, refunds with attempt count and next retry time, outbox | Is the only service that talks to the provider |

## Order states

`PENDING` then one of:

- `REJECTED_OUT_OF_STOCK`: stock was short at reservation.
- `AWAITING_PAYMENT`, which leads to one of:
  - `CONFIRMED`
  - `CANCELLED_PAYMENT_DECLINED`
  - `CANCELLED_OUT_OF_STOCK`: a late success whose claim was refused, so a refund follows.

## Failure branches

| Case | What happens | Customer sees | Cart |
|---|---|---|---|
| Short stock | Inventory checks all lines in one transaction. If any is short it reserves nothing and returns the short items. Order marks `REJECTED_OUT_OF_STOCK`. Payment is never called. | The list of short items | Untouched |
| Declined payment | The webhook becomes `PaymentDeclined`. Order cancels. `OrderCancelled` makes Inventory release the hold straight away. | Payment declined, can retry | Untouched |
| Late success after the hold lapsed | The hold expired and the stock may be gone. Order asks Inventory to claim. The claim is refused, so Order cancels as out of stock and requests a full refund. Payment refunds automatically. No partial shipment. | Cancellation email | Untouched |
| Refund fails | The refund row stays open (`FAILED_RETRYING`) with an attempt count. A worker retries with the same refund key, so a retry can't refund twice. At the retry limit an alert goes to ops and the row stays in the manual queue until `REFUNDED`. | Refund arrives late | Untouched |
| Duplicate webhook | The provider event id is inserted into `processed_webhooks` in the same transaction as the payment update. A repeat hits the unique key, is ignored, and gets a 200. | Nothing | Unchanged |
| Retried charge request | The idempotency key is the order id, so the provider returns the original charge. | Nothing | Unchanged |

## Why the claim step exists

The payment webhook can arrive up to 30 minutes after the 10-minute hold started. So the hold can lapse before the money is confirmed. Inventory is the only authority on stock, and the claim is one transaction on the reservation row. A background expiry and a claim therefore can't both win. The outcome is either `CLAIMED` or refused, and a refused claim triggers the refund.

## Assumptions to confirm

1. **Lapsed hold with stock still free.** The claim re-takes all lines atomically instead of refunding. The customer keeps a paid order whenever it can still be fulfilled. To refund on every lapse, make the claim require a `HELD` reservation.
2. **Emails.** Order sends the "cancelled, refunded" email through the existing mail sender. No notification service is named in the brief. A "refund completed" email can be added on `RefundCompleted`.
3. **Emptying the cart.** On `OrderConfirmed`, Cart empties the whole cart. The brief doesn't say how to treat edits made after Place order.
4. **Refund outcome.** The diagram shows it as the provider's reply to the refund call. If the provider reports refunds by webhook, they go through the same signature check and `processed_webhooks` dedup as charges.
5. **Retry limit.** "Attempts exhausted" is a number to set. A refund is never closed by hitting it.
