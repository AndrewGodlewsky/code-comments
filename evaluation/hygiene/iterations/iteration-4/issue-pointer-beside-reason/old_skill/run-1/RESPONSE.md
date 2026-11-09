Hi,

I fixed the amount formatting in `billing/export.py` so every amount is written with exactly two decimal places. `format_amount` used to return `str(value)`, so 12.5 went out as `12.5` and 3 as `3`, and the importer rejected the whole file. It now returns `f"{float(value):.2f}"`:

- 12.5 becomes "12.50"
- 3 becomes "3.00"
- "7" (a string) becomes "7.00"

I also added a short note to the `format_amount` docstring saying the importer rejects the whole file unless every amount matches `^\d+\.\d{2}$`, so the two-decimal rule should not be removed. `export_row` is unchanged because it already calls `format_amount`.

I checked the output with a quick script: every formatted value matches `^\d+\.\d{2}$`, and `export_row` returns `[1, 'Acme', '12.50']` for an amount of 12.5. The repository has no test suite, so I did not add tests.

Things to check before the next nightly run:

1. Negative amounts still fail. The pattern has no minus sign, so a credit of -5 would be written as "-5.00" and still reject the file. I did not change this because the request did not cover it. If credits can appear in this export, the vendor needs to accept them or they need a different treatment.
2. Rounding. Amounts with more than two decimals are rounded silently, and binary floats round some values unexpectedly (2.675 becomes "2.67"). If the amounts are money values held as `Decimal`, the formatting should use `Decimal` with an explicit rounding mode instead. I do not know the type of `invoice["amount"]` in the rest of the system, so I used float.
3. The fix was checked only against the sample values above. It has not been run against a real invoice file or the vendor's importer.
