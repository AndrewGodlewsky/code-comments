I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, "CHF")` rounds to the nearest 0.05, with halves rounding up (2.37 gives 2.35, 2.38 gives 2.40, 2.375 gives 2.40).
- `round_price(amount)` and `round_price(amount, None)` take the same path as before and round to the cent, so existing callers (`invoices/lines.py`, `pricing/tax.py`, `shop/labels.py`, `shop/reports.py`) are unaffected.
- Any other currency code also rounds to the cent. Nothing in the request covered other currencies, so I kept that as the default. Tell me if another currency needs its own rule.

I added tests to `tests/test_rounding.py` for the no-currency path and for CHF rounding, including the half-way cases. All 8 tests pass (`python -m unittest discover -s tests -t .`).
