I renamed `export --since` to `--after`, with no alias for the old spelling. Behaviour is unchanged: the filter still keeps rows changed on or after the date. The three tests pass.

**Corrected**
- `app/cli.py`: the option is now `--after`, and it feeds the existing `since` parameter of `export_rows`. I left that internal parameter and its docstring alone, because they are still accurate.
- `app/backfill.py`: the call to `export` now passes `--after`.
- `tests/test_cli.py`: the test passes `--after` and is renamed `test_after_keeps_rows_...`.
- `README.md`: the usage example uses `--after`.
- `docs/cli.md`: the option table row, the "Without `--after`" sentence, and the last sentence. That sentence said the flag "shares its name" with the API filter, which is no longer true. It now says `--after` has the same meaning as the API's `since` filter and the two are named differently.
- `docs/runbooks/backfill.md`: the example command uses `--after`.
- `CHANGELOG.md`: I added a line under the existing Unreleased heading saying `--since` was renamed to `--after` and is no longer accepted.

**Kept as written**
- `CHANGELOG.md` 1.2.0 entry "Added `--since`...": a released entry, true for its version.
- `docs/adr/0002-incremental-export.md`: an ADR that records the decision under the old name. It may need superseding or a note that the flag is now `--after`.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record with the command as it was run.
- The API's `GET /orders.csv?since=...` in `docs/cli.md`: the orders API's own parameter, which this change doesn't touch. It is now the one place that still says `since`.
- "since the night before" in the ADR: unrelated wording.

No instruction files were touched. No other drift turned up that predates this change.
