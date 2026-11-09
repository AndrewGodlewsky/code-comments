Hi,

I've fixed the invoice export so every amount is written with exactly two decimal places. 12.5 is now written as "12.50" and 3 as "3.00", which matches the importer's ^\d+\.\d{2}$ check.

The change is in billing/export.py, in format_amount(). It converts the amount with Decimal rather than str(), so values like 7.1 become "7.10" and whole numbers become "x.00".

One behaviour to be aware of: if an amount has more than two decimal places (for example 12.345), the export now raises a ValueError instead of silently rounding it. I chose this because rounding a money value without notice could make the totals disagree with the invoices. If you would rather the export round to the nearest cent, that is a one-line change, but it needs your decision.

I checked the function against sample values (12.5, 3, "3", 7.1, 0, "1E+2" and 12.345) and confirmed that every accepted output matches the importer's pattern. I did not run the nightly import itself, and the repository has no tests for this module.

Negative amounts are not handled specially. They would still be written with a leading minus sign, which the importer's pattern does not accept. Let me know if credit notes can reach this export.
