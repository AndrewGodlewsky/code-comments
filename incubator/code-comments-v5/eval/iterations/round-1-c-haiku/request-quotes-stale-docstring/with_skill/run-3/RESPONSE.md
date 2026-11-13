The deliveries CLI now checks the date it is given. When `parse_date` returns None, it prints `invalid date` to stderr and exits with status 2. A valid date still prints the delivery date and exits 0.

One part of the request rested on a false premise. `parse_date` returns None only when the text matches no date format, such as `tbc`. A well-formed date that does not exist, such as `31/02/2026`, makes it raise ValueError instead of returning None. The old `parse_date` docstring said it returns None for any invalid date, which was wrong. I corrected the docstring to describe both cases.

Because of that, the CLI also treats a ValueError from `parse_date` as an invalid date and prints the same message with status 2. Without this, `31/02/2026` would have produced a traceback rather than the clear error the request asked for. This goes slightly beyond the literal request, so say if you would rather keep only the None case.

Changes, all in `C:/Users/godle/AppData/Local/Temp/code-comments-planning-research/repo/incubator/code-comments-v5/eval/iterations/round-1-c-haiku/request-quotes-stale-docstring/with_skill/run-3/outputs`:
- `deliveries/cli.py`: handles None and ValueError from `parse_date`, with a comment on why ValueError is possible.
- `deliveries/dates.py`: `parse_date` docstring now states the None case and the ValueError case.
- `tests/test_cli.py`: new tests for a valid date, a non-date, and a nonexistent date.

Verification: all 8 tests pass (`python -m unittest discover -s tests -t .`). Manual runs gave `invalid date` with status 2 for `tbc` and `31/02/2026`, and `2026-03-17` with status 0 for `14/03/2026`.

Not changed: `deliveries/importer.py` already catches ValueError from `parse_date` and its docstring matches the behaviour. The `read_date` docstring in `deliveries/formats.py` is accurate as written. The CLI still fails with an IndexError when no argument is given; that is outside this request and I left it alone.

No git operations were run, so nothing is committed.
