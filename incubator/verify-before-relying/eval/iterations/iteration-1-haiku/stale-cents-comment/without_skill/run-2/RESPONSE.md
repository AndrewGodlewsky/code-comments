I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
from decimal import Decimal

CARD_PROCESSING_FEE = Decimal("0.30")


def add_card_fee(order):
    order.total = order.total + CARD_PROCESSING_FEE
    return order
```

I checked it with a `Decimal("12.50")` order, which becomes `12.80`. The existing 3 tests still pass.

Please check one thing before relying on this. The comment on `Order.total` in `orders/model.py` says the total is "in integer cents". The rest of the code does not match that. `apply_discount` in `orders/discounts.py` multiplies and divides by 100 and produces fractional results, and the tests use `Decimal` dollar amounts such as `Decimal("12.50")`. I followed the code and tests and treated the total as dollars, so the fee is `Decimal("0.30")`. If totals really are integer cents, the fee should be `30` instead, and the current version would add 0.3 cents per order. I did not change the `model.py` comment, since I don't know which one is out of date. Someone who knows how totals are stored should confirm which it is and fix the comment to match.
