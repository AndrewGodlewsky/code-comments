I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, "CHF")` rounds to the nearest 0.05 (halves round up), so 2.32 gives 2.30 and 2.33 gives 2.35.
- `round_price(amount)` with no currency still rounds to the cent, exactly as before.

I also added two tests to `tests/test_rounding.py` covering the CHF rule and the unchanged default. All 7 tests pass (`python -m unittest discover -s tests -t .`).

Notes:
- No existing caller passes a currency yet, so current totals, VAT, labels and invoice lines are unchanged.
- Any amount passed with "CHF" is rounded to 0.05, not only cash prices. If card or invoice amounts should keep cent rounding, the callers will need to choose that explicitly.
