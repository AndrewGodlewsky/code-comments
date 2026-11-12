I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. `Order.total` is integer cents, so the fee is added as `30`.

```python
def add_card_fee(order):
    """Add the 30-cent card processing fee to the order total and return the order."""
    order.total = order.total + 30
    return order
```

Checks: a 1250-cent order becomes 1280, and the existing three tests still pass.

I did not add a test for the new function, since you did not ask for one. I can add `tests/test_fees.py` if you want it covered.
