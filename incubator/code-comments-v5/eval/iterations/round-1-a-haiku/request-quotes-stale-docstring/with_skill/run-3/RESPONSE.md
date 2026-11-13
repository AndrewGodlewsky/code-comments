The deliveries CLI now checks the parsed date. If the date is invalid it prints "invalid date" to stderr and exits with status 2. A valid date still prints the delivery date and exits 0.

One thing you should know: parse_date does not return None for every invalid date. It returns None for text that matches no accepted format (such as "tbc"), but it raises ValueError for a well-formed date that does not exist (such as 31/02/2026). Its docstring claimed None in both cases, which was wrong. I corrected the docstring in deliveries/dates.py. I did not change the behaviour, because deliveries/importer.py relies on the ValueError to list non-existent dates as skipped rows.

Because of that, the CLI treats a ValueError from parse_date the same as None. Without this, `31/02/2026` would crash with a traceback instead of the clear message you asked for. If you only wanted the None case handled, say so and I will narrow it.

Changes:
- deliveries/cli.py: checks for None and for ValueError, prints "invalid date" to stderr, returns 2.
- deliveries/dates.py: docstring now says None means no accepted format, and ValueError means the day does not exist.
- tests/test_cli.py: new tests for a valid date, `tbc`, and `31/02/2026`.

Verification: the full test suite passes (8 tests). Manually, `tbc` and `31/02/2026` exit 2 with "invalid date" on stderr, and `14/03/2026` prints 2026-03-17 and exits 0.

Not done: I did not commit or push anything, because the instructions for this exercise say not to use git.
