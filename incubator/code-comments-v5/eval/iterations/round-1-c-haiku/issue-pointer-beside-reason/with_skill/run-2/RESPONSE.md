I changed `format_amount` in `billing/export.py` so every amount is written with exactly two decimal places. It now returns `Decimal(str(value)).quantize(Decimal("0.01"))` as a string, so 12.5 becomes "12.50" and 3 becomes "3.00". I added a comment above the function recording that the vendor importer rejects the whole file unless amounts match `^\d+\.\d{2}$`, that the importer cannot be changed, and that the rule is tracked in #212.

I did not run the code or any tests, because none were provided and I had no way to execute them here.

One open risk: the importer's pattern has no minus sign, so a negative amount such as -3.00 would still fail the whole file. The code does not show whether negative amounts occur, so I did not handle them. If credit notes or refunds can appear in this export, the vendor's pattern needs checking before the next nightly run.
