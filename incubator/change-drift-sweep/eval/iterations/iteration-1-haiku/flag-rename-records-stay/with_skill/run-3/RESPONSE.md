I renamed the `export` option `--since` to `--after`. Its behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The old spelling is removed, as you asked.

Changes:
- `app/cli.py`: the option is now `--after`, and the parsed value is read from `args.after`.
- `app/backfill.py`: the backfill now calls `export` with `--after`.
- `tests/test_cli.py`: the test uses `--after`, and its name now starts with `test_after_`. `python -m unittest` passes (3 tests).
- `README.md`, `docs/runbooks/backfill.md`: examples use `--after`.
- `docs/cli.md`: the option table and the notes now say `--after`. The sentence that claimed the flag shares its name with the API's `since` filter was no longer true, so it now says `--after` has the same meaning as that filter.
- `CHANGELOG.md`: added a line under `Unreleased` recording the rename and that the old spelling is removed.

Kept as written:
- `CHANGELOG.md` 1.2.0 entry: a released record that says `--since`.
- `docs/adr/0002-incremental-export.md`: a dated decision record that names `--since` in its title and Decision section. The rename does not contradict its substance, but it now names a flag that no longer exists. It may need a short superseding note or a new ADR if you want the decision record to match the current spelling.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record of a command run that day.
- `docs/cli.md` line 6: `GET /orders.csv?since=` is the orders API's own filter, an outside fact, so it is unchanged.

Not changed: the `since=` keyword argument and the `since` parameter of `export_rows` in `app/export.py`. They are internal names, not the flag, so the behaviour and the Python call sites are unaffected.

The drift sweep (`value_drift.py --old=--since --strings`) now finds only the kept records and the new changelog line that names the old flag.
