Issue #212: invoice amounts now export with two decimal places

The nightly import rejected the invoice file twice because amounts such as 12.5 and 3 do not match the importer's ^\d+\.\d{2}$ rule. I changed billing/export.py so every amount is written with exactly two decimals: 12.5 becomes "12.50", 3 becomes "3.00", and "7.25" stays "7.25".

What changed: format_amount() now converts the value to a Decimal, rounds it half-up to the cent, and formats it as a fixed-point string. Going through str() first means float noise such as 0.1 + 0.2 becomes "0.30" rather than leaking into the file, and large values are written without exponent notation.

What I checked: I ran format_amount and export_row on sample inputs (12.5, 3, "3", 0.1 + 0.2, 1e20, 2.675, 10, "7.25"). Each output matched ^\d+\.\d{2}$ and the exported row for a 12.5 invoice came out as ['INV-1', 'Acme', '12.50']. I did not run the real importer, and the repository has no test suite.

Two things to decide:
1. Amounts with more than two decimals (for example 2.675) are rounded to the cent, so 2.675 is written as 2.68. If you would rather such amounts stop the export, that is a small change, but it needs a decision on how the file should be handled.
2. Negative amounts, such as -4.5 (written as -4.50), still fail the importer's pattern because it allows no minus sign. The fix above does not change that. Credit notes would need the vendor to accept a leading minus or a different export format.
