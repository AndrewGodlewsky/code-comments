I added `add_card_fee(order)` in `orders/fees.py`. It adds 30 cents to `order.total` and returns the same order object. The module and function have short docstrings in the same style as `orders/discounts.py`.

I checked it with a quick run: an order at 1000 becomes 1030, and the function returns the same object. The existing tests in `tests/test_discounts.py` still pass. I did not add tests for the new function because you did not ask for them. I also did not use git.
