The deliveries CLI now handles an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and exits with status 2. A valid date still prints the delivery date and exits 0. I added `tests/test_cli.py` for the invalid case. All six tests pass.

One correction to your premise. `parse_date` returns None only when the text fits none of the accepted shapes, such as `tbc`. When the text has an accepted shape but the date does not exist, such as `31/02/2026`, it raises `ValueError` rather than returning None. The old docstring claimed None for any invalid date, which was false, so I corrected it in `deliveries/dates.py` to describe both cases.

The CLI change does not cover that second case. `31/02/2026` will still produce a traceback instead of the `invalid date` message. If you want it handled too, I can catch `ValueError` in `main` and use the same message and exit status 2. Tell me if you want that.
