I renamed `export`'s `--since` option to `--after`. Behaviour is unchanged, and the three tests in `python -m unittest` pass. The old spelling is gone, as you said it could be.

**Code**
- `app/cli.py`: the option is now `--after`.
- `app/export.py`: I also renamed the `since` parameter and its docstring to `after`, so the code reads consistently.
- `app/backfill.py`: the call to `export` uses `--after`.
- `tests/test_cli.py`: the test passes `--after`, and I renamed it to `test_after_keeps_rows_changed_on_or_after_the_date`.

**Docs that describe the current code, updated**
- `README.md`: the usage example uses `--after`.
- `docs/cli.md`: the options table and the "Without `--after`" line are updated.
- `docs/runbooks/backfill.md`: the single-day command uses `--after`.
- `docs/cli.md` had one sentence that was no longer true. It said the option "shares its name and meaning with the API's filter". I rewrote it to say the meaning is the same but the names now differ: the API still calls its filter `since`.

**Left word for word**
- `docs/adr/0002-incremental-export.md` still says `--since`, as a historical decision record.
- `docs/incidents/2026-07-14-missed-night.md` still says `--since`, as a dated report of what was run then.
- The 1.2.0 entry in `CHANGELOG.md` still says "Added `--since`".
- The orders API's `GET /orders.csv?since=...` in `docs/cli.md` is an outside fact, so it stays.

I added one entry under Unreleased in `CHANGELOG.md` noting the rename and that `--since` is no longer accepted.

I found no other mismatches that my change did not cause.
