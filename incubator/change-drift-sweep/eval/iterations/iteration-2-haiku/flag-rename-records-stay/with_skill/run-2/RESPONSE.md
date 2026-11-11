I renamed the `export` command's `--since` option to `--after`. Its behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given day.

Changed:
- `app/cli.py`: the option is now `--after`, and it still feeds the same filter.
- `app/backfill.py`: the backfill now calls `export` with `--after`. Without this, backfill would have broken.
- `tests/test_cli.py`: the option is now `--after`, and the test name matches.
- `docs/cli.md`: the option table and text now use `--after`. The sentence saying the option shares its name with the orders API filter was no longer true, so it now says `--after` has the same meaning as the API's `since` filter.
- `docs/runbooks/backfill.md` and `README.md`: example commands now use `--after`.
- `CHANGELOG.md`: added a line under Unreleased saying `--since` was renamed to `--after` and that callers must change.

Left as written:
- `CHANGELOG.md` 1.2.0 entry: a released record.
- `docs/adr/0002-incremental-export.md`: an accepted, dated decision record that still says the command takes `--since`. The rename contradicts it, so it may need a new ADR that supersedes it. I did not edit it.
- `docs/incidents/2026-07-14-missed-night.md`: a past incident record. Its command with `--since` will now fail if rerun as written.
- `docs/cli.md`: the orders API's `GET /orders.csv?since=` query parameter, which is an outside fact and is unchanged.

Verification: `python -m unittest` passes all 3 tests. The drift sweep for `--since` now finds only the records listed above and the changelog line that names the old flag on purpose.

Action needed: the nightly job and any other caller of `reportctl export --since` live outside this repository, so I could not check or update them. They must switch to `--after`, or they will fail.
