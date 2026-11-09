Hi,

I fixed the amount formatting in `billing/export.py` so every amount in the invoice file is now written with exactly two decimal places. For example, 12.5 becomes "12.50" and 3 becomes "3.00". Amounts will match the importer's `^\d+\.\d{2}$` check, so the whole file should no longer be rejected for formatting.

What changed: `format_amount` now converts the value through `Decimal` and quantizes it to cents, so float artefacts such as 0.1 + 0.2 come out as "0.30" rather than "0.30000000000000004". I checked the output for integers, floats, numeric strings and a value with three decimals; every result matched the pattern.

One thing to be aware of: an amount with more than two decimal places (for example 1234.567) is now rounded half-up to cents (1234.57) instead of being exported as-is. That is the only way to satisfy the importer's format. If you would rather such amounts stop the export so someone can look at them, let me know and I can change that.

I have not run the nightly import itself, and the repository has no test suite for this module, so the check above was a manual one.
