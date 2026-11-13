The deliveries CLI now prints "invalid date" to stderr and exits with status 2 for a bad date. The new tests and the existing ones pass.

One thing differed from what you described. `parse_date` only returns None for text that matches no accepted format, such as "tbc" or blank. For a date that has the right shape but doesn't exist, like 31/02/2026, it raises ValueError. `importer.py` and its test already rely on that. A check for None alone would have let a typo like 31/02/2026 crash the CLI with a traceback. So `cli.py` treats both cases as invalid.

Changes:
- `deliveries/cli.py`: catches ValueError and checks for None, then prints "invalid date" to stderr and returns 2.
- `deliveries/dates.py`: the `parse_date` docstring said None means "not a valid date". It now says None means no format matched and ValueError means the date doesn't exist.
- `deliveries/formats.py`: the `read_date` docstring now mentions the ValueError.
- `tests/test_cli.py` is new. It covers a valid date, "tbc" and 31/02/2026.
