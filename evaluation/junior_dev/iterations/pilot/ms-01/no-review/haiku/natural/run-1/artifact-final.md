# Checkout across Cart, Inventory, Payment and Order

This flowchart shows checkout from **Place order** to a confirmed order, a clean stop, or a refund. Order is the orchestrator: it calls Inventory and Payment over HTTP and reacts to their results. Payment hears from the provider by webhook. Cart changes only after an order is confirmed.

Read the diagram top to bottom. Each box names the service that acts, what it stores, and what triggers it. Red boxes are failure outcomes. Dotted arrows are retries or background jobs.

```mermaid
flowchart TD
    subgraph CART["Cart service"]
        A1["Customer presses Place order<br/>Cart sends its lines and prices to Order<br/>Stores: cart (not changed)"]
        A2["Cart empties on OrderConfirmed<br/>Removes lines in the order snapshot<br/>Stores: cart"]
    end

    subgraph ORDER["Order service (orchestrator)"]
        B1["Create order with status PLACED<br/>Generates order id<br/>Stores: order and order lines with price snapshot"]
        B2["Ask Inventory to reserve all lines<br/>HTTP POST /reservations, key = order id"]
        B3["Status AWAITING_PAYMENT<br/>Ask Payment to charge<br/>HTTP POST /charges, key = order id"]
        B4["Ask Inventory to commit the reservation<br/>key = order id"]
        B5["Status CONFIRMED<br/>Publish OrderConfirmed<br/>Stores: order status"]
        B6["Status CANCELLED_SHORT_STOCK<br/>Return list of short items to customer"]
        B7["Status PAYMENT_DECLINED<br/>Ask Inventory to release the reservation"]
        B8["Status CANCELLED_OUT_OF_STOCK<br/>Ask Payment for a full refund"]
        B9["Email customer: order cancelled, out of stock, refund issued"]
    end

    subgraph INV["Inventory service"]
        C1{"Every line has enough free stock?<br/>checked in one database transaction"}
        C2["Reserve nothing<br/>Return list of short items<br/>Stores: no change"]
        C3["Reserve all lines<br/>Stores: reservation HELD, expires_at = now + 10 min<br/>free stock reduced"]
        C4["Sweeper, runs every minute<br/>HELD past expires_at becomes EXPIRED<br/>Stock goes back on sale"]
        C5{"Reservation still HELD?<br/>conditional update, one transaction"}
        C6["Commit reservation to COMMITTED<br/>Stock sold for good<br/>Stores: reservation, stock"]
        C7["Reply RESERVATION_LOST<br/>Nothing committed"]
        C8["Release reservation to RELEASED<br/>Stock goes back on sale"]
    end

    subgraph PAY["Payment service (only service that talks to the provider)"]
        D0["Charge call to provider times out or fails<br/>Retry with the same idempotency key"]
        D1["Store payment row PENDING, unique on order id<br/>Call provider charge with idempotency key = order id<br/>Stores: payment"]
        D2["Provider decides later<br/>Usually seconds, can take up to 30 minutes"]
        D3["Provider webhook arrives<br/>POST /webhooks/provider<br/>May arrive more than once"]
        D4{"Provider event id already in webhook_events?"}
        D5["Acknowledge with 200 and stop<br/>No second state change"]
        D6["Record event id, move payment PENDING to SUCCEEDED or DECLINED once<br/>Publish PaymentSucceeded or PaymentDeclined<br/>Stores: webhook_events, payment"]
        D7{"Outcome from provider"}
        D8["Store refund row REQUESTED before calling provider<br/>Call provider refund, key = refund plus order id<br/>Stores: refund"]
        D9{"Provider accepted the refund?"}
        D10["Refund SUCCEEDED<br/>Stores: refund"]
        D11["Refund FAILED, row stays open<br/>Retry with backoff, same key<br/>After max attempts, alert an operator"]
    end

    subgraph CUST["Customer"]
        Z1(["Order confirmed, cart emptied"])
        Z2(["Shown short items, cart unchanged, can edit and retry"])
        Z3(["Told payment declined, cart unchanged, can retry"])
        Z4(["Cancelled and emailed, refund in progress or done, cart unchanged"])
    end

    %% Stock check and reservation
    A1 --> B1 --> B2 --> C1
    C1 -- "no" --> C2 --> B6 --> Z2
    C1 -- "yes" --> C3 --> B3

    %% Payment request and provider outcome
    B3 --> D1
    D1 -.->|"timeout or error, retry"| D0
    D0 -.->|"same key, provider cannot double charge"| D1
    D1 --> D2 --> D3 --> D4
    D4 -- "yes, duplicate" --> D5
    D4 -- "no, first delivery" --> D6 --> D7

    %% Declined branch
    D7 -- "declined" --> B7 --> C8 --> Z3

    %% Succeeded branch: claim the stock
    D7 -- "succeeded" --> B4 --> C5
    C4 -.->|"status EXPIRED"| C5
    C5 -- "yes, still HELD" --> C6 --> B5 --> A2 --> Z1

    %% Late success after the hold lapsed
    C5 -- "no, expired or released" --> C7 --> B8
    B8 --> B9 --> Z4
    B8 --> D8 --> D9
    D9 -- "yes" --> D10
    D9 -- "no" --> D11
    D11 -.->|"retry, same key"| D8

    %% Background hold expiry
    C3 -.->|"no claim within 10 minutes"| C4

    classDef fail fill:#fde2e2,stroke:#b42318,color:#3d0a0a
    classDef ok fill:#dcfae6,stroke:#067647,color:#053321
    class C2,B6,B7,C8,C7,B8,B9,D11,C4,D5,Z2,Z3,Z4 fail
    class C6,B5,A2,D10,Z1 ok
```

## Notes on the flow

**Who does what, and what each service stores**

| Service | Triggered by | Acts | Stores |
|---|---|---|---|
| Cart | Customer presses Place order | Sends lines and prices to Order. Empties on OrderConfirmed. | Cart. Not changed until confirmed. |
| Order | Cart request, Inventory and Payment replies, OrderConfirmed-related events | Orchestrates every step, sets order status, sends refund request and email | Order, order lines (price snapshot), status |
| Inventory | Order reserve, commit and release calls, expiry sweeper | Checks and reserves all lines in one transaction. Commits or releases. Expires holds. | Stock levels, reservations (HELD, COMMITTED, RELEASED, EXPIRED) |
| Payment | Order charge and refund calls, provider webhook | Only service that calls the provider. Dedupes webhooks. Retries refunds. | Payment rows, webhook event ids, refund rows |

**Why each branch is safe**

- **Short stock.** Inventory checks every line in one transaction. If any line is short, it reserves nothing and returns the short items. No payment is requested.
- **Declined payment.** Payment records the decline. Order releases the reservation so the stock is available again. The cart was never touched.
- **Late success after the hold lapsed.** The 10-minute hold can expire while the provider is still working, since the outcome can take up to 30 minutes. Commit is a conditional update that succeeds only while the reservation is still HELD. If it has expired or been released, Inventory replies RESERVATION_LOST. Order then cancels the order as out of stock and requests a full refund. The refund key is tied to the order, so retries are safe.
- **Failed refund.** The refund row is saved before the provider is called. A failure leaves the row open. It is retried with the same key and backoff, and an operator is alerted after the maximum number of attempts. It is never dropped.
- **Duplicate webhooks.** Payment stores each provider event id with a unique constraint. A repeat is acknowledged and ignored. Payment moves each payment from PENDING to a final state only once.
- **Cart.** The cart is emptied only on OrderConfirmed. On every failure path the cart stays as it was.

**Assumptions to confirm**

- The 10-minute hold is not extended while payment is pending. This follows the brief. It is the reason the late-success branch exists.
- Late success always leads to a refund, even if the stock is still free. Re-reserving stock when it is still free is possible but not in the brief, so it is left out.
- The email is sent by Order through an email gateway. The brief does not name an owner for email.
- OrderConfirmed empties only the lines in the order snapshot. Lines the customer adds during checkout are kept. Product should confirm this against "emptied".
- Events are delivered at least once. Every consumer (Cart on OrderConfirmed, Inventory on commit or release, Order on payment events) must handle repeats safely.
