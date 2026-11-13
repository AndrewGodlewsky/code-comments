I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

```python
CARD_PROCESSING_FEE = Decimal("0.30")

def add_card_fee(order):
    order.total = order.total + CARD_PROCESSING_FEE
    return order
```

I used `Decimal("0.30")` because the existing tests and discount code treat `order.total` as a `Decimal` amount in dollars (for example `Decimal("12.50")`). Adding 0.30 gives 12.80 for a 12.50 order and 0.30 for a zero order. The existing 3 tests still pass.

There is a conflict to resolve. The comment on `Order.total` in `orders/model.py` says "amount due, in integer cents", which contradicts how the tests and the discount code use it. I did not change that comment. If totals really are integer cents, the fee should be `30` instead of `Decimal("0.30")`, and the discount code would need a fix too. Please confirm which unit is correct, then either update that comment or switch the fee.
