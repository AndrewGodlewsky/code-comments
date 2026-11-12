I fixed `format_amount` in `billing/export.py` so every amount is written with exactly two decimal places. It now returns `format(Decimal(str(value)), ".2f")`, so 12.5 becomes "12.50", 3 becomes "3.00", and "7" becomes "7.00". I checked these outputs by running the function. The docstring now states the two-decimal contract and points to #212 as the reason. `billing/__init__.py` is empty and needed no change.

One thing to confirm: amounts with more than two decimal places are rounded to two places using Decimal's default rounding (half-even), so 1234.005 becomes "1234.00". If the finance team needs a different rounding rule, tell me and I will change it.

Nothing was committed, and nothing outside the repository was changed.
