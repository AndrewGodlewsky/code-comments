The deliveries CLI now checks for an invalid date. In `deliveries/cli.py`, when `parse_date` returns `None`, `main` prints `invalid date` to stderr and returns 2, so `python -m deliveries.cli DATE` exits with status 2.

Before the change, `python -m deliveries.cli tbc` crashed with a `TypeError` (exit 1) inside `delivery_date`. It now prints `invalid date` and exits 2. A valid date such as `2026-03-14` still prints `2026-03-17` and exits 0. The five existing unit tests pass.

I did not add a test for the CLI path, and I did not change `importer.py`, which already skips `None` dates. No comment was added: the change is routine and the existing docstrings stay accurate.
