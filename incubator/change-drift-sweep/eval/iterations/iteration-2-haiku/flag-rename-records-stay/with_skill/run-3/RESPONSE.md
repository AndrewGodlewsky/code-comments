The `export` command's `--since` option is now `--after`. Behaviour is unchanged: it keeps rows whose `changed` date is on or after the given date, and without it every row is written. `--since` is removed, not kept as an alias, as you asked.

Changes:
- `app/cli.py`: the option is defined as `--after` and read from `args.after`. The `export_rows` keyword stays `since`, since it is an internal name.
- `app/backfill.py`: the backfill loop now calls the export with `--after`. Without this, backfill would have broken.
- `tests/test_cli.py`: the test now passes `--after`, and it is renamed to `test_after_keeps_rows_changed_on_or_after_the_date`.
- `README.md` and `docs/runbooks/backfill.md`: examples use `--after`.
- `docs/cli.md`: the option table, the "without" sentence, and the note that the option matches the API filter now refer to `--after`. The note says `--after` has the same meaning as the API's `since` query parameter, which is unchanged.
- `CHANGELOG.md`: one line under `[Unreleased]` records the rename and that `--since` is removed.

Checks: `python -m unittest` runs 3 tests, all passing. Parsing `export x.csv --after 2026-05-01` gives `after='2026-05-01'`.

Kept as written:
- `CHANGELOG.md` 1.2.0 entry (released 2026-06-03): it is a record of that release.
- `docs/incidents/2026-07-14-missed-night.md`: it records the command run on 14 July.
- `docs/adr/0002-incremental-export.md`: an accepted ADR that says `--since DATE`. The ADR README says accepted ADRs are not edited, so it is unchanged. The rename probably needs a new ADR that supersedes 0002. I did not write one.
- The `since=` query parameter in `docs/cli.md` and the orders API: this is an outside fact about the API, not our flag.

Anyone who has a script or a copied command using `--since` will now get an argument error. The changelog line says so, but a release note alone may not reach them.
