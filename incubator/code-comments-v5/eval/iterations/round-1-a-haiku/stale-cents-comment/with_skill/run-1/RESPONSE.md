I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is a `Decimal("0.30")` constant, because the tests and `apply_discount` treat `total` as a Decimal in dollars.

I also corrected one stale comment. `orders/model.py` said `total` was in "integer cents", but the existing tests use `Decimal("12.50")` and `apply_discount` multiplies it as a decimal. The comment now reads "amount due, in dollars as a Decimal, e.g. Decimal("12.50")".

I added `tests/test_fees.py` with two tests: the fee is added to the total, and the same order object is returned. All 5 tests in the repo pass.

Please confirm one thing. If the shop actually stores totals in integer cents, the fee constant and the model comment are both wrong, and the fee should become `30`.
