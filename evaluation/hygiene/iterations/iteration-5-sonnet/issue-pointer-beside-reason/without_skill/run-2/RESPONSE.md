Issue #212 is fixed in billing/export.py: `format_amount` now always writes exactly two decimal places, so 12.5 becomes "12.50" and 3 becomes "3.00". That matches the importer's `^\d+\.\d{2}$` check.

I ran it on 12.5, 3, "7", 0, 2.675 and 1234.567. All came out with two decimals.

- **Rounding:** values with more than two decimals are rounded half-up, so 2.675 gives "2.68". Floats are converted via their printed form first, so they round as written. If finance wants different rounding, say so.
- **Negative amounts:** these would come out as "-5.00", which the importer's pattern would still reject. Nothing in the current code suggests they occur, so I left it alone.
- **Tests:** I only ran the spot checks above. The repository has no test suite.
