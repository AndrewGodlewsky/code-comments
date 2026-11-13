I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The total is in integer cents, so the fee is stored as `CARD_PROCESSING_FEE = 30` with a `# cents` note. A quick check on an order totalling 1250 cents returned 1280.

I did not add tests, since you did not ask for them. I also did not record a reason for the fee beyond "card processing": if the fee has a source, such as a payment-provider contract or a ticket, tell me and I will put it beside the constant.
