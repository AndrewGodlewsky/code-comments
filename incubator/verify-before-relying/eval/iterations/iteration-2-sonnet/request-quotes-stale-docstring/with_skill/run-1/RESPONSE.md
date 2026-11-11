The premise is partly wrong. The docstring of `parse_date` in `deliveries/dates.py` says it returns None for anything that isn't a valid date. It only returns None for text that doesn't have the shape of a date (for example "tbc" or blank). Text that has a date's shape but isn't a real date, such as `31/02/2026`, raises `ValueError` from `datetime.date`. `deliveries/importer.py` and its test already rely on that.

Checking only for None would have left a mistyped date like 31/02/2026 ending in a traceback instead of the clear error you wanted. So `deliveries/cli.py` now treats both cases the same way: on None or ValueError it prints "invalid date" to stderr and returns exit status 2.

Corrections made:
- `parse_date` docstring (`deliveries/dates.py`) now says it returns None if the text doesn't look like a date, and raises ValueError if it has a date's shape but the date doesn't exist.
- `read_date` docstring (`deliveries/formats.py`) had the same gap and now notes the ValueError.

I added `tests/test_cli.py` covering both cases (exit status 2, "invalid date" on stderr, nothing on stdout). All 7 tests pass.

Not changed: running the CLI with no argument still raises IndexError, which you didn't ask about.
