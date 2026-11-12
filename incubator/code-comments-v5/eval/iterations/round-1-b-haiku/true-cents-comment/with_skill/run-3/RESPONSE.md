I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object. The fee is held in a module constant, `CARD_FEE_CENTS = 30`, and the total stays in integer cents to match `orders/model.py`.

I checked it with a quick run: an order totalling 1250 cents came back as 1280. The existing three tests in `tests/test_discounts.py` still pass.

I did not add a test file for the new function, since you only asked for the function. I can add `tests/test_fees.py` if you want it covered.
