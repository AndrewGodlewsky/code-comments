Hi,

I fixed the amount formatting in `billing/export.py` so every amount in the invoice file is written with exactly two decimal places. 12.5 now exports as "12.50" and 3 as "3.00", which matches the importer's `^\d+\.\d{2}$` check.

What changed: `format_amount` now converts the value through `Decimal` and rounds it to cents (ROUND_HALF_UP). Going through `str(value)` first keeps float artifacts such as 0.1 + 0.2 from leaking into the file. Its docstring now states the two-decimal contract. The rest of the file, including `export_row`, is unchanged.

I checked the output with a quick script: 12.5, 3, 3.0, "12.5", 0.1 + 0.2, 1000 and "0.5" all produce strings that match the importer's pattern, and `export_row` returns `['I-1', 'Acme', '12.50']` for a sample invoice. The repo has no test suite, so this was a manual check only.

Things to be aware of:
- Amounts are rounded to the nearest cent. A value with more than two decimals, such as 2.675, is rounded (to 2.68), not truncated or rejected.
- Negative amounts (for example, credit notes) would still fail the importer's pattern, because it has no minus sign. I left that alone because the request was only about decimal places. If credit notes can reach this export, that needs a separate decision with the finance vendor.
- I did not commit anything. The change is uncommitted in the working tree.
