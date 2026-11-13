I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, currency=None)`. With no currency, or any currency other than "CHF", it still rounds to the cent with halves rounding up, exactly as before.
- With `currency="CHF"`, it rounds to the nearest 0.05, with halves rounding up. For example, 2.37 becomes 2.35, 2.38 becomes 2.40, and 2.375 becomes 2.40.

Existing callers (`tax.py`, `labels.py`, `reports.py`, `lines.py`) pass only the amount, so their behaviour is unchanged. I did not change any of them to pass a currency yet, so CHF rounding is not applied anywhere in the shop until those call sites are updated.

I added tests in `tests/test_rounding.py` for the no-currency path and for CHF rounding. The full suite runs with `python -m unittest discover -s tests -t .` from the repository directory: 7 tests, all passing.

Decision for you: any currency other than "CHF" falls back to cent rounding. If other currencies need their own steps later, they will need a rule for each.
