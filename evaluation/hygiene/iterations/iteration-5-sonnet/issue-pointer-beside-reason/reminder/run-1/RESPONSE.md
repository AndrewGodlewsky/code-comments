I fixed `format_amount` in `billing/export.py` so every amount is written with exactly two decimal places: 12.5 becomes "12.50" and 3 becomes "3.00". I ran it on 12.5, 3 and 0.1+0.2, and they gave "12.50", "3.00" and "0.30". I didn't add a test file.

I also updated the function's docstring, which only said "formatted for the export file". I added a short comment saying why the format is fixed: the vendor's importer rejects the whole file unless amounts match `^\d+\.\d{2}$`, and we can't change it (issue #212).

One thing to be aware of: `f"{value:.2f}"` rounds amounts that have more than two decimals (round-half-even on the binary float value). If amounts can arrive as floats with more precision than cents, it would be safer to store them as `Decimal` or integer cents upstream.
