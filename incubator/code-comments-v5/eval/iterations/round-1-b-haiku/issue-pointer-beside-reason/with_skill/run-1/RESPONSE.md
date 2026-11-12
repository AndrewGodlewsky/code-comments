Fixed `billing/export.py` so every amount is written with exactly two decimal places. `format_amount` now returns `f"{Decimal(str(value)):.2f}"`, so `12.5` becomes `"12.50"` and `3` becomes `"3.00"`. I added a comment above it citing #212 and the importer's `^\d+\.\d{2}$` rule, so the reason stays next to the code.

I checked the function directly: `12.5` gives `12.50`, `3` gives `3.00`, `"7.1"` gives `7.10`, `0.1+0.2` gives `0.30`, and `10**16` gives `10000000000000000.00`. I did not run any test suite, because the exercise has none.

Amounts are converted through `str()` before `Decimal`, which avoids binary float artefacts. Rounding uses Decimal's default (half-even) when a value has more than two decimal places. Tell me if the finance team expects half-up rounding instead.

One thing the fix does not cover: the importer's pattern also rejects negative amounts, so a credit note such as `-3.5` would still be written as `-3.50` and would still fail the file. If credit notes can reach this export, that needs a separate decision from the vendor or from you.
