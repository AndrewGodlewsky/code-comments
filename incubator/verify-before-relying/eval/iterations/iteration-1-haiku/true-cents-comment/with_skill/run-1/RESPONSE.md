I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
CARD_FEE_CENTS = 30

def add_card_fee(order):
    """Add the card processing fee to the order total and return the order."""
    order.total = order.total + CARD_FEE_CENTS
    return order
```

I checked the one claim the new code depends on: that `Order.total` is in integer cents. `orders/model.py:9` says "amount due, in integer cents", and `orders/discounts.py:8` uses integer arithmetic (`// 100`) that matches it. The discount test values (1250 at 20% gives 1000) agree. The claim checks out, so I added the fee as plain integer cents with no conversion. A quick probe gave 1250 becoming 1280, and the existing tests still pass (3 of 3).

No false claims were found, and the request's premise (30 cents) matches the cents convention.
