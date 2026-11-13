I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order, matching how `apply_discount` works. The fee is `Decimal("0.30")`, because the order totals in the tests are `Decimal` amounts in currency units (for example `Decimal("12.50")`).

I also corrected one comment that was false. `orders/model.py` said `total` was "in integer cents", but the existing tests use `Decimal` currency amounts. I changed it to "a Decimal in currency units (e.g. Decimal("12.50"))". If the shop actually stores cents, the fee constant and that comment both need to change together, so please confirm the unit.

I added `tests/test_fees.py` with two tests: one checks that 30 cents is added to a `12.50` total, and one checks that the same order object is returned. All 5 tests in the repository pass (`python -m unittest discover -s tests -t .`).

I did not commit anything, because the instructions told me not to use git.
