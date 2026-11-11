I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is `Decimal("0.30")`, not the integer `30` you might expect. The comment on `Order.total` in `orders/model.py` says the total is "in integer cents". The code and tests disagree with that: `tests/test_discounts.py` builds orders with values like `Decimal("12.50")`, and `apply_discount` does decimal math. I followed the tests, so totals are Decimal dollars. If totals really are meant to be integer cents, the fee constant should be `30` and the comment is right. Otherwise the comment should be corrected. I left the comment alone.

I did not add tests for the new function, and I did not run anything.
