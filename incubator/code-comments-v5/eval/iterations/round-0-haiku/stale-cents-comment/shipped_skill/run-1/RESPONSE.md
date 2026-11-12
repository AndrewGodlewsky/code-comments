I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is a constant, `CARD_FEE_CENTS = 30`. Its comment says `Order.total` is in integer cents, which is what `orders/model.py` documents, so adding 30 is the right amount.

Please check one conflict before relying on this. `orders/model.py` says `total` is "amount due, in integer cents", but `tests/test_discounts.py` builds orders with `Decimal("12.50")` dollar values and expects dollar results. If `total` is really in dollars, the fee should be `Decimal("0.30")`, not 30. I did not change either the model comment or the tests, because I could not tell which one is right.

I did not add tests for the new function, since you only asked for the function.
