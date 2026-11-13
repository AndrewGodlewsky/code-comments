I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is stored as `CARD_PROCESSING_FEE = 30`, in integer cents, the same unit `Order.total` uses. The function is not idempotent: calling it twice on the same order adds the fee twice. I did not add a test; say if you want one in `tests/`.
