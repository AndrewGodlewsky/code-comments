I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- With no currency (`round_price(x)` or `round_price(x, None)`), the code path is unchanged: it rounds to the cent with halves up.
- With `"CHF"`, it rounds to the nearest 0.05 with halves up, then returns a two-decimal value. For example, 2.32 becomes 2.30, 2.33 becomes 2.35, and 2.345 becomes 2.35.
- Any other currency raises `ValueError`. I chose this over silently falling back to cent rounding, since that would round Swiss prices wrongly without warning. Tell me if you would rather other currencies fall back to the cent.

Before changing the function, I grepped the whole repository, all file types including dotfiles, for `round_price` and the rounding terms. The constraints I found, all kept:

- `pricing/rounding.py` module docstring: "Every amount is rounded here, nowhere else." The new CHF branch lives in this same function, so this still holds.
- `pricing/rounding.py` function docstring: cent rounding with halves up. I kept this for the default path and documented the CHF branch next to it.
- `README.md`: `round_price` is "the one place money is rounded." Still true.
- `invoices/lines.py` docstring: a line is rounded once, not unit by unit. Its call has no currency, so it is unchanged.
- `pricing/tax.py` docstring: VAT is rounded once with `round_price`. Unchanged.
- `shop/labels.py` comment: labels never show a fraction of a cent. Its call has no currency, so it is unchanged.
- `shop/reports.py` docstring: daily totals round to the cent so they match the invoice lines. Its call has no currency, so it is unchanged. A CHF total would not match cent-based lines, so callers that mix currencies need to know this.
- `tests/test_rounding.py` and `tests/test_totals.py`: cent rounding and halves-up cases. The existing tests are unchanged and still pass.

I added tests in `tests/test_rounding.py` for the explicit `None` path, the CHF rounding cases, and the rejected currency. All 8 tests pass with `python -m unittest discover -s tests -t .`.

No other files needed changes.
