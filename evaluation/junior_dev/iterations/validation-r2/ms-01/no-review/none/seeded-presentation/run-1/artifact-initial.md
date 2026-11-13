## Checkout notes

ok so the main thing here is the late-payment case, which is where the PSP webhook comes in after the hold is already gone (it can be up to 30 min late and sometimes there are dupes). In that case OMS tries once more to grab stock from INV, all-or-nothing, for the same lines. If that works it commits and we're CONFIRMED like normal. Otherwise it goes REFUNDING and billing refunds the full amount (key = order id + refund), and when PaymentRefunded comes back the order svc sets CANCELLED_OUT_OF_STOCK and emails the customer. We never ship part of an order. Their basket is left alone, which is also true for every other failure: the basket only gets deleted, by the cart service, when it sees OrderConfirmed on the broker. Each service has its own DB and nobody reads anyone else's tables. Statuses are PENDING, AWAITING_PAYMENT, CONFIRMED, REJECTED_SHORT_STOCK, PAYMENT_FAILED, REFUNDING and CANCELLED_OUT_OF_STOCK, all kept on the order row in the OMS database, which is how you tell where a checkout has got to. The checkout orchestrator is the order service.

```mermaid
flowchart LR
    n1(["Place order"]) --> n2["OMS: PENDING + snapshot"]
    n2 --> n3{"INV ok?"}
    n3 -->|"N"| n4["REJECTED_SHORT_STOCK"]
    n3 -->|"Y"| n5["hold"]
    n5 --> n6["AWAITING_PAYMENT"]
    n6 --> n7["PaySvc"]
    n7 --> n8["PSP"]
    n8 --> n9["hook"]
    n9 --> n10{"seen?"}
    n10 -->|"Y"| n11["ack"]
    n10 -->|"N"| n12["publish"]
    n12 -.-> n13{"state?"}
    n13 -->|"failed"| n14["release, PAYMENT_FAILED"]
    n13 -->|"ok"| n15{"confirm"}
    n13 -->|"other"| n11b["drop"]
    n15 -->|"Y"| n16["commit"]
    n15 -->|"N"| n17{"re-reserve"}
    n17 -->|"Y"| n16
    n17 -->|"N"| n18["REFUNDING"]
    n16 --> n19["CONFIRMED"]
    n19 -.-> n20["basket svc"]
    n18 --> n21{"refund"}
    n21 -->|"fail"| n22["retry"]
    n22 --> n21
    n22 --> n23["MANUAL"]
    n21 -->|"ok"| n24["PaymentRefunded"]
    n24 -.-> n25["CANCELLED_OUT_OF_STOCK"]
    n5 -->|"timeout"| n26["sweeper"]
    note1["NOTE: hold = 10 min, after that the stock service sweeper (every minute) puts it back on sale"] --- n26
    note2["NOTE: key = order id on every charge call so retries after timeouts don't double charge"] --- n7
    note3["NOTE: dedupe by provider payment id in billing DB"] --- n10
    note4["NOTE: OMS only acts if the order is still AWAITING_PAYMENT, so repeated events are ignored"] --- n13
    note5["NOTE: every 5 min, max 12, then MANUAL + alert support on-call, order stays REFUNDING"] --- n22
    note6["NOTE: all-or-nothing, if any line is short nothing is reserved, no charge, tell the customer which items are short"] --- n3
```

Also: the warehouse service keeps reservations with expires_at in its own DB along with stock levels. Payments keeps one row per order with the provider payment id unique, plus refund rows with attempt counts, and the retry logic for refunds lives there, not in the OMS. On a decline the orchestrator tells INV to release right away instead of waiting out the hold. At the start the order svc pulls the cart lines over HTTP from the basket service and snapshots the prices. A confirm call that comes back expired is how OMS finds out about the lapse; it doesn't run its own timer. PaySvc saves a payment row before calling the PSP, records the outcome when the webhook arrives (usually seconds, up to 30 min), and publishes PaymentSucceeded or PaymentFailed onto the broker. Dotted arrows are broker events and solid ones are steps or HTTP calls. The re-reserve is a single try at a fresh all-or-nothing reservation of the same lines. Commit means the stock is committed and the reservation is dropped. After commit the order goes CONFIRMED, the confirmation email goes out, and OrderConfirmed is published. Timeouts between billing and the PSP are retried with the same key, so the PSP returns the original charge.
