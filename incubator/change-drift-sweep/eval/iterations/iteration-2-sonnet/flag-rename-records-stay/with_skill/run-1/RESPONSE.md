I renamed the export command's `--since` option to `--after`, and the three unit tests pass. Behaviour is unchanged: the same rows are selected and the old spelling is removed outright, with no alias. `export_rows` keeps its internal `since` parameter, since it is not user-facing and its docstring is still true.

**Corrected, by file**
- `app/cli.py`: the option is now `--after`, and the parser passes `args.after` to `export_rows`.
- `app/backfill.py`: it calls `export` with `--after`. Without this, backfills would have broken.
- `tests/test_cli.py`: the test renamed to `test_after_...` and now passes `--after`.
- `README.md`: the usage example uses `--after`.
- `docs/cli.md`: the options table and the "Without ..." sentence use `--after`. I also reworded the last line, which said the flag "shares its name" with the API filter. That is no longer true, so it now says `--after` has the same meaning as the API's `since` filter.
- `docs/runbooks/backfill.md`: the example command uses `--after`.
- `CHANGELOG.md`: I added a line under the existing `Unreleased` heading, noting the rename and that `--since` is no longer accepted.

**Kept word for word**
- `CHANGELOG.md` 1.2.0 entry ("Added `--since`"): a released record.
- `docs/adr/0002-incremental-export.md`: an ADR, true when written. It may need superseding, since the CLI no longer takes `--since`.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record. The `--since` command was correct on that date.
- `docs/cli.md` line 6, `GET /orders.csv?since=2026-05-01`: the orders API's own parameter, an outside fact that this change does not touch.
- The "since the night before" wording in the ADR is unrelated.

I made no changes to instruction files, and found no drift that predates this change.
