I renamed the `export` option `--since` to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. `--since` is no longer accepted, as you asked.

Changed:
- `app/cli.py`: the option is now `--after`, and it feeds the same `since` argument of `export_rows`. I left that internal parameter name alone.
- `app/backfill.py`: the backfill calls the CLI with `--after`. Without this, backfill would have broken.
- `tests/test_cli.py`: the test now uses `--after`, and its name now says `after`.
- `README.md`, `docs/runbooks/backfill.md`: the examples use `--after`.
- `docs/cli.md`: the option table, the "without" sentence, and the sentence that claimed the flag shares its name with the API filter. That last claim is no longer true, so it now says `--after` means the same as the API's `since` filter.
- `CHANGELOG.md`: added an Unreleased entry for the rename, marked as breaking. Existing entries are untouched.

Left as written, because they are records or outside facts:
- `docs/adr/0002-incremental-export.md` (accepted ADR, title and body still say `--since`). Its wording is now out of date for the current code. Superseding it would need a new ADR.
- `CHANGELOG.md` 1.2.0 entry (`Added --since`).
- `docs/incidents/2026-07-14-missed-night.md` (dated incident note, its manual export command uses `--since`). Running that exact command now fails.
- `docs/cli.md` line 6: the orders API's `?since=` query parameter, which is outside this repo.

No number words, unit conversions or computed figures depended on the old name.

I did not run the test suite (`python -m unittest`), so the changes are checked by reading only.
