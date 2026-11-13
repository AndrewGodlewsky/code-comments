The premise is wrong. The docstring of `parse_date` in `deliveries/dates.py` says it returns None for anything that is not a valid date. That is false for well-shaped dates that do not exist. `parse_date("31/02/2026")` and `parse_date("2026-02-31")` raise `ValueError`. Only text with no date shape returns None, such as "tbc" or a blank string.

What I did:

- Corrected the `parse_date` docstring to match the code. It now says None means no date shape, and that ValueError is raised for a date shape naming a day that does not exist. The function body is unchanged.
- In `deliveries/cli.py`, `main` now treats both outcomes as an invalid date. A None result, or a ValueError from `parse_date`, prints "invalid date" to stderr and returns 2, so `sys.exit(main())` exits with status 2. Handling only None would have left 31/02/2026 crashing with a traceback.
- Added `tests/test_cli.py` with three cases: "tbc" exits 2, "31/02/2026" exits 2, and "14/03/2026" still prints 2026-03-17 with exit 0.

Verification: all 8 tests pass (`python -B -m unittest discover -s tests -t .`). Manual runs gave "invalid date" with exit 2 for "tbc" and "31/02/2026", and 2026-03-17 with exit 0 for "14/03/2026".

Not changed: `deliveries/importer.py` already catches ValueError and lists those rows as skipped, so its behaviour is unchanged.
