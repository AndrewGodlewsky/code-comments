The nightly CSV export now has a `currency` column with the ISO 4217 code, such as `EUR`. I put it last, after `ts`, not right next to `amount`.

The reason is the warehouse load. `deploy/warehouse/load_ledger.sql` reads the export by position (`c1`..`c4`, where `c3` is amount and `c4` is ts), and the 01:30 cron job runs it on the same file. A column inserted between amount and ts would shift `ts` into the wrong field and load currency codes into `posted_at`. The SQL file's comment says new columns go at the end for this reason.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`, with a comment explaining the placement.
- `tests/test_csv_out.py`: a new test checks the full header order and that the currency value is written.
- `docs/finance.md`: a short note on the `currency` column.

All 7 unit tests pass. A sample export is `id,account,amount,ts,currency` followed by `E-1,4000,12.50,2026-11-01T09:00:00Z,EUR`. `reports/monthly.py` finds columns by name, so it is unaffected.

I did not change the warehouse load or the staging definition, and I could not run `warehouse-load` here. Before this ships, someone should confirm that it accepts an extra fifth field.

If finance needs currency next to amount, the loader must change too: `load_ledger.sql` would read `c5` for `posted_at`, and the comment about end-only columns would need updating. That change has to ship with the exporter in the same deploy, because both run from `/srv/ledger-export`.
