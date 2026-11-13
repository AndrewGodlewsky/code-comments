I renamed the export command's `--since` option to `--after`. Its behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date. `--since` is no longer accepted, so any caller still using it will fail. The nightly job is outside this repository, so its call must be changed to `--after` before its next run. The unit tests pass (`python -m unittest`, 3 tests).

Changes:
- `app/cli.py`: the option is now `--after`, and it passes the value through as before.
- `app/backfill.py`: the backfill calls `export` with `--after`.
- `tests/test_cli.py`: the test is renamed to `test_after_keeps_rows_changed_on_or_after_the_date` and uses `--after`.
- `README.md` and `docs/runbooks/backfill.md`: the examples use `--after`.
- `docs/cli.md`: the option table and the text now use `--after`. The sentence saying the option shares its name with the orders API filter was no longer true, so it now says the API's `since` filter has the same meaning. The API query parameter is still `since`.
- `CHANGELOG.md`: added an Unreleased entry for the rename.

Left unchanged on purpose:
- `docs/adr/0002-incremental-export.md` still says `--since`. Accepted ADRs are not edited, so a later ADR would be needed if you want the record to point at the new name.
- `docs/incidents/2026-07-14-missed-night.md` records the command as it was run on that day.
- The `since` parameter of `export_rows` in `app/export.py` is an internal Python name, so I did not rename it.

I did not commit anything.
