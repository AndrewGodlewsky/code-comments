I fixed `billing/export.py` so every amount is written with exactly two decimal places. `format_amount` now returns `f"{value:.2f}"`, so 12.5 becomes "12.50" and 3 becomes "3.00". `export_row` is unchanged because it already calls `format_amount`.

I added a comment beside the formatting code that records the importer constraint (`^\d+\.\d{2}$`, which rejects the whole file otherwise) and points to issue #212. I also updated the docstring to say the result has exactly two decimal places.

Things to check:
- `format_amount` assumes `amount` is a number (int, float or Decimal). A string such as "12.5" would now raise a ValueError, where the old `str()` passed it through. I did not check how `invoice["amount"]` is populated, so please confirm it is numeric.
- Values are rounded to two places using float formatting. Amounts with more than two decimals are rounded, not rejected. Negative amounts still fail the importer's regex, and I did not change that.
- `billing/__init__.py` is empty and was not changed.
- I did not run any tests, because the repository contains none that I could find in the input files.
