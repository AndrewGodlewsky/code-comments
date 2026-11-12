I changed the deliveries CLI so that an invalid date gets a clear error.

In `deliveries/cli.py`, `main` now checks the result of `parse_date`. When it is `None`, the CLI prints `invalid date` to stderr and returns status 2 (the entry point passes that to `sys.exit`). Valid dates behave as before.

Checks:
- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits with 2.
- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits with 0.
- `python -m unittest discover -s tests -t .` runs 5 tests, all passing.

Your claim that `parse_date` returns `None` for invalid input holds: it returns `None` for blank text, notes such as "tbc", and dates that do not exist. I did not change any comments, since the existing docstrings remain accurate.
