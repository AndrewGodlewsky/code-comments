I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is `Decimal("0.30")` because `Order.total` holds dollars as a `Decimal`. The existing discount code and tests use that convention. I also corrected the comment on `Order.total` in `orders/model.py`: it said "in integer cents", which the code and tests contradict. It now says "in dollars as a Decimal".

I added `tests/test_fees.py` with two tests (the fee is added, and the same order object is returned). The full suite passes: 5 tests, OK.

One thing to check: if `Order.total` was meant to be integer cents, the fee constant and the comment would both need to change. The current code and tests say dollars.
