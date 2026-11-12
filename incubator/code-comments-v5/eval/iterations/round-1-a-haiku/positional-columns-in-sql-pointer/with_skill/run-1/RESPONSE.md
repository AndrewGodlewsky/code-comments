The nightly CSV export now has a `currency` column directly after `amount`:

```
id,account,amount,currency,ts
E-1,4000,12.50,EUR,2026-11-01T09:00:00Z
```

Changes:

- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "currency", "ts"]`.
- `deploy/warehouse/load_ledger.sql`: the warehouse load reads the export by position (`c1..c4`), so inserting `currency` would have shifted `ts` into `c4`'s place and loaded it into `posted_at` under the wrong column. The SELECT now reads `c1, c2, c3, c5`, skipping `c4` (currency). The comment above it now lists the positions. The old comment said new columns must go at the end, which no longer describes this change, so I replaced it.
- `tests/test_csv_out.py`: added a test that `currency` sits immediately after `amount` and carries the entry's value.

All 7 unit tests pass. `reports/monthly.py` reads by header name, so it is unaffected. `docs/finance.md` needs no change.

Things to check before this ships:

1. Deploy the exporter and the SQL change together. The cron runs the export at 01:00 and the load at 01:30 from the same checkout. If the SQL goes out first, tonight's load will read the old 4-column files, `c5` will be NULL, and `posted_at NOT NULL` will fail the insert. Likewise, reloading an old-format file after this change will fail. If you would rather not touch the production SQL, the alternative is to append `currency` at the end of `COLUMNS` and leave `load_ledger.sql` as it was. That meets the header-name requirement but not the side-by-side request.
2. The warehouse table `ledger_raw` has no currency column, so the loaded data still does not include currency. Finance's spreadsheet export gets it; the warehouse does not. Add a column to `deploy/warehouse/schema.sql` (appended at the end) and to the load if the warehouse needs it.
3. Nothing was committed. Per the instructions for this run, no git commands were used.
