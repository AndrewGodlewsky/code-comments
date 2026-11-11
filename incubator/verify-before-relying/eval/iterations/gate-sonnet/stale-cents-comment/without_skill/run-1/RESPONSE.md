I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

`Order.total` is documented in `orders/model.py` as integer cents, so the fee is the constant `CARD_FEE_CENTS = 30`, not 0.30. I didn't run it and didn't add tests.

Calling it twice charges the fee twice. Nothing in the order records whether the fee was already applied.
