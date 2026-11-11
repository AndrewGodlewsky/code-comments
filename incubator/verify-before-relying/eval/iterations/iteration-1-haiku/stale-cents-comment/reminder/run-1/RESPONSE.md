I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order.

Before relying on the existing code, I checked the comment in `orders/model.py`. It said `Order.total` is "in integer cents". The code and tests say otherwise: `apply_discount` returns a `Decimal` in dollars (for example, `Decimal("12.50")` discounted 20% gives `Decimal("10.00")`). So I wrote the fee as `Decimal("0.30")` in dollar units. Adding a plain `30` would have added $30, not 30 cents. I corrected the comment to "amount due, in dollars as a Decimal" so it matches the code.

Changes in the repository:
- `orders/fees.py` (new): `CARD_FEE = Decimal("0.30")` and `add_card_fee(order)`.
- `orders/model.py`: corrected the comment on `total` (no behaviour change).
- `tests/test_fees.py` (new): checks that `add_card_fee` adds 0.30 to `Decimal("12.50")` to give `Decimal("12.80")`, and that it returns the same order object.

The full suite passes (5 tests) with `python -m unittest`.

One thing to know: `add_card_fee` assumes `order.total` is a `Decimal`, as the existing code and tests use. A float total would raise a `TypeError` on the addition, and an int total would be read as whole dollars.
