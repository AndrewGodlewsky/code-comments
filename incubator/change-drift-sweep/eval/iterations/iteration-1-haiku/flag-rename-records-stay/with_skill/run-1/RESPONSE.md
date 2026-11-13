I renamed the `export` command's `--since` option to `--after`. Its behaviour is unchanged, and the old spelling is removed, not aliased.

Changes:
- `app/cli.py`: the argparse option is now `--after`, and it still feeds the same filter.
- `app/backfill.py`: the call that runs the export for each missed day now passes `--after`.
- `tests/test_cli.py`: the test is renamed to `test_after_keeps_rows_changed_on_or_after_the_date` and uses `--after`. `python -m unittest` passes (3 tests).
- `README.md` and `docs/runbooks/backfill.md`: the example commands use `--after`.
- `docs/cli.md`: the option table, the default-behaviour sentence, and the note on the API filter now use `--after`. The note now says `--after` has the same meaning as the API's `since` filter.
- `CHANGELOG.md`: one line under `[Unreleased]` records the rename.

Kept as written:
- `CHANGELOG.md` 1.2.0 entry: a released entry, true for its date.
- `docs/adr/0002-incremental-export.md`: an accepted ADR, which the ADR README says is not edited. It still says `--since`. If you want the record to match the new name, a later ADR should supersede it.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident note. Its manual export command uses `--since` and will now fail if copied as written.
- The API's `GET /orders.csv?since=` query parameter in `docs/cli.md`: an outside fact about the orders API, so it is unchanged.

Action needed outside this repo: the nightly job and any other caller that passes `--since` to `reportctl export` must switch to `--after`, or it will fail with an unrecognised-argument error. I could not check the job's code from here.
