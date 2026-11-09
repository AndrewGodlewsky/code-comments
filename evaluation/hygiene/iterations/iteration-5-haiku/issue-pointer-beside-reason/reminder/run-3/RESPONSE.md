Issue #212: invoice amounts now export with two decimal places.

The fix is in `billing/export.py`. `format_amount` used to return `str(value)`, so 12.5 went out as "12.5" and 3 as "3", which the finance vendor's `^\d+\.\d{2}$` check rejects for the whole file. It now converts the value through `Decimal` and rounds it to cents (ROUND_HALF_UP), so:

- 12.5 becomes "12.50"
- 3 becomes "3.00"
- 2.675 becomes "2.68"

Going through `str(value)` before `Decimal` means float artifacts are not introduced. The docstring now describes the two-decimal output. I did not change `export_row`, whose docstring is still accurate.

I checked these values by calling the function directly; I did not run the nightly import or the vendor's validator.

One thing to confirm with the finance side: amounts with more than two decimal places are rounded, not rejected. If any invoice could carry sub-cent precision that should be an error instead, tell me and I will make it fail. Negative amounts (for example credit notes) would still be written with a minus sign, which the vendor's pattern also rejects. I left that alone because nothing in this change addresses it.
