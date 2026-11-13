# Checkout across Cart, Inventory, Payment and Order

## Notes before the diagram

**What each service stores**

- **Cart:** cart lines and cart status. Cart is emptied only when it receives OrderConfirmed. It keeps the order id it was given so a repeated Place order press reuses it.
- **Order:** order id, status, the frozen line and price snapshot taken at Place order, and refund and email state. The order id is the key for the reservation and for the charge.
- **Inventory:** stock on hand, and reservations with status HELD, CLAIMED or EXPIRED plus `expires_at` (created time + 10 minutes).
- **Payment:** charges keyed by order id (PENDING, SUCCEEDED, DECLINED), refunds keyed by `refund:` + order id, and the provider event ids it has already processed.

**How the services talk**

- HTTP for commands: Cart calls Order, Order calls Inventory and Payment.
- Broker events for outcomes: PaymentSucceeded, PaymentDeclined, OrderConfirmed, OrderFailed, RefundSucceeded.
- Only Payment calls the payment provider, and only Payment receives its webhooks.

**Idempotency and safety rules**

- The charge idempotency key is the order id. Any retry of the charge call reuses it, so the customer is never charged twice.
- The webhook dedupe key is the provider event id. It is recorded in the same database transaction as the state change, so a duplicate delivery changes nothing.
- The claim is one conditional update: Inventory converts a reservation to CLAIMED only if it is still HELD and now is before `expires_at`. An expired hold cannot be claimed even before the sweeper has run, which prevents a double sale.
- Refunds are retried with the same key until they succeed. A failed refund stays open and alerts operations. It is never dropped.

**Timing risk**

The hold lasts 10 minutes, but the webhook can take up to 30 minutes. Many successful payments will therefore arrive after the hold has lapsed. The late-success path is a normal path, not a rare edge case. This is listed as an open question below.

## Flowchart

```mermaid
flowchart TD
    subgraph CART["Cart service: stores cart lines and cart status"]
        C1(["Customer presses Place order"])
        C2["Send cart snapshot to Order and record the order id"]
        C3["Show which items are short. Cart unchanged"]
        C4["Show the reason for failure. Cart unchanged, customer can retry"]
        C5["Empty cart. Runs only on OrderConfirmed"]
    end

    subgraph ORDER["Order service: stores order status, frozen lines and prices, refund state"]
        O1["Create order PENDING_STOCK with frozen lines and prices"]
        O2["Ask Inventory to reserve all lines, keyed by order id"]
        O3["Status AWAITING_PAYMENT. Ask Payment to charge, keyed by order id"]
        O4["Ask Inventory to claim the reservation"]
        O5["Status CONFIRMED. Publish OrderConfirmed"]
        O6["Status REJECTED_OUT_OF_STOCK. Return short items to Cart"]
        O7["Status PAYMENT_DECLINED. Publish OrderFailed"]
        O8["Status CANCELLED_OUT_OF_STOCK. Request full refund"]
        O9["Refund still open. Keep REFUND_PENDING and alert ops"]
        O10["Refund confirmed. Email customer that the order is cancelled and refunded"]
        O11["Status CHECKOUT_FAILED. No charge was sent"]
    end

    subgraph INV["Inventory service: stores stock on hand, reservations with expires_at and status"]
        I1["Check every line in one transaction"]
        I2{"Any line short?"}
        I3["Create reservation HELD, expires in 10 min, hold stock"]
        I4{"Claim: still HELD and now before expires_at?"}
        I5["Mark reservation CLAIMED. Stock is sold to this order"]
        I6["Refuse claim: reservation EXPIRED or stock sold elsewhere"]
        I7["Sweeper: HELD past 10 min becomes EXPIRED. Stock back on sale"]
        I8["Release reservation. Stock back on sale"]
    end

    subgraph PAY["Payment service: stores charges and refunds keyed by order id, processed event ids"]
        P1["Record charge PENDING keyed by order id"]
        P2["Call provider with order id as idempotency key. Retry with same key"]
        P3["Webhook arrives. Verify signature, read provider event id"]
        P4{"Event id already processed?"}
        P5["Acknowledge only. No state change, no event"]
        P6{"Provider outcome?"}
        P7["Mark charge SUCCEEDED. Publish PaymentSucceeded"]
        P8["Mark charge DECLINED. Publish PaymentDeclined"]
        P9["No webhook after 30 min: query provider for charge status"]
        P10["Record refund PENDING keyed by refund plus order id"]
        P11["Call provider to refund full amount, same key on retry"]
        P12{"Refund outcome?"}
        P13["Mark refund SUCCEEDED. Publish RefundSucceeded"]
        P14["Mark refund FAILED. Keep it open, retry with backoff, never drop"]
    end

    PROV["Payment provider (external). Sends webhooks, may send duplicates"]

    C1 --> C2
    C2 --> O1
    O1 --> O2
    O2 --> I1
    O2 -. "Inventory unreachable before any charge" .-> O11
    O11 --> C4
    I1 --> I2
    I2 -- "Yes: nothing reserved, no payment" --> O6
    O6 --> C3
    I2 -- "No: all lines held" --> I3
    I3 -. "Not claimed within 10 min" .-> I7
    I3 --> O3
    O3 --> P1
    P1 --> P2
    P2 -. "No webhook after 30 min" .-> P9
    P2 --> PROV
    P9 --> PROV
    PROV -- "Webhook: seconds to 30 min" --> P3
    P3 --> P4
    P4 -- "Yes: duplicate delivery" --> P5
    P4 -- "No: first delivery" --> P6
    P6 -- "Declined" --> P8
    P8 --> O7
    O7 --> I8
    I8 --> C4
    P6 -- "Succeeded" --> P7
    P7 --> O4
    O4 --> I4
    I4 -- "Yes" --> I5
    I5 -- "Confirm" --> O5
    O5 --> C5
    I4 -- "No: late success after hold lapsed" --> I6
    I6 --> O8
    O8 --> P10
    P10 --> P11
    P11 --> PROV
    PROV -- "Refund result" --> P12
    P12 -- "Succeeded" --> P13
    P13 --> O10
    P12 -- "Failed" --> P14
    P14 --> O9
    P14 -. "Retry after backoff" .-> P11

    classDef fail fill:#fde2e2,stroke:#b00020,color:#000
    class C3,C4,O6,O7,O8,O9,O11,I6,P8,P14 fail
```

Red nodes are failure outcomes. Solid arrows are the main path. Dotted arrows are timers, retries and fallbacks.

## Failure cases

| Case | Caught by | What happens | Cart | Money | Stock |
|---|---|---|---|---|---|
| Short stock | Inventory `I2` | Nothing reserved, no payment requested, short items returned | Unchanged, short items shown | None taken | None held |
| Payment declined | Payment `P8` | Order PAYMENT_DECLINED, reservation released | Unchanged | None taken | Released to sale |
| Late success after hold lapsed | Inventory `I4`, claim refused | Order cancelled as out of stock, full refund, customer emailed after refund is confirmed | Unchanged | Refunded in full | Not held by this order |
| Refund fails at provider | Payment `P12`, `P14` | Refund stays open, retried with same key, ops alerted, order stays REFUND_PENDING | Unchanged | Owed to customer until refunded | Not held |
| Duplicate webhook | Payment `P4` | Acknowledged, no state change, no event published | Unchanged | Charged once | Unchanged |
| Provider webhook never arrives | Payment `P9` | Charge status queried from provider after 30 min, then handled as above | Unchanged until outcome | Per provider status | Per outcome |

The cart is emptied only on OrderConfirmed (`C5`), so every failure above leaves it exactly as it was.

## Open questions

1. **Hold length against webhook delay.** A 10-minute hold and a webhook of up to 30 minutes mean many good orders will take the refund path. Options include lengthening the hold to at least 30 minutes, which ties up stock longer, or accepting refunds as a common outcome. The brief does not decide this.
2. **Who sends the customer email, and when.** The diagram sends it after the refund is confirmed (`O10`). If the refund is failing, the customer hears nothing until it succeeds. Confirm this timing and the owning service.
3. **Refund result channel.** The diagram assumes the provider returns the refund result either synchronously or by webhook. If it is a webhook, the same event-id dedupe rule applies.
4. **Repeated Place order presses.** The Order is created before stock is checked. The design assumes Cart reuses the order id it already holds so a double press cannot create two orders. Confirm this.
5. **Reconciliation at 30 minutes.** `P9` queries the provider. If the provider reports success for a charge still PENDING, the flow continues from `P7`. This needs an owner for the timer.
