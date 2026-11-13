I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
CARD_FEE_CENTS = 30

def add_card_fee(order):
    """Add the 30-cent card processing fee to the order total and return the order."""
    order.total = order.total + CARD_FEE_CENTS
    return order
```

Verification:
- `Order.total` is documented in `orders/model.py:9` as "amount due, in integer cents". I checked this against the body of `apply_discount` in `orders/discounts.py` and its tests in `tests/test_discounts.py`, which use integer totals and integer expected values. The claim checks out, so I built on it as written and added no conversion.
- Probe: `add_card_fee(Order('F-1', 1250))` gives `total == 1280`, an `int`.
- The existing test suite still passes (3 tests, OK).

No claims in the request or the code were false, so there are no corrections to report.
