I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, "CHF")` rounds to the nearest 0.05, with halves rounding up. For example, 2.52 becomes 2.50, 2.53 becomes 2.55, and 2.525 becomes 2.55.
- `round_price(amount)` with no currency is unchanged. It still rounds to the cent with halves rounding up.
- Any currency other than "CHF" also gets the cent rounding.

I added tests for both behaviours in `tests/test_rounding.py`. All 7 tests in the repo pass.

None of the existing callers pass a currency yet: `invoices/lines.py`, `pricing/tax.py`, `shop/labels.py` and `shop/reports.py`. Swiss prices will not round to 0.05 until those callers pass "CHF". I left them alone because the request was only about `round_price`.

Two things to check when you wire them up:
- `shop/labels.py` formats the rounded value to two decimals, which works fine for 0.05 steps.
- `shop/reports.py` says its totals must match the sum of the invoice lines to the cent. If CHF is rounded on the lines, the totals should be rounded the same way.
