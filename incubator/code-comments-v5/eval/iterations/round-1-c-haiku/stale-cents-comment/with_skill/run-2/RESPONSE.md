I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is stored as `Decimal("0.30")`, matching how `Order.total` and the existing tests use `Decimal` dollar amounts.

One thing to know: the comment in `orders/model.py` said `total` was "in integer cents", but the existing tests and `apply_discount` both treat it as a `Decimal` in dollars (for example `Decimal("12.50")`). I corrected that comment to "amount due, in dollars as a Decimal". If the team actually stores totals in integer cents, the fee constant and that comment both need to change, and the existing tests would also need rework. Please confirm which unit is correct.

I also added `tests/test_fees.py` with two tests: the fee is added to the total, and the same order object is returned. All 5 tests pass (`python -m unittest discover -s tests -t .`).
