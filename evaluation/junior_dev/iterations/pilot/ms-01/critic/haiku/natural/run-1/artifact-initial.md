# Checkout across Cart, Inventory, Payment and Order

This flowchart shows one checkout from **Place order** to a confirmed order, a refund, or a clean failure. Each colored lane is one service, and each node shows what the service does and what it stores. The dotted lines are asynchronous: webhooks from the payment provider and events on the message broker.

```mermaid
flowchart TD
    CUST_PRESS(["Customer presses Place order"])

    subgraph CART["Cart service"]
        CART_SNAP["Build snapshot: lines, unit prices, totals<br/>Cart DB not changed"]
        CART_EMPTY["Empty cart<br/>Only on OrderConfirmed event"]
    end

    subgraph ORD["Order service"]
        ORD_PLACE["Insert order PLACED with snapshot<br/>Stores: orders, order_lines (never edited)"]
        ORD_RESERVE["Ask Inventory to reserve every line<br/>HTTP, key = order id"]
        ORD_CHECK{"Reserved?"}
        ORD_REJECT["Status REJECTED_SHORT_STOCK<br/>Stores: short item list"]
        ORD_TELL_SHORT["Show customer the short items<br/>No payment requested, cart unchanged"]
        ORD_AWAIT_PAY["Status AWAITING_PAYMENT<br/>Stores: status"]
        ORD_DECLINED["Status PAYMENT_DECLINED<br/>Tell customer, cart unchanged"]
        ORD_CLAIM["Ask Inventory to claim reservation<br/>HTTP, key = order id"]
        ORD_CLAIM_OK{"Claim result?"}
        ORD_CONFIRM["Status CONFIRMED<br/>Publish OrderConfirmed"]
        ORD_CANCEL["Status CANCELLED_OUT_OF_STOCK<br/>Publish OrderCancelled"]
        ORD_EMAIL["Email customer: items sold out, full refund issued"]
    end

    subgraph INV["Inventory service"]
        INV_CHECK["One DB transaction: check every line<br/>Stores: stock levels"]
        INV_SHORT{"Any line short?"}
        INV_NOTHING["Reserve nothing<br/>Reply with short item list"]
        INV_HOLD["Reserve all lines<br/>Stores: reservation HELD, expires_at = now + 10 min"]
        INV_SWEEP["Sweep every minute: HELD past expires_at becomes RELEASED<br/>Stock back on sale"]
        INV_CLAIM_CHECK{"Reservation still HELD and not expired?"}
        INV_CLAIMED["Mark reservation CLAIMED<br/>Stock now sold to this order"]
        INV_LAPSED["Reply lapsed<br/>Hold expired, stock may be sold to someone else"]
        INV_RELEASE["Release reservation, idempotent by order id<br/>Stock back on sale"]
    end

    subgraph PAY["Payment service"]
        PAY_RECORD["Insert charge PENDING before calling provider<br/>Stores: charges, unique on order id"]
        PAY_CHARGE["Send charge to provider<br/>Idempotency-Key = order id"]
        PAY_WAIT["Waiting for provider outcome<br/>Seconds, up to 30 min"]
        PAY_WEBHOOK["Webhook received<br/>Verify signature, read provider event id"]
        PAY_RECON["Reconcile job at 35 min: query provider for PENDING charges"]
        PAY_DUP{"Event id already stored?"}
        PAY_IGNORE["Return 200, change nothing"]
        PAY_OUTCOME{"Provider outcome"}
        PAY_SUCCESS["Store SUCCEEDED and event id<br/>Publish PaymentSucceeded via outbox"]
        PAY_DECLINE["Store DECLINED and event id<br/>Publish PaymentDeclined via outbox"]
        PAY_REFUND["Refund full amount<br/>Key = refund for order id<br/>Stores: refund REFUND_PENDING"]
        PAY_REFUND_OUT{"Refund outcome"}
        PAY_REFUNDED["Store REFUNDED"]
        PAY_REFUND_FAIL["Store REFUND_FAILED with error"]
        PAY_OPS["Alert ops: refund stays open in queue, never dropped"]
    end

    PROV(["Payment provider (external)"])

    CUST_PRESS --> CART_SNAP
    CART_SNAP -->|"HTTP cart snapshot"| ORD_PLACE
    ORD_PLACE --> ORD_RESERVE
    ORD_RESERVE -->|"HTTP reserve"| INV_CHECK

    INV_CHECK --> INV_SHORT
    INV_SHORT -->|"yes"| INV_NOTHING
    INV_SHORT -->|"no"| INV_HOLD
    INV_NOTHING -->|"reply: short items"| ORD_CHECK
    INV_HOLD -->|"reply: reserved"| ORD_CHECK
    INV_HOLD -.->|"10 min pass, no claim"| INV_SWEEP

    ORD_CHECK -->|"no"| ORD_REJECT
    ORD_REJECT --> ORD_TELL_SHORT
    ORD_CHECK -->|"yes"| ORD_AWAIT_PAY

    ORD_AWAIT_PAY -->|"HTTP charge, key = order id"| PAY_RECORD
    PAY_RECORD --> PAY_CHARGE
    PAY_CHARGE -->|"charge request"| PROV
    PAY_CHARGE --> PAY_WAIT
    PROV -.->|"webhook: seconds to 30 min, may repeat"| PAY_WEBHOOK
    PAY_WAIT -.->|"no webhook by 35 min"| PAY_RECON
    PAY_WEBHOOK --> PAY_DUP
    PAY_RECON -->|"same handling as webhook"| PAY_DUP

    PAY_DUP -->|"yes: duplicate"| PAY_IGNORE
    PAY_DUP -->|"no: new event"| PAY_OUTCOME
    PAY_OUTCOME -->|"succeeded"| PAY_SUCCESS
    PAY_OUTCOME -->|"declined"| PAY_DECLINE

    PAY_DECLINE -->|"PaymentDeclined event"| ORD_DECLINED
    ORD_DECLINED -->|"HTTP release"| INV_RELEASE

    PAY_SUCCESS -->|"PaymentSucceeded event"| ORD_CLAIM
    ORD_CLAIM -->|"HTTP claim"| INV_CLAIM_CHECK
    INV_CLAIM_CHECK -->|"yes"| INV_CLAIMED
    INV_CLAIM_CHECK -->|"no: expired or released"| INV_LAPSED
    INV_CLAIMED -->|"claimed"| ORD_CLAIM_OK
    INV_LAPSED -->|"lapsed"| ORD_CLAIM_OK

    ORD_CLAIM_OK -->|"claimed"| ORD_CONFIRM
    ORD_CLAIM_OK -->|"lapsed: late success"| ORD_CANCEL
    ORD_CONFIRM -->|"OrderConfirmed event"| CART_EMPTY

    ORD_CANCEL --> ORD_EMAIL
    ORD_CANCEL -->|"OrderCancelled event"| PAY_REFUND
    PAY_REFUND -->|"refund request"| PROV
    PROV -.->|"refund result"| PAY_REFUND_OUT
    PAY_REFUND_OUT -->|"refunded"| PAY_REFUNDED
    PAY_REFUND_OUT -->|"failed"| PAY_REFUND_FAIL
    PAY_REFUND_FAIL -->|"retry with backoff"| PAY_REFUND
    PAY_REFUND_FAIL -->|"retries exhausted"| PAY_OPS
```

## Notes on the flow

**Happy path.** Order records the snapshot, Inventory holds every line for 10 minutes, Payment charges with the order id as the idempotency key, and the provider's webhook reports success. Order then claims the reservation and confirms. Only the confirmed order empties the cart.

**Short stock.** Inventory checks all lines in one transaction and reserves nothing if any line is short. Order records the short items, shows them to the customer, and never calls Payment. The cart is untouched.

**Declined payment.** Payment stores DECLINED and publishes an event. Order releases the reservation so the stock goes back on sale, and the cart is untouched. The provider key is the order id, so a retry of the same order would return the same decline. A retry must be a new Place order attempt with a new order id.

**Late success after the hold lapsed.** The hold can expire while the webhook is still pending. Inventory's claim is a conditional update (HELD and not expired), so it rejects the claim once the hold has lapsed or the stock has gone. Order then cancels as out of stock, emails the customer, and Payment refunds the full amount. Nothing ships partially, and the cart is not emptied.

**Failed refund.** Payment records REFUND_FAILED, keeps the refund open, and retries with backoff. If retries are exhausted it alerts ops. The refund is never marked done until the provider confirms it.

**Duplicate webhooks.** Payment stores each provider event id with a unique constraint, so a repeat returns 200 with no state change. The status transition is also conditional (PENDING to a final state only once). Order's handlers and Inventory's claim and release are idempotent on the order id, so a duplicate `PaymentSucceeded` event is a no-op.

## What each service stores

| Service | Stores |
|---|---|
| Cart | Cart lines (unchanged until OrderConfirmed) |
| Inventory | Stock levels, reservations (state, order id, lines, expires_at) |
| Payment | Charges (PENDING, SUCCEEDED, DECLINED), refunds, processed provider event ids |
| Order | Orders and status, immutable order lines, short-item list when rejected |

## Assumptions and open points

1. **Claim on payment success, not at charge.** The order claims stock only when the payment succeeds. A hold that lapses during the wait goes back on sale and is handled by the late-success branch.
2. **Email sender.** The brief has four services, so Order sends the email through an email provider. If email must come from a separate notification service, add it as a fifth lane.
3. **Reconciliation at 35 minutes.** This is an addition beyond the brief. It covers a webhook that never arrives, so a PENDING charge gets queried from the provider and goes through the same dedupe path.
4. **Refund outcome delivery.** The diagram assumes refund results come back synchronously or by webhook, and both go through the same dedupe.
5. **Outbox.** Payment and Order publish events from a transactional outbox, so a state change and its event cannot diverge.
6. **Retry limit.** The number of refund retries and the alert threshold are not set in the brief and need a decision.
7. **Hold length.** The 10-minute hold is fixed by the brief. A longer hold while payment is pending would reduce late successes, but it is not part of this design.