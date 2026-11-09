I changed `format_amount` in `billing/export.py` so every amount is written with exactly two decimal places: 12.5 becomes "12.50" and 3 becomes "3.00".

I also added a comment beside the formatting line. It says the finance vendor's importer matches each amount against `^\d+\.\d{2}$` and rejects the whole file on any mismatch, and that we can't change the importer (#212). I didn't run it or add tests.

- **Negative amounts:** these would be written as "-5.00", which doesn't match the importer's pattern, so the file would still be rejected. Nothing I read says whether negative amounts occur (credit notes, for example). If they do, we need to know how the vendor expects them written.
- **Rounding:** values with more than two decimals are rounded by Python's float formatting. If amounts can be stored as floats with more precision, tell me whether you want `Decimal`-based rounding.
