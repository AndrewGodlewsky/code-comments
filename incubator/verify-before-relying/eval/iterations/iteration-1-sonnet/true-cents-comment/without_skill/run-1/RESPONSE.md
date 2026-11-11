I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

`Order.total` is stored in integer cents (see `orders/model.py`), so the fee is the constant `CARD_FEE_CENTS = 30`, not 0.30.

I didn't add tests or run anything. The function doesn't check whether the order was already charged the fee, so calling it twice adds 60 cents.
