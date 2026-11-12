I changed the deliveries CLI so a date it cannot read gets a clear error.

In `deliveries/cli.py`, `main` now checks the result of `parse_date`. When it is `None`, the CLI prints `invalid date` to stderr and returns status 2, so `sys.exit(main())` exits with 2. Valid dates behave as before.

I also added `tests/test_cli.py`, which checks that an invalid date prints `invalid date` to stderr, prints nothing to stdout, and returns 2.

Verification: all 6 unit tests pass (`python -m unittest discover -s tests -t .`). Running `python -m deliveries.cli not-a-date` prints `invalid date` and exits with status 2.
