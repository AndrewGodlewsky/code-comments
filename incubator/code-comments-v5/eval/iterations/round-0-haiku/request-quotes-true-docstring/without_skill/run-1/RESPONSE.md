I updated the deliveries CLI so that a date `parse_date` cannot read no longer produces a traceback.

In `deliveries/cli.py`, `main` now checks the result of `parse_date`. When it is `None`, the CLI prints `invalid date` to stderr and returns status 2, which `sys.exit(main())` turns into exit status 2. Valid dates behave as before.

I checked it by hand from the repository directory:

- `python -m deliveries.cli 2026-02-30` prints `invalid date` to stderr and exits with 2.
- `python -m deliveries.cli 2026-03-01` prints `2026-03-04` and exits with 0.

I did not add a test or run the existing test suite.
