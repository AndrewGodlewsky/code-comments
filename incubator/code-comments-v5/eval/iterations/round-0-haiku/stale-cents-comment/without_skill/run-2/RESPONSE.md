I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

```python
CARD_PROCESSING_FEE = Decimal("0.30")

def add_card_fee(order):
    order.total = order.total + CARD_PROCESSING_FEE
    return order
```

I used `Decimal("0.30")` rather than `30` because the existing tests and `apply_discount` treat totals as dollar `Decimal` values (for example, `Decimal("12.50")`). A smoke run with a `Decimal("12.50")` total gave `12.80`, as a `Decimal`.

One thing to check: the docstring-style comment on `Order.total` in `orders/model.py` says the total is "in integer cents". That contradicts the rest of the code. I did not change it because it was outside this request. If totals really are cents, the fee should be `30` instead, and `apply_discount` and the tests would need a review. Either way, that comment should be corrected.

I did not add a unit test file for the fee. I did not use git.
