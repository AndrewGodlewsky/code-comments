I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order.

`Order.total` is stored in integer cents (see `orders/model.py`), so the fee is the constant `CARD_FEE_CENTS = 30`, not `0.30`.

I also added `tests/test_fees.py` with two tests (the total goes up by 30 cents, and the same order object is returned). The test suite passes.

The function doesn't check whether the order is paid by card, and calling it twice charges the fee twice. Callers need to apply it once, and only for card payments.
