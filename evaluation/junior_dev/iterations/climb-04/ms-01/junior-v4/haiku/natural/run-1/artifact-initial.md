# Checkout across Cart, Inventory, Payment and Order

This flowchart shows checkout from **Place order** to a confirmed order, a cancelled order with refund, or a stopped checkout with the cart unchanged. Each subgraph is one service. Each node says what the service does and what it stores. Dashed arrows are timers or background jobs, not customer actions.

Before reading the chart, note three rules that shape it:

- **The order is the unit of work.** The order id is the idempotency key for the charge, for the refund and for the cart-emptying event, so a retry at any step is safe.
- **Stock is held first, paid second, and claimed only after payment succeeds.** A 10-minute hold runs while payment is pending. If the webhook arrives after the hold has lapsed, the late-success branch decides whether the order can still be fulfilled.
- **The cart is never changed by a failed checkout.** Only a `OrderConfirmed` event empties it.

```mermaid
flowchart TD
    CUST(["Customer presses Place order"])

    subgraph CART ["Cart service"]
        CART1["Read cart lines and prices<br/>stores: carts, cart_lines (unchanged)"]
        CART2["On OrderConfirmed: empty cart<br/>consumer, idempotent on order id<br/>stores: carts"]
    end

    subgraph ORDER ["Order service"]
        ORD1["Look for an open checkout on this cart<br/>stores: orders"]
        ORD2["Create order PENDING_STOCK<br/>snapshot lines and prices, order id is the key<br/>stores: orders, order_lines, order_status_history"]
        ORD3["Ask Inventory to reserve all lines"]
        ORD4["Status FAILED_SHORT_STOCK<br/>short items shown to customer"]
        ORD5["Status AWAITING_PAYMENT<br/>ask Payment to charge, key = order id"]
        ORD6["Status FAILED_PAYMENT<br/>ask Inventory to release hold"]
        ORD7["Ask Inventory to claim the reservation"]
        ORD8["Status CONFIRMED<br/>publish OrderConfirmed, email customer"]
        ORD9["Status CANCELLED_OUT_OF_STOCK<br/>ask Payment to refund full amount"]
    end

    subgraph INV ["Inventory service"]
        INV1{"Every line has enough free stock?"}
        INV2["Reserve nothing, return short item list<br/>stores: nothing written"]
        INV3["Create reservation HELD, expires_at = now + 10 min<br/>stores: reservations, reservation_lines, held counts"]
        INV4["Claim: HELD becomes CLAIMED, held stock becomes sold<br/>stores: reservations, stock"]
        INV5{"Reservation still HELD?"}
        INV6{"Same lines free now? Re-reserve and claim in one transaction"}
        INV7["Claim refused, return short item list"]
        INV8["Release: HELD becomes RELEASED, held stock back on sale"]
        INV9["Sweeper every minute: HELD past expires_at becomes EXPIRED, held stock back on sale"]
    end

    subgraph PAY ["Payment service (only service that talks to the provider)"]
        PAY1["Insert payment row PENDING, unique on order id<br/>stores: payments"]
        PAY2["Charge provider with Idempotency-Key = order id"]
        PAY3{"Event id already in webhook_events?"}
        PAY4["Return 200, change nothing"]
        PAY5["Record event id, verify signature<br/>guarded update: PENDING to SUCCEEDED or DECLINED<br/>stores: webhook_events, payments, outbox"]
        PAY6["Watchdog: poll provider for charge status"]
        PAY7["Save refund row REFUND_PENDING, key = refund id<br/>stores: refunds"]
        PAY8["Call provider refund for full amount"]
        PAY9{"Refund succeeded?"}
        PAY10["Refund SUCCEEDED"]
        PAY11["Retry with backoff, same key<br/>after max attempts: REFUND_FAILED, ops alert"]
    end

    PROV(["Payment provider"])

    CUST --> CART1
    CART1 -->|"POST /orders with lines and prices"| ORD1
    ORD1 -->|"open checkout exists"| EXIST(["Return existing order, no new hold or charge"])
    ORD1 -->|"none"| ORD2
    ORD2 --> ORD3
    ORD3 -->|"POST /reservations, all or nothing"| INV1

    INV1 -->|"No, a line is short"| INV2
    INV2 -->|"409 with short items"| ORD4
    ORD4 --> STOP_SHORT(["Stop: cart unchanged, customer sees short items and can retry"])

    INV1 -->|"Yes"| INV3
    INV3 -.->|"no claim within 10 min"| INV9
    INV3 -->|"reservation id returned"| ORD5
    ORD5 -->|"POST /charges, Idempotency-Key = order id"| PAY1
    PAY1 --> PAY2
    PAY2 --> PROV
    PAY2 -.->|"no webhook after 35 min"| PAY6
    PAY6 -->|"poll"| PROV
    PROV -.->|"status reply, same path as webhook"| PAY3
    PROV -->|"webhook: succeeded or declined, up to 30 min, may repeat"| PAY3

    PAY3 -->|"Yes, duplicate"| PAY4
    PAY4 --> STOP_DUP(["Stop: no second processing"])
    PAY3 -->|"No, new event"| PAY5

    PAY5 -->|"DECLINED, publish PaymentDeclined"| ORD6
    ORD6 -->|"POST /reservations/id/release"| INV8
    INV8 --> STOP_DEC(["Stop: customer told payment declined, cart unchanged, can retry"])

    PAY5 -->|"SUCCEEDED, publish PaymentSucceeded"| ORD7
    ORD7 -->|"POST /reservations/id/claim"| INV5
    INV5 -->|"Yes, on time"| INV4
    INV5 -->|"No, expired or swept"| INV6
    INV6 -->|"Yes"| INV4
    INV6 -->|"No"| INV7
    INV7 -->|"claim short, with items"| ORD9
    INV4 -->|"CLAIMED"| ORD8
    ORD8 -->|"OrderConfirmed event"| CART2
    ORD8 --> STOP_OK(["Success: order CONFIRMED, cart emptied"])

    ORD9 -->|"POST /refunds, full amount"| PAY7
    PAY7 --> PAY8
    PAY8 --> PROV
    PROV -->|"refund result, sync or webhook, same dedupe"| PAY9
    PAY9 -->|"Yes"| PAY10
    PAY10 --> STOP_REF(["Stop: order cancelled, customer emailed, refund done"])
    PAY9 -->|"No or error"| PAY11
    PAY11 -->|"retry"| PAY8
    PAY11 -->|"attempts exhausted"| OPS(["Ops queue: open refund, retried until resolved, never dropped"])

    classDef stop fill:#f4f4f4,stroke:#777,color:#222
    classDef bad fill:#fde8e8,stroke:#b42318,color:#4a0d0d
    class STOP_SHORT,STOP_DUP,STOP_DEC,STOP_OK,STOP_REF,EXIST stop
    class OPS,PAY11 bad
```

## Notes on the flow

**Happy path.** Cart sends its lines and prices to Order. Order snapshots them, asks Inventory to reserve all lines, then asks Payment to charge with the order id as the key. Payment's provider webhook arrives, Payment records it, and Payment publishes `PaymentSucceeded`. Order asks Inventory to claim the reservation (HELD to CLAIMED). Order then sets CONFIRMED and publishes `OrderConfirmed`, which Cart consumes to empty the cart.

**Short stock.** Inventory checks all lines in one transaction. If any line is short, it writes nothing and returns the short items. No hold and no charge happen. The cart is unchanged.

**Declined payment.** Payment publishes `PaymentDeclined`. Order moves to FAILED_PAYMENT and releases the hold. If the release call fails, the 10-minute sweeper still returns the stock. The customer can press Place order again, which creates a new order and a new key.

**Late success after the hold lapsed.** The provider can take up to 30 minutes, so the 10-minute hold can expire first. When the success arrives, the claim checks whether the hold still exists. If it has expired, Inventory tries once to re-reserve and claim the same lines in one transaction. If that fails, the claim returns the short items, Order sets CANCELLED_OUT_OF_STOCK, and Payment refunds the full amount. The customer gets an email. We never ship a partial order.

**Failed refund.** The refund row is saved before the provider call, so a crash cannot lose the intent. Failures retry with backoff under the same key. After the last attempt the row becomes REFUND_FAILED and an ops alert is raised. The row stays open until someone resolves it, so a refund is never silently dropped.

**Duplicate webhooks.** Payment records each provider event id with a unique constraint. A repeat is acknowledged and changes nothing. The status update is also guarded (PENDING only), so two different events that both claim success cannot process twice.

**Timers.** Inventory's sweeper expires holds every minute. Payment's watchdog polls the provider if a payment is still pending after 35 minutes, so a lost webhook cannot leave an order stuck.

## What each service stores

| Service | Owns | Notes |
|---|---|---|
| Cart | `carts`, `cart_lines` | Written only by customer edits and the `OrderConfirmed` consumer. Never read by other services. |
| Order | `orders`, `order_lines` (price snapshot), `order_status_history`, outbox | Holds the checkout state and the open-checkout check. |
| Inventory | `stock`, `reservations`, `reservation_lines` | Hold, claim, release and expiry are all state changes on `reservations`. |
| Payment | `payments`, `webhook_events`, `refunds`, outbox | `webhook_events` gives duplicate protection. `refunds` gives refund durability. |

## Decisions to confirm

1. **Claim at payment success, not at reservation.** This keeps stock held only while payment is pending. The cost is that a payment finishing after the hold lapses can be cancelled even when the stock is still free. Extending the hold to about 35 minutes would avoid most of those cancellations, but would lock stock longer after declines. The brief fixes the hold at 10 minutes, so this design does not extend it.
2. **Late success retries the reservation once.** If the same lines are still free, the order is fulfilled. The alternative is to refund immediately. Confirm which the business wants.
3. **Refund outcome channel.** The brief covers charge webhooks only. This design assumes refunds return a synchronous result or a webhook handled by the same dedupe path. Confirm with the provider.
4. **Who sends email.** Order sends the confirmation and cancellation emails in this design. Confirm that a separate notifications service is not planned.
5. **Duplicate checkout.** A second Place order while the first is AWAITING_PAYMENT returns the existing order, which prevents a second hold and charge. This check is in Order, so the cart is not touched.
6. **Cart lag.** If the broker is slow, the cart can still show items after confirmation for a short time. The order id dedupe makes this safe, but the customer may see stale items briefly.