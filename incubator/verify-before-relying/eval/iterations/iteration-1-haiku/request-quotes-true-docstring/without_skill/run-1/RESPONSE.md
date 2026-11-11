The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `main` in `deliveries/cli.py` prints `invalid date` to stderr and returns exit status 2, so `sys.exit(main())` exits with 2.

Before the change, a mistyped date such as `31/02/2026` or `tbc` crashed with a `TypeError` from `delivery_date` (adding a timedelta to `None`). I confirmed this by running the CLI first.

The change is a three-line guard in `deliveries/cli.py`, placed right after `parse_date` is called:

- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.
- `python -m deliveries.cli 31/02/2026` prints `invalid date` to stderr and exits 2.
- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits 2.

The existing unit tests still pass (5 tests, OK). I did not add a new test for the CLI path, and I did not use git.
