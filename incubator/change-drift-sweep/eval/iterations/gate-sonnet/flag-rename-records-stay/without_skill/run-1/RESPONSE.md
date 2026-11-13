I renamed the export command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows changed on or after the date. `--since` is no longer accepted, as you asked.

Changed:
- `app/cli.py`: the option is now `--after`.
- `app/backfill.py`: the backfill job now calls `export` with `--after`. This is one of our own jobs, so it would have broken otherwise.
- `docs/cli.md`, `README.md` and `docs/runbooks/backfill.md`: the examples and option table use `--after`.
- `tests/test_cli.py`: the test passes `--after` and is renamed to match.
- `CHANGELOG.md`: a new entry under Unreleased notes the rename.

Left alone on purpose:
- The internal `since` parameter of `export_rows` is not user-facing, so I kept it.
- The 1.2.0 changelog line and ADR 0002 still say `--since`. They record what was true when they were written, and the ADR README says accepted ADRs are not edited. If you want the decision recorded, a new ADR superseding 0002 would be the way.

I ran the tests and they pass. Any cron jobs or scripts outside this repository that still pass `--since` will now fail, so check those.
