I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order. I added `tests/test_fees.py` for it. All 5 tests pass (3 existing discount tests, 2 new fee tests).

One conflict to check: the `Order` comment in `orders/model.py` said `total` was "in integer cents". The existing discount tests use `Decimal` dollars (for example `Decimal("12.50")`), and `apply_discount` does no cents conversion. I built on the tested behaviour: the fee is `Decimal("0.30")` added to a dollar total. I corrected the comment to say the total is dollars as a `Decimal`. If `total` is really meant to be integer cents, the fee constant and the comment both need to change to 30 instead of `Decimal("0.30")`.

Also note: `apply_discount` on an `int` total returns a `float` (because of `/ 100`), and adding a `Decimal` fee to a `float` raises `TypeError`. The existing tests only use `Decimal` totals, so I left that alone.
