Hi Finance,

The nightly CSV export now has a `currency` column with the ISO 4217 code of each entry (for example `EUR`). It is the last column, after `ts`, not directly next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` reads the export by position (`c1`..`c4` map to id, account, amount, ts). If `currency` went between `amount` and `ts`, the loader would put the currency code into the `posted_at` field and the timestamps would be lost in the warehouse. The comment in that file says new export columns must go at the end, so I followed that rule.

Your team finds columns by header name, so the column order does not affect your spreadsheets. The header row is now `id,account,amount,ts,currency`.

What changed:
- `exporter/csv_out.py`: added `currency` to `COLUMNS` at the end, with a comment explaining the placement.
- `tests/test_csv_out.py`: added a check that the header ends with `currency` and that the currency value is written.

The loader and the schema are unchanged. The monthly report reads columns by name, so it is unaffected. All 8 unit tests pass.

If you really need `currency` next to `amount`, that is a coordinated change: `load_ledger.sql` would have to select `c1, c2, c3, c5`, and the warehouse would need to ignore the currency field. That should go out in the same deploy as the export change, so the 01:00 export and 01:30 load never disagree. I have not made that change.
