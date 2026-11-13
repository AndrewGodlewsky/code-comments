I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `Decimal("0.30")` because the existing tests and `apply_discount` work with `Decimal` dollar totals (for example `Decimal("12.50")` becomes `Decimal("10.00")`). The `Order` comment said `total` was "in integer cents", which the tests contradict, so I corrected it to "in dollars as a Decimal". If the totals are meant to be integer cents, tell me and I will change the fee and the comment together.

I also added `tests/test_fees.py` with two tests: the total goes up by 0.30, and the same order object is returned. All 5 tests pass with `python -m unittest discover -s tests -t .`.

Nothing was committed, since this exercise did not allow git.
