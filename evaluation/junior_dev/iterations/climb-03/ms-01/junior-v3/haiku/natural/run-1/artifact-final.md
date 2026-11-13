# Checkout across Cart, Inventory, Payment and Order

## What this is

Order runs checkout. It reads the cart snapshot from Cart, holds stock in Inventory, asks Payment to charge the customer, and then confirms the order or cancels it. Stock is held before any money is requested. Main flow: Place order, then cart snapshot, then hold stock for 10 minutes, then charge, then the provider's webhook says paid, then claim the hold, then the order is CONFIRMED and its lines leave the cart. If the payment succeeds after the hold has lapsed, the order is cancelled, emailed and refunded in full.

## Terms

- **Snapshot**: the cart's lines and prices, copied into the order when Place order is pressed.
- **Hold**: Inventory's 10-minute reservation of stock for one order. It ends in a claim or it lapses.
- **Claim**: turns an ACTIVE hold that has not expired into sold stock.
- **Idempotency key**: an id sent with a request. Repeating the request with the same key has no further effect. For holds, charges and refunds the key is the order id.
- **Charge / refund**: Payment's record of one payment or refund, keyed by order id.
- **Webhook**: the provider's HTTP call to Payment that reports a charge outcome.
- **Inbox**: Payment's table of webhook event ids it has already handled. A repeat is skipped.
- **Outbox**: each service writes its outgoing event in the same transaction as its state change. A relay publishes it to the **broker**.
- **Communication**: HTTP when a caller needs an answer. Broker events for notifications. Solid arrows below are HTTP, dashed arrows are events.

## Flowchart

```mermaid
flowchart TD
  Start(["Customer presses Place order"]) --> CartRead

  subgraph CART ["Cart service (own DB)"]
    CartRead["Return lines and prices<br/>cart NOT changed"]
    CartClear["On OrderConfirmed: remove the ordered lines<br/>safe to repeat"]
  end

  CartRead -->|"HTTP: cart snapshot"| OrderNew

  subgraph ORDER ["Order service (own DB, runs checkout)"]
    OrderNew["Create order PLACED<br/>store snapshot of lines and prices"]
    OrderPending["Store hold id, state PAYMENT_PENDING"]
    OrderShort["REJECTED_OUT_OF_STOCK<br/>customer sees short items"]
    OrderDeclined["PAYMENT_DECLINED<br/>release hold"]
    OrderLapsed["RESERVATION_EXPIRED<br/>customer told hold lapsed, payment still awaited"]
    OrderCheck{"State still PAYMENT_PENDING<br/>or RESERVATION_EXPIRED?"}
    OrderConfirmed["CONFIRMED<br/>publish OrderConfirmed"]
    OrderCancelled["CANCELLED_OUT_OF_STOCK<br/>email customer: cancelled, full refund"]
  end

  OrderNew -->|"HTTP: ReserveStock, all lines, key = order id"| StockCheck

  subgraph INV ["Inventory service (own DB)"]
    StockCheck{"Every line has enough free stock?"}
    NoHold["Write nothing<br/>return the short items"]
    Hold["One transaction: hold ACTIVE<br/>expires_at = now + 10 min, free stock down"]
    Sweep["Every minute: ACTIVE holds past expires_at<br/>become EXPIRED, stock back on sale"]
    ClaimCheck{"Hold ACTIVE and not past expires_at?"}
    Claimed["CLAIMED: stock sold to this order"]
    ClaimLapsed["Return EXPIRED, change nothing"]
    Released["RELEASED: stock back on sale"]
  end

  StockCheck -->|"No: a line is short"| NoHold
  StockCheck -->|"Yes"| Hold
  NoHold -->|"HTTP: SHORT, items"| OrderShort
  OrderShort --> DoneShort(["Ends: nothing reserved, nothing charged, cart kept"])
  Hold -->|"HTTP: RESERVED, hold id"| OrderPending
  Sweep -.->|"event: ReservationExpired"| OrderLapsed

  OrderPending -->|"HTTP: RequestCharge, key = order id"| PayStart

  subgraph PAY ["Payment service (own DB, only service that calls the provider)"]
    PayStart["Store charge PENDING<br/>provider charge, key = order id"]
    Hook["Webhook: verify signature<br/>one transaction: insert event id in inbox, update charge"]
    Dup{"Event id already in inbox?"}
    Ack["Return 200, change nothing"]
    Recon["Every 5 min: ask provider about PENDING charges older than 35 min"]
    Outcome{"Charge still PENDING?<br/>then provider says succeeded or declined"}
    Declined["Charge DECLINED<br/>publish PaymentDeclined"]
    Succeeded["Charge SUCCEEDED<br/>publish PaymentSucceeded"]
    RefundStart["Store refund PENDING<br/>provider refund, key = order id, full amount"]
    RefundOut{"Refund outcome?"}
    Refunded["Refund REFUNDED<br/>publish RefundSucceeded"]
    RefundFail["Refund FAILED, row kept<br/>retry with backoff, alert on-call after N tries"]
  end

  Provider(["Payment provider decides<br/>webhook: usually seconds, up to 30 min"])
  PayStart -->|"provider charge"| Provider
  Provider -->|"webhook"| Hook
  Hook --> Dup
  Dup -->|"Yes: duplicate"| Ack
  Dup -->|"No: new event"| Outcome
  Recon -->|"poll result"| Outcome
  Outcome -->|"Already final: change nothing"| Ack
  Outcome -->|"Declined"| Declined
  Outcome -->|"Succeeded"| Succeeded

  Declined -->|"event: PaymentDeclined"| OrderDeclined
  OrderDeclined -->|"HTTP: ReleaseReservation"| Released
  Released --> DoneDecl(["Ends: payment declined, stock back on sale, cart kept"])

  Succeeded -->|"event: PaymentSucceeded"| OrderCheck
  OrderCheck -->|"No: already CONFIRMED or CANCELLED"| DoneDup(["Ends: duplicate event, nothing to do"])
  OrderCheck -->|"Yes: HTTP ClaimReservation, key = order id"| ClaimCheck
  ClaimCheck -->|"Yes"| Claimed
  ClaimCheck -->|"No: hold lapsed"| ClaimLapsed
  Claimed -->|"HTTP: CLAIMED"| OrderConfirmed
  OrderConfirmed -->|"event: OrderConfirmed"| CartClear
  CartClear --> DoneOk(["Ends: order CONFIRMED, ordered lines removed from cart"])

  ClaimLapsed -->|"HTTP: EXPIRED"| OrderCancelled
  OrderCancelled -->|"HTTP: RefundFull, key = order id"| RefundStart
  OrderCancelled --> DoneLate(["Ends: order cancelled and emailed, refund runs separately"])
  RefundStart --> RefundOut
  RefundOut -->|"Refunded"| Refunded
  RefundOut -->|"Failed"| RefundFail
  RefundFail -->|"retry"| RefundStart
  Refunded --> DoneRefund(["Ends: refund REFUNDED"])
```

## Failure cases

| Case | What happens | Where it ends |
|---|---|---|
| A line is short | Inventory writes nothing. Order sets REJECTED_OUT_OF_STOCK and shows the short items. | Nothing reserved, nothing charged, cart kept |
| Payment declined | Payment marks the charge DECLINED. Order releases the hold. | Stock back on sale, cart kept |
| Hold lapses before the webhook | Sweeper marks the hold EXPIRED. Order tells the customer the hold lapsed and keeps waiting for payment. | Still open until the webhook arrives |
| Payment succeeds after the hold lapsed | The claim returns EXPIRED. Order cancels as out of stock, emails the customer and asks Payment for a full refund. | Order cancelled, refund runs separately |
| Refund fails at the provider | The refund row stays FAILED. Payment retries with backoff and alerts on-call after N tries. | Never dropped silently |
| Duplicate webhook | The event id is already in the inbox. Payment returns 200 and changes nothing. | No change |
| Webhook and poll both report the outcome | Whichever arrives second finds the charge already final and changes nothing. | No change |
| Checkout fails at any other point | The cart is never emptied before CONFIRMED. | Cart kept, customer can try again |

## Open questions

- What is N, the number of refund retries before an alert?
- Is the customer told if a refund finally fails after the cancellation email?
- What happens when an HTTP reply is lost? The idempotency key makes a retry safe, but the retry rule is not set here.
- Does the every-5-minutes poll (Recon) stay? The brief does not require it. It is the only way to learn an outcome if a webhook is lost.