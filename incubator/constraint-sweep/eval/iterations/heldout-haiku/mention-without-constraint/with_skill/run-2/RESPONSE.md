I added the `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, currency=None)`. With `"CHF"`, the amount rounds to the nearest 0.05, halves up. With no currency, the code is the same cent rounding as before.
- `"CHF"` is the only currency with new behaviour. Any other value also falls back to cent rounding. You did not say what other currencies should do, so tell me if they need their own rule.
- I added tests to `tests/test_rounding.py` for the no-currency path, for CHF rounding (2.37 to 2.35, 2.38 to 2.40), and for CHF halves rounding up (2.375 to 2.40). All 8 tests pass.

Sweep: `round_price` is called from `pricing/tax.py`, `invoices/lines.py`, `shop/labels.py` and `shop/reports.py`. Each has a comment or docstring that states a constraint. All of them call without a currency, so the default path is unchanged and all four stay live and are kept:
- `pricing/tax.py:10`: add_vat is rounded once with round_price.
- `invoices/lines.py:10-11`: a line product is rounded once, not unit by unit.
- `shop/labels.py:9-10`: a label never shows a fraction of a cent.
- `shop/reports.py:10`: daily totals match the invoice lines to the cent.

No stale constraints were found, and I did not change any other file.
