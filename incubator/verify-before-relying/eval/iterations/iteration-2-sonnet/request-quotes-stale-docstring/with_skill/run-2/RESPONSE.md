The premise is off: parse_date's docstring (deliveries/dates.py) says it returns None for anything that isn't a valid date, but that only holds for text in no accepted format ("tbc", blank, "abc"). A well-formed date that doesn't exist, such as 31/02/2026 or 2026-13-45, makes read_date raise ValueError (from date()), and test_importer.py pins this (read_orders catches it). So a CLI that only checked for None would have crashed with a traceback on exactly the typo you care about.

What I did:
- deliveries/cli.py: main now treats both None and ValueError as invalid: prints "invalid date" to stderr and returns 2 (exit status 2 via sys.exit). Verified by running `python -m deliveries.cli 31/02/2026` and `xx`: both print "invalid date", exit 2.
- Corrected the docstrings to match the code, in place: parse_date (deliveries/dates.py) and read_date (deliveries/formats.py) now say None means no accepted format and ValueError means the date doesn't exist. The code itself is unchanged.
- Added tests/test_cli.py covering both cases. The full suite passes.

Not changed: the importer, which already handles both cases correctly.
