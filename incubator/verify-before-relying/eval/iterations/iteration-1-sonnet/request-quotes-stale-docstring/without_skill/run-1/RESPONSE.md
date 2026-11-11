The deliveries CLI now prints "invalid date" to stderr and exits with status 2 for a bad date.

One thing differed from the request. `parse_date` only returns None for text that isn't written like a date, such as "tbc" or a blank. A date that is well-formed but doesn't exist, such as 31/02/2026 or 2026-13-45, raises ValueError instead. `importer.py` already relies on that. Checking only for None would still have crashed with a traceback on those typos. The CLI therefore treats both cases as invalid.

Changes:
- `deliveries/cli.py` catches ValueError, checks for None, prints "invalid date" to stderr and returns 2.
- `deliveries/dates.py`: I corrected the `parse_date` docstring, which said None covers every invalid date. It now mentions the ValueError case.

I ran the CLI by hand. "tbc" and 31/02/2026 both print "invalid date" and exit 2, and 2026-03-14 still prints the delivery date and exits 0. The existing tests pass. I didn't add a CLI test.
