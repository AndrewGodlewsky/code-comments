I added `add_card_fee(order)` in `orders/fees.py`, with a test in `tests/test_fees.py`. It adds
`Decimal("0.30")` to `order.total` and returns the order.

One correction on the way: the comment on `Order.total` in `orders/model.py` said the total
is in integer cents, but it is not. The existing tests build orders such as
`Order("A-1001", Decimal("12.50"))` and expect a 20% discount to leave `Decimal("10.00")`, so
totals are Decimal dollars. Adding 30 would have charged a $30 fee. I changed the comment to
say dollars, as a Decimal, and left the code alone.
