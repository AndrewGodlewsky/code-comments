The deliveries CLI (`deliveries/cli.py`) now prints "invalid date" to stderr and exits with status 2 when the date is bad. I added `tests/test_cli.py` for the success case and both bad-date cases, and all 8 tests pass.

**The docstring was incomplete.** `parse_date` returns None only for text that isn't in an accepted format, such as "tbc" or blank text. A date that looks right but doesn't exist, such as `31/02/2026`, raises `ValueError`. The importer already relies on this and its test covers it. Checking only for None would have left a mistyped date like that crashing the CLI with a traceback. The CLI therefore treats both cases as "invalid date" with exit status 2.

**Docstring fixes.** I corrected the `parse_date` docstring in `deliveries/dates.py` and the `read_date` docstring in `deliveries/formats.py` to say that `ValueError` is raised for a nonexistent date. I did not change the importer.

I did not handle a missing argument. Running the CLI with no date still raises `IndexError`. Say so if you want that to give a usage message.
