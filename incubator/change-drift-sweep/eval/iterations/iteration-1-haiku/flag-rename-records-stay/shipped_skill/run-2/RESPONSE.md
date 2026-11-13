I renamed the `export` option `--since` to `--after`. Behaviour is unchanged: it still keeps rows changed on or after the date, and omitting it still writes every row.

Changes:
- `app/cli.py`: the option is now `--after`, and it passes the value to `export_rows` as before.
- `app/backfill.py`: the backfill job now calls the CLI with `--after`, so it keeps working.
- `tests/test_cli.py`: the test uses `--after` and is renamed to match. `python -m unittest` passes (3 tests).
- `docs/cli.md`: the option table and text now say `--after`. The sentence that claimed `--since` shares its name with the API filter is corrected: `--after` has the same meaning as the API's `since` filter.
- `README.md` and `docs/runbooks/backfill.md`: example commands use `--after`.
- `CHANGELOG.md`: added an Unreleased entry for the rename.

Left unchanged on purpose:
- `docs/adr/0002-incremental-export.md` still says `--since`. Accepted ADRs are not edited here, so the rename needs a new ADR that supersedes 0002 if you want the decision record to match.
- `docs/incidents/2026-07-14-missed-night.md` records a command as it was run on that day. It now fails with an argparse error, so the incident note is out of date for anyone who copies it.
- The internal `export_rows(..., since=...)` parameter keeps its name. Only the command-line spelling changed.

Anyone who still runs `--since` will get an "unrecognized arguments" error. Any scripts outside this repository that call `reportctl export --since` will need the same change.
