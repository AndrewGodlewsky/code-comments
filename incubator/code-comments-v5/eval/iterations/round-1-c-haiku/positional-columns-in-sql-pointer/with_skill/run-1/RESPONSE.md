Done. The CSV export now has a `currency` column right after `amount`:

    id, account, amount, currency, ts

Changes:

- `exporter/csv_out.py`: `COLUMNS` now includes `currency` between `amount` and `ts`. The `Entry` already carried `currency`, so no other code changed.
- `deploy/warehouse/load_ledger.sql`: this loader reads the export by position, not by header name. With the new order, `ts` moves from c4 to c5, so the insert would have put timestamps into the wrong column. The select now reads `c1, c2, c3, c5` and skips `currency` (c4), because `ledger_raw` has no currency column. I also rewrote the comment above it: the old text said new columns must go at the end, which no longer describes the mapping.
- `tests/test_csv_out.py`: added `test_currency_sits_beside_amount`, which checks that the header places `currency` directly after `amount` and that the row holds `EUR`.

The unit tests pass (7 of 7). I could not run `warehouse-load` against a real staging table, so the load change is verified by reading the SQL only.

Please check two things:

1. The warehouse owners wrote "new export columns go at the end" as a rule. This change breaks that rule on purpose, so the loader mapping had to change with it. Confirm that is acceptable before this ships. If you would rather keep the old loader mapping untouched, the alternative is to put `currency` at the end of the export instead.
2. Currency is exported but not loaded into the warehouse. If finance needs it there, `ledger_raw` needs a new column added at the end, and the loader select must map it.
