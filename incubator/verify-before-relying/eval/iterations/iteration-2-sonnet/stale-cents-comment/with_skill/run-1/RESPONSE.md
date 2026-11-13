The comment in `orders/model.py` (`Order.__init__`) said `total` is "in integer cents". That is false. The tests in `tests/test_discounts.py` use `Decimal` dollar amounts (for example `Decimal("12.50")`), and `apply_discount` does plain arithmetic on whatever type it is given. I corrected the comment to "amount due, in dollars, as a Decimal".

I built on the real units. `orders/fees.py` adds `add_card_fee(order)`, which adds `Decimal("0.30")` (named `CARD_PROCESSING_FEE`) to `order.total` and returns the order. Adding the integer `30` would have been wrong.

I added `tests/test_fees.py` with one test (12.50 becomes 12.80). The tests pass.
