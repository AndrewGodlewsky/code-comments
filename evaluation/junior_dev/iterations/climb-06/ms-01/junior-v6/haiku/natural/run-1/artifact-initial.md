# Checkout across Cart, Inventory, Payment and Order

Checkout is a saga run by the **Order service**. It reserves stock, then requests payment, then waits for the provider's webhook. It claims the stock only after the payment succeeds, and it compensates with a release (on decline) or a full refund (when the stock is gone). The **Cart service** is read-only until the order is confirmed.

## Flowchart

```mermaid
flowchart TD
    subgraph CU["Customer, browser"]
        CU1(["Presses Place order"])
        CU2(["Sees short items, cart unchanged"])
        CU3(["Sees payment declined, cart unchanged, can retry"])
        CU4(["Sees order confirmed"])
        CU5(["Gets out-of-stock email, refund started"])
    end

    subgraph CA["Cart service, owns carts DB"]
        CA1["Return read-only snapshot of lines and prices"]
        CA2["On OrderConfirmed: empty this cart"]
    end

    subgraph OR["Order service, owns orders DB, runs the saga"]
        OR1["Insert order PLACING<br/>copy lines and prices into order lines<br/>key = client request id"]
        OR2{"Reserve result"}
        OR3["Status REJECTED_SHORT_STOCK<br/>store short item list"]
        OR4["Status AWAITING_PAYMENT<br/>ask Payment to charge"]
        OR5{"Payment event"}
        OR6["Status PAYMENT_DECLINED<br/>ask Inventory to release"]
        OR7["Ask Inventory to claim reservation"]
        OR8{"Claim accepted"}
        OR9["Status CONFIRMED<br/>publish OrderConfirmed"]
        OR10["Status CANCELLED_OUT_OF_STOCK<br/>publish RefundRequested"]
        OR11["Send out-of-stock email"]
        OR12["Hold expired while waiting<br/>set hold_expired flag, keep waiting"]
    end

    subgraph IN["Inventory service, owns stock and reservations DB"]
        IN1{"Every line has enough stock<br/>checked in one transaction"}
        IN2["Reject, write nothing<br/>return short items"]
        IN3["Insert reservation HELD<br/>expires_at = now + 10 min<br/>one per order id"]
        IN4{"Claim while HELD and not expired<br/>conditional update"}
        IN5["Status CLAIMED<br/>stock now sold"]
        IN6["Claim refused<br/>hold already EXPIRED or RELEASED"]
        IN7["Expiry sweep<br/>HELD past expires_at to EXPIRED<br/>stock back on sale"]
        IN8["Release<br/>HELD to RELEASED<br/>stock back on sale"]
    end

    subgraph PA["Payment service, owns charges, refunds and webhook log DB"]
        PA1["Insert charge PENDING<br/>unique on order id"]
        PA2["Call provider charge<br/>Idempotency-Key = order id"]
        PA3["Webhook received<br/>verify signature"]
        PA4{"Provider event id already in webhook log"}
        PA5["Return 200, change nothing"]
        PA6["One transaction: log event id,<br/>set charge SUCCEEDED or DECLINED,<br/>write outbox event"]
        PA7["Publish PaymentSucceeded or PaymentDeclined"]
        PA8["Insert refund row PENDING<br/>unique on order id"]
        PA9["Call provider refund, full amount<br/>Idempotency-Key = refund plus order id"]
        PA10{"Provider accepted refund"}
        PA11["Refund SUCCEEDED<br/>publish RefundCompleted"]
        PA12["Retry with backoff<br/>row stays open"]
        PA13{"Attempts past limit"}
        PA14["Refund FAILED_NEEDS_ATTENTION<br/>page ops, keep retrying"]
        PA15["Charge still PENDING after 45 min<br/>reconcile by polling provider"]
    end

    PR["Payment provider, external"]

    CU1 -- "HTTP POST /orders" --> OR1
    OR1 -- "HTTP GET snapshot" --> CA1
    CA1 -- "lines and prices" --> OR1
    OR1 -- "HTTP reserve, order id and lines" --> IN1
    IN1 -- "no" --> IN2
    IN1 -- "yes" --> IN3
    IN2 -- "short items" --> OR2
    IN3 -- "reserved" --> OR2
    IN3 -. "10 min pass with no claim" .-> IN7
    IN7 -- "ReservationExpired event" --> OR12
    OR2 -- "short" --> OR3
    OR3 --> CU2
    OR2 -- "reserved" --> OR4
    OR4 -- "HTTP charge, key = order id" --> PA1
    PA1 --> PA2
    PA2 -- "charge request" --> PR
    PR -- "webhook, seconds to 30 min, may repeat" --> PA3
    PA3 --> PA4
    PA4 -- "yes, duplicate" --> PA5
    PA4 -- "no, new event" --> PA6
    PA6 --> PA7
    PA7 -- "PaymentDeclined or PaymentSucceeded" --> OR5
    OR5 -- "declined" --> OR6
    OR6 -- "HTTP release, order id" --> IN8
    OR6 --> CU3
    OR5 -- "succeeded" --> OR7
    OR7 -- "HTTP claim, order id" --> IN4
    IN4 -- "yes" --> IN5
    IN4 -- "no" --> IN6
    IN5 -- "claimed" --> OR8
    IN6 -- "refused" --> OR8
    OR8 -- "claimed" --> OR9
    OR8 -- "refused, late success" --> OR10
    OR9 -- "OrderConfirmed event" --> CA2
    OR9 --> CU4
    OR10 -- "RefundRequested event" --> PA8
    OR10 --> OR11
    OR11 --> CU5
    PA8 --> PA9
    PA9 -- "HTTP refund" --> PR
    PR -- "refund result" --> PA10
    PA10 -- "accepted" --> PA11
    PA10 -- "failed or no answer" --> PA12
    PA12 --> PA13
    PA13 -- "no" --> PA9
    PA13 -- "yes" --> PA14
    PA14 -. "scheduled retry, row never deleted" .-> PA9
    OR12 -. "webhook still decides outcome" .-> OR5
    OR12 -. "no webhook after 45 min" .-> PA15
    PA15 -- "poll provider status" --> PR
    PR -. "status treated like a webhook" .-> PA6

    classDef fail fill:#fde7e7,stroke:#b42318,color:#1d1d1d
    classDef ok fill:#e7f5ec,stroke:#1e7b45,color:#1d1d1d
    class OR3,OR6,OR10,IN2,IN6,PA12,PA14 fail
    class OR9,IN5,PA11,CU4 ok
```

## How to read it

- **Service**: each box is one service, and the box's database is its only store. Services never read each other's tables.
- **Trigger**: a press of Place order, an HTTP call, a broker event, a provider webhook, or a timer (the hold expiry).
- **Reservation**: a hold on stock that stops other customers from taking it. It lasts 10 minutes unless claimed.
- **Claim**: converts a held reservation into a sale. It succeeds only while the hold is still HELD. The check and update happen in one conditional database update, so a claim and an expiry cannot both win.
- **Idempotency key**: a value sent with a request so that a retry has the same effect as the first call. Charges use the order id. Refunds use `refund:` plus the order id.
- **Outbox**: the event is written in the same transaction as the state change and published from there. An event is never lost when a state changes.

## Stored state per service

| Service | Stores | Key rules |
|---|---|---|
| Cart | carts, cart lines | Read-only for checkout. Emptied only on OrderConfirmed. |
| Inventory | stock per SKU (on hand, held), reservations (order id, lines, status, expires_at) | One reservation per order id. Statuses: HELD, CLAIMED, RELEASED, EXPIRED. |
| Payment | charges (order id unique, amount, status, provider ref), refunds (order id unique, amount, status, attempts), webhook log (provider event id unique), outbox | A webhook's status change and its log row commit together. |
| Order | orders (status, total, hold_expired flag), order lines (name, SKU, quantity, unit price as at Place order), status history, outbox | Lines are copied at Place order and never updated afterwards. |

Order statuses: PLACING, REJECTED_SHORT_STOCK, AWAITING_PAYMENT, PAYMENT_DECLINED, CONFIRMED, CANCELLED_OUT_OF_STOCK.

## Failure branches

- **Short stock.** Inventory checks every line in one transaction and reserves nothing if any line is short. Order sets REJECTED_SHORT_STOCK, stores the short items, and tells the customer which items. No payment is requested. The cart is unchanged.
- **Declined payment.** Payment records DECLINED and publishes it. Order releases the reservation at once, so the stock goes back on sale without waiting for the timer. The order is terminal. A retry creates a new order id, because a retry with the old key would get the old declined answer back from the provider. The cart is unchanged.
- **Late success after the hold lapsed.** The hold can expire while the order waits for the webhook. Order keeps waiting, and the outcome still arrives by webhook. On success, Order asks Inventory to claim and is refused, since the reservation is EXPIRED. Order sets CANCELLED_OUT_OF_STOCK, publishes RefundRequested, and emails the customer. Payment refunds the full amount. The stock is not given back to this order, and the cart is unchanged, so the customer can try again.
- **Failed refund.** A refund row is written before the provider is called, so the request survives a crash. On a failed or unanswered call, the row stays open and retries with backoff. It is never deleted. After the attempt limit, it becomes FAILED_NEEDS_ATTENTION, ops are paged, and retries continue. A daily reconciliation compares provider refunds with open rows.
- **Duplicate webhook.** Payment checks the provider event id in the webhook log. A repeat returns 200 and changes nothing. The status change and the log row commit together, so a crash cannot leave one without the other. Order also ignores events for orders already in a final state, because the broker is at-least-once and can redeliver.
- **Charge outcome unknown.** If the charge call times out, Payment retries with the same order id key, and the provider returns the same result. If no webhook arrives after 45 minutes, Payment polls the provider and treats the answer like a webhook.
- **Double-click on Place order.** The client request id is the key for the order insert, so the second request returns the first order.

## Rules the diagram depends on

1. Stock is reserved before any charge is requested. Order only charges while it holds a reservation.
2. Stock is claimed only after a successful payment. A claim before payment would remove the late-success case and force a release on every decline.
3. The cart is written only on OrderConfirmed. No other branch touches it.
4. Every money movement has an idempotency key that is stored before the call: charge = order id, refund = refund plus order id.
5. Every event is published through an outbox, and every consumer is idempotent by event id.
6. Any charge that succeeds on an order that does not end CONFIRMED has a refund row, and that row stays open until the provider confirms it.

## Open decisions

1. **Hold length against the 30-minute webhook window.** With a 10-minute hold, any payment slower than the hold loses its stock and is refunded. The brief fixes the hold at 10 minutes, so this is accepted as written. Extending the hold while AWAITING_PAYMENT would reduce refunds but would hold stock for abandoned checkouts. This needs a product decision.
2. **Who sends the emails.** This design has Order send them. If there is a separate notifications service, the Order steps change to publishing an event.
3. **Refund attempt limit and alert route.** The limit, the backoff schedule, and who is paged are not set.
4. **Message broker.** The design assumes at-least-once delivery. The broker is not named in the brief.
5. **Customer-facing copy for AWAITING_PAYMENT.** The customer may wait up to 30 minutes. The screen needs a waiting state that says what happens if the stock is gone.