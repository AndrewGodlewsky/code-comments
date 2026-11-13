I added `add_card_fee(order)` in a new file, `orders/fees.py`. It adds the 30-cent card processing fee (`CARD_PROCESSING_FEE_CENTS = 30`) to `order.total` and returns the same order object. Totals are integer cents, matching `Order.total` in `orders/model.py`.

I checked the existing comments and docstrings against the code before relying on them. `Order.total` is documented as amount due in integer cents, and that matches how `apply_discount` in `orders/discounts.py` computes it. The `apply_discount` docstring matches its code and its tests, so I found no wrong descriptions and changed nothing existing.

I also added `tests/test_fees.py` with two tests: the total goes up by 30 cents (1250 becomes 1280), and the function returns the same order object. All 5 tests pass (`python -m unittest discover -s tests -t .`).

Nothing conflicted with your request.
