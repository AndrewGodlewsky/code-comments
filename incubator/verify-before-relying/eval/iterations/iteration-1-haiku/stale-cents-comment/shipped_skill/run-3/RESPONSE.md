I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

Changes:
- `orders/fees.py` (new): `add_card_fee` adds `CARD_PROCESSING_FEE = Decimal("0.30")` to the total.
- `orders/model.py`: the comment on `Order.total` said "amount due, in integer cents". The existing tests use `Decimal` dollar amounts (`Decimal("12.50")` gives `Decimal("10.00")` after a 20% discount), so the comment was false. I changed it to "amount due, in dollars as a Decimal".

The existing 3 tests pass. A quick check of `add_card_fee` on an order of 12.50 gives 12.80.

Please confirm the unit. I took dollars from the tests, not from a stated requirement. If `total` is really integer cents, the fee should be `30` and the model comment and tests need to change.
