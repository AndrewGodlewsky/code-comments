I renamed the `export` option `--since` to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The old `--since` spelling is removed, as you asked.

Changes:
- `app/cli.py`: the option is now `--after`, and its value is passed through as before.
- `app/backfill.py`: the backfill now calls `export` with `--after`.
- `tests/test_cli.py`: the date-filter test uses `--after` and is renamed to match. `python -m unittest` passes (3 tests).
- `README.md`, `docs/runbooks/backfill.md`: usage examples use `--after`.
- `docs/cli.md`: the option table and notes use `--after`. The note that the option "shares its name" with the API's `since` filter is now wrong, so it now says the meaning matches.
- `CHANGELOG.md`: added an Unreleased entry for the rename.

Left unchanged on purpose:
- `docs/adr/0002-incremental-export.md` still says `--since`. It is an accepted decision record, so I did not rewrite it. If you want it to reflect the current CLI, record the rename as a new ADR that supersedes 0002.
- `docs/incidents/2026-07-14-missed-night.md` records a command that was run on 2026-07-14, so it stays as written.
- `CHANGELOG.md` keeps the 1.2.0 entry that added `--since`.

Please check one thing outside this repository: the nightly job. The ADR says it passes `--since` with the date of its last successful run. If that job calls `reportctl export --since` from its own config, it will fail after this change and needs the same rename. You said only your own jobs call reportctl, but I could not see that job from here.
