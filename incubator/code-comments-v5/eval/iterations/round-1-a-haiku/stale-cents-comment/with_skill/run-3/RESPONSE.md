I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total`, mutates the order the same way `apply_discount` does, and returns the order. I also added `tests/test_fees.py` with two tests, and all 5 tests pass with `python -m unittest`.

One thing to know: the `Order.total` comment in `orders/model.py` said "amount due, in integer cents". The existing code and tests treat totals as dollar `Decimal` values (for example `Decimal("12.50")` discounted 20% gives `Decimal("10.00")`), so that comment was false. I changed it to "amount due, in dollars as Decimal". The fee is therefore `Decimal("0.30")`. If totals are meant to be integer cents, the comment and the fee constant both need to change, so please confirm which unit is correct.

I did not use git or any task tracking, and I did not commit anything.
