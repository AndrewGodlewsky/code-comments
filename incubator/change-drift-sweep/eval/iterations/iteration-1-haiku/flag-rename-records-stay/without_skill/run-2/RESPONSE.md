I renamed the `export` command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row.

Changes:
- `app/cli.py`: the option is now `--after`, and it passes the value through as before.
- `app/backfill.py`: the backfill now calls `export` with `--after`.
- `tests/test_cli.py`: the date-filter test uses `--after` and is renamed to match. `python -m unittest` passes (3 tests).
- `README.md`, `docs/runbooks/backfill.md`: the examples use `--after`.
- `docs/cli.md`: the option table and the note about the API filter now say `--after` has the same meaning as the API's `since` parameter. The old note claimed the two shared a name, which is no longer true.
- `CHANGELOG.md`: an Unreleased entry records the rename and that `--since` is removed with no alias.

`--since` is now rejected with an argparse error. I checked this directly. Only our own jobs call `reportctl`, so no alias was added.

Left unchanged on purpose:
- `docs/adr/0002-incremental-export.md` still says `--since`. Accepted ADRs are not edited under `docs/adr/README.md`, so a superseding ADR would be needed if we want the decision record to reflect the new name. I did not write one.
- `docs/incidents/2026-07-14-missed-night.md` and the 1.2.0 CHANGELOG entry describe past events and keep the old spelling.

Anything outside the repo that calls `reportctl export --since` (cron files, the nightly job config, scripts on other machines) will break on its next run. You said only our own jobs call it, but those jobs should be checked for the old flag before this ships.
