I added `add_card_fee(order)` in `orders/fees.py`. It adds the card processing fee to `order.total` and returns the order.

The fee is `Decimal("0.30")`, not 30 cents as an integer. The `Order.total` comment in `orders/model.py` said the total was "in integer cents", but `apply_discount` and the existing tests all treat it as a `Decimal` in dollars (for example `Decimal("12.50")`). I followed the code and tests and corrected that comment to "amount due, a Decimal in dollars". If the total was meant to be integer cents, the fee and the comment both need changing, and that decision is yours to confirm.

Checks: `add_card_fee(Order("A-1", Decimal("12.50")))` gives a total of `Decimal("12.80")`. The existing three tests in `tests/test_discounts.py` pass. I did not add a test for the fee.
