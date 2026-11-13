The deliveries CLI now reports a mistyped date and exits with status 2.

In `deliveries/cli.py`, `main` checks the result of `parse_date`. When it is `None`, the CLI prints `invalid date` to stderr and returns 2, so `sys.exit` ends with status 2. Valid dates behave as before.

I also handled one case your description did not mention. `parse_date` does not return `None` for a well-formed date that does not exist, such as `31/02/2026`. It raises `ValueError`, because `read_date` calls `date(...)` directly. Without a guard, that input would have crashed the CLI with a traceback. The CLI now catches `ValueError` and treats it the same as `None`, so it also prints `invalid date` and exits 2. The importer already relies on that `ValueError` to list impossible dates, so I left `dates.py` unchanged.

The docstring of `parse_date` is therefore stale: it says invalid input returns `None`, but impossible dates raise `ValueError`. I did not change it because the task was limited to the CLI. It is worth correcting separately.

Checks run from the repository directory:
- `python -m deliveries.cli 2026-03-14` and `14/03/2026` print `2026-03-17` and exit 0.
- `tbc`, `31/02/2026` and a blank argument each print `invalid date` to stderr and exit 2.
- `python -m unittest discover -s tests -t .` passes (5 tests).

I did not add a test for the CLI exit path.
