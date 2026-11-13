I added `add_card_fee(order)` in `orders/fees.py`. It adds a 30-cent fee to `order.total` and returns the order.

The comment in `orders/model.py` says `total` is in integer cents. The existing code and tests don't match that: `tests/test_discounts.py` builds orders with `Decimal` dollar amounts such as `Decimal("12.50")`. I followed the tests, so the fee is `Decimal("0.30")`. If totals really are meant to be integer cents, the fee should be `30` and the comment in `model.py` is right. The tests are what disagree. Tell me which it is and I'll adjust.

I did not add tests or run anything.
