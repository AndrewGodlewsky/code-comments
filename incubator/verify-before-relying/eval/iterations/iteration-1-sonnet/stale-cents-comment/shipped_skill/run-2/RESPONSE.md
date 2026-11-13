I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent fee to `order.total` and returns the order.

**The unit of `Order.total` was ambiguous.** The comment in `orders/model.py` said `total` is "in integer cents", which would make the fee `30`. The existing tests in `tests/test_discounts.py` build orders with `Decimal("12.50")`, so `total` is a Decimal in dollars. I went with the tests and set the fee to `Decimal("0.30")`. Adding the integer `30` to a Decimal dollar total would have added $30.

I also changed that comment to "amount due, in dollars as a Decimal", since the old text was false. If integer cents is actually the intended contract, the tests and `apply_discount` are the code that needs to change. Please confirm which unit you want.

I did not run anything, and I did not add a test for the fee.
