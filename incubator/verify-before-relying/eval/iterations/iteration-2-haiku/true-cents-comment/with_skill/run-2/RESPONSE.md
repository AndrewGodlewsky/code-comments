I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
CARD_FEE_CENTS = 30

def add_card_fee(order):
    """Add the 30-cent card processing fee to the order total and return the order."""
    order.total = order.total + CARD_FEE_CENTS
    return order
```

`Order.total` is documented in `orders/model.py` as amount due in integer cents, so adding the integer 30 is the correct unit. I checked that claim against the code: `apply_discount` in `orders/discounts.py` also works in integer cents, and the existing tests use cent values. I did not find any false comment or docstring that this change depends on, so nothing was corrected.

I smoke-tested it: an order at 1250 becomes 1280. The existing test suite (3 tests) still passes. I did not add a test file for the fee, since the request did not ask for one.
