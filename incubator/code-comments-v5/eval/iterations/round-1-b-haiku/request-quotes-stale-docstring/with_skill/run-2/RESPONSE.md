The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date is bad.

One part of the premise was wrong. parse_date returns None only when the text matches none of the accepted shapes (for example "tbc"). When the text has an accepted shape but names no real date (for example "31/02/2026"), it raises ValueError, not None. The docstring said it returns None for anything invalid, which was false for that case. The CLI now handles both: a None result or a ValueError gives "invalid date" and exit 2. Without the ValueError handling, a date like 31/02/2026 would have produced a traceback.

Changes:
- deliveries/cli.py: main catches ValueError from parse_date, treats None the same way, and prints "invalid date" to stderr and returns 2.
- deliveries/dates.py: the parse_date docstring now says it returns None for text in none of the accepted shapes and raises ValueError for a well-formed but impossible date.
- tests/test_cli.py: new tests for a valid date (prints 2026-03-17, exit 0), "tbc" (exit 2), and "31/02/2026" (exit 2).

Checks: `python -m unittest` runs 8 tests, all passing. `python -m deliveries.cli tbc` and `python -m deliveries.cli 31/02/2026` each print "invalid date" and exit 2. `python -m deliveries.cli 14/03/2026` prints 2026-03-17 and exits 0.

The importer is unchanged. It already catches ValueError and treats None as an undated row, so its behaviour is the same.

Not done: no git commit or push, since this exercise was run without git.
