The deliveries CLI now checks for a None result from parse_date. When the date is not in a supported format, it prints "invalid date" to stderr and exits with status 2. Valid dates still print the delivery date and exit 0.

Changes:
- deliveries/cli.py: after parse_date, return 2 with "invalid date" on stderr when the result is None.
- deliveries/dates.py: the parse_date docstring said None was returned for any invalid date. That was stale. An impossible date such as 31/02/2026 matches the day-first shape, so date() raises ValueError rather than returning None. The docstring now says None means no supported format matched, and that ValueError is raised for a nonexistent date.

Checked: `python -m deliveries.cli tbc` prints "invalid date" and exits 2. `python -m deliveries.cli 2026-03-14` prints 2026-03-17 and exits 0. The existing unittest suite passes (5 tests).

Gap to decide on: the CLI does not catch ValueError, so `python -m deliveries.cli 31/02/2026` still ends in a traceback rather than the "invalid date" message. Your request covered only the None case. If you want impossible dates to get the same message and exit 2, the CLI needs to catch ValueError too. I left that out because it is a behaviour change you did not ask for.
