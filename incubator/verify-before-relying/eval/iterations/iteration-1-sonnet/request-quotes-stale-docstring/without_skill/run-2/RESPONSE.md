The deliveries CLI now prints "invalid date" to stderr and exits with status 2 for a bad date. One thing differed from what you described, so the check covers two cases.

`parse_date` only returns None for text that isn't shaped like a date, such as "tbc" or a blank. A date with the right shape that doesn't exist, such as `31/02/2026` or `2026-13-45`, makes it raise `ValueError` instead. Its docstring said it returns None for any invalid date, which was wrong. `importer.py` already relies on the `ValueError` behaviour. A check for None alone would have let a mistyped date like `31/02/2026` crash the CLI with a traceback.

- **`deliveries/cli.py`:** the CLI catches `ValueError` and also checks for None. Either one prints "invalid date" to stderr and returns 2.
- **`deliveries/dates.py`:** I corrected the `parse_date` docstring to describe both behaviours. I left the behaviour itself alone, so the importer is unaffected.

I ran `tbc` and `31/02/2026`, and both printed "invalid date" and exited 2. `2026-03-14` still prints its delivery date. The existing tests pass. I didn't add a test for the CLI.

I didn't handle a missing argument, which still raises `IndexError`. Say if you want that covered too.
