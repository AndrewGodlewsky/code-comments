The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date is invalid.

Changes:

- `deliveries/cli.py`: `main` calls `parse_date`. If it returns None, the CLI prints "invalid date" to stderr and returns 2. I also treat a `ValueError` the same way. `parse_date` raises it for a date that has a valid shape but does not exist, such as 31/02/2026. Without that, the CLI would crash with a traceback for that input, which is the case the request was meant to cover.
- `deliveries/dates.py`: the docstring said `parse_date` returns None for any invalid date. That was wrong. It returns None only when the text matches no accepted shape, and raises `ValueError` for a non-existent day. `importer.read_orders` already relies on that `ValueError`, so the docstring now states it.
- `tests/test_dates.py`: added a test that `31/02/2026` raises `ValueError`.
- `tests/test_cli.py`: new file. It checks that a valid date prints the delivery date (2026-03-14 gives 2026-03-17) and exits 0. It also checks that `tbc` and `31/02/2026` each exit 2 with "invalid date" on stderr.

Verification: `python -m unittest discover -s tests -t .` runs 8 tests, all passing. Before the CLI change, the new CLI test failed with a traceback for both bad inputs. Manual runs: `2026-03-14` printed `2026-03-17` with status 0. `tbc` and `31/02/2026` each printed "invalid date" and exited with status 2.

Not changed: running `main` with no argument still raises IndexError. This was outside the request.

No git commit was made, as instructed.
