I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object.

The fee is stored as `Decimal("0.30")` because the existing order totals are `Decimal` dollar amounts (see `tests/test_discounts.py`, e.g. `Decimal("12.50")`). I also added `tests/test_fees.py` with two tests (the fee is added to the total, and the same order is returned). All 5 tests pass with `python -m unittest`.

One thing to check: the comment on `Order.total` in `orders/model.py` says the total is "in integer cents", but the code and tests treat it as dollars in `Decimal`. I did not change that comment, since it is outside this request. If the comment is right and totals really are integer cents, the fee would need to be `30` instead, and the test expectation would change too.
