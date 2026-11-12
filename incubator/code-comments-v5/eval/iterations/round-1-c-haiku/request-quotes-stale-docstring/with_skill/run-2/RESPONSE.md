The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date is not valid.

One part of the premise was false. `parse_date` returns None only when the text matches none of the accepted formats (for example "tbc"). When the text has an accepted shape but names no real date (for example "31/02/2026"), it raises ValueError. I checked this by running it. The docstring said None for every invalid date, so I corrected it. I did not change `parse_date` to return None for impossible dates, because `deliveries/importer.py` relies on the ValueError to list those rows in `skipped`.

Because of that, the CLI handles both cases. A ValueError from `parse_date` is treated the same as None, so 31/02/2026 gets the same clear error instead of a traceback.

Changes, all inside the repository:
- `deliveries/dates.py`: the `parse_date` docstring now states both behaviours.
- `deliveries/cli.py`: `main` catches ValueError, and on None or ValueError prints "invalid date" to stderr and returns 2. Valid dates print the same output as before.
- `tests/test_cli.py` (new): covers a valid date, "tbc", and "31/02/2026". All 8 tests pass.

Not handled: running the CLI with no argument still raises IndexError from `argv[0]`. That was outside the request, so I left it alone.
