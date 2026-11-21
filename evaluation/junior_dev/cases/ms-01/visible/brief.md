## Checkout across Cart, Inventory, Payment and Order

We're moving checkout out of the monolith into four services that already exist as stubs: **Cart**, **Inventory**, **Payment** and **Order**. I need a design for the whole checkout flow, including the bad case where a customer's payment goes through after the stock they wanted has gone.

### Fixed requirements

- Each service owns its own database. No service reads another's tables. Services talk over HTTP or through events on the shared message broker.
- Checkout starts when the customer presses **Place order**. The order records the cart's lines and prices as they were at that moment. Later cart edits or price changes don't affect it.
- Stock is reserved **before** any payment is requested. Reservation is all-or-nothing: if any line is short, nothing is reserved, no payment is requested, and the customer is told which items are short.
- A reservation holds stock for **10 minutes**. If the order hasn't claimed the stock by then, it goes back on sale.
- Only the Payment service talks to the payment provider. Every charge request carries the **order id as the idempotency key**, so a retried request can never charge the customer twice.
- The provider reports the outcome (succeeded or declined) by webhook. This usually takes seconds but can take up to **30 minutes**, and the same webhook may be delivered more than once. A repeat must not be processed twice.
- Because of that delay, a payment can succeed after the hold has lapsed and the stock has been sold to someone else. We never keep money for an order we can't fulfil: refund the full amount automatically, cancel the order as out of stock, and email the customer. We don't ship partial orders.
- Refunds can fail at the provider. A refund must never be silently dropped.
- The cart is emptied only once the order is confirmed. If checkout fails for any reason, the cart stays exactly as it was so the customer can try again.

### What I want

A **Mermaid flowchart** of the checkout, with short notes before or after it. Show which service does each step, what triggers it, what each service stores, and every failure branch above: short stock, declined payment, late success after the hold lapsed, failed refund, and duplicate webhooks. Someone who has never seen our stack should be able to follow it.
