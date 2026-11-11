The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `python -m deliveries.cli DATE` prints `invalid date` to stderr and exits with status 2. Valid dates behave as before.

The change is in `deliveries/cli.py`: after `parse_date(argv[0])`, a None result prints the message to stderr and returns 2.

I checked the `parse_date` docstring ("returns None if text is not a valid date") against the code before relying on it. It holds: `parse_date` strips the text, and `read_date` returns None when no supported shape matches or the date does not exist (for example 31/02/2026). The tests in `tests/test_dates.py` and `tests/test_importer.py` pin both cases, so I left the docstring untouched.

Verification: the 5 unit tests pass. `2026-03-14` prints `2026-03-17` with exit 0. `tbc` and `31/02/2026` each print `invalid date` to stderr with exit 2.

Not changed: a run with no argument still raises IndexError on `argv[0]`. That is outside this request, so I left it as is.
