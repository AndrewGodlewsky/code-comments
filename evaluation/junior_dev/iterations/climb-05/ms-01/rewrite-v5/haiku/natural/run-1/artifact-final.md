# Checkout across Cart, Inventory, Payment and Order: flow design

## What this is

Checkout moves out of the monolith into four services: **Cart**, **Inventory**, **Payment** and **Order**. Each service has its own database and no service reads another's tables. Services talk to each other with HTTP calls or with events on a shared message broker.

Today checkout runs inside the monolith as one step. In the new design, the **Order** service drives checkout as a series of steps across the other three. Each service records its own state. A step that fails leads to a clear end state, and the customer's cart is never changed unless the order is confirmed.

The flow runs in this order. First, Inventory holds the stock for 10 minutes. Then Payment charges the customer. The hold is turned into a sale only when the payment succeeds while the hold is still valid. A payment can arrive late, after the hold has expired and the stock has gone to someone else. In that case the order is cancelled and the customer is refunded in full. Money is never kept for an order that cannot be filled.

Two rules hold everywhere:
- **Hold, then claim.** Stock is first held. It is sold (claimed) only after a successful payment, and only if the hold is still valid.
- **Idempotency keys.** The order id is the key for the reservation, the charge and the claim. If the same request or event arrives again, the work is not done a second time.

## Terms

- **Service**: a separate program with its own database. Each of the four services is one.
- **Order service**: the service that runs the checkout steps in order and records the order's status.
- **Snapshot**: a copy of the cart lines and prices, saved on the order when the customer presses Place order. Later cart changes do not touch it.
- **Hold (reservation)**: stock set aside for one order for 10 minutes. The units are not sold yet.
- **Claim**: turning a valid hold into sold stock.
- **Release**: giving held units back so they can be sold again.
- **Sweeper**: a background job in Inventory. It finds holds past their expiry time and releases them.
- **Payment provider**: the outside company that moves the money. Only the Payment service talks to it.
- **Charge**: a request to the provider to take the order total from the customer.
- **Refund**: a request to the provider to give money back.
- **Webhook**: a message the provider sends to Payment when the outcome of a charge or refund is known. It can take up to 30 minutes. It can arrive more than once.
- **Idempotency key**: an id sent with a request. If the same key comes again, the receiver does not repeat the work.
- **Event**: a message that says something happened, such as PaymentSucceeded. Services publish events to the broker, and other services react to them.
- **Outbox**: a table in Payment's database. An event is written there in the same transaction as the state change, so the event is not lost. A background job then publishes it.
- **Processed event ids**: the list of webhook ids Payment has already handled.
- **STUCK**: the state of a refund that has failed too many times. Operations staff are paged, and the row is kept.

## Flowchart

```mermaid
flowchart TD
    START_NODE(["Customer presses Place order<br/>Cart UI calls Order over HTTP"])
    PROV["Payment provider<br/>only the Payment service talks to it"]

    subgraph CART["Cart service: owns carts and cart lines"]
        C0["Return current lines and prices<br/>read only, cart unchanged"]
        C_CLEAR["On OrderConfirmed: remove the checked-out lines<br/>lines added after the snapshot stay"]
    end

    subgraph ORDER["Order service: owns orders, snapshot lines, order state"]
        O1["Create order PENDING_STOCK<br/>store snapshot: lines, unit prices, total"]
        O2["Ask Inventory to reserve every line<br/>key = order id"]
        O4["Order FAILED_SHORT_STOCK<br/>return the short items to customer"]
        O5["Ask Payment to charge the total<br/>key = order id"]
        O6["Order AWAITING_PAYMENT"]
        O7["Order FAILED_DECLINED"]
        O8["Ask Inventory to claim stock for order id"]
        O9{"Claim accepted?"}
        O10["Order CONFIRMED<br/>publish OrderConfirmed"]
        O11["Order CANCELLED_OUT_OF_STOCK<br/>ask Payment to refund full total"]
        O12["Email customer: cancelled as out of stock,<br/>full refund requested"]
    end

    subgraph INV["Inventory service: owns stock levels and reservations"]
        I1{"All lines available<br/>in one transaction?"}
        I_SHORT["Write nothing<br/>return the short SKUs"]
        I_HOLD["Write reservation HELD, expires_at = now + 10 min<br/>move units from available to held"]
        I_SWEEP["Sweeper: HELD past expires_at<br/>set EXPIRED, units back on sale"]
        I_REL["Release: set RELEASED<br/>units back on sale"]
        I_CLAIM{"Reservation still HELD<br/>and not expired?"}
        I_SOLD["Set CLAIMED<br/>units become sold to this order"]
        I_REFUSE["Refuse claim with reason<br/>expired or stock gone"]
    end

    subgraph PAY["Payment service: owns charges, refunds, processed event ids, outbox"]
        P1["Store charge PENDING<br/>key = order id"]
        P2["Send charge request to provider<br/>with idempotency key = order id"]
        P3["Provider webhook arrives<br/>signature checked, may repeat, up to 30 min"]
        P4{"Event id already recorded?"}
        P5["Return 200, do nothing"]
        P6["One DB transaction: record event id,<br/>charge PENDING to SUCCEEDED or DECLINED,<br/>write outbox row"]
        P7{"Outcome"}
        P8["Publish PaymentDeclined"]
        P9["Publish PaymentSucceeded"]
        P10["Store refund REQUESTED<br/>amount = full charge"]
        P11["Send refund to provider<br/>key = order id plus refund"]
        P12{"Refund accepted?"}
        P13["Refund webhook sets REFUNDED<br/>deduplicated like charge webhooks"]
        P14["Retry with backoff, same key<br/>after a set number of tries: STUCK, page ops, row kept"]
        P15["No webhook 30 min after charge:<br/>query provider, treat answer as a webhook"]
    end

    START_NODE --> C0
    C0 --> O1
    O1 --> O2
    O2 --> I1
    I1 -->|"some line short"| I_SHORT
    I_SHORT --> O4
    I1 -->|"all lines available"| I_HOLD
    I_HOLD -.->|"10 min pass, not claimed"| I_SWEEP
    I_HOLD --> O5
    O5 --> P1
    P1 --> P2
    P2 -->|"charge request"| PROV
    P2 -->|"accepted, outcome by webhook"| O6
    PROV -.->|"webhook"| P3
    P2 -.->|"no webhook after 30 min"| P15
    P15 --> P4
    P3 --> P4
    P4 -->|"yes, duplicate"| P5
    P4 -->|"no, new event"| P6
    P6 --> P7
    P7 -->|"declined"| P8
    P8 --> O7
    O7 --> I_REL
    O7 --> END_DECL(["Customer told payment declined<br/>cart unchanged, may retry"])
    P7 -->|"succeeded"| P9
    P9 --> O8
    O8 --> I_CLAIM
    I_CLAIM -->|"yes"| I_SOLD
    I_CLAIM -->|"no: late success"| I_REFUSE
    I_SOLD --> O9
    I_REFUSE --> O9
    O9 -->|"accepted"| O10
    O9 -->|"refused"| O11
    O10 --> C_CLEAR
    O10 --> END_OK(["Customer sees confirmation"])
    O11 --> O12
    O11 --> P10
    P10 --> P11
    P11 --> P12
    P12 -->|"yes"| P13
    P12 -->|"no"| P14
    P14 -.->|"retry"| P11
    P13 --> END_REFUND(["Customer has full refund<br/>order CANCELLED_OUT_OF_STOCK, refunded"])
    O4 --> END_SHORT(["Customer sees short items<br/>cart unchanged, no payment requested"])

    C_CLEAR ~~~ END_OK
```

## The steps

1. **Start.** The customer presses Place order. The Cart UI calls Order over HTTP. Order asks Cart for the current lines and prices. Cart only reads them. The cart does not change.
2. **Order saves the snapshot.** Order creates the order in state PENDING_STOCK. It stores the lines, unit prices and total. Nothing later changes these values.
3. **Reserve stock.** Order asks Inventory to reserve every line, using the order id as the key.
4. **Inventory checks all lines at once.** If any line is short, Inventory writes nothing and returns the short items. Order moves to FAILED_SHORT_STOCK. The customer sees the short items. The cart is unchanged. No payment is requested.
5. **Hold the stock.** If every line is available, Inventory writes a HELD reservation that expires 10 minutes from now. It moves those units from available to held. If nothing claims the hold in 10 minutes, the sweeper sets it to EXPIRED and puts the units back on sale.
6. **Charge the customer.** Order asks Payment to charge the total, using the order id as the key. Once Payment accepts, Order moves to AWAITING_PAYMENT.
7. **Send the charge.** Payment saves the charge as PENDING. It sends the charge request to the provider with the order id as the idempotency key. The provider accepts it and reports the outcome later by webhook.
8. **Receive the outcome.** The webhook can take up to 30 minutes and can arrive twice. Payment checks the signature, then checks the event id against its processed list.
   - If the event id is already there, Payment returns 200 and does nothing.
   - If it is new, Payment, in one database transaction, records the event id, sets the charge to SUCCEEDED or DECLINED, and writes an outbox row.
   - If no webhook arrives 30 minutes after the charge, Payment asks the provider for the outcome and treats the answer as a webhook.
9. **Declined.** Payment publishes PaymentDeclined. Order moves to FAILED_DECLINED and asks Inventory to release the hold. The customer is told the payment was declined. The cart is unchanged and the customer may try again.
10. **Succeeded: claim the stock.** Payment publishes PaymentSucceeded. Order asks Inventory to claim the stock. Inventory checks that the hold is still HELD and not expired.
    - If it is, Inventory sets the reservation to CLAIMED. The units become sold to this order. Go to step 11.
    - If it is not (a late success), Inventory refuses the claim and gives the reason. Go to step 12.
11. **Confirmed.** Order moves to CONFIRMED and publishes OrderConfirmed. Cart removes the lines that were checked out. Lines added after the snapshot stay in the cart. The customer sees the confirmation.
12. **Cancelled: refund in full.** Order moves to CANCELLED_OUT_OF_STOCK. It asks Payment to refund the full total and emails the customer that the order was cancelled as out of stock and a full refund was requested.
    - Payment saves the refund as REQUESTED for the full charge amount. It sends the refund to the provider with the key "order id plus refund".
    - When the provider accepts, a refund webhook sets the refund to REFUNDED. Repeat webhooks are ignored, as in step 8.
    - If the provider does not accept, Payment retries with backoff and the same key. After a set number of tries, the refund becomes STUCK. Operations staff are paged. The row is kept until it is resolved.

We never ship partial orders. A paid order is either confirmed in full or refunded in full.

## What happens when things fail

| Failure | What happens | Customer sees |
|---|---|---|
| A line is short | Inventory reserves nothing. No payment is requested. | The short items. Cart unchanged. |
| The payment is declined | Order releases the hold. | "Payment declined." Cart unchanged. May retry. |
| The payment succeeds after the hold has expired | Claim is refused. The order is cancelled and refunded in full. | A cancellation email and a full refund. |
| The same webhook arrives twice | The second copy is recognised by its event id and ignored. | Nothing extra. |
| The provider never sends the webhook | After 30 minutes Payment asks the provider for the outcome. | Delayed confirmation. |
| A retried charge request | The same idempotency key means the provider does not charge twice. | Nothing extra. |
| The refund is not accepted | Payment retries with the same key. After a set number of tries it marks the refund STUCK, pages operations and keeps the row. | A refund is still owed. Operations resolves it. The refund is never dropped. |
| Checkout fails for any reason | The cart is not changed. | The cart exactly as it was. |

## Open questions

- How many refund tries happen before a refund becomes STUCK, and how long is the backoff between them?
- What happens if Payment cannot reach the provider when it sends the charge? The brief does not say.
- What happens if Order's claim call to Inventory gets no reply? The stock may or may not have been claimed.
- What happens if Cart fails to remove the checked-out lines after the order is confirmed?

## Notes on the flowchart

- Dashed arrows are events that happen later: the 10-minute expiry, the webhook, the 30-minute check and the refund retries.
- Solid arrows are steps that happen right away.
- Each box is labelled with the service that owns it. Each service writes only to its own database.
- The end boxes show what the customer sees in each outcome.