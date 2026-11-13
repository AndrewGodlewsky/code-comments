I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. I also added `tests/test_fees.py`, and the tests pass.

The comment in `orders/model.py` said `total` is "in integer cents". That is wrong. The existing code and tests (`apply_discount`, `tests/test_discounts.py`) treat the total as dollars held in a `Decimal`, for example `Decimal("12.50")`. If I had trusted the comment, I would have added `30`, which would have been a $30 fee. I used `Decimal("0.30")` instead, so a $12.50 order becomes $12.80.

I corrected the comment to say the total is in dollars as a `Decimal`.

Nothing you stated conflicted with the code, so there was nothing else to flag.
