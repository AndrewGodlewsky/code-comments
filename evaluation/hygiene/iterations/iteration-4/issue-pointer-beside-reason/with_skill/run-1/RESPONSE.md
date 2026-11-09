Hi,

I fixed `billing/export.py` so every invoice amount is written with exactly two decimal places. `format_amount` now returns `12.5` as "12.50" and `3` as "3.00". Amounts given as strings, such as "12.5", are handled the same way.

The change uses `Decimal` rather than plain string conversion, so float values such as 0.1 + 0.2 do not leak extra digits into the file. The docstring now records the importer's rule and points to issue #212, since the importer is outside our control.

I checked the function on sample inputs (12.5, 3, "3", 0, 7.1, 0.1 + 0.2). Every output matches `^\d+\.\d{2}$`, and a full row comes out as `[1, 'Acme', '12.50']`. The repository has no test suite, so this was a manual check only.

Two things to decide:

1. **Rounding.** An amount with more than two decimals, such as 1234.005, is now rounded half-up to cents (1234.01). Before, it would have produced a value the importer rejects. If finance expects a different rounding rule, or wants such amounts reported as errors instead, tell me and I will change it.
2. **Negative amounts.** The importer's pattern has no minus sign, so a credit amount such as -12.50 will still fail the whole file. I did not change this because the pattern is the vendor's rule. If we issue negative invoice amounts, we need to ask finance how they should be sent.

The change is uncommitted in the working tree.
