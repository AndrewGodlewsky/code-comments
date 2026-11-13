I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount)` with no currency behaves exactly as before: it rounds to the cent, halves up.
- `round_price(amount, "CHF")` rounds to the nearest 0.05, halves up. For example, 2.33 becomes 2.35 and 2.32 becomes 2.30.
- Any other currency value also rounds to the cent. The request did not cover other currencies, so I chose this. If you want them to raise an error instead, say so.

I added tests in `tests/test_rounding.py` for the no-currency path and the CHF path. All 7 tests pass (`python -m unittest discover -s tests -t .`).

Constraint sweep:
- Every caller (`invoices/lines.py`, `pricing/tax.py`, `shop/labels.py`, `shop/reports.py`) calls `round_price` without a currency, so they keep the cent rounding they rely on. No live constraint was broken, and I left those files unchanged.
- The `round_price` docstring said it always rounds to the cent. That became false with the CHF branch, so I corrected it.
- `shop/labels.py` (line 9) and `shop/reports.py` (line 10) say that `round_price` gives cent precision. The default path still does, so both comments remain true.
- `README.md` line 5 describes `round_price` as the one place money is rounded. It is still accurate, so I left it unchanged.
