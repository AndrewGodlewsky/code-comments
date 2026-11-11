I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, "CHF")` rounds to the nearest 0.05 CHF, with halves rounding up (2.37 gives 2.35, 2.38 gives 2.40).
- `round_price(amount)` with no currency is unchanged: it still rounds to the cent, with halves rounding up.
- Any other currency string also falls back to cent rounding. Tell me if you would rather it raise an error.

Constraints I found by grepping the whole repository (all file types, including hidden files):

- The module docstring says "Every amount is rounded here, nowhere else." It still holds. I kept it.
- The `round_price` docstring said "to the cent". I updated it to describe the cent default and the CHF step.
- `README.md` says `round_price` is "the one place money is rounded". Still true, and I left it alone.
- `shop/labels.py` (`price_label`) comments that labels never show a fraction of a cent. It calls `round_price` without a currency, so it is unchanged. Swiss labels would still show cent precision. Changing that needs a currency passed through `price_label`, which I did not do.
- `shop/reports.py` (`daily_total`) says totals match the invoice lines to the cent. It also calls without a currency, so it is unchanged. A CHF daily total would need the same change, which I did not make.
- `pricing/tax.py` (`add_vat`) and `invoices/lines.py` (`line_total`) call `round_price` without a currency and are unchanged.
- The existing tests in `tests/test_rounding.py` and `tests/test_totals.py` still pass. I added CHF and default-behaviour tests to `tests/test_rounding.py`.

Test run: `python -I -m unittest discover -s tests -t .` gives 9 tests, all passing.

The changed files are `pricing/rounding.py` and `tests/test_rounding.py`.
