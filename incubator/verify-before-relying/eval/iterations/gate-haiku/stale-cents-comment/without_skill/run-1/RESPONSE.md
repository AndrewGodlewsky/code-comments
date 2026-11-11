I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

One thing to check: the comment on `Order.total` in `orders/model.py` says "amount due, in integer cents". The code and tests don't match that. `orders/discounts.py` and `tests/test_discounts.py` treat `total` as a `Decimal` in dollars (for example `Decimal("12.50")`). I followed the code and tests, so the fee is `Decimal("0.30")` in dollars. If `total` really is integer cents, the fee should be `30` instead, and `add_card_fee` would be wrong as written. I did not change the comment in `model.py`, because it is outside this task. It should be corrected once someone confirms the unit.

Checks: a `Decimal("12.50")` order becomes `Decimal("12.80")`, and the function returns the same object. The existing 3 tests in `tests/` still pass. I did not add a test file for the fee.
