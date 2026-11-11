The premise in the model comment is wrong: `orders/model.py:9` said `Order.total` is "in integer cents", but the tests (`tests/test_discounts.py`) build orders with `Decimal` dollar amounts (`Decimal("12.50")`), and `apply_discount` does Decimal arithmetic on them. The total is a Decimal in dollars, so the 30-cent fee is `Decimal("0.30")`, not `30`. Adding 30 would have charged $30.

What I did:
- Added `orders/fees.py` with `add_card_fee(order)`, which adds `Decimal("0.30")` to `order.total` and returns the order.
- Corrected the comment at `orders/model.py:9` to "amount due, as a Decimal in dollars (Decimal("12.50") is $12.50)".
- Added `tests/test_fees.py` (12.50 -> 12.80). All tests pass.

Checked and trusted: `apply_discount`'s docstring (percent 0 to 100, returns the order, raises ValueError out of range) matches its body and tests.
