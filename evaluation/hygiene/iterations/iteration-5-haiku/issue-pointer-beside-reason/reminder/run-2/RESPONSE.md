Hi,

The export now writes every amount with exactly two decimal places, so the nightly import's `^\d+\.\d{2}$` check should accept the file. For example, 12.5 is written as "12.50" and 3 as "3.00".

What changed, in `billing/export.py`:

- `format_amount` converts the value to a Decimal, rounds it to cents, and returns it as a string with two decimal places. It uses `Decimal(str(value))`, so float artifacts such as 0.1 + 0.2 come out as "0.30" rather than a long decimal.
- The docstring now describes the two-decimal output. `export_row` is unchanged and still returns the same row layout.

One behaviour to be aware of: any amount with more than two decimal places is now rounded half-up to the nearest cent (for example, 1234.005 becomes "1234.01"). Previously such a value would have been written as-is and would also have failed the importer's check. If the finance team wants amounts like that rejected instead of rounded, tell me and I will change it.

I checked the function directly on sample values (12.5, 3, "3", 10, 0, "7.25", 1234.005) and each result matched the pattern. The repository has no test suite, so I did not add tests and did not run the nightly import.

Nothing has been committed.
