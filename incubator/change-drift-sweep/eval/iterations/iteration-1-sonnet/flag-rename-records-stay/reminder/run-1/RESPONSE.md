`reportctl export` now takes `--after` instead of `--since`. The old spelling is removed, as you said. Behaviour is unchanged: it still keeps rows changed on or after the date. The three tests pass.

Changed:
- `app/cli.py`: the option is now `--after`. It still feeds `export_rows`' `since` parameter, which I left alone because it is internal and its docstring is still accurate.
- `app/backfill.py`: the call to `main` now passes `--after`. Without this, backfill would have broken.
- `tests/test_cli.py`: the test now passes `--after`, and I renamed it to `test_after_keeps_rows_changed_on_or_after_the_date`.
- `README.md` and `docs/runbooks/backfill.md`: the example commands now use `--after`.
- `docs/cli.md`: the option table and the "Without `--after`" line are updated. The line saying `--since` shares its name with the API filter was no longer true, so it now says `--after` has the same meaning as the API's `since` filter.

Left as written:
- `CHANGELOG.md`, `docs/adr/0002-incremental-export.md` and `docs/incidents/2026-07-14-missed-night.md` still say `--since`. They record what was true when they were written. The ADR says accepted ADRs are not edited, so if you want the rename on record, it needs a new ADR that supersedes 0002.
- The orders API's `?since=` query in `docs/cli.md` is an outside fact, so it is unchanged.

Mismatches I found that the rename did not cause: none.

One thing to check: the incident note's `--since` command no longer runs. If anyone copies it from that note, it will fail.
