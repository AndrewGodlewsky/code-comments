I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

`Order.total` is stored in integer cents (see `orders/model.py`), so the fee is the constant `CARD_PROCESSING_FEE = 30`, not `0.30`. The constant's comment states the unit.

I did not add tests, and I did not run anything. The function does not check whether the fee has already been applied, so calling it twice adds the fee twice.

I added no other comments, because nothing else about the change needed explaining. I had no reason or source for the fee amount beyond your request, so none is recorded.
