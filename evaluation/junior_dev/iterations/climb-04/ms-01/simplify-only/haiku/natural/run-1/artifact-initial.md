# Checkout across Cart, Inventory, Payment and Order

This document shows the whole checkout flow as one Mermaid flowchart. Each box is one step, labelled with the service that runs it. Boxes also say what triggers the step and what the service stores. Dotted arrows are timers or fallback paths. Solid arrows are the normal path and the failure branches.

**Rules the diagram enforces:**
- Stock is reserved before any charge is requested.
- Reservation is all-or-nothing.
- A reservation holds stock for 10 minutes.
- Only Payment talks to the provider, and it uses the order id as the idempotency key.
- The provider's result arrives by webhook, and duplicate webhooks are ignored.
- Money is never kept for an order that cannot be fulfilled.
- Refunds are tracked until they succeed.
- The cart is emptied only after the order is confirmed.

```mermaid
flowchart TD
    start(["Customer presses Place order"]) --> c1

    subgraph CART ["Cart service: stores cart and cart lines"]
        c1["Send cart lines and prices to Order<br/>HTTP POST"]
        c_short["Show the short items<br/>Cart unchanged"]
        c_fail["Show failure, offer retry<br/>Cart unchanged"]
        c_empty["Empty cart<br/>Trigger: OrderConfirmed event"]
    end

    subgraph ORDER ["Order service: stores orders, price snapshot, status"]
        o1["Create order, status PENDING<br/>Stores order id, lines and prices as of now"]
        o_short["Status REJECTED_SHORT_STOCK<br/>Stores short SKUs"]
        o2["Status AWAITING_PAYMENT<br/>Request charge, key = order id"]
        o_commit["Ask Inventory to commit reservation<br/>Timeout: retry same key, never refund"]
        o_ok["Status CONFIRMED<br/>Publish OrderConfirmed"]
        o_late["Status CANCELLED_OUT_OF_STOCK<br/>Request refund, email customer"]
        o_decl["Status CANCELLED_DECLINED<br/>Ask Inventory to release"]
    end

    subgraph INV ["Inventory service: stores stock on hand and reservations"]
        i_reserve["One transaction over all lines<br/>Trigger: reserve request"]
        i_check{"Every line has enough stock?"}
        i_none["Reserve nothing<br/>Return short SKUs"]
        i_hold["Reserve all lines<br/>Reservation HELD, expires_at = now + 10 min"]
        i_sweep["Sweeper, every minute<br/>Trigger: timer. HELD past expires_at becomes EXPIRED, stock back on sale"]
        i_commit{"Reservation still HELD<br/>and expires_at in the future?"}
        i_sold["Commit: stock sold to this order"]
        i_release["Release reservation, stock back on sale<br/>Idempotent"]
    end

    subgraph PAY ["Payment service: stores charges, webhook event ids, refunds, outbox"]
        p_create["Insert charge PENDING, unique on order id<br/>Call provider, key = order id"]
        p_hook["Webhook receiver<br/>Verify signature"]
        p_dup{"Provider event id already processed?"}
        p_dupok["Return 200, no change"]
        p_update["One transaction: record event id, move charge forward only, write outbox row"]
        p_recon["Reconcile, every 5 min<br/>Trigger: timer. Charges PENDING over 35 min, query provider"]
        p_refund["Insert refund REQUESTED, key = refund order id<br/>Call provider for full amount"]
        p_refres{"Refund succeeded?"}
        p_refok["Refund SUCCEEDED<br/>Publish RefundSucceeded"]
        p_refail["Refund FAILED, row stays open<br/>Retry with backoff, alert ops after N tries"]
    end

    provider(["Payment provider, external<br/>Outcome in seconds, up to 30 min"])
    broker[["Message broker"]]

    c1 -->|"POST order with snapshot"| o1
    o1 -->|"reserve all lines"| i_reserve
    i_reserve --> i_check
    i_check -->|"no"| i_none
    i_none -->|"short SKUs"| o_short
    o_short -->|"customer told which items"| c_short
    i_check -->|"yes"| i_hold
    i_hold -->|"reservation id"| o2
    o2 -->|"charge request"| p_create
    p_create -->|"charge request"| provider
    provider -->|"webhook, may repeat"| p_hook
    p_recon -.->|"query status"| provider
    p_recon -.-> p_update
    p_hook --> p_dup
    p_dup -->|"yes"| p_dupok
    p_dup -->|"no"| p_update
    p_update -->|"ChargeSucceeded or ChargeDeclined"| broker
    broker -->|"ChargeDeclined"| o_decl
    o_decl --> i_release
    i_release -->|"customer told, cart unchanged, may retry"| c_fail
    broker -->|"ChargeSucceeded"| o_commit
    o_commit --> i_commit
    i_commit -->|"yes"| i_sold
    i_sold --> o_ok
    o_ok -->|"OrderConfirmed"| broker
    broker -->|"OrderConfirmed"| c_empty
    i_commit -->|"no: hold lapsed or stock gone"| o_late
    o_late -->|"refund"| p_refund
    p_refund -->|"refund call"| provider
    provider -->|"refund result, sync or webhook"| p_refres
    p_refres -->|"yes"| p_refok
    p_refok -->|"RefundSucceeded"| broker
    p_refres -->|"no"| p_refail
    p_refail -.->|"retry with backoff"| p_refund
    i_sweep -.->|"hold lapsed"| i_commit
```

## Step by step

1. **Place order (Cart).** Cart sends the cart's lines and prices to Order. Cart does not change anything yet.
2. **Create order (Order).** Order stores a PENDING order with its own id and a copy of the lines and prices. Later cart edits do not change this copy.
3. **Reserve (Inventory).** Inventory checks every line in one transaction.
   - If any line is short, it reserves nothing. Order records REJECTED_SHORT_STOCK, and Cart shows the short items. No payment is requested.
   - If every line is available, Inventory holds all of them for 10 minutes. Order moves to AWAITING_PAYMENT.
4. **Charge (Payment).** Payment records a PENDING charge keyed by the order id and calls the provider with the same key. A retried request returns the existing charge, so the customer cannot be charged twice.
5. **Provider result (Payment).** The webhook is checked for a valid signature. If its provider event id was already processed, Payment returns 200 and changes nothing. Otherwise Payment records the event id and moves the charge forward only. The new state is published through an outbox row, so the event is not lost if the broker is down.
6. **Declined.** Order cancels and asks Inventory to release the hold at once. The cart is unchanged and the customer can retry.
7. **Succeeded in time.** Order asks Inventory to commit the reservation. Inventory checks `HELD` and `expires_at` in the same transaction that the sweeper uses, so a late commit cannot succeed after the hold has lapsed. Order becomes CONFIRMED and publishes OrderConfirmed. Cart empties on that event.
8. **Succeeded late.** If the hold has lapsed or the stock has gone, the commit fails. Order cancels as out of stock, emails the customer, and asks Payment for a full refund. Payment keeps the refund row open and retries with backoff until the provider confirms it. After repeated failures it alerts operations. The row is never dropped.

## Stores by service

| Service | What it stores |
|---|---|
| Cart | Cart and cart lines. Emptied only on OrderConfirmed. |
| Order | Orders, status, the price snapshot, short SKUs, and the outbox. |
| Inventory | Stock on hand, reservations with `expires_at`, and the release and commit records. |
| Payment | Charges keyed by order id, processed webhook event ids, refund rows, and the outbox. |

## Terminal states

| Outcome | Order status | Stock | Money | Cart |
|---|---|---|---|---|
| Short stock | REJECTED_SHORT_STOCK | Nothing held | Not charged | Unchanged, short items shown |
| Declined | CANCELLED_DECLINED | Released now | Not charged | Unchanged, retry allowed |
| Confirmed | CONFIRMED | Sold | Charged | Emptied |
| Late success | CANCELLED_OUT_OF_STOCK | Not sold to this order | Refund requested until it succeeds | Unchanged |

## Decisions and open points

- **Claim means commit.** The brief does not say what "claims the stock" means. This design treats it as the commit made after payment succeeds. That makes the 10-minute hold and the up-to-30-minute webhook wait collide, which is what produces the late-success path. Customers whose payment takes longer than 10 minutes will often hit that path, and product should accept that cost.
- **No re-reserve before refund.** If the stock is still free when a late payment arrives, the design could re-reserve it instead of refunding. The brief says to refund, so this is not included. It is a candidate change to discuss.
- **Timeouts are not rejections.** Order retries a commit that times out, using the same key. It refunds only when Inventory actually says the reservation is gone. Refunding on a timeout could refund a customer who did get the stock.
- **Lost webhooks.** Payment reconciles charges still pending after 35 minutes by querying the provider. This is an assumption added for safety, not part of the brief.
- **Delivery is at least once.** Every consumer checks the order's current state before acting. Duplicate events do nothing.
- **Cart edits during checkout.** If the customer edits the cart before OrderConfirmed arrives, the cart should remove only the confirmed lines, not clear everything. Otherwise new items would be lost.
- **Email owner.** The brief names no notification service, so this design has Order send the emails.
- **Provider key lifetime.** The provider must keep idempotency keys for longer than the 35-minute window, or the duplicate-charge guarantee depends on it.