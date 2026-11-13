## Order fulfilment: move checkout to events

Today `POST /orders` calls Inventory, Payment and Notification synchronously inside the request. When one of them is slow, checkout times out, and we have had customers charged for stock we did not hold. We are replacing this with an event-driven flow, and before anyone writes code I want the flow drawn.

### Fixed

- **Accepting an order.** Order Service writes the order (status `PENDING`) and an `OrderPlaced` row in its `outbox` table in one database transaction, then returns `202 Accepted` with the order ID. The request handler never talks to the broker.
- **Relay.** A relay polls the outbox every 500 ms, publishes unsent rows oldest first, and marks a row sent only after the broker acknowledges it. If it dies between the ack and the mark, the row goes out again on the next poll. Delivery is therefore at-least-once.
- **Broker.** One topic, `order-events`, keyed by order ID, so each consumer group receives one order's events in the order they were published. Every event carries a unique `eventId`, the `orderId` and a type.
- **Services.** Inventory, Payment and Notification each have their own database and their own consumer group. Each must be safe when it receives the same event twice.
- **Business rules.** The card is never charged unless stock is reserved. Not enough stock: no charge, order cancelled. Card declined: the reservation is released and the order cancelled. Only Order Service changes order status, and the final statuses are `CONFIRMED` and `CANCELLED`.
- **Card provider.** It accepts an idempotency key; a repeat call with the same key returns the first result and does not charge again. A decline is a normal answer. A timeout or 5xx is an error.
- **Errors.** When handling a message throws, the consumer retries it after 1 s, 10 s and 60 s. If the fourth attempt fails too, the message goes to that group's dead-letter queue, on-call is paged and the consumer moves on. Nothing else is undone: the order keeps whatever status it has.
- **Email.** The customer gets a confirmation or a cancellation email. Email is best-effort: a failed send never changes the order status.

### Yours to decide

How consumers handle duplicates, how Inventory and Payment publish their own results, how Payment avoids a second charge, how Order Service learns the outcome, and what triggers the email.

### Format

A Mermaid `sequenceDiagram` covering the happy path and both cancellation paths, with short notes before or after it. Show where each piece of state is written and what happens on duplicates and failures.
