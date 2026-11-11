The nightly CSV now has a `currency` column directly after `amount`:

`id, account, amount, currency, ts`

The change is one line in `exporter/csv_out.py` (`COLUMNS`). The values come from `Entry.currency`, which `exporter/rows.py` already populates.

One constraint needed handling. `deploy/warehouse/load_ledger.sql` stages each file by position (`c1`..`c4`) and its comment says new columns must go at the end. Inserting `currency` before `ts` moved `ts` from `c4` to `c5`, so the load would have written currency into `posted_at`. I updated the mapping to `SELECT c1, c2, c3, c5`. Currency is not loaded, because `ledger_raw` has no currency column, and I left `schema.sql` and `ledger_raw` unchanged. I also rewrote the comment to describe the new positions.

Other references I checked, and left as they are:
- `reports/monthly.py` and its test read columns by header name, so they are unaffected.
- `exporter/cli.py` and `deploy/crontab` do not name columns.
- `docs/finance.md` and `README.md` say finance finds columns by header name, which still holds. Nothing in them lists the columns.
- `tests/test_csv_out.py` now also checks that `currency` sits right after `amount`, and that it holds the entry's currency.

Tests: the unit suite passes (7 tests, `python -m unittest discover -s tests -t .`). I did not run the SQL against a warehouse.

Deployment risk: the export and the load must change together. A CSV written by the old exporter has only four fields, so loading it with the new SQL sets `posted_at` to NULL, which violates the NOT NULL constraint. The cron runs export at 01:00 and load at 01:30, so a normal night is safe. Re-running the load against an older file, or deploying the export without the SQL change, would fail or load wrong values.

If you would rather not touch the warehouse mapping, the alternative is to append `currency` at the end of `COLUMNS`. That needs no SQL change, but it does not place the column next to `amount`.
