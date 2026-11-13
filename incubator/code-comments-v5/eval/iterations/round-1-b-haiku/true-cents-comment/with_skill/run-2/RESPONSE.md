I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
"""Fees added to an order's total before payment."""

CARD_FEE_CENTS = 30


def add_card_fee(order):
    """Add the card processing fee to the order total and return the order."""
    order.total = order.total + CARD_FEE_CENTS
    return order
```

`Order.total` is stored in integer cents (see `orders/model.py`), so the fee is `30` cents. I did not add tests, since you only asked for the function.
