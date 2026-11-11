The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and returns status 2 (`deliveries/cli.py`). A valid date still prints the delivery date and returns 0.

I also corrected the `parse_date` docstring, which said it returns None for anything that is not a valid date. That was false. It returns None only when the text matches no supported shape (such as `tbc`). A well-formed date that does not exist, such as `31/02/2026`, raises ValueError. The importer depends on that behaviour. The docstring now says so (`deliveries/dates.py`).

Tests: added a `parse_date` test for the ValueError case, and a new `tests/test_cli.py` covering the invalid-date exit path and a valid date. All 8 tests pass.

One gap to decide on: the CLI check only covers None. A mistyped impossible date such as `31/02/2026` still raises ValueError and the CLI prints a traceback instead of `invalid date`. I did not handle that because you asked for the None case only. If you want it, the CLI can also catch ValueError and treat it the same way.
