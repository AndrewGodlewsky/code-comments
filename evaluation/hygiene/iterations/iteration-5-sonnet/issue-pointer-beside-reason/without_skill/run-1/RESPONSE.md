Issue #212 is fixed in `billing/export.py`: `format_amount` now always writes exactly two decimal places, so 12.5 becomes "12.50" and 3 becomes "3.00". That matches the vendor's `^\d+\.\d{2}$` check.

- It converts through `Decimal(str(value))` and rounds half-up to cents. This avoids float artifacts, so 2.675 gives "2.68" rather than "2.67".
- Values with more than two decimals are rounded, not rejected. Say so if you'd rather fail loudly on those.
- Negative amounts would produce "-5.00", which the vendor's pattern rejects. I left that alone because I don't know whether credits appear in the file.
- I ran it by hand on 12.5, 3, "3", 0.1, 1234.567 and 2.675 and the output was correct. There is no test suite in the repo, so I added no tests.
