I renamed the export command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row.

Changes:
- `app/cli.py`: the option is now `--after`, and it is passed to `export_rows` as `after`.
- `app/export.py`: the parameter is renamed from `since` to `after`, including the docstring and the filter.
- `app/backfill.py`: the backfill calls `export` with `--after`.
- `tests/test_cli.py`: the test is renamed to `test_after_keeps_rows_changed_on_or_after_the_date` and uses `--after`.
- `README.md`, `docs/cli.md` and `docs/runbooks/backfill.md`: the examples and the option table use `--after`. The `docs/cli.md` note that the option matches the API filter now says `--after` has the same meaning as the API's `since` filter.
- `CHANGELOG.md`: one line added under `[Unreleased]` saying `--since` was renamed to `--after`.

Kept as written:
- `CHANGELOG.md` 1.2.0 entry ("Added `--since` ..."): a released entry, true for its version.
- `docs/adr/0002-incremental-export.md`: a decision record. Its title and its decision text still name `--since`. The decision itself still holds, so it does not need superseding for this rename, but a reader will see the old spelling there.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record, so the command it quotes stays as it was run on that day.
- `GET /orders.csv?since=2026-05-01` in `docs/cli.md`: this is the orders API's own filter, not our flag, so it is unchanged.
- "Most rows had not changed since the night before" in the ADR: ordinary English, unrelated.

Tests: `python -m unittest` runs 3 tests, all passing. The drift script found no living prose still using `--since`.
