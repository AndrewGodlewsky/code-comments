I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

`Order.total` is stored in integer cents (see `orders/model.py`), so the fee is the constant `CARD_FEE_CENTS = 30`, not 0.30.

I didn't add tests, and I didn't add comments beyond the module and function docstrings, since the code and the existing `total` comment cover the units. Nothing in the repo says whether the fee should be applied only once per order, or only to card payments. The function adds it every time it is called. Tell me if you want a guard against double application.
