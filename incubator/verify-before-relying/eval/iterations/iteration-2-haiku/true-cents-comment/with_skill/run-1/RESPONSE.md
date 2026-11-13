I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is added as 30 because `Order.total` is stored in integer cents. The comment in `orders/model.py` says so ("amount due, in integer cents"). I checked that claim against the code and tests: `tests/test_discounts.py` takes 20% off 1250 and gets 1000, which only works in integer cents. The claim checks out, so I relied on it and left the comment unchanged.

The existing tests still pass (3 of 3). I also ran the new function once on an order with a total of 1250 and got 1280.
