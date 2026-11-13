I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The function is in `orders/fees.py`; a test file is in `tests/test_fees.py`.

One thing I changed that you should know about: the comment in `orders/model.py:9` said `total` was "amount due, in integer cents". The tests in `tests/test_discounts.py` pin `total` as a `Decimal` in dollars (for example, `Decimal("12.50")` with 20% off gives `Decimal("10.00")`), and `apply_discount` works in those units too. So I corrected the comment to "amount due, a Decimal in dollars". Because of that, the fee is `Decimal("0.30")`, not the integer `30`. Adding 30 to a dollar total would have added $30.

All 5 tests pass (`python -B -m unittest discover -s tests -t .`), including the 2 new fee tests.
