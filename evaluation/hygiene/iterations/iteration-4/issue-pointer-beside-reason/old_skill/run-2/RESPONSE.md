Issue #212: `billing/export.py` now writes every amount with exactly two decimal places.

What changed: `format_amount` in `billing/export.py` converts the value to a `Decimal` and quantizes it to cents, so 12.5 becomes "12.50", 3 becomes "3.00", and 19.999 becomes "20.00". The docstring now states the two-decimal contract and why it exists (the vendor importer checks `^\d+\.\d{2}$` and rejects the whole file otherwise, and the importer cannot be changed). `export_row` is unchanged because it already calls `format_amount`.

Checked: I ran `format_amount` on 12.5, 3, "7", 0.1+0.2, 19.999, 2.675, 10.0 and 100. Every output matched `^\d+\.\d{2}$`. I did not run the nightly import or the vendor importer itself.

Two things to confirm:
1. Rounding. Amounts with more than two decimals are now rounded, not truncated, and I chose ROUND_HALF_UP (so 2.675 becomes 2.68). Nobody specified a rounding mode. If finance expects a different rule, tell me and I will change it. I did not record a reason for this choice in the code because none was given.
2. Negative amounts and thousands separators. The importer's regex does not accept a minus sign or commas, so a negative credit or an amount like "1,250.00" would still fail the file. I did not change that, because I don't know whether invoices can contain such amounts. If they can, the importer rule needs to be raised with the vendor or the export needs handling for them.
