The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date is not valid.

One claim in your request was wrong. parse_date returns None for text that is not a date shape (such as "tbc" or blank), but for a date in an accepted format that names no real day (such as 31/02/2026) it raises ValueError, not None. Its docstring said it returns None in every invalid case, so I corrected the docstring to describe both behaviours. I did not change parse_date's behaviour: read_orders in deliveries/importer.py relies on the ValueError to list impossible dates as skipped lines.

Changes:
- deliveries/cli.py: main() treats both None and ValueError from parse_date as an invalid date, prints "invalid date" to stderr and returns 2. Valid dates behave as before.
- deliveries/dates.py: parse_date docstring now states the None and ValueError cases.
- tests/test_cli.py (new): covers a valid date, a non-date ("tbc") and an impossible date (31/02/2026), checking exit status and output.

All 8 tests pass (python -m unittest discover -s tests -t .). Running the CLI with 31/02/2026 prints "invalid date" and exits 2; 14/03/2026 prints 2026-03-17 and exits 0.

Not changed: running the CLI with no argument still raises IndexError on argv[0]. This is outside the request, so I left it alone.
