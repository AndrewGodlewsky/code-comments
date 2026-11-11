I added `add_card_fee(order)` in `orders/fees.py`. It adds 30 to `order.total` and returns the order. I also added `tests/test_fees.py`, and the full test suite passes.

The fee is 30 because `Order.total` is stored in integer cents. The comment in `orders/model.py` says so, and `apply_discount` and its tests treat the total the same way. The 30-cent fee is therefore the integer 30, not 0.30.

I found no conflicts between the comments or docs and what the code does, so I corrected nothing.
