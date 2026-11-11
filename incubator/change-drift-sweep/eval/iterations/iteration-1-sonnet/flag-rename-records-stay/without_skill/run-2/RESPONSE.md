I renamed the export command's `--since` option to `--after`. It behaves as before, and the old spelling is removed, as you said.

Changed:
- `app/cli.py`: the option is now `--after`.
- `app/backfill.py`: the backfill helper calls `export` with `--after`. It would have failed on the old spelling.
- `tests/test_cli.py`: the test uses `--after`. The test suite passes.
- `README.md`, `docs/cli.md`, `docs/runbooks/backfill.md`: the examples and option table use `--after`.
- `CHANGELOG.md`: added an Unreleased entry saying the option was renamed and `--since` is no longer accepted.

Notes:
- In `docs/cli.md` I reworded the sentence saying the option shares its name with the orders API filter. The API's `since` query parameter is unchanged, so the doc now says `--after` has the same meaning as that filter.
- I left `export_rows(since=...)` as it is, because it is an internal parameter and not the command line.
- I did not edit the historical records, the ADR `docs/adr/0002-incremental-export.md` and the incident note `docs/incidents/2026-07-14-missed-night.md`. They describe what was true when they were written. The 1.2.0 changelog entry is left alone for the same reason. The ADR may deserve a short "superseded by the rename" note if you want one.
- Any job outside this repo that still passes `--since` will now fail. You said only your own jobs call reportctl, but check that their scheduler configs are updated.
