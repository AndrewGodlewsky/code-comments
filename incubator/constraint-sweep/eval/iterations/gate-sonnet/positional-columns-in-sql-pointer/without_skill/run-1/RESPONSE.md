I added `currency` to the CSV export, but as the last column (after `ts`), not directly next to `amount`.

Why: `warehouse/load.sql` reads the CSV fields by position (`c1`..`c4`), and its comment says new export columns must go at the end. If `currency` sat right after `amount`, `ts` would shift to the fifth field and the warehouse would load the wrong values into `posted_at`. Finance finds columns by header name (`docs/finance.md`), so they should still see `currency` easily. It just won't be adjacent to `amount`.

Changes:
- `exporter/csv_out.py`: `COLUMNS` is now `["id", "account", "amount", "ts", "currency"]`.
- `tests/test_csv_out.py`: header check includes `currency`; added tests that the value is written and that the first four columns keep their positions. All tests pass.

Not changed: the warehouse side. `load.sql` still loads only the first four fields, so currency is not yet in `ledger_raw`. If the warehouse should have it too, that needs an `ALTER TABLE ... ADD COLUMN` and an update to `load.sql`. Please also confirm the loader tolerates a fifth field in staging.

If finance truly needs `currency` physically beside `amount`, the warehouse load would have to change in the same release. Let me know and I can do that.
