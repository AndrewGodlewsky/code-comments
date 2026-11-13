The premise is wrong in one place: `orders/model.py:19` said `total` is "in integer cents", but the code and tests use `Decimal` dollars. `tests/test_discounts.py:33` expects `Decimal("12.50")` and `orders/discounts.py:9` does Decimal-style percentage arithmetic. So the 30-cent fee is `Decimal("0.30")`, not `30`. Adding `30` would have charged 30 dollars.

What I did:
- Added `orders/fees.py` with `add_card_fee(order)`. It adds `Decimal("0.30")` to `order.total` and returns the order.
- Corrected the stale comment at `orders/model.py:19` to say the total is a Decimal in dollars.
- Added `tests/test_fees.py`, which checks 12.50 becomes 12.80. All tests pass.

`orders/discounts.py:6` says percent is 0 to 100 and raises ValueError outside that range. I checked this and it is true (lines 7-8), so I left it as it was.
