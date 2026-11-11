I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The premise in the `Order.total` comment is wrong. `orders/model.py:9` said `# amount due, in integer cents`, but `total` holds a `Decimal` in dollars: the tests build orders with `Decimal("12.50")` and `apply_discount` multiplies it as a dollar amount. I probed `Order('x', Decimal('12.50')).total` and it is a `Decimal` of `12.50`. So I used `Decimal("0.30")` as the fee rather than the integer `30`, which would have added $30.00 per order. I corrected the comment in place to `# amount due, a Decimal in dollars`.

Checked: the 3 existing tests in `tests/test_discounts.py` still pass. I also ran `add_card_fee` on an order totalling 12.50 and got 12.80. I did not add tests for the new function.
