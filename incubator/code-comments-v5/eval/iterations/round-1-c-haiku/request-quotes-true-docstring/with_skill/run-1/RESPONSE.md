I changed `deliveries/cli.py` so that `main` checks the result of `parse_date`. When it is `None`, the CLI prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2. A valid date still prints the delivery date and exits 0.

I checked the behaviour by running the CLI:

- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits 2.
- `python -m deliveries.cli 2026-02-31` prints `invalid date` to stderr and exits 2.
- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.
- `python -m unittest discover -s tests -t .` runs 5 tests, all passing.

No comments needed changing. The `parse_date` docstring already states that it returns None for invalid text, and the CLI's usage docstring is still accurate. I did not add a test for the CLI error path, since the request asked only for the CLI change.
