The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date can't be read.

Before relying on the docstring, I checked it against the code and tests. It was wrong. `parse_date` returns None only when the text matches none of the accepted formats (for example "tbc" or a blank cell). When the text has an accepted shape but names a date that doesn't exist, such as 31/02/2026, `parse_date` raises ValueError. The importer already relies on that ValueError, and the test for it passes. The docstring said None for every invalid date, so I corrected it in `deliveries/dates.py`. It now says None for an unrecognised format and ValueError for a nonexistent date.

Changes:
- `deliveries/cli.py`: `main` handles both cases. A None result, or a ValueError from `parse_date`, prints "invalid date" to stderr and returns 2. Valid dates behave as before.
- `deliveries/dates.py`: docstring corrected as described above.
- `tests/test_dates.py`: added a test that 31/02/2026 raises ValueError.
- `tests/test_cli.py` (new): covers a valid date (prints 2026-03-17, status 0), "tbc" (status 2), and 31/02/2026 (status 2).

Conflict to decide on: you asked for the CLI to react to None only. I also handled ValueError, because without that a mistyped date like 31/02/2026 would crash with a traceback rather than the clear message you wanted. If you want the ValueError case left as a traceback, remove the `except` branch in `main`.

Not changed: running the CLI with no argument still raises IndexError. That is outside this request.

Verification: `python -m unittest discover -s tests -t .` runs 9 tests, all passing. Manually, `python -m deliveries.cli tbc` and `python -m deliveries.cli 31/02/2026` each print "invalid date" and exit 2, and `python -m deliveries.cli 14/03/2026` prints 2026-03-17 and exits 0.
