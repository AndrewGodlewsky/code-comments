I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The premise needed checking. `orders/model.py:9` said `Order.total` was "amount due, in integer cents". That is false. The existing tests use `Decimal("12.50")`, and `apply_discount` works in dollars, so `total` is a `Decimal` in dollars. A probe confirmed it: `Order('X', Decimal('12.50')).total + 30` gives `Decimal('42.50')`, which would add 30 dollars instead of 30 cents.

So the fee is `Decimal("0.30")`, with `CARD_PROCESSING_FEE` as a module constant.

What I changed:
- `orders/model.py:9`: corrected the comment to "amount due, in dollars as a Decimal". This is a description of code, so I fixed it in place and left the code alone.
- `orders/fees.py`: new file with `add_card_fee`.
- `tests/test_fees.py`: new file. It checks that `Decimal("12.50")` becomes `Decimal("12.80")` and that the same order object is returned.

Verification: `python -B -m unittest discover -s tests -t .` runs 5 tests, all passing (3 existing, 2 new). No bytecode was written.
