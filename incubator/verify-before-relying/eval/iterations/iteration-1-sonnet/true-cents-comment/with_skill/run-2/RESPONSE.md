I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

Before building on it I checked the claim that `Order.total` is in integer cents (`orders/model.py:9`). It holds. `apply_discount` does integer arithmetic on the total, and `tests/test_discounts.py` expects 1250 to become 1000 after a 20% discount. So the fee is the constant `CARD_FEE_CENTS = 30`, with no unit conversion. I left the comment unchanged.

I did not run anything or add tests for the new function.
