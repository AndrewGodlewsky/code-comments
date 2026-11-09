Fixed `format_amount` in `billing/export.py` so every invoice amount is written with exactly two decimal places. 12.5 now exports as "12.50", 3 as "3.00", and string or Decimal amounts are handled the same way. Every amount I checked matches `^\d+\.\d{2}$`, including the sample values above.

I added a docstring that records the vendor importer's rule and points to #212, since that issue is where the constraint came from. The importer itself is unchanged.

Two things need your decision:

1. Rounding. Amounts with more than two decimals (for example 2.345) are rounded half-up to two places (2.345 becomes "2.35"). You did not specify a rounding rule, and I have not found a reason for this one in the repository. Please confirm it, or tell me which rule the accounting team expects. If amounts with more than two decimals should never reach the export, that would be a separate check.

2. There are no tests in this repository, so I checked the behaviour with a quick manual run rather than a test suite.

The changes are uncommitted.
