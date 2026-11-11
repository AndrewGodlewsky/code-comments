I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

`Order.total` is stored in integer cents (see the comment in `orders/model.py`), so the fee is the constant `CARD_FEE_CENTS = 30`, not 0.30.

I didn't add tests or run anything. The function doesn't guard against applying the fee twice, so call it once per order.
