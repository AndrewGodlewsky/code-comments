I renamed the `export` command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The unit tests pass (3 of 3).

Changes made:
- `app/cli.py`: the option is now `--after DATE`, and it is passed through to `export_rows` as before. I left the internal `since` parameter of `export_rows` alone because it is not part of the CLI.
- `app/backfill.py`: the `backfill` helper called `main` with `--since`, so it now uses `--after`. Without this change the backfill would have failed.
- `tests/test_cli.py`: the option is now `--after`, and the test name matches.
- `README.md`, `docs/runbooks/backfill.md`: usage examples now use `--after`.
- `docs/cli.md`: the option table, the "without" sentence, and the sentence about matching the API filter now use `--after`. That last sentence said the option "shares its name" with the API filter, which is no longer true. It now says `--after` has the same meaning as the API's `since` filter. The API's own `?since=` parameter is unchanged.

Left unchanged on purpose:
- `CHANGELOG.md`: the 1.2.0 entry ("Added `--since`") is history. The `[Unreleased]` section does not yet record this rename. Since it breaks anyone using `--since`, it probably needs an entry, but I did not add one.
- `docs/adr/0002-incremental-export.md`: this is an accepted ADR that names `--since`. It is now out of date. Per `docs/adr/README.md`, a change like this needs a new superseding ADR rather than an edit, so I did not edit it.
- `docs/incidents/2026-07-14-missed-night.md`: this is a dated incident report. Its command uses `--since`, and that command no longer works. I left it as written.

Mismatches my change did not cause: none found. The comments and docstrings in `app/export.py` and `app/backfill.py` describe the current behaviour correctly.
