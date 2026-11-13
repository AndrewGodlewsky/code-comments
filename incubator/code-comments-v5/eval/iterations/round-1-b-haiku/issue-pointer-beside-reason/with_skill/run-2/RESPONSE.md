I changed `format_amount` in `billing/export.py` so every amount is written with exactly two decimal places. It now returns `f"{value:.2f}"`, so 12.5 becomes "12.50" and 3 becomes "3.00". `export_row` already calls it, so the invoice file gets the fixed format with no other change.

I also rewrote the function's docstring to state the two-decimal contract and point to issue #212, since the reason for the format lives beside the code. I left `billing/__init__.py` alone.

Checked by running the function directly: 12.5 gives "12.50", 3 gives "3.00", Decimal("7.1") gives "7.10", and -3 gives "-3.00". There is no test suite in this directory, so I did not run one.

Two things to check before this goes live:

1. Amounts with more than two decimal places are now rounded silently. For example, 12.345 is written as "12.35". If upstream values can carry more precision than cents, decide whether to round, or to reject and report them, rather than letting the rounding pass unnoticed.
2. The importer's pattern `^\d+\.\d{2}$` has no minus sign, so a negative amount such as -3.00 will still fail the whole file. I did not check whether invoices can be negative. If they can, that needs a separate decision with the finance vendor.
