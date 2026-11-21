# Checkout across Cart, Inventory, Payment and Order

## How to read this

- Each box is a step. Each swimlane is the service that performs it.
- Arrow labels say what triggers the next step. "HTTP" is a direct request. "event" is a message on the shared broker.
- What each service stores is in the table below the diagram. Each service writes only to its own database.
- Failure branches are labelled **F1 to F6** and explained after the diagram.

## Flowchart

```mermaid
flowchart TD
    CUST(["Customer presses Place order"])
    PROV[["Payment provider - external"]]

    subgraph CART["CART service"]
        C1["Snapshot cart lines and prices as they are now<br/>Cart is NOT changed"]
        C2["Empty the cart"]
        C3["Cart left exactly as it was<br/>Customer can retry"]
    end

    subgraph ORDER["ORDER service"]
        O1["Create order with new order id<br/>status PENDING<br/>stores the snapshot, frozen"]
        O2["HTTP: ask Inventory to reserve all lines"]
        O3["Status REJECTED_OUT_OF_STOCK<br/>reply to customer with the short items"]
        O4["Status AWAITING_PAYMENT<br/>HTTP: ask Payment to charge"]
        O5["Status PAID_PENDING_CLAIM<br/>HTTP: ask Inventory to claim the stock"]
        O6["Status CONFIRMED<br/>publish event OrderConfirmed<br/>email customer: order confirmed"]
        O7["Status CANCELLED_PAYMENT_DECLINED<br/>email customer: payment declined"]
        O8["Status CANCELLED_OUT_OF_STOCK<br/>request full refund from Payment<br/>email customer: out of stock, refund coming"]
    end

    subgraph INV["INVENTORY service"]
        I1{"Is every line<br/>in stock?"}
        I2["Reserve ALL lines in one transaction<br/>hold expires in 10 minutes"]
        I3["Reserve NOTHING<br/>return list of short lines"]
        I4{"Is the hold still HELD?<br/>atomic update HELD to CLAIMED"}
        I5["Hold becomes CLAIMED<br/>stock is sold to this order"]
        I6["Claim refused<br/>hold was already released and stock may be resold"]
        I7["Timer: hold older than 10 min and not claimed<br/>becomes RELEASED<br/>stock back on sale"]
        I8["Release the hold<br/>stock back on sale"]
    end

    subgraph PAY["PAYMENT service"]
        P1["Record payment PENDING<br/>call provider to charge<br/>idempotency key = order id"]
        P2["Webhook arrives from provider<br/>seconds to 30 minutes later"]
        P3{"Provider event id<br/>already recorded?"}
        P4["Duplicate: do nothing<br/>reply 200 OK"]
        P5{"Outcome?"}
        P6["Payment SUCCEEDED<br/>publish event PaymentSucceeded"]
        P7["Payment DECLINED<br/>publish event PaymentDeclined"]
        P8["Record refund PENDING for full amount<br/>call provider to refund<br/>idempotency key = refund + order id"]
        P9{"Provider accepted<br/>the refund?"}
        P10["Refund stays PENDING<br/>retry later with backoff<br/>never deleted"]
        P11["Retries exhausted: refund FAILED_NEEDS_ATTENTION<br/>alert operations<br/>stays on a manual retry list"]
        P12["Refund REFUNDED<br/>publish event RefundCompleted"]
    end

    CUST --> C1
    C1 -->|"HTTP: create order from snapshot"| O1
    O1 --> O2
    O2 -->|"HTTP"| I1
    I1 -->|"yes"| I2
    I1 -->|"no, any line short  F1"| I3
    I3 -->|"HTTP reply"| O3
    O3 -->|"nothing charged, nothing reserved"| C3
    I2 -->|"HTTP reply: reserved"| O4
    O4 -->|"HTTP"| P1
    P1 -->|"charge request"| PROV
    PROV -->|"webhook"| P2
    P2 --> P3
    P3 -->|"yes  F5"| P4
    P3 -->|"no: record event id, same transaction as the next step"| P5
    P5 -->|"succeeded"| P6
    P5 -->|"declined  F2"| P7

    P6 -->|"event"| O5
    O5 -->|"HTTP"| I4
    I4 -->|"yes"| I5
    I5 -->|"HTTP reply: claimed"| O6
    O6 -->|"event OrderConfirmed"| C2

    I4 -->|"no: hold lapsed  F3"| I6
    I6 -->|"HTTP reply: refused"| O8
    O8 -->|"event or HTTP: refund request"| P8
    P8 -->|"refund request"| PROV
    PROV -->|"accepted or rejected"| P9
    P9 -->|"accepted"| P12
    P9 -->|"failed  F4"| P10
    P10 -->|"retry"| P8
    P10 -->|"max attempts"| P11
    P11 -->|"ops retries manually"| P8

    P7 -->|"event"| O7
    O7 -->|"event OrderCancelled"| I8
    O7 -->|"event OrderCancelled"| C3

    O4 -.->|"10 minutes pass with no claim"| I7
```

## The failure branches

| Ref | Case | What happens | Where the customer ends up |
|---|---|---|---|
| **F1** | **Short stock** | Inventory checks every line and reserves nothing if any line is short. Order replies to the customer with the short items. Payment is never called. | Cart unchanged. Told which items are short. |
| **F2** | **Declined payment** | Payment publishes `PaymentDeclined`. Order cancels. Inventory releases the hold. If the hold has already lapsed, the release does nothing. | Cart unchanged. Told the payment was declined. |
| **F3** | **Success after the hold lapsed** | The 10-minute timer releases the stock, and it may be sold to someone else. The webhook then reports success, so Order asks Inventory to claim the stock. Inventory refuses because the hold is no longer HELD. Order cancels as out of stock and asks Payment for a full refund. | Cart unchanged. Emailed that the order was cancelled for lack of stock and the refund is on its way. |
| **F4** | **Refund fails at the provider** | The refund stays PENDING and is retried with backoff. After the retry limit it becomes `FAILED_NEEDS_ATTENTION` and operations are alerted. It stays on a manual retry list and is never deleted. Retries are safe because the refund request has its own idempotency key. | Order stays CANCELLED_OUT_OF_STOCK. Refund is completed later. |
| **F5** | **Duplicate webhook** | Payment stores the provider's event id under a unique constraint. A repeat finds it, returns 200 and stops. | No visible effect. |
| **F6** | **Hold expires while waiting** (dotted arrow) | Nothing fails at this point. The stock goes back on sale, and the order keeps waiting for the webhook. The outcome is decided later, either by F2 or F3 above, or by a normal success if the stock is still unsold. | See F2 and F3. |

## Who does what, what triggers it, what it stores

| Service | Triggered by | Steps it performs | What it stores in its own database |
|---|---|---|---|
| **Cart** | Customer presses Place order. Event `OrderConfirmed`. | Takes the snapshot and sends it to Order. Empties the cart only on `OrderConfirmed`. | Cart lines and current prices. Cart is never emptied on any failure. |
| **Order** | HTTP create from Cart. Replies from Inventory. Events from Payment. | Owns the order's status and decides what happens next. Sends emails. | Order id, status, frozen copy of the lines and prices, total, timestamps. Order status is `PENDING`, `REJECTED_OUT_OF_STOCK`, `AWAITING_PAYMENT`, `PAID_PENDING_CLAIM`, `CONFIRMED`, `CANCELLED_PAYMENT_DECLINED` or `CANCELLED_OUT_OF_STOCK`. |
| **Inventory** | HTTP reserve, claim. A timer. Event `OrderCancelled`. | Checks stock and reserves all-or-nothing. Claims the hold. Releases expired or unneeded holds. | Stock levels. One hold per order: order id, lines, status `HELD`, `CLAIMED` or `RELEASED`, `expires_at` (created time + 10 min). |
| **Payment** | HTTP charge request. Provider webhooks. Refund request. Retry timer. | The only service that talks to the provider. Handles webhook deduplication. Runs refunds and retries. | Payment per order: order id (also the idempotency key), amount, status. Processed provider event ids (unique). Refund per order: status, attempt count, next retry time, last error. |

## Why it is safe

- **One owner for each decision.** Only Order changes order status. Only Inventory changes holds. Only Payment talks to the provider. No service reads another's tables.
- **No double charge.** Every charge request carries the order id as the idempotency key. If Payment crashes and re-sends, the provider returns the original result.
- **No double processing.** Webhooks are deduplicated by provider event id. The event id and the resulting state change are written in the same transaction, so a crash cannot record one without the other.
- **Claim versus expiry is race-free.** Claim and expiry both use a conditional update on the hold row (`HELD` to `CLAIMED`, or `HELD` to `RELEASED`). Whichever commits first wins, and the other sees the new status and does nothing.
- **Event publishing is reliable.** Each service writes its state change and the outgoing event in one transaction (an outbox table), and a relay publishes to the broker. Consumers apply status changes only from an allowed previous status, so a re-delivered broker message is harmless.
- **Money is never kept for an order we cannot fulfil.** The only route out of "payment succeeded" without a confirmed order is the refund branch (F3). That branch has no end state other than REFUNDED or the visible FAILED_NEEDS_ATTENTION list.
- **Cart.** Cart changes only when it receives `OrderConfirmed`. The order uses its own snapshot, so cart edits and price changes during checkout do not affect it.

## Assumptions and open points

1. **Emails.** I assumed Order sends the customer emails through whatever mail mechanism already exists. If a separate notification service exists, Order should publish the events and that service should send the emails.
2. **Provider never answers.** The brief says up to 30 minutes. I suggest a reconciliation job that asks the provider for the status of any payment still PENDING after about 35 minutes, and treats the answer as if it were a webhook. Please confirm.
3. **Cart edits during payment.** On `OrderConfirmed`, the cart is emptied entirely. If the customer added items while waiting, those would be lost. A safer option is to have Cart empty only the lines in the snapshot. I need your decision.
4. **Refund outcome by webhook.** I assumed refund results can also arrive by webhook and use the same deduplication. If they come back synchronously, step P9 handles it directly.
5. **Retry limit for refunds.** The number of attempts and the backoff schedule are not set here. They need a decision. Whatever they are, exhausting them leads to an alert, never to dropping the refund.
