# Checkout across Cart, Inventory, Payment and Order

## Shape of the design

- **Order is the orchestrator.** It starts checkout when the customer presses Place order, and it decides each next step from the replies and events it receives.
- **Cart is read-only until the order is confirmed.** It hands over a snapshot of its lines and prices, and it only removes lines after `OrderConfirmed`.
- **Inventory owns stock holds.** A hold lasts 10 minutes. Stock is taken only when a hold is claimed, and a hold that lapses returns stock to sale.
- **Payment is the only service that calls the payment provider.** It uses the order id as the idempotency key on charges and refunds. It records the provider's webhook outcomes, and it drops repeat webhooks.
- **Commands that need an answer use HTTP. Notifications use broker events.** Each service writes its state change and its outgoing event in one database transaction (transactional outbox). Each consumer records the ids of messages it has processed (inbox), so redelivery is harmless.

## Flowchart

```mermaid
flowchart TD
  Start(["Customer presses Place order"]) --> CartRead

  subgraph CART ["Cart service (own DB)"]
    CartRead["Read lines and prices from the cart<br/>cart is NOT changed"]
    CartClear["On OrderConfirmed: remove the ordered lines<br/>idempotent on order id"]
  end

  CartRead -->|"HTTP: cart snapshot"| OrderNew

  subgraph ORDER ["Order service (own DB, runs the checkout)"]
    OrderNew["Create order, state PLACED<br/>store lines and prices as a snapshot"]
    OrderShort["State REJECTED_OUT_OF_STOCK<br/>customer sees the short items"]
    OrderReserved["State RESERVED<br/>store reservation id"]
    OrderPending["State PAYMENT_PENDING"]
    OrderDeclined["State PAYMENT_DECLINED<br/>ask Inventory to release the hold"]
    OrderExpired["State RESERVATION_EXPIRED<br/>customer told hold lapsed, payment still awaited"]
    OrderClaim["On PaymentSucceeded: if state is still open<br/>(PAYMENT_PENDING or RESERVATION_EXPIRED),<br/>HTTP ClaimReservation, key = order id<br/>if already CONFIRMED or CANCELLED, do nothing"]
    OrderConfirmed["State CONFIRMED<br/>publish OrderConfirmed"]
    OrderLate["State CANCELLED_OUT_OF_STOCK"]
    OrderEmail["Email customer: order cancelled as out of stock, full refund"]
  end

  OrderNew -->|"HTTP: ReserveStock, all lines, key = order id"| StockCheck

  subgraph INV ["Inventory service (own DB)"]
    StockCheck{"Every line has enough free stock?"}
    NoHold["Write nothing<br/>return the list of short items"]
    Hold["One transaction: create reservation ACTIVE<br/>expires_at = now + 10 min, free stock goes down"]
    Sweep["Sweeper, about every minute:<br/>ACTIVE past expires_at becomes EXPIRED<br/>stock goes back on sale"]
    ClaimCheck{"Reservation still ACTIVE and not past expires_at?"}
    Claimed["Mark CLAIMED, stock now sold to this order<br/>repeat calls get the same answer"]
    ClaimLapsed["Return EXPIRED, change nothing"]
    Released["Mark RELEASED, stock back on sale"]
  end

  StockCheck -->|"No, a line is short"| NoHold
  StockCheck -->|"Yes"| Hold
  NoHold -->|"HTTP: SHORT"| OrderShort
  Hold -->|"HTTP: RESERVED"| OrderReserved
  OrderReserved --> OrderPending
  Sweep -.->|"event: ReservationExpired"| OrderExpired

  OrderPending -->|"HTTP: RequestCharge, key = order id"| PayStart

  subgraph PAY ["Payment service (own DB, only service that talks to the provider)"]
    PayStart["Store charge PENDING<br/>provider charge, idempotency key = order id"]
    Wait["Provider decides, outcome arrives by webhook<br/>usually seconds, up to 30 min"]
    Reconcile["Reconciliation: poll provider for charges PENDING over 35 min"]
    Hook["Webhook receiver: verify signature,<br/>insert provider event id into webhook_events"]
    Dup{"Event id already stored?"}
    Ack["Return 200, change nothing"]
    Outcome{"Provider outcome?"}
    Declined["Store charge DECLINED<br/>publish PaymentDeclined"]
    Succeeded["Store charge SUCCEEDED<br/>publish PaymentSucceeded"]
    RefundStart["Store refund PENDING<br/>provider refund, key = refund for order id, full amount"]
    RefundOut{"Refund outcome?"}
    Refunded["Store refund REFUNDED<br/>publish RefundSucceeded"]
    RefundFail["Store refund FAILED, row kept<br/>retry with backoff"]
    RefundAlert["After N failed tries alert on-call<br/>retries continue until REFUNDED"]
  end

  PayStart --> Wait
  Wait --> Hook
  Reconcile --> Outcome
  Hook --> Dup
  Dup -->|"Yes, duplicate"| Ack
  Dup -->|"No, new event"| Outcome
  Outcome -->|"Declined"| Declined
  Outcome -->|"Succeeded"| Succeeded

  Declined -->|"event: PaymentDeclined"| OrderDeclined
  OrderDeclined -->|"HTTP: ReleaseReservation"| Released
  Released --> DoneDecl(["Ends: payment declined, stock released, cart kept"])

  Succeeded -->|"event: PaymentSucceeded"| OrderClaim
  OrderClaim -->|"HTTP: ClaimReservation"| ClaimCheck
  ClaimCheck -->|"Yes"| Claimed
  ClaimCheck -->|"No, hold lapsed"| ClaimLapsed
  Claimed -->|"HTTP: CLAIMED"| OrderConfirmed
  OrderConfirmed -->|"event: OrderConfirmed"| CartClear
  CartClear --> DoneOk(["Ends: order CONFIRMED, ordered lines removed from cart"])

  ClaimLapsed -->|"HTTP: EXPIRED"| OrderLate
  OrderLate --> OrderEmail
  OrderEmail --> DoneLate
  OrderLate -->|"HTTP: RefundFull, key = order id"| RefundStart
  RefundStart --> RefundOut
  RefundOut -->|"Refunded"| Refunded
  RefundOut -->|"Failed"| RefundFail
  RefundFail -->|"retry"| RefundStart
  RefundFail --> RefundAlert
  Refunded -->|"event: RefundSucceeded"| DoneLate

  OrderShort --> DoneShort(["Ends: nothing reserved, nothing charged, cart kept"])

  Reconcile -.-> Hook
```

## Who stores what

| Service | Stores | Written when |
|---|---|---|
| Cart | Live cart and its lines; processed message ids | Customer edits the cart; ordered lines removed on `OrderConfirmed` |
| Order | Order row with state, price snapshot, reservation id, charge reference; outbox; inbox; email log | Each state change |
| Inventory | Stock per SKU (on hand, held); reservations (order id unique, lines, status ACTIVE / CLAIMED / RELEASED / EXPIRED, `expires_at`); outbox | Reserve, claim, release, sweep |
| Payment | Charges (order id unique, amount, status, provider ref); `webhook_events` (provider event id unique); refunds (order id unique, status, attempts, next retry); outbox | Charge, each webhook, each refund attempt |

## Failure branches

| Branch | What happens | Cart |
|---|---|---|
| Short stock | Inventory writes nothing and returns the short items. Order goes to REJECTED_OUT_OF_STOCK. No payment is requested. | Kept |
| Declined payment | Payment stores DECLINED and publishes `PaymentDeclined`. Order releases the hold, so stock goes back on sale. | Kept |
| Late success after hold lapsed | The hold lapses at 10 minutes and stock is released. The webhook arrives later. `ClaimReservation` returns EXPIRED, so Order cancels as out of stock, requests a full refund, and emails the customer. | Kept |
| Failed refund | Refund row is marked FAILED and kept. It is retried with backoff. After N failures, on-call is alerted, and reconciliation keeps retrying until REFUNDED. The refund is never dropped. | Kept |
| Duplicate webhook | Event id is already in `webhook_events`, so the service returns 200 and changes nothing. A duplicate `PaymentSucceeded` reaching Order is a no-op because the state is already final. A repeated claim gets the same answer. | Unchanged |
| Webhook never arrives | Reconciliation polls the provider for charges PENDING over 35 minutes and feeds the same outcome path. | Unchanged |
| Call result unknown (timeout) | Retry with the same order id key. Inventory reserve and claim are idempotent per order id. If the result is still unknown, Order asks Inventory for the reservation status before deciding. | Unchanged |

## Why the risky cases are safe

- **No double charge.** Payment keeps one charge per order id (unique key) and sends the order id to the provider as the idempotency key.
- **No double processing of webhooks.** The provider event id is stored with a unique constraint in the same transaction that changes the charge state.
- **Stock is never sold twice.** The claim is a conditional update: it succeeds only if the reservation is ACTIVE and `expires_at` is still in the future. Only one of a sweep and a claim can win.
- **No money kept for an unfulfillable order.** A claim that comes after the hold has lapsed always leads to a full refund.
- **Cart is never lost on failure.** Cart changes only after `OrderConfirmed`.

## Decisions to confirm

1. **Which cart lines are cleared.** The diagram removes only the ordered lines, so items added during checkout survive. Clearing the whole cart would be simpler, but it could drop those items.
2. **Provider charge on hold lapse.** The diagram leaves the provider charge running when the hold lapses. The provider may still succeed, which is why the refund path exists. Cancelling the pending charge, where the provider supports it, is an optional extra.
3. **Thresholds.** The N failed-refund tries before an alert, the 35-minute reconciliation age, and the sweeper interval are proposals, not requirements.
4. **Refund outcome channel.** The diagram assumes the refund result comes back either synchronously or by webhook. Confirm which the provider uses.