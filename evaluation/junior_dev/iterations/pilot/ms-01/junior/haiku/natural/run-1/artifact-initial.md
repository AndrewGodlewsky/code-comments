# Checkout across Cart, Inventory, Payment and Order

Checkout runs as four services. Order drives the flow. Inventory holds stock, Payment is the only service that talks to the payment provider, and Cart is written once, at the very end. Each service owns its tables. Services talk over HTTP or through broker events.

## Flow

```mermaid
flowchart TD
  START(["Customer presses Place order"]) --> O1

  subgraph ORDER["Order service"]
    O1["Create order, status PLACING<br/>stores: orders"]
    O2["Copy cart lines and prices into the order<br/>stores: order_lines, frozen snapshot"]
    O3["Status AWAITING_PAYMENT<br/>HTTP call asks Payment to charge"]
    O_SHORT["Status SHORT_STOCK<br/>stores: orders"]
    O_COMMIT["Ask Inventory to commit the reservation"]
    O_CONF["Status CONFIRMED<br/>publishes OrderConfirmed"]
    O_LATE["Status CANCELLED_OUT_OF_STOCK<br/>publishes OrderCancelledOutOfStock"]
    O_DEC["Status DECLINED"]
    O_MAIL["Email customer: out of stock, refunded in full"]
  end

  subgraph CART["Cart service"]
    C1["Return current lines and prices<br/>read only, nothing changes"]
    C2["Remove the ordered lines from the cart<br/>runs on OrderConfirmed, idempotent"]
  end

  subgraph INV["Inventory service"]
    I1["Reserve every line in one transaction<br/>stores: reservations ACTIVE, expires_at = now plus 10 min"]
    I2["Commit: check ACTIVE and not past expires_at<br/>stores: stock sold, reservation COMMITTED"]
    I3["Release reservation<br/>stores: reservation RELEASED"]
    I4["Sweeper every minute<br/>ACTIVE past expires_at becomes EXPIRED"]
  end

  subgraph PAY["Payment service, the only one that talks to the provider"]
    P1["Create charge row, key = order id<br/>stores: charges PENDING"]
    P2["Send charge to provider with Idempotency-Key = order id"]
    P3["Webhook in: store provider event id<br/>stores: webhook_events, unique event id"]
    P4["Set charge SUCCEEDED or DECLINED, only if still PENDING<br/>stores: outbox event"]
    P5["Create refund row, key = refund for order id<br/>stores: refunds REFUND_PENDING"]
    P6["Send full refund to provider with the same key"]
    P7["Refund webhook in, deduplicated by event id<br/>stores: refunds REFUNDED or REFUND_FAILED"]
    P8["Retry refund with backoff, alert ops after N tries<br/>row is never deleted"]
    P9["Reconciliation: no webhook after 30 min, query provider by order id"]
  end

  PROV["Payment provider, external"]

  D_STOCK{"Every line reserved?"}
  D_DUP{"Event id seen before?"}
  D_RES{"Reservation still ACTIVE?"}
  D_REF{"Provider confirmed refund?"}

  O1 --> C1 --> O2 --> I1 --> D_STOCK
  I1 -.->|"10 min hold clock"| I4

  D_STOCK -->|"No: some line short, nothing reserved"| O_SHORT --> E_SHORT(["Customer sees which items are short. Cart unchanged. No payment requested"])
  D_STOCK -->|"Yes"| O3 --> P1 --> P2 --> PROV
  O3 -.->|"timer starts"| P9

  PROV -.->|"Webhook: seconds, up to 30 min, may repeat"| P3 --> D_DUP
  D_DUP -->|"Yes: duplicate, no action, return 200"| E_DUP(["No second action"])
  D_DUP -->|"No: new event"| P4
  P9 -->|"outcome from provider query"| P4

  P4 -->|"DECLINED"| O_DEC --> I3 --> E_DEC(["Customer told payment declined. Cart unchanged. Retry uses a new order id"])
  P4 -->|"SUCCEEDED"| O_COMMIT --> I2 --> D_RES

  D_RES -->|"Yes: stock sold"| O_CONF --> C2 --> E_OK(["Customer sees confirmation. Cart emptied"])
  D_RES -->|"No: hold lapsed or released, late success"| O_LATE --> P5 --> P6 --> PROV
  PROV -.->|"Refund webhook, may repeat"| P7 --> D_REF
  D_REF -->|"Yes"| O_MAIL --> E_REF(["Customer refunded in full and emailed"])
  D_REF -->|"No: failed or no answer"| P8 --> P6
```

## How to read it

- Each box names its owner service, what it stores, and what triggers it.
- Solid arrows are HTTP calls or broker events. Dotted arrows are waits: webhooks, timers and the sweeper.
- Cart is written only at C2, after the order is confirmed. Every failure branch leaves the cart exactly as it was.
- No service reads another service's tables. Each cross-service fact arrives by call or event.

## What each service stores

| Service | Stores | Notes |
|---|---|---|
| Cart | Cart and cart lines | Read at Place order. Written only at C2. |
| Order | orders (status), order_lines (frozen snapshot), status history, processed event ids | The snapshot never changes after Place order. |
| Inventory | stock (on hand), reservations (order id, sku, qty, status, expires_at) | Available stock = on hand minus ACTIVE reservations. Keyed by order id. |
| Payment | charges (key = order id), refunds (key = refund for order id), webhook_events (unique provider event id), outbox | Only service with provider credentials. |

## Failure branches

| Branch | Where in diagram | What happens | Cart | Customer sees |
|---|---|---|---|---|
| Short stock | D_STOCK, No | Inventory reserves nothing, in one transaction. Order is SHORT_STOCK. No payment is requested. | Unchanged | The short items |
| Declined payment | P4, DECLINED | Order is DECLINED. Inventory releases the hold. | Unchanged | Decline message. Retrying creates a new order |
| Late success after hold lapsed | D_RES, No | Commit is refused. Order is CANCELLED_OUT_OF_STOCK. Payment refunds the full amount. Email is sent once the refund is confirmed. | Unchanged | Cancellation and refund email |
| Failed refund | D_REF, No | The refund row stays open and is retried with backoff. Ops is alerted after N tries. The row is never deleted. | Unchanged | No refund email until the refund succeeds |
| Duplicate webhook | D_DUP, Yes; same check at P7 | The provider event id is already stored, so nothing happens and 200 is returned. The conditional update (only if PENDING) blocks a second outcome for the same charge. | Unchanged | Nothing new |
| No webhook | P9 | After 30 min, Payment asks the provider by order id and feeds the answer into P4. | Unchanged | Pending page until resolved |

## Decisions beyond the brief (for review)

- Every Inventory call is keyed by order id, so reserve, commit and release can be retried safely.
- Each service writes its events through a transactional outbox, so a committed state change is never lost.
- The commit step checks expires_at itself and does not rely on the sweeper. The sweeper runs every minute, so a lapsed hold can still show ACTIVE for up to a minute.
- Late success is detected at commit time. The brief says refund, so the design does not try to re-reserve the stock.
- A retry after a decline must use a new order id. The provider key is the order id, so reusing it would return the original declined result.
- The reconciliation job (P9) is not in the brief. It is added so that an order cannot wait forever on a lost webhook.
- Order sends the customer email, because Order owns customer communication.

## Open questions

- Cart edits during checkout: should C2 remove only the ordered lines (by line id) and keep anything added later? This design assumes yes.
- Should the cart be locked during checkout? The brief does not require it, and this design does not lock it.
- Where does REFUND_FAILED alert go? Ops needs a named channel and a runbook.
- Should Order cancel early when the reservation expires, instead of waiting for the webhook? This design waits, because late success must still be handled.