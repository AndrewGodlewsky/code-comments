`round_price` in `pricing/rounding.py` now takes an optional `currency` argument, defaulting to `None`.

- `currency="CHF"` rounds to the nearest 0.05 (halves round up), so 2.37 becomes 2.35 and 2.375 becomes 2.40.
- With no currency, or any other currency, it behaves exactly as before: round to the cent, half up.

I checked every use of `round_price` before changing it (`invoices/lines.py`, `pricing/tax.py`, `shop/labels.py`, `shop/reports.py`, the tests, and the README). All of them call it with one argument, so they keep the old behaviour. None of their comments constrain it in a way this change affects. I did not edit those files.

I ran the existing tests and a few CHF examples by hand. I did not add tests for CHF.
