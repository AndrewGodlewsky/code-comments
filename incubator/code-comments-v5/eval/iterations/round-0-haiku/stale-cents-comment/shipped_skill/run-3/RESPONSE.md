I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee (`CARD_FEE_CENTS = 30`) to `order.total` and returns the order.

I followed the `Order.total` comment in `orders/model.py`, which says the total is in integer cents, so the fee is added as 30. A smoke check confirmed that an order at 1000 becomes 1030 and that the function returns the same order. The existing 3 tests in `tests/test_discounts.py` still pass. I did not add a test for the fee.

Please check one thing. `tests/test_discounts.py` builds orders with `Decimal` dollar amounts such as `Decimal("12.50")`, which contradicts the cents comment in `orders/model.py`. If totals are really dollars, `add_card_fee` would add $30 instead of 30 cents, and the fee would need to be `Decimal("0.30")`. Someone needs to confirm which unit is correct. I did not change either comment or test.
