I added `currency` to the nightly CSV export, but as the last column rather than beside `amount`.

The reason is `deploy/warehouse/load_ledger.sql`. The warehouse loader skips the header and reads each row by position (`c1`..`c4` map to `entry_id`, `account_code`, `amount`, `posted_at`). If `currency` went between `amount` and `ts`, `ts` would move to position 5 and the loader would silently put the currency code into `posted_at`. Appending at the end leaves every existing position unchanged, so the loader keeps working as it does now.

What changed:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment saying new columns go at the end because the loader is positional.
- `tests/test_csv_out.py`: added checks that `currency` is in the header, that the first four columns keep their positions, and that the value `EUR` lands under the `currency` header.

Tests: all 8 pass (`python -m unittest discover -s tests -t .`). Sample output for one entry:
```
id,account,amount,ts,currency
E-1,4000,12.50,2026-11-01T09:00:00Z,EUR
```

Not changed, and needing a decision:
- The warehouse load still ignores the new column because `load_ledger.sql` only selects `c1`..`c4`. If finance needs currency in the warehouse, `ledger_raw` needs a new column added at the end (`ALTER TABLE ... ADD COLUMN`, as `schema.sql` describes) and the load needs `c5` added to the SELECT.
- `reports/monthly.py` reads by header name, so it is unaffected. Totals are still summed across currencies without conversion, as before.
- Nothing was committed; this exercise was run without git.
