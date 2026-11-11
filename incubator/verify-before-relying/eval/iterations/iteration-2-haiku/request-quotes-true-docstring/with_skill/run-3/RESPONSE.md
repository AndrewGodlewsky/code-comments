The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `deliveries/cli.py` prints `invalid date` to stderr and exits with status 2.

Your premise checks out. The `parse_date` docstring says it returns `None` for invalid input. `read_date` in `deliveries/formats.py` does return `None` for text that matches no shape or names a date that does not exist, and `tests/test_dates.py` pins `None` for blank and `"tbc"` input. I built on that as written and did not change the docstring.

Before the change, a mistyped date such as `tbc` or `31/02/2026` crashed with a `TypeError` from `delivery_date`. Now:

- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.
- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits 2.
- `python -m deliveries.cli 31/02/2026` prints `invalid date` to stderr and exits 2.

The existing 5 unit tests pass. I did not add a test for the CLI branch, since the repo has no CLI tests yet.
