The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date is not usable.

Two things I found while doing this:

- `parse_date` does not only return None. For a well-shaped date that does not exist, such as `31/02/2026`, `read_date` calls `date(...)`, which raises ValueError. Its docstring ("or None if text is not a valid date") is therefore incomplete. `importer.py` already catches ValueError for this reason. Since you want a mistyped date to get a clear message, I made the CLI treat both cases the same way. If you would rather keep the CLI to the None check only, `31/02/2026` would give a traceback instead.
- I did not change `dates.py` or its docstring. Updating that docstring to mention the ValueError is a sensible follow-up.

Changes:
- `deliveries/cli.py`: `main` catches ValueError from `parse_date`, treats None the same way, prints "invalid date" to stderr and returns 2.
- `tests/test_cli.py` (new): covers a valid date, `tbc`, and `31/02/2026`.

Results: `python -m unittest discover -s tests -t .` runs 8 tests, all passing. `python -m deliveries.cli tbc` and `python -m deliveries.cli 31/02/2026` both print "invalid date" and exit 2. `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.

Not covered: running the CLI with no argument still raises IndexError, which I left alone because it was not part of the request.
