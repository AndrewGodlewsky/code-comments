I renamed the `export` option `--since` to `--after` in `app/cli.py`. The behavior is unchanged: it still keeps rows whose `changed` date is on or after the given date. The backfill code in `app/backfill.py` now passes `--after`, so it keeps working. The unit tests pass (`python -m unittest`, 3 tests).

Updated to the new name:
- `README.md` usage example
- `docs/cli.md` option table, the "without the option" sentence, and the note on sharing a name with the API filter (the API's `since=` query parameter is unchanged, so the note now says the option shares its meaning with it)
- `docs/runbooks/backfill.md` single-day command
- `tests/test_cli.py` test name and argument
- `CHANGELOG.md`: added a line under `[Unreleased]`. The released 1.2.0 entry is unchanged.

Kept as they are, because they are records of past decisions or events:
- `CHANGELOG.md` 1.2.0 entry ("Added `--since` ...") is a released entry.
- `docs/incidents/2026-07-14-missed-night.md` records the exact command run on 14 July 2026.
- `docs/adr/0002-incremental-export.md` (accepted, dated 2026-05-28) still says `--since DATE` in its title and decision. The rename contradicts that text, so the ADR may need superseding by a new ADR. I did not edit it, because accepted ADRs are not edited.

Not changed: the orders API's `?since=` query parameter in `docs/cli.md`, which is an outside fact.

Not run: `/code-comments:stale-refs`, because it is not installed in this environment.
