The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `main` in `deliveries/cli.py` prints `invalid date` to stderr and returns status 2, so `sys.exit(main())` exits with 2. Valid dates behave as before.

The change is four lines in `deliveries/cli.py`, placed between the `parse_date` call and the `delivery_date` call. I did not add a CLI test, so the new branch is covered only by the manual checks below.

Checks run:
- `python -m deliveries.cli "next tuesday"` printed `invalid date` to stderr and exited 2.
- `python -m deliveries.cli "2026-03-14"` printed `2026-03-17` and exited 0.
- The existing unit tests passed (5 tests, OK).
