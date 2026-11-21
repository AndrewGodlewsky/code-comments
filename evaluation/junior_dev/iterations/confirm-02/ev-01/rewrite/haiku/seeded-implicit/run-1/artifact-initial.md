## Order fulfilment (event-driven)

Parts: Order Service, a broker topic (order-events), Inventory, Payment (talks to the card provider) and Notification. Producers publish through an outbox and relay. Consumers are idempotent. Usual retries and a DLQ.

```mermaid
sequenceDiagram
    actor Customer
    participant Order
    participant Broker
    participant Inventory
    participant Payment
    participant Notification
    Customer->>Order: place order
    Order-->>Customer: 202
    Order->>Broker: OrderPlaced (via outbox)
    Broker->>Inventory: OrderPlaced
    Inventory->>Broker: StockReserved (via outbox)
    Broker->>Payment: StockReserved
    Payment->>Broker: PaymentCaptured (via outbox)
    Broker->>Order: PaymentCaptured
    Order->>Broker: OrderConfirmed (via outbox)
    Broker->>Notification: OrderConfirmed
    Notification->>Customer: email
```

Unhappy paths: StockUnavailable and PaymentDeclined, both ending in OrderCancelled and a cancellation email. Payment uses an idempotency key with the card provider.
