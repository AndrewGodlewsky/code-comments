The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when `parse_date` returns None.

Before relying on the `parse_date` docstring ("returns None if text is not a valid date"), I checked it against the code and tests. It matches. Blank text, a note like "tbc", a non-matching shape, and a nonexistent date such as 31/02/2026 all give None. That is confirmed by `read_date` in `formats.py` and by `tests/test_dates.py` and `tests/test_importer.py`. No comments or docs needed correcting, and I found no conflicts with a stated requirement.

Changes:
- `deliveries/cli.py`: `main` checks for None, prints the message to stderr and returns 2. The `__main__` block passes that return value to `sys.exit`.
- `tests/test_cli.py` (new): covers a valid date, plus "tbc", blank and 31/02/2026 giving the error, nothing on stdout, and status 2.

The full test suite passes, and running `python -m deliveries.cli 31/02/2026` exits with status 2.

I did not change one related gap. Running the CLI with no argument still raises an IndexError, because `argv[0]` is read without a check. You didn't ask for that, so I left it.
