I fixed `format_amount` in `billing/export.py` so every invoice amount is written with exactly two decimal places. `12.5` now exports as `"12.50"`, `3` as `"3.00"`, and `12.499` rounds to `"12.50"`.

The change is one function plus an import. The docstring now states the two-decimal contract and points to issue #212, which is why the vendor importer rejects the whole file otherwise. `export_row` is unchanged because it calls `format_amount`.

Things to check:
- Amounts with more than two decimal places are rounded to two (Decimal's default rounding, half-even), not rejected. If the finance team wants a different rounding rule, tell me and I will change it.
- I did not run any tests, because the repository has none for this module that I could see.
