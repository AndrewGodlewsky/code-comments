# Checkout across Cart, Inventory, Payment and Order: flow design

## How to read this

Checkout is a saga. The **Order** service drives it. Each service records its own state in its own database, and services hand off with HTTP calls or broker events. Two rules hold throughout:

- **Hold, then claim.** Inventory holds stock for 10 minutes when checkout starts. The stock is only *claimed* (sold) when payment succeeds while the hold is still valid.
- **Idempotency keys.** The order id is the key for reservations, charges and claims. Repeating a request, or re-delivering an event, changes nothing the second time.

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
        P14["Retry with backoff, same key<br/>after N tries: STUCK, page ops, row kept"]
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
