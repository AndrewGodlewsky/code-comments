I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

Before building on it I checked the claim that `Order.total` is in integer cents (the comment in `orders/model.py`). It holds. `apply_discount` and its tests work in whole numbers, for example 1250 becomes 1000 at 20% off. The fee is therefore the integer `30`, kept as `CARD_FEE_CENTS`. I added no conversion and left the comment as it was.

I ran it once on `Order("A", 1250)` and got a total of 1280. I did not add tests for the new function.
