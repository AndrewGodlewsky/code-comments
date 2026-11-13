I renamed `reportctl export --since` to `--after`. It behaves as before and the old spelling is no longer accepted. The three tests pass.

Changed:
- `app/cli.py`: the option is now `--after`.
- `app/backfill.py`: it now calls `export` with `--after`. Without this the backfill would have failed.
- `tests/test_cli.py`: the test uses `--after` and is renamed to match.
- `README.md` and `docs/runbooks/backfill.md`: the example commands use `--after`.
- `docs/cli.md`: the options table and the "without" sentence use `--after`. I also reworded the line saying the flag shares its name with the API filter. That is no longer true, so it now says `--after` selects the same rows as the API's `since` filter and the names differ.
- `CHANGELOG.md`: added an Unreleased entry for the rename.

Left alone on purpose:
- The orders API's `?since=` query parameter is a separate interface.
- The internal `since` parameter of `export_rows`, which is not user-facing.
- The 1.2.0 changelog entry, ADR 0002 and the 2026-07-14 incident note. They record what was true at the time.

Your own jobs and scripts outside this repo that call `reportctl export --since` will need updating. I couldn't see those.
