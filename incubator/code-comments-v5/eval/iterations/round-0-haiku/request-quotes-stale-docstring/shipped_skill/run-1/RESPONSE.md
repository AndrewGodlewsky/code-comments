The deliveries CLI now checks for a None from parse_date. When it gets None, it prints "invalid date" to stderr and exits with status 2. The change is in `deliveries/cli.py`.

I also fixed a false docstring in `deliveries/dates.py`. The `parse_date` docstring said it returns None for any invalid date. In fact, a date in an accepted shape that names no real day, such as 31/02/2026, raises ValueError (the importer relies on this). The docstring now says that.

Checks: `python -m deliveries.cli tbc` prints "invalid date" and exits 2. `python -m deliveries.cli 14/03/2026` prints 2026-03-17 and exits 0. The existing unittest suite passes (5 tests).

Gap for you to decide: an impossible date such as 31/02/2026 still produces a traceback from the CLI, because parse_date raises ValueError rather than returning None. I left it alone since you asked only about None. If you want a clear message for that case too, the CLI can catch ValueError and print the same "invalid date" message with status 2. I can add that.
