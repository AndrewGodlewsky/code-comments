Hi,

I fixed `billing/export.py` so every amount in the invoice export is written with exactly two decimal places. `format_amount` now converts each value to a decimal and quantizes it to cents, so 12.5 becomes "12.50" and 3 becomes "3.00". Values with more than two decimal places are rounded half-up to cents (1234.567 becomes "1234.57"). Strings such as "7.5" are also accepted.

I checked the output against `^\d+\.\d{2}$` for 12.5, 3, 0.1, 1234.567, "7.5", 2.675 and 10, and all of them match. I also added a comment beside the function that records the vendor constraint and points to issue #212.

Two things to be aware of:
- Negative amounts would still produce a leading minus sign (for example "-3.00"), which the importer's pattern rejects. I did not change that, because nothing I was given says how credits should be exported. If the export can contain credit notes, they need a decision from you or the finance vendor.
- I chose half-up rounding for amounts with more than two decimals. Nothing in the request specified a rounding rule, so please confirm it matches what the accounting team expects.

No tests were added. I only checked the formatting with the sample values above.
