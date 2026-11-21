Fulfilment flow v2 (diagram + notes, important stuff is mostly in the notes)

The Mailer just sends whatever OrderConfirmed/OrderCancelled it gets off the bus and writes the eventId into its seen-ids table after the send (it checks that table first), so in theory a crash between send and write can mail twice, which is fine since email is best-effort, and a failed send is just a throw like any other so it goes through the normal retries and the DLQ, and it never touches order status anyway, nothing does except OMS, which flips an order to CONFIRMED or CANCELLED only while it is still PENDING, when it consumes StockUnavailable or PaymentCaptured or PaymentDeclined, all in one transaction with its outbox row (OrderConfirmed/OrderCancelled) and its dedupe insert. Retries are 1 s, 10 s, 60 s, so four tries total, then the DLQ for that consumer group plus a page to on-call and the consumer carries on with the next message, and nothing gets rolled back, the order just stays in whatever status it had (e.g. PENDING with the stock hold still in place if it was PaySvc that dead-lettered). Card declines are not errors (that's the PaymentDeclined path: StockSvc drops the hold and OMS cancels) but card provider timeouts and 5xx are, so they go through the retry thing, and because PaySvc always sends orderId as the idempotency key a retry gets the first result back instead of double charging, which also covers PaySvc dying after the charge but before its commit: it never acked, so the StockReserved comes back, its eventId isn't in the seen table yet, the second charge call with the same key just returns the original capture, and then the commit goes through.

```mermaid
sequenceDiagram
    participant Pager as on-call
    participant DLQ
    actor U as user
    participant API as OrderSvc
    participant odb as OMS db
    participant rly as relay
    participant bus as the bus
    participant StockSvc
    participant sdb as stock db
    participant PaySvc
    participant pdb as pay db
    participant PSP as card provider
    participant Mailer
    participant mdb as mailer db
    U->>+API: POST
    API->>odb: write x2 (1 txn)
    Note right of Pager: 4 tries then DLQ + page
    API-->>-U: 202
    loop 500ms
        rly->>odb: poll
        rly->>bus: pub
        bus-->>rly: ok
        rly->>odb: mark
    end
    Note over rly: crash after ok, before mark = dup
    bus->>+StockSvc: OrderPlaced
    StockSvc->>sdb: hold + outbox + seen
    Note left of sdb: or StockUnavailable + seen, no hold
    StockSvc-->>-bus: (via relay) StockReserved / StockUnavailable
    bus->>+PaySvc: StockReserved
    PaySvc->>pdb: seen?
    PaySvc->>+PSP: charge (key orderId)
    PSP-->>-PaySvc: captured / declined
    PaySvc->>pdb: record + outbox + seen
    PaySvc-->>-bus: (via relay) PaymentCaptured / PaymentDeclined
    Note over PSP: timeout/5xx = throw = retry
    bus->>StockSvc: PaymentDeclined (if declined)
    StockSvc->>sdb: release + seen
    bus->>API: StockUnavailable / PaymentCaptured / PaymentDeclined
    API->>odb: status + outbox + seen
    Note right of odb: only if PENDING
    rly->>bus: OrderConfirmed / OrderCancelled
    bus->>Mailer: OrderConfirmed / OrderCancelled
    Mailer->>mdb: seen?
    Mailer->>U: mail
    Mailer->>mdb: seen
    Note over DLQ: per consumer group
```

Also: everything is on the order-events topic, keyed by orderId (so per-order ordering within each consumer group), each event has eventId/orderId/type and groups ignore types they don't care about. The relay (every 500 ms, oldest first, marks a row sent only after the broker's ack, so a crash between ack and mark means a republish, i.e. at-least-once) is the same in OrderSvc, StockSvc and PaySvc, each of which has its own outbox in its own DB written in the same txn as the state change, which is also why a service dying after its commit but before the relay got the row out loses nothing (the row is still unsent and goes out on the first poll after restart) and why a rolled-back txn never produces an event (there is no row); the request handler in the orders API publishes nothing itself, it just does the one-transaction insert of order (PENDING) + OrderPlaced outbox row and answers 202 with the orderId. Every consumer (OMS, inventory, payments, mailer) has its own consumer group and a dedupe table keyed on eventId in its own DB: it looks the eventId up first and if it's already there it acks and skips, otherwise it inserts it in the same transaction as the side effect and the outbox row, commits, then acks (the PK catches two copies racing), with the card call and the email being the two things that happen outside that txn. Payments only acts on StockReserved and ignores OrderPlaced, and the stock service only emits StockReserved after the hold commits, which is how 'no charge without stock' works.
