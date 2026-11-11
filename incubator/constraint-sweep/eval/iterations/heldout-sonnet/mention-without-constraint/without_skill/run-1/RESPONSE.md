`round_price` in `pricing/rounding.py` now takes an optional `currency` argument.

- `round_price(amount, "CHF")` rounds to the nearest 0.05, with halves rounding up. For example 2.32 becomes 2.30, 2.33 becomes 2.35, and 2.325 becomes 2.35.
- With no currency, or any currency other than "CHF", it behaves exactly as before: round to the cent, halves up.

I added tests for CHF rounding, CHF halves, and a non-CHF currency in `tests/test_rounding.py`, and the suite passes.

Existing callers (invoices, tax, labels, reports) don't pass a currency, so none of them change. To get Swiss cash rounding in those paths, they need to pass the currency through.
