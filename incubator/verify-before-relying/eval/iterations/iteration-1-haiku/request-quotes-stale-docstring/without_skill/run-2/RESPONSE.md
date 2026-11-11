The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date can't be read.

Changed `deliveries/cli.py`: `main` treats a `None` from `parse_date` as an invalid date.

One thing I found while doing this: the `parse_date` docstring is not accurate. A well-formed but impossible date such as `31/02/2026` makes `parse_date` raise `ValueError` rather than return `None`. An uncaught exception would have given a traceback instead of the clear message, so the CLI also catches `ValueError` and treats it the same way. `tbc` and blank input still return `None` and take the same path.

I did not change the `parse_date` docstring in `deliveries/dates.py`, since that is outside the request. It should say that impossible dates raise `ValueError`.

I added `tests/test_cli.py` with three cases: a valid date prints the delivery date, `tbc` exits 2 with the message, and `31/02/2026` exits 2 with the message. All 8 tests pass.
