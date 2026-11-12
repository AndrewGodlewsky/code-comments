The CSV export now has a `currency` column directly after `amount`. The header is `id,account,amount,currency,ts`, and each row carries the ISO 4217 code from the entry (for example `EUR`).

One thing you need to know: the warehouse load reads this file by position, not by header name. `deploy/warehouse/load_ledger.sql` stages the fields as c1..c4 and loads c4 as `posted_at`. With `currency` placed before `ts`, `ts` moves to position c5, so the load would have written currency into `posted_at` without an error. I changed the load to match:

- `deploy/warehouse/load_ledger.sql` now selects `c1, c2, c3, c5`. Position c4 (currency) is skipped, because `ledger_raw` has no currency column. The `ledger_raw` table and `schema.sql` are unchanged.
- The comment in that file now says the staged fields follow `COLUMNS` in `exporter/csv_out.py`, and that any new export column must be mapped in that SELECT. The old comment said new columns must go at the end, which is no longer true.
- `exporter/csv_out.py` has a comment at `COLUMNS` pointing to that load file.

Decision for you: currency is exported but not loaded into the warehouse. If finance needs it in `ledger_raw`, that is a schema change (`ALTER TABLE ledger_raw ADD COLUMN currency`, added at the end as the schema file requires) plus a SELECT change. I did not make it, because it changes the production table.

Tests: `tests/test_csv_out.py` now checks that `currency` is in the header, sits immediately after `amount`, and holds `EUR` for the sample entry. All 7 tests pass (`python -m unittest discover -s tests -t .`). I also ran the CLI on a sample record and the output matched the header above. I did not run `warehouse-load` against a real staging table, so the new SELECT is verified only by reading it against the column order.

`reports/monthly.py` reads columns by name, so it is unaffected. `docs/finance.md` is unchanged.
