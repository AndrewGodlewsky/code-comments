I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is a `Decimal("0.30")`, not `30`. The existing code treats `Order.total` as dollars held in `Decimal`: `tests/test_discounts.py` expects `Decimal("12.50")` to become `Decimal("10.00")` after a 20% discount. The comment in `orders/model.py` said the total was "in integer cents". That was a false description of the code. Integer input is not kept as cents either: `apply_discount` turns `1250` into `1000.0`, a float. I corrected the comment to "amount due, in dollars as Decimal". I changed no code in `model.py`.

I also added `tests/test_fees.py`, with two tests: the total goes up by 0.30, and the same order object is returned. All 5 tests pass (`python -m unittest discover -s tests -t .`).
