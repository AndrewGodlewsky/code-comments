I added `currency` right after `amount` in `COLUMNS` (export/columns.py). `write_export` picks it up from each payment record, which already carries a currency.

As the docstring in export/columns.py says, the bank's import job reads columns by position from `ingest/layout.json`, so I added `currency` there in the same place. Without that, the reader would have put the currency code in `reference` and dropped the real reference. The tests pass.
