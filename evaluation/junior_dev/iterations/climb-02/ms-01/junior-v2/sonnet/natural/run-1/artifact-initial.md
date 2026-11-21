# Checkout across Cart, Inventory, Payment and Order

## How to read this

- **Order** coordinates checkout. It decides what happens next after each event and owns the order's status.
- The other three services do one job each and report back with an event: **Cart** holds the basket, **Inventory** holds stock, and **Payment** talks to the payment provider.
- Services never read each other's tables. Two things cross a service boundary:
  - **HTTP calls** are used where the caller needs an answer straight away (Order asking Cart for the basket).
  - **Events on the broker** are used for everything else. A box labelled `emit X` publishes event X.
- Every service writes its state change and its outgoing event in the same database transaction (an outbox table). A separate relay then publishes the event.
  - A crash can therefore never leave "state changed, event lost".
  - Events are delivered at least once, so each consumer keeps an inbox table of event ids it has already handled and ignores repeats.

## Flowchart

```mermaid
flowchart TD
    CUST(["Customer presses Place order"])

    subgraph ORDER["ORDER service. Stores: orders, order lines and prices snapshot, status, refund status, outbox, inbox"]
        O1["Create order with new order id, status PLACED. Save cart lines and prices as they are right now"]
        O2["Status REJECTED_SHORT_STOCK. Save the list of short items. Tell the customer which items are short"]
        O3["Status AWAITING_PAYMENT. emit PaymentRequested with order id and total"]
        O4["Status PAYMENT_DECLINED. Tell the customer. emit ReleaseStock"]
        O5["Ask Inventory to claim the stock: emit ClaimStock"]
        O6["Status CONFIRMED. emit OrderConfirmed. Send confirmation email"]
        O7["Status CANCELLED_OUT_OF_STOCK, refund PENDING. Send out-of-stock email saying a full refund is on its way. emit RefundRequested with full amount"]
        O8["Refund status REFUNDED. Send refund-complete email"]
        O9["Refund status STUCK. Order stays cancelled. Ops alerted"]
    end

    subgraph CART["CART service. Stores: carts, cart lines, current prices"]
        K1["Return the cart's current lines and prices. Read only, cart not changed"]
        K2["Empty the cart"]
        K0["Cart left exactly as it was. Customer can retry"]
    end

    subgraph INV["INVENTORY service. Stores: stock levels, reservations with order id, lines, expires_at and state HELD, CLAIMED, RELEASED or EXPIRED, outbox, inbox"]
        I1["Try to reserve every line in one database transaction"]
        D1{"Is every line in stock?"}
        I2["Reserve nothing. emit StockShort with the short items"]
        I3["Create hold on all lines, expires_at = now + 10 minutes. emit StockReserved"]
        I4["Expiry job runs every minute: any HELD reservation past expires_at becomes EXPIRED and its stock goes back on sale"]
        I5["Claim in one transaction"]
        D2{"Hold still HELD, or lapsed but every line still free right now?"}
        I6["Reservation becomes CLAIMED. Stock is sold. emit StockClaimed"]
        I7["Nothing is taken. emit StockClaimFailed"]
        I8["Reservation becomes RELEASED. Stock back on sale"]
    end

    subgraph PAY["PAYMENT service. Stores: payments, webhook_events with unique provider event id, refunds with state and attempt count, outbox, inbox"]
        P1["Create payment record PENDING. Send charge to provider with idempotency key = order id. Retry on timeout with the same key"]
        PROV[["Payment provider. Reports result by webhook, usually seconds, up to 30 minutes"]]
        P2["Webhook received. Verify signature"]
        D3{"Provider event id already in webhook_events?"}
        P3["Duplicate. Do nothing, reply 200 OK"]
        P4["Store event in webhook_events, update payment, reply 200 OK"]
        D4{"Provider outcome?"}
        P5["emit PaymentDeclined"]
        P6["emit PaymentSucceeded"]
        P7["Create or load refund record for the order: full amount, PENDING. Send refund to provider with idempotency key refund-order id"]
        D5{"Provider accepted and completed the refund?"}
        P8["Refund state REFUNDED. emit RefundSucceeded"]
        P9["Refund state FAILED. Keep the record. Retry later with backoff using the same key"]
        D6{"More than the retry limit?"}
        P10["Refund state STUCK. emit RefundStuck and raise an ops alert. Record stays open for manual action"]
    end

    CUST -->|"HTTP: create order for cart"| O1
    O1 -->|"HTTP: get cart lines and prices"| K1
    K1 -->|"lines and prices returned"| O1
    O1 -->|"emit OrderPlaced with the snapshot lines"| I1
    I1 --> D1
    D1 -->|"No, any line short"| I2
    D1 -->|"Yes, all lines"| I3
    I2 -->|"event StockShort"| O2
    O2 --> K0
    I3 -->|"event StockReserved"| O3
    I3 -.->|"10 minutes pass without a claim"| I4
    O3 -->|"event PaymentRequested"| P1
    P1 -->|"HTTP: charge, key = order id"| PROV
    PROV -->|"webhook, may repeat"| P2
    P2 --> D3
    D3 -->|"Yes"| P3
    D3 -->|"No"| P4
    P4 --> D4
    D4 -->|"Declined"| P5
    D4 -->|"Succeeded"| P6
    P5 -->|"event PaymentDeclined"| O4
    O4 -->|"event ReleaseStock"| I8
    O4 --> K0
    P6 -->|"event PaymentSucceeded"| O5
    O5 -->|"event ClaimStock"| I5
    I5 --> D2
    D2 -->|"Yes"| I6
    D2 -->|"No, stock sold to someone else"| I7
    I6 -->|"event StockClaimed"| O6
    O6 -->|"event OrderConfirmed"| K2
    I7 -->|"event StockClaimFailed"| O7
    O7 -->|"event RefundRequested"| P7
    O7 --> K0
    P7 -->|"HTTP: refund"| D5
    D5 -->|"Yes"| P8
    D5 -->|"No, error or timeout"| P9
    P9 --> D6
    D6 -->|"No, retry"| P7
    D6 -->|"Yes"| P10
    P8 -->|"event RefundSucceeded"| O8
    P10 -->|"event RefundStuck"| O9
```

## Failure branches

| Case | Where it branches | What happens | Cart |
|---|---|---|---|
| **Short stock** | Inventory, decision "Is every line in stock?" | Nothing is reserved (one transaction, all or nothing). No payment is requested. `StockShort` lists the short items, and Order stores them as REJECTED_SHORT_STOCK and shows them to the customer. | Untouched |
| **Declined payment** | Payment, decision "Provider outcome?" | `PaymentDeclined` makes Order set PAYMENT_DECLINED. Order emits `ReleaseStock` and Inventory frees the hold at once, so the stock does not sit idle for the rest of the 10 minutes. | Untouched |
| **Late success after the hold lapsed** | Inventory, decision "Hold still HELD, or lapsed but every line still free?" | The payment succeeded but the claim fails because the stock has gone. Order cancels as CANCELLED_OUT_OF_STOCK, requests a full refund and emails the customer. No partial orders are shipped, because the claim covers all lines or none. | Untouched |
| **Failed refund** | Payment, decision "Provider accepted and completed the refund?" | The refund record is never deleted. A retry worker keeps retrying with the same idempotency key (`refund-<order id>`), so a retry cannot refund twice. After the retry limit the record becomes STUCK, an alert goes to ops, and it stays in the queue until a person resolves it. Order shows the refund as STUCK. | Untouched |
| **Duplicate webhook** | Payment, decision "Provider event id already in webhook_events?" | The provider event id has a unique constraint. A repeat hits the constraint, is acknowledged with 200 and is not processed. No event is emitted twice. | n/a |

## What each service stores

| Service | Owns |
|---|---|
| **Cart** | Carts, cart lines, current prices. It is emptied only when it receives `OrderConfirmed`. |
| **Order** | Orders and their line and price snapshot (frozen at Place order), status, short-item list, refund status, outbox and inbox. |
| **Inventory** | Stock levels, and reservations with order id, lines, `expires_at` and state (HELD, CLAIMED, RELEASED, EXPIRED). It also keeps an outbox and an inbox. |
| **Payment** | Payments (one per order), `webhook_events` (unique provider event id), refunds (state, attempts, next retry time), outbox and inbox. |

## Order statuses

PLACED, then one of:
- REJECTED_SHORT_STOCK
- AWAITING_PAYMENT, then one of:
  - PAYMENT_DECLINED
  - CONFIRMED
  - CANCELLED_OUT_OF_STOCK (refund status PENDING, then REFUNDED or STUCK)

## Rules that make this safe

1. **Order first, then reserve, then pay.** Payment is only requested after `StockReserved`, so a short basket never causes a charge.
2. **One idempotency key per money movement.** The charge uses the order id and the refund uses `refund-<order id>`. If Payment times out and retries, the provider returns the original result.
3. **Claim is decided in one place.** Only Inventory decides whether a claim succeeds, in a single transaction. The expiry job and a late claim therefore cannot both win.
4. **Hold expiry does not cancel the order.** While AWAITING_PAYMENT, a lapsed hold changes nothing in Order, because the payment may still succeed (up to 30 minutes). The stock decision is made at claim time.
5. **The cart is emptied by `OrderConfirmed` only.** Every other path leaves it as it was. Clearing is safe to repeat.
6. **Snapshot is final.** Pricing and lines come from the order's own snapshot after Place order. Cart edits and price changes after that moment do not touch the order.
7. **Payment success for an order that is no longer waiting.** If `PaymentSucceeded` arrives for an order that is not AWAITING_PAYMENT (for example, already cancelled), Order requests a refund rather than ignoring the money.

## Choices to confirm

- **Late claim:** I let a claim succeed on a lapsed hold if every line is still free at that moment. This avoids refunding a customer when the stock is still there. If you want strictly "lapsed means refund", remove the "or lapsed but every line still free" clause.
- **No webhook:** If the provider sends no webhook after about 35 minutes, Payment should ask the provider for the payment status. This is not drawn in the chart.
- **Cart clearing:** `OrderConfirmed` removes only the lines in the order's snapshot. Anything the customer added after pressing Place order stays in the cart. This is not drawn in the chart.
- **Double-click on Place order:** Order allows one open order per cart, so a double click returns the existing order instead of creating a second one. This is not drawn in the chart.
- **Emails:** Order sends them, so no fifth service is needed.
