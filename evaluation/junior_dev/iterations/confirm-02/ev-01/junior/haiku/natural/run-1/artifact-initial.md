# Order fulfilment: event-driven checkout flow

Status: proposed design, for review before any code is written.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Cust as Customer
    participant OS as Order Service
    participant RL as Order relay
    participant BR as Broker order-events
    participant INV as Inventory
    participant PAY as Payment
    participant CARD as Card provider
    participant NT as Notification
    participant MAIL as Email provider

    Note over Cust,OS: Accept the order (no broker call in the request)
    Cust->>OS: POST /orders
    Note over OS: One tx: insert orders row PENDING and outbox row OrderPlaced
    OS-->>Cust: 202 Accepted with orderId
    RL->>BR: publish OrderPlaced, key orderId, mark sent only after ack
    BR->>INV: deliver OrderPlaced

    alt Enough stock (happy path and card decline)
        Note over INV: One tx: processed_events insert, reservation row unique on orderId, outbox row StockReserved
        INV->>BR: publish StockReserved via Inventory relay
        BR->>PAY: deliver StockReserved
        Note over PAY: One tx: processed_events insert, payments row unique on orderId, status ATTEMPTING
        PAY->>CARD: charge, idempotency key orderId
        alt Card accepts
            CARD-->>PAY: charged
            Note over PAY: One tx: payments status CHARGED, outbox row PaymentCharged
            PAY->>BR: publish PaymentCharged via Payment relay
            BR->>OS: deliver PaymentCharged
            Note over OS: One tx: processed_events insert, UPDATE orders to CONFIRMED WHERE PENDING, outbox row OrderConfirmed
            OS->>BR: publish OrderConfirmed via Order relay
            BR->>NT: deliver OrderConfirmed
            Note over NT: Record notification row keyed by eventId
            NT->>MAIL: confirmation email, best-effort
        else Card declines (normal answer, not an error)
            CARD-->>PAY: declined
            Note over PAY: One tx: payments status DECLINED, outbox row PaymentDeclined
            PAY->>BR: publish PaymentDeclined via Payment relay
            par Release the reservation
                BR->>INV: deliver PaymentDeclined
                Note over INV: One tx: processed_events insert, reservation RELEASED (no-op if already released)
            and Cancel the order
                BR->>OS: deliver PaymentDeclined
                Note over OS: One tx: processed_events insert, UPDATE orders to CANCELLED WHERE PENDING, outbox row OrderCancelled
                OS->>BR: publish OrderCancelled via Order relay
                BR->>NT: deliver OrderCancelled
                NT->>MAIL: cancellation email, best-effort
            end
        end
    else Not enough stock (no charge)
        Note over INV: One tx: processed_events insert, outbox row StockRejected, nothing reserved
        INV->>BR: publish StockRejected via Inventory relay
        BR->>OS: deliver StockRejected
        Note over OS: One tx: processed_events insert, UPDATE orders to CANCELLED WHERE PENDING, outbox row OrderCancelled
        OS->>BR: publish OrderCancelled via Order relay
        BR->>NT: deliver OrderCancelled
        NT->>MAIL: cancellation email, best-effort
        Note over PAY: Never receives an event, so the card is never called
    end

    opt Duplicate delivery (relay crashed after ack, before mark)
        BR->>OS: deliver PaymentCharged again
        Note over OS: processed_events hit, no-op, nothing published
    end

    opt Card timeout or 5xx during charge
        CARD-->>PAY: timeout or 5xx error
        Note over PAY: Handler throws, outbox untouched, payments row stays ATTEMPTING
        loop Retry after 1 s, 10 s and 60 s
            BR->>PAY: redeliver StockReserved
            PAY->>CARD: charge, same key orderId
            Note over CARD: Returns the first result if an earlier call already charged
        end
        Note over BR,PAY: If the 4th attempt also fails
        BR->>PAY: move message to Payment dead-letter queue
        Note over PAY: Page on-call and move on. Order keeps PENDING. Stock stays reserved until a human acts.
    end
```

## Where each piece of state is written

| Service | Table or store | Written when | Key |
|---|---|---|---|
| Order Service | `orders` | Accept (PENDING), then CONFIRMED or CANCELLED | `orderId`. Transitions are guarded by `WHERE status = 'PENDING'`. |
| Order Service | `outbox` | Same tx as each status change | `eventId` |
| Inventory | `reservations` | Reserve, or release on PaymentDeclined | unique `orderId` |
| Inventory | `outbox` | StockReserved or StockRejected | `eventId` |
| Payment | `payments` | ATTEMPTING before the card call, then CHARGED or DECLINED | unique `orderId` |
| Payment | `outbox` | PaymentCharged or PaymentDeclined | `eventId` |
| Notification | `notifications` | Email attempt and result | `eventId` |
| Each consumer | `processed_events` | In the same tx as its state change | `eventId` |

Only Order Service writes order status. Only Order Service publishes OrderConfirmed and OrderCancelled.

## Decisions (the brief's "yours to decide" list)

- **Duplicates.** Every consumer inserts the incoming `eventId` into its own `processed_events` table in the same local transaction as its state change. A second delivery hits the primary key and does nothing. Each state change is also guarded by a natural key (unique `orderId`, or `WHERE status = ...`), so the logic stays correct even if the dedupe row were lost.
- **Inventory and Payment results.** Each service publishes its own result through its own outbox and relay, to `order-events`, keyed by `orderId`. Results are never sent by direct call.
- **Payment avoids a second charge.** The card call uses idempotency key `orderId`, not `eventId`. Redelivery, handler retry, and a crash between "card charged" and "CHARGED saved" all reuse the same key, and the provider returns the first result. If the `payments` row already says CHARGED or DECLINED, Payment does not call the card and only re-publishes from its outbox.
- **How Order Service learns the outcome.** Order Service is a consumer of `order-events` like the others. It applies PaymentCharged as CONFIRMED, and StockRejected or PaymentDeclined as CANCELLED. These outcomes are mutually exclusive by construction, because Payment only runs after a reservation and only Inventory emits StockRejected, so the guarded transition cannot flip a status.
- **What triggers the email.** Notification reacts only to OrderConfirmed and OrderCancelled, never to raw inventory or payment events. The email is therefore tied to a status that Order Service has committed.
- **Email failure.** Notification records the send attempt and its result. A failed send is recorded and does not change order status. My recommendation is that it does not enter the retry or DLQ path, so it stays best-effort. The brief does not settle this, so please confirm.
- **Ordering.** A single topic keyed by `orderId` keeps each order's events in publish order within a partition. Cross-producer order is also safe by causality: each event is published only after the event that caused it has been consumed.

## Consequences and open holes

1. **Dead-lettered orders stay PENDING.** If Payment's card keeps failing, the order is stuck until a human re-drives or cancels it, and stock stays reserved meanwhile. The brief says "nothing else is undone", so this needs an on-call runbook, not an automatic fix.
2. **Charged but dead-lettered.** If the card charged but Payment could not save or publish the result, the customer may be charged for an order that stays PENDING. Re-driving the DLQ message is safe because of the idempotency key. A reconciliation job that compares the provider with `payments` would catch cases where nobody re-drives. This is a proposal, not something the brief asks for.
3. **In-place retries block the partition.** The 1 s, 10 s and 60 s retries pause the consumer, so other orders that share its partition wait too. Keeping one topic rules out separate retry topics. If that delay is unacceptable, the choice needs revisiting.
4. **Relay must be single-writer per outbox.** Two concurrent relays could publish one order's rows out of order. Each service's relay runs as one active instance, or uses a row lock.
5. **Retention.** `processed_events` must be kept at least as long as the broker can redeliver. The card provider's idempotency window must also cover the longest retry chain, which is roughly 71 s plus the time to reach the 4th attempt.
6. **Notification duplicates at the provider.** If the email provider accepts a message but the consumer crashes before recording it, the customer may get a second email. Passing `eventId` as the provider's idempotency key, where supported, reduces this.
