I renamed the export command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The test suite passes (`python -m unittest`, 3 tests).

Changes:
- `app/cli.py`: the option is now `--after` (stored as `args.after`, passed to `export_rows` as `since`, so the export function is untouched).
- `app/backfill.py`: the backfill calls `export` with `--after`.
- `tests/test_cli.py`: the test uses `--after`, and its name now reads `test_after_keeps_rows_changed_on_or_after_the_date`.
- `README.md` and `docs/runbooks/backfill.md`: example commands use `--after`.
- `docs/cli.md`: the option table and the notes now show `--after`. The old note said `--since` shared its name with the orders API filter, which is no longer true, so it now says `--after` takes the same date as the API's `since` filter.

Left as written on purpose:
- `docs/cli.md` line 6 describes the orders API's own `?since=` parameter, which is an outside fact.
- `app/export.py` keeps its internal `since` parameter and docstring, since they describe the function's own argument and not the CLI.
- `CHANGELOG.md` line 11 records the historical `--since` addition.
- `docs/adr/0002-incremental-export.md` (lines 1 and 13) is an ADR that still says `--since`.
- `docs/incidents/2026-07-14-missed-night.md` line 4 is a dated report that shows the old command.

Mismatches my change did not cause: none beyond those kept deliberately. Note that the CHANGELOG has no entry for this rename. I did not add one, because the request did not ask for it; add an entry under the next release if you want the rename recorded.
