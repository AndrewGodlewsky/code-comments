Fixed issue #212 in `billing/export.py`. `format_amount` now returns `f"{value:.2f}"`, so every amount is written with exactly two decimal places: 12.5 becomes "12.50" and 3 becomes "3.00". `export_row` is unchanged because it already calls `format_amount`.

I added a comment above the return line that records the importer's `^\d+\.\d{2}$` check and the #212 rejection, so the next editor knows why the format must not drift back to `str(value)`.

Caveats:
- `.2f` rounds using float arithmetic and round-half-even. If invoice amounts are stored as floats, values such as 0.125 may round unexpectedly. Storing amounts as `Decimal` would make the rounding explicit. I did not change the amount type because the request did not cover it.
- Amounts with more than two decimal places are rounded silently to two. If the finance team expects an error for those instead, tell me and I will change it.
- I did not add tests because the repository has none for billing.
