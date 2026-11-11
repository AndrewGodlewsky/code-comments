The deliveries CLI now exits with status 2 and prints "invalid date" to stderr when the date can't be read. Valid dates still print the delivery date and exit 0.

I checked parse_date's docstring against the code before relying on it. It said parse_date returns None for an invalid date, which is only half true:

- Text that matches no accepted format (for example "tbc" or blank) returns None.
- Text that matches a format but names a date that doesn't exist (for example 31/02/2026) raises ValueError, because the date constructor rejects it. importer.read_orders depends on that ValueError to list such rows as skipped, and test_importer covers it.

I corrected the docstring in deliveries/dates.py to describe both cases. I did not change parse_date's behaviour.

Changes:
- deliveries/cli.py: parse_date is called inside a try. A ValueError or a None result prints "invalid date" to stderr and returns 2. The ValueError case goes beyond what you asked: without it, a day like 31/02/2026 would crash with a traceback instead of the clear message, and that is the typo case you described.
- deliveries/dates.py: docstring corrected as above.
- tests/test_cli.py (new): valid date prints 2026-03-17 and exits 0; "tbc" and 31/02/2026 each exit 2 with "invalid date" on stderr.
- tests/test_dates.py: added a test that 31/02/2026 raises ValueError.

Results: `python -m unittest discover -s tests -t .` runs 9 tests, all passing. I also ran the CLI by hand: `tbc` and `31/02/2026` exit 2 with "invalid date", and `14/03/2026` prints 2026-03-17.

Not changed: running the CLI with no argument still raises IndexError. That was outside the request.
