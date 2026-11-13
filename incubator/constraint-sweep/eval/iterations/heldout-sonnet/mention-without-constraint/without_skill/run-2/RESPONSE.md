`round_price` now takes an optional `currency` argument (`round_price(amount, currency=None)`) in `pricing/rounding.py`.

- With `currency="CHF"` it rounds to the nearest 0.05, with halves rounding up. For example, 2.32 becomes 2.30, 2.33 becomes 2.35 and 2.375 becomes 2.40.
- With no currency (or `None`) the code path is the same as before, so it rounds to the cent with half-up.
- Any other currency value also gets the default cent rounding.

I added tests for CHF rounding and for the unchanged default in `tests/test_rounding.py`, and ran the suite.

The existing callers (tax, invoice lines, labels, reports) don't pass a currency, so they still round to the cent. Swiss cash totals won't get 0.05 rounding until those callers pass "CHF". I left them alone because you didn't ask for that.
