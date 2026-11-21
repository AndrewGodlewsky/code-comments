## Checkout design: the Order service orchestrates

Each service keeps its own state. No service reads another's database.

| Service | What it stores in its own DB |
|---|---|
| Cart | the customer's cart lines |
| Order | the order: line and price snapshot taken at *Place order*, plus its **status**. The status is the only record of how far a checkout has got. |
| Inventory | stock levels; reservations with `expires_at` = created + 10 min |
| Payment | one payment row per order (provider payment id is unique); refund rows with status and attempt count |

Order statuses: `PENDING` -> `AWAITING_PAYMENT` -> `CONFIRMED`, or one of `REJECTED_SHORT_STOCK`, `PAYMENT_FAILED`, `REFUNDING` -> `CANCELLED_OUT_OF_STOCK`.

Arrows: a solid arrow is the next step or a synchronous HTTP call. A dotted arrow is an event on the message broker.

```mermaid
flowchart TD
    placeOrder(["Customer presses Place order"]) --> createOrder["Order: fetch cart from Cart over HTTP,<br/>save order PENDING with line + price snapshot"]
    createOrder --> reserve{"Order asks Inventory to reserve all lines.<br/>Every line in stock?"}
    reserve -->|"no"| shortStock["Inventory reserves nothing.<br/>Order: status REJECTED_SHORT_STOCK,<br/>customer shown the short items.<br/>No payment requested, cart untouched"]
    reserve -->|"yes"| held["Inventory: save reservation,<br/>expires in 10 min"]
    held --> requestPay["Order: status AWAITING_PAYMENT,<br/>asks Payment to charge"]
    requestPay --> charge["Payment: save payment row,<br/>send charge to provider,<br/>idempotency key = order id"]
    charge --> webhook["Provider webhook to Payment:<br/>seconds to 30 min later,<br/>may arrive more than once"]
    webhook --> dup{"Payment: provider payment id<br/>already recorded?"}
    dup -->|"yes"| ignoreHook["Acknowledge webhook, do nothing"]
    dup -->|"no"| publishPay["Payment: record outcome,<br/>publish PaymentSucceeded or PaymentFailed"]
    publishPay -.-> awaiting{"Order: is the order still<br/>AWAITING_PAYMENT?"}
    awaiting -->|"no, already handled"| ignoreEvent["Ignore event"]
    awaiting -->|"PaymentFailed"| declined["Order: ask Inventory to release<br/>the reservation now,<br/>status PAYMENT_FAILED, cart untouched"]
    awaiting -->|"PaymentSucceeded"| confirmRes{"Order asks Inventory to confirm<br/>the reservation. Still active?"}
    confirmRes -->|"yes"| commitStock["Inventory: commit stock,<br/>drop reservation"]
    confirmRes -->|"no, expired"| retryRes{"Order asks Inventory for ONE fresh<br/>all-or-nothing reservation<br/>of the same lines. All in stock?"}
    retryRes -->|"yes"| commitStock
    retryRes -->|"no"| refunding["Order: status REFUNDING,<br/>asks Payment to refund the full amount"]
    commitStock --> confirmed["Order: status CONFIRMED,<br/>email confirmation,<br/>publish OrderConfirmed"]
    confirmed -.-> clearCart["Cart: delete the cart"]
    refunding --> refund{"Payment sends refund to provider,<br/>idempotency key = order id + refund.<br/>Accepted?"}
    refund -->|"no"| retryRefund["Payment: refund row PENDING,<br/>retry every 5 min, up to 12 tries"]
    retryRefund -->|"next try"| refund
    retryRefund -->|"12th try failed"| manual["Payment: mark refund MANUAL,<br/>alert support on-call.<br/>Order stays REFUNDING"]
    refund -->|"yes"| refunded["Payment: publish PaymentRefunded"]
    refunded -.-> cancelled["Order: status CANCELLED_OUT_OF_STOCK,<br/>email customer: refunded, item sold out.<br/>Cart untouched"]
    held -->|"not confirmed within 10 min"| sweeper["Inventory sweeper, runs every minute:<br/>releases the reservation,<br/>stock back on sale"]
```

### Notes

- **Retries without double charging.** If the call from Order to Payment, or from Payment to the provider, times out, it is retried with the same key: the order id for a charge, and order id + "refund" for a refund. The provider returns the original charge or refund instead of making a new one.
- **Duplicates.** Payment drops a webhook whose provider payment id is already in its DB. Broker events can also repeat. Order acts on a payment event only while the order is `AWAITING_PAYMENT`, so a repeat finds the order already moved on and is ignored.
- **Expiry.** The Order service doesn't run the 10-minute timer; Inventory's sweeper does. Order only learns that the hold lapsed when confirm returns "expired". A declined payment releases stock at once instead of waiting for the sweeper.
- **Late success.** It gets exactly one fresh reservation attempt, and an order is never fulfilled partially. If that attempt fails, the customer gets a full refund, the order becomes `CANCELLED_OUT_OF_STOCK`, and the customer is emailed.
- **Refund failure.** The retry state lives in Payment's refund row (status, attempt count). After 12 failed tries (about 1 hour) the refund becomes `MANUAL` and support is alerted. The order stays `REFUNDING` until `PaymentRefunded` arrives.
- **Cart.** Only the Cart service deletes a cart, and only when it receives `OrderConfirmed`. Every failure path leaves the cart as it was.
