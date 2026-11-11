The deliveries CLI now checks the result of `parse_date`. When the argument is not a valid date, it prints `invalid date` to stderr and exits with status 2. Before this change, an invalid date reached `delivery_date(None)` and crashed with a TypeError traceback.

The change is in `deliveries/cli.py`: after `parse_date` returns, a `None` result prints the message to stderr and returns 2. I checked three cases by running the module:

- `14/03/2026` prints `2026-03-17` and exits 0.
- `2026-02-31` (a date that does not exist) prints `invalid date` and exits 2.
- `tbc` prints `invalid date` and exits 2.

The existing five unit tests still pass. I did not add a CLI test, and no comments needed changing: the module docstring and usage line remain accurate.
