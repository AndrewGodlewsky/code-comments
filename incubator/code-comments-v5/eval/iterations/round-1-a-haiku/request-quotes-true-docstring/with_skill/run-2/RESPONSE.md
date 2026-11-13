The deliveries CLI now checks the result of `parse_date`. When the argument is not a valid date, it prints `invalid date` to stderr and exits with status 2. Before this change, a bad date such as `tomorrow` or `31/02/2026` crashed with a `TypeError` from `delivery_date(None)`.

The change is in `deliveries/cli.py`, in `main`:

- If `parse_date(argv[0])` returns `None`, print `invalid date` to stderr and return 2.
- Otherwise, print the delivery date as before.

Checked by running the module:

- `2026-03-14` prints `2026-03-17` and exits 0.
- `tomorrow` prints `invalid date` to stderr and exits 2.
- `31/02/2026` prints `invalid date` to stderr and exits 2.
- `python -m unittest discover -s tests -t .` runs 5 tests, all OK.

No comments became false, so none were changed. I did not add a test for the new branch; the CLI has no existing tests, and adding one is easy if you want it.
