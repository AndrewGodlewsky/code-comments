I renamed the export command's `--since` option to `--after`. Its behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The old spelling is removed, as you asked.

Changes:
- `app/cli.py`: the option is now `--after`, and it still feeds the same filter.
- `app/backfill.py`: the backfill job now calls `--after`. Without this change the nightly backfill would break.
- `tests/test_cli.py`: the test now uses `--after`, and its name matches. All 3 tests pass with `python -m unittest`.
- `README.md`, `docs/cli.md`, `docs/runbooks/backfill.md`: examples and the option table now use `--after`. In `docs/cli.md` I reworded the note that tied the option to the API filter: the API's `since` query parameter keeps its name, and `--after` selects the same rows as it.
- `CHANGELOG.md`: added an Unreleased entry noting the rename and that the old spelling is gone.
- `docs/adr/0002-incremental-export.md`: added a one-line note that the option is now `--after`. The rest of the ADR is a historical record, so I left its text as it was.

Left as-is on purpose:
- `docs/incidents/2026-07-14-missed-night.md` records the command that was actually run that day.
- The 1.2.0 changelog entry describes the release as it shipped.

Before this goes out, check that nothing outside this repo still passes `--since` to `reportctl`. You said only your own jobs call it, and I found no other callers in the repo, but I could not check the jobs themselves from here.
