I added `add_card_fee(order)` in `orders/fees.py`, with a test in `tests/test_fees.py`. Order
totals are integer cents, so it adds 30 to `order.total` and returns the order. The tests pass.
