The CSV export now has a `currency` column directly after `amount`:

`id, account, amount, currency, ts`

The change is in `exporter/csv_out.py` (`COLUMNS`). I added two tests to `tests/test_csv_out.py`: one checks that `currency` sits right after `amount`, and one checks that it is written as given. All 8 tests pass.

One constraint shaped the change. `deploy/warehouse/load_ledger.sql` loads the CSV by position (`SELECT c1, c2, c3, c4`), and its comment said new columns must go at the end. Putting currency beside amount moves `ts` from position 4 to position 5, so the load would have written timestamps into `posted_at` from the wrong field. I changed the select to `c1, c2, c3, c5` in the same change, and rewrote the comment, which said new columns go at the end and was no longer true.

Points to know before deploying:

- The warehouse table (`ledger_raw`) has no currency column, so the load skips currency. If finance needs it in the warehouse, that is a separate change: add a column to the table at the end, then select it.
- Deploy the exporter and the load SQL together. The export runs at 01:00 and the load at 01:30 (`deploy/crontab`). If only the exporter ships, tonight's load will mis-map the fields.
- `reports/monthly.py` and `docs/finance.md` find columns by header name, so they are unaffected.
- `deploy/crontab` is unchanged.
