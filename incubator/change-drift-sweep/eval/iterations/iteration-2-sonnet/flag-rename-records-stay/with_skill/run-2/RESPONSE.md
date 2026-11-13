I renamed `reportctl export --since` to `--after`. Behaviour is unchanged (still rows changed on or after the date) and `--since` is no longer accepted. The tests pass.

**Corrected**
- `app/cli.py`: the option and its use. `export_rows` keeps its internal `since` parameter, since it is not user-facing.
- `app/backfill.py`: the nightly backfill call now passes `--after`. This would have broken otherwise.
- `tests/test_cli.py`: the call and the test name.
- `README.md`, `docs/runbooks/backfill.md`: the example commands.
- `docs/cli.md`: the option table, the "Without ..." sentence, and the closing sentence. It said the option "shares its name" with the API filter, which is no longer true, so it now says it has the same meaning as the API's `since` filter.
- `CHANGELOG.md`: added a line under the existing `Unreleased` heading.

**Kept as written**
- `CHANGELOG.md` 1.2.0 entry ("Added `--since`"): a released record.
- `docs/adr/0002-incremental-export.md`: a decision record, true when written. It may want superseding or a note, since it names `--since`.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record of the command as run then.
- `docs/cli.md` API example `GET /orders.csv?since=2026-05-01`: the orders API's own parameter, an outside fact, unchanged.
- `Most rows had not changed since the night before` in the ADR: unrelated.

**Drift not caused by this change**: none found.
