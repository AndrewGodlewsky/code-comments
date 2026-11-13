The deliveries CLI now prints `invalid date` to stderr and exits with status 2 when the date is not valid. Changes:

- `deliveries/cli.py`: `main` calls `parse_date`. If it returns `None`, or raises `ValueError`, it prints `invalid date` to stderr and returns 2. Valid input still prints the delivery date and returns 0.
- `deliveries/dates.py`: the `parse_date` docstring was false. It said `None` is returned for any invalid date, but a date with a valid shape that does not exist (such as `31/02/2026`) raises `ValueError`, as `importer.py` already expects. The docstring now says that.
- `tests/test_cli.py` (new): covers a valid date, a note such as `tbc`, and a non-existent day.
- `tests/test_dates.py`: adds a test that `31/02/2026` raises `ValueError`.

Verification: `python -m unittest discover -s tests -t .` runs 9 tests and all pass. Manual runs: `tbc` and `31/02/2026` each print `invalid date` and exit 2; `2026-03-14` prints `2026-03-17` and exits 0.

Decision for you: I also handled `ValueError` in the CLI, not only `None`. Without it, `31/02/2026` would produce a traceback instead of the clear message you asked for. If you want only the `None` case handled, remove the `try`/`except` in `main`.

Not changed: running `deliveries.cli` with no argument still raises `IndexError` from `argv[0]`. Tell me if you want that handled too.
