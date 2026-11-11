I renamed `reportctl export --since` to `--after`. The old spelling is gone, as you said. Behaviour is unchanged: the same date comparison runs, and the 3 tests pass.

**Changed**
- `app/cli.py`: the option is now `--after` and the parsed value is read from `args.after`.
- `app/backfill.py`: the internal `export` call passes `--after`.
- `tests/test_cli.py`: the test calls `--after`, and I renamed it to `test_after_keeps_rows_changed_on_or_after_the_date`.
- `docs/cli.md`: the option table row and the "Without `--after`" sentence now use the new name. I reworded the closing sentence, which said the flag "shares its name" with the API filter. That is no longer true, so it now says `--after` "has the same meaning as the API's `since` filter".
- `README.md` and `docs/runbooks/backfill.md`: the example commands use `--after`.

**Kept as written**
- `CHANGELOG.md`, the 1.2.0 entry "Added `--since`": a released record. I did not add a changelog line, because the existing Unreleased section only lists a different change. You may want one there noting the rename.
- `docs/adr/0002-incremental-export.md`: an ADR, true as of its date. It still names `--since`, so it may need superseding or a note.
- `docs/incidents/2026-07-14-missed-night.md`: a dated incident record. Its `--since` command is what was run then, so it is unchanged.
- The orders API's `?since=` filter in `docs/cli.md` is an outside fact and stays `since`. The CLI option and the API filter now have different names.

**Left alone**
- The Python parameter `since` in `export_rows` (`app/export.py`) and its docstring. It is not user-facing and is still accurate. I can rename it to `after` too if you want it to match.

Nothing else was already out of date. A search for `--since` shows hits only in the three records above. No relative links changed.
