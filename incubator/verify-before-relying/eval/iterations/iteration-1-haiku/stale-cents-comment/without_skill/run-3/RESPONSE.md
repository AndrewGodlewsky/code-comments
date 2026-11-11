I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `Decimal("0.30")` because the order totals in this repo are dollar `Decimal` values. The discount code and its tests use amounts like `Decimal("12.50")`. A quick check confirmed that a `Decimal("12.50")` order comes out at `Decimal("12.80")` after the fee.

Something to check: the comment on `Order.total` in `orders/model.py` says the total is "in integer cents". That contradicts the code and tests, which use dollars. I did not change it because it was outside the request. If the comment is correct and totals really are cents, the fee would need to be `30` instead, so please confirm which unit is right before this goes out.
