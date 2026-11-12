I fixed `billing/export.py` so every amount is written with exactly two decimal places. `format_amount` now returns `12.5` as `"12.50"` and `3` as `"3.00"`. I checked these and a few other values (`"7.1"` becomes `"7.10"`, `0.1 + 0.2` becomes `"0.30"`, `1234` becomes `"1234.00"`).

The change converts the value through `Decimal(str(value))` and quantizes it to two places, so float binary noise does not leak into the output. The docstring records the vendor constraint and points to #212. `export_row` is unchanged.

Two things to check:
- Amounts with more than two decimal places are rounded to two, using Decimal's default rounding (ROUND_HALF_EVEN). Nothing in the request said which rounding rule the accounting side expects. If it needs half-up, that is a one-line change.
- Negative amounts would still produce a leading `-`, which the importer's pattern `^\d+\.\d{2}$` does not match. The request did not mention credit notes, so I left that alone. Tell me if negative amounts can occur.
