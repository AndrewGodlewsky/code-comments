The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `main` prints `invalid date` to stderr and returns status 2, so `python -m deliveries.cli tbc` exits 2 with that message. A valid date still prints the delivery date and exits 0.

Changes:
- `deliveries/cli.py`: after `parse_date(argv[0])`, a `None` result prints `invalid date` to stderr and returns 2. Before this change, a bad date crashed with a `TypeError` from `delivery_date`.
- `tests/test_cli.py` (new): one test for a valid date (prints `2026-03-17` and returns 0) and one for `tbc` (returns 2, writes `invalid date` to stderr, nothing to stdout).

Verification: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. I also ran the CLI by hand for `tbc` (message, exit 2) and `14/03/2026` (`2026-03-17`, exit 0).

Checks on existing descriptions: I compared the docstrings against the code and tests and found no conflicts, so I changed none of them.
- `parse_date`'s docstring ("None if text is not a valid date") matches `read_date`, which returns `None` for blank, note and nonexistent dates, as `tests/test_dates.py` confirms.
- `read_date`'s docstring matches its logic.
- The `read_orders` docstring, which lists blank, note and nonexistent dates as skipped, matches `tests/test_importer.py`.
- The CLI module docstring matches the usage.

Not changed, for you to decide: `main` still indexes `argv[0]` directly, so running the CLI with no arguments raises `IndexError` rather than a usage message. This is outside the request, so I left it alone.
