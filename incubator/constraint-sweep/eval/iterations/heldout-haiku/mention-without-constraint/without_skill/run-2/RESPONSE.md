I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, currency="CHF")` rounds to the nearest 0.05 CHF, with halves rounding up. For example, 2.37 becomes 2.35, and 2.375 becomes 2.40.
- `round_price(amount)` with no currency is unchanged. It still rounds to the cent with halves rounding up.

I added tests for both paths in `tests/test_rounding.py`. The unit tests pass (`python -m unittest discover -s tests -t .`, 8 tests, all OK).

Decision for you: any other currency code also falls back to cent rounding. If other currencies need their own rules, the `if currency == "CHF"` branch is the place to add them.
