The `export` command's `--since` option is now `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and without it every row is written. The old `--since` spelling is removed, as you asked.

I updated the places that call or document the option:

- `app/cli.py`: the option is now `--after`, and the value is passed through unchanged.
- `app/backfill.py`: the backfill now calls `export --after`.
- `tests/test_cli.py`: the date-filter test uses `--after` and is renamed to match. All 3 tests pass (`python -m unittest`).
- `docs/cli.md`, `README.md`, `docs/runbooks/backfill.md`: examples and the option table use `--after`.
- `CHANGELOG.md`: added a line under Unreleased noting the rename and that the old spelling is gone.

I left two historical records alone. The 1.2.0 CHANGELOG entry and ADR 0002 both describe `--since` as it was when they were written. ADR 0002 still says `--since` in its title and decision text, so anyone reading it later will see the old name. If you want that ADR updated, I can add a superseding note or edit it in place.

I kept the internal parameter name `since` in `export_rows`, since it is not user-facing and renaming it would only add churn.
